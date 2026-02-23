from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv("TOKYO_VOTES_DB", "data/derived/tokyo_votes.db"))
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("TOKYO_VOTES_CORS", "https://ethaneismann.com").split(",") if o.strip()]

app = FastAPI(title="Tokyo Trip Votes API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class VoteIn(BaseModel):
    activityId: str = Field(min_length=1)
    person: Literal["Jodi", "Ethan", "Aniek", "Axel"]
    value: Literal[1, -1]
    reason: str = Field(min_length=1, max_length=500)


class VoteOut(BaseModel):
    activityId: str
    person: str
    value: int
    reason: str
    updatedAt: str


def conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS votes (
          activity_id TEXT NOT NULL,
          person TEXT NOT NULL,
          value INTEGER NOT NULL,
          reason TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (activity_id, person)
        )
        """
    )
    c.commit()
    return c


@app.get("/health")
def health() -> dict:
    return {"ok": True, "db": str(DB_PATH)}


@app.get("/votes")
def get_votes() -> dict[str, dict[str, VoteOut]]:
    c = conn()
    rows = c.execute(
        "SELECT activity_id, person, value, reason, updated_at FROM votes"
    ).fetchall()
    c.close()

    out: dict[str, dict[str, VoteOut]] = {}
    for activity_id, person, value, reason, updated_at in rows:
        out.setdefault(activity_id, {})[person] = {
            "activityId": activity_id,
            "person": person,
            "value": value,
            "reason": reason,
            "updatedAt": updated_at,
        }
    return out


@app.post("/votes")
def upsert_vote(payload: VoteIn) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    c = conn()
    c.execute(
        """
        INSERT INTO votes(activity_id, person, value, reason, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(activity_id, person) DO UPDATE SET
          value=excluded.value,
          reason=excluded.reason,
          updated_at=excluded.updated_at
        """,
        (payload.activityId, payload.person, payload.value, payload.reason.strip(), ts),
    )
    c.commit()
    c.close()
    return {"ok": True, "updatedAt": ts}
