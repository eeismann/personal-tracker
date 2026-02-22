"""Merge data sources into daily_summary.csv and tracker.json."""

import json
from datetime import date, timedelta

import pandas as pd

from pipeline.config import (
    DAILY_SUMMARY_CSV,
    DASHBOARD_DATA_DIR,
    DERIVED_DIR,
    TRACKER_JSON,
    WEEKLY_SUMMARY_CSV,
)
from pipeline.db import load_csvs


def _load_source(directory: str, pattern: str, dedup_by_date: bool = True) -> pd.DataFrame:
    """Load a source and ensure date column is string YYYY-MM-DD."""
    df = load_csvs(directory, pattern, dedup_by_date=dedup_by_date)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def build_daily_summary() -> pd.DataFrame:
    """Join all sources into one row per day."""
    # Load sources
    sleep = _load_source("oura", "sleep_*.csv")
    readiness = _load_source("oura", "readiness_*.csv")
    activity = _load_source("oura", "activity_*.csv")
    workouts = _load_source("apple_health", "workouts_*.csv", dedup_by_date=False)
    sauna = _load_source("sauna", "sessions.csv")
    work = _load_source("work", "hours_*.csv")
    weather = _load_source("weather", "daily_*.csv")
    mood = _load_source("manual", "mood_energy.csv")

    # Collect all dates
    all_dates = set()
    for df in [sleep, readiness, activity, workouts, sauna, work, weather, mood]:
        if not df.empty and "date" in df.columns:
            all_dates.update(df["date"].unique())

    if not all_dates:
        return pd.DataFrame()

    # Build base dataframe with all dates
    summary = pd.DataFrame({"date": sorted(all_dates)})

    # Merge Oura sleep
    if not sleep.empty:
        sleep_cols = sleep[["date", "score", "total_sleep_min", "deep_min", "rem_min", "hr_lowest"]].copy()
        sleep_cols = sleep_cols.rename(columns={
            "score": "sleep_score",
            "total_sleep_min": "sleep_total_min",
            "deep_min": "sleep_deep_min",
            "rem_min": "sleep_rem_min",
            "hr_lowest": "sleep_hr_lowest",
        })
        summary = summary.merge(sleep_cols, on="date", how="left")

    # Merge Oura readiness
    if not readiness.empty:
        readiness_cols = readiness[["date", "score", "resting_heart_rate"]].copy()
        readiness_cols = readiness_cols.rename(columns={
            "score": "readiness_score",
            "resting_heart_rate": "resting_hr",
        })
        summary = summary.merge(readiness_cols, on="date", how="left")

    # Merge Oura activity
    if not activity.empty:
        activity_cols = activity[["date", "score", "active_calories", "steps"]].copy()
        activity_cols = activity_cols.rename(columns={
            "score": "activity_score",
        })
        summary = summary.merge(activity_cols, on="date", how="left")

    # Workout flag (any workout that day)
    if not workouts.empty:
        workout_days = workouts.groupby("date").agg(
            workout_count=("type", "count"),
            workout_types=("type", lambda x: ",".join(sorted(set(x.dropna())))),
            workout_duration_min=("duration_min", "sum"),
        ).reset_index()
        summary = summary.merge(workout_days, on="date", how="left")

    # Sauna flag
    if not sauna.empty:
        sauna_days = sauna.groupby("date").agg(
            sauna_sessions=("type", "count"),
        ).reset_index()
        summary = summary.merge(sauna_days, on="date", how="left")

    # Work hours
    if not work.empty:
        work_cols = work[["date", "total_work_hr", "meeting_count", "meeting_hr", "focus_hr"]].copy()
        summary = summary.merge(work_cols, on="date", how="left")

    # Weather
    if not weather.empty:
        weather_cols = weather[["date", "high_f", "low_f", "condition"]].copy()
        weather_cols = weather_cols.rename(columns={
            "high_f": "weather_high_f",
            "low_f": "weather_low_f",
            "condition": "weather_condition",
        })
        summary = summary.merge(weather_cols, on="date", how="left")

    # Mood
    if not mood.empty:
        # Take last entry per day if multiple
        mood_daily = mood.sort_values("time").groupby("date").last().reset_index()
        mood_cols = mood_daily[["date", "mood", "energy"]].copy()
        summary = summary.merge(mood_cols, on="date", how="left")

    summary = summary.sort_values("date").reset_index(drop=True)
    return summary


def build_weekly_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily summary into weekly buckets."""
    if daily.empty:
        return pd.DataFrame()

    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["week"] = df["date"].dt.isocalendar().week.astype(int)
    df["year"] = df["date"].dt.year

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    agg_dict = {col: "mean" for col in numeric_cols if col not in ("week", "year")}

    # Count-based aggregations
    if "workout_count" in df.columns:
        agg_dict["workout_count"] = "sum"
    if "sauna_sessions" in df.columns:
        agg_dict["sauna_sessions"] = "sum"
    if "steps" in df.columns:
        agg_dict["steps"] = "sum"

    weekly = df.groupby(["year", "week"]).agg(agg_dict).reset_index()
    weekly = weekly.round(1)
    return weekly


def build_tracker_json(daily: pd.DataFrame) -> dict:
    """Build the tracker.json consumed by the Next.js dashboard."""
    if daily.empty:
        return {"days": {}, "generated": str(date.today())}

    days = {}
    for _, row in daily.iterrows():
        date_str = str(row["date"])

        # Determine workout type for habits display
        workout = None
        if pd.notna(row.get("workout_types")):
            types = str(row["workout_types"]).lower()
            if "strength" in types or "weight" in types:
                workout = "weights"
            if "running" in types or "cycling" in types or "cardio" in types:
                workout = "both" if workout == "weights" else "cardio"
            if not workout:
                workout = "cardio"  # Default for unknown workout types

        # Map readiness to stress level
        stress = None
        readiness = row.get("readiness_score")
        if pd.notna(readiness):
            if readiness >= 75:
                stress = "low"
            elif readiness >= 55:
                stress = "moderate"
            else:
                stress = "high"

        sleep_hours = None
        if pd.notna(row.get("sleep_total_min")):
            sleep_hours = round(row["sleep_total_min"] / 60, 1)

        days[date_str] = {
            "date": date_str,
            "habits": {
                "workout": workout,
                "sauna": pd.notna(row.get("sauna_sessions")) and int(row["sauna_sessions"]) > 0,
                "meditation": False,  # TODO: detect from Apple Health
            },
            "sleep": sleep_hours,
            "restingHR": int(row["resting_hr"]) if pd.notna(row.get("resting_hr")) else None,
            "stress": stress,
            "location": None,
            "notes": None,
            "timeWithArno": None,
            "timeWorking": int(row["total_work_hr"] * 60) if pd.notna(row.get("total_work_hr")) else None,
            "timeCoding": None,
            # Extended fields for new dashboard
            "sleepScore": int(row["sleep_score"]) if pd.notna(row.get("sleep_score")) else None,
            "readinessScore": int(row["readiness_score"]) if pd.notna(row.get("readiness_score")) else None,
            "activityScore": int(row["activity_score"]) if pd.notna(row.get("activity_score")) else None,
            "steps": int(row["steps"]) if pd.notna(row.get("steps")) else None,
            "activeCalories": int(row["active_calories"]) if pd.notna(row.get("active_calories")) else None,
            "sleepDeepMin": int(row["sleep_deep_min"]) if pd.notna(row.get("sleep_deep_min")) else None,
            "sleepRemMin": int(row["sleep_rem_min"]) if pd.notna(row.get("sleep_rem_min")) else None,
            "weatherHighF": round(row["weather_high_f"], 0) if pd.notna(row.get("weather_high_f")) else None,
            "weatherCondition": row.get("weather_condition") if pd.notna(row.get("weather_condition")) else None,
            "mood": int(row["mood"]) if pd.notna(row.get("mood")) else None,
            "energy": int(row["energy"]) if pd.notna(row.get("energy")) else None,
        }

    # Load travel data
    trips_df = _load_source("travel", "trips.csv")
    flights_df = _load_source("travel", "flights.csv")

    trips = []
    if not trips_df.empty:
        for _, row in trips_df.iterrows():
            trips.append({
                "tripId": str(row.get("trip_id", "")),
                "departureDate": str(row.get("departure_date", "")),
                "returnDate": str(row.get("return_date", "")),
                "destinationCity": str(row.get("destination_city", "")),
                "destinationCountry": str(row.get("destination_country", "")),
                "purpose": str(row.get("purpose", "")),
                "durationDays": int(row["duration_days"]) if pd.notna(row.get("duration_days")) else 0,
                "totalMiles": int(row["total_miles"]) if pd.notna(row.get("total_miles")) else 0,
                "flightCount": int(row["flight_count"]) if pd.notna(row.get("flight_count")) else 0,
            })

    flights = []
    if not flights_df.empty:
        for _, row in flights_df.iterrows():
            flights.append({
                "flightDate": str(row.get("flight_date", "")),
                "tripId": str(row.get("trip_id", "")),
                "origin": str(row.get("origin_iata", "")),
                "destination": str(row.get("destination_iata", "")),
                "airline": str(row.get("airline", "")),
                "flightNumber": str(row.get("flight_number", "")),
                "miles": int(row["miles"]) if pd.notna(row.get("miles")) else 0,
            })

    return {
        "days": days,
        "travel": {"trips": trips, "flights": flights},
        "generated": str(date.today()),
    }


def run_merge() -> None:
    """Execute the full merge pipeline."""
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    print("Building daily summary...")
    daily = build_daily_summary()
    if daily.empty:
        print("No data found in any source. Run ingest first.")
        return

    # Save daily summary CSV
    daily.to_csv(DAILY_SUMMARY_CSV, index=False)
    print(f"  {len(daily)} days -> {DAILY_SUMMARY_CSV}")

    # Save weekly summary CSV
    print("Building weekly summary...")
    weekly = build_weekly_summary(daily)
    if not weekly.empty:
        weekly.to_csv(WEEKLY_SUMMARY_CSV, index=False)
        print(f"  {len(weekly)} weeks -> {WEEKLY_SUMMARY_CSV}")

    # Build and save tracker.json
    print("Building tracker.json...")
    tracker = build_tracker_json(daily)
    TRACKER_JSON.write_text(json.dumps(tracker, indent=2, default=str))
    print(f"  {len(tracker['days'])} days -> {TRACKER_JSON}")

    # Also copy to dashboard public dir
    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    dashboard_json = DASHBOARD_DATA_DIR / "tracker.json"
    dashboard_json.write_text(json.dumps(tracker, indent=2, default=str))
    print(f"  Copied to {dashboard_json}")
