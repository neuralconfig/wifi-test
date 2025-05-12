# Wi-Fi Connection Test Tool

A Python script for testing Wi-Fi connections with specific parameters. This tool allows you to:

- Connect to a specified SSID with password
- Set a custom MAC address
- Ping specified targets from the wireless interface (optional)
- Run iperf bandwidth tests (optional)
- Disconnect when done

## Features

- Automatic detection of available wireless interfaces
- Detailed debug logging for troubleshooting
- Enhanced error handling and recovery
- Support for hidden networks
- Signal strength reporting
- Verification of successful connection
- Incorrect password detection with automatic error codes
- Authentication failure diagnosis for automation tools
- Network bandwidth testing with iperf3
- Configurable TCP/UDP performance testing

## Requirements

- Python 3.6+
- Linux operating system
- Root privileges (sudo)
- Required packages: `iw`, `wpa_supplicant`, `dhclient`, `ip`
- Optional packages: `iperf3` (for bandwidth testing)

## Installation

Clone the repository:

```bash
git clone https://github.com/neuralconfig/wifi-test.git
cd wifi-test
chmod +x wifi-test.py
```

## Usage

The script must be run with root privileges:

```bash
sudo ./wifi-test.py --device DEVICE --ssid SSID --password PASSWORD --mac MAC_ADDRESS [OPTIONS]
```

### Required Arguments

- `--device`: Wireless interface device name (e.g., wlp58s0)
- `--ssid`: Wi-Fi network SSID to connect to
- `--password`: Wi-Fi network password
- `--mac`: MAC address to set for the wireless interface (e.g., 00:11:22:33:44:55)

### Ping Test Options (Optional)

- `--ping-targets`: Comma-separated list of IP addresses or hostnames to ping. If not specified, ping tests will be skipped.
- `--count`: Number of ping packets to send to each target (default: 3)

### iperf Bandwidth Test Options (Optional)

- `--iperf-server`: IP address or hostname of the iperf server. If not specified, iperf tests will be skipped.
- `--iperf-port`: Port number for iperf connection (default: 5201)
- `--iperf-protocol`: Protocol to use for iperf test (tcp or udp, default: tcp)
- `--iperf-duration`: Duration of iperf test in seconds (default: 10)
- `--iperf-bandwidth`: Target bandwidth for UDP tests (default: 100M)
- `--iperf-parallel`: Number of parallel client threads (default: 1)
- `--iperf-reverse`: If specified, run iperf test in reverse direction (upload from server)

### Examples

Basic connection test (no ping or iperf):
```bash
sudo ./wifi-test.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55
```

Connection test with ping:
```bash
sudo ./wifi-test.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55 --ping-targets 192.168.37.1,192.168.37.252 --count 3
```

Connection test with iperf TCP test:
```bash
sudo ./wifi-test.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55 --iperf-server 192.168.37.1 --iperf-duration 30
```

Connection test with iperf UDP test:
```bash
sudo ./wifi-test.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55 --iperf-server 192.168.37.1 --iperf-protocol udp --iperf-bandwidth 50M
```

Comprehensive test with ping and iperf:
```bash
sudo ./wifi-test.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55 --ping-targets 192.168.37.1,192.168.37.252 --iperf-server 192.168.37.1 --iperf-protocol tcp --iperf-duration 20 --iperf-parallel 4
```

## Logging and Debugging

The script provides detailed logging to help troubleshoot connection issues:

- All logs are written to `wifi_test.log` in the current directory
- Console output includes the most important status messages
- Debug level logging captures all commands, outputs, and connection details
- Signal strength and network details are logged when available

If you're having trouble with connections, check the log file for detailed information about what's happening during each step of the connection process.


## How It Works

1. Verifies root privileges and required tools
2. Detects available wireless interfaces
3. Sets the MAC address of the specified wireless interface
4. Connects to the specified Wi-Fi network using wpa_supplicant
   - Generates a configuration with scanning for hidden networks enabled
   - Uses debug mode for more verbose output
   - Attempts multiple connection strategies if needed
   - Detects authentication failures and incorrect passwords
   - Reports authentication failures with error codes for automation
5. Obtains an IP address via DHCP
6. Verifies connection status and reports signal strength
7. Optional: Pings each target in the list using the wireless interface
8. Optional: Runs bandwidth tests using iperf3
   - Binds to the Wi-Fi interface's IP to ensure tests use the wireless connection
   - Supports both TCP and UDP tests with customizable parameters
   - Reports detailed bandwidth, jitter, and packet loss statistics
9. Disconnects from the network and cleans up

## Troubleshooting

If the connection fails:

1. Check `wifi_test.log` for detailed error messages
2. Verify that the wireless interface exists and is working
3. Ensure you have the correct SSID and password
   - The tool will detect incorrect passwords and return an appropriate error code
   - Authentication failures are detected early and reported with specific error messages
4. Confirm that the MAC address is in the correct format
5. Make sure all required tools are installed

### Password Authentication Issues

The tool specifically checks for authentication failures that indicate incorrect passwords:

- If an authentication failure is detected, the script will exit with an error code
- Error codes are prefixed with "ERROR_CODE=" for easy parsing by automation tools
- The tool searches system logs and wpa_supplicant output to diagnose authentication failures
- Authentication failures are detected before attempting DHCP to avoid timeouts

### Error Codes

The script produces specific error codes for automation systems:

- `ERROR_CODE=AUTH_FAILURE`: Incorrect password for the Wi-Fi network
- `ERROR_CODE=CONN_FAILURE`: General connection failure (not related to password)
- `ERROR_CODE=NO_INTERFACE`: No valid wireless interface found

## License

MIT License - See LICENSE file for details