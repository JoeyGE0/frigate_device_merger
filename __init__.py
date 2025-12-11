"""Frigate Device Merger - Adds MAC addresses to Frigate cameras for device merging."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr

_LOGGER = logging.getLogger(__name__)

DOMAIN = "frigate_device_merger"


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Frigate Device Merger component."""
    
    async def update_frigate_devices_service(call: ServiceCall) -> None:
        """Service to manually trigger Frigate device update."""
        _LOGGER.info("Manual update triggered via service call")
        await async_update_frigate_devices(hass)
    
    # Register service
    hass.services.async_register(
        DOMAIN,
        "update_devices",
        update_frigate_devices_service,
    )
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Frigate Device Merger from a config entry."""
    import asyncio
    
    # Wait a bit for other integrations to finish setting up
    async def delayed_update():
        await asyncio.sleep(10)  # Wait 10 seconds for other integrations to initialize
        await async_update_frigate_devices(hass)
    
    # Schedule update after startup
    hass.async_create_task(delayed_update())
    
    return True


async def async_update_frigate_devices(hass: HomeAssistant) -> None:
    """Update Frigate camera devices with MAC addresses from other integrations."""
    import re
    
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
            _LOGGER.debug("Found MAC %s for IP %s from %s", mac_address, ip_address, device_entry.name)
    
    # Build a map of Frigate camera names to IPs by checking camera entities
    from homeassistant.helpers import entity_registry as er
    entity_registry = er.async_get(hass)
    
    frigate_camera_to_ip: dict[str, str] = {}
    
    # Scan Frigate camera entities to extract IPs from stream URLs
    for entity_entry in entity_registry.entities.values():
        if entity_entry.platform != "frigate" or entity_entry.domain != "camera":
            continue
        
        # Try to get camera entity state to extract stream URL
        state = hass.states.get(entity_entry.entity_id)
        if state and hasattr(state, "attributes"):
            # Check for stream source or RTSP URL in attributes
            stream_source = state.attributes.get("stream_source") or state.attributes.get("entity_picture")
            if stream_source:
                # Extract IP from RTSP URL (rtsp://user:pass@IP:port/...)
                ip_match = re.search(r'@([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', stream_source)
                if ip_match:
                    camera_name = entity_entry.original_name or entity_entry.name or ""
                    frigate_camera_to_ip[camera_name.lower()] = ip_match.group(1)
                    _LOGGER.debug("Found IP %s for Frigate camera '%s' from stream URL", ip_match.group(1), camera_name)
    
    # Also check Frigate config entries for camera info
    for config_entry in hass.config_entries.async_entries("frigate"):
        # Frigate might store camera config in entry data or options
        # This is a fallback - entity scanning above should work better
        pass
    
    # Now find Frigate devices and update them
    frigate_devices_updated = 0
    
    for device_entry in device_registry.devices.values():
        # Check if this is a Frigate device
        is_frigate = False
        for identifier_domain, identifier_id in device_entry.identifiers:
            if identifier_domain == "frigate":
                is_frigate = True
                break
        
        if not is_frigate:
            continue
        
        device_name = device_entry.name or ""
        camera_name_normalized = device_name.lower().replace(" ", "_").replace("-", "_")
        
        # Try to find IP for this Frigate camera
        camera_ip = None
        
        # Method 1: Check our map from entity scanning
        for cam_name, cam_ip in frigate_camera_to_ip.items():
            cam_name_normalized = cam_name.lower().replace(" ", "_").replace("-", "_")
            if cam_name_normalized in camera_name_normalized or camera_name_normalized in cam_name_normalized:
                camera_ip = cam_ip
                _LOGGER.debug("Matched Frigate camera '%s' to IP %s from entity scan", device_name, camera_ip)
                break
        
        # Method 2: Try to extract IP from device name
        if not camera_ip:
            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', device_name)
            if ip_match:
                camera_ip = ip_match.group()
                _LOGGER.debug("Extracted IP %s from Frigate device name '%s'", camera_ip, device_name)
        
        # Method 3: Check device's entities for stream URLs
        if not camera_ip:
            for entity_id in device_entry.identifiers:
                # Get entities associated with this device
                for entity_entry in entity_registry.entities.values():
                    if entity_entry.device_id == device_entry.id and entity_entry.domain == "camera":
                        state = hass.states.get(entity_entry.entity_id)
                        if state and hasattr(state, "attributes"):
                            stream_source = state.attributes.get("stream_source") or state.attributes.get("entity_picture")
                            if stream_source:
                                ip_match = re.search(r'@([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', stream_source)
                                if ip_match:
                                    camera_ip = ip_match.group(1)
                                    _LOGGER.debug("Found IP %s for Frigate device '%s' from entity stream", camera_ip, device_name)
                                    break
                        if camera_ip:
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
                    "Updated Frigate device '%s' (IP: %s) with MAC address: %s",
                    device_name,
                    camera_ip,
                    mac_address,
                )
            else:
                _LOGGER.debug("Frigate device '%s' already has MAC address", device_name)
        elif camera_ip:
            _LOGGER.warning(
                "Could not find MAC address for Frigate camera '%s' (IP: %s). "
                "Make sure the camera is configured in another integration (Hikvision, Unifi, etc.)",
                device_name,
                camera_ip,
            )
    
    if frigate_devices_updated > 0:
        _LOGGER.info("Updated %d Frigate camera(s) with MAC addresses for device merging", frigate_devices_updated)
    else:
        _LOGGER.warning("No Frigate cameras were updated. Make sure other integrations are set up first.")
