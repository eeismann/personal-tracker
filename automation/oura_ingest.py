"""Automated Oura Ring data ingestion.

Fetches the latest Oura data, rebuilds the database, and syncs
tracker.json to the personal website.

Usage:
    python automation/oura_ingest.py
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path so pipeline imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

import os


def main():
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Starting Oura ingest...")

    # 1. Fetch Oura data
    try:
        from pipeline.ingest.oura import OuraIngestor

        OuraIngestor().run()
        print("Oura ingest complete.")
    except Exception as e:
        print(f"Oura ingest failed: {e}")
        return

    # 2. Rebuild database and derived data
    try:
        from pipeline.db import rebuild_db
        from pipeline.transform.merge import run_merge

        rebuild_db()
        run_merge()
        print("Rebuild complete.")
    except Exception as e:
        print(f"Rebuild failed: {e}")
        return

    # 3. Sync tracker.json to personal website
    try:
        src = PROJECT_ROOT / "data" / "derived" / "tracker.json"
        website_path = os.environ.get("PERSONAL_WEBSITE_PATH", "")
        if website_path:
            dest = Path(website_path) / "public" / "data" / "tracker.json"
        else:
            dest = PROJECT_ROOT.parent / "personal-website" / "public" / "data" / "tracker.json"
        shutil.copy2(src, dest)
        print(f"Synced tracker.json to {dest.parent}")
    except Exception as e:
        print(f"Sync failed: {e}")

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Done.")


if __name__ == "__main__":
    main()
