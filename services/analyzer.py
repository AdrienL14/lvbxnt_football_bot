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
            weight = max(0.52, 1.0 - (index * 0.09))
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
        }

    def _power(self, stats: Dict, context: Dict, table_row: Dict, home_bonus: float = 0.0) -> float:
        rank = table_row.get("rank") or 12
        points = table_row.get("points") or 0
        gd = table_row.get("goals_diff") or 0
        return (
            stats["weighted_points"] * 2.1
            + stats["weighted_goal_diff"] * 1.5
            + stats["avg_for"] * 5.3
            - stats["avg_against"] * 5.1
            + context["weighted_points"] * 1.4
            + context["clean_sheet_rate"] * 3.5
            + points * 0.09
            + gd * 0.15
            - rank * 0.48
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
                score += 1.1 if hs > a_s else -1.1 if hs < a_s else 0
            else:
                score += 1.1 if a_s > hs else -1.1 if a_s < hs else 0
        return round(score / checked, 2) if checked else 0.0

    def _expected_goals(self, home_stats: Dict, away_stats: Dict, home_ctx: Dict, away_ctx: Dict) -> Tuple[float, float, float]:
        exp_home = round((home_stats["avg_for"] * 0.56) + (away_stats["avg_against"] * 0.44) + (home_ctx["avg_for"] * 0.25) + 0.12, 2)
        exp_away = round((away_stats["avg_for"] * 0.56) + (home_stats["avg_against"] * 0.44) + (away_ctx["avg_for"] * 0.22), 2)
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
        if confidence >= 82:
            return "Faible"
        if confidence >= 70:
            return "Moyen"
        return "Élevé"

    def _short_reason(self, prediction: str, gap: float, total_goal_power: float, home_ctx: Dict, away_ctx: Dict) -> str:
        if prediction in {"X2", "Victoire extérieur", "Victoire extérieur & +1.5 buts"}:
            return "Extérieur plus solide dans la dynamique actuelle"
        if prediction in {"1X", "Victoire domicile", "Victoire domicile & +1.5 buts"}:
            return "Domicile plus solide dans la dynamique actuelle"
        if prediction == "BTTS Oui":
            return "Les deux équipes montrent un profil offensif"
        if "2.5" in prediction:
            return "Projection de buts au-dessus de la moyenne"
        return "Match équilibré avec légère tendance buts"

    def _balance_penalty(self, gap: float, total_goal_power: float) -> int:
        if abs(gap) < 1.15 and total_goal_power < 2.65:
            return 10
        if abs(gap) < 1.85 and total_goal_power < 2.25:
            return 7
        return 0

    def _overvalued_favorite_penalty(self, gap: float, home_table: Dict, away_table: Dict, home_ctx: Dict, away_ctx: Dict) -> int:
        home_rank = home_table.get("rank") or 12
        away_rank = away_table.get("rank") or 12
        rank_diff = away_rank - home_rank
        if gap > 2.4 and rank_diff >= 8 and home_ctx["weighted_points"] < 5.2:
            return 6
        if gap < -2.4 and (-rank_diff) >= 8 and away_ctx["weighted_points"] < 5.2:
            return 6
        return 0

    def _goal_market_penalty(self, total_goal_power: float, btts_strength: float, prediction: str) -> int:
        if prediction == "BTTS Oui" and btts_strength < 0.57:
            return 6
        if prediction == "Plus de 2.5 buts" and total_goal_power < 2.75:
            return 7
        if prediction == "Plus de 1.5 buts" and total_goal_power < 2.05:
            return 5
        return 0

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

        home_power = self._power(home_stats, home_ctx, home_table, home_bonus=2.15)
        away_power = self._power(away_stats, away_ctx, away_table, home_bonus=0.0)
        gap = round(home_power - away_power + self._h2h_bias(recent, match["home_name"], match["away_name"]), 2)

        exp_home, exp_away, total_goal_power = self._expected_goals(home_stats, away_stats, home_ctx, away_ctx)
        btts_strength = round((home_stats["btts_rate"] + away_stats["btts_rate"]) / 2, 2)
        primary, alt1, alt2 = self._score_candidates(exp_home, exp_away)

        if mode == "prudent":
            if gap >= 2.9:
                prediction, bet_type, confidence = "1X", "double_chance_home", min(90, round(69 + gap * 1.9))
                safe_bet, main_bet, value_bet = "1X", "1X", "Victoire domicile"
            elif gap <= -2.9:
                prediction, bet_type, confidence = "X2", "double_chance_away", min(90, round(69 + abs(gap) * 1.9))
                safe_bet, main_bet, value_bet = "X2", "X2", "Victoire extérieur"
            else:
                prediction, bet_type, confidence = "Plus de 1.5 buts", "over15", min(81, round(60 + total_goal_power * 2.3))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 1.5 buts", "Plus de 2.5 buts"
        elif mode == "agressif":
            if total_goal_power >= 3.05 and btts_strength >= 0.58:
                prediction, bet_type, confidence = "BTTS Oui", "btts", min(83, round(56 + total_goal_power * 3.0))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "BTTS Oui", "Plus de 2.5 buts"
            elif gap >= 4.3:
                prediction, bet_type, confidence = "Victoire domicile & +1.5 buts", "combo_home_goals", min(85, round(57 + gap * 2.0))
                safe_bet, main_bet, value_bet = "Victoire domicile", "Domicile & +1.5 buts", "Domicile & +2.5 buts"
            elif gap <= -4.3:
                prediction, bet_type, confidence = "Victoire extérieur & +1.5 buts", "combo_away_goals", min(85, round(57 + abs(gap) * 2.0))
                safe_bet, main_bet, value_bet = "Victoire extérieur", "Extérieur & +1.5 buts", "Extérieur & +2.5 buts"
            else:
                prediction, bet_type, confidence = "Plus de 2.5 buts", "over25", min(79, round(55 + total_goal_power * 2.7))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 2.5 buts", "BTTS Oui"
        else:
            if gap >= 3.15:
                prediction, bet_type, confidence = "Victoire domicile", "1x2_home", min(86, round(61 + gap * 2.0))
                safe_bet, main_bet, value_bet = "1X", "Victoire domicile", "Domicile & +1.5 buts"
            elif gap <= -3.15:
                prediction, bet_type, confidence = "Victoire extérieur", "1x2_away", min(86, round(61 + abs(gap) * 2.0))
                safe_bet, main_bet, value_bet = "X2", "Victoire extérieur", "Extérieur & +1.5 buts"
            elif total_goal_power >= 3.05:
                prediction, bet_type, confidence = "Plus de 2.5 buts", "over25", min(80, round(58 + total_goal_power * 2.3))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 2.5 buts", "BTTS Oui"
            else:
                prediction, bet_type, confidence = "Plus de 1.5 buts", "over15", min(77, round(58 + total_goal_power * 1.9))
                safe_bet, main_bet, value_bet = "Plus de 1.5 buts", "Plus de 1.5 buts", "Match nul"

        confidence -= reliability["confidence_penalty"]
        confidence -= self._balance_penalty(gap, total_goal_power)
        confidence -= self._overvalued_favorite_penalty(gap, home_table, away_table, home_ctx, away_ctx)
        confidence -= self._goal_market_penalty(total_goal_power, btts_strength, prediction)
        confidence = max(45, min(90, confidence))

        no_bet = False
        if confidence < 59 or reliability["data_status"] == "faible":
            no_bet = True
        if abs(gap) < 0.95 and total_goal_power < 2.45:
            no_bet = True
        if mode == "agressif" and confidence < 66:
            no_bet = True

        risk_level = self._risk_level(confidence, no_bet)
        if confidence >= 82 and not no_bet:
            value_flag = "✅ Value"
        elif confidence >= 70 and not no_bet:
            value_flag = "⚪ Correct"
        else:
            value_flag = "❌ À éviter"

        why_text = self._short_reason(prediction, gap, total_goal_power, home_ctx, away_ctx)
        sniper_score = round(
            confidence
            + min(abs(gap) * 2.8, 14)
            + (6 if reliability["data_status"] == "bon" else 0)
            + (4 if not no_bet else -8)
            - (6 if prediction in {"BTTS Oui", "Plus de 2.5 buts"} else 0),
            2,
        )

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
            "expected_home_goals": exp_home,
            "expected_away_goals": exp_away,
            "gap": gap,
            "total_goal_power": total_goal_power,
            "sniper_score": sniper_score,
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
                if analysis["confidence"] < 78:
                    continue
                if analysis["data_status"] != "bon":
                    continue
                if abs(analysis.get("gap", 0)) < 2.2 and analysis["bet_type"] != "over15":
                    continue
                picks.append({**match, "competition_code": code, **analysis})

        picks.sort(
            key=lambda item: (
                item.get("sniper_score", 0),
                item.get("confidence", 0),
                abs(item.get("gap", 0)),
            ),
            reverse=True,
        )

        final = []
        seen = set()
        for item in picks:
            key = f"{item.get('competition_code')}::{item.get('prediction')}"
            if key in seen:
                continue
            seen.add(key)
            final.append(item)
            if len(final) == 3:
                break
        return final
