## Sync algorithm: last 48 hours, idempotent

1. **Load configuration**
   - Read `.env` for Telegram API credentials and MySQL connection details.
   - Read `channels.json` for a list of channel identifiers (`username_or_id`) and enabled flags.

2. **Open MySQL connection**
   - Connect using host, port, user, password, database.
   - If `DB_SSL_CA` is configured, pass it to the MySQL connector so the connection uses TLS.

3. **Create sync log row**
   - Insert into `sync_logs` with:
     - `started_at = NOW()`
     - `status = 'partial'`
   - Store the returned `id` as `sync_id` for later update.

4. **Connect to Telegram**
   - Create a Telethon `TelegramClient` using the configured `session_name`, `api_id`, and `api_hash`.
   - Use a local session file so that login (code + 2FA) is only required on first run.

5. **Prepare time window**
   - Compute `from_datetime = now_utc - 48 hours`.
   - All messages older than `from_datetime` are ignored.

6. **Per-channel processing**
   - For each enabled channel in `channels.json`:
     1. Resolve the channel entity using `client.get_entity(username_or_id)`.
     2. Upsert the `channels` row:
        - Insert or update on `(telegram_id)` and `username`, `title`.
        - Retrieve the local `channels.id` primary key as `channel_id`.
     3. Fetch messages using `client.iter_messages(entity, offset_date=from_datetime, reverse=True)`:
        - This yields messages newer than `from_datetime`, in ascending order.
     4. For each message:
        - Extract:
          - `message_id = msg.id`
          - `text = msg.message` (includes captions for media)
          - `media_url = NULL` for now (can be extended later)
          - `published_at = msg.date` (normalized to UTC)
        - Upsert into `messages` using:
          - `INSERT INTO messages (channel_id, message_id, text, media_url, published_at, synced_at)`
          - `VALUES (..., NOW())`
          - `ON DUPLICATE KEY UPDATE text = VALUES(text), media_url = VALUES(media_url)`
        - If the row was inserted, increment `messages_inserted`; otherwise increment `messages_skipped`.
     5. After the channel loop, increment `channels_processed`.
   - Any per-channel errors (e.g., `RPCError`) mark the overall sync `status` as `'partial'`, and the error is appended to `error_message`.

7. **Finalize sync log**
   - After all channels are processed (or on fatal error):
     - Update the `sync_logs` row with:
       - `finished_at = NOW()`
       - `status` = `'success'`, `'partial'`, or `'error'`
       - `channels_processed`, `messages_inserted`, `messages_skipped`
       - `error_message` (if any)

8. **UI integration**
   - The desktop UI triggers this algorithm via a background worker thread.
   - It disables the Sync button during execution and re-enables it on completion.
   - It shows simple log lines and the last sync time + status to the user.

