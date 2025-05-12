#!/usr/bin/env python3
"""
Wi-Fi Connection Test Tool CLI

A command-line interface for the Wi-Fi test tool.
"""

import sys
import argparse
from wifitest import WiFiTester

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
                        
    parser.add_argument('--log-file', default='wifi_test.log',
                        help='Path to the log file (default: wifi_test.log)')

    parser.add_argument('--vrf', action='store_true',
                        help='Enable VRF-like routing for the wireless interface to ensure traffic goes through it')

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
            iperf_reverse=args.iperf_reverse,
            log_file=args.log_file,
            vrf=args.vrf
        )

        print(f"Starting test with the following parameters:")
        print(f"  Device: {args.device}")
        print(f"  SSID: {args.ssid}")
        print(f"  MAC Address: {args.mac}")
        print(f"  VRF Routing: {'Enabled' if args.vrf else 'Disabled'}")

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

        print(f"\nDetailed logs will be written to {args.log_file}\n")

        success = tester.run_test()

        if success:
            print("\nWi-Fi test completed successfully!")
        else:
            print("\nWi-Fi test failed. Check log file for details.")

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\nError in main function: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()