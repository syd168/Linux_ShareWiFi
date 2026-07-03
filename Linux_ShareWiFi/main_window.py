"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QButtonGroup,
)

from . import create_ap_cli as cap
from .qr_dialog import QrDialog
from .qr_utils import generate_qr_png
from .workers import ClientsWorker, CreateHotspotWorker, RefreshWorker, StopHotspotWorker


class HotspotListItem(QListWidgetItem):
    def __init__(self, hotspot: cap.RunningHotspot):
        super().__init__()
        self.hotspot = hotspot


class HotspotRowWidget(QWidget):
    def __init__(
        self,
        hotspot: cap.RunningHotspot,
        on_stop,
        on_qr,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.hotspot = hotspot
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(
            QLabel(
                f"PID {hotspot.pid}  |  WiFi: {hotspot.phy_iface}  |  AP: {hotspot.ap_iface}"
            ),
            stretch=1,
        )
        btn_stop = QPushButton("Stop")
        btn_qr = QPushButton("QR")
        btn_stop.clicked.connect(lambda: on_stop(hotspot.phy_iface))
        btn_qr.clicked.connect(lambda: on_qr(hotspot))
        layout.addWidget(btn_stop)
        layout.addWidget(btn_qr)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux Share WiFi")
        self.resize(720, 680)
        self._running: list[cap.RunningHotspot] = []
        self._workers: list = []

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addLayout(self._build_config_section())
        root.addLayout(self._build_action_section())
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)
        root.addWidget(self._build_hotspot_section())
        root.addWidget(self._build_clients_section())

        self.status_label = QLabel("Ready")
        root.addWidget(self.status_label)

        self._populate_interfaces()
        self._load_defaults()
        self.refresh_hotspots()

        self.combo_wifi.currentIndexChanged.connect(self._update_create_enabled)

    def _build_config_section(self) -> QVBoxLayout:
        box = QGroupBox("Hotspot settings")
        layout = QVBoxLayout(box)

        form = QFormLayout()
        self.entry_ssid = QLineEdit("MyAccessPoint")
        form.addRow("SSID", self.entry_ssid)

        pass_row = QHBoxLayout()
        self.entry_pass = QLineEdit("12345678")
        self.entry_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry_pass.setPlaceholderText("WiFi password (min. 8 characters)")
        self.btn_show_pass = QToolButton()
        self.btn_show_pass.setCheckable(True)
        self.btn_show_pass.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_show_pass.setAutoRaise(False)
        self.btn_show_pass.setFixedHeight(self.entry_pass.sizeHint().height())
        self.btn_show_pass.toggled.connect(self._toggle_pass_visibility)
        self._update_show_pass_button(False)
        self.cb_open = QCheckBox("Open network")
        self.cb_open.toggled.connect(self._on_open_toggled)
        pass_row.addWidget(self.entry_pass, stretch=1)
        pass_row.addWidget(self.btn_show_pass)
        pass_row.addWidget(self.cb_open)
        form.addRow("Password", pass_row)

        self.combo_wifi = QComboBox()
        self.combo_internet = QComboBox()
        form.addRow("WiFi interface", self.combo_wifi)
        form.addRow("Share Internet via", self.combo_internet)

        freq_row = QHBoxLayout()
        self.freq_group = QButtonGroup(self)
        self.rb_auto = QRadioButton("Auto")
        self.rb_24 = QRadioButton("2.4 GHz")
        self.rb_5 = QRadioButton("5 GHz")
        self.rb_auto.setChecked(True)
        for i, rb in enumerate((self.rb_auto, self.rb_24, self.rb_5)):
            self.freq_group.addButton(rb, i)
            freq_row.addWidget(rb)
        form.addRow("Frequency", freq_row)

        layout.addLayout(form)
        outer = QVBoxLayout()
        outer.addWidget(box)
        return outer

    def _build_action_section(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.btn_create = QPushButton("Create hotspot")
        self.btn_stop_top = QPushButton("Stop selected")
        self.btn_create.clicked.connect(self.on_create)
        self.btn_stop_top.clicked.connect(self.on_stop_selected)
        row.addWidget(self.btn_create)
        row.addStretch()
        row.addWidget(self.btn_stop_top)
        return row

    def _build_hotspot_section(self) -> QGroupBox:
        box = QGroupBox("Active Hotspots (right-click for details)")
        layout = QVBoxLayout(box)

        self.hotspot_list = QListWidget()
        self.hotspot_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.hotspot_list.customContextMenuRequested.connect(self._on_hotspot_context)
        self.hotspot_list.itemSelectionChanged.connect(self._update_create_enabled)
        layout.addWidget(self.hotspot_list)

        btn_row = QHBoxLayout()
        self.btn_refresh_hotspots = QPushButton("Refresh list")
        self.btn_refresh_hotspots.clicked.connect(self.refresh_hotspots)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_refresh_hotspots)
        layout.addLayout(btn_row)
        return box

    def _build_clients_section(self) -> QGroupBox:
        box = QGroupBox("Connected devices")
        layout = QVBoxLayout(box)
        self.clients_table = QTableWidget(0, 4)
        self.clients_table.setHorizontalHeaderLabels(["#", "Hostname", "IP", "MAC"])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.clients_table)
        self.btn_refresh_clients = QPushButton("Refresh clients")
        self.btn_refresh_clients.clicked.connect(self.refresh_clients)
        layout.addWidget(self.btn_refresh_clients)
        return box

    def _populate_interfaces(self):
        wifi = cap.list_wifi_interfaces()
        all_ifaces = cap.list_network_interfaces()
        self.combo_wifi.clear()
        self.combo_internet.clear()
        for iface in wifi:
            self.combo_wifi.addItem(iface)
        for iface in all_ifaces:
            self.combo_internet.addItem(iface)
        if self.combo_wifi.count():
            self.combo_wifi.setCurrentIndex(0)
        for i, iface in enumerate(all_ifaces):
            if iface.startswith("en") or iface.startswith("eth"):
                self.combo_internet.setCurrentIndex(i)
                break

    def _load_defaults(self):
        self.entry_ssid.setText("MyAccessPoint")
        self.entry_pass.setText("12345678")

    def _freq_band(self) -> str | None:
        if self.rb_24.isChecked():
            return "2.4"
        if self.rb_5.isChecked():
            return "5"
        return None

    def _update_show_pass_button(self, visible: bool):
        icon = QIcon()
        for name in (
            ("view-conceal", "view-hidden") if visible else ("view-reveal", "view-visible")
        ):
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                break
        self.btn_show_pass.setIcon(icon)
        self.btn_show_pass.setText("Hide" if visible else "Show")
        self.btn_show_pass.setToolTip("Hide password" if visible else "Show password as plain text")

    def _toggle_pass_visibility(self, visible: bool):
        self.entry_pass.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self._update_show_pass_button(visible)

    def _on_open_toggled(self, checked: bool):
        self.entry_pass.setEnabled(not checked)
        self.btn_show_pass.setEnabled(not checked)
        if checked and self.btn_show_pass.isChecked():
            self.btn_show_pass.blockSignals(True)
            self.btn_show_pass.setChecked(False)
            self.btn_show_pass.blockSignals(False)
            self._toggle_pass_visibility(False)

    def _selected_hotspot(self) -> cap.RunningHotspot | None:
        item = self.hotspot_list.currentItem()
        return item.hotspot if isinstance(item, HotspotListItem) else None

    def _selected_hotspot_id(self) -> str | None:
        hs = self._selected_hotspot()
        if hs:
            return hs.phy_iface
        return None

    def _update_create_enabled(self):
        wifi = self.combo_wifi.currentText()
        busy = cap.wifi_iface_is_running(wifi, self._running) if wifi else False
        self.btn_create.setEnabled(bool(wifi) and not busy)

    def _set_busy(self, busy: bool, message: str = ""):
        self.progress.setVisible(busy)
        self.btn_create.setEnabled(not busy and self.btn_create.isEnabled())
        self.btn_stop_top.setEnabled(not busy)
        if message:
            self.status_label.setText(message)

    def refresh_hotspots(self):
        worker = RefreshWorker(self)
        worker.hotspots_ready.connect(self._on_hotspots_ready)
        worker.error.connect(lambda m: self.status_label.setText(m))
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def _on_hotspots_ready(self, hotspots: list):
        self._running = hotspots
        self.hotspot_list.clear()
        for hs in hotspots:
            item = HotspotListItem(hs)
            row = HotspotRowWidget(hs, self._stop_hotspot, self._show_qr_for_hotspot, self)
            item.setSizeHint(row.sizeHint())
            self.hotspot_list.addItem(item)
            self.hotspot_list.setItemWidget(item, row)
        if self.hotspot_list.count():
            self.hotspot_list.setCurrentRow(0)
        count = len(hotspots)
        if count:
            self.status_label.setText(
                f"{count} active hotspot(s) — pick a free WiFi interface to create another"
            )
            self.btn_stop_top.setEnabled(True)
        else:
            self.status_label.setText("Not running")
            self.btn_stop_top.setEnabled(False)
            self.clients_table.setRowCount(0)
        self._update_create_enabled()

    def on_create(self):
        ssid = self.entry_ssid.text().strip()
        if not ssid:
            QMessageBox.warning(self, "Validation", "SSID is required")
            return
        wifi = self.combo_wifi.currentText()
        internet = self.combo_internet.currentText()
        if cap.wifi_iface_is_running(wifi, self._running):
            QMessageBox.warning(self, "Already running", f"Hotspot already active on {wifi}")
            return
        passphrase = "" if self.cb_open.isChecked() else self.entry_pass.text()

        self._set_busy(True, "Creating hotspot...")
        worker = CreateHotspotWorker(wifi, internet, ssid, passphrase, self._freq_band(), self)
        worker.line.connect(self.status_label.setText)
        worker.finished_ok.connect(self._on_create_finished)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def _on_create_finished(self, ok: bool, message: str):
        self._set_busy(False, message)
        self.refresh_hotspots()

    def on_stop_selected(self):
        hs_id = self._selected_hotspot_id()
        if not hs_id:
            QMessageBox.information(self, "Stop", "Select a hotspot in the Active Hotspots list")
            return
        self._stop_hotspot(hs_id)

    def _stop_hotspot(self, hotspot_id: str):
        self._set_busy(True, f"Stopping {hotspot_id}...")
        worker = StopHotspotWorker(hotspot_id, self)
        worker.finished_ok.connect(self._on_stop_finished)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def _on_stop_finished(self, ok: bool, message: str):
        self._set_busy(False, message)
        self.refresh_hotspots()

    def _on_hotspot_context(self, pos):
        item = self.hotspot_list.itemAt(pos)
        if not isinstance(item, HotspotListItem):
            return
        self.hotspot_list.setCurrentItem(item)
        details = cap.show_hotspot_info(item.hotspot.phy_iface)
        if not details:
            QMessageBox.warning(self, "Details", "Could not read hotspot details")
            return
        body = (
            f"SSID: {details.ssid or '(unknown)'}\n"
            f"Password: {details.passphrase or '(none)'}\n"
            f"Security: {details.encryption or '(unknown)'}\n"
            f"Hidden: {details.hidden or 'No'}\n"
            f"Channel: {details.channel or '(unknown)'}\n"
            f"Band: {details.band or '(unknown)'}\n"
            f"Gateway: {details.gateway or '(unknown)'}\n"
            f"WiFi interface: {details.phy_iface}\n"
            f"AP interface: {details.ap_iface}\n"
            f"Internet sharing: {details.internet_iface}\n"
            f"PID: {details.pid}"
        )
        QMessageBox.information(self, f"Hotspot: {details.ssid or item.hotspot.phy_iface}", body)

    def _show_qr_for_hotspot(self, hs: cap.RunningHotspot):
        details = cap.show_hotspot_info(hs.phy_iface)
        if not details or not details.ssid:
            QMessageBox.warning(self, "QR", "Could not read SSID for QR code")
            return
        open_net = details.encryption == "Open" or not details.passphrase or details.passphrase == "(none)"
        path = generate_qr_png(details.ssid, details.passphrase if not open_net else "", open_network=open_net)
        QrDialog(path, details.ssid, self).exec()

    def refresh_clients(self):
        hs = self._selected_hotspot()
        if not hs:
            QMessageBox.information(self, "Clients", "Select a hotspot in the list")
            return
        worker = ClientsWorker(hs.pid, self)
        worker.clients_ready.connect(self._on_clients_ready)
        worker.error.connect(lambda m: self.status_label.setText(m))
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def _on_clients_ready(self, clients: list):
        self.clients_table.setRowCount(0)
        for i, client in enumerate(clients, start=1):
            row = self.clients_table.rowCount()
            self.clients_table.insertRow(row)
            self.clients_table.setItem(row, 0, QTableWidgetItem(str(i)))
            self.clients_table.setItem(row, 1, QTableWidgetItem(client.hostname))
            self.clients_table.setItem(row, 2, QTableWidgetItem(client.ip))
            self.clients_table.setItem(row, 3, QTableWidgetItem(client.mac))


def run_app() -> int:
    app = QApplication([])
    app.setApplicationName("Linux_ShareWiFi")
    win = MainWindow()
    win.show()
    return app.exec()
