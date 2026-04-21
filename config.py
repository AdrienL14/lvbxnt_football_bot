import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# APIs
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
API_FOOTBALL_API_KEY = os.getenv("API_FOOTBALL_API_KEY")

# StatsBomb (optionnel)
STATSBOMB_ENABLED = False