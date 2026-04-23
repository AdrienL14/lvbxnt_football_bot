# LVBXNT Football Bot V4

Version V4 locale, plus rapide et plus sélective, déjà structurée pour la future partie Oracle 24/7.

## Ce qui change
- Sniper Pro plus strict
- max 3 picks propres
- sinon 2 / 1 / NO VALUE BET
- filtre anti-matchs trop équilibrés
- filtre anti-favoris surévalués
- préchargement du cache au démarrage
- structure déjà prête pour Oracle plus tard

## Installation locale Windows
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Remplis ensuite ton `.env` avec tes vraies clés API puis lance:
```powershell
python app.py
```

## Commandes bot
- `/start`
- `/history`
- `/settle`

## GitHub
```powershell
git add .
git commit -m "LVBXNT Football Bot V4"
git push
```

## Plus tard pour Oracle
Le projet contient déjà:
- variables d’environnement propres
- `start_oracle.sh`
- `lvbxnt_football_bot.service`

Quand tu auras ton compte Oracle, on fera uniquement:
- création VM
- upload projet
- venv
- service systemd
- lancement 24/7
