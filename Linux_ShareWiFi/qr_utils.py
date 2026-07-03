"""Generate WiFi QR codes for joining the hotspot."""

from __future__ import annotations

import os
import tempfile

import qrcode
from qrcode.constants import ERROR_CORRECT_H


def build_wifi_qr_string(ssid: str, password: str, *, open_network: bool) -> str:
    if open_network or not password:
        return f"WIFI:T:nopass;S:{ssid};;"
    return f"WIFI:T:WPA;S:{ssid};P:{password};;"


def generate_qr_png(ssid: str, password: str, *, open_network: bool) -> str:
    payload = build_wifi_qr_string(ssid, password, open_network=open_network)
    path = os.path.join(tempfile.gettempdir(), f"Linux_ShareWiFi_qr_{os.getuid()}.png")
    img = qrcode.make(payload, error_correction=ERROR_CORRECT_H)
    img.save(path)
    return path
