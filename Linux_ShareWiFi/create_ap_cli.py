"""Wrapper around the system create_ap script."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable

CREATE_AP = os.environ.get("CREATE_AP_BIN", "create_ap")
CONFIG_PATH = os.environ.get("CREATE_AP_CONFIG", "/etc/create_ap.conf")
PKEXEC = ["pkexec", "--user", "root"]


def _runner_prefix() -> list[str]:
    if os.geteuid() == 0:
        return [CREATE_AP]
    return PKEXEC + [CREATE_AP]


def run_command(args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = _runner_prefix() + args
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=False,
    )


def list_wifi_interfaces() -> list[str]:
    if not shutil.which("iw"):
        return []
    proc = subprocess.run(["iw", "dev"], capture_output=True, text=True, check=False)
    return re.findall(r"^\s*Interface\s+(\S+)", proc.stdout, re.MULTILINE)


def list_network_interfaces() -> list[str]:
    sys_net = "/sys/class/net"
    if not os.path.isdir(sys_net):
        return []
    return sorted(
        name
        for name in os.listdir(sys_net)
        if name != "lo" and os.path.isdir(os.path.join(sys_net, name))
    )


@dataclass
class RunningHotspot:
    pid: str
    phy_iface: str
    ap_iface: str


def parse_running_line(line: str) -> RunningHotspot | None:
    line = line.strip()
    if not line:
        return None
    m = re.match(r"^(\S+)\s+(\S+)(?:\s+\((\S+)\))?$", line)
    if not m:
        return None
    pid, phy, ap = m.group(1), m.group(2), m.group(3)
    return RunningHotspot(pid=pid, phy_iface=phy, ap_iface=ap or phy)


def list_running_hotspots() -> list[RunningHotspot]:
    proc = run_command(["--list-running"])
    if proc.returncode != 0 and not proc.stdout.strip():
        return []
    out: list[RunningHotspot] = []
    for line in proc.stdout.splitlines():
        item = parse_running_line(line)
        if item:
            out.append(item)
    return out


@dataclass
class HotspotDetails:
    pid: str = ""
    phy_iface: str = ""
    ap_iface: str = ""
    internet_iface: str = ""
    ssid: str = ""
    passphrase: str = ""
    encryption: str = ""
    gateway: str = ""
    channel: str = ""
    band: str = ""
    hidden: str = ""


def parse_show_info(text: str) -> HotspotDetails:
    details = HotspotDetails()
    mapping = {
        "PID": "pid",
        "PHY_IFACE": "phy_iface",
        "AP_IFACE": "ap_iface",
        "INTERNET_IFACE": "internet_iface",
        "SSID": "ssid",
        "PASSPHRASE": "passphrase",
        "ENCRYPTION": "encryption",
        "GATEWAY": "gateway",
        "CHANNEL": "channel",
        "BAND": "band",
        "HIDDEN": "hidden",
    }
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        attr = mapping.get(key.strip())
        if attr:
            setattr(details, attr, value.strip())
    return details


def show_hotspot_info(hotspot_id: str) -> HotspotDetails | None:
    proc = run_command(["--show-info", hotspot_id])
    if proc.returncode != 0:
        return None
    return parse_show_info(proc.stdout)


def stop_hotspot(hotspot_id: str) -> tuple[bool, str]:
    proc = run_command(["--stop", hotspot_id], capture=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


@dataclass
class ConnectedClient:
    mac: str
    ip: str
    hostname: str


def list_clients(pid_or_iface: str) -> list[ConnectedClient]:
    proc = run_command(["--list-clients", pid_or_iface])
    clients: list[ConnectedClient] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("MAC"):
            continue
        parts = line.split()
        if len(parts) >= 3:
            clients.append(ConnectedClient(mac=parts[0], ip=parts[1], hostname=parts[2]))
    return clients


def build_mkconfig_args(
    wifi_iface: str,
    internet_iface: str,
    ssid: str,
    passphrase: str,
    *,
    freq_band: str | None,
) -> list[str]:
    args = [
        wifi_iface,
        internet_iface,
        ssid,
        passphrase,
        "--mkconfig",
        CONFIG_PATH,
    ]
    if freq_band in ("2.4", "5"):
        args.extend(["--freq-band", freq_band])
    return args


def build_create_from_config_args() -> list[str]:
    return ["--config", CONFIG_PATH]


def stream_create_hotspot(args: Iterable[str]):
    """Yield stdout lines while create_ap runs. Does not wait after iteration ends."""
    cmd = _runner_prefix() + list(args)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        yield line.rstrip("\n")
    # Intentionally do not wait(): create_ap keeps running until the hotspot stops.


def wifi_iface_is_running(wifi_iface: str, running: list[RunningHotspot] | None = None) -> bool:
    items = running if running is not None else list_running_hotspots()
    return any(h.phy_iface == wifi_iface for h in items)
