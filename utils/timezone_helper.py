from __future__ import annotations

from datetime import timezone, timedelta, datetime


def get_bot_tz():
    # Pas de ZoneInfo / tzdata -> stable Windows, local, Oracle
    return timezone(timedelta(hours=4))


def format_day_label(day_offset: int) -> str:
    base = datetime.now(get_bot_tz()).date()
    target = base.fromordinal(base.toordinal() + day_offset)
    if day_offset == 0:
        prefix = "Aujourd’hui"
    elif day_offset == 1:
        prefix = "Demain"
    else:
        prefix = "Après-demain"
    return f"{prefix} ({target.strftime('%d/%m')})"
