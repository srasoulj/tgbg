from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig, ChannelConfig, load_config
from ..sync_runner import run_full_sync


class SyncWorker(QThread):
    finished_with_status = Signal(str)
    log_line = Signal(str)

    def __init__(self, app_config: AppConfig):
        super().__init__()
        self._config = app_config

    def run(self) -> None:
        try:
            self.log_line.emit("Starting sync...")
            asyncio.run(run_full_sync(self._config))
            self.log_line.emit("Sync completed.")
            self.finished_with_status.emit("success")
        except Exception as exc:  # noqa: BLE001
            self.log_line.emit(f"Error during sync: {exc}")
            self.finished_with_status.emit("error")


class MainWindow(QWidget):
    def __init__(self, app_config: Optional[AppConfig] = None):
        super().__init__()
        self.setWindowTitle("Telegram Channel Sync")

        self._config = app_config or load_config()
        self._worker: Optional[SyncWorker] = None

        # UI elements
        self.channel_list = QListWidget()
        self.sync_button = QPushButton("Sync now")
        self.status_label = JLabel = QLabel("Last sync: never")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self._build_layout()
        self._populate_channels()

        self.sync_button.clicked.connect(self._on_sync_clicked)

    def _build_layout(self) -> None:
        root_layout = QHBoxLayout()

        # Left: channels
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Channels"))
        left_layout.addWidget(self.channel_list)

        # Right: controls and logs
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.sync_button)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(QLabel("Logs"))
        right_layout.addWidget(self.log_view)

        root_layout.addLayout(left_layout)
        root_layout.addLayout(right_layout)

        self.setLayout(root_layout)

    def _populate_channels(self) -> None:
        for ch in self._config.channels or []:
            item = QListWidgetItem(ch.username_or_id)
            item.setCheckState(2 if ch.enabled else 0)
            self.channel_list.addItem(item)

    def _on_sync_clicked(self) -> None:
        # Update enabled flags from UI
        updated_channels: list[ChannelConfig] = []
        for idx in range(self.channel_list.count()):
            item = self.channel_list.item(idx)
            enabled = item.checkState() == 2
            updated_channels.append(ChannelConfig(username_or_id=item.text(), enabled=enabled))
        self._config.channels = updated_channels

        self.sync_button.setEnabled(False)
        self._append_log("Triggering sync...")

        self._worker = SyncWorker(self._config)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished_with_status.connect(self._on_sync_finished)
        self._worker.start()

    def _append_log(self, line: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_view.append(f"[{timestamp}] {line}")

    def _on_sync_finished(self, status: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.setText(f"Last sync: {timestamp} ({status})")
        self.sync_button.setEnabled(True)


def run_ui() -> None:
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 500)
    window.show()
    sys.exit(app.exec())


