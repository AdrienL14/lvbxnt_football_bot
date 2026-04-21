from __future__ import annotations

from services.history_store import read_history


def format_match_list_message(day_label: str, matches: list[dict]) -> str:
    if not matches:
        return f"📅 *{day_label}*\n\nAucun match disponible."
    text = f"📅 *{day_label}*\n\nClique sur un match pour recevoir l'analyse dans un message séparé.\n\n"
    for m in matches[:18]:
        text += (
            f"• *{m['home_name']} vs {m['away_name']}*\n"
            f"🏆 {m.get('competition', 'Compétition')}\n"
            f"🕒 {m.get('utc_date', '')[:16].replace('T', ' ')}\n\n"
        )
    return text[:4000]


def format_analysis_message(match: dict, analysis: dict, mode: str) -> str:
    return (
        f"📊 *Analyse {mode.capitalize()}*\n\n"
        f"*{match['home_name']} vs {match['away_name']}*\n"
        f"🏆 {match.get('competition', 'Compétition')}\n\n"
        f"🎯 Pronostic : *{analysis['prediction']}*\n"
        f"📈 Confiance : *{analysis['confidence']}%*\n"
        f"🔮 Score probable : *{analysis['probable_score']}*\n"
    )


def format_sniper_message(day_label: str, picks: list[dict]) -> str:
    lines = [f"🎯 *SNIPER — {day_label}*\n"]
    for i, item in enumerate(picks, start=1):
        lines.append(
            f"{i}. *{item['home_name']} vs {item['away_name']}*\n"
            f"🎯 {item['prediction']} ({item['confidence']}%)\n"
            f"🔮 {item['probable_score']}\n"
        )
    return "\n".join(lines)


def format_history_message() -> str:
    items = read_history()
    if not items:
        return "📜 *Historique vide*"
    lines = ["📜 *Historique*\n"]
    for item in items[:20]:
        lines.append(
            f"• *{item.get('match','') }*\n"
            f"🎯 {item.get('prediction','')} ({item.get('confidence','')}%)\n"
            f"🔮 {item.get('score','')}\n"
            f"🕒 {item.get('created_at','')}\n"
        )
    return "\n".join(lines)
