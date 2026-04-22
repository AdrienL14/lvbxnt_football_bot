# LVBXNT Football Bot V2

Version V2 plus propre pour le local maintenant, avec base déjà prête pour Oracle plus tard.

## Ce qui change
- historique réel en SQLite
- suivi automatique des résultats réglés
- sessions utilisateur persistantes
- intégration API-Football pour fixtures + standings
- analyse améliorée avec forme pondérée + classement
- projet nettoyé pour GitHub

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

## Push GitHub
```powershell
git init
git add .
git commit -m "LVBXNT Football Bot V2"
git branch -M main
git remote add origin TON_URL_GITHUB
git push -u origin main
```

## Plus tard pour Oracle
Le code est déjà prêt pour variables d’environnement + stockage local + lancement stable.
Quand tu auras ton compte Oracle, on fera uniquement la partie déploiement 24/7.
