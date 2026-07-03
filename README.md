# Linux Share WiFi

**English** | [中文](README.zh-CN.md)

Standalone **PySide6** Linux WiFi hotspot GUI. It uses the system [`create_ap`](https://github.com/lakinduakash/linux-wifi-hotspot) script as the backend (same as the GTK `wihotspot` app).

You can copy the entire `Linux_ShareWiFi` folder anywhere and run it on its own.

## Features

- Create / stop WiFi hotspots (NAT sharing)
- Select WiFi adapter and upstream internet adapter
- SSID, password, open network, 2.4 / 5 GHz band
- Active hotspot list with **Stop** / **QR** on each row
- Right-click a hotspot row for details (SSID, password, gateway, etc.)
- Connected client list with refresh
- Non-root users authorize via `pkexec` (same as the C GUI)
- **Show / Hide** toggle next to the password field

## Quick start

```bash
cd Linux_ShareWiFi
chmod +x run.sh
./run.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m Linux_ShareWiFi
```

**Run as a normal user** (do not use `sudo ./run.sh`). Polkit will prompt for authorization when creating or stopping a hotspot.

The default hotspot SSID is **MyAccessPoint**; you can change it in the UI.

## Can it run on a fresh Ubuntu install?

**Yes**, but copying the `Linux_ShareWiFi` folder alone is not enough—you also need system dependencies and the `create_ap` backend.

### What this project provides out of the box

- Copy the whole folder anywhere
- `./run.sh` creates a virtual environment and installs **PySide6** and **qrcode**
- **No** need to compile the GTK/C `wihotspot` app

### What a fresh Ubuntu install is still missing

| Category | Install | Notes |
|----------|---------|-------|
| Python | `python3`, `python3-venv` | Minimal installs may not include venv |
| Qt UI | Desktop environment (GNOME, etc.) | No GUI without a display |
| Hotspot backend | **`create_ap`** | The GUI is the front-end; this creates the hotspot |
| System tools | hostapd, dnsmasq, iptables, iw, iproute2 | Required when `create_ap` runs |
| Permissions | `pkexec` (policykit-1) | Authorization dialog when creating/stopping hotspots |
| Optional | haveged | Useful when entropy is low |

**Fresh Ubuntu does not include `create_ap` by default**—that is the step most people miss.

### Recommended setup (Ubuntu Desktop)

```bash
# 1. System dependencies
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
  hostapd dnsmasq iptables iw iproute2 policykit-1 haveged git

# 2. Install create_ap (pick one)

# Option A: PPA (easiest)
sudo add-apt-repository ppa:lakinduakash/lwh
sudo apt update
sudo apt install linux-wifi-hotspot   # includes create_ap

# Option B: CLI only from source
git clone https://github.com/lakinduakash/linux-wifi-hotspot.git
cd linux-wifi-hotspot
sudo make install-cli-only

# 3. Run Linux Share WiFi
cd /path/to/Linux_ShareWiFi
chmod +x run.sh
./run.sh
```

### Troubleshooting

1. **UI opens but no WiFi adapters in the list**  
   Run `iw dev` and confirm the driver works and the adapter supports AP mode.

2. **Hotspot creation fails**  
   Often missing `hostapd` / `dnsmasq`, or NetworkManager holds the adapter.  
   Try: `sudo systemctl stop hostapd dnsmasq`, then create again.

3. **PySide6 fails to start (missing libxcb, etc.)**  
   Uncommon on Ubuntu Desktop; server or headless setups may need extra Qt/X11 libraries.

4. **Hotspot details incomplete**  
   Requires a recent `create_ap` with `--show-info` support.

5. **Copying `.venv` to another machine**  
   Not recommended. Delete `.venv` on the new machine and run `./run.sh` to recreate it.

### Comparison with the GTK version

| | GTK original | Linux Share WiFi |
|---|--------------|------------------|
| Build | Requires gcc, GTK dev packages | **Not required** |
| Python | Not required | 3.9+ |
| create_ap | Required | **Also required** |
| System hotspot tools | Required | **Also required** |

On a **fresh Ubuntu Desktop** with dependencies and `create_ap` installed, it **runs normally** and is easier to deploy than the C/GTK build (no compilation).

## Dependencies

### Python packages (installed by `run.sh` / pip)

- Python 3.9+
- PySide6 >= 6.5.0
- qrcode[pil] >= 7.4.2

See `requirements.txt`.

### System tools

- `create_ap` (must be installed separately; see above)
- `hostapd`, `dnsmasq`, `iptables`, `iw`, `iproute2`, `bash`, `pkexec`
- Optional: `haveged`

Install `create_ap` from [linux-wifi-hotspot](https://github.com/lakinduakash/linux-wifi-hotspot) or your distribution packages.

Optional environment variables for custom script paths:

```bash
export CREATE_AP_BIN=/path/to/create_ap
export CREATE_AP_CONFIG=/etc/create_ap.conf
```

## Project layout

```
Linux_ShareWiFi/
  README.md
  README.zh-CN.md
  requirements.txt
  pyproject.toml
  run.sh
  Linux_ShareWiFi/
    __main__.py          # python -m Linux_ShareWiFi
    main_window.py       # Qt main window
    create_ap_cli.py     # create_ap wrapper
    workers.py           # background threads
    qr_utils.py          # QR generation
    qr_dialog.py
```

## Relationship to linux-wifi-hotspot

| | GTK original | Linux Share WiFi |
|---|--------------|------------------|
| UI | GTK 3 + Glade | PySide6 |
| Backend | create_ap | create_ap |
| Language | C | Python |
| Repository | May share monorepo | **Standalone repo** |

## License

FreeBSD (aligned with upstream create_ap). See the upstream project for full terms.
