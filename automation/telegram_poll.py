"""Poll Telegram bot for Apple Health JSON exports and trigger ingest.

Reads TELEGRAM_BOT_TOKEN and chat/user allowlists from .env.
Persists the last processed update_id to data/state/telegram_offset.json.

Usage:
    python automation/telegram_poll.py           # poll once
    python automation/telegram_poll.py --watch   # poll every 60s

Multi-machine notes:
- Keep machine-specific secrets in each machine's local `.env`.
- You can allow one or many chats via TELEGRAM_CHAT_ID / TELEGRAM_CHAT_IDS.
- Optionally constrain sender identity via TELEGRAM_ALLOWED_USER_IDS / TELEGRAM_ALLOWED_USERNAMES.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import httpx
from dotenv import load_dotenv

# Ensure project root is on sys.path so pipeline imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Always load .env from project root (portable across cwd/launchd)
load_dotenv(PROJECT_ROOT / ".env")

from pipeline.config import RAW_DIR

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Single or comma-separated chat IDs
_CHAT_IDS_RAW = ",".join(
    [
        os.environ.get("TELEGRAM_CHAT_ID", ""),
        os.environ.get("TELEGRAM_CHAT_IDS", ""),
    ]
)
ALLOWED_CHAT_IDS = {s.strip() for s in _CHAT_IDS_RAW.split(",") if s.strip()}

# Optional sender allowlists (recommended for group chats)
_ALLOWED_USER_IDS_RAW = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = {s.strip() for s in _ALLOWED_USER_IDS_RAW.split(",") if s.strip()}

_ALLOWED_USERNAMES_RAW = os.environ.get("TELEGRAM_ALLOWED_USERNAMES", "")
ALLOWED_USERNAMES = {s.strip().lstrip("@").lower() for s in _ALLOWED_USERNAMES_RAW.split(",") if s.strip()}

OFFSET_FILE = PROJECT_ROOT / "data" / "state" / "telegram_offset.json"
DOWNLOAD_DIR = RAW_DIR / "apple_health"


def _load_offset() -> int:
    """Load the last processed update_id."""
    if OFFSET_FILE.exists():
        data = json.loads(OFFSET_FILE.read_text())
        return int(data.get("offset", 0))
    return 0


def _save_offset(offset: int) -> None:
    """Persist the next update_id to fetch."""
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(json.dumps({"offset": offset}))


def _get_updates(token: str, offset: int, long_poll: bool = False) -> list[dict]:
    """Call Telegram getUpdates. Uses short polling by default to avoid 409 conflicts."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    poll_timeout = 30 if long_poll else 0
    params = {"offset": offset, "timeout": poll_timeout}
    resp = httpx.get(url, params=params, timeout=poll_timeout + 15)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data.get("result", [])


def _download_file(token: str, file_id: str, dest: Path) -> Path:
    """Download a file from Telegram by file_id."""
    # Get file path from Telegram
    url = f"https://api.telegram.org/bot{token}/getFile"
    resp = httpx.get(url, params={"file_id": file_id}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"getFile failed: {data}")
    file_path = data["result"]["file_path"]

    # Download the file
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    resp = httpx.get(download_url, timeout=60)
    resp.raise_for_status()

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return dest


def _is_allowed_sender(msg: dict) -> bool:
    """Validate sender if allowlists are provided."""
    if not ALLOWED_USER_IDS and not ALLOWED_USERNAMES:
        return True

    sender = msg.get("from", {})
    sender_id = str(sender.get("id", ""))
    sender_username = str(sender.get("username", "")).lower()

    if ALLOWED_USER_IDS and sender_id in ALLOWED_USER_IDS:
        return True
    if ALLOWED_USERNAMES and sender_username in ALLOWED_USERNAMES:
        return True
    return False


def _is_allowed_chat(chat_id: str) -> bool:
    """Validate chat id if allowlist is configured."""
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS


def _safe_filename(name: str | None) -> str:
    if not name:
        return "health-export.json"
    base = Path(name).name
    return base.replace(" ", "_")


def _looks_like_health_json(data: dict) -> bool:
    # Accept known HealthExport shape without being too strict.
    keys = set(data.keys())
    return bool({"workouts", "dailySummary", "samples", "exportDate"} & keys)


def poll_once() -> int:
    """Poll for new messages, download JSON files, run ingest. Returns count of files processed."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        return 0

    offset = _load_offset()
    updates = _get_updates(TELEGRAM_BOT_TOKEN, offset)

    if not updates:
        print("No new messages.")
        return 0

    downloaded: list[Path] = []
    max_update_id = offset

    for update in updates:
        update_id = update["update_id"]
        max_update_id = max(max_update_id, update_id)

        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not _is_allowed_chat(chat_id):
            continue
        if not _is_allowed_sender(msg):
            continue

        doc = msg.get("document")
        text = msg.get("text", "")

        if doc:
            # File attachment — download .json files (by extension or MIME)
            file_name = _safe_filename(doc.get("file_name"))
            mime = str(doc.get("mime_type", "")).lower()
            if not (file_name.lower().endswith(".json") or mime == "application/json"):
                continue

            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            dest = DOWNLOAD_DIR / f"{timestamp}-{file_name}"
            file_id = doc["file_id"]
            print(f"Downloading {file_name}...")

            try:
                _download_file(TELEGRAM_BOT_TOKEN, file_id, dest)
                # Validate JSON parseability
                payload = json.loads(dest.read_text())
                if not _looks_like_health_json(payload):
                    print(f"  Skipping {dest.name}: does not look like health export payload")
                    dest.unlink(missing_ok=True)
                    continue
                downloaded.append(dest)
                print(f"  Saved to {dest}")
            except Exception as e:
                print(f"  Failed to download {file_name}: {e}")

        elif text.lstrip().startswith("{"):
            # Text message that looks like JSON
            try:
                payload = json.loads(text)
                if not _looks_like_health_json(payload):
                    continue
            except json.JSONDecodeError:
                continue

            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            dest = DOWNLOAD_DIR / f"health-export-{timestamp}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
            downloaded.append(dest)
            print(f"  Saved text JSON to {dest}")

    # Advance offset past all processed updates
    _save_offset(max_update_id + 1)

    if not downloaded:
        print("No new health export files found.")
        return 0

    # Run ingest and rebuild
    print(f"\nProcessing {len(downloaded)} file(s)...")
    try:
        from pipeline.ingest.apple_health import AppleHealthIngestor

        AppleHealthIngestor().run()
        print("Ingest complete.")
    except Exception as e:
        print(f"Ingest failed: {e}")
        return len(downloaded)

    try:
        from pipeline.db import rebuild_db
        from pipeline.transform.merge import run_merge

        rebuild_db()
        run_merge()
        print("Rebuild complete.")
    except Exception as e:
        print(f"Rebuild failed: {e}")

    return len(downloaded)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Poll Telegram for health exports")
    parser.add_argument("--watch", action="store_true", help="Poll continuously every 60 seconds")
    parser.add_argument("--interval", type=int, default=60, help="Watch mode interval in seconds")
    args = parser.parse_args()

    if args.watch:
        print("Watching for Telegram messages (Ctrl+C to stop)...")
        while True:
            try:
                poll_once()
            except KeyboardInterrupt:
                print("\nStopped.")
                break
            except Exception as e:
                print(f"Poll error: {e}")
            time.sleep(max(5, args.interval))
    else:
        poll_once()


if __name__ == "__main__":
    main()
