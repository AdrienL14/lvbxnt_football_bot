import requests
class ApiFootballService:
    def __init__(self, api_key: str, host: str = "v3.football.api-sports.io"):
        self.api_key = api_key or ""; self.host = host; self.base_url = f"https://{host}"
    def fixtures_by_league(self, league_id, season):
        if not self.api_key or not league_id or not season: return []
        try:
            r = requests.get(f"{self.base_url}/fixtures", params={"league":league_id,"season":season}, headers={"x-apisports-key":self.api_key,"x-rapidapi-host":self.host}, timeout=12)
            if r.status_code != 200: return []
            data = r.json()
        except Exception:
            return []
        out=[]
        for item in (data.get("response") or []):
            fixture=item.get("fixture") or {}; teams=item.get("teams") or {}; goals=item.get("goals") or {}
            out.append({"provider":"API-Football","provider_match_id":fixture.get("id"),"utc_date":fixture.get("date",""),
                        "home_name":((teams.get("home") or {}).get("name")) or "","away_name":((teams.get("away") or {}).get("name")) or "",
                        "status":((fixture.get("status") or {}).get("short")) or "SCHEDULED","home_score":goals.get("home"),"away_score":goals.get("away")})
        return out
