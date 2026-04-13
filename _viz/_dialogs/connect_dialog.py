from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..constants import DEFAULT_WS_HOST, DEFAULT_WS_PORT


class ConnectDialog(QDialog):
    """Dialog to enter WebSocket connection parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Live Source")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._host_input = QLineEdit(DEFAULT_WS_HOST)
        form.addRow("Host:", self._host_input)

        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(DEFAULT_WS_PORT)
        form.addRow("Port:", self._port_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._connect_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    @property
    def host(self) -> str:
        return self._host_input.text().strip()

    @property
    def port(self) -> int:
        return self._port_input.value()
