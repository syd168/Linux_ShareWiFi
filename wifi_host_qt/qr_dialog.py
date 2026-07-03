"""QR code preview dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class QrDialog(QDialog):
    def __init__(self, image_path: str, ssid: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"QR code — {ssid}")
        self.setModal(True)

        layout = QVBoxLayout(self)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(image_path)
        if not pix.isNull():
            label.setPixmap(pix.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            label.setText("Failed to load QR image")
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
