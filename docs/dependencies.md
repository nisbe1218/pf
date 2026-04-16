# Dépendances et services externes

## Backend Python / Django

Liste des dépendances principales du backend (`backend/requirements.txt`) :

- `django` - framework web
- `djangorestframework` - API REST
- `djangorestframework-simplejwt` - authentification JWT
- `psycopg2-binary` - driver PostgreSQL
- `python-dotenv` - lecture du `.env`
- `django-cors-headers` - gestion des CORS
- `bcrypt` - hachage des mots de passe
- `pandas` - lecture et manipulation de fichiers CSV/Excel
- `numpy` - calcul numérique
- `scikit-learn` - apprentissage automatique
- `joblib` - sérialisation de modèles
- `openpyxl` - lecture/écriture Excel
- `xlrd` - lecture Excel

## Frontend React

Dépendances listées dans `frontend/package.json` :

- `react`, `react-dom` - base de l’application React
- `react-router-dom` - routage côté client
- `react-scripts` - outils Create React App
- `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled` - interface Material UI
- `axios` - communication HTTP avec le backend
- `chart.js`, `react-chartjs-2` - graphiques
- `plotly.js-dist-min`, `react-plotly.js` - visualisation avancée
- `jwt-decode` - décodage du token JWT côté client
- `xlsx` - lecture de fichiers Excel côté frontend
- `REACT_APP_API_URL` - variable d’environnement React utilisée pour pointer vers le backend local `http://localhost:8000/api/`

## Infrastructure

- `docker-compose.yml` orchestre trois services :
  - `db` : PostgreSQL 16
  - `backend` : service Django
  - `frontend` : service React
- Volume Docker persistant : `postgres_data`

## Services externes potentiels

- PostgreSQL comme service de données relationnelles
- API interne du backend accessible via `http://localhost:8000/api/`
- Les bibliothèques ML optionnelles sont détectées dynamiquement :
  - `xgboost` pour XGBoost
  - `lightgbm` pour LightGBM
  - `catboost` pour CatBoost

## Contraintes techniques

- Le backend utilise `DB_HOST=db` car PostgreSQL est dans un conteneur Docker séparé
- Le frontend démarre avec `npm install && npm start` dans le conteneur
- Le projet est conçu pour fonctionner sous Docker sur Windows
- Les données cliniques sont normalisées avec des clés de champ définies globalement dans `predictions/views.py`

## Bonnes pratiques recommandées

- Ne pas committer les fichiers générés (`export_db.sql`, logs temporaires)
- Utiliser un fichier `.env` pour les secrets et les paramètres d’environnement
- Maintenir à jour `requirements.txt` et `package.json`
