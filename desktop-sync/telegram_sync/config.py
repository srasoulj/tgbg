from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


@dataclass
class ChannelConfig:
    username_or_id: str
    enabled: bool = True


@dataclass
class AppConfig:
    api_id: int
    api_hash: str
    session_name: str

    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    db_ssl_ca: str | None = None

    channels: List[ChannelConfig] | None = None


def load_config(base_dir: Path | None = None) -> AppConfig:
    """
    Load configuration from .env and channels.json.

    Expected .env variables:
      TELEGRAM_API_ID
      TELEGRAM_API_HASH
      TELEGRAM_SESSION_NAME
      DB_HOST
      DB_PORT
      DB_USER
      DB_PASSWORD
      DB_NAME
      DB_SSL_CA (optional)

    Channel configuration is stored in channels.json next to this file:
      [
        { "username_or_id": "some_channel", "enabled": true }
      ]
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    # Load .env from desktop-sync root if present
    project_root = base_dir.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session_name = os.environ.get("TELEGRAM_SESSION_NAME", "telegram_sync_session")

    db_host = os.environ["DB_HOST"]
    db_port = int(os.environ.get("DB_PORT", "3306"))
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]
    db_name = os.environ["DB_NAME"]
    db_ssl_ca = os.environ.get("DB_SSL_CA") or None

    channels_path = project_root / "channels.json"
    channels: List[ChannelConfig] = []
    if channels_path.exists():
        data = json.loads(channels_path.read_text(encoding="utf-8"))
        for item in data:
            channels.append(
                ChannelConfig(
                    username_or_id=item["username_or_id"],
                    enabled=bool(item.get("enabled", True)),
                )
            )

    return AppConfig(
        api_id=api_id,
        api_hash=api_hash,
        session_name=session_name,
        db_host=db_host,
        db_port=db_port,
        db_user=db_user,
        db_password=db_password,
        db_name=db_name,
        db_ssl_ca=db_ssl_ca,
        channels=channels,
    )

