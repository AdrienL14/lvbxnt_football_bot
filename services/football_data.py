from __future__ import annotations

import requests

class FootballDataService:
    def __init__(self, api_key: str):
        self.api_key = api_key or ""
        self.base_url = "https://api.football-data.org/v4"

    def competition_matches(self, code: str, date_from: str, date_to: str):
        if not self.api_key or not code:
            return []
        try:
            response = requests.get(
                f"{self.base_url}/competitions/{code}/matches",
                params={"dateFrom": date_from, "dateTo": date_to},
                headers={"X-Auth-Token": self.api_key},
                timeout=15,
            )
            if response.status_code != 200:
                return []
            data = response.json()
        except Exception:
            return []
        out = []
        for match in (data.get("matches") or []):
            full_time = ((match.get("score") or {}).get("fullTime") or {})
            out.append({
                "provider": "football-data.org",
                "provider_match_id": match.get("id"),
                "utc_date": match.get("utcDate", ""),
                "home_name": (match.get("homeTeam") or {}).get("name", ""),
                "away_name": (match.get("awayTeam") or {}).get("name", ""),
                "status": match.get("status", "SCHEDULED"),
                "home_score": full_time.get("home"),
                "away_score": full_time.get("away"),
            })
        return out
