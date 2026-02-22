"""Google Calendar ingestor — pulls work hours from a Google Sheet populated by Apps Script."""

import os
import re
from datetime import date
from io import StringIO

import httpx
import pandas as pd

from pipeline.config import RAW_DIR
from pipeline.ingest.base import BaseIngestor


class GoogleCalendarIngestor(BaseIngestor):
    source_name = "work"

    def __init__(self):
        self.sheet_url = os.environ.get("GOOGLE_SHEET_URL", "")
        if not self.sheet_url:
            raise ValueError(
                "GOOGLE_SHEET_URL not set in environment. Add it to .env\n"
                "Format: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/..."
            )
        # Extract spreadsheet ID from URL
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", self.sheet_url)
        if not match:
            raise ValueError(f"Could not extract spreadsheet ID from URL: {self.sheet_url}")
        self.spreadsheet_id = match.group(1)

    def _get_csv_export_url(self) -> str:
        """Build the public CSV export URL for the work_hours sheet."""
        return (
            f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
            f"/gviz/tq?tqx=out:csv&sheet=work_hours"
        )

    def fetch(self, start_date: date, end_date: date) -> dict:
        """Download the Google Sheet as CSV."""
        url = self._get_csv_export_url()
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        return {"csv_text": resp.text}

    def transform(self, raw_data: dict) -> dict[str, pd.DataFrame]:
        """Parse the CSV and extract work hours columns."""
        csv_text = raw_data["csv_text"]
        df = pd.read_csv(StringIO(csv_text))

        if df.empty:
            return {"hours": pd.DataFrame()}

        # Keep only the columns we care about
        keep_cols = [
            "date", "first_event_time", "last_event_time",
            "total_work_hr", "meeting_count", "meeting_hr", "focus_hr",
        ]
        available = [c for c in keep_cols if c in df.columns]
        df = df[available].copy()

        # Ensure date format
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        return {"hours": df}
