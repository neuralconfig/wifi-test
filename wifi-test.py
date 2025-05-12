#!/usr/bin/env python3
"""
Wi-Fi Connection Test Tool

A Python script to test Wi-Fi connections with specific parameters:
- Connect to a specified SSID with password
- Set custom MAC address
- Ping specified targets from the wireless interface
- Disconnect when done
"""

import subprocess
import argparse
import sys
import time
import logging
import re
import os
from typing import List, Dict, Any, Optional


class WiFiTester:
    """Class for testing Wi-Fi connections with specific parameters."""

    def __init__(self, device: str, ssid: str, password: str, mac: str,
                 ping_targets: List[str], ping_count: int,
                 iperf_server: Optional[str] = None, iperf_port: int = 5201,
                 iperf_protocol: str = 'tcp', iperf_duration: int = 10,
                 iperf_bandwidth: str = '100M', iperf_parallel: int = 1,
                 iperf_reverse: bool = False):
        self.device = device
        self.ssid = ssid
        self.password = password
        self.mac = mac
        self.ping_targets = ping_targets
        self.ping_count = ping_count

        # iperf parameters
        self.iperf_server = iperf_server
        self.iperf_port = iperf_port
        self.iperf_protocol = iperf_protocol
        self.iperf_duration = iperf_duration
        self.iperf_bandwidth = iperf_bandwidth
        self.iperf_parallel = iperf_parallel
        self.iperf_reverse = iperf_reverse

        self.setup_logging()
        
    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.DEBUG,  # Changed from INFO to DEBUG for more verbose output
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("wifi_test.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Wi-Fi Test Tool initialized")
    
    def run_command(self, command: List[str], timeout: int = 30) -> Dict[str, Any]:
        """
        Run a shell command and return the result.

        Args:
            command: List of command and arguments
            timeout: Timeout in seconds

        Returns:
            Dictionary containing success status, stdout, stderr, and return code
        """
        cmd_str = ' '.join(command)
        self.logger.debug(f"Running command: {cmd_str}")

        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "command": cmd_str
        }

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            result["stdout"] = process.stdout
            result["stderr"] = process.stderr
            result["returncode"] = process.returncode
            result["success"] = process.returncode == 0

            # Log stdout for debugging (but truncate if very long)
            if process.stdout:
                stdout_log = process.stdout if len(process.stdout) < 500 else process.stdout[:500] + "... [truncated]"
                self.logger.debug(f"Command stdout: {stdout_log}")

            if not result["success"]:
                self.logger.warning(f"Command failed with return code {process.returncode}")
                self.logger.warning(f"Command: {cmd_str}")
                self.logger.warning(f"stderr: {process.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout} seconds: {cmd_str}")
            result["stderr"] = f"Command timed out after {timeout} seconds"

        except Exception as e:
            self.logger.error(f"Error executing command: {cmd_str}")
            self.logger.error(f"Error details: {str(e)}")
            result["stderr"] = str(e)

        return result
    
    def check_root(self) -> bool:
        """Check if the script is running with root privileges."""
        is_root = os.geteuid() == 0
        if not is_root:
            self.logger.error("This script must be run as root (sudo)")
        return is_root

    def check_wifi_interfaces(self) -> List[str]:
        """Check for available wireless interfaces and return a list of them."""
        self.logger.info("Checking for available wireless interfaces...")

        # Try using iw to list interfaces
        iw_result = self.run_command(["iw", "dev"])
        interfaces = []

        if iw_result["success"]:
            # Parse the output to find interface names
            lines = iw_result["stdout"].split('\n')
            for line in lines:
                if "Interface" in line:
                    # Extract the interface name
                    interface = line.split("Interface")[1].strip()
                    interfaces.append(interface)

        if not interfaces:
            # Fallback to using ip link if iw didn't find any
            ip_result = self.run_command(["ip", "link", "show"])
            if ip_result["success"]:
                lines = ip_result["stdout"].split('\n')
                for line in lines:
                    if ":" in line and "state" in line:
                        # This line likely contains an interface name
                        # Extract the interface name (between the number and the colon)
                        parts = line.split(':')
                        if len(parts) >= 2:
                            interface = parts[1].strip()
                            if "wlan" in interface or "wlp" in interface or "wl" in interface:
                                interfaces.append(interface)

        if interfaces:
            self.logger.info(f"Found wireless interfaces: {', '.join(interfaces)}")
        else:
            self.logger.warning("No wireless interfaces found!")

        return interfaces
    
    def set_mac_address(self) -> bool:
        """Set the MAC address of the wireless interface."""
        self.logger.info(f"Setting MAC address of {self.device} to {self.mac}")
        
        # First, bring the interface down
        down_result = self.run_command(["ip", "link", "set", self.device, "down"])
        if not down_result["success"]:
            self.logger.error(f"Failed to bring down interface {self.device}")
            return False
        
        # Set the MAC address
        mac_result = self.run_command(["ip", "link", "set", self.device, "address", self.mac])
        if not mac_result["success"]:
            self.logger.error(f"Failed to set MAC address to {self.mac}")
            # Try to bring the interface back up before returning
            self.run_command(["ip", "link", "set", self.device, "up"])
            return False
        
        # Bring the interface back up
        up_result = self.run_command(["ip", "link", "set", self.device, "up"])
        if not up_result["success"]:
            self.logger.error(f"Failed to bring up interface {self.device}")
            return False
        
        self.logger.info(f"Successfully set MAC address to {self.mac}")
        return True
    
    def connect_to_wifi(self) -> bool:
        """Connect to the specified Wi-Fi network."""
        self.logger.info(f"Connecting to SSID: {self.ssid} using device {self.device}")

        # Check if the wireless interface exists
        iw_dev_result = self.run_command(["iw", "dev"])
        if self.device not in iw_dev_result["stdout"]:
            self.logger.error(f"Wireless interface {self.device} not found!")
            self.logger.debug(f"Available interfaces: {iw_dev_result['stdout']}")
            return False

        # Print details of the interface
        if_details = self.run_command(["ip", "link", "show", self.device])
        self.logger.debug(f"Interface details before connection: {if_details['stdout']}")

        # First, make sure NetworkManager doesn't interfere
        self.logger.debug("Disabling NetworkManager for wifi")
        nm_result = self.run_command(["nmcli", "radio", "wifi", "off"])
        if not nm_result["success"]:
            self.logger.warning("Failed to disable NetworkManager, continuing anyway")
        time.sleep(1)

        # Kill any existing wpa_supplicant processes for this interface
        self.logger.debug(f"Killing any existing wpa_supplicant processes for {self.device}")
        self.run_command(["pkill", "-f", f"wpa_supplicant.*{self.device}"])
        time.sleep(1)

        # Ensure the interface is up
        self.logger.debug(f"Making sure interface {self.device} is up")
        self.run_command(["ip", "link", "set", self.device, "up"])
        time.sleep(1)

        # Generate wpa_supplicant configuration
        self.logger.debug("Generating wpa_supplicant configuration")
        wpa_config = f"""ctrl_interface=/var/run/wpa_supplicant
network={{
    ssid="{self.ssid}"
    psk="{self.password}"
    key_mgmt=WPA-PSK
    scan_ssid=1
}}
"""
        wpa_conf_path = os.path.abspath("./wpa_temp.conf")
        with open(wpa_conf_path, "w") as f:
            f.write(wpa_config)

        self.logger.debug(f"wpa_supplicant config written to {wpa_conf_path}")

        # Check for existing wpa_supplicant processes
        ps_result = self.run_command(["ps", "aux", "|", "grep", "wpa_supplicant"])
        self.logger.debug(f"Existing wpa_supplicant processes: {ps_result['stdout']}")

        # Start wpa_supplicant in debug mode
        self.logger.info("Starting wpa_supplicant...")
        wpa_result = self.run_command([
            "wpa_supplicant",
            "-d",  # Debug output
            "-B",  # Run in background
            "-i", self.device,  # Interface
            "-c", wpa_conf_path  # Config file
        ])

        if not wpa_result["success"]:
            self.logger.error(f"Failed to start wpa_supplicant: {wpa_result['stderr']}")
            # Try again with verbose output to see more details
            self.logger.info("Trying again with verbose output...")
            wpa_verbose = self.run_command([
                "wpa_supplicant",
                "-v",  # Verbose output
                "-i", self.device,  # Interface
                "-c", wpa_conf_path,  # Config file
                "-B"   # Run in background
            ])

            if not wpa_verbose["success"]:
                self.logger.error("Failed to start wpa_supplicant in verbose mode too")
                self.logger.error(f"Error: {wpa_verbose['stderr']}")
                return False

        self.logger.info("Started wpa_supplicant, waiting for connection...")

        # Use this method to monitor and detect authentication issues before trying DHCP
        time.sleep(2)  # Initial wait for wpa_supplicant to start

        # Check for authentication failures with a more aggressive approach to catch issues early
        auth_failure = False
        for attempt in range(1, 6):  # More attempts with shorter interval to catch failures quickly
            self.logger.debug(f"Checking connection status (attempt {attempt}/5)...")

            # Check wpa_supplicant output directly first (faster than waiting for logs)
            wpa_status = self.run_command([
                "wpa_cli", "-i", self.device, "status"
            ])
            self.logger.debug(f"wpa_cli status: {wpa_status['stdout']}")

            # Immediately fail on specific authentication failure indicators or handshake in progress too long
            auth_fail_indicators = [
                "WRONG_KEY", "HANDSHAKE_FAILED", "4WAY_HANDSHAKE_FAILED",
                "ASSOCIATION_REJECT", "AUTHENTICATION_FAILED", "DISCONNECTED"
            ]

            # If we see a 4-way handshake, wait and check if we get COMPLETED state
            if "4WAY_HANDSHAKE" in wpa_status["stdout"]:
                self.logger.debug("4-way handshake in progress, waiting for completion...")
                # Wait a moment for handshake to complete
                time.sleep(2)

                # Check status again to see if handshake completed
                wpa_status_after = self.run_command([
                    "wpa_cli", "-i", self.device, "status"
                ])
                self.logger.debug(f"wpa_cli status after wait: {wpa_status_after['stdout']}")

                # If still in handshake or disconnected, it's likely a password failure
                if "4WAY_HANDSHAKE" in wpa_status_after["stdout"] or "DISCONNECTED" in wpa_status_after["stdout"]:
                    self.logger.error("Authentication failed - 4-way handshake did not complete")
                    auth_failure = True
                    break

            if any(indicator in wpa_status["stdout"] for indicator in auth_fail_indicators):
                self.logger.error(f"WPA authentication failure detected in status output")
                auth_failure = True
                break

            # Also check current log output for immediate failures (dmesg is more real-time)
            dmesg = self.run_command(["dmesg", "|", "grep", "-i", "wpa"])
            self.logger.debug(f"dmesg wpa entries: {dmesg['stdout']}")

            # Common authentication failure patterns in kernel messages
            if any(error in dmesg["stdout"] for error in [
                "authentication with", "failed", "4-Way Handshake failed",
                "wrong password", "handshake timeout"
            ]):
                self.logger.error("Authentication failed - Detected in kernel logs")
                auth_failure = True
                break

            # Check if connected successfully
            iw_result = self.run_command(["iw", "dev", self.device, "link"])
            self.logger.debug(f"iw dev link: {iw_result['stdout']}")

            # Check for both physical connection and authentication success
            if "Connected to" in iw_result["stdout"] and "COMPLETED" in wpa_status["stdout"]:
                self.logger.info(f"Successfully associated with AP and authenticated: {iw_result['stdout']}")
                # If we see successful connection and authentication, return true to proceed with DHCP
                return True

            # If we have connection but not COMPLETED state, just note it and continue trying
            if "Connected to" in iw_result["stdout"] and "COMPLETED" not in wpa_status["stdout"]:
                self.logger.debug("Connected to AP but authentication not yet complete")

            # Short wait between checks to catch early failures
            time.sleep(2)

        # If we have an explicit authentication failure, return immediately
        if auth_failure:
            self.logger.error("Authentication failed - Incorrect password or authentication issue")
            # Stop wpa_supplicant to clean up
            self.run_command(["pkill", "-f", f"wpa_supplicant.*{self.device}"])
            return False

        # If we reach here without connecting or explicit failure, try more aggressive log checking
        self.logger.debug("Checking system logs for authentication issues...")

        # Check multiple log sources for problems
        log_sources = [
            ["grep", "-i", "wpa_supplicant", "/var/log/syslog"],
            ["journalctl", "-u", "wpa_supplicant", "--no-pager", "-n", "50"],
            ["wpa_cli", "-i", self.device, "status"]
        ]

        for cmd in log_sources:
            log_result = self.run_command(cmd)

            # Look for authentication errors in the output
            error_patterns = [
                "authentication with", "failed", "4-Way Handshake failed",
                "WRONG_KEY", "WPA:", "reason=15", "reason=3", "wrong password",
                "timeout", "DISCONNECT", "HANDSHAKE", "unable to connect"
            ]

            if any(pattern in log_result["stdout"] for pattern in error_patterns):
                self.logger.error(f"Authentication issue detected in logs")
                return False

        # Final connection check before proceeding
        iw_final = self.run_command(["iw", "dev", self.device, "link"])
        wpa_final = self.run_command(["wpa_cli", "-i", self.device, "status"])

        # Check both connection and authentication status
        if "Connected to" not in iw_final["stdout"]:
            self.logger.warning("Could not confirm AP association")
            # Return false to avoid trying DHCP if we can't confirm association
            return False

        # Check if we have a successful authentication
        if "COMPLETED" not in wpa_final["stdout"]:
            self.logger.error("Connection established but authentication not completed")
            self.logger.error("This is likely due to an incorrect password")
            return False

        self.logger.info("Connection and authentication successful, proceeding with DHCP")

        # Get IP address via DHCP
        self.logger.info("Obtaining IP address via DHCP...")
        dhcp_result = self.run_command(["dhclient", "-v", self.device], timeout=60)

        if not dhcp_result["success"]:
            self.logger.error(f"Failed to get IP address via DHCP: {dhcp_result['stderr']}")

            # Check if we got an IP address anyway
            ip_addr = self.run_command(["ip", "addr", "show", self.device])
            if "inet " in ip_addr["stdout"]:
                self.logger.info("IP address found despite dhclient failure, continuing...")
            else:
                self.logger.error("No IP address obtained, connection failed")
                return False

        # Display network interface information
        self.logger.info("Checking network interface details...")
        ip_addr = self.run_command(["ip", "addr", "show", self.device])
        self.logger.info(f"IP address info: {ip_addr['stdout']}")

        # Get current connection details
        iw_result = self.run_command(["iw", "dev", self.device, "link"])
        iw_details = self.run_command(["iw", "dev", self.device, "info"])
        self.logger.info(f"Connection details: {iw_result['stdout']}")
        self.logger.debug(f"Interface details: {iw_details['stdout']}")

        if iw_result["success"] and "Connected to" in iw_result["stdout"]:
            self.logger.info(f"Successfully connected to SSID: {self.ssid}")

            # Get signal strength
            signal_check = self.run_command(["iw", "dev", self.device, "station", "dump"])
            if "signal:" in signal_check["stdout"]:
                signal_line = [line for line in signal_check["stdout"].split("\n") if "signal:" in line]
                if signal_line:
                    self.logger.info(f"Signal strength: {signal_line[0].strip()}")

            return True
        else:
            self.logger.warning("Connection status uncertain - unable to confirm association with AP")

            # Check if we have an IP address anyway
            if "inet " in ip_addr["stdout"]:
                self.logger.info("IP address obtained, assuming connection is functional")
                return True
            else:
                self.logger.error("No AP association and no IP address, connection failed")
                return False
    
    def ping_from_interface(self, target: str) -> Dict[str, Any]:
        """
        Ping a target from the specified wireless interface.
        
        Args:
            target: IP address or hostname to ping
            
        Returns:
            Dictionary with ping results
        """
        self.logger.info(f"Pinging {target} from interface {self.device} ({self.ping_count} times)")
        
        ping_result = self.run_command([
            "ping", 
            "-c", str(self.ping_count),  # Count
            "-I", self.device,  # Interface
            target
        ])
        
        return {
            "target": target,
            "success": ping_result["success"],
            "output": ping_result["stdout"],
            "error": ping_result["stderr"]
        }
    
    def ping_all_targets(self) -> List[Dict[str, Any]]:
        """Ping all specified targets and return results."""
        results = []

        for target in self.ping_targets:
            results.append(self.ping_from_interface(target))

        return results

    def run_iperf_test(self) -> Dict[str, Any]:
        """
        Run an iperf bandwidth test to the specified server.

        Returns:
            Dictionary with test results, including success status and bandwidth values.
        """
        self.logger.info(f"Running iperf test to server {self.iperf_server}")

        # Build the iperf command with appropriate parameters
        iperf_cmd = ["iperf3", "-c", self.iperf_server, "-p", str(self.iperf_port),
                     "-t", str(self.iperf_duration), "-J"]  # JSON output

        # Add protocol-specific parameters
        if self.iperf_protocol == 'udp':
            iperf_cmd.extend(["-u", "-b", self.iperf_bandwidth])

        # Add parallel streams if specified
        if self.iperf_parallel > 1:
            iperf_cmd.extend(["-P", str(self.iperf_parallel)])

        # Add reverse direction if specified
        if self.iperf_reverse:
            iperf_cmd.append("-R")

        # Force iperf to use the Wi-Fi interface by binding to its IP
        # First, get the IP address of the Wi-Fi interface
        ip_result = self.run_command(["ip", "-j", "addr", "show", "dev", self.device])

        # Initialize with default result
        result = {
            "success": False,
            "error": "Failed to run iperf test",
            "protocol": self.iperf_protocol,
            "duration": self.iperf_duration,
            "bandwidth": "0",
            "bandwidth_units": "bps"
        }

        if ip_result["success"]:
            try:
                # Parse IP address from JSON output if available
                import json
                ip_data = json.loads(ip_result["stdout"])

                # Find IPv4 address
                for addr_info in ip_data[0].get("addr_info", []):
                    if addr_info.get("family") == "inet":  # IPv4
                        device_ip = addr_info.get("local")
                        if device_ip:
                            iperf_cmd.extend(["-B", device_ip])
                            self.logger.info(f"Binding iperf to interface IP: {device_ip}")
                            break
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                self.logger.warning(f"Failed to parse IP address from JSON: {str(e)}")
                # Fallback to text parsing if JSON fails
                ip_text = self.run_command(["ip", "addr", "show", "dev", self.device])
                if ip_text["success"]:
                    import re
                    ip_match = re.search(r'inet\s+([0-9.]+)', ip_text["stdout"])
                    if ip_match:
                        device_ip = ip_match.group(1)
                        iperf_cmd.extend(["-B", device_ip])
                        self.logger.info(f"Binding iperf to interface IP: {device_ip}")

        # Run the test
        self.logger.debug(f"Running iperf command: {' '.join(iperf_cmd)}")
        iperf_result = self.run_command(iperf_cmd, timeout=self.iperf_duration + 10)

        if iperf_result["success"]:
            try:
                # Parse the JSON output
                import json
                data = json.loads(iperf_result["stdout"])

                # Extract the relevant results
                if 'end' in data:
                    if self.iperf_protocol == 'tcp':
                        # Get TCP stats
                        if 'sum_received' in data['end']:
                            bps = data['end']['sum_received']['bits_per_second']
                            result["bandwidth"] = f"{bps/1000000:.2f}"
                            result["bandwidth_units"] = "Mbps"
                            result["success"] = True
                        elif 'sum' in data['end']:
                            bps = data['end']['sum']['bits_per_second']
                            result["bandwidth"] = f"{bps/1000000:.2f}"
                            result["bandwidth_units"] = "Mbps"
                            result["success"] = True
                    elif self.iperf_protocol == 'udp':
                        # Get UDP stats
                        if 'sum' in data['end']:
                            bps = data['end']['sum']['bits_per_second']
                            result["bandwidth"] = f"{bps/1000000:.2f}"
                            result["bandwidth_units"] = "Mbps"
                            result["jitter_ms"] = data['end']['sum'].get('jitter_ms', 0)
                            result["lost_packets"] = data['end']['sum'].get('lost_packets', 0)
                            result["total_packets"] = data['end']['sum'].get('packets', 0)
                            if result["total_packets"] > 0:
                                result["packet_loss_percent"] = (result["lost_packets"] / result["total_packets"]) * 100
                            else:
                                result["packet_loss_percent"] = 0
                            result["success"] = True

                # Save the raw output for debugging
                result["raw_output"] = iperf_result["stdout"]

            except Exception as e:
                self.logger.error(f"Failed to parse iperf output: {str(e)}")
                result["error"] = f"Failed to parse iperf output: {str(e)}"
                result["raw_output"] = iperf_result["stdout"]
        else:
            result["error"] = iperf_result["stderr"]
            self.logger.error(f"iperf test failed: {iperf_result['stderr']}")

        return result
    
    def disconnect(self) -> bool:
        """Disconnect from the Wi-Fi network and clean up."""
        self.logger.info(f"Disconnecting from {self.ssid}")
        
        # Kill wpa_supplicant
        wpa_kill = self.run_command(["pkill", "-f", f"wpa_supplicant.*{self.device}"])
        
        # Release DHCP lease
        dhcp_release = self.run_command(["dhclient", "-r", self.device])
        
        # Bring down interface
        self.run_command(["ip", "link", "set", self.device, "down"])
        
        # Remove temporary config
        if os.path.exists("wpa_temp.conf"):
            os.remove("wpa_temp.conf")
        
        self.logger.info("Successfully disconnected from Wi-Fi network")
        return True
    
    def run_test(self) -> bool:
        """Run the complete Wi-Fi test."""
        self.logger.info("=== Starting Wi-Fi Connection Test ===")

        # Check if running as root
        if not self.check_root():
            self.logger.error("This script must be run as root (sudo)")
            return False

        try:
            # Check available Wi-Fi interfaces
            available_interfaces = self.check_wifi_interfaces()
            if self.device not in available_interfaces:
                self.logger.warning(f"The specified interface {self.device} was not found in the available interfaces")
                self.logger.info(f"Available interfaces: {', '.join(available_interfaces) if available_interfaces else 'None'}")

                # If available interfaces exist, automatically use the first one in non-interactive mode
                if available_interfaces:
                    self.device = available_interfaces[0]
                    self.logger.info(f"INTERFACE_CHANGE: Automatically selecting interface {self.device}")
                    print(f"NOTICE: Using available wireless interface {self.device} instead of the specified one")
                else:
                    self.logger.error(f"Cannot proceed without a valid wireless interface")
                    print("ERROR_CODE=NO_INTERFACE: No valid wireless interfaces found")
                    return False

            # Check for required tools
            self.logger.info("Checking for required tools...")
            required_tools = ["iw", "wpa_supplicant", "dhclient", "ip"]
            missing_tools = []

            for tool in required_tools:
                which_result = self.run_command(["which", tool])
                if not which_result["success"]:
                    missing_tools.append(tool)
                    self.logger.error(f"Required tool not found: {tool}")

            if missing_tools:
                self.logger.error(f"Missing required tools: {', '.join(missing_tools)}")
                self.logger.error("Please install these tools before continuing")
                return False

            # Set MAC address
            self.logger.info("=== Step 1: Setting MAC Address ===")
            if not self.set_mac_address():
                self.logger.error("Failed to set MAC address, aborting test")
                return False

            # Connect to Wi-Fi
            self.logger.info(f"=== Step 2: Connecting to SSID {self.ssid} ===")

            # Attempt to connect
            connection_result = self.connect_to_wifi()

            if not connection_result:
                # Check logs to determine if it was a password issue for better error reporting
                auth_failure = False

                with open("wifi_test.log", "r") as log_file:
                    log_content = log_file.read()

                    # Check if the log contains authentication failure messages
                    if any(error in log_content for error in [
                        "Authentication failed", "Incorrect password",
                        "4-Way Handshake failed", "WRONG_KEY",
                        "authentication with", "auth", "handshake"
                    ]):
                        auth_failure = True

                if auth_failure:
                    self.logger.error(f"PASSWORD ERROR: Authentication failed for SSID '{self.ssid}' - incorrect password")
                    # Return specific error code that can be checked by automation
                    print(f"ERROR_CODE=AUTH_FAILURE: Incorrect password for network '{self.ssid}'")
                else:
                    self.logger.error(f"CONNECTION ERROR: Failed to connect to Wi-Fi network '{self.ssid}'")
                    print(f"ERROR_CODE=CONN_FAILURE: Connection failed to network '{self.ssid}'")

                return False

            # Ping targets (if any are specified)
            if self.ping_targets:
                self.logger.info(f"=== Step 3: Pinging Targets ===")
                ping_results = self.ping_all_targets()

                # Print ping results
                print("\nPing Results:")
                print("============")
                for result in ping_results:
                    print(f"\nTarget: {result['target']}")
                    print(f"Success: {result['success']}")
                    if result['success']:
                        # Extract and print relevant ping statistics
                        output_lines = result['output'].strip().split('\n')
                        for line in output_lines:
                            if any(x in line for x in ["packets transmitted", "min/avg/max", "packet loss"]):
                                print(line)
                    else:
                        print(f"Error: {result['error']}")
            else:
                self.logger.info("Ping tests skipped (no targets specified)")

            # Run iperf test if server is specified
            if self.iperf_server:
                step_number = 4 if self.ping_targets else 3
                self.logger.info(f"=== Step {step_number}: Running iperf Bandwidth Test ===")

                iperf_result = self.run_iperf_test()

                # Print iperf results
                print("\niperf Bandwidth Test Results:")
                print("===========================")

                if iperf_result["success"]:
                    print(f"Protocol: {self.iperf_protocol.upper()}")
                    print(f"Bandwidth: {iperf_result['bandwidth']} {iperf_result['bandwidth_units']}")

                    if self.iperf_protocol == 'udp':
                        print(f"Jitter: {iperf_result.get('jitter_ms', 'N/A')} ms")
                        print(f"Packet Loss: {iperf_result.get('packet_loss_percent', 'N/A'):.2f}%")
                        print(f"Lost/Total Packets: {iperf_result.get('lost_packets', 'N/A')}/{iperf_result.get('total_packets', 'N/A')}")
                else:
                    print(f"iperf test failed: {iperf_result.get('error', 'Unknown error')}")
            else:
                self.logger.info("iperf test skipped (no server specified)")

            # Disconnect
            step_number = 5 if self.ping_targets and self.iperf_server else 4 if self.ping_targets or self.iperf_server else 3
            self.logger.info(f"=== Step {step_number}: Disconnecting ===")
            disconnect_result = self.disconnect()

            self.logger.info("=== Wi-Fi Connection Test Complete ===")
            return disconnect_result

        except KeyboardInterrupt:
            self.logger.info("Test interrupted by user")
            self.disconnect()
            return False

        except Exception as e:
            self.logger.error(f"Error during test: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.disconnect()
            return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Wi-Fi Connection Test Tool',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--device', required=True,
                        help='Wireless interface device name (e.g., wlp58s0)')
    
    parser.add_argument('--ssid', required=True,
                        help='Wi-Fi network SSID to connect to')
    
    parser.add_argument('--password', required=True,
                        help='Wi-Fi network password')
    
    parser.add_argument('--mac', required=True,
                        help='MAC address to set for the wireless interface (e.g., 00:11:22:33:44:55)')
    
    parser.add_argument('--ping-targets',
                        help='Comma-separated list of IP addresses or hostnames to ping. If not specified, ping tests will be skipped.')

    parser.add_argument('--count', type=int, default=3,
                        help='Number of ping packets to send to each target (default: 3)')

    # iperf-related arguments
    parser.add_argument('--iperf-server',
                        help='IP address or hostname of the iperf server. If not specified, iperf tests will be skipped.')

    parser.add_argument('--iperf-port', type=int, default=5201,
                        help='Port number for iperf connection (default: 5201)')

    parser.add_argument('--iperf-protocol', choices=['tcp', 'udp'], default='tcp',
                        help='Protocol to use for iperf test (tcp or udp, default: tcp)')

    parser.add_argument('--iperf-duration', type=int, default=10,
                        help='Duration of iperf test in seconds (default: 10)')

    parser.add_argument('--iperf-bandwidth', default='100M',
                        help='Target bandwidth for UDP tests (default: 100M)')

    parser.add_argument('--iperf-parallel', type=int, default=1,
                        help='Number of parallel client threads (default: 1)')

    parser.add_argument('--iperf-reverse', action='store_true',
                        help='Run iperf test in reverse direction (upload from server)')

    return parser.parse_args()


def main():
    """Main function to run the Wi-Fi test tool."""
    print("\nWi-Fi Connection Test Tool")
    print("=========================\n")

    try:
        args = parse_arguments()

        # Handle optional ping targets
        ping_targets = []
        if args.ping_targets:
            ping_targets = args.ping_targets.split(',')

        # Create and run the tester
        tester = WiFiTester(
            device=args.device,
            ssid=args.ssid,
            password=args.password,
            mac=args.mac,
            ping_targets=ping_targets,
            ping_count=args.count,
            iperf_server=args.iperf_server,
            iperf_port=args.iperf_port,
            iperf_protocol=args.iperf_protocol,
            iperf_duration=args.iperf_duration,
            iperf_bandwidth=args.iperf_bandwidth,
            iperf_parallel=args.iperf_parallel,
            iperf_reverse=args.iperf_reverse
        )

        print(f"Starting test with the following parameters:")
        print(f"  Device: {args.device}")
        print(f"  SSID: {args.ssid}")
        print(f"  MAC Address: {args.mac}")

        # Only display ping parameters if targets are specified
        if ping_targets:
            print(f"  Ping Targets: {args.ping_targets}")
            print(f"  Ping Count: {args.count}")
        else:
            print(f"  Ping Tests: Disabled (no targets specified)")

        # Only display iperf parameters if server is specified
        if args.iperf_server:
            print(f"\n  iperf Server: {args.iperf_server}:{args.iperf_port}")
            print(f"  iperf Protocol: {args.iperf_protocol.upper()}")
            print(f"  iperf Duration: {args.iperf_duration} seconds")
            if args.iperf_protocol == 'udp':
                print(f"  iperf Bandwidth: {args.iperf_bandwidth}")
            if args.iperf_parallel > 1:
                print(f"  iperf Parallel Streams: {args.iperf_parallel}")
            if args.iperf_reverse:
                print(f"  iperf Direction: Reverse (upload)")
        else:
            print(f"\n  iperf Tests: Disabled (no server specified)")

        print("\nDetailed logs will be written to wifi_test.log\n")

        success = tester.run_test()

        if success:
            print("\nWi-Fi test completed successfully!")
        else:
            print("\nWi-Fi test failed. Check wifi_test.log for details.")

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\nError in main function: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()