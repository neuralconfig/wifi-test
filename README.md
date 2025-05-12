# Wi-Fi Connection Test Tool

A Python script for testing Wi-Fi connections with specific parameters. This tool allows you to:

- Connect to a specified SSID with password
- Set a custom MAC address
- Ping specified targets from the wireless interface
- Disconnect when done

## Features

- Automatic detection of available wireless interfaces
- Detailed debug logging for troubleshooting
- Enhanced error handling and recovery
- Support for hidden networks
- Signal strength reporting
- Verification of successful connection

## Requirements

- Python 3.6+
- Linux operating system
- Root privileges (sudo)
- Required packages: `iw`, `wpa_supplicant`, `dhclient`, `ip`

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
sudo ./wifi-test.py --device DEVICE --ssid SSID --password PASSWORD --mac MAC_ADDRESS --ping-targets TARGETS [--count COUNT]
```

### Arguments

- `--device`: Wireless interface device name (e.g., wlp58s0)
- `--ssid`: Wi-Fi network SSID to connect to
- `--password`: Wi-Fi network password
- `--mac`: MAC address to set for the wireless interface (e.g., 00:11:22:33:44:55)
- `--ping-targets`: Comma-separated list of IP addresses or hostnames to ping
- `--count`: Number of ping packets to send to each target (default: 3)

### Example

```bash
sudo ./wifi-test.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55 --ping-targets 192.168.37.1,192.168.37.252 --count 3
```

## Logging and Debugging

The script provides detailed logging to help troubleshoot connection issues:

- All logs are written to `wifi_test.log` in the current directory
- Console output includes the most important status messages
- Debug level logging captures all commands, outputs, and connection details
- Signal strength and network details are logged when available

If you're having trouble with connections, check the log file for detailed information about what's happening during each step of the connection process.

## Demo Mode

For testing without root privileges or actual hardware, use the `test_demo.py` script:

```bash
./test_demo.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55 --ping-targets 192.168.37.1,192.168.37.252 --count 3
```

## How It Works

1. Verifies root privileges and required tools
2. Detects available wireless interfaces
3. Sets the MAC address of the specified wireless interface
4. Connects to the specified Wi-Fi network using wpa_supplicant
   - Generates a configuration with scanning for hidden networks enabled
   - Uses debug mode for more verbose output
   - Attempts multiple connection strategies if needed
5. Obtains an IP address via DHCP
6. Verifies connection status and reports signal strength
7. Pings each target in the list using the wireless interface
8. Disconnects from the network and cleans up

## Troubleshooting

If the connection fails:

1. Check `wifi_test.log` for detailed error messages
2. Verify that the wireless interface exists and is working
3. Ensure you have the correct SSID and password
4. Confirm that the MAC address is in the correct format
5. Make sure all required tools are installed

## License

MIT License - See LICENSE file for details