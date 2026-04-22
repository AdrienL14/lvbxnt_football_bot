from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from config import BOT_STORAGE_DIR

DB_PATH = Path(BOT_STORAGE_DIR) / "history.sqlite3"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                settled_at TEXT,
                user_id INTEGER,
                mode TEXT NOT NULL,
                competition_code TEXT,
                competition TEXT,
                day_label TEXT,
                kickoff_utc TEXT,
                match_key TEXT,
                home_name TEXT,
                away_name TEXT,
                prediction TEXT,
                bet_type TEXT,
                confidence INTEGER,
                score_prediction TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                final_score TEXT,
                won INTEGER,
                provider TEXT,
                note TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER PRIMARY KEY,
                mode TEXT,
                day_offset INTEGER,
                matches_json TEXT,
                updated_at TEXT
            )
            """
        )
        conn.commit()


def save_analysis(item: Dict[str, Any]) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analysis_history (
                created_at, user_id, mode, competition_code, competition, day_label, kickoff_utc,
                match_key, home_name, away_name, prediction, bet_type, confidence,
                score_prediction, status, provider, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("created_at"), item.get("user_id"), item.get("mode"), item.get("competition_code"),
                item.get("competition"), item.get("day_label"), item.get("kickoff_utc"), item.get("match_key"),
                item.get("home_name"), item.get("away_name"), item.get("prediction"), item.get("bet_type"),
                item.get("confidence"), item.get("score_prediction"), item.get("status", "pending"),
                item.get("provider"), item.get("note"),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def read_recent(limit: int = 20) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM analysis_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def history_summary() -> Dict[str, Any]:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0]
        settled = conn.execute("SELECT COUNT(*) FROM analysis_history WHERE won IS NOT NULL").fetchone()[0]
        wins = conn.execute("SELECT COUNT(*) FROM analysis_history WHERE won = 1").fetchone()[0]
        pending = total - settled
        by_mode = {}
        for mode in ["prudent", "normal", "agressif", "sniper"]:
            mode_settled = conn.execute("SELECT COUNT(*) FROM analysis_history WHERE mode = ? AND won IS NOT NULL", (mode,)).fetchone()[0]
            mode_wins = conn.execute("SELECT COUNT(*) FROM analysis_history WHERE mode = ? AND won = 1", (mode,)).fetchone()[0]
            by_mode[mode] = round((mode_wins / mode_settled) * 100) if mode_settled else 0
    global_winrate = round((wins / settled) * 100) if settled else 0
    return {"total": total, "settled": settled, "pending": pending, "wins": wins, "global_winrate": global_winrate, "by_mode": by_mode}


def _bet_result(bet_type: str, home_score: int, away_score: int) -> bool | None:
    total = home_score + away_score
    if bet_type == "double_chance_home":
        return home_score >= away_score
    if bet_type == "double_chance_away":
        return away_score >= home_score
    if bet_type == "1x2_home":
        return home_score > away_score
    if bet_type == "1x2_away":
        return away_score > home_score
    if bet_type == "draw":
        return home_score == away_score
    if bet_type == "over15":
        return total >= 2
    if bet_type == "over25":
        return total >= 3
    if bet_type == "btts":
        return home_score > 0 and away_score > 0
    if bet_type == "combo_home_goals":
        return home_score > away_score and total >= 2
    if bet_type == "combo_away_goals":
        return away_score > home_score and total >= 2
    return None


def settle_pending(hub, now_str: str) -> int:
    updated = 0
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM analysis_history WHERE won IS NULL ORDER BY id ASC LIMIT 100").fetchall()
        for row in rows:
            item = dict(row)
            result = hub.find_finished_result(
                competition_code=item.get("competition_code") or "",
                home=item.get("home_name") or "",
                away=item.get("away_name") or "",
                kickoff_utc=item.get("kickoff_utc") or "",
            )
            if not result:
                continue
            home_score = result.get("home_score")
            away_score = result.get("away_score")
            if home_score is None or away_score is None:
                continue
            won = _bet_result(item.get("bet_type") or "", home_score, away_score)
            if won is None:
                continue
            conn.execute(
                "UPDATE analysis_history SET settled_at = ?, status = 'settled', final_score = ?, won = ? WHERE id = ?",
                (now_str, f"{home_score}-{away_score}", 1 if won else 0, item["id"]),
            )
            updated += 1
        conn.commit()
    return updated
