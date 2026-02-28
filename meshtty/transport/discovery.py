"""Auto-discovery of Meshtastic devices across all transports."""

from __future__ import annotations

# Known USB VID substrings for common Meshtastic serial chips:
#   CP210x (Silicon Labs): VID 10C4
#   CH340/CH341:           VID 1A86
#   FTDI:                  VID 0403
#   Espressif USB-JTAG:    VID 303A
_MESHTASTIC_VIDS = {"10C4", "1A86", "0403", "303A"}

# Meshtastic BLE service UUID (used to identify devices during scan)
MESHTASTIC_SERVICE_UUID = "6ba4e4e0-b3f8-11ea-b3de-0242ac130004"


def scan_serial_ports() -> list[dict]:
    """Return list of likely Meshtastic serial ports.

    Each entry: {"port": str, "description": str, "hwid": str}
    """
    try:
        import serial.tools.list_ports
    except ImportError:
        return []

    results = []
    for p in serial.tools.list_ports.comports():
        hwid_upper = p.hwid.upper()
        if any(vid in hwid_upper for vid in _MESHTASTIC_VIDS):
            results.append(
                {
                    "port": p.device,
                    "description": p.description,
                    "hwid": p.hwid,
                }
            )
    return results


async def scan_ble_devices(timeout: float = 5.0) -> list[dict]:
    """Async BLE scan. Returns list of {"address": str, "name": str} dicts.

    Filters for devices whose name contains "meshtastic" or that advertise
    the Meshtastic service UUID.
    """
    try:
        import bleak
    except ImportError:
        return []

    devices = await bleak.BleakScanner.discover(timeout=timeout, return_adv=True)
    results = []
    for addr, (device, adv) in devices.items():
        name = device.name or ""
        service_uuids = [str(u).lower() for u in (adv.service_uuids or [])]
        is_meshtastic = (
            "meshtastic" in name.lower()
            or MESHTASTIC_SERVICE_UUID.lower() in service_uuids
        )
        if is_meshtastic:
            results.append({"address": addr, "name": name or "Unknown"})
    return results
