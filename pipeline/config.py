from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root
ROOT = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DERIVED_DIR = DATA_DIR / "derived"
RAW_CACHE_DIR = DATA_DIR / "raw_cache"

# Database
DB_PATH = DERIVED_DIR / "tracker.db"

# Output files
DAILY_SUMMARY_CSV = DERIVED_DIR / "daily_summary.csv"
WEEKLY_SUMMARY_CSV = DERIVED_DIR / "weekly_summary.csv"
TRACKER_JSON = DERIVED_DIR / "tracker.json"

# Dashboard public data
DASHBOARD_DATA_DIR = ROOT / "dashboard" / "public" / "data"
