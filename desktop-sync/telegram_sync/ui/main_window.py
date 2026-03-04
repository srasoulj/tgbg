from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QInputDialog,
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
    need_code = Signal()
    need_password = Signal()

    def __init__(self, app_config: AppConfig, main_window: "MainWindow"):
        super().__init__()
        self._config = app_config
        self._main_window = main_window

    def run(self) -> None:
        try:
            self.log_line.emit("Starting sync...")
            result = asyncio.run(run_full_sync(
                self._config,
                get_code_callback=self._main_window.get_telegram_code_callback(self),
                get_password_callback=self._main_window.get_2fa_password_callback(self),
            ))
            if result:
                self.log_line.emit(
                    f"Done: {result['channels_processed']} channel(s), "
                    f"{result['messages_inserted']} new messages, "
                    f"{result['messages_skipped']} already in DB."
                )
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
        if self._config.channels is None:
            self._config.channels = []
        self._worker: Optional[SyncWorker] = None
        self._pending_code_future: Optional[asyncio.Future] = None
        self._pending_password_future: Optional[asyncio.Future] = None

        # Path to channels.json used by config loader
        self._channels_path = Path(__file__).resolve().parents[2] / "channels.json"

        # UI elements
        self.channel_list = QListWidget()
        self.channel_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.sync_button = QPushButton("Sync now")
        self.add_channel_button = QPushButton("Add channel")
        self.status_label = JLabel = QLabel("Last sync: never")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        # Path to channels.json used by config loader
        self._channels_path = Path(__file__).resolve().parents[2] / "channels.json"
        # Path to store last sync metadata
        self._last_sync_path = Path(__file__).resolve().parents[2] / "last_sync.json"

        self._build_layout()
        self._populate_channels()
        self._load_last_sync()

        self.sync_button.clicked.connect(self._on_sync_clicked)
        self.add_channel_button.clicked.connect(self._on_add_channel_clicked)

    def get_telegram_code_callback(self, worker: SyncWorker):
        def _get():
            future = asyncio.get_event_loop().create_future()
            self._pending_code_future = future
            worker.need_code.emit()
            return future
        return _get

    def get_2fa_password_callback(self, worker: SyncWorker):
        def _get():
            future = asyncio.get_event_loop().create_future()
            self._pending_password_future = future
            worker.need_password.emit()
            return future
        return _get

    def _on_need_code(self) -> None:
        if self._pending_code_future is None:
            return
        text, ok = QInputDialog.getText(
            self,
            "Telegram login",
            "Enter the one-time code sent to your Telegram app:",
        )
        self._pending_code_future.get_loop().call_soon_thread_safe(
            self._pending_code_future.set_result, text if ok else ""
        )
        self._pending_code_future = None

    def _on_need_password(self) -> None:
        if self._pending_password_future is None:
            return
        text, ok = QInputDialog.getText(
            self,
            "Telegram 2FA",
            "Enter your Cloud Password (2FA):",
            QInputDialog.EchoMode.Password,
        )
        self._pending_password_future.get_loop().call_soon_thread_safe(
            self._pending_password_future.set_result, text if ok else ""
        )
        self._pending_password_future = None

    def _build_layout(self) -> None:
        root_layout = QHBoxLayout()

        # Left: channels
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Channels"))
        left_layout.addWidget(self.add_channel_button)
        left_layout.addWidget(self.channel_list)

        # Right: controls and logs
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.sync_button)
        right_layout.addWidget(QLabel("Messages are saved to the database. View them in the web app (web-app-php)."))
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(QLabel("Logs"))
        right_layout.addWidget(self.log_view)

        root_layout.addLayout(left_layout)
        root_layout.addLayout(right_layout)

        self.setLayout(root_layout)

    def _populate_channels(self) -> None:
        self.channel_list.clear()
        for ch in self._config.channels or []:
            self._add_channel_row(ch)

    def _add_channel_row(self, ch: ChannelConfig) -> None:
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 32))

        checkbox = QCheckBox(ch.username_or_id)
        checkbox.setChecked(ch.enabled)

        remove_btn = QPushButton("🗑")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setFlat(True)
        remove_btn.setStyleSheet(
            "QPushButton { border: none; color: #f97373; font-size: 14px; }"
            "QPushButton:hover { color: #ef4444; }"
        )

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        row_layout.addWidget(checkbox)
        row_layout.addStretch(1)
        row_layout.addWidget(remove_btn)

        self.channel_list.addItem(item)
        self.channel_list.setItemWidget(item, row_widget)

        def _on_remove_clicked() -> None:
            row = self.channel_list.row(item)
            if row >= 0:
                self.channel_list.takeItem(row)

            self._config.channels = [
                cfg for cfg in (self._config.channels or [])
                if cfg.username_or_id != ch.username_or_id
            ]
            self._save_channels_to_file()
            self._append_log(f"Removed channel '{ch.username_or_id}'.")

        remove_btn.clicked.connect(_on_remove_clicked)

    def _on_sync_clicked(self) -> None:
        # Update enabled flags from UI (checkboxes in each row)
        updated_channels: list[ChannelConfig] = []
        for idx in range(self.channel_list.count()):
            item = self.channel_list.item(idx)
            widget = self.channel_list.itemWidget(item)
            if widget is None:
                continue
            checkbox = widget.findChild(QCheckBox)
            if checkbox is None:
                continue
            updated_channels.append(
                ChannelConfig(
                    username_or_id=checkbox.text(),
                    enabled=checkbox.isChecked(),
                )
            )
        self._config.channels = updated_channels
        self._save_channels_to_file()

        self.sync_button.setEnabled(False)
        self._append_log("Triggering sync...")

        self._worker = SyncWorker(self._config, self)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished_with_status.connect(self._on_sync_finished)
        self._worker.need_code.connect(self._on_need_code, Qt.ConnectionType.QueuedConnection)
        self._worker.need_password.connect(self._on_need_password, Qt.ConnectionType.QueuedConnection)
        self._worker.start()

    def _append_log(self, line: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_view.append(f"[{timestamp}] {line}")

    def _on_sync_finished(self, status: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        label = f"Last sync: {timestamp} ({status})"
        self.status_label.setText(label)
        # Persist last sync status so it survives app restarts
        payload = {"last_sync_label": label, "timestamp": timestamp, "status": status}
        try:
            self._last_sync_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Failed to persist last sync status: {exc}")
        self.sync_button.setEnabled(True)

    def _on_add_channel_clicked(self) -> None:
        text, ok = QInputDialog.getText(
            self,
            "Add channel",
            "Enter channel username (without @) or numeric ID:",
        )
        if not ok:
            return
        username_or_id = (text or "").strip()
        if not username_or_id:
            return

        # Prevent duplicates
        for ch in self._config.channels or []:
            if ch.username_or_id == username_or_id:
                self._append_log(f"Channel '{username_or_id}' is already in the list.")
                return

        new_ch = ChannelConfig(username_or_id=username_or_id, enabled=True)
        self._config.channels.append(new_ch)

        self._add_channel_row(new_ch)

        self._save_channels_to_file()
        self._append_log(f"Added channel '{username_or_id}'.")

    def _load_last_sync(self) -> None:
        if not self._last_sync_path.exists():
            return
        try:
            data = json.loads(self._last_sync_path.read_text(encoding="utf-8"))
            label = data.get("last_sync_label")
            if label:
                self.status_label.setText(label)
        except Exception:  # noqa: BLE001
            # Ignore errors and keep default label
            return

    def _save_channels_to_file(self) -> None:
        data = [
            {"username_or_id": ch.username_or_id, "enabled": bool(ch.enabled)}
            for ch in (self._config.channels or [])
        ]
        try:
            self._channels_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"Failed to save channels.json: {exc}")


def run_ui() -> None:
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 500)
    window.show()
    sys.exit(app.exec())


