from __future__ import annotations

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import BOT_TOKEN
from services.provider_hub import ProviderHub
from services.analyzer import MatchAnalyzer
from services.history_store import init_db, save_analysis, history_summary, settle_pending
from services.session_store import save_session, load_session
from utils.formatters import format_match_list_message, format_analysis_message, format_sniper_summary_message, format_history_message
from utils.team_normalizer import build_match_key
from utils.timezone_helper import now_local, format_day_label

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

hub = ProviderHub()
analyzer = MatchAnalyzer(hub)


def _main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ Prudent", callback_data="mode:prudent"), InlineKeyboardButton("⚖️ Normal", callback_data="mode:normal"), InlineKeyboardButton("🔥 Agressif", callback_data="mode:agressif")],
        [InlineKeyboardButton("🎯 Sniper", callback_data="sniper:choose_day")],
        [InlineKeyboardButton("📜 Historique", callback_data="history:show"), InlineKeyboardButton("🔄 MAJ Résultats", callback_data="history:settle")],
    ])


def _day_picker(prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    rows = []
    for offset in [0, 1, 2]:
        rows.append([InlineKeyboardButton(format_day_label(offset), callback_data=f"{prefix}:{offset}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=back_callback), InlineKeyboardButton("🏠 Home", callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


def _matches_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in matches[:18]:
        label = f"🔎 {item['home_name']} vs {item['away_name']}"
        rows.append([InlineKeyboardButton(label[:64], callback_data=f"analyze:{item['token']}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="back:day_picker"), InlineKeyboardButton("🏠 Home", callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


async def _refresh_results() -> int:
    return settle_pending(hub, now_local().strftime("%Y-%m-%d %H:%M:%S"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    refreshed = await _refresh_results()
    summary = history_summary()
    extra = f"\n🔄 Résultats réglés maintenant: *{refreshed}*" if refreshed else ""
    text = (
        "🤖 *LVBXNT Football Bot V2*\n\n"
        "Analyse plus propre, historique réel et suivi auto des résultats.\n\n"
        f"📊 Winrate suivi: *{summary['global_winrate']}%* | Analyses: *{summary['total']}* | Pending: *{summary['pending']}*"
        f"{extra}"
    )
    await update.effective_message.reply_text(text, reply_markup=_main_menu(), parse_mode="Markdown")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _refresh_results()
    await update.effective_message.reply_text(format_history_message(), parse_mode="Markdown")


async def settle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    refreshed = await _refresh_results()
    summary = history_summary()
    await update.effective_message.reply_text(
        f"🔄 Mise à jour terminée\n\nRésultats réglés: *{refreshed}*\nWinrate global: *{summary['global_winrate']}%*",
        parse_mode="Markdown",
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id
    await query.answer("⚡")

    if data in {"back:menu", "history:settle"}:
        refreshed = await _refresh_results()
        summary = history_summary()
        extra = f"\n🔄 Réglés maintenant: *{refreshed}*" if data == "history:settle" else ""
        await query.edit_message_text(
            "🤖 *LVBXNT Football Bot V2*\n\n"
            "Choisis un mode d’analyse.\n\n"
            f"📊 Winrate: *{summary['global_winrate']}%* | Total: *{summary['total']}* | Pending: *{summary['pending']}*"
            f"{extra}",
            reply_markup=_main_menu(),
            parse_mode="Markdown",
        )
        return

    if data == "back:day_picker":
        session = load_session(user_id)
        mode = session.get("mode", "normal")
        await query.edit_message_text(f"📅 *Mode {mode.capitalize()}*\n\nChoisis la date à analyser.", reply_markup=_day_picker("day", "back:menu"), parse_mode="Markdown")
        return

    if data == "back:sniper_picker":
        await query.edit_message_text("🎯 *Sniper Mode*\n\nChoisis la date à scanner.", reply_markup=_day_picker("sniper", "back:menu"), parse_mode="Markdown")
        return

    if data.startswith("mode:"):
        mode = data.split(":", 1)[1]
        current = load_session(user_id)
        current["mode"] = mode
        save_session(user_id, current, now_local().strftime("%Y-%m-%d %H:%M:%S"))
        await query.edit_message_text(f"📅 *Mode {mode.capitalize()}*\n\nChoisis la date à analyser.", reply_markup=_day_picker("day", "back:menu"), parse_mode="Markdown")
        return

    if data.startswith("day:"):
        day_offset = int(data.split(":", 1)[1])
        session = load_session(user_id)
        mode = session.get("mode", "normal")
        matches = hub.all_matches_for_day(day_offset)
        payload = {"mode": mode, "day_offset": day_offset, "matches_by_token": {m["token"]: m for m in matches}}
        save_session(user_id, payload, now_local().strftime("%Y-%m-%d %H:%M:%S"))
        await query.edit_message_text(format_match_list_message(format_day_label(day_offset), matches, mode), reply_markup=_matches_keyboard(matches), parse_mode="Markdown")
        return

    if data == "sniper:choose_day":
        await query.edit_message_text("🎯 *Sniper Mode*\n\nChoisis la date à scanner.", reply_markup=_day_picker("sniper", "back:menu"), parse_mode="Markdown")
        return

    if data.startswith("sniper:") and data != "sniper:choose_day":
        day_offset = int(data.split(":", 1)[1])
        picks = analyzer.sniper_auto_scan(day_offset=day_offset)
        if not picks:
            await query.edit_message_text(
                f"🎯 *SNIPER — {format_day_label(day_offset)}*\n\nAucun spot vraiment propre trouvé.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back:sniper_picker"), InlineKeyboardButton("🏠 Home", callback_data="back:menu")]]),
                parse_mode="Markdown",
            )
            return
        await query.edit_message_text(
            format_sniper_summary_message(format_day_label(day_offset), picks),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back:sniper_picker"), InlineKeyboardButton("🏠 Home", callback_data="back:menu")]]),
            parse_mode="Markdown",
        )
        for item in picks:
            save_analysis({
                "created_at": now_local().strftime("%Y-%m-%d %H:%M:%S"), "user_id": user_id, "mode": "sniper",
                "competition_code": item.get("competition_code"), "competition": item.get("competition"), "day_label": format_day_label(day_offset),
                "kickoff_utc": item.get("utc_date"), "match_key": build_match_key(item.get("home_name", ""), item.get("away_name", ""), item.get("utc_date", "")),
                "home_name": item.get("home_name"), "away_name": item.get("away_name"), "prediction": item.get("prediction"),
                "bet_type": item.get("bet_type"), "confidence": item.get("confidence"), "score_prediction": item.get("score_primary"),
                "provider": item.get("provider"), "note": item.get("why_text"),
            })
            await context.bot.send_message(chat_id=update.effective_chat.id, text=format_analysis_message(item, item, "sniper"), parse_mode="Markdown")
        return

    if data == "history:show":
        await _refresh_results()
        await query.edit_message_text(format_history_message(), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back:menu"), InlineKeyboardButton("🏠 Home", callback_data="back:menu")]]), parse_mode="Markdown")
        return

    if data.startswith("analyze:"):
        token = data.split(":", 1)[1]
        session = load_session(user_id)
        match = (session.get("matches_by_token") or {}).get(token)
        mode = session.get("mode", "normal")
        day_offset = session.get("day_offset", 0)
        if not match:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Analyse indisponible. Recharge la liste.")
            return
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Analyse en cours...")
        analysis = analyzer.analyze_match_fast(competition_code=match.get("competition_code", ""), match=match, mode=mode)
        save_analysis({
            "created_at": now_local().strftime("%Y-%m-%d %H:%M:%S"), "user_id": user_id, "mode": mode,
            "competition_code": match.get("competition_code"), "competition": match.get("competition"), "day_label": format_day_label(day_offset),
            "kickoff_utc": match.get("utc_date"), "match_key": build_match_key(match.get("home_name", ""), match.get("away_name", ""), match.get("utc_date", "")),
            "home_name": match.get("home_name"), "away_name": match.get("away_name"), "prediction": analysis.get("prediction"),
            "bet_type": analysis.get("bet_type"), "confidence": analysis.get("confidence"), "score_prediction": analysis.get("score_primary"),
            "provider": match.get("provider"), "note": analysis.get("why_text"),
        })
        await context.bot.send_message(chat_id=update.effective_chat.id, text=format_analysis_message(match, analysis, mode), parse_mode="Markdown")
        return


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN manquant dans .env")
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("settle", settle_command))
    application.add_handler(CallbackQueryHandler(on_callback))
    print("🚀 LVBXNT Football Bot V2 lancé...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
