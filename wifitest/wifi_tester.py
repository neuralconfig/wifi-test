"""
Main Wi-Fi tester class.
"""

import os
import logging
import traceback
from typing import List, Dict, Any, Optional

from .utils.logging_setup import setup_logging
from .utils.command import run_command
from .interface import InterfaceManager
from .network import NetworkManager
from .testing import NetworkTester

class WiFiTester:
    """Class for testing Wi-Fi connections with specific parameters."""

    def __init__(self, device: str, ssid: str, password: str, mac: str,
                 ping_targets: List[str], ping_count: int,
                 iperf_server: Optional[str] = None, iperf_port: int = 5201,
                 iperf_protocol: str = 'tcp', iperf_duration: int = 10,
                 iperf_bandwidth: str = '100M', iperf_parallel: int = 1,
                 iperf_reverse: bool = False,
                 log_file: str = "wifi_test.log",
                 vrf: bool = False):
        """
        Initialize the Wi-Fi tester.
        
        Args:
            device: Wireless interface device name
            ssid: Wi-Fi network SSID
            password: Wi-Fi network password
            mac: MAC address to set for the wireless interface
            ping_targets: List of IP addresses or hostnames to ping
            ping_count: Number of ping packets to send
            iperf_server: IP address or hostname of the iperf server
            iperf_port: Port number for iperf connection
            iperf_protocol: Protocol to use for iperf test (tcp or udp)
            iperf_duration: Duration of iperf test in seconds
            iperf_bandwidth: Target bandwidth for UDP tests
            iperf_parallel: Number of parallel client threads
            iperf_reverse: Run iperf test in reverse direction
            log_file: Path to the log file
            vrf: Enable VRF-like routing for the wireless interface
        """
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

        # VRF routing feature
        self.vrf = vrf
        
        # Setup logging
        self.logger = setup_logging(log_file)
        
        # Initialize managers
        self.interface_manager = InterfaceManager(device, mac, self.logger)
        self.network_manager = NetworkManager(device, ssid, password, self.logger, vrf=self.vrf)
        self.network_tester = NetworkTester(
            device, ping_targets, ping_count,
            iperf_server, iperf_port, iperf_protocol,
            iperf_duration, iperf_bandwidth, iperf_parallel,
            iperf_reverse, self.logger
        )

    def run_test(self) -> bool:
        """
        Run the complete Wi-Fi test.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("=== Starting Wi-Fi Connection Test ===")

        # Check if running as root
        if not self.interface_manager.check_root():
            self.logger.error("This script must be run as root (sudo)")
            return False

        try:
            # Check available Wi-Fi interfaces
            available_interfaces = self.interface_manager.check_wifi_interfaces()
            if self.device not in available_interfaces:
                self.logger.warning(f"The specified interface {self.device} was not found in the available interfaces")
                self.logger.info(f"Available interfaces: {', '.join(available_interfaces) if available_interfaces else 'None'}")

                # If available interfaces exist, automatically use the first one in non-interactive mode
                if available_interfaces:
                    self.device = available_interfaces[0]
                    self.interface_manager.device = self.device
                    self.network_manager.device = self.device
                    self.network_tester.device = self.device
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
                which_result = run_command(["which", tool], logger=self.logger)
                if not which_result["success"]:
                    missing_tools.append(tool)
                    self.logger.error(f"Required tool not found: {tool}")

            if missing_tools:
                self.logger.error(f"Missing required tools: {', '.join(missing_tools)}")
                self.logger.error("Please install these tools before continuing")
                return False

            # Set MAC address
            self.logger.info("=== Step 1: Setting MAC Address ===")
            if not self.interface_manager.set_mac_address():
                self.logger.error("Failed to set MAC address, aborting test")
                return False

            # Connect to Wi-Fi
            self.logger.info(f"=== Step 2: Connecting to SSID {self.ssid} ===")

            # Attempt to connect
            connection_result = self.network_manager.connect_to_wifi()

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
                ping_results = self.network_tester.ping_all_targets()

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

                iperf_result = self.network_tester.run_iperf_test()

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
            disconnect_result = self.network_manager.disconnect()

            self.logger.info("=== Wi-Fi Connection Test Complete ===")
            return disconnect_result

        except KeyboardInterrupt:
            self.logger.info("Test interrupted by user")
            self.network_manager.disconnect()
            return False

        except Exception as e:
            self.logger.error(f"Error during test: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.network_manager.disconnect()
            return False