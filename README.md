# Wi-Fi Connection Test Tool

A Python script for testing Wi-Fi connections with specific parameters. This tool allows you to:

- Connect to a specified SSID with password
- Set a custom MAC address
- Ping specified targets from the wireless interface
- Disconnect when done

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

## Demo Mode

For testing without root privileges or actual hardware, use the `test_demo.py` script:

```bash
./test_demo.py --device wlp58s0 --ssid wifitest --password 12345678 --mac 00:11:22:33:44:55 --ping-targets 192.168.37.1,192.168.37.252 --count 3
```

## How It Works

1. Sets the MAC address of the specified wireless interface
2. Connects to the specified Wi-Fi network using wpa_supplicant
3. Obtains an IP address via DHCP
4. Pings each target in the list using the wireless interface
5. Disconnects from the network and cleans up

## License

MIT License - See LICENSE file for details