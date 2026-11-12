"""Persistent learner profile store (SQLite).

One row per (learner, field) with a full update history, so the tutor can
show *what* it remembers and *when* it learned it. See profile_schema.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB = os.environ.get("TUTOR_DB", "tutor_memory.db")

# Fields the reflection step is allowed to write (profile contract).
PROFILE_FIELDS = {
    "goals": list,
    "learns_best_by": str,        # e.g. "worked examples before theory"
    "pace": str,                  # e.g. "short steps, frequent checks"
    "mastered_topics": list,
    "active_topics": list,
    "misconceptions": list,       # [{"topic": ..., "note": ..., "seen_count": int}]
    "preferences": dict,          # free-form small key/values
}


def _connect(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS profile_fields (
               learner TEXT NOT NULL,
               field   TEXT NOT NULL,
               value   TEXT NOT NULL,
               updated_at TEXT NOT NULL,
               PRIMARY KEY (learner, field)
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS profile_history (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               learner TEXT NOT NULL, field TEXT NOT NULL,
               old_value TEXT, new_value TEXT, updated_at TEXT NOT NULL
           )"""
    )
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_profile(learner: str, db_path: str = DEFAULT_DB) -> dict:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT field, value FROM profile_fields WHERE learner = ?", (learner,)
        ).fetchall()
    return {field: json.loads(value) for field, value in rows}


def validate_updates(updates: dict) -> dict:
    """Drop anything outside the profile contract; coerce types strictly."""
    clean = {}
    for field, value in updates.items():
        expected = PROFILE_FIELDS.get(field)
        if expected is None:
            continue
        if expected is list and isinstance(value, list):
            clean[field] = value
        elif expected is str and isinstance(value, str):
            clean[field] = value
        elif expected is dict and isinstance(value, dict):
            clean[field] = value
    return clean


def apply_updates(learner: str, updates: dict, db_path: str = DEFAULT_DB) -> dict:
    """Validate + persist updates, recording history. Returns the new profile."""
    clean = validate_updates(updates)
    current = get_profile(learner, db_path)
    with _connect(db_path) as conn:
        for field, value in clean.items():
            conn.execute(
                "INSERT INTO profile_history (learner, field, old_value, new_value, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (learner, field, json.dumps(current.get(field)), json.dumps(value), _now()),
            )
            conn.execute(
                "INSERT INTO profile_fields (learner, field, value, updated_at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT(learner, field) DO UPDATE SET value = excluded.value,"
                " updated_at = excluded.updated_at",
                (learner, field, json.dumps(value), _now()),
            )
        conn.commit()
    return get_profile(learner, db_path)


def render_for_prompt(profile: dict, learner: str) -> str:
    """Render the profile as the memory block injected into the system prompt."""
    if not profile:
        return f"Learner: {learner}\n(No profile yet — this is the first session. Ask about goals and preferred learning style early.)"
    lines = [f"Learner: {learner}"]
    if profile.get("goals"):
        lines.append("Goals: " + "; ".join(profile["goals"]))
    if profile.get("learns_best_by"):
        lines.append(f"Learns best by: {profile['learns_best_by']}")
    if profile.get("pace"):
        lines.append(f"Pace: {profile['pace']}")
    if profile.get("mastered_topics"):
        lines.append("Mastered (do not re-teach unless reviewing): " + ", ".join(profile["mastered_topics"]))
    if profile.get("active_topics"):
        lines.append("Currently learning: " + ", ".join(profile["active_topics"]))
    for item in profile.get("misconceptions", []):
        lines.append(
            f"Watch out: {item.get('topic')} — {item.get('note')} "
            f"(seen {item.get('seen_count', 1)}x). Re-teach with a different strategy."
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Learner profile inspector")
    parser.add_argument("--learner", required=True)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--db", default=DEFAULT_DB)
    args = parser.parse_args()
    if args.show:
        print(render_for_prompt(get_profile(args.learner, args.db), args.learner))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
