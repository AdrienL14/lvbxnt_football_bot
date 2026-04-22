from __future__ import annotations

import requests

class TheSportsDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key or "123"
        self.base_url = f"https://www.thesportsdb.com/api/v1/json/{self.api_key}"

    def _get(self, endpoint: str):
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception:
            return None
        return None

    def next_league_events(self, league_id: str):
        if not league_id:
            return []
        data = self._get(f"eventsnextleague.php?id={league_id}") or {}
        out = []
        for item in (data.get("events") or []):
            date_event = item.get("dateEvent")
            str_time = item.get("strTime") or "00:00:00"
            utc_date = f"{date_event}T{str_time}Z" if date_event else ""
            out.append({
                "provider": "TheSportsDB",
                "provider_match_id": item.get("idEvent"),
                "utc_date": utc_date,
                "home_name": item.get("strHomeTeam", ""),
                "away_name": item.get("strAwayTeam", ""),
                "status": "SCHEDULED",
                "home_score": None,
                "away_score": None,
            })
        return out

    def past_league_events(self, league_id: str):
        if not league_id:
            return []
        data = self._get(f"eventspastleague.php?id={league_id}") or {}
        out = []
        for item in (data.get("events") or []):
            date_event = item.get("dateEvent")
            str_time = item.get("strTime") or "00:00:00"
            utc_date = f"{date_event}T{str_time}Z" if date_event else ""
            try:
                hs = int(item["intHomeScore"]) if item.get("intHomeScore") is not None else None
                a_s = int(item["intAwayScore"]) if item.get("intAwayScore") is not None else None
            except Exception:
                hs = None
                a_s = None
            out.append({
                "provider": "TheSportsDB",
                "provider_match_id": item.get("idEvent"),
                "utc_date": utc_date,
                "home_name": item.get("strHomeTeam", ""),
                "away_name": item.get("strAwayTeam", ""),
                "status": "FINISHED" if hs is not None and a_s is not None else "SCHEDULED",
                "home_score": hs,
                "away_score": a_s,
            })
        return out
