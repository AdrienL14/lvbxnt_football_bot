from __future__ import annotations

from services.history_store import read_recent, history_summary
from utils.timezone_helper import format_local_kickoff


def format_match_list_message(day_label: str, matches: list[dict], mode: str) -> str:
    if not matches:
        return f"📅 *{day_label}*\n\nAucun match trouvé."
    lines = [f"📅 *{day_label}*", f"🎛️ Mode: *{mode.capitalize()}*", "Clique sur un match pour lancer l’analyse.\n"]
    for match in matches[:18]:
        lines.append(
            f"• *{match['home_name']} vs {match['away_name']}*\n"
            f"🏆 {match.get('competition', 'Compétition')}\n"
            f"🕒 {format_local_kickoff(match.get('utc_date', ''))}"
        )
    return "\n\n".join(lines)[:4000]


def format_analysis_message(match: dict, analysis: dict, mode: str) -> str:
    no_bet_line = "⛔ *NO BET* : data trop faible ou confiance trop basse\n\n" if analysis.get("no_bet") else ""
    return (
        f"📊 *Analyse {mode.capitalize()}*\n\n"
        f"*{match['home_name']} vs {match['away_name']}*\n"
        f"🏆 {match.get('competition', 'Compétition')}\n"
        f"🕒 {format_local_kickoff(match.get('utc_date', ''))}\n\n"
        f"{no_bet_line}"
        f"🎯 Pronostic : *{analysis['prediction']}*\n"
        f"📈 Confiance : *{analysis['confidence']}%*\n"
        f"⚠️ Risque : *{analysis['risk_level']}*\n"
        f"📌 Data : *{analysis['data_status']}*\n"
        f"🧠 Pourquoi : *{analysis['why_text']}*\n"
        f"📝 Note data : *{analysis['data_note']}*\n\n"
        f"🏠 Forme domicile ciblée : *{analysis['home_form']['form_string']}*\n"
        f"🛫 Forme extérieur ciblée : *{analysis['away_form']['form_string']}*\n"
        f"📊 Rang estimé : *{analysis['home_rank']} vs {analysis['away_rank']}*\n\n"
        f"💰 Safe : *{analysis['safe_bet']}*\n"
        f"🔥 Main : *{analysis['main_bet']}*\n"
        f"💎 Value : *{analysis['value_bet']}*\n\n"
        f"🔮 Score probable : *{analysis['score_primary']}*\n"
        f"▫️ Alt 1 : {analysis['score_alt1']}\n"
        f"▫️ Alt 2 : {analysis['score_alt2']}\n\n"
        f"📍 Verdict : *{analysis['value_flag']}*"
    )


def format_sniper_summary_message(day_label: str, picks: list[dict]) -> str:
    lines = [f"🎯 *SNIPER — {day_label}*\n"]
    for i, item in enumerate(picks, start=1):
        lines.append(
            f"{i}. *{item['home_name']} vs {item['away_name']}*\n"
            f"🏆 {item.get('competition', '')}\n"
            f"🎯 {item['prediction']} ({item['confidence']}%)\n"
            f"⚠️ {item['risk_level']}"
        )
    lines.append("\nLes analyses détaillées arrivent juste après.")
    return "\n".join(lines)


def format_history_message() -> str:
    items = read_recent(20)
    summary = history_summary()
    if not items:
        return "📜 *Historique vide*"
    lines = [
        "📜 *Historique*",
        f"📊 Global: *{summary['global_winrate']}%* | Total: *{summary['total']}* | Réglés: *{summary['settled']}* | En attente: *{summary['pending']}*",
        f"🛡️ Prudent: *{summary['by_mode']['prudent']}%* | ⚖️ Normal: *{summary['by_mode']['normal']}%*",
        f"🔥 Agressif: *{summary['by_mode']['agressif']}%* | 🎯 Sniper: *{summary['by_mode']['sniper']}%*\n",
    ]
    for item in items:
        status = "✅ Gagné" if item.get("won") == 1 else "❌ Perdu" if item.get("won") == 0 else "🕒 Pending"
        final_score = item.get("final_score") or "-"
        lines.append(
            f"• *{item.get('home_name','')} vs {item.get('away_name','')}*\n"
            f"🎯 {item.get('prediction','')} ({item.get('confidence','')}%)\n"
            f"🔮 {item.get('score_prediction','')} | Final: {final_score}\n"
            f"📌 {status} | {item.get('created_at','')}"
        )
    return "\n\n".join(lines)[:4000]
