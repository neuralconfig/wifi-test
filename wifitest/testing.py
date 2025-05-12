"""
Testing module for Wi-Fi network.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional
from .utils.command import run_command

class NetworkTester:
    """
    Class for testing Wi-Fi network connectivity.
    """
    
    def __init__(self, device: str, 
                 ping_targets: List[str], ping_count: int,
                 iperf_server: Optional[str] = None, iperf_port: int = 5201,
                 iperf_protocol: str = 'tcp', iperf_duration: int = 10,
                 iperf_bandwidth: str = '100M', iperf_parallel: int = 1,
                 iperf_reverse: bool = False,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the network tester.
        
        Args:
            device: Wireless interface device name
            ping_targets: List of IP addresses or hostnames to ping
            ping_count: Number of ping packets to send
            iperf_server: IP address or hostname of the iperf server
            iperf_port: Port number for iperf connection
            iperf_protocol: Protocol to use for iperf test (tcp or udp)
            iperf_duration: Duration of iperf test in seconds
            iperf_bandwidth: Target bandwidth for UDP tests
            iperf_parallel: Number of parallel client threads
            iperf_reverse: Run iperf test in reverse direction
            logger: Logger instance
        """
        self.device = device
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
        
        self.logger = logger
    
    def ping_from_interface(self, target: str) -> Dict[str, Any]:
        """
        Ping a target from the specified wireless interface.
        
        Args:
            target: IP address or hostname to ping
            
        Returns:
            Dictionary with ping results
        """
        if self.logger:
            self.logger.info(f"Pinging {target} from interface {self.device} ({self.ping_count} times)")
        
        ping_result = run_command([
            "ping", 
            "-c", str(self.ping_count),  # Count
            "-I", self.device,  # Interface
            target
        ], logger=self.logger)
        
        return {
            "target": target,
            "success": ping_result["success"],
            "output": ping_result["stdout"],
            "error": ping_result["stderr"]
        }
    
    def ping_all_targets(self) -> List[Dict[str, Any]]:
        """
        Ping all specified targets and return results.
        
        Returns:
            List of dictionaries containing ping results
        """
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
        if not self.iperf_server:
            if self.logger:
                self.logger.warning("No iperf server specified, skipping test")
            return {
                "success": False,
                "error": "No iperf server specified"
            }
            
        if self.logger:
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
        ip_result = run_command(["ip", "-j", "addr", "show", "dev", self.device], logger=self.logger)

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
                ip_data = json.loads(ip_result["stdout"])

                # Find IPv4 address
                for addr_info in ip_data[0].get("addr_info", []):
                    if addr_info.get("family") == "inet":  # IPv4
                        device_ip = addr_info.get("local")
                        if device_ip:
                            iperf_cmd.extend(["-B", device_ip])
                            if self.logger:
                                self.logger.info(f"Binding iperf to interface IP: {device_ip}")
                            break
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                if self.logger:
                    self.logger.warning(f"Failed to parse IP address from JSON: {str(e)}")
                # Fallback to text parsing if JSON fails
                ip_text = run_command(["ip", "addr", "show", "dev", self.device], logger=self.logger)
                if ip_text["success"]:
                    ip_match = re.search(r'inet\s+([0-9.]+)', ip_text["stdout"])
                    if ip_match:
                        device_ip = ip_match.group(1)
                        iperf_cmd.extend(["-B", device_ip])
                        if self.logger:
                            self.logger.info(f"Binding iperf to interface IP: {device_ip}")

        # Run the test
        if self.logger:
            self.logger.debug(f"Running iperf command: {' '.join(iperf_cmd)}")
        iperf_result = run_command(iperf_cmd, timeout=self.iperf_duration + 10, logger=self.logger)

        if iperf_result["success"]:
            try:
                # Parse the JSON output
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
                if self.logger:
                    self.logger.error(f"Failed to parse iperf output: {str(e)}")
                result["error"] = f"Failed to parse iperf output: {str(e)}"
                result["raw_output"] = iperf_result["stdout"]
        else:
            result["error"] = iperf_result["stderr"]
            if self.logger:
                self.logger.error(f"iperf test failed: {iperf_result['stderr']}")

        return result