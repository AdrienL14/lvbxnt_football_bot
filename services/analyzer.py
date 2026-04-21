from __future__ import annotations

from typing import Dict, List
from services.competition_catalog import COMPETITIONS


class MatchAnalyzer:
    def __init__(self, hub):
        self.hub = hub

    def _recent_team_form(self, recent: List[Dict], team_name: str) -> Dict:
        name = team_name.lower()
        played = wins = draws = losses = 0
        goals_for = goals_against = 0

        for m in recent:
            home = (m.get("home_name") or "").lower()
            away = (m.get("away_name") or "").lower()
            hs = m.get("home_score")
            a_s = m.get("away_score")
            if hs is None or a_s is None:
                continue

            if name == home:
                played += 1
                goals_for += hs
                goals_against += a_s
                if hs > a_s:
                    wins += 1
                elif hs == a_s:
                    draws += 1
                else:
                    losses += 1

            elif name == away:
                played += 1
                goals_for += a_s
                goals_against += hs
                if a_s > hs:
                    wins += 1
                elif hs == a_s:
                    draws += 1
                else:
                    losses += 1

        points = wins * 3 + draws
        return {
            "played": played,
            "points": points,
            "avg_for": round(goals_for / played, 2) if played else 0,
            "avg_against": round(goals_against / played, 2) if played else 0,
        }

    def analyze_match_fast(self, competition_code: str, match: Dict, mode: str = "normal") -> Dict:
        recent = self.hub.competition_recent_results(competition_code) if competition_code else []
        home_form = self._recent_team_form(recent, match["home_name"])
        away_form = self._recent_team_form(recent, match["away_name"])

        home_strength = home_form["points"] + home_form["avg_for"] * 2 - home_form["avg_against"]
        away_strength = away_form["points"] + away_form["avg_for"] * 2 - away_form["avg_against"]

        base_conf = 58
        if mode == "prudent":
            base_conf = 62
        elif mode == "agressif":
            base_conf = 54

        if home_strength > away_strength + 2:
            prediction = "Victoire domicile"
            probable_score = "2-0"
            confidence = min(88, round(base_conf + (home_strength - away_strength) * 3))
        elif away_strength > home_strength + 2:
            prediction = "Victoire extérieur"
            probable_score = "0-2"
            confidence = min(88, round(base_conf + (away_strength - home_strength) * 3))
        else:
            prediction = "Plus de 1.5 buts"
            probable_score = "1-1"
            confidence = min(82, round(base_conf + 6))

        return {
            "prediction": prediction,
            "confidence": confidence,
            "probable_score": probable_score,
            "home_form": home_form,
            "away_form": away_form,
        }

    def sniper_auto_scan(self, day_offset: int = 0) -> List[Dict]:
        picks = []
        for code in COMPETITIONS.keys():
            matches = self.hub.competition_matches_for_day(code, day_offset)
            for match in matches[:4]:
                analysis = self.analyze_match_fast(code, match, mode="normal")
                if analysis["confidence"] >= 70:
                    picks.append({
                        "competition_code": code,
                        "home_name": match["home_name"],
                        "away_name": match["away_name"],
                        "prediction": analysis["prediction"],
                        "confidence": analysis["confidence"],
                        "probable_score": analysis["probable_score"],
                    })
        picks.sort(key=lambda x: x["confidence"], reverse=True)
        return picks[:3]
