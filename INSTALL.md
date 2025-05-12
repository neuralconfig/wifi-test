# Installation Requirements

## Required Packages

To run the Wi-Fi test tool, you need the following packages installed:

```bash
sudo apt-get install iw wireless-tools iproute2 dhcpcd5 wpasupplicant
```

### Package Descriptions:

1. **iw**: Core tool for configuring Linux wireless devices and creating virtual interfaces
2. **wireless-tools**: Legacy tools for manipulating wireless extensions
3. **iproute2**: Suite of utilities for network interface management (includes the 'ip' command)
4. **dhcpcd5**: DHCP client for obtaining IP addresses
5. **wpasupplicant**: Required for connecting to WPA/WPA2 networks

## Verifying Installation

After installing the packages, verify that the essential commands are available:

```bash
which iw ip dhclient wpa_supplicant
```

## Driver Requirements

The Wi-Fi test functionality requires:

1. A Wi-Fi card with Linux driver support
2. Proper firmware for your wireless card

Most modern Linux distributions include drivers for common Wi-Fi cards, but some may require installation of additional firmware packages.

## Checking Driver Status

Run the following command to see if your wireless card is properly recognized:

```bash
iw dev
```

This should show your wireless interface. If it doesn't appear, you may need to install additional drivers.

## Additional Notes

- Some wireless cards have restrictions on changing MAC addresses
- Check your distribution's documentation for specific wireless driver packages if needed