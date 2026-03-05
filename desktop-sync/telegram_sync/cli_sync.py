from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from .config import load_config
from .sync_runner import run_full_sync


def _last_sync_path() -> Path:
    # Keep in sync with UI: desktop-sync/last_sync.json
    return Path(__file__).resolve().parents[1] / "last_sync.json"


def _write_last_sync(status: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"Last sync: {timestamp} ({status})"
    payload = {"last_sync_label": label, "timestamp": timestamp, "status": status}
    _last_sync_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="telegram_sync.cli_sync",
        description="Run one Telegram->DB sync using the existing session (no interactive login).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the sync result as JSON to stdout.",
    )
    args = parser.parse_args(argv)

    cfg = load_config()

    try:
        # Important: do NOT pass code/password callbacks.
        # If the session is not authorized, run_full_sync will fail instead of prompting for login.
        result = asyncio.run(run_full_sync(cfg))
        _write_last_sync("success")
    except Exception as exc:  # noqa: BLE001
        _write_last_sync("error")
        print(f"sync failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        # Keep stdout concise for launchd logs.
        print(
            "sync ok: "
            f"{result.get('channels_processed', 0)} channel(s), "
            f"{result.get('messages_inserted', 0)} inserted, "
            f"{result.get('messages_skipped', 0)} skipped"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

