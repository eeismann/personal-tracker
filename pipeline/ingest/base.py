"""Abstract base class for all data source ingestors."""

import abc
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from pipeline.config import RAW_DIR


class BaseIngestor(abc.ABC):
    """Base class every data source ingestor extends."""

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Directory name under data/raw/ (e.g. 'oura', 'apple_health')."""

    @property
    def raw_dir(self) -> Path:
        return RAW_DIR / self.source_name

    @abc.abstractmethod
    def fetch(self, start_date: date, end_date: date) -> dict:
        """Pull raw data from the source. Returns raw API/file data."""

    @abc.abstractmethod
    def transform(self, raw_data: dict) -> dict[str, pd.DataFrame]:
        """Normalize raw data into DataFrames keyed by CSV name prefix."""

    def get_last_date(self, csv_pattern: str) -> date | None:
        """Read the last ingested date from existing CSV files matching pattern."""
        files = sorted(self.raw_dir.glob(csv_pattern))
        if not files:
            return None
        df = pd.read_csv(files[-1])
        if df.empty or "date" not in df.columns:
            return None
        return date.fromisoformat(df["date"].iloc[-1])

    def append_to_csv(self, df: pd.DataFrame, filepath: Path) -> None:
        """Deduplicate by date and append new rows to a CSV file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if filepath.exists():
            existing = pd.read_csv(filepath)
            combined = pd.concat([existing, df], ignore_index=True)
            if "date" in combined.columns:
                combined = combined.drop_duplicates(subset=["date"], keep="last")
                combined = combined.sort_values("date").reset_index(drop=True)
        else:
            combined = df

        combined.to_csv(filepath, index=False)

    def save(self, dataframes: dict[str, pd.DataFrame]) -> None:
        """Write each DataFrame to its year-partitioned CSV."""
        for prefix, df in dataframes.items():
            if df.empty:
                continue
            df["date"] = pd.to_datetime(df["date"]).dt.date
            for year, year_df in df.groupby(df["date"].apply(lambda d: d.year)):
                year_df = year_df.copy()
                year_df["date"] = year_df["date"].astype(str)
                filepath = self.raw_dir / f"{prefix}_{year}.csv"
                self.append_to_csv(year_df, filepath)

    def run(self, start_date: date | None = None, end_date: date | None = None) -> None:
        """Orchestrate: determine date range, fetch, transform, save."""
        if end_date is None:
            end_date = date.today() - timedelta(days=1)

        if start_date is None:
            # Try incremental: start from day after last ingested
            last = self.get_last_date(f"*_*.csv")
            if last:
                start_date = last + timedelta(days=1)
            else:
                # Default: last 90 days for first run
                start_date = end_date - timedelta(days=90)

        if start_date > end_date:
            print(f"[{self.source_name}] Already up to date (last: {start_date - timedelta(days=1)})")
            return

        print(f"[{self.source_name}] Fetching {start_date} to {end_date}")
        raw_data = self.fetch(start_date, end_date)

        print(f"[{self.source_name}] Transforming data")
        dataframes = self.transform(raw_data)

        row_count = sum(len(df) for df in dataframes.values())
        print(f"[{self.source_name}] Saving {row_count} rows")
        self.save(dataframes)
        print(f"[{self.source_name}] Done")
