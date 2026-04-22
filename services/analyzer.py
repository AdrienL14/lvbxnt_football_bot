from __future__ import annotations

from typing import Dict, List, Tuple
from services.competition_catalog import COMPETITIONS
from services.reliability_engine import build_reliability
from utils.team_normalizer import normalize_team_name

class MatchAnalyzer:
    def __init__(self, hub):
        self.hub = hub

    def _slice_team(self, recent: List[Dict], team_name: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        overall, home_only, away_only = [], [], []
        target = normalize_team_name(team_name)
        for match in recent:
            home = normalize_team_name(match.get("home_name", ""))
            away = normalize_team_name(match.get("away_name", ""))
            hs = match.get("home_score")
            a_s = match.get("away_score")
            if hs is None or a_s is None:
                continue
            if target == home:
                overall.append(match)
                home_only.append(match)
            elif target == away:
                overall.append(match)
                away_only.append(match)
        return overall[:8], home_only[:5], away_only[:5]

    def _stats(self, matches: List[Dict], team_name: str) -> Dict:
        target = normalize_team_name(team_name)
        played = wins = draws = losses = 0
        goals_for = goals_against = clean_sheets = btts_yes = 0
        over15 = over25 = over35 = 0
        weighted_points = 0.0
        weighted_goal_diff = 0.0
        for index, match in enumerate(matches):
            home = normalize_team_name(match.get("home_name", ""))
            away = normalize_team_name(match.get("away_name", ""))
            hs = match.get("home_score")
            a_s = match.get("away_score")
            if hs is None or a_s is None:
                continue
            if target == home:
                gf, ga = hs, a_s
            elif target == away:
                gf, ga = a_s, hs
            else:
                continue
            weight = max(0.55, 1.0 - (index * 0.08))
            played += 1
            goals_for += gf
            goals_against += ga
            weighted_goal_diff += (gf - ga) * weight
            if gf > ga:
                wins += 1
                weighted_points += 3 * weight
            elif gf == ga:
                draws += 1
                weighted_points += 1 * weight
            else:
                losses += 1
            if ga == 0:
                clean_sheets += 1
            if gf > 0 and ga > 0:
                btts_yes += 1
            if gf + ga >= 2:
                over15 += 1
            if gf + ga >= 3:
                over25 += 1
            if gf + ga >= 4:
                over35 += 1
        return {
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "points": wins * 3 + draws,
            "weighted_points": round(weighted_points, 2),
            "weighted_goal_diff": round(weighted_goal_diff, 2),
            "avg_for": round(goals_for / played, 2) if played else 0,
            "avg_against": round(goals_against / played, 2) if played else 0,
            "clean_sheet_rate": round(clean_sheets / played, 2) if played else 0,
            "btts_rate": round(btts_yes / played, 2) if played else 0,
            "over15_rate": round(over15 / played, 2) if played else 0,
            "over25_rate": round(over25 / played, 2) if played else 0,
            "over35_rate": round(over35 / played, 2) if played else 0,
            "form_string": f"{wins}V-{draws}N-{losses}D",
        }

    def _power(self, stats: Dict, context: Dict, table_row: Dict, home_bonus: float = 0.0) -> float:
        rank = table_row.get("rank") or 12
        points = table_row.get("points") or 0
        gd = table_row.get("goals_diff") or 0
        return (
            stats["weighted_points"] * 2.0
            + stats["weighted_goal_diff"] * 1.4
            + stats["avg_for"] * 5.4
            - stats["avg_against"] * 4.9
            + context["weighted_points"] * 1.3
            + context["clean_sheet_rate"] * 3.2
            + points * 0.09
            + gd * 0.15
            - rank * 0.45
            + home_bonus
        )

    def _h2h_bias(self, recent: List[Dict], home_name: str, away_name: str) -> float:
        home = normalize_team_name(home_name)
        away = normalize_team_name(away_name)
        score = 0.0
        checked = 0
        for match in recent[:18]:
            h = normalize_team_name(match.get("home_name", ""))
            a = normalize_team_name(match.get("away_name", ""))
            hs = match.get("home_score")
            a_s = match.get("away_score")
            if hs is None or a_s is None:
                continue
            if {home, away} != {h, a}:
                continue
            checked += 1
            if h == home:
                score += 1.2 if hs > a_s else -1.2 if hs < a_s else 0
            else:
                score += 1.2 if a_s > hs else -1.2 if a_s < hs else 0
        return round(score / checked, 2) if checked else 0.0

    def _expected_goals(self, home_stats: Dict, away_stats: Dict, home_ctx: Dict, away_ctx: Dict) -> Tuple[float, float, float]:
        exp_home = round((home_stats["avg_for"] * 0.55) + (away_stats["avg_against"] * 0.45) + (home_ctx["avg_for"] * 0.25) + 0.15, 2)
        exp_away = round((away_stats["avg_for"] * 0.55) + (home_stats["avg_against"] * 0.45) + (away_ctx["avg_for"] * 0.20), 2)
        total = round(exp_home + exp_away, 2)
        return exp_home, exp_away, total

    def _score_candidates(self, exp_home: float, exp_away: float) -> Tuple[str, str, str]:
        primary = f"{max(0, round(exp_home))}-{max(0, round(exp_away))}"
        alt1 = f"{max(0, round(exp_home + 0.4))}-{max(0, round(exp_away))}"
        alt2 = f"{max(0, round(exp_home))}-{max(0, round(exp_away + 0.4))}"
        return primary, alt1, alt2

    def _risk_level(self, confidence: int, no_bet: bool) -> str:
        if no_bet:
            return "Élevé"
        if confidence >= 81:
            return "Faible"
        if confidence >= 69:
            return "Moyen"
        return "Élevé"

    def analyze_match_fast(self, competition_code: str, match: Dict, mode: str = "normal") -> Dict:
        recent = self.hub.competition_recent_results(competition_code) if competition_code else []
        home_overall, home_home, _ = self._slice_team(recent, match["home_name"])
        away_overall, _, away_away = self._slice_team(recent, match["away_name"])
        home_stats = self._stats(home_overall, match["home_name"])
        away_stats = self._stats(away_overall, match["away_name"])
        home_ctx = self._stats(home_home, match["home_name"])
        away_ctx = self._stats(away_away, match["away_name"])
        home_table = self.hub.get_table_row(competition_code, match["home_name"])
        away_table = self.hub.get_table_row(competition_code, match["away_name"])
        reliability = build_reliability(home_stats, away_stats, home_table, away_table)
        home_power = self._power(home_stats, home_ctx, home_table, home_bonus=2.2)
        away_power = self._power(away_stats, away_ctx, away_table, home_bonus=0.0)
        gap = round(home_power - away_power + self._h2h_bias(recent, match["home_name"], match["away_name"]), 2)
        exp_home, exp_away, total_goal_power = self._expected_goals(home_stats, away_stats, home_ctx, away_ctx)
        btts_strength = round((home_stats["btts_rate"] + away_stats["btts_rate"]) / 2, 2)
        primary, alt1, alt2 = self._score_candidates(exp_home, exp_away)
        if mode == "prudent":
            if gap >= 2.8:
                prediction, bet_type, confidence = "1X", "double_chance_home", min(90, round(68 + gap * 2.0))
                safe_bet, main_bet, value_bet = "1X", "1X", "Victoire domicile"
                why_text = "domicile plus stable + meilleure forme"
            elif gap <= -2.8:
                prediction, bet_type, confidence = "X2", "double_chance_away", min(90, round(68 + abs(gap) * 2.0))
                safe_bet, main_bet, value_bet = "X2", "X2", "Victoire extérieur"
                why_text = "extérieur plus solide sur la dynamique"
            else:
                prediction, bet_type, confidence = "Plus de 1.5 buts", "over15", min(80, round(60 + total_goal_power * 2.4))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 1.5 buts", "Plus de 2.5 buts"
                why_text = "match serré mais profil buts jouable"
        elif mode == "agressif":
            if total_goal_power >= 3.0 and btts_strength >= 0.56:
                prediction, bet_type, confidence = "BTTS Oui", "btts", min(82, round(56 + total_goal_power * 3.0))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "BTTS Oui", "Plus de 2.5 buts"
                why_text = "deux équipes marquent souvent"
            elif gap >= 4.2:
                prediction, bet_type, confidence = "Victoire domicile & +1.5 buts", "combo_home_goals", min(85, round(57 + gap * 2.1))
                safe_bet, main_bet, value_bet = "Victoire domicile", "Domicile & +1.5 buts", "Domicile & +2.5 buts"
                why_text = "écart net + projection buts favorable"
            elif gap <= -4.2:
                prediction, bet_type, confidence = "Victoire extérieur & +1.5 buts", "combo_away_goals", min(85, round(57 + abs(gap) * 2.1))
                safe_bet, main_bet, value_bet = "Victoire extérieur", "Extérieur & +1.5 buts", "Extérieur & +2.5 buts"
                why_text = "écart net même hors domicile"
            else:
                prediction, bet_type, confidence = "Plus de 2.5 buts", "over25", min(78, round(55 + total_goal_power * 2.8))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 2.5 buts", "BTTS Oui"
                why_text = "lecture offensive plus agressive"
        else:
            if gap >= 3.1:
                prediction, bet_type, confidence = "Victoire domicile", "1x2_home", min(86, round(61 + gap * 2.0))
                safe_bet, main_bet, value_bet = "1X", "Victoire domicile", "Domicile & +1.5 buts"
                why_text = "forme, classement et contexte domicile alignés"
            elif gap <= -3.1:
                prediction, bet_type, confidence = "Victoire extérieur", "1x2_away", min(86, round(61 + abs(gap) * 2.0))
                safe_bet, main_bet, value_bet = "X2", "Victoire extérieur", "Extérieur & +1.5 buts"
                why_text = "meilleure dynamique globale à l’extérieur"
            elif total_goal_power >= 3.1:
                prediction, bet_type, confidence = "Plus de 2.5 buts", "over25", min(80, round(58 + total_goal_power * 2.4))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 2.5 buts", "BTTS Oui"
                why_text = "projection buts au-dessus de la moyenne"
            else:
                prediction, bet_type, confidence = "Plus de 1.5 buts", "over15", min(77, round(58 + total_goal_power * 2.0))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 1.5 buts", "Match nul"
                why_text = "match équilibré mais minimum buts probable"
        confidence = max(48, confidence - reliability["confidence_penalty"])
        no_bet = confidence < 58 or reliability["data_status"] == "faible"
        if mode == "agressif" and reliability["data_status"] != "bon" and confidence < 66:
            no_bet = True
        risk_level = self._risk_level(confidence, no_bet)
        if confidence >= 82 and not no_bet:
            value_flag = "✅ Value"
        elif confidence >= 69 and not no_bet:
            value_flag = "⚪ Correct"
        else:
            value_flag = "❌ À éviter"
        home_rank = home_table.get("rank") or "?"
        away_rank = away_table.get("rank") or "?"
        why_text = f"{why_text} | gap {gap} | rang {home_rank} vs {away_rank}"
        return {
            "prediction": prediction,
            "bet_type": bet_type,
            "confidence": confidence,
            "score_primary": primary,
            "score_alt1": alt1,
            "score_alt2": alt2,
            "safe_bet": safe_bet,
            "main_bet": main_bet,
            "value_bet": value_bet,
            "value_flag": value_flag,
            "risk_level": risk_level,
            "why_text": why_text,
            "no_bet": no_bet,
            "data_status": reliability["data_status"],
            "data_note": reliability["data_note"],
            "home_form": home_stats,
            "away_form": away_stats,
            "home_rank": home_rank,
            "away_rank": away_rank,
            "expected_home_goals": exp_home,
            "expected_away_goals": exp_away,
        }

    def sniper_auto_scan(self, day_offset: int = 0) -> List[Dict]:
        picks = []
        for code in COMPETITIONS:
            matches = self.hub.competition_matches_for_day(code, day_offset)
            for match in matches[:8]:
                analysis = self.analyze_match_fast(code, match, mode="prudent")
                if analysis["no_bet"]:
                    continue
                if analysis["bet_type"] not in {"double_chance_home", "double_chance_away", "1x2_home", "1x2_away", "over15"}:
                    continue
                if analysis["confidence"] < 79 or analysis["data_status"] != "bon":
                    continue
                picks.append({**match, "competition_code": code, **analysis})
        picks.sort(key=lambda item: (item["confidence"], item.get("expected_home_goals", 0) + item.get("expected_away_goals", 0)), reverse=True)
        return picks[:4]
