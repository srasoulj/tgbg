from __future__ import annotations

from pathlib import Path

from telethon import TelegramClient


def get_telegram_client(session_name: str, api_id: int, api_hash: str) -> TelegramClient:
    """
    Create and return a connected Telethon client.

    The first run will be interactive, asking the user for the login code and 2FA
    password in the console. Subsequent runs reuse the local session file.
    """
    session_dir = Path.cwd() / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_path = session_dir / session_name

    client = TelegramClient(str(session_path), api_id, api_hash)
    return client

