from __future__ import annotations

import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import BOT_TOKEN, PRELOAD_ON_START
from services.provider_hub import ProviderHub
from services.analyzer import MatchAnalyzer
from services.history_store import init_db, save_analysis, history_summary, settle_pending
from services.session_store import save_session, load_session
from utils.formatters import (
    format_match_list_message,
    format_analysis_message,
    format_sniper_summary_message,
    format_history_message,
)
from utils.team_normalizer import build_match_key
from utils.timezone_helper import now_local, format_day_choice_label, next_day_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

hub = ProviderHub()
analyzer = MatchAnalyzer(hub)

BTN_PRUDENT = "🛡️ Prudent"
BTN_NORMAL = "⚖️ Normal"
BTN_AGRESSIF = "🔥 Agressif"
BTN_SNIPER = "🎯 Sniper"
BTN_HISTORY = "📜 Historique"
BTN_SETTLE = "🔄 MAJ Résultats"
BTN_HOME = "🏠 Menu"

MODE_BY_BUTTON = {
    BTN_PRUDENT: "prudent",
    BTN_NORMAL: "normal",
    BTN_AGRESSIF: "agressif",
}


def _keyboard(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[label for label in row] for row in rows],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _main_menu() -> ReplyKeyboardMarkup:
    return _keyboard([
        [BTN_PRUDENT, BTN_NORMAL, BTN_AGRESSIF],
        [BTN_SNIPER],
        [BTN_HISTORY, BTN_SETTLE],
    ])


def _day_menu() -> ReplyKeyboardMarkup:
    labels = next_day_labels(3)
    return _keyboard([
        [labels[0], labels[1]],
        [labels[2]],
        [BTN_HOME],
    ])


def _match_button_label(match: dict) -> str:
    home = (match.get("home_name") or "").strip()
    away = (match.get("away_name") or "").strip()
    label = f"⚽ {home} vs {away}"
    return label[:60]


def _matches_menu(matches: list[dict]) -> ReplyKeyboardMarkup:
    rows = [[_match_button_label(match)] for match in matches[:18]]
    rows.append([BTN_HOME])
    return _keyboard(rows)


async def _refresh_results() -> int:
    return settle_pending(hub, now_local().strftime("%Y-%m-%d %H:%M:%S"))


async def _warm_cache() -> None:
    try:
        for offset in (0, 1, 2):
            hub.all_matches_for_day(offset)
        hub.preload_recent_for_priority_competitions(limit=8)
        logger.info("Cache V4 préchargé")
    except Exception as exc:
        logger.warning("Préchargement cache ignoré: %s", exc)


async def _send_home(chat, refreshed: int = 0) -> None:
    summary = history_summary()
    extra = f"\n🔄 Résultats réglés maintenant : {refreshed}" if refreshed else ""
    text = (
        "🤖 *LVBXNT Football Bot V4*\n\n"
        "Choisis directement ton mode d’analyse ci-dessous 👇\n\n"
        f"📊 Winrate : *{summary['global_winrate']}%* | Total : *{summary['total']}* | Pending : *{summary['pending']}*"
        f"{extra}"
    )
    await chat.reply_text(text, reply_markup=_main_menu(), parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_home(update.effective_message)
    if PRELOAD_ON_START:
        context.application.create_task(_warm_cache())


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        format_history_message(),
        reply_markup=_main_menu(),
        parse_mode="Markdown",
    )


async def settle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "⏳ Mise à jour des résultats en cours...",
        reply_markup=_main_menu(),
    )
    refreshed = await _refresh_results()
    summary = history_summary()
    await update.effective_message.reply_text(
        f"🔄 Mise à jour terminée\n\nRésultats réglés : *{refreshed}*\nWinrate global : *{summary['global_winrate']}%*",
        reply_markup=_main_menu(),
        parse_mode="Markdown",
    )


async def _show_day_picker(message, user_id: int, mode: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    current = load_session(user_id)
    current["mode"] = mode
    current["day_offset"] = current.get("day_offset", 0)
    save_session(user_id, current, now_local().strftime("%Y-%m-%d %H:%M:%S"))
    await message.reply_text(
        f"📊 *Analyse {mode.capitalize()}*\n\nChoisis directement la date à analyser 👇",
        reply_markup=_day_menu(),
        parse_mode="Markdown",
    )
    context.application.create_task(_warm_cache())


async def _show_matches(message, user_id: int, mode: str, day_offset: int) -> None:
    await message.reply_text("⏳ Chargement des matchs...", reply_markup=_day_menu())
    matches = hub.all_matches_for_day(day_offset)
    payload = {
        "mode": mode,
        "day_offset": day_offset,
        "matches_by_token": {m["token"]: m for m in matches},
    }
    save_session(user_id, payload, now_local().strftime("%Y-%m-%d %H:%M:%S"))
    await message.reply_text(
        format_match_list_message(format_day_choice_label(day_offset), matches, mode),
        reply_markup=_matches_menu(matches) if matches else _day_menu(),
        parse_mode="Markdown",
    )


def _resolve_day_offset(text: str) -> int | None:
    labels = next_day_labels(3)
    for idx, label in enumerate(labels):
        if text == label:
            return idx
    return None


def _resolve_selected_match(user_id: int, text: str) -> tuple[dict | None, str, int]:
    session = load_session(user_id)
    mode = session.get("mode", "normal")
    day_offset = session.get("day_offset", 0)
    for match in (session.get("matches_by_token") or {}).values():
        if _match_button_label(match) == text:
            return match, mode, day_offset
    return None, mode, day_offset


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    text = (message.text or "").strip()
    user_id = update.effective_user.id
    session = load_session(user_id)

    if text in {"/start", BTN_HOME, "Menu", "🏠 Home"}:
        await _send_home(message)
        return

    if text in MODE_BY_BUTTON:
        await _show_day_picker(message, user_id, MODE_BY_BUTTON[text], context)
        return

    if text == BTN_SNIPER:
        current = load_session(user_id)
        current["mode"] = "sniper"
        save_session(user_id, current, now_local().strftime("%Y-%m-%d %H:%M:%S"))
        await message.reply_text(
            "🎯 *Sniper Pro*\n\nChoisis directement la date à scanner 👇",
            reply_markup=_day_menu(),
            parse_mode="Markdown",
        )
        context.application.create_task(_warm_cache())
        return

    if text == BTN_HISTORY:
        await update.effective_message.reply_text(
            format_history_message(),
            reply_markup=_main_menu(),
            parse_mode="Markdown",
        )
        return

    if text == BTN_SETTLE:
        await settle_command(update, context)
        return

    day_offset = _resolve_day_offset(text)
    if day_offset is not None:
        mode = session.get("mode", "normal")
        if mode == "sniper":
            await message.reply_text("⏳ Scan sniper en cours...", reply_markup=_day_menu())
            picks = analyzer.sniper_auto_scan(day_offset=day_offset)
            if not picks:
                await message.reply_text(
                    f"🎯 *SNIPER — {format_day_choice_label(day_offset)}*\n\nNO VALUE BET",
                    reply_markup=_day_menu(),
                    parse_mode="Markdown",
                )
                return
            await message.reply_text(
                format_sniper_summary_message(format_day_choice_label(day_offset), picks),
                reply_markup=_main_menu(),
                parse_mode="Markdown",
            )
            for item in picks:
                save_analysis({
                    "created_at": now_local().strftime("%Y-%m-%d %H:%M:%S"),
                    "user_id": user_id,
                    "mode": "sniper",
                    "competition_code": item.get("competition_code"),
                    "competition": item.get("competition"),
                    "day_label": format_day_choice_label(day_offset),
                    "kickoff_utc": item.get("utc_date"),
                    "match_key": build_match_key(item.get("home_name", ""), item.get("away_name", ""), item.get("utc_date", "")),
                    "home_name": item.get("home_name"),
                    "away_name": item.get("away_name"),
                    "prediction": item.get("prediction"),
                    "bet_type": item.get("bet_type"),
                    "confidence": item.get("confidence"),
                    "score_prediction": item.get("score_primary"),
                    "provider": item.get("provider"),
                    "note": item.get("why_text"),
                })
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=format_analysis_message(item, item, "sniper"),
                    parse_mode="Markdown",
                    reply_markup=_main_menu(),
                )
            return

        await _show_matches(message, user_id, mode, day_offset)
        return

    match, mode, day_offset = _resolve_selected_match(user_id, text)
    if match:
        await message.reply_text(
            "⏳ Analyse en cours...",
            reply_markup=_matches_menu(list((session.get("matches_by_token") or {}).values())),
        )
        analysis = analyzer.analyze_match_fast(
            competition_code=match.get("competition_code", ""),
            match=match,
            mode=mode,
        )
        save_analysis({
            "created_at": now_local().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "mode": mode,
            "competition_code": match.get("competition_code"),
            "competition": match.get("competition"),
            "day_label": format_day_choice_label(day_offset),
            "kickoff_utc": match.get("utc_date"),
            "match_key": build_match_key(match.get("home_name", ""), match.get("away_name", ""), match.get("utc_date", "")),
            "home_name": match.get("home_name"),
            "away_name": match.get("away_name"),
            "prediction": analysis.get("prediction"),
            "bet_type": analysis.get("bet_type"),
            "confidence": analysis.get("confidence"),
            "score_prediction": analysis.get("score_primary"),
            "provider": match.get("provider"),
            "note": analysis.get("why_text"),
        })
        await message.reply_text(
            format_analysis_message(match, analysis, mode),
            reply_markup=_matches_menu(list((session.get("matches_by_token") or {}).values())),
            parse_mode="Markdown",
        )
        return

    await message.reply_text("⚠️ Choisis un bouton du menu pour continuer.", reply_markup=_main_menu())


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN manquant dans .env")
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("settle", settle_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("🚀 LVBXNT Football Bot V4 lancé...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
