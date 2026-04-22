from __future__ import annotations

from typing import Dict


def build_reliability(home_stats: Dict, away_stats: Dict, home_table: Dict | None, away_table: Dict | None) -> Dict:
    home_played = int(home_stats.get("played", 0) or 0)
    away_played = int(away_stats.get("played", 0) or 0)
    min_played = min(home_played, away_played)
    penalty = 0
    notes: list[str] = []
    if min_played < 4:
        penalty += 14
        notes.append("peu de matchs récents")
    elif min_played < 6:
        penalty += 8
        notes.append("échantillon encore moyen")
    else:
        notes.append("forme récente exploitable")
    if not home_table or not away_table:
        penalty += 6
        notes.append("classement non confirmé")
    else:
        notes.append("classement confirmé")
    if min_played >= 6 and home_table and away_table:
        status = "bon"
    elif min_played >= 4:
        status = "moyen"
    else:
        status = "faible"
    return {"data_status": status, "confidence_penalty": penalty, "data_note": ", ".join(notes)}
