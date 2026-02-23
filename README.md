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

## Tokyo trip voting backend

This repo now includes a tiny shared backend for `/tokyo-trip` family voting.

Run locally:

```bash
cd /Users/orindagold/Documents/personal-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn pipeline.votes_api:app --host 0.0.0.0 --port 8789
```

Endpoints:
- `GET /health`
- `GET /votes`
- `POST /votes` with `{ activityId, person, value, reason }`

Env vars:
- `TOKYO_VOTES_DB` (default: `data/derived/tokyo_votes.db`)
- `TOKYO_VOTES_CORS` (default: `https://ethaneismann.com`)

Then set in personal-website deploy env:
- `NEXT_PUBLIC_TOKYO_VOTES_API=https://<your-backend-host>`
