# Frigate Device Merger

A Home Assistant custom component that automatically adds MAC addresses to Frigate camera devices, enabling device merging with other camera integrations (Hikvision, Unifi Protect, Reolink, etc.).

## What it does

Home Assistant merges devices when they share the same MAC address. Frigate cameras don't include MAC addresses in their device info, so they appear as separate devices even when they're the same physical camera configured in other integrations.

This component:

1. Scans your device registry for cameras from other integrations (Hikvision, Unifi, Reolink, etc.)
2. Extracts MAC addresses and IP addresses from those devices
3. Matches Frigate cameras by IP address (based on your frigate.yml config)
4. Adds MAC addresses to Frigate camera devices
5. Home Assistant automatically merges the devices!

## Installation

### Option 1: HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed
2. Go to HACS > Integrations
3. Click the three dots (⋮) in the top right
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/JoeyGE0/frigate_device_merger`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Frigate Device Merger" and install it
9. Restart Home Assistant
10. Go to **Settings** > **Devices & Services** > **Add Integration**
11. Search for "Frigate Device Merger" and add it

### Option 2: Manual Installation

1. Download the latest release or clone this repository
2. Copy the `frigate_device_merger` folder to your Home Assistant `custom_components` directory:

   ```
   config/custom_components/frigate_device_merger/
   ```

3. Restart Home Assistant

4. Go to **Settings** > **Devices & Services** > **Add Integration**

5. Search for "Frigate Device Merger" and add it

## Configuration

**No configuration needed!** The component is fully automatic:

1. **Auto-detects Frigate cameras** - Scans your Frigate camera entities and extracts IP addresses from their RTSP stream URLs
2. **Auto-detects other integrations** - Finds MAC addresses and IPs from Hikvision, Unifi, Reolink, etc.
3. **Auto-matches by IP** - When a Frigate camera and another integration share the same IP address, it adds the MAC address to the Frigate device
4. **Auto-merges devices** - Home Assistant automatically merges devices with matching MAC addresses

The component intelligently extracts IP addresses from:

- Frigate camera stream URLs (RTSP streams)
- Device names (if they contain IPs)
- Config entry data from other integrations

## Usage

The component runs automatically:

- On startup (after a short delay to let other integrations initialize)
- When you add the integration

You can also manually trigger an update by calling the service:

```yaml
service: frigate_device_merger.update_devices
```

## How it works

1. **Scans Frigate cameras**: Extracts IP addresses from Frigate camera entities by parsing RTSP stream URLs (e.g., `rtsp://user:pass@192.168.1.11/stream`)
2. **Scans other integrations**: For non-Frigate devices (Hikvision, Unifi, etc.), it extracts:
   - MAC address from device connections/identifiers
   - IP address from config entry data, device name, or stream URLs
3. **Matches by IP**: When a Frigate camera and another integration share the same IP address, it automatically links them
4. **Adds MAC addresses**: Adds the MAC address to the Frigate device's identifiers and connections
5. **Auto-merges**: Home Assistant's device registry automatically merges devices with matching MAC addresses

No manual configuration or mapping needed - it figures everything out automatically!

## Troubleshooting

**Devices aren't merging:**

- Make sure your other camera integrations (Hikvision, Unifi, etc.) are set up first
- Check that those integrations include MAC addresses in their device info
- Verify the camera IP addresses match between Frigate config and other integrations
- Check the Home Assistant logs for warnings about missing MAC addresses

**Can't find MAC address for a camera:**

- The component logs a warning if it can't find a MAC for a Frigate camera
- Make sure the camera is configured in another integration that exposes MAC addresses
- Verify the IP address matches between Frigate and the other integration

## Requirements

- Home Assistant 2024.1.0 or later
- Frigate integration installed
- At least one other camera integration (Hikvision, Unifi Protect, Reolink, etc.) that exposes MAC addresses

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.
