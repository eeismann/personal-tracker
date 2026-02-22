"""CLI entry point for the personal tracker pipeline."""

import os

import click
from dotenv import load_dotenv

# Load .env before any pipeline imports that might read env vars
load_dotenv()


@click.group()
def cli():
    """Personal data tracker pipeline."""


@cli.command()
@click.option("--all", "all_sources", is_flag=True, help="Run all ingestors")
@click.option("--source", type=click.Choice(["oura", "apple_health", "calendar", "travel"]), help="Run a specific ingestor")
@click.option("--days", type=int, default=None, help="Override: fetch last N days")
def ingest(all_sources: bool, source: str | None, days: int | None):
    """Pull data from external sources."""
    from datetime import date, timedelta

    start = date.today() - timedelta(days=days) if days else None
    end = date.today() - timedelta(days=1)

    sources_to_run = []
    if all_sources:
        sources_to_run = ["oura", "apple_health", "calendar", "travel"]
    elif source:
        sources_to_run = [source]

    if not sources_to_run:
        click.echo("Specify --all or --source. Use --help for options.")
        return

    for src in sources_to_run:
        try:
            if src == "oura":
                from pipeline.ingest.oura import OuraIngestor
                OuraIngestor().run(start_date=start, end_date=end)
            elif src == "apple_health":
                from pipeline.ingest.apple_health import AppleHealthIngestor
                AppleHealthIngestor().run(start_date=start, end_date=end)
            elif src == "calendar":
                from pipeline.ingest.google_calendar import GoogleCalendarIngestor
                GoogleCalendarIngestor().run(start_date=start, end_date=end)
            elif src == "travel":
                from pipeline.ingest.travel import extract_travel_from_events
                sheet_url = os.environ.get("GOOGLE_SHEET_URL", "")
                if not sheet_url:
                    click.echo("Error: GOOGLE_SHEET_URL not set in .env")
                    continue
                import re as _re
                sheet_id = _re.search(r"/d/([a-zA-Z0-9_-]+)", sheet_url).group(1)
                events_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=events"
                extract_travel_from_events(events_url)
        except ValueError as e:
            click.echo(f"Error: {e}")
        except Exception as e:
            click.echo(f"[{src}] Failed: {e}")


@cli.command("pull-health")
def pull_health():
    """Pull latest health exports from GitHub and ingest."""
    import subprocess

    click.echo("Pulling latest from GitHub...")
    subprocess.run(["git", "pull", "--ff-only"], check=True)

    click.echo("Ingesting Apple Health data...")
    from pipeline.ingest.apple_health import AppleHealthIngestor
    AppleHealthIngestor().run()

    click.echo("Rebuilding database...")
    from pipeline.db import rebuild_db
    from pipeline.transform.merge import run_merge
    rebuild_db()
    run_merge()
    click.echo("Done.")


@cli.command()
def rebuild():
    """Rebuild SQLite database and generate summaries."""
    from pipeline.db import rebuild_db
    from pipeline.transform.merge import run_merge

    click.echo("Rebuilding database...")
    rebuild_db()
    click.echo()

    click.echo("Merging into summaries...")
    run_merge()


@cli.command()
@click.option("--mood", type=click.IntRange(1, 5), required=True)
@click.option("--energy", type=click.IntRange(1, 5), required=True)
@click.option("--notes", type=str, default="")
def log_mood(mood: int, energy: int, notes: str):
    """Log mood and energy level."""
    import csv
    from datetime import datetime

    from pipeline.config import RAW_DIR

    filepath = RAW_DIR / "manual" / "mood_energy.csv"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    row = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "mood": mood,
        "energy": energy,
        "notes": notes,
    }

    write_header = not filepath.exists()
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    click.echo(f"Logged mood={mood} energy={energy} at {row['time']}")


@cli.command()
@click.option("--type", "session_type", type=click.Choice(["sauna", "cold_plunge", "both"]), required=True)
@click.option("--duration", type=int, required=True, help="Duration in minutes")
def log_sauna(session_type: str, duration: int):
    """Log a sauna or cold plunge session."""
    import csv
    from datetime import datetime

    from pipeline.config import RAW_DIR

    filepath = RAW_DIR / "sauna" / "sessions.csv"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    row = {
        "date": now.strftime("%Y-%m-%d"),
        "start_time": now.strftime("%Y-%m-%dT%H:%M"),
        "type": session_type,
        "duration_min": duration,
        "avg_hr": "",
        "max_hr": "",
    }

    write_header = not filepath.exists()
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    click.echo(f"Logged {session_type} session ({duration} min)")


@cli.command()
@click.argument("destination")
@click.option("--depart", type=str, required=True, help="Departure date (YYYY-MM-DD)")
@click.option("--return-date", "return_date", type=str, required=True, help="Return date (YYYY-MM-DD)")
@click.option("--country", type=str, default="")
@click.option("--purpose", type=str, default="personal")
def log_trip(destination: str, depart: str, return_date: str, country: str, purpose: str):
    """Log a travel trip."""
    import csv
    from datetime import date

    from pipeline.config import RAW_DIR

    filepath = RAW_DIR / "travel" / "trips.csv"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    dep = date.fromisoformat(depart)
    ret = date.fromisoformat(return_date)
    trip_id = f"{dep.year}-{dep.strftime('%j')}"
    duration = (ret - dep).days

    row = {
        "trip_id": trip_id,
        "departure_date": depart,
        "return_date": return_date,
        "destination_city": destination,
        "destination_country": country,
        "purpose": purpose,
        "duration_days": duration,
    }

    write_header = not filepath.exists()
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    click.echo(f"Logged trip to {destination} ({duration} days)")


if __name__ == "__main__":
    cli()
