from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import BOT_TOKEN
from services.provider_hub import ProviderHub
from services.analyzer import MatchAnalyzer
from services.history_store import append_history
from services.competition_catalog import COMPETITIONS
from utils.formatters import (
    format_match_list_message,
    format_analysis_message,
    format_sniper_message,
    format_history_message,
)
from utils.timezone_helper import get_bot_tz, format_day_label

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TZ = get_bot_tz()
hub = ProviderHub()
analyzer = MatchAnalyzer(hub)

# session légère par utilisateur
USER_SESSION: Dict[int, Dict[str, Any]] = {}


def _main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ Prudent", callback_data="mode:prudent"),
         InlineKeyboardButton("⚖️ Normal", callback_data="mode:normal"),
         InlineKeyboardButton("🔥 Agressif", callback_data="mode:agressif")],
        [InlineKeyboardButton("🎯 Sniper", callback_data="sniper:choose_day")],
        [InlineKeyboardButton("📜 Historique", callback_data="history:show")],
    ])


def _day_picker(prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for offset in [0, 1, 2]:
        rows.append([InlineKeyboardButton(format_day_label(offset), callback_data=f"{prefix}:{offset}")])
    rows.append([InlineKeyboardButton("⬅️ Retour", callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


def _matches_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in matches[:18]:
        label = f"🔎 {item['home_name']} vs {item['away_name']}"
        rows.append([InlineKeyboardButton(label[:64], callback_data=f"analyze:{item['token']}")])
    rows.append([InlineKeyboardButton("⬅️ Retour", callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 *Lvbxnt Football Bot*\n\n"
        "Choisis un mode d’analyse.\n"
        "Ensuite tu pourras choisir : aujourd’hui, demain ou après-demain."
    )
    await update.effective_message.reply_text(text, reply_markup=_main_menu(), parse_mode="Markdown")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id

    await query.answer("⚡")

    if data == "back:menu":
        await query.edit_message_text(
            "🤖 *Lvbxnt Football Bot*\n\nChoisis un mode d’analyse.",
            reply_markup=_main_menu(),
            parse_mode="Markdown",
        )
        return

    if data.startswith("mode:"):
        mode = data.split(":", 1)[1]
        USER_SESSION.setdefault(user_id, {})
        USER_SESSION[user_id]["mode"] = mode

        await query.edit_message_text(
            f"📅 *Mode {mode.capitalize()}*\n\nChoisis la date à analyser.",
            reply_markup=_day_picker("day"),
            parse_mode="Markdown",
        )
        return

    if data.startswith("day:"):
        day_offset = int(data.split(":", 1)[1])
        mode = USER_SESSION.get(user_id, {}).get("mode", "normal")
        # Par défaut on garde la même logique actuelle : on liste les matchs de la ligue / source principale du bot.
        # Ici on récupère un agrégat cross-compétitions pour la date choisie.
        matches = hub.all_matches_for_day(day_offset)

        USER_SESSION.setdefault(user_id, {})
        USER_SESSION[user_id]["day_offset"] = day_offset
        USER_SESSION[user_id]["matches_by_token"] = {m["token"]: m for m in matches}

        text = format_match_list_message(format_day_label(day_offset), matches)
        await query.edit_message_text(text, reply_markup=_matches_keyboard(matches), parse_mode="Markdown")
        return

    if data == "sniper:choose_day":
        await query.edit_message_text(
            "🎯 *Sniper Mode*\n\nChoisis la date à scanner.",
            reply_markup=_day_picker("sniper"),
            parse_mode="Markdown",
        )
        return

    if data.startswith("sniper:") and data != "sniper:choose_day":
        day_offset = int(data.split(":", 1)[1])
        picks = analyzer.sniper_auto_scan(day_offset=day_offset)

        if not picks:
            await query.edit_message_text(
                f"🎯 *SNIPER — {format_day_label(day_offset)}*\n\nN/A — aucun match propre trouvé.",
                reply_markup=_main_menu(),
                parse_mode="Markdown",
            )
            return

        # Historique : on enregistre aussi les picks sniper
        for item in picks:
            append_history({
                "created_at": datetime.now(BOT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                "mode": "sniper",
                "day_label": format_day_label(day_offset),
                "match": f"{item['home_name']} vs {item['away_name']}",
                "prediction": item["prediction"],
                "confidence": item["confidence"],
                "score": item["probable_score"],
            })

        await query.edit_message_text(
            format_sniper_message(format_day_label(day_offset), picks),
            reply_markup=_main_menu(),
            parse_mode="Markdown",
        )
        return

    if data == "history:show":
        await query.edit_message_text(
            format_history_message(),
            reply_markup=_main_menu(),
            parse_mode="Markdown",
        )
        return

    if data.startswith("analyze:"):
        token = data.split(":", 1)[1]
        session = USER_SESSION.get(user_id, {})
        match = (session.get("matches_by_token") or {}).get(token)
        mode = session.get("mode", "normal")

        if not match:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Analyse indisponible. Recharge la liste.",
            )
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏳ Analyse en cours...",
        )

        analysis = analyzer.analyze_match_fast(
            competition_code=match.get("competition_code", ""),
            match=match,
            mode=mode,
        )

        append_history({
            "created_at": datetime.now(BOT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode,
            "day_label": session.get("day_offset", 0),
            "match": f"{match['home_name']} vs {match['away_name']}",
            "prediction": analysis["prediction"],
            "confidence": analysis["confidence"],
            "score": analysis["probable_score"],
        })

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=format_analysis_message(match, analysis, mode),
            parse_mode="Markdown",
        )
        return


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(on_callback))
    print("🚀 Bot lancé...")
    application.run_polling()


if __name__ == "__main__":
    main()
