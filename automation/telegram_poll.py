"""Poll Telegram bot for Apple Health JSON exports and trigger ingest.

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env.
Persists the last processed update_id to automation/telegram_offset.json.

Usage:
    python automation/telegram_poll.py          # poll once
    python automation/telegram_poll.py --watch   # poll every 60s
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Ensure project root is on sys.path so pipeline imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

import os

from pipeline.config import RAW_DIR

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
OFFSET_FILE = Path(__file__).resolve().parent / "telegram_offset.json"
DOWNLOAD_DIR = RAW_DIR / "apple_health"


def _load_offset() -> int:
    """Load the last processed update_id."""
    if OFFSET_FILE.exists():
        data = json.loads(OFFSET_FILE.read_text())
        return data.get("offset", 0)
    return 0


def _save_offset(offset: int) -> None:
    """Persist the next update_id to fetch."""
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


def poll_once() -> int:
    """Poll for new messages, download JSON files, run ingest. Returns count of files processed."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        return 0
    if not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_CHAT_ID not set in .env")
        return 0

    offset = _load_offset()
    updates = _get_updates(TELEGRAM_BOT_TOKEN, offset)

    if not updates:
        print("No new messages.")
        return 0

    downloaded = []
    max_update_id = offset

    for update in updates:
        update_id = update["update_id"]
        max_update_id = max(max_update_id, update_id)

        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))

        # Only process messages from our configured chat
        if chat_id != TELEGRAM_CHAT_ID:
            continue

        doc = msg.get("document")
        text = msg.get("text", "")

        if doc:
            # File attachment — download .json files
            file_name = doc.get("file_name", "")
            if not file_name.endswith(".json"):
                continue

            file_id = doc["file_id"]
            dest = DOWNLOAD_DIR / file_name
            print(f"Downloading {file_name}...")

            try:
                _download_file(TELEGRAM_BOT_TOKEN, file_id, dest)
                downloaded.append(dest)
                print(f"  Saved to {dest}")
            except Exception as e:
                print(f"  Failed to download {file_name}: {e}")

        elif text.lstrip().startswith("{"):
            # Text message that looks like JSON (from old app version)
            try:
                json.loads(text)  # validate it's real JSON
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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Poll Telegram for health exports")
    parser.add_argument("--watch", action="store_true", help="Poll continuously every 60 seconds")
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
            time.sleep(60)
    else:
        poll_once()


if __name__ == "__main__":
    main()
