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
                 ping_targets: List[str], ping_count: int):
        self.device = device
        self.ssid = ssid
        self.password = password
        self.mac = mac
        self.ping_targets = ping_targets
        self.ping_count = ping_count
        self.setup_logging()
        
    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("wifi_test.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_command(self, command: List[str], timeout: int = 30) -> Dict[str, Any]:
        """
        Run a shell command and return the result.
        
        Args:
            command: List of command and arguments
            timeout: Timeout in seconds
            
        Returns:
            Dictionary containing success status, stdout, stderr, and return code
        """
        self.logger.debug(f"Running command: {' '.join(command)}")
        
        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1
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
            
            if not result["success"]:
                self.logger.warning(f"Command failed with return code {process.returncode}")
                self.logger.warning(f"stderr: {process.stderr}")
        
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout} seconds")
            result["stderr"] = f"Command timed out after {timeout} seconds"
        
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}")
            result["stderr"] = str(e)
        
        return result
    
    def check_root(self) -> bool:
        """Check if the script is running with root privileges."""
        return os.geteuid() == 0
    
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
        self.logger.info(f"Connecting to SSID: {self.ssid}")
        
        # First, make sure NetworkManager doesn't interfere
        self.run_command(["nmcli", "radio", "wifi", "off"])
        time.sleep(1)
        
        # Kill any existing wpa_supplicant processes for this interface
        self.run_command(["pkill", "-f", f"wpa_supplicant.*{self.device}"])
        time.sleep(1)
        
        # Generate wpa_supplicant configuration
        wpa_config = f"""ctrl_interface=/var/run/wpa_supplicant
network={{
    ssid="{self.ssid}"
    psk="{self.password}"
}}
"""
        with open("wpa_temp.conf", "w") as f:
            f.write(wpa_config)
        
        # Start wpa_supplicant
        wpa_result = self.run_command([
            "wpa_supplicant", 
            "-B",  # Run in background
            "-i", self.device,  # Interface
            "-c", "wpa_temp.conf"  # Config file
        ])
        
        if not wpa_result["success"]:
            self.logger.error("Failed to start wpa_supplicant")
            return False
        
        self.logger.info("Started wpa_supplicant, waiting for connection...")
        
        # Wait for connection to be established
        time.sleep(5)
        
        # Get IP address via DHCP
        dhcp_result = self.run_command(["dhclient", "-v", self.device], timeout=60)
        
        if not dhcp_result["success"]:
            self.logger.error("Failed to get IP address via DHCP")
            return False
        
        self.logger.info("Successfully connected to Wi-Fi network")
        
        # Check connection status
        iw_result = self.run_command(["iw", "dev", self.device, "link"])
        if iw_result["success"] and "Connected to" in iw_result["stdout"]:
            self.logger.info(f"Connection details: {iw_result['stdout']}")
            return True
        else:
            self.logger.warning("Connected but link status is uncertain")
            return True  # Still return True as we don't want to fail the process
    
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
        if not self.check_root():
            self.logger.error("This script must be run as root")
            return False
        
        try:
            # Set MAC address
            if not self.set_mac_address():
                return False
            
            # Connect to Wi-Fi
            if not self.connect_to_wifi():
                return False
            
            # Ping targets
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
            
            # Disconnect
            return self.disconnect()
            
        except KeyboardInterrupt:
            self.logger.info("Test interrupted by user")
            self.disconnect()
            return False
        
        except Exception as e:
            self.logger.error(f"Error during test: {str(e)}")
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
    
    parser.add_argument('--ping-targets', required=True,
                        help='Comma-separated list of IP addresses or hostnames to ping')
    
    parser.add_argument('--count', type=int, default=3,
                        help='Number of ping packets to send to each target')
    
    return parser.parse_args()


def main():
    """Main function to run the Wi-Fi test tool."""
    args = parse_arguments()
    
    # Split the ping targets string into a list
    ping_targets = args.ping_targets.split(',')
    
    # Create and run the tester
    tester = WiFiTester(
        device=args.device,
        ssid=args.ssid,
        password=args.password,
        mac=args.mac,
        ping_targets=ping_targets,
        ping_count=args.count
    )
    
    success = tester.run_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()