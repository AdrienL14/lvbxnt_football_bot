from __future__ import annotations

from datetime import timezone, timedelta, datetime
from config import BOT_TIMEZONE_OFFSET


def get_bot_tz():
    return timezone(timedelta(hours=BOT_TIMEZONE_OFFSET))


def now_local() -> datetime:
    return datetime.now(get_bot_tz())


def format_day_label(day_offset: int) -> str:
    base = now_local().date()
    target = base.fromordinal(base.toordinal() + day_offset)
    if day_offset == 0:
        prefix = "Aujourd’hui"
    elif day_offset == 1:
        prefix = "Demain"
    elif day_offset == 2:
        prefix = "Après-demain"
    else:
        prefix = target.strftime("%A")
    return f"{prefix} ({target.strftime('%d/%m')})"


def format_local_kickoff(utc_date: str) -> str:
    if not utc_date:
        return "Heure inconnue"
    try:
        dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(get_bot_tz())
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return utc_date[:16].replace("T", " ")
