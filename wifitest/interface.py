"""
Wi-Fi interface management module.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from .utils.command import run_command

class InterfaceManager:
    """
    Class for managing Wi-Fi interfaces.
    """
    
    def __init__(self, device: str, mac: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the interface manager.
        
        Args:
            device: Wireless interface device name
            mac: MAC address to set
            logger: Logger instance
        """
        self.device = device
        self.mac = mac
        self.logger = logger
    
    def check_root(self) -> bool:
        """Check if the script is running with root privileges."""
        is_root = os.geteuid() == 0
        if not is_root and self.logger:
            self.logger.error("This script must be run as root (sudo)")
        return is_root
    
    def check_wifi_interfaces(self) -> List[str]:
        """
        Check for available wireless interfaces and return a list of them.
        
        Returns:
            List of available wireless interfaces
        """
        if self.logger:
            self.logger.info("Checking for available wireless interfaces...")

        # Try using iw to list interfaces
        iw_result = run_command(["iw", "dev"], logger=self.logger)
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
            ip_result = run_command(["ip", "link", "show"], logger=self.logger)
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

        if self.logger:
            if interfaces:
                self.logger.info(f"Found wireless interfaces: {', '.join(interfaces)}")
            else:
                self.logger.warning("No wireless interfaces found!")

        return interfaces
    
    def set_mac_address(self) -> bool:
        """
        Set the MAC address of the wireless interface.
        
        Returns:
            True if successful, False otherwise
        """
        if self.logger:
            self.logger.info(f"Setting MAC address of {self.device} to {self.mac}")
        
        # First, bring the interface down
        down_result = run_command(["ip", "link", "set", self.device, "down"], logger=self.logger)
        if not down_result["success"]:
            if self.logger:
                self.logger.error(f"Failed to bring down interface {self.device}")
            return False
        
        # Set the MAC address
        mac_result = run_command(["ip", "link", "set", self.device, "address", self.mac], logger=self.logger)
        if not mac_result["success"]:
            if self.logger:
                self.logger.error(f"Failed to set MAC address to {self.mac}")
            # Try to bring the interface back up before returning
            run_command(["ip", "link", "set", self.device, "up"], logger=self.logger)
            return False
        
        # Bring the interface back up
        up_result = run_command(["ip", "link", "set", self.device, "up"], logger=self.logger)
        if not up_result["success"]:
            if self.logger:
                self.logger.error(f"Failed to bring up interface {self.device}")
            return False
        
        if self.logger:
            self.logger.info(f"Successfully set MAC address to {self.mac}")
        return True