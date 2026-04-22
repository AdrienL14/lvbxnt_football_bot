from __future__ import annotations

import json
from typing import Any, Dict

from services.history_store import _connect


def save_session(user_id: int, payload: Dict[str, Any], updated_at: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_sessions (user_id, mode, day_offset, matches_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                mode = excluded.mode,
                day_offset = excluded.day_offset,
                matches_json = excluded.matches_json,
                updated_at = excluded.updated_at
            """,
            (user_id, payload.get("mode"), payload.get("day_offset"), json.dumps(payload.get("matches_by_token") or {}, ensure_ascii=False), updated_at),
        )
        conn.commit()


def load_session(user_id: int) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM user_sessions WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {}
    try:
        matches_by_token = json.loads(row["matches_json"] or "{}")
    except Exception:
        matches_by_token = {}
    return {
        "mode": row["mode"] or "normal",
        "day_offset": row["day_offset"] if row["day_offset"] is not None else 0,
        "matches_by_token": matches_by_token,
        "updated_at": row["updated_at"],
    }
