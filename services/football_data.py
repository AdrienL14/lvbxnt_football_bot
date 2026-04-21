import requests
class FootballDataService:
    def __init__(self, api_key: str):
        self.api_key = api_key or ""
        self.base_url = "https://api.football-data.org/v4"
    def competition_matches(self, code, date_from, date_to):
        if not self.api_key or not code: return []
        try:
            r = requests.get(f"{self.base_url}/competitions/{code}/matches", params={"dateFrom":date_from,"dateTo":date_to}, headers={"X-Auth-Token":self.api_key}, timeout=12)
            if r.status_code != 200: return []
            data = r.json()
        except Exception:
            return []
        out=[]
        for m in (data.get("matches") or []):
            ft = ((m.get("score") or {}).get("fullTime") or {})
            out.append({"provider":"football-data.org","provider_match_id":m.get("id"),"utc_date":m.get("utcDate",""),
                        "home_name":(m.get("homeTeam") or {}).get("name",""),"away_name":(m.get("awayTeam") or {}).get("name",""),
                        "status":m.get("status","SCHEDULED"),"home_score":ft.get("home"),"away_score":ft.get("away")})
        return out
