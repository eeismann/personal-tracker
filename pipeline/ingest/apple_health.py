"""Apple Health JSON export ingestor for steps, workouts, and sleep data.

Reads JSON files exported from the health_export iOS app placed in
data/raw/apple_health/. The iOS app produces this structure:

{
  "workouts": [{"type", "start", "end", "durationMinutes", "totalEnergyBurnedKcal", "totalDistanceMeters", "source"}],
  "dailySummary": [{"date", "metric", "aggregation", "value", "unit"}],
  "samples": [{"kind", "metric", "start", "end", "numericValue", "stringValue", "unit"}]
}

See data/raw/apple_health/example_export.json for a full example.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from pipeline.ingest.base import BaseIngestor

# Workout type mapping: iOS app type -> simplified type
WORKOUT_TYPE_MAP = {
    "strengthtraining": "strength",
    "running": "running",
    "treadmillrunning": "running",
    "cycling": "cycling",
    "indoorcycling": "cycling",
    "swimming": "swimming",
    "walking": "walking",
    "treadmillwalking": "walking",
    "hiking": "hiking",
    "yoga": "yoga",
    "mixedcardio": "cardio",
    "cooldown": "cooldown",
}

# Sleep category values from HKCategoryValueSleepAnalysis
SLEEP_CATEGORY = {
    "0": "inBed",
    "3": "core",
    "4": "deep",
    "5": "rem",
}


def _parse_iso(s: str | None) -> datetime | None:
    """Parse ISO 8601 datetime strings from the iOS export."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S %z"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # Try fromisoformat as fallback (handles most ISO 8601 variants)
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


PACIFIC = ZoneInfo("America/Los_Angeles")


def _to_pacific(dt: datetime | None) -> datetime | None:
    """Convert a datetime to Pacific time. Naive datetimes assumed UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(PACIFIC)


def _normalize_workout_type(name: str) -> str:
    """Map iOS app workout type to a simplified type string."""
    key = name.lower().strip().replace(" ", "").replace("_", "")
    return WORKOUT_TYPE_MAP.get(key, name.lower().strip())


class AppleHealthIngestor(BaseIngestor):
    source_name = "apple_health"

    def fetch(self, start_date: date, end_date: date) -> dict:
        """Read all JSON files in the apple_health raw directory."""
        json_files = sorted(self.raw_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(
                f"No JSON files found in {self.raw_dir}. "
                "Export Apple Health data from the iOS app and place files there."
            )

        combined = {"workouts": [], "dailySummary": [], "samples": []}

        for path in json_files:
            data = json.loads(path.read_text())
            combined["workouts"].extend(data.get("workouts", []))
            combined["dailySummary"].extend(data.get("dailySummary", []))
            combined["samples"].extend(data.get("samples", []))

        return combined

    def transform(self, raw_data: dict) -> dict[str, pd.DataFrame]:
        return {
            "workouts": self._transform_workouts(raw_data.get("workouts", [])),
            "steps": self._transform_steps(raw_data.get("dailySummary", [])),
            "sleep": self._transform_sleep(raw_data.get("samples", [])),
        }

    def _transform_workouts(self, data: list[dict]) -> pd.DataFrame:
        rows = []
        for item in data:
            start_dt = _to_pacific(_parse_iso(item.get("start")))
            end_dt = _to_pacific(_parse_iso(item.get("end")))
            workout_date = start_dt.strftime("%Y-%m-%d") if start_dt else None

            duration_min = item.get("durationMinutes")
            if duration_min is not None:
                duration_min = round(duration_min)

            energy = item.get("totalEnergyBurnedKcal")
            distance_m = item.get("totalDistanceMeters")
            distance_km = round(distance_m / 1000, 2) if distance_m else None

            rows.append({
                "date": workout_date,
                "start_time": start_dt.isoformat() if start_dt else None,
                "end_time": end_dt.isoformat() if end_dt else None,
                "type": _normalize_workout_type(item.get("type", "other")),
                "duration_min": duration_min,
                "active_calories": round(energy) if energy else None,
                "distance_km": distance_km,
                "avg_hr": None,
                "max_hr": None,
            })
        return pd.DataFrame(rows)

    def _transform_steps(self, data: list[dict]) -> pd.DataFrame:
        rows = []
        for item in data:
            if item.get("metric") != "stepCount":
                continue
            rows.append({
                "date": item.get("date"),
                "steps": round(item.get("value", 0)) if item.get("value") is not None else None,
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.groupby("date", as_index=False).agg({"steps": "sum"})
        return df

    def _transform_sleep(self, data: list[dict]) -> pd.DataFrame:
        # Collect sleep samples and compute durations per night
        # Group by the date the sleep ended (the morning date)
        nights: dict[str, dict[str, float]] = {}

        for item in data:
            if item.get("metric") != "sleepAnalysis":
                continue

            start_dt = _to_pacific(_parse_iso(item.get("start")))
            end_dt = _to_pacific(_parse_iso(item.get("end")))
            if not start_dt or not end_dt:
                continue

            # Use the end date as the "sleep date" (the morning you woke up)
            sleep_date = end_dt.strftime("%Y-%m-%d")
            duration_hr = (end_dt - start_dt).total_seconds() / 3600

            category_val = item.get("stringValue", "")
            stage = SLEEP_CATEGORY.get(category_val)

            if sleep_date not in nights:
                nights[sleep_date] = {
                    "asleep_hr": 0.0,
                    "in_bed_hr": 0.0,
                    "deep_hr": 0.0,
                    "rem_hr": 0.0,
                    "core_hr": 0.0,
                    "source": "Apple Watch",
                }

            night = nights[sleep_date]

            if stage == "inBed":
                night["in_bed_hr"] += duration_hr
            elif stage == "core":
                night["asleep_hr"] += duration_hr
                night["core_hr"] += duration_hr
            elif stage == "deep":
                night["asleep_hr"] += duration_hr
                night["deep_hr"] += duration_hr
            elif stage == "rem":
                night["asleep_hr"] += duration_hr
                night["rem_hr"] += duration_hr

        rows = []
        for sleep_date, night in sorted(nights.items()):
            # Total in_bed includes time asleep
            total_in_bed = night["in_bed_hr"] + night["asleep_hr"]
            rows.append({
                "date": sleep_date,
                "asleep_hr": round(night["asleep_hr"], 1),
                "in_bed_hr": round(total_in_bed, 1),
                "deep_hr": round(night["deep_hr"], 1),
                "rem_hr": round(night["rem_hr"], 1),
                "core_hr": round(night["core_hr"], 1),
                "source": night["source"],
            })
        return pd.DataFrame(rows)

    def save(self, dataframes: dict[str, pd.DataFrame]) -> None:
        """Write each DataFrame to its year-partitioned CSV.

        Overrides base to handle workouts (which can have multiple per day).
        """
        for prefix, df in dataframes.items():
            if df.empty:
                continue
            df["date"] = pd.to_datetime(df["date"]).dt.date
            for year, year_df in df.groupby(df["date"].apply(lambda d: d.year)):
                year_df = year_df.copy()
                year_df["date"] = year_df["date"].astype(str)
                filepath = self.raw_dir / f"{prefix}_{year}.csv"
                self._append_to_csv(year_df, filepath, prefix)

    def _append_to_csv(self, df: pd.DataFrame, filepath: Path, prefix: str) -> None:
        """Deduplicate and append. For workouts, dedup on date+start_time."""
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if filepath.exists():
            existing = pd.read_csv(filepath)
            combined = pd.concat([existing, df], ignore_index=True)
            if prefix == "workouts" and "start_time" in combined.columns:
                combined = combined.drop_duplicates(
                    subset=["date", "start_time"], keep="last"
                )
            elif "date" in combined.columns:
                combined = combined.drop_duplicates(subset=["date"], keep="last")
            combined = combined.sort_values("date").reset_index(drop=True)
        else:
            combined = df

        combined.to_csv(filepath, index=False)
