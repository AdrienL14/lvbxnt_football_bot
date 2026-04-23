def generate_reason(home_strength, away_strength):
    if away_strength > home_strength:
        return "Extérieur plus solide dans la dynamique actuelle"
    elif home_strength > away_strength:
        return "Domicile plus solide dans la dynamique actuelle"
    else:
        return "Match équilibré avec légère tendance"
