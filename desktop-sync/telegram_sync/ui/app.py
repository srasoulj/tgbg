from __future__ import annotations

if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Allow running as script: python telegram_sync/ui/app.py
    desktop_sync_root = Path(__file__).resolve().parent.parent.parent
    if str(desktop_sync_root) not in sys.path:
        sys.path.insert(0, str(desktop_sync_root))
    from telegram_sync.ui.main_window import run_ui
    run_ui()
else:
    from .main_window import run_ui

