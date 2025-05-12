"""
Wi-Fi Connection Test Tool

A Python package to test Wi-Fi connections with specific parameters:
- Connect to a specified SSID with password
- Set custom MAC address
- Ping specified targets from the wireless interface
- Run iperf bandwidth tests
- Disconnect when done
"""

from .wifi_tester import WiFiTester

__version__ = "1.0.0"