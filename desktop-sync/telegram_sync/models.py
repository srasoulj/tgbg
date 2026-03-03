from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Channel:
    id: int
    telegram_id: int
    username: Optional[str]
    title: str


@dataclass
class MessageRecord:
    channel_id: int
    message_id: int
    text: Optional[str]
    media_url: Optional[str]
    published_at: datetime


