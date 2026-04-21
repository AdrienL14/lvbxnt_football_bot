from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

from config import SPORTSDB_API_KEY, FOOTBALL_DATA_API_KEY, API_FOOTBALL_API_KEY, STATSBOMB_ENABLED
from services.thesportsdb import TheSportsDBService
from services.football_data import FootballDataService
from services.api_football import ApiFootballService
from services.statsbomb import StatsBombService
from services.competition_catalog import COMPETITIONS
from utils.team_normalizer import build_match_key, choose_best_name, normalize_team_name
from utils.timezone_helper import get_bot_tz

BOT_TZ = get_bot_tz()
CACHE: Dict[str, Dict] = {}
CACHE_TTL = 300


def _now_ts() -> float:
    return time.time()


def _get_cache(key: str):
    item = CACHE.get(key)
    if not item:
        return None
    if _now_ts() - item["ts"] > CACHE_TTL:
        CACHE.pop(key, None)
        return None
    return item["value"]


def _set_cache(key: str, value) -> None:
    CACHE[key] = {"ts": _now_ts(), "value": value}


def _merge_match(existing: Dict, incoming: Dict) -> Dict:
    merged = dict(existing)
    merged["home_name"] = choose_best_name(existing.get("home_name", ""), incoming.get("home_name", ""))
    merged["away_name"] = choose_best_name(existing.get("away_name", ""), incoming.get("away_name", ""))

    for field in ("provider_match_id", "status", "home_score", "away_score"):
        if merged.get(field) in (None, "", "SCHEDULED") and incoming.get(field) not in (None, ""):
            merged[field] = incoming[field]

    preferred = {"football-data.org": 3, "API-Football": 2, "TheSportsDB": 1}
    if preferred.get(incoming.get("provider", ""), 0) > preferred.get(merged.get("provider", ""), 0):
        merged["provider"] = incoming.get("provider", merged.get("provider"))

    return merged


class ProviderHub:
    def __init__(self):
        self.sportsdb = TheSportsDBService(SPORTSDB_API_KEY)
        self.football_data = FootballDataService(FOOTBALL_DATA_API_KEY)
        self.api_football = ApiFootballService(API_FOOTBALL_API_KEY)
        self.statsbomb = StatsBombService(STATSBOMB_ENABLED)

    def competition_matches_for_day(self, code: str, day_offset: int = 0) -> List[Dict]:
        cache_key = f"day::{code}::{day_offset}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        comp = COMPETITIONS.get(code)
        if not comp:
            return []

        target_day = datetime.now(BOT_TZ).date() + timedelta(days=day_offset)
        from_date = target_day.strftime("%Y-%m-%d")
        to_date = target_day.strftime("%Y-%m-%d")

        out: List[Dict] = []

        if comp.get("sportsdb_league_id"):
            # TheSportsDB "next league events" often returns more than one day; we filter below
            out.extend(self.sportsdb.next_league_events(comp.get("sportsdb_league_id")))

        if comp.get("football_data_code"):
            out.extend(
                self.football_data.competition_matches(
                    comp["football_data_code"],
                    from_date,
                    to_date,
                )
            )

        uniq: Dict[str, Dict] = {}
        for m in out:
            utc_date = m.get("utc_date", "")
            if from_date not in utc_date:
                # filter strict by target day when source returned a broader set
                try:
                    dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(BOT_TZ).date()
                    if dt != target_day:
                        continue
                except Exception:
                    pass

            m["competition_code"] = code
            m["competition"] = comp["name"]
            m["token"] = build_match_key(m.get("home_name", ""), m.get("away_name", ""), m.get("utc_date", ""))
            key = m["token"]
            uniq[key] = _merge_match(uniq[key], m) if key in uniq else m

        matches = list(uniq.values())
        matches.sort(key=lambda x: x.get("utc_date", ""))
        _set_cache(cache_key, matches)
        return matches

    def all_matches_for_day(self, day_offset: int = 0) -> List[Dict]:
        cache_key = f"all::{day_offset}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        all_matches: List[Dict] = []
        uniq: Dict[str, Dict] = {}

        for code in COMPETITIONS.keys():
            for m in self.competition_matches_for_day(code, day_offset):
                key = m["token"]
                uniq[key] = _merge_match(uniq[key], m) if key in uniq else m

        all_matches = list(uniq.values())
        all_matches.sort(key=lambda x: (x.get("competition", ""), x.get("utc_date", "")))
        _set_cache(cache_key, all_matches)
        return all_matches

    def competition_recent_results(self, code: str) -> List[Dict]:
        cache_key = f"recent::{code}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        comp = COMPETITIONS.get(code)
        if not comp:
            return []

        out: List[Dict] = []

        if comp.get("sportsdb_league_id"):
            out.extend(self.sportsdb.past_league_events(comp.get("sportsdb_league_id")))

        if len(out) < 10 and comp.get("football_data_code"):
            today = datetime.now(BOT_TZ).date()
            from_date = today - timedelta(days=35)
            out.extend(
                self.football_data.competition_matches(
                    comp["football_data_code"],
                    from_date.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                )
            )

        uniq: Dict[str, Dict] = {}
        for m in out:
            m["competition_code"] = code
            m["competition"] = comp["name"]
            key = build_match_key(m.get("home_name", ""), m.get("away_name", ""), m.get("utc_date", ""))
            uniq[key] = _merge_match(uniq[key], m) if key in uniq else m

        matches = list(uniq.values())
        matches.sort(key=lambda x: x.get("utc_date", ""), reverse=True)
        _set_cache(cache_key, matches)
        return matches

    def find_finished_score(self, competition_code: str, home: str, away: str, kickoff_utc: str) -> Optional[str]:
        wanted_key = build_match_key(home, away, kickoff_utc)
        recent = self.competition_recent_results(competition_code)

        for m in recent:
            candidate_key = build_match_key(m.get("home_name", ""), m.get("away_name", ""), m.get("utc_date", ""))
            if candidate_key == wanted_key:
                hs, a_s = m.get("home_score"), m.get("away_score")
                if hs is not None and a_s is not None:
                    return f"{hs}-{a_s}"

        wanted_home = normalize_team_name(home)
        wanted_away = normalize_team_name(away)
        for m in recent:
            if normalize_team_name(m.get("home_name", "")) == wanted_home and normalize_team_name(m.get("away_name", "")) == wanted_away:
                hs, a_s = m.get("home_score"), m.get("away_score")
                if hs is not None and a_s is not None:
                    return f"{hs}-{a_s}"
        return None
