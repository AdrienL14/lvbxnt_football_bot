from __future__ import annotations

from config import DEFAULT_SEASON_EUROPE, DEFAULT_SEASON_BRAZIL, DEFAULT_SEASON_ARGENTINA

COMPETITIONS = {
    "PL": {"name": "Premier League", "sportsdb_league_id": "4328", "football_data_code": "PL", "api_football_league_id": 39, "season": DEFAULT_SEASON_EUROPE},
    "ELC": {"name": "EFL Championship", "sportsdb_league_id": "4329", "football_data_code": "ELC", "api_football_league_id": 40, "season": DEFAULT_SEASON_EUROPE},
    "PD": {"name": "La Liga", "sportsdb_league_id": "4335", "football_data_code": "PD", "api_football_league_id": 140, "season": DEFAULT_SEASON_EUROPE},
    "SA": {"name": "Serie A", "sportsdb_league_id": "4332", "football_data_code": "SA", "api_football_league_id": 135, "season": DEFAULT_SEASON_EUROPE},
    "B1": {"name": "Bundesliga", "sportsdb_league_id": "4331", "football_data_code": "BL1", "api_football_league_id": 78, "season": DEFAULT_SEASON_EUROPE},
    "FL1": {"name": "Ligue 1", "sportsdb_league_id": "4334", "football_data_code": "FL1", "api_football_league_id": 61, "season": DEFAULT_SEASON_EUROPE},
    "PPL": {"name": "Primeira Liga", "sportsdb_league_id": "4344", "api_football_league_id": 94, "season": DEFAULT_SEASON_EUROPE},
    "DED": {"name": "Eredivisie", "sportsdb_league_id": "4337", "api_football_league_id": 88, "season": DEFAULT_SEASON_EUROPE},
    "BSA": {"name": "Belgian Pro League", "sportsdb_league_id": "4338", "api_football_league_id": 144, "season": DEFAULT_SEASON_EUROPE},
    "CL": {"name": "UEFA Champions League", "sportsdb_league_id": "4480", "football_data_code": "CL", "api_football_league_id": 2, "season": DEFAULT_SEASON_EUROPE},
    "EL": {"name": "UEFA Europa League", "sportsdb_league_id": "4481", "football_data_code": "EL", "api_football_league_id": 3, "season": DEFAULT_SEASON_EUROPE},
    "BSA_BR": {"name": "Brazil Serie A", "sportsdb_league_id": "4351", "api_football_league_id": 71, "season": DEFAULT_SEASON_BRAZIL},
    "ARG": {"name": "Argentina Liga Profesional", "sportsdb_league_id": "4406", "api_football_league_id": 128, "season": DEFAULT_SEASON_ARGENTINA},
}
