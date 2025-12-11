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
        ip_address = None
        for config_entry_id in device_entry.config_entries:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if config_entry:
                # Check common integration config fields for IP/host
                if "host" in config_entry.data:
                    ip_address = config_entry.data["host"]
                elif "ip_address" in config_entry.data:
                    ip_address = config_entry.data["ip_address"]
                elif "url" in config_entry.data:
                    # Extract IP from URL
                    url = config_entry.data["url"]
                    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', url)
                    if ip_match:
                        ip_address = ip_match.group()
        
        # Fallback: try to extract IP from device name
        if not ip_address:
            device_name = device_entry.name or ""
            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', device_name)
            if ip_match:
                ip_address = ip_match.group()
        
        if ip_address and mac_address:
            ip_to_mac[ip_address] = mac_address
            _LOGGER.info("Found MAC %s for IP %s from device: %s", mac_address, ip_address, device_entry.name)
    
    _LOGGER.info("Found %d IP-to-MAC mappings from other integrations", len(ip_to_mac))
    
    # Build a map of camera names to IPs from other integrations' config entries
    # This is more reliable than trying to extract from Frigate stream URLs (which go through go2rtc proxy)
    camera_name_to_ip: dict[str, str] = {}
    
    # Scan config entries from camera integrations to build name->IP map
    for config_entry in hass.config_entries.async_entries():
        if config_entry.domain in ("hikvision_isapi", "unifiprotect", "reolink"):
            host = config_entry.data.get("host", "")
            if host:
                # Try to extract IP
                ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', host)
                if ip_match:
                    ip_address = ip_match.group()
                    # Get device name from device registry
                    for device_entry in device_registry.devices.values():
                        if config_entry.entry_id in device_entry.config_entries:
                            device_name = device_entry.name or ""
                            # Normalize name for matching - try multiple variations
                            name_variations = [
                                device_name.lower().replace(" ", "_").replace("-", "_"),
                                device_name.lower().replace(" ", "_"),
                                device_name.lower().replace("-", "_"),
                                device_name.lower(),
                            ]
                            for name_var in name_variations:
                                camera_name_to_ip[name_var] = ip_address
                            _LOGGER.info("Mapped camera name '%s' (variations: %s) to IP %s from %s integration", 
                                       device_name, name_variations[:2], ip_address, config_entry.domain)
                            break
    
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
        camera_name_normalized = device_name.lower().replace(" ", "_").replace("-", "_")
        
        # Try to find IP for this Frigate camera
        camera_ip = None
        
        # Method 1: Match by camera name from other integrations
        if camera_name_normalized in camera_name_to_ip:
            camera_ip = camera_name_to_ip[camera_name_normalized]
            _LOGGER.info("Matched Frigate camera '%s' to IP %s by name", device_name, camera_ip)
        
        # Method 2: Try to extract IP from device name
        if not camera_ip:
            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', device_name)
            if ip_match:
                camera_ip = ip_match.group()
                _LOGGER.info("Extracted IP %s from Frigate device name '%s'", camera_ip, device_name)
        
        # Method 3: Check device's entities for stream URLs
        if not camera_ip:
            for entity_entry in entity_registry.entities.values():
                if entity_entry.device_id == device_entry.id and entity_entry.domain == "camera":
                    state = hass.states.get(entity_entry.entity_id)
                    if state and hasattr(state, "attributes"):
                        stream_source = state.attributes.get("stream_source") or state.attributes.get("entity_picture")
                        if stream_source:
                            ip_match = re.search(r'@([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', stream_source)
                            if ip_match:
                                camera_ip = ip_match.group(1)
                                _LOGGER.info("Found IP %s for Frigate device '%s' from entity stream", camera_ip, device_name)
                                break
                    if camera_ip:
                        break
        
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
                # Get current identifiers and connections
                current_identifiers = set(device_entry.identifiers)
                current_connections = set(device_entry.connections)
                
                # Add MAC address identifier and connection
                new_identifiers = current_identifiers.copy()
                new_identifiers.add(("mac", mac_address))
                
                new_connections = current_connections.copy()
                new_connections.add((dr.CONNECTION_NETWORK_MAC, mac_address))
                
                # Update device registry
                device_registry.async_update_device(
                    device_entry.id,
                    identifiers=new_identifiers,
                    connections=new_connections,
                )
                
                frigate_devices_updated += 1
                _LOGGER.info(
                    "✓ Updated Frigate device '%s' (IP: %s) with MAC address: %s",
                    device_name,
                    camera_ip,
                    mac_address,
                )
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
