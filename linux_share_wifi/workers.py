"""Background workers for create_ap operations."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from . import create_ap_cli as cap


class CreateHotspotWorker(QThread):
    line = Signal(str)
    finished_ok = Signal(bool, str)

    def __init__(
        self,
        wifi_iface: str,
        internet_iface: str,
        ssid: str,
        passphrase: str,
        freq_band: str | None,
        parent=None,
    ):
        super().__init__(parent)
        self.wifi_iface = wifi_iface
        self.internet_iface = internet_iface
        self.ssid = ssid
        self.passphrase = passphrase
        self.freq_band = freq_band

    def run(self):
        try:
            mk_args = cap.build_mkconfig_args(
                self.wifi_iface,
                self.internet_iface,
                self.ssid,
                self.passphrase,
                freq_band=self.freq_band,
            )
            proc = cap.run_command(mk_args)
            if proc.returncode != 0:
                self.finished_ok.emit(False, proc.stdout + proc.stderr)
                return

            enabled = False
            for line in cap.stream_create_hotspot(cap.build_create_from_config_args()):
                self.line.emit(line)
                if "AP-ENABLED" in line:
                    enabled = True
                    break
            self.finished_ok.emit(enabled, "Hotspot started" if enabled else "Hotspot failed to start")
        except Exception as exc:  # noqa: BLE001 — surface to UI
            self.finished_ok.emit(False, str(exc))


class StopHotspotWorker(QThread):
    finished_ok = Signal(bool, str)

    def __init__(self, hotspot_id: str, parent=None):
        super().__init__(parent)
        self.hotspot_id = hotspot_id

    def run(self):
        ok, msg = cap.stop_hotspot(self.hotspot_id)
        self.finished_ok.emit(ok, msg or ("Stopped" if ok else "Stop failed"))


class RefreshWorker(QThread):
    hotspots_ready = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            self.hotspots_ready.emit(cap.list_running_hotspots())
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class ClientsWorker(QThread):
    clients_ready = Signal(list)
    error = Signal(str)

    def __init__(self, hotspot_id: str, parent=None):
        super().__init__(parent)
        self.hotspot_id = hotspot_id

    def run(self):
        try:
            self.clients_ready.emit(cap.list_clients(self.hotspot_id))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
