"""Where touch-grass remembers the last time you saw the sky."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_MINUTES = 180


def home() -> Path:
    path = Path(os.environ.get("TOUCHGRASS_HOME", Path.home() / ".touchgrass"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def max_minutes() -> int:
    return int(os.environ.get("TOUCHGRASS_MAX_MINUTES", DEFAULT_MAX_MINUTES))


def now() -> datetime:
    return datetime.now(timezone.utc)


def _state_file() -> Path:
    return home() / "state.json"


def _receipts_file() -> Path:
    return home() / "receipts.jsonl"


def load() -> dict:
    try:
        return json.loads(_state_file().read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(state: dict) -> None:
    _state_file().write_text(json.dumps(state, indent=2))


def last_grass() -> datetime | None:
    value = load().get("last_grass")
    return datetime.fromisoformat(value) if value else None


def mark_grass(at: datetime | None = None) -> None:
    state = load()
    state["last_grass"] = (at or now()).isoformat()
    save(state)


def ensure_baseline() -> None:
    """First run starts the clock now instead of blocking a brand-new user."""
    if last_grass() is None:
        mark_grass()


def minutes_indoors(at: datetime | None = None) -> float:
    last = last_grass()
    if last is None:
        return 0.0
    return ((at or now()) - last).total_seconds() / 60


def add_receipt(receipt: dict) -> None:
    with _receipts_file().open("a") as f:
        f.write(json.dumps(receipt) + "\n")


def receipts() -> list[dict]:
    try:
        lines = _receipts_file().read_text().splitlines()
    except FileNotFoundError:
        return []
    return [json.loads(line) for line in lines if line.strip()]
