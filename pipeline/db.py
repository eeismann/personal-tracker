"""Rebuild SQLite database from all CSV source files."""

import sqlite3
from pathlib import Path

import pandas as pd

from pipeline.config import DB_PATH, RAW_DIR


# Map of table name -> (directory, glob pattern)
CSV_SOURCES = {
    "oura_sleep": ("oura", "sleep_*.csv"),
    "oura_readiness": ("oura", "readiness_*.csv"),
    "oura_activity": ("oura", "activity_*.csv"),
    "apple_health_steps": ("apple_health", "steps_*.csv"),
    "apple_health_workouts": ("apple_health", "workouts_*.csv"),
    "apple_health_sleep": ("apple_health", "sleep_*.csv"),
    "sauna_sessions": ("sauna", "sessions.csv"),
    "work_hours": ("work", "hours_*.csv"),
    "travel_trips": ("travel", "trips.csv"),
    "travel_flights": ("travel", "flights.csv"),
    "weather_daily": ("weather", "daily_*.csv"),
    "mood_energy": ("manual", "mood_energy.csv"),
}


def load_csvs(directory: str, pattern: str, dedup_by_date: bool = True) -> pd.DataFrame:
    """Load and concatenate all CSVs matching a pattern in a directory."""
    source_dir = RAW_DIR / directory
    files = sorted(source_dir.glob(pattern))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_csv(f) for f in files]
    combined = pd.concat(dfs, ignore_index=True)
    if "date" in combined.columns:
        if dedup_by_date:
            combined = combined.drop_duplicates(subset=["date"], keep="last")
        combined = combined.sort_values("date").reset_index(drop=True)
    return combined


def rebuild_db() -> None:
    """Drop and recreate all tables from CSV files."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing DB for clean rebuild
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    total_rows = 0

    # Tables that can have multiple rows per day
    multi_row_tables = {"apple_health_workouts", "sauna_sessions"}

    for table_name, (directory, pattern) in CSV_SOURCES.items():
        df = load_csvs(directory, pattern, dedup_by_date=table_name not in multi_row_tables)
        if df.empty:
            print(f"  [{table_name}] No data found, skipping")
            continue
        df.to_sql(table_name, conn, index=False, if_exists="replace")
        # Add index on date column if it exists
        if "date" in df.columns:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_date ON {table_name}(date)")
        total_rows += len(df)
        print(f"  [{table_name}] {len(df)} rows")

    conn.commit()
    conn.close()
    print(f"  Database rebuilt: {total_rows} total rows -> {DB_PATH}")
