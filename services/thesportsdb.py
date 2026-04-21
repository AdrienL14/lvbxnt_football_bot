import requests
class TheSportsDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key or "123"
        self.base_url = f"https://www.thesportsdb.com/api/v1/json/{self.api_key}"
    def _get(self, endpoint: str):
        try:
            r = requests.get(f"{self.base_url}/{endpoint}", timeout=12)
            if r.status_code == 200: return r.json()
        except Exception:
            return None
        return None
    def next_league_events(self, league_id):
        if not league_id: return []
        data = self._get(f"eventsnextleague.php?id={league_id}") or {}
        out=[]
        for e in (data.get("events") or []):
            date_event = e.get("dateEvent"); str_time = e.get("strTime") or "00:00:00"
            utc_date = f"{date_event}T{str_time}Z" if date_event else ""
            out.append({"provider":"TheSportsDB","provider_match_id":e.get("idEvent"),"utc_date":utc_date,
                        "home_name":e.get("strHomeTeam",""),"away_name":e.get("strAwayTeam",""),
                        "status":"SCHEDULED","home_score":None,"away_score":None})
        return out
    def past_league_events(self, league_id):
        if not league_id: return []
        data = self._get(f"eventspastleague.php?id={league_id}") or {}
        out=[]
        for e in (data.get("events") or []):
            date_event = e.get("dateEvent"); str_time = e.get("strTime") or "00:00:00"
            utc_date = f"{date_event}T{str_time}Z" if date_event else ""
            try:
                hs = int(e["intHomeScore"]) if e.get("intHomeScore") is not None else None
                a = int(e["intAwayScore"]) if e.get("intAwayScore") is not None else None
            except Exception:
                hs = a = None
            out.append({"provider":"TheSportsDB","provider_match_id":e.get("idEvent"),"utc_date":utc_date,
                        "home_name":e.get("strHomeTeam",""),"away_name":e.get("strAwayTeam",""),
                        "status":"FINISHED" if hs is not None and a is not None else "SCHEDULED","home_score":hs,"away_score":a})
        return out
