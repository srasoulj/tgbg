#!/usr/bin/env bash
set -euo pipefail

# This script is meant to be run from the desktop-sync directory.
#
# Requirements:
# - Use the existing Telegram session file under desktop-sync/sessions/
# - Only run when https://www.google.com is reachable

GOOGLE_URL="https://www.google.com"

# Connectivity gate (exactly google.com)
if ! /usr/bin/curl -fsS --max-time 8 "$GOOGLE_URL" >/dev/null; then
  # Quiet success exit so launchd doesn't treat "offline" as a failure.
  exit 0
fi

# Activate venv if present (recommended).
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

exec python -m telegram_sync.cli_sync

