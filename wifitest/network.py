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
    
    def __init__(self, device: str, ssid: str, password: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the network manager.
        
        Args:
            device: Wireless interface device name
            ssid: Wi-Fi network SSID
            password: Wi-Fi network password
            logger: Logger instance
        """
        self.device = device
        self.ssid = ssid
        self.password = password
        self.logger = logger
        self.wpa_conf_path = os.path.abspath("./wpa_temp.conf")
    
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
                # If we see successful connection and authentication, return true to proceed with DHCP
                return True

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

            return True
        else:
            if self.logger:
                self.logger.warning("Connection status uncertain - unable to confirm association with AP")

            # Check if we have an IP address anyway
            if "inet " in ip_addr["stdout"]:
                if self.logger:
                    self.logger.info("IP address obtained, assuming connection is functional")
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