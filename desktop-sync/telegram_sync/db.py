from __future__ import annotations

from datetime import datetime
from typing import Optional

import mysql.connector
from mysql.connector import MySQLConnection


def get_connection(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    ssl_ca: Optional[str] = None,
) -> MySQLConnection:
    kwargs: dict = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }
    if ssl_ca:
        kwargs["ssl_ca"] = ssl_ca

    return mysql.connector.connect(**kwargs)


def upsert_channel(conn: MySQLConnection, telegram_id: int, username: Optional[str], title: str) -> int:
    """
    Ensure a channel row exists and return its local ID.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channels (telegram_id, username, title)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
              username = VALUES(username),
              title = VALUES(title)
            """,
            (telegram_id, username, title),
        )
        if cur.lastrowid:
            channel_id = cur.lastrowid
        else:
            cur.execute("SELECT id FROM channels WHERE telegram_id = %s", (telegram_id,))
            row = cur.fetchone()
            channel_id = int(row[0])
    conn.commit()
    return channel_id


def upsert_message(
    conn: MySQLConnection,
    channel_id: int,
    message_id: int,
    text: Optional[str],
    media_url: Optional[str],
    published_at: datetime,
) -> bool:
    """
    Insert or update a message.

    Returns True if a new row was inserted, False if it was an update/duplicate.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages (channel_id, message_id, text, media_url, published_at, synced_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
              text = VALUES(text),
              media_url = VALUES(media_url)
            """,
            (channel_id, message_id, text, media_url, published_at),
        )
        inserted = cur.rowcount == 1 and cur.lastrowid is not None
    conn.commit()
    return inserted


def create_sync_log(conn: MySQLConnection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sync_logs (started_at, status)
            VALUES (NOW(), 'partial')
            """
        )
        sync_id = int(cur.lastrowid)
    conn.commit()
    return sync_id


def update_sync_log(
    conn: MySQLConnection,
    sync_id: int,
    status: str,
    channels_processed: int,
    messages_inserted: int,
    messages_skipped: int,
    error_message: Optional[str] = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sync_logs
            SET finished_at = NOW(),
                status = %s,
                channels_processed = %s,
                messages_inserted = %s,
                messages_skipped = %s,
                error_message = %s
            WHERE id = %s
            """,
            (status, channels_processed, messages_inserted, messages_skipped, error_message, sync_id),
        )
    conn.commit()


def get_last_message_published_for_telegram(
    conn: MySQLConnection,
    telegram_id: int,
) -> Optional[datetime]:
    """
    Return the most recent published_at for messages in a channel
    identified by its Telegram ID, or None if no messages exist yet.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT MAX(m.published_at)
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE c.telegram_id = %s
            """,
            (telegram_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return row[0]

