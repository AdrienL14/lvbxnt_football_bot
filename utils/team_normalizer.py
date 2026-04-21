import re, unicodedata
from datetime import datetime

STOPWORDS = {"fc","cf","afc","sc","ac","club","de","futbol","football","fk","sv","rc","cd","sd","ca","ud","us","as","the"}
ALIASES = {
    "athletic bilbao":"athletic club","athletic club bilbao":"athletic club",
    "brighton and hove albion":"brighton hove albion","brighton and hove albion fc":"brighton hove albion",
    "brighton hove albion fc":"brighton hove albion","brighton and hove":"brighton hove albion",
    "ca osasuna":"osasuna","club atletico de madrid":"atletico madrid","atletico de madrid":"atletico madrid",
    "deportivo alaves":"alaves","real sociedad de futbol":"real sociedad","fc barcelona":"barcelona",
    "rcd mallorca":"mallorca","valencia cf":"valencia","girona fc":"girona",
    "real betis balompie":"real betis","manchester city fc":"manchester city","chelsea fc":"chelsea",
    "afc bournemouth":"bournemouth","leeds united fc":"leeds united","burnley fc":"burnley",
    "paris saint germain":"psg"
}
def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
def normalize_team_name(name: str) -> str:
    text = _strip_accents((name or "").lower()).replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text in ALIASES: text = ALIASES[text]
    tokens = [t for t in text.split() if t not in STOPWORDS]
    text = " ".join(tokens).strip()
    if text in ALIASES: text = ALIASES[text]
    return text
def choose_best_name(*names: str) -> str:
    candidates = [n for n in names if n]
    if not candidates: return ""
    return sorted(candidates, key=lambda n: (-len(normalize_team_name(n).split()), len(n), n.lower()))[0]
def kickoff_bucket(date_str: str) -> str:
    if not date_str: return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return (date_str or "")[:16]
def build_match_key(home: str, away: str, kickoff_utc: str) -> str:
    return f"{normalize_team_name(home)}|{normalize_team_name(away)}|{kickoff_bucket(kickoff_utc)}"
