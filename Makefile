.PHONY: setup ingest ingest-oura ingest-apple-health rebuild dashboard all clean poll-telegram

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

all: ingest rebuild

poll-telegram:
	$(PYTHON) automation/telegram_poll.py

clean:
	rm -f data/derived/tracker.db
	rm -rf data/raw_cache/*
