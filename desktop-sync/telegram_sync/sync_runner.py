from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Optional

from telethon import events
from telethon.errors import RPCError, SessionPasswordNeededError

from .config import AppConfig, ChannelConfig, load_config
from .db import create_sync_log, get_connection, upsert_channel, upsert_message, update_sync_log
from .fetch_service import fetch_recent_messages_for_channel
from .telegram_client import get_telegram_client


async def run_full_sync(
    app_config: Optional[AppConfig] = None,
    get_code_callback=None,
    get_password_callback=None,
) -> dict:
    """
    Orchestrate a full sync run:

    - Load config and channel list
    - Open DB connection and create a sync_logs row
    - Connect to Telegram client
    - For each enabled channel:
        - Fetch messages from the last 48 hours
        - Upsert channel row
        - Upsert each message (idempotent via UNIQUE(channel_id, message_id))
    - Update sync_logs with counts and final status
    """
    if app_config is None:
        app_config = load_config()

    channels = [c for c in (app_config.channels or []) if c.enabled]
    if not channels:
        return {"channels_processed": 0, "messages_inserted": 0, "messages_skipped": 0}

    conn = get_connection(
        host=app_config.db_host,
        port=app_config.db_port,
        user=app_config.db_user,
        password=app_config.db_password,
        database=app_config.db_name,
        ssl_ca=app_config.db_ssl_ca,
    )

    sync_id = create_sync_log(conn)
    channels_processed = 0
    messages_inserted = 0
    messages_skipped = 0
    status = "success"
    error_message: Optional[str] = None

    client = get_telegram_client(app_config.session_name, app_config.api_id, app_config.api_hash)

    try:
        async with client:
            # Ensure we are authorized; if not, perform interactive sign-in.
            if not await client.is_user_authorized():
                if get_code_callback is None:
                    raise RuntimeError("Telegram login required but no code callback provided.")

                phone = input("Enter your phone number for Telegram (with country code): ")
                await client.send_code_request(phone)
                code_future = get_code_callback()
                code = await code_future

                try:
                    await client.sign_in(phone=phone, code=code)
                except SessionPasswordNeededError:
                    if get_password_callback is None:
                        raise RuntimeError("Telegram 2FA password required but no password callback provided.")
                    password_future = get_password_callback()
                    password = await password_future
                    await client.sign_in(phone=phone, password=password)

            for channel_cfg in channels:
                try:
                    tg_channel, messages_iter = await fetch_recent_messages_for_channel(
                        client, channel_cfg, hours=48
                    )
                    channel_id = upsert_channel(
                        conn,
                        telegram_id=int(tg_channel.id),
                        username=getattr(tg_channel, "username", None),
                        title=getattr(tg_channel, "title", str(channel_cfg.username_or_id)),
                    )

                    async for msg in messages_iter:
                        if not msg:
                            continue
                        if not hasattr(msg, "id"):
                            continue

                        # Text: prefer message.text; for media, Telethon puts caption into .message
                        text = msg.message or ""

                        # For now we do not download media; media_url can be extended later.
                        media_url = None

                        published_at = msg.date
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)

                        inserted = upsert_message(
                            conn,
                            channel_id=channel_id,
                            message_id=int(msg.id),
                            text=text,
                            media_url=media_url,
                            published_at=published_at,
                        )
                        if inserted:
                            messages_inserted += 1
                        else:
                            messages_skipped += 1

                    channels_processed += 1
                except RPCError as e:
                    status = "partial"
                    if error_message is None:
                        error_message = f"Error syncing channel {channel_cfg.username_or_id}: {e}"
                except Exception as e:  # noqa: BLE001
                    status = "partial"
                    tb = traceback.format_exc()
                    if error_message is None:
                        error_message = f"Unexpected error for channel {channel_cfg.username_or_id}: {e}\n{tb}"

    except Exception as e:  # noqa: BLE001
        status = "error"
        tb = traceback.format_exc()
        error_message = f"Fatal error during sync: {e}\n{tb}"
    finally:
        update_sync_log(
            conn,
            sync_id=sync_id,
            status=status,
            channels_processed=channels_processed,
            messages_inserted=messages_inserted,
            messages_skipped=messages_skipped,
            error_message=error_message,
        )
        conn.close()

    return {
        "channels_processed": channels_processed,
        "messages_inserted": messages_inserted,
        "messages_skipped": messages_skipped,
    }

