# Personal Tracker

Automated personal data collection pipeline + interactive dashboard.

## Architecture

- **pipeline/** — Python data ingestion & processing (Oura, Apple Health, Google Calendar, etc.)
- **dashboard/** — Next.js visualization app
- **data/** — Git-tracked CSVs (source of truth)
- **automation/** — launchd plists, Apple Shortcuts, Google Apps Scripts

## Quick Start

```bash
make setup          # Create venv, install dependencies
cp .env.example .env  # Add your API tokens
make ingest         # Pull data from all sources
make rebuild        # Build SQLite DB + daily summary
make dashboard      # Start Next.js dev server
```

## Data Flow

```
[Oura API] [Apple Health] [Google Calendar] [Weather API]
                          │
                 Python ingest scripts
                          │
                  data/raw/**/*.csv
                          │
                 Python merge/transform
                          │
            data/derived/daily_summary.csv
            dashboard/public/data/tracker.json
```

## Commands

| Command | Description |
|---------|-------------|
| `make setup` | Create venv and install all dependencies |
| `make ingest` | Run all data ingestors |
| `make ingest-oura` | Pull Oura Ring data only |
| `make rebuild` | Rebuild SQLite DB and summaries |
| `make dashboard` | Start dashboard dev server |
| `make all` | Ingest + rebuild + sync |
