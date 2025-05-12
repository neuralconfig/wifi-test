"""
Network connection module for Wi-Fi testing.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from .utils.command import run_command

class NetworkManager:
    """
    Class for managing Wi-Fi network connections.
    """
    
    def __init__(self, device: str, ssid: str, password: str, logger: Optional[logging.Logger] = None, vrf: bool = False):
        """
        Initialize the network manager.

        Args:
            device: Wireless interface device name
            ssid: Wi-Fi network SSID
            password: Wi-Fi network password
            logger: Logger instance
            vrf: Enable VRF-like routing for the wireless interface
        """
        self.device = device
        self.ssid = ssid
        self.password = password
        self.logger = logger
        self.vrf = vrf
        self.wpa_conf_path = os.path.abspath("./wpa_temp.conf")
        self.vrf_table_id = 200  # ID for our custom routing table
    
    def connect_to_wifi(self) -> bool:
        """
        Connect to the specified Wi-Fi network.
        
        Returns:
            True if successful, False otherwise
        """
        if self.logger:
            self.logger.info(f"Connecting to SSID: {self.ssid} using device {self.device}")

        # Check if the wireless interface exists
        iw_dev_result = run_command(["iw", "dev"], logger=self.logger)
        if self.device not in iw_dev_result["stdout"]:
            if self.logger:
                self.logger.error(f"Wireless interface {self.device} not found!")
                self.logger.debug(f"Available interfaces: {iw_dev_result['stdout']}")
            return False

        # Print details of the interface
        if_details = run_command(["ip", "link", "show", self.device], logger=self.logger)
        if self.logger:
            self.logger.debug(f"Interface details before connection: {if_details['stdout']}")

        # First, make sure NetworkManager doesn't interfere
        if self.logger:
            self.logger.debug("Disabling NetworkManager for wifi")
        nm_result = run_command(["nmcli", "radio", "wifi", "off"], logger=self.logger)
        if not nm_result["success"] and self.logger:
            self.logger.warning("Failed to disable NetworkManager, continuing anyway")
        time.sleep(1)

        # Kill any existing wpa_supplicant processes for this interface
        if self.logger:
            self.logger.debug(f"Killing any existing wpa_supplicant processes for {self.device}")
        run_command(["pkill", "-f", f"wpa_supplicant.*{self.device}"], logger=self.logger)
        time.sleep(1)

        # Ensure the interface is up
        if self.logger:
            self.logger.debug(f"Making sure interface {self.device} is up")
        run_command(["ip", "link", "set", self.device, "up"], logger=self.logger)
        time.sleep(1)

        # Generate wpa_supplicant configuration
        if self.logger:
            self.logger.debug("Generating wpa_supplicant configuration")
        wpa_config = f"""ctrl_interface=/var/run/wpa_supplicant
network={{
    ssid="{self.ssid}"
    psk="{self.password}"
    key_mgmt=WPA-PSK
    scan_ssid=1
}}
"""
        with open(self.wpa_conf_path, "w") as f:
            f.write(wpa_config)

        if self.logger:
            self.logger.debug(f"wpa_supplicant config written to {self.wpa_conf_path}")

        # Check for existing wpa_supplicant processes
        ps_result = run_command(["ps", "aux", "|", "grep", "wpa_supplicant"], logger=self.logger)
        if self.logger:
            self.logger.debug(f"Existing wpa_supplicant processes: {ps_result['stdout']}")

        # Start wpa_supplicant in debug mode
        if self.logger:
            self.logger.info("Starting wpa_supplicant...")
        wpa_result = run_command([
            "wpa_supplicant",
            "-d",  # Debug output
            "-B",  # Run in background
            "-i", self.device,  # Interface
            "-c", self.wpa_conf_path  # Config file
        ], logger=self.logger)

        if not wpa_result["success"]:
            if self.logger:
                self.logger.error(f"Failed to start wpa_supplicant: {wpa_result['stderr']}")
                self.logger.info("Trying again with verbose output...")
            wpa_verbose = run_command([
                "wpa_supplicant",
                "-v",  # Verbose output
                "-i", self.device,  # Interface
                "-c", self.wpa_conf_path,  # Config file
                "-B"   # Run in background
            ], logger=self.logger)

            if not wpa_verbose["success"]:
                if self.logger:
                    self.logger.error("Failed to start wpa_supplicant in verbose mode too")
                    self.logger.error(f"Error: {wpa_verbose['stderr']}")
                return False

        if self.logger:
            self.logger.info("Started wpa_supplicant, waiting for connection...")

        # Use this method to monitor and detect authentication issues before trying DHCP
        time.sleep(2)  # Initial wait for wpa_supplicant to start

        # Check for authentication failures with a more aggressive approach to catch issues early
        auth_failure = False
        for attempt in range(1, 6):  # More attempts with shorter interval to catch failures quickly
            if self.logger:
                self.logger.debug(f"Checking connection status (attempt {attempt}/5)...")

            # Check wpa_supplicant output directly first (faster than waiting for logs)
            wpa_status = run_command([
                "wpa_cli", "-i", self.device, "status"
            ], logger=self.logger)
            if self.logger:
                self.logger.debug(f"wpa_cli status: {wpa_status['stdout']}")

            # Immediately fail on specific authentication failure indicators or handshake in progress too long
            auth_fail_indicators = [
                "WRONG_KEY", "HANDSHAKE_FAILED", "4WAY_HANDSHAKE_FAILED",
                "ASSOCIATION_REJECT", "AUTHENTICATION_FAILED", "DISCONNECTED"
            ]

            # If we see a 4-way handshake, wait and check if we get COMPLETED state
            if "4WAY_HANDSHAKE" in wpa_status["stdout"]:
                if self.logger:
                    self.logger.debug("4-way handshake in progress, waiting for completion...")
                # Wait a moment for handshake to complete
                time.sleep(2)

                # Check status again to see if handshake completed
                wpa_status_after = run_command([
                    "wpa_cli", "-i", self.device, "status"
                ], logger=self.logger)
                if self.logger:
                    self.logger.debug(f"wpa_cli status after wait: {wpa_status_after['stdout']}")

                # If still in handshake or disconnected, it's likely a password failure
                if "4WAY_HANDSHAKE" in wpa_status_after["stdout"] or "DISCONNECTED" in wpa_status_after["stdout"]:
                    if self.logger:
                        self.logger.error("Authentication failed - 4-way handshake did not complete")
                    auth_failure = True
                    break

            if any(indicator in wpa_status["stdout"] for indicator in auth_fail_indicators):
                if self.logger:
                    self.logger.error(f"WPA authentication failure detected in status output")
                auth_failure = True
                break

            # Also check current log output for immediate failures (dmesg is more real-time)
            dmesg = run_command(["dmesg", "|", "grep", "-i", "wpa"], logger=self.logger)
            if self.logger:
                self.logger.debug(f"dmesg wpa entries: {dmesg['stdout']}")

            # Common authentication failure patterns in kernel messages
            if any(error in dmesg["stdout"] for error in [
                "authentication with", "failed", "4-Way Handshake failed",
                "wrong password", "handshake timeout"
            ]):
                if self.logger:
                    self.logger.error("Authentication failed - Detected in kernel logs")
                auth_failure = True
                break

            # Check if connected successfully
            iw_result = run_command(["iw", "dev", self.device, "link"], logger=self.logger)
            if self.logger:
                self.logger.debug(f"iw dev link: {iw_result['stdout']}")

            # Check for both physical connection and authentication success
            if "Connected to" in iw_result["stdout"] and "COMPLETED" in wpa_status["stdout"]:
                if self.logger:
                    self.logger.info(f"Successfully associated with AP and authenticated: {iw_result['stdout']}")
                # If we see successful connection and authentication, break the loop to proceed with DHCP
                break

            # If we have connection but not COMPLETED state, just note it and continue trying
            if "Connected to" in iw_result["stdout"] and "COMPLETED" not in wpa_status["stdout"]:
                if self.logger:
                    self.logger.debug("Connected to AP but authentication not yet complete")

            # Short wait between checks to catch early failures
            time.sleep(2)

        # If we have an explicit authentication failure, return immediately
        if auth_failure:
            if self.logger:
                self.logger.error("Authentication failed - Incorrect password or authentication issue")
            # Stop wpa_supplicant to clean up
            run_command(["pkill", "-f", f"wpa_supplicant.*{self.device}"], logger=self.logger)
            return False

        # If we reach here without connecting or explicit failure, try more aggressive log checking
        if self.logger:
            self.logger.debug("Checking system logs for authentication issues...")

        # Check multiple log sources for problems
        log_sources = [
            ["grep", "-i", "wpa_supplicant", "/var/log/syslog"],
            ["journalctl", "-u", "wpa_supplicant", "--no-pager", "-n", "50"],
            ["wpa_cli", "-i", self.device, "status"]
        ]

        for cmd in log_sources:
            log_result = run_command(cmd, logger=self.logger)

            # Look for authentication errors in the output
            error_patterns = [
                "authentication with", "failed", "4-Way Handshake failed",
                "WRONG_KEY", "WPA:", "reason=15", "reason=3", "wrong password",
                "timeout", "DISCONNECT", "HANDSHAKE", "unable to connect"
            ]

            if any(pattern in log_result["stdout"] for pattern in error_patterns):
                if self.logger:
                    self.logger.error(f"Authentication issue detected in logs")
                return False

        # Final connection check before proceeding
        iw_final = run_command(["iw", "dev", self.device, "link"], logger=self.logger)
        wpa_final = run_command(["wpa_cli", "-i", self.device, "status"], logger=self.logger)

        # Check both connection and authentication status
        if "Connected to" not in iw_final["stdout"]:
            if self.logger:
                self.logger.warning("Could not confirm AP association")
            # Return false to avoid trying DHCP if we can't confirm association
            return False

        # Check if we have a successful authentication
        if "COMPLETED" not in wpa_final["stdout"]:
            if self.logger:
                self.logger.error("Connection established but authentication not completed")
                self.logger.error("This is likely due to an incorrect password")
            return False

        if self.logger:
            self.logger.info("Connection and authentication successful, proceeding with DHCP")

        # Get IP address via DHCP
        if self.logger:
            self.logger.info("Obtaining IP address via DHCP...")
        dhcp_result = run_command(["dhclient", "-v", self.device], timeout=60, logger=self.logger)

        if not dhcp_result["success"]:
            if self.logger:
                self.logger.error(f"Failed to get IP address via DHCP: {dhcp_result['stderr']}")

            # Check if we got an IP address anyway
            ip_addr = run_command(["ip", "addr", "show", self.device], logger=self.logger)
            if "inet " in ip_addr["stdout"]:
                if self.logger:
                    self.logger.info("IP address found despite dhclient failure, continuing...")
            else:
                if self.logger:
                    self.logger.error("No IP address obtained, connection failed")
                return False

        # Display network interface information
        if self.logger:
            self.logger.info("Checking network interface details...")
        ip_addr = run_command(["ip", "addr", "show", self.device], logger=self.logger)
        if self.logger:
            self.logger.info(f"IP address info: {ip_addr['stdout']}")

        # Get current connection details
        iw_result = run_command(["iw", "dev", self.device, "link"], logger=self.logger)
        iw_details = run_command(["iw", "dev", self.device, "info"], logger=self.logger)
        if self.logger:
            self.logger.info(f"Connection details: {iw_result['stdout']}")
            self.logger.debug(f"Interface details: {iw_details['stdout']}")

        if iw_result["success"] and "Connected to" in iw_result["stdout"]:
            if self.logger:
                self.logger.info(f"Successfully connected to SSID: {self.ssid}")

            # Get signal strength
            signal_check = run_command(["iw", "dev", self.device, "station", "dump"], logger=self.logger)
            if "signal:" in signal_check["stdout"]:
                signal_line = [line for line in signal_check["stdout"].split("\n") if "signal:" in line]
                if signal_line and self.logger:
                    self.logger.info(f"Signal strength: {signal_line[0].strip()}")

            # Setup VRF-like routing if enabled
            if self.vrf:
                if self.logger:
                    self.logger.info("Setting up VRF-like routing for wireless interface...")
                self.setup_vrf_routing()

            return True
        else:
            if self.logger:
                self.logger.warning("Connection status uncertain - unable to confirm association with AP")

            # Check if we have an IP address anyway
            if "inet " in ip_addr["stdout"]:
                if self.logger:
                    self.logger.info("IP address obtained, assuming connection is functional")

                # Setup VRF-like routing if enabled (in secondary check case)
                if self.vrf:
                    if self.logger:
                        self.logger.info("Setting up VRF-like routing for wireless interface...")
                    self.setup_vrf_routing()

                return True
            else:
                if self.logger:
                    self.logger.error("No AP association and no IP address, connection failed")
                return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the Wi-Fi network and clean up.
        
        Returns:
            True if successful, False otherwise
        """
        if self.logger:
            self.logger.info(f"Disconnecting from {self.ssid}")
        
        # Clean up VRF routing if enabled
        if self.vrf:
            if self.logger:
                self.logger.info("Cleaning up VRF-like routing for wireless interface...")
            self.cleanup_vrf_routing()

        # Kill wpa_supplicant
        run_command(["pkill", "-f", f"wpa_supplicant.*{self.device}"], logger=self.logger)

        # Release DHCP lease
        run_command(["dhclient", "-r", self.device], logger=self.logger)

        # Bring down interface
        run_command(["ip", "link", "set", self.device, "down"], logger=self.logger)
        
        # Remove temporary config
        if os.path.exists(self.wpa_conf_path):
            os.remove(self.wpa_conf_path)
        
        if self.logger:
            self.logger.info("Successfully disconnected from Wi-Fi network")
        return True

    def setup_vrf_routing(self) -> bool:
        """
        Create a custom routing table for the wireless interface.
        This ensures traffic generated by ping tests uses the wireless interface.

        Returns:
            True if successful, False otherwise
        """
        # Get the IP address of the wireless interface
        ip_info = run_command(["ip", "-j", "addr", "show", self.device], logger=self.logger)

        try:
            # Extract IP address
            import json
            import re

            # Try to parse IP address from JSON first
            device_ip = None
            prefix = None
            gateway = None

            try:
                ip_data = json.loads(ip_info["stdout"])
                for addr_info in ip_data[0].get("addr_info", []):
                    if addr_info.get("family") == "inet":  # IPv4
                        device_ip = addr_info.get("local")
                        prefix = addr_info.get("prefixlen")
                        if device_ip:
                            break
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                if self.logger:
                    self.logger.warning(f"Error parsing IP info from JSON: {str(e)}")

                # Fallback to text parsing if JSON fails
                ip_match = re.search(r'inet\s+([0-9.]+)/([0-9]+)', ip_info["stdout"])
                if ip_match:
                    device_ip = ip_match.group(1)
                    prefix = ip_match.group(2)

            if not device_ip:
                if self.logger:
                    self.logger.error("Could not determine IP address for custom routing")
                return False

            # Get DHCP-provided gateway information (most reliable)
            # Check for dhclient lease files - try various possible locations
            lease_files = [
                "/var/lib/dhcp/dhclient.leases",
                "/var/lib/dhcp/dhclient.*.leases",
                "/var/lib/dhclient/dhclient.leases",
                f"/var/lib/dhcp/dhclient.{self.device}.leases"
            ]

            for lease_file in lease_files:
                # Use ls to check if file exists because it might include wildcards
                find_lease = run_command(["ls", "-1", lease_file], logger=self.logger)
                if find_lease["success"]:
                    files = find_lease["stdout"].strip().split('\n')
                    for file in files:
                        if file and file != "ls: cannot access":  # Valid file found
                            lease_info = run_command(["cat", file], logger=self.logger)
                            if lease_info["success"]:
                                # Look for the most recent lease for our interface
                                leases = lease_info["stdout"].split("lease {")
                                for lease in reversed(leases):  # Start with most recent lease
                                    if self.device in lease and "routers" in lease:
                                        router_match = re.search(r'option routers ([0-9.]+);', lease)
                                        if router_match:
                                            gateway = router_match.group(1)
                                            if self.logger:
                                                self.logger.info(f"Found DHCP-provided gateway from {file}: {gateway}")
                                            break
                            if gateway:
                                break
                if gateway:
                    break

            # If no gateway from DHCP lease, try directly asking the dhclient process
            if not gateway:
                # Try getting dhclient configuration
                dhclient_config = run_command(["dhclient", "-T", "-nw", "-1", self.device], logger=self.logger)
                if dhclient_config["success"] and "router" in dhclient_config["stdout"]:
                    router_match = re.search(r'router ([0-9.]+)', dhclient_config["stdout"])
                    if router_match:
                        gateway = router_match.group(1)
                        if self.logger:
                            self.logger.info(f"Found gateway from dhclient: {gateway}")

            # If still no gateway, try looking at the route table
            if not gateway:
                # First check for default route
                gateway_info = run_command(["ip", "route", "show", "dev", self.device], logger=self.logger)
                gateway_match = re.search(r'default\s+via\s+([0-9.]+)', gateway_info["stdout"])
                if gateway_match:
                    gateway = gateway_match.group(1)
                    if self.logger:
                        self.logger.info(f"Found gateway from route table: {gateway}")
                else:
                    # If default gateway is not found, try extracting the first hop in the subnet
                    route_match = re.search(r'[0-9.]+/[0-9]+\s+via\s+([0-9.]+)', gateway_info["stdout"])
                    if route_match:
                        gateway = route_match.group(1)
                        if self.logger:
                            self.logger.info(f"Found gateway as first hop: {gateway}")

            # Last resort: guess gateway from IP address
            if not gateway:
                # If no gateway found, use standard gateway heuristics
                octets = device_ip.split('.')
                if len(octets) == 4 and prefix:
                    # For common /24 networks, try gateway at .1
                    if int(prefix) == 24:
                        gateway = f"{octets[0]}.{octets[1]}.{octets[2]}.1"
                    # For /16 networks, make an educated guess
                    elif int(prefix) == 16:
                        gateway = f"{octets[0]}.{octets[1]}.0.1"
                    else:
                        gateway = f"{octets[0]}.{octets[1]}.{octets[2]}.1"

                    if self.logger:
                        self.logger.warning(f"Could not determine gateway from DHCP. Guessing: {gateway}")
                else:
                    if self.logger:
                        self.logger.error("Could not determine gateway for custom routing")
                    return False

            subnet = f"{device_ip}/{prefix}" if prefix else f"{device_ip}/24"  # Default to /24 if prefix not found

            if self.logger:
                self.logger.info(f"Setting up custom routing for {self.device} with IP {device_ip} via gateway {gateway}")

            # Create routing table definition in /etc/iproute2/rt_tables if it doesn't exist
            # Note: This requires root privileges
            rt_tables_cmd = run_command([
                "grep", "-q", f"{self.vrf_table_id} wifi-test", "/etc/iproute2/rt_tables"
            ], logger=self.logger)

            if not rt_tables_cmd["success"]:
                if self.logger:
                    self.logger.info("Adding wifi-test routing table to /etc/iproute2/rt_tables")
                run_command([
                    "bash", "-c", f"echo '{self.vrf_table_id} wifi-test' >> /etc/iproute2/rt_tables"
                ], logger=self.logger)

            # Add rule to use table wifi-test for traffic from this IP
            run_command([
                "ip", "rule", "add", "from", device_ip, "table", "wifi-test"
            ], logger=self.logger)

            # Add route for local subnet
            run_command([
                "ip", "route", "add", subnet, "dev", self.device, "table", "wifi-test"
            ], logger=self.logger)

            # Add default route through wireless gateway
            run_command([
                "ip", "route", "add", "default", "via", gateway, "dev", self.device, "table", "wifi-test"
            ], logger=self.logger)

            # Verify the routing table was created correctly
            if self.logger:
                route_check = run_command(["ip", "route", "show", "table", "wifi-test"], logger=self.logger)
                self.logger.info(f"VRF-like routing table created: {route_check['stdout']}")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to configure VRF-like routing: {str(e)}")
            return False

    def cleanup_vrf_routing(self) -> bool:
        """
        Remove custom routing rules created for testing.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the IP address
            ip_info = run_command(["ip", "-j", "addr", "show", self.device], logger=self.logger)
            device_ip = None

            try:
                import json
                ip_data = json.loads(ip_info["stdout"])
                for addr_info in ip_data[0].get("addr_info", []):
                    if addr_info.get("family") == "inet":  # IPv4
                        device_ip = addr_info.get("local")
                        if device_ip:
                            break
            except (json.JSONDecodeError, IndexError, KeyError, ValueError) as e:
                if self.logger:
                    self.logger.warning(f"Error parsing IP info from JSON: {str(e)}")

                # Fallback to text parsing if JSON fails
                import re
                ip_match = re.search(r'inet\s+([0-9.]+)/[0-9]+', ip_info["stdout"])
                if ip_match:
                    device_ip = ip_match.group(1)

            if device_ip:
                # Remove the rule
                rule_del = run_command([
                    "ip", "rule", "del", "from", device_ip, "table", "wifi-test"
                ], logger=self.logger)

                if rule_del["success"] and self.logger:
                    self.logger.info(f"Removed custom routing rule for {device_ip}")

            # Flush the routing table
            route_flush = run_command([
                "ip", "route", "flush", "table", "wifi-test"
            ], logger=self.logger)

            if route_flush["success"] and self.logger:
                self.logger.info("Flushed wifi-test routing table")

            return True

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error cleaning up VRF-like routing: {str(e)}")
            return False