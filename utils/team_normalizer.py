from __future__ import annotations

import re
import unicodedata
from datetime import datetime

STOPWORDS = {
    "fc", "cf", "afc", "sc", "ac", "club", "de", "futbol", "football", "fk",
    "sv", "rc", "cd", "sd", "ca", "ud", "us", "as", "the"
}

ALIASES = {
    "psg": "paris saint germain",
    "paris sg": "paris saint germain",
    "paris saint germain fc": "paris saint germain",
    "om": "marseille",
    "ol": "lyon",
    "asm": "monaco",
    "man city": "manchester city",
    "man city fc": "manchester city",
    "man utd": "manchester united",
    "man united": "manchester united",
    "spurs": "tottenham hotspur",
    "wolves": "wolverhampton wanderers",
    "newcastle utd": "newcastle united",
    "brighton and hove albion": "brighton hove albion",
    "brighton & hove albion": "brighton hove albion",
    "afc bournemouth": "bournemouth",
    "athletic bilbao": "athletic club",
    "athletic club bilbao": "athletic club",
    "barca": "barcelona",
    "fc barcelona": "barcelona",
    "atleti": "atletico madrid",
    "club atletico de madrid": "atletico madrid",
    "atletico de madrid": "atletico madrid",
    "deportivo alaves": "alaves",
    "real sociedad de futbol": "real sociedad",
    "ca osasuna": "osasuna",
    "rcd mallorca": "mallorca",
    "valencia cf": "valencia",
    "girona fc": "girona",
    "real betis balompie": "real betis",
    "inter": "inter milan",
    "internazionale": "inter milan",
    "internazionale milano": "inter milan",
    "ac milan": "milan",
    "as roma": "roma",
    "juve": "juventus",
    "bayern": "bayern munich",
    "bayern munchen": "bayern munich",
    "dortmund": "borussia dortmund",
    "bvb": "borussia dortmund",
    "leverkusen": "bayer leverkusen",
    "gladbach": "borussia monchengladbach",
    "sporting": "sporting cp",
    "sporting lisbon": "sporting cp",
    "porto fc": "porto",
    "sl benfica": "benfica",
    "psv": "psv eindhoven",
    "ajax amsterdam": "ajax",
    "standard liege": "standard de liege",
    "chelsea fc": "chelsea",
    "manchester city fc": "manchester city",
}

def strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))

def normalize_team_name(name: str) -> str:
    text = strip_accents((name or "").lower())
    text = text.replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text in ALIASES:
        text = ALIASES[text]
    tokens = [token for token in text.split() if token not in STOPWORDS]
    text = " ".join(tokens).strip()
    if text in ALIASES:
        text = ALIASES[text]
    return text

def choose_best_name(*names: str) -> str:
    candidates = [n for n in names if n]
    if not candidates:
        return ""
    return sorted(candidates, key=lambda n: (-len(normalize_team_name(n).split()), len(n), n.lower()))[0]

def kickoff_bucket(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return (date_str or "")[:16]

def build_match_key(home: str, away: str, kickoff_utc: str) -> str:
    return f"{normalize_team_name(home)}|{normalize_team_name(away)}|{kickoff_bucket(kickoff_utc)}"
