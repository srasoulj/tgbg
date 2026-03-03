## Security risks and mitigations

### Telegram credentials & session security

- **Risk**: API ID/API hash or Telethon session file is stolen from disk.
- **Mitigations**:
  - Store API credentials only in `.env` on the local machine, never in version control.
  - Keep the Telethon session file in a user-only directory (default in this project is `desktop-sync/sessions/`).
  - Protect the workstation with disk encryption and OS user accounts.

### Database credentials & exposure

- **Risk**: MySQL is reachable from the public internet or credentials are leaked.
- **Mitigations**:
  - Restrict MySQL access to trusted IPs or VPN networks.
  - Use strong, unique passwords and a dedicated user for this app.
  - Enable TLS for MySQL (use `DB_SSL_CA` so the desktop app connects securely).
  - Consider separate DB users:
    - one with write access for the desktop sync app,
    - one with read-only access for the web app.

### Injection and untrusted content

- **Risk**: SQL injection or XSS due to Telegram message content.
- **Mitigations**:
  - Always use parameterized queries in Python (MySQL connector) and Eloquent in PHP.
  - In the Laravel views, escape message text (`e($message->text)`) and only convert newlines with `nl2br`.
  - Do not execute or eval any user-supplied text.

### Denial of service / large channels

- **Risk**: Very active channels generate a large number of messages in 48 hours, stressing the DB or UI.
- **Mitigations**:
  - Limit sync window to 48 hours and optionally add a max per-channel message count per sync.
  - Use pagination in the web app (already implemented).
  - Monitor DB size and add indexes as needed (`channel_id, published_at`).

### API endpoint abuse (optional ingestion API)

- **Risk**: If the `/api/messages` endpoint is exposed, attackers could spam messages.
- **Mitigations**:
  - Require a strong API key or better authentication mechanism.
  - Rate-limit the endpoint and log failures.
  - Keep the endpoint on a private network if you do not need public access.

## Scalability improvements

### Read scalability

- Add full-text indexes on `messages.text` if you later need search.
- Add composite indexes for cross-channel views (e.g., `(published_at)` for a global timeline).
- Use DB connection pooling on the Laravel side (default configuration works for most cases).

### Sync scalability

- Parallelize per-channel fetching using asyncio and Telethon if you have many channels.
- Make the sync interval configurable (still manually triggered in the UI, but you can warn about large runs).
- Consider batching `INSERT` statements in Python if you observe latency issues.

### Evolvability

- If direct DB access from the desktop app becomes undesirable, move to the Laravel ingestion API and have the desktop app POST messages instead.
- Add background jobs on the web side to enrich data (e.g., link previews) without changing the sync path.

