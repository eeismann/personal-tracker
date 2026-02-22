"""Oura Ring API v2 ingestor for sleep, readiness, and activity data."""

import json
import os
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

from pipeline.config import RAW_CACHE_DIR
from pipeline.ingest.base import BaseIngestor

OURA_BASE_URL = "https://api.ouraring.com/v2/usercollection"


class OuraIngestor(BaseIngestor):
    source_name = "oura"

    def __init__(self):
        self.token = os.environ.get("OURA_TOKEN", "")
        if not self.token:
            raise ValueError("OURA_TOKEN not set in environment. Add it to .env")
        self.client = httpx.Client(
            base_url=OURA_BASE_URL,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )
        self.cache_dir = RAW_CACHE_DIR / "oura"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_endpoint(self, endpoint: str, start: date, end: date) -> list[dict]:
        """Fetch paginated data from an Oura API endpoint."""
        all_data = []
        params = {"start_date": str(start), "end_date": str(end)}

        while True:
            resp = self.client.get(f"/{endpoint}", params=params)
            resp.raise_for_status()
            body = resp.json()
            all_data.extend(body.get("data", []))
            next_token = body.get("next_token")
            if not next_token:
                break
            params["next_token"] = next_token

        return all_data

    def _cache_raw(self, name: str, data: list[dict], start: date, end: date) -> None:
        """Cache raw JSON response for debugging."""
        path = self.cache_dir / f"{name}_{start}_{end}.json"
        path.write_text(json.dumps(data, indent=2, default=str))

    def fetch(self, start_date: date, end_date: date) -> dict:
        endpoints = ["daily_sleep", "daily_readiness", "daily_activity"]
        raw = {}
        for ep in endpoints:
            data = self._fetch_endpoint(ep, start_date, end_date)
            self._cache_raw(ep, data, start_date, end_date)
            raw[ep] = data
        return raw

    def transform(self, raw_data: dict) -> dict[str, pd.DataFrame]:
        return {
            "sleep": self._transform_sleep(raw_data.get("daily_sleep", [])),
            "readiness": self._transform_readiness(raw_data.get("daily_readiness", [])),
            "activity": self._transform_activity(raw_data.get("daily_activity", [])),
        }

    def _transform_sleep(self, data: list[dict]) -> pd.DataFrame:
        rows = []
        for item in data:
            contributors = item.get("contributors", {})
            rows.append({
                "date": item.get("day"),
                "score": item.get("score"),
                "total_sleep_min": item.get("total_sleep_duration", 0) // 60 if item.get("total_sleep_duration") else None,
                "deep_min": item.get("deep_sleep_duration", 0) // 60 if item.get("deep_sleep_duration") else None,
                "rem_min": item.get("rem_sleep_duration", 0) // 60 if item.get("rem_sleep_duration") else None,
                "light_min": item.get("light_sleep_duration", 0) // 60 if item.get("light_sleep_duration") else None,
                "awake_min": item.get("awake_time", 0) // 60 if item.get("awake_time") else None,
                "efficiency": contributors.get("efficiency"),
                "hr_lowest": item.get("lowest_heart_rate"),
                "hr_average": None,  # Not directly in daily_sleep
                "hrv_average": None,  # Available in sleep periods, not daily
                "breath_average": None,
            })
        return pd.DataFrame(rows)

    def _transform_readiness(self, data: list[dict]) -> pd.DataFrame:
        rows = []
        for item in data:
            contributors = item.get("contributors", {})
            rows.append({
                "date": item.get("day"),
                "score": item.get("score"),
                "temperature_deviation": item.get("temperature_deviation"),
                "hrv_balance": contributors.get("hrv_balance"),
                "recovery_index": contributors.get("recovery_index"),
                "resting_heart_rate": contributors.get("resting_heart_rate"),
            })
        return pd.DataFrame(rows)

    def _transform_activity(self, data: list[dict]) -> pd.DataFrame:
        rows = []
        for item in data:
            rows.append({
                "date": item.get("day"),
                "score": item.get("score"),
                "active_calories": item.get("active_calories"),
                "steps": item.get("steps"),
                "equivalent_walking_distance": item.get("equivalent_walking_distance"),
            })
        return pd.DataFrame(rows)
