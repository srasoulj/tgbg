## tgbg – Telegram to DB and Browser

tgbg is a small system that:
- **Syncs messages from Telegram channels into MySQL** using a desktop app.
- **Displays synced messages in a browser** using a lightweight Go web app.

This document explains how to run both parts locally.

---

## Prerequisites

- **Python 3.10+** (for the desktop sync app)
- **Go 1.21+** (for the web app)
- **MySQL 8.x** (or compatible) running locally or remotely
- **Telegram API credentials** (API ID and API hash from `https://my.telegram.org`)

---

## 1. Database setup

1. Create a MySQL database (for example `telegram_reader`) and user:

```sql
CREATE DATABASE telegram_reader CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tgbg'@'%' IDENTIFIED BY 'your_db_password_here';
GRANT ALL PRIVILEGES ON telegram_reader.* TO 'tgbg'@'%';
FLUSH PRIVILEGES;
```

2. Apply the schema from `schema.sql` (if present in the repo) or your own equivalent schema defining at least:
   - `channels` table
   - `messages` table
   - `sync_logs` table

---

## 2. Desktop sync app (Python + Qt)

The desktop app lives in `desktop-sync` and:
- Connects to Telegram via Telethon.
- Syncs the **last 48 hours** of messages for enabled channels into MySQL.
- Can be run as a simple GUI to trigger syncs.

### 2.1. Configure environment

From the repo root:

```bash
cd desktop-sync
cp .env.example .env  # if you have an example file; otherwise create .env
```

Edit `.env` and set:
- **Telegram**:
  - `TG_API_ID`
  - `TG_API_HASH`
  - `TG_SESSION_NAME` (local session file name, e.g. `tgbg-session`)
- **Database**:
  - `DB_HOST`
  - `DB_PORT`
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_SSL_CA` (optional, for TLS)

Also make sure `channels.json` exists with content like:

```json
[
  { "username_or_id": "some_public_channel", "enabled": true },
  { "username_or_id": "another_channel", "enabled": false }
]
```

Only channels with `"enabled": true` are processed.

### 2.2. Create virtual environment and install dependencies

```bash
cd desktop-sync
python -m venv .venv
.\.venv\Scripts\activate  # on Windows
# source .venv/bin/activate  # on macOS/Linux
pip install -r requirements.txt
```

(If `requirements.txt` is missing, install at least `telethon`, `PySide6`, and `mysql-connector-python` or the DB driver used in the code.)

### 2.3. Run the desktop app

From inside `desktop-sync` with the virtualenv activated:

```bash
python -m telegram_sync.ui.app
```

The first run will:
- Ask for your **phone number** in the console.
- Open a **code prompt** in the GUI when Telegram sends you a one‑time code.
- If your account has **2FA enabled**, the GUI will also ask for your Telegram cloud password.

Once authorized:
- Choose which channels are enabled in the GUI.
- Click **Sync** to run a sync. Progress and summary (channels processed, messages inserted/skipped) are shown in the log area.

---

## 3. Web app (Go)

The Go web app in `web-app-go` reads from the same MySQL database and exposes:
- `/` – list of channels
- `/channels?id=<channel_id>&page=<n>` – paginated messages for a channel

### 3.1. Configure environment

The Go app reads DB settings from environment variables:

- `DB_HOST` (default: `localhost`)
- `DB_PORT` (default: `3306`)
- `DB_NAME` (default: `telegram_reader`)
- `DB_USER` (default: `tgbg`)
- `DB_PASSWORD` (default: empty)

You can create a small `.env` or export variables in your shell, for example:

```bash
set DB_HOST=localhost
set DB_PORT=3306
set DB_NAME=telegram_reader
set DB_USER=tgbg
set DB_PASSWORD=your_db_password_here
```

### 3.2. Run the Go web app

From the repo root:

```bash
cd web-app-go
go run ./...
```

By default it listens on `http://localhost:8080`.

Open that URL in a browser to:
- See all synced channels.
- Click a channel to browse messages with pagination.

---

## 4. Typical local workflow

1. **Start MySQL** and ensure the schema is applied.
2. **Run the desktop sync app** (`desktop-sync`) to pull recent messages from Telegram into MySQL.
3. **Run the Go web app** (`web-app-go`) to browse synced messages in the browser.

---

## 5. Deploying the Go web app to a server

This is a minimal example of running the Go app on a Linux server (e.g. Ubuntu) behind a reverse proxy.

### 5.1. Prepare the server

- Install **Go** and **MySQL client libraries** (or ensure network access to your DB).
- Clone the repo onto the server, for example into `/opt/tgbg`.
- Ensure the server can reach your MySQL instance (same network / security group / firewall rules).

### 5.2. Configure environment on the server

On the server, set the same DB env vars used locally, but pointing to your production DB:

```bash
export DB_HOST=your-db-hostname-or-ip
export DB_PORT=3306
export DB_NAME=telegram_reader
export DB_USER=tgbg
export DB_PASSWORD=your_strong_prod_password
```

You can keep these in a file like `/etc/tgbg.env` and load them from your service manager (systemd, docker, etc.).

### 5.3. Run as a systemd service (example)

Create a unit file `/etc/systemd/system/tgbg-web.service`:

```ini
[Unit]
Description=tgbg Go web app
After=network.target

[Service]
Type=simple
EnvironmentFile=/etc/tgbg.env
WorkingDirectory=/opt/tgbg/web-app-go
ExecStart=/usr/local/bin/go run ./...
Restart=on-failure
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tgbg-web
sudo systemctl start tgbg-web
```

By default the app listens on `:8080`. You can:
- Expose port `8080` directly, or
- Put Nginx/Apache/another reverse proxy in front and proxy requests to `http://127.0.0.1:8080`.

### 5.4. Reverse proxy with Nginx (very short example)

```nginx
server {
    listen 80;
    server_name your-domain.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Reload Nginx and you should be able to reach the app at `http://your-domain.example.com/`.

---

## 6. Deploying when the server cannot access GitHub

Sometimes your Linux server cannot reach GitHub (firewall, no outbound internet, etc.). In that case you can still deploy from your **local laptop** over SSH in two ways.

### 6.1. Option A – copy files with `scp` (simplest)

1. **Prepare a directory on the server (once)**

   SSH into the server as `root` (or another user) and create a deployment folder, for example:

   ```bash
   mkdir -p /var/www/tgbg
   ```

2. **From your laptop, upload the app code**

   From the repo root on your laptop:

   ```bash
   # Copy only the relevant subfolders to the server
   scp -r web-app-go desktop-sync root@api.amoozal.com:/var/www/tgbg
   ```

   - Adjust the destination path if you prefer a different folder.
   - Do **not** upload `.venv`, `.env`, `sessions`, `__pycache__`, etc. – they should stay local and/or be recreated on the server.

3. **Run the Go web app on the server**

   ```bash
   ssh root@api.amoozal.com
   cd /var/www/tgbg/web-app-go
   go run ./...
   ```

   Once this works, you can turn it into a systemd service as shown in section **5.3** so it runs in the background.

### 6.2. Option B – use the server as a bare Git remote (no GitHub needed)

This option gives you a nicer workflow: you `git push` from your laptop directly to the server, even if the server cannot reach GitHub.

1. **Create a bare repo on the server (once)**

   ```bash
   ssh root@api.amoozal.com
   mkdir -p /opt/git/tgbg.git
   cd /opt/git/tgbg.git
   git init --bare
   ```

2. **Add a `production` remote on your laptop**

   From the repo root on your laptop:

   ```bash
   git remote add production root@api.amoozal.com:/opt/git/tgbg.git
   git push production main   # or your current branch
   ```

3. **Check out a working copy on the server**

   ```bash
   ssh root@api.amoozal.com
   mkdir -p /var/www/tgbg
   cd /var/www/tgbg
   git clone /opt/git/tgbg.git .
   ```

4. **Deploy updates**

   - On your laptop, commit your changes and run:

   ```bash
   git push production main
   ```

   - On the server:

   ```bash
   cd /var/www/tgbg
   git pull
   sudo systemctl restart tgbg-web   # if you use the systemd service from section 5.3
   ```

This way the **source of truth** is still your local git repo (and optionally GitHub), but the server gets updates by pulling from the bare repo that lives on the same machine.

---

## 7. Connecting the desktop app to a remote SQL server

The desktop app talks to MySQL using the values from `desktop-sync/.env`.

To point it at a remote MySQL server instead of localhost:

1. **On the MySQL server**
   - Ensure MySQL is listening on a network interface accessible from your desktop (for example `0.0.0.0:3306` or a private IP).
   - Open the firewall / security group for TCP **port 3306** from your desktop’s IP or VPN network.
   - Create a user that can connect from your desktop’s IP or `%`:

```sql
CREATE USER 'tgbg'@'%' IDENTIFIED BY 'your_db_password_here';
GRANT ALL PRIVILEGES ON telegram_reader.* TO 'tgbg'@'%';
FLUSH PRIVILEGES;
```

2. **In `desktop-sync/.env` on your machine**
   - Set:

```env
DB_HOST=your-remote-db-hostname-or-ip
DB_PORT=3306
DB_NAME=telegram_reader
DB_USER=tgbg
DB_PASSWORD=your_db_password_here
```

   - If you require TLS, also configure `DB_SSL_CA` to point to the CA file provided by your hosting/cloud provider.

3. **Run the desktop app as usual**
   - Activate the virtualenv in `desktop-sync`.
   - Start the app with `python -m telegram_sync.ui.app`.

The sync UI will now read and write data against the **remote** MySQL instance, and your deployed Go web app can read from the same database.

---

## 8. Notes

- The Telegram login uses a local session file, so you only need to enter the code/2FA password on first run or when the session expires.
- The sync algorithm is described in more detail in `desktop-sync/sync-algorithm.md`.
- Treat `.env`, `channels.json`, session files and `.venv` as **local development artifacts** and do not commit them to git.

