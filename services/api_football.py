from __future__ import annotations

import requests

class ApiFootballService:
    def __init__(self, api_key: str, host: str = "v3.football.api-sports.io"):
        self.api_key = api_key or ""
        self.host = host
        self.base_url = f"https://{host}"

    def _get(self, endpoint: str, params: dict | None = None):
        if not self.api_key:
            return {}
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                params=params or {},
                headers={"x-apisports-key": self.api_key, "x-rapidapi-host": self.host},
                timeout=15,
            )
            if response.status_code != 200:
                return {}
            return response.json() or {}
        except Exception:
            return {}

    def fixtures_by_league_and_date(self, league_id: int, season: int, date_str: str):
        if not league_id or not season or not date_str:
            return []
        data = self._get("fixtures", {"league": league_id, "season": season, "date": date_str})
        out = []
        for item in (data.get("response") or []):
            fixture = item.get("fixture") or {}
            teams = item.get("teams") or {}
            goals = item.get("goals") or {}
            league = item.get("league") or {}
            out.append({
                "provider": "API-Football",
                "provider_match_id": fixture.get("id"),
                "utc_date": fixture.get("date", ""),
                "home_name": ((teams.get("home") or {}).get("name")) or "",
                "away_name": ((teams.get("away") or {}).get("name")) or "",
                "status": ((fixture.get("status") or {}).get("short")) or "SCHEDULED",
                "home_score": goals.get("home"),
                "away_score": goals.get("away"),
                "venue": (fixture.get("venue") or {}).get("name", ""),
                "league_round": league.get("round", ""),
            })
        return out

    def standings(self, league_id: int, season: int):
        if not league_id or not season:
            return {}
        data = self._get("standings", {"league": league_id, "season": season})
        response = data.get("response") or []
        if not response:
            return {}
        league = response[0].get("league") or {}
        rows = (league.get("standings") or [[]])[0]
        output = {}
        for row in rows:
            team = row.get("team") or {}
            team_name = team.get("name") or ""
            all_stats = row.get("all") or {}
            output[team_name] = {
                "rank": row.get("rank"),
                "points": row.get("points"),
                "goals_diff": row.get("goalsDiff"),
                "played": all_stats.get("played"),
                "wins": all_stats.get("win"),
                "draws": all_stats.get("draw"),
                "losses": all_stats.get("lose"),
            }
        return output
