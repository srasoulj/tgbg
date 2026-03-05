#!/usr/bin/env bash
set -euo pipefail

# Same as run_sync_if_online.sh, but intended for launchd execution.
# Connectivity gate must check exactly https://www.google.com

GOOGLE_URL="https://www.google.com"

if ! /usr/bin/curl -fsS --max-time 8 "$GOOGLE_URL" >/dev/null; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') offline: google.com unreachable"
  exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') online: starting sync"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" -m telegram_sync.cli_sync
fi

exec /usr/bin/python3 -m telegram_sync.cli_sync

