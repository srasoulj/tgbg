from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Tuple

from telethon.tl.custom.message import Message
from telethon.tl.types import Channel as TgChannel

from .config import ChannelConfig


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def fetch_recent_messages_for_channel(
    client,
    channel_cfg: ChannelConfig,
    hours: int = 48,
) -> Tuple[TgChannel, Iterable[Message]]:
    """
    Fetch messages from the last `hours` hours for a single channel.

    Returns a tuple of (resolved_channel_entity, iterable_of_messages).
    """
    from_datetime = _now_utc() - timedelta(hours=hours)

    entity = await client.get_entity(channel_cfg.username_or_id)

    messages_iter = client.iter_messages(
        entity,
        offset_date=from_datetime,
        reverse=True,
    )

    return entity, messages_iter

