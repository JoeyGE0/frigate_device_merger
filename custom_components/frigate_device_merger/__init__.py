"""Frigate Device Merger - Adds MAC addresses to Frigate cameras for device merging."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

_LOGGER = logging.getLogger(__name__)

DOMAIN = "frigate_device_merger"


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Frigate Device Merger component."""
    _LOGGER.info("Frigate Device Merger: async_setup called")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Frigate Device Merger from a config entry."""
    import asyncio
    
    _LOGGER.error("=== Frigate Device Merger: Integration loaded ===")
    _LOGGER.error("Entry ID: %s, Entry data: %s", entry.entry_id, entry.data)
    
    # Register service in async_setup_entry (not async_setup) to avoid services.yaml requirement
    async def update_devices_service(call: ServiceCall) -> None:
        """Service to manually trigger Frigate device update."""
        _LOGGER.error("Manual update triggered via service call")
        try:
            await async_update_frigate_devices(hass)
        except Exception as e:
            _LOGGER.error("Error in manual update: %s", e, exc_info=True)
    
    hass.services.async_register(
        DOMAIN,
        "update_devices",
        update_devices_service,
    )
    _LOGGER.error("Service registered: %s.update_devices", DOMAIN)
    
    async def run_update():
        """Run the update with error handling."""
        try:
            _LOGGER.error("Running Frigate device merger update...")
            await async_update_frigate_devices(hass)
        except Exception as e:
            _LOGGER.error("Error in Frigate device merger update: %s", e, exc_info=True)
    
    async def delayed_update(event: Event = None):
        """Wait for Home Assistant to fully start and other integrations to initialize."""
        _LOGGER.error("Waiting 15 seconds for other integrations to initialize...")
        await asyncio.sleep(15)
        _LOGGER.error("15 seconds elapsed, running update now...")
        await run_update()
    
    # Listen for Home Assistant start event, then wait additional time
    async def on_started(event: Event):
        _LOGGER.error("Home Assistant started event received, scheduling update")
        hass.async_create_task(delayed_update(event))
    
    # Always listen for the start event
    _LOGGER.error("Registering event listener for HOMEASSISTANT_STARTED")
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, on_started)
    
    # If already started, run immediately with delay
    if hass.is_running:
        _LOGGER.error("Home Assistant already running, scheduling immediate update")
        hass.async_create_task(delayed_update())
    else:
        _LOGGER.error("Home Assistant not running yet, waiting for start event")
    
    return True


async def async_update_frigate_devices(hass: HomeAssistant) -> None:
    """Update Frigate camera devices with MAC addresses from other integrations."""
    import re
    
    _LOGGER.info("=== Starting Frigate Device Merger scan ===")
    device_registry = dr.async_get(hass)
    
    # Build a map of IP addresses to MAC addresses from other integrations
    ip_to_mac: dict[str, str] = {}
    
    # Scan all devices to find MAC addresses and their associated IPs
    for device_entry in device_registry.devices.values():
        # Skip Frigate devices - we want to get MACs from other integrations
        is_frigate = False
        for identifier_domain, _ in device_entry.identifiers:
            if identifier_domain == "frigate":
                is_frigate = True
                break
        if is_frigate:
            continue
        
        # Get MAC address from connections
        mac_address = None
        for connection_type, connection_id in device_entry.connections:
            if connection_type == dr.CONNECTION_NETWORK_MAC:
                mac_address = connection_id.lower()
                break
        
        # Also check identifiers for MAC
        if not mac_address:
            for identifier_domain, identifier_id in device_entry.identifiers:
                if identifier_domain == "mac":
                    mac_address = identifier_id.lower()
                    break
        
        if not mac_address:
            continue
        
        # Try to get IP address from config entry data
        # Only trust IPs from camera integrations, and only if they make sense
        ip_address = None
        for config_entry_id in device_entry.config_entries:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if config_entry and config_entry.domain in ("hikvision_isapi", "unifiprotect", "reolink"):
                # Only get IP from camera integrations
                if "host" in config_entry.data:
                    host = config_entry.data["host"]
                    # Extract IP from host (might be hostname or IP)
                    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', host)
                    if ip_match:
                        ip_address = ip_match.group()
                        # Validate it's a private IP (cameras are usually on local network)
                        if ip_address.startswith(("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
                            break
                        else:
                            ip_address = None  # Not a private IP, probably wrong
                elif "ip_address" in config_entry.data:
                    ip_address = config_entry.data["ip_address"]
                    if ip_address.startswith(("192.168.", "10.", "172.16.")):
                        break
                    else:
                        ip_address = None
        
        # Fallback: try to extract IP from device name (but be careful - device names might have wrong IPs)
        if not ip_address:
            device_name = device_entry.name or ""
            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', device_name)
            if ip_match:
                potential_ip = ip_match.group()
                # Only trust private IPs from device names
                if potential_ip.startswith(("192.168.", "10.", "172.16.")):
                    ip_address = potential_ip
        
        if ip_address and mac_address:
            # Only add if we haven't seen this IP before, or log a warning if there's a conflict
            if ip_address in ip_to_mac and ip_to_mac[ip_address] != mac_address:
                _LOGGER.warning(
                    "IP %s already mapped to MAC %s, but device '%s' has MAC %s. "
                    "Skipping this mapping to avoid conflicts.",
                    ip_address, ip_to_mac[ip_address], device_entry.name, mac_address
                )
            else:
                ip_to_mac[ip_address] = mac_address
                _LOGGER.info("Found MAC %s for IP %s from device: %s (%s)", 
                           mac_address, ip_address, device_entry.name, config_entry.domain if config_entry else "unknown")
    
    _LOGGER.info("Found %d IP-to-MAC mappings from other integrations", len(ip_to_mac))
    
    # Get Frigate camera IPs from Frigate API/config
    # This is the correct source - Frigate knows the real camera IPs
    frigate_camera_to_ip: dict[str, str] = {}
    
    # Try to get Frigate config from API
    frigate_config_entry = None
    for config_entry in hass.config_entries.async_entries("frigate"):
        frigate_config_entry = config_entry
        break
    
    if frigate_config_entry:
        try:
            # Get Frigate URL from config
            frigate_url = frigate_config_entry.data.get("url") or frigate_config_entry.data.get("host", "http://ccab4aaf-frigate:5000")
            if not frigate_url.startswith("http"):
                frigate_url = f"http://{frigate_url}"
            
            # Call Frigate API to get config
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{frigate_url}/api/config", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            config_data = await response.json()
                            
                            # Extract camera IPs from go2rtc streams (most reliable)
                            if "go2rtc" in config_data and "streams" in config_data["go2rtc"]:
                                for camera_name, stream_configs in config_data["go2rtc"]["streams"].items():
                                    if isinstance(stream_configs, list):
                                        for stream_config in stream_configs:
                                            if isinstance(stream_config, str) and stream_config.startswith("rtsp://"):
                                                # Extract IP from RTSP URL: rtsp://user:pass@IP:port/path
                                                ip_match = re.search(r'@([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', stream_config)
                                                if ip_match:
                                                    frigate_camera_to_ip[camera_name.lower()] = ip_match.group(1)
                                                    _LOGGER.info("Got IP %s for Frigate camera '%s' from go2rtc config", ip_match.group(1), camera_name)
                                                    break
                            
                            # Also check cameras section for IPs in ffmpeg inputs
                            if "cameras" in config_data:
                                for camera_name, camera_config in config_data["cameras"].items():
                                    if camera_name.lower() not in frigate_camera_to_ip:
                                        if "ffmpeg" in camera_config and "inputs" in camera_config["ffmpeg"]:
                                            for input_config in camera_config["ffmpeg"]["inputs"]:
                                                if isinstance(input_config, dict) and "path" in input_config:
                                                    path = input_config["path"]
                                                    if path.startswith("rtsp://"):
                                                        ip_match = re.search(r'@([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', path)
                                                        if ip_match:
                                                            frigate_camera_to_ip[camera_name.lower()] = ip_match.group(1)
                                                            _LOGGER.info("Got IP %s for Frigate camera '%s' from ffmpeg config", ip_match.group(1), camera_name)
                                                            break
                                                elif isinstance(input_config, str) and input_config.startswith("rtsp://"):
                                                    ip_match = re.search(r'@([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', input_config)
                                                    if ip_match:
                                                        frigate_camera_to_ip[camera_name.lower()] = ip_match.group(1)
                                                        _LOGGER.info("Got IP %s for Frigate camera '%s' from ffmpeg input", ip_match.group(1), camera_name)
                                                        break
                            
                            _LOGGER.info("Got %d camera IPs from Frigate API", len(frigate_camera_to_ip))
                except Exception as e:
                    _LOGGER.warning("Failed to get Frigate config from API: %s", e)
        except Exception as e:
            _LOGGER.warning("Failed to access Frigate API: %s", e)
    
    # Fallback: Build a map of camera names to IPs from other integrations' config entries
    # Only use this if we couldn't get IPs from Frigate API
    camera_name_to_ip: dict[str, str] = {}
    if not frigate_camera_to_ip:
        # First, build IP->device_name map from devices we already scanned
    ip_to_device_names: dict[str, list[str]] = {}
    for device_entry in device_registry.devices.values():
        # Skip Frigate devices
        is_frigate = False
        for identifier_domain, _ in device_entry.identifiers:
            if identifier_domain == "frigate":
                is_frigate = True
                break
        if is_frigate:
            continue
        
        # Get MAC address
        mac_address = None
        for connection_type, connection_id in device_entry.connections:
            if connection_type == dr.CONNECTION_NETWORK_MAC:
                mac_address = connection_id.lower()
                break
        
        if not mac_address:
            continue
        
        # Get IP address (same logic as before)
        ip_address = None
        for config_entry_id in device_entry.config_entries:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if config_entry:
                if "host" in config_entry.data:
                    host = config_entry.data["host"]
                    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', host)
                    if ip_match:
                        ip_address = ip_match.group()
                        break
        
        if ip_address:
            device_name = device_entry.name or ""
            if ip_address not in ip_to_device_names:
                ip_to_device_names[ip_address] = []
            ip_to_device_names[ip_address].append(device_name)
    
    # Now build name->IP map with all name variations
    for ip_address, device_names in ip_to_device_names.items():
        for device_name in device_names:
            # Create all possible name variations
            name_variations = [
                device_name.lower().replace(" ", "_").replace("-", "_"),
                device_name.lower().replace(" ", "_"),
                device_name.lower().replace("-", "_"),
                device_name.lower(),
                # Also try without common suffixes
                device_name.lower().replace(" camera", "").replace(" ", "_"),
                device_name.lower().replace(" camera", "").replace("-", "_"),
            ]
            for name_var in name_variations:
                if name_var:  # Don't add empty strings
                    camera_name_to_ip[name_var] = ip_address
            _LOGGER.info("Mapped device name '%s' to IP %s (variations: %s)", 
                       device_name, ip_address, name_variations[:3])
    
    _LOGGER.info("Frigate camera IPs: %s", frigate_camera_to_ip)
    _LOGGER.info("Fallback camera name IPs: %s", camera_name_to_ip)
    
    # Now find Frigate devices and update them
    frigate_devices_updated = 0
    frigate_camera_count = 0
    
    for device_entry in device_registry.devices.values():
        # Check if this is a Frigate device
        is_frigate = False
        for identifier_domain, identifier_id in device_entry.identifiers:
            if identifier_domain == "frigate":
                is_frigate = True
                frigate_camera_count += 1
                break
        
        if not is_frigate:
            continue
        
        device_name = device_entry.name or ""
        
        # Skip the main Frigate server device (usually just named "Frigate")
        # We only want individual camera devices
        if device_name.lower() == "frigate" or device_name.lower().startswith("frigate "):
            _LOGGER.debug("Skipping main Frigate server device: %s", device_name)
            continue
        
        camera_name_normalized = device_name.lower().replace(" ", "_").replace("-", "_")
        
        # Try to find IP for this Frigate camera
        camera_ip = None
        
        # Method 1: Get IP from Frigate API/config (most reliable)
        if camera_name_normalized in frigate_camera_to_ip:
            camera_ip = frigate_camera_to_ip[camera_name_normalized]
            _LOGGER.info("Got IP %s for Frigate camera '%s' from Frigate config", camera_ip, device_name)
        
        # Method 2: Match by camera name from other integrations (fallback)
        if not camera_ip and camera_name_normalized in camera_name_to_ip:
            camera_ip = camera_name_to_ip[camera_name_normalized]
            _LOGGER.info("Matched Frigate camera '%s' to IP %s by name from other integration", device_name, camera_ip)
        
        # Method 3: Try to extract IP from device name
        if not camera_ip:
            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', device_name)
            if ip_match:
                camera_ip = ip_match.group()
                _LOGGER.info("Extracted IP %s from Frigate device name '%s'", camera_ip, device_name)
        
        # Method 3: Check device's entities for stream URLs (but Frigate uses go2rtc proxy, so this won't work)
        # Skip this - Frigate cameras go through go2rtc proxy at 127.0.0.1
        
        # If we found an IP, look up MAC address
        if camera_ip and camera_ip in ip_to_mac:
            mac_address = ip_to_mac[camera_ip]
            
            # Check if MAC is already added
            has_mac = False
            for conn_type, conn_id in device_entry.connections:
                if conn_type == dr.CONNECTION_NETWORK_MAC and conn_id.lower() == mac_address:
                    has_mac = True
                    break
            
            if not has_mac:
                # Check if MAC is already registered to another device
                mac_already_registered = False
                for other_device in device_registry.devices.values():
                    if other_device.id == device_entry.id:
                        continue  # Skip self
                    for conn_type, conn_id in other_device.connections:
                        if conn_type == dr.CONNECTION_NETWORK_MAC and conn_id.lower() == mac_address:
                            mac_already_registered = True
                            _LOGGER.info(
                                "MAC %s already registered to device '%s' (%s). "
                                "Home Assistant will merge devices automatically.",
                                mac_address, other_device.name or "Unknown", other_device.manufacturer or "Unknown"
                            )
                            break
                    if mac_already_registered:
                        break
                
                if not mac_already_registered:
                    # Get current identifiers and connections
                    current_identifiers = set(device_entry.identifiers)
                    current_connections = set(device_entry.connections)
                    
                    # Add MAC address identifier and connection
                    new_identifiers = current_identifiers.copy()
                    new_identifiers.add(("mac", mac_address))
                    
                    new_connections = current_connections.copy()
                    new_connections.add((dr.CONNECTION_NETWORK_MAC, mac_address))
                    
                    # Update device registry
                    try:
                        device_registry.async_update_device(
                            device_entry.id,
                            new_identifiers=new_identifiers,
                            new_connections=new_connections,
                        )
                        
                        frigate_devices_updated += 1
                        _LOGGER.info(
                            "✓ Updated Frigate device '%s' (IP: %s) with MAC address: %s",
                            device_name,
                            camera_ip,
                            mac_address,
                        )
                    except Exception as e:
                        # Handle collision errors gracefully
                        if "DeviceConnectionCollisionError" in str(type(e).__name__) or "already registered" in str(e).lower():
                            _LOGGER.info(
                                "MAC %s collision detected for device '%s'. "
                                "This is expected - Home Assistant will merge devices automatically.",
                                mac_address, device_name
                            )
                        else:
                            raise
            else:
                _LOGGER.info("Frigate device '%s' already has MAC address", device_name)
        elif camera_ip:
            _LOGGER.warning(
                "Could not find MAC address for Frigate camera '%s' (IP: %s). "
                "Make sure the camera is configured in another integration (Hikvision, Unifi, etc.)",
                device_name,
                camera_ip,
            )
        else:
            _LOGGER.warning("Could not find IP address for Frigate camera '%s'", device_name)
    
    # Log summary
    _LOGGER.info(
        "=== Frigate Device Merger scan complete ==="
    )
    _LOGGER.info(
        "Found %d Frigate camera(s), %d IP-to-MAC mappings, updated %d camera(s)",
        frigate_camera_count,
        len(ip_to_mac),
        frigate_devices_updated
    )
    
    if frigate_devices_updated > 0:
        _LOGGER.info("✓ Successfully updated %d Frigate camera(s) with MAC addresses", frigate_devices_updated)
    elif frigate_camera_count == 0:
        _LOGGER.warning("No Frigate cameras found. Make sure Frigate integration is set up.")
    elif len(ip_to_mac) == 0:
        _LOGGER.warning(
            "Found %d Frigate camera(s) but no MAC addresses from other integrations. "
            "Make sure your camera integrations (Hikvision, Unifi, etc.) are configured.",
            frigate_camera_count
        )
    else:
        _LOGGER.warning(
            "Found %d Frigate camera(s) and %d MAC address(es) but couldn't match them by IP. "
            "Check that IP addresses match between Frigate and other integrations.",
            frigate_camera_count,
            len(ip_to_mac)
        )
