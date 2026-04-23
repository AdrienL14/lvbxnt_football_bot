from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY", "123")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
API_FOOTBALL_API_KEY = os.getenv("API_FOOTBALL_API_KEY", "")
STATSBOMB_ENABLED = os.getenv("STATSBOMB_ENABLED", "0") == "1"
BOT_TIMEZONE_OFFSET = int(os.getenv("BOT_TIMEZONE_OFFSET", "4"))
BOT_STORAGE_DIR = Path(os.getenv("BOT_STORAGE_DIR", "data"))
BOT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SEASON_EUROPE = int(os.getenv("DEFAULT_SEASON_EUROPE", "2025"))
DEFAULT_SEASON_BRAZIL = int(os.getenv("DEFAULT_SEASON_BRAZIL", "2026"))
DEFAULT_SEASON_ARGENTINA = int(os.getenv("DEFAULT_SEASON_ARGENTINA", "2026"))

PRELOAD_ON_START = os.getenv("PRELOAD_ON_START", "1") == "1"

# Réservé pour la future partie Oracle / 24-7
RUN_ENV = os.getenv("RUN_ENV", "local")
ORACLE_READY = os.getenv("ORACLE_READY", "1") == "1"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", "8080"))
