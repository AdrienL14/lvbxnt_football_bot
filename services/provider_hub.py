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

TTL_DAY = 1800
TTL_ALL = 1800
TTL_RECENT = 21600
TTL_STANDINGS = 21600


def _now_ts() -> float:
    return time.time()


def _get_cache(key: str):
    item = CACHE.get(key)
    if not item:
        return None
    if _now_ts() - item["ts"] > item["ttl"]:
        CACHE.pop(key, None)
        return None
    return item["value"]


def _set_cache(key: str, value, ttl: int) -> None:
    CACHE[key] = {"ts": _now_ts(), "ttl": ttl, "value": value}


def _merge_match(existing: Dict, incoming: Dict) -> Dict:
    merged = dict(existing)
    merged["home_name"] = choose_best_name(existing.get("home_name", ""), incoming.get("home_name", ""))
    merged["away_name"] = choose_best_name(existing.get("away_name", ""), incoming.get("away_name", ""))
    for field in ("provider_match_id", "status", "home_score", "away_score", "venue", "league_round"):
        if merged.get(field) in (None, "", "SCHEDULED") and incoming.get(field) not in (None, ""):
            merged[field] = incoming[field]
    preferred = {"API-Football": 4, "football-data.org": 3, "TheSportsDB": 1}
    if preferred.get(incoming.get("provider", ""), 0) > preferred.get(merged.get("provider", ""), 0):
        merged["provider"] = incoming.get("provider", merged.get("provider"))
    return merged


class ProviderHub:
    def __init__(self):
        self.sportsdb = TheSportsDBService(SPORTSDB_API_KEY)
        self.football_data = FootballDataService(FOOTBALL_DATA_API_KEY)
        self.api_football = ApiFootballService(API_FOOTBALL_API_KEY)
        self.statsbomb = StatsBombService(STATSBOMB_ENABLED)

    def _strict_target_day(self, utc_date: str, target_day) -> bool:
        if not utc_date:
            return False
        try:
            dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(BOT_TZ).date()
            return dt == target_day
        except Exception:
            return target_day.strftime("%Y-%m-%d") in utc_date

    def competition_matches_for_day(self, code: str, day_offset: int = 0) -> List[Dict]:
        cache_key = f"day::{code}::{day_offset}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        comp = COMPETITIONS.get(code)
        if not comp:
            return []

        target_day = datetime.now(BOT_TZ).date() + timedelta(days=day_offset)
        target_str = target_day.strftime("%Y-%m-%d")
        out: List[Dict] = []

        league_id = comp.get("api_football_league_id")
        season = comp.get("season")
        if league_id and season:
            out.extend(self.api_football.fixtures_by_league_and_date(league_id, season, target_str))

        if len(out) < 6 and comp.get("football_data_code"):
            out.extend(self.football_data.competition_matches(comp["football_data_code"], target_str, target_str))

        if len(out) < 4 and comp.get("sportsdb_league_id"):
            out.extend(self.sportsdb.next_league_events(comp.get("sportsdb_league_id")))

        uniq: Dict[str, Dict] = {}
        for match in out:
            if not self._strict_target_day(match.get("utc_date", ""), target_day):
                continue
            match["competition_code"] = code
            match["competition"] = comp["name"]
            match["token"] = build_match_key(match.get("home_name", ""), match.get("away_name", ""), match.get("utc_date", ""))
            key = match["token"]
            uniq[key] = _merge_match(uniq[key], match) if key in uniq else match

        matches = list(uniq.values())
        matches.sort(key=lambda item: item.get("utc_date", ""))
        _set_cache(cache_key, matches, TTL_DAY)
        return matches

    def all_matches_for_day(self, day_offset: int = 0) -> List[Dict]:
        cache_key = f"all::{day_offset}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        uniq: Dict[str, Dict] = {}
        for code in COMPETITIONS:
            for match in self.competition_matches_for_day(code, day_offset):
                key = match["token"]
                uniq[key] = _merge_match(uniq[key], match) if key in uniq else match

        matches = list(uniq.values())
        matches.sort(key=lambda item: (item.get("competition", ""), item.get("utc_date", "")))
        _set_cache(cache_key, matches, TTL_ALL)
        return matches

    def preload_recent_for_priority_competitions(self, limit: int = 8) -> None:
        for code in list(COMPETITIONS.keys())[:limit]:
            try:
                self.competition_recent_results(code)
                self.competition_standings(code)
            except Exception:
                continue

    def competition_recent_results(self, code: str) -> List[Dict]:
        cache_key = f"recent::{code}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        comp = COMPETITIONS.get(code)
        if not comp:
            return []

        today = datetime.now(BOT_TZ).date()
        from_date = today - timedelta(days=45)
        out: List[Dict] = []

        league_id = comp.get("api_football_league_id")
        season = comp.get("season")
        if league_id and season:
            for offset in range(0, 35):
                date_str = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
                fixtures = self.api_football.fixtures_by_league_and_date(league_id, season, date_str)
                finished = [x for x in fixtures if x.get("home_score") is not None and x.get("away_score") is not None]
                out.extend(finished)
                if len(out) >= 24:
                    break

        if len(out) < 12 and comp.get("football_data_code"):
            out.extend(
                self.football_data.competition_matches(
                    comp["football_data_code"],
                    from_date.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                )
            )

        if len(out) < 12 and comp.get("sportsdb_league_id"):
            out.extend(self.sportsdb.past_league_events(comp.get("sportsdb_league_id")))

        uniq: Dict[str, Dict] = {}
        for match in out:
            match["competition_code"] = code
            match["competition"] = comp["name"]
            key = build_match_key(match.get("home_name", ""), match.get("away_name", ""), match.get("utc_date", ""))
            uniq[key] = _merge_match(uniq[key], match) if key in uniq else match

        matches = [m for m in uniq.values() if m.get("home_score") is not None and m.get("away_score") is not None]
        matches.sort(key=lambda item: item.get("utc_date", ""), reverse=True)
        _set_cache(cache_key, matches, TTL_RECENT)
        return matches

    def competition_standings(self, code: str) -> Dict[str, Dict]:
        cache_key = f"standings::{code}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        comp = COMPETITIONS.get(code)
        if not comp:
            return {}

        league_id = comp.get("api_football_league_id")
        season = comp.get("season")
        raw = self.api_football.standings(league_id, season) if league_id and season else {}
        normalized = {normalize_team_name(name): info for name, info in raw.items()}
        _set_cache(cache_key, normalized, TTL_STANDINGS)
        return normalized

    def get_table_row(self, competition_code: str, team_name: str) -> Dict:
        return self.competition_standings(competition_code).get(normalize_team_name(team_name), {})

    def find_finished_result(self, competition_code: str, home: str, away: str, kickoff_utc: str) -> Optional[Dict]:
        wanted_key = build_match_key(home, away, kickoff_utc)
        recent = self.competition_recent_results(competition_code)
        wanted_home = normalize_team_name(home)
        wanted_away = normalize_team_name(away)

        for match in recent:
            candidate_key = build_match_key(match.get("home_name", ""), match.get("away_name", ""), match.get("utc_date", ""))
            if candidate_key == wanted_key and match.get("home_score") is not None and match.get("away_score") is not None:
                return match

        for match in recent:
            if normalize_team_name(match.get("home_name", "")) == wanted_home and normalize_team_name(match.get("away_name", "")) == wanted_away:
                if match.get("home_score") is not None and match.get("away_score") is not None:
                    return match
        return None
