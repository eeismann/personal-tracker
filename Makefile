.PHONY: setup ingest ingest-oura ingest-apple-health rebuild dashboard all clean poll-telegram sync

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

setup:
	python3 -m venv $(VENV)
	$(PIP) install -e ".[dev]"
	cd dashboard && npm install

ingest:
	$(PYTHON) -m pipeline.cli ingest --all

ingest-oura:
	$(PYTHON) -m pipeline.cli ingest --source oura

ingest-apple-health:
	$(PYTHON) -m pipeline.cli ingest --source apple_health

rebuild:
	$(PYTHON) -m pipeline.cli rebuild

dashboard:
	cd dashboard && npm run dev

all: ingest rebuild sync

poll-telegram:
	$(PYTHON) automation/telegram_poll.py

sync:
	@if [ -n "$$PERSONAL_WEBSITE_PATH" ]; then \
		cp data/derived/tracker.json "$$PERSONAL_WEBSITE_PATH/public/data/tracker.json"; \
		echo "Synced tracker.json to $$PERSONAL_WEBSITE_PATH"; \
	else \
		cp data/derived/tracker.json ../personal-website/public/data/tracker.json; \
		echo "Synced tracker.json to ../personal-website"; \
	fi

clean:
	rm -f data/derived/tracker.db
	rm -rf data/raw_cache/*
