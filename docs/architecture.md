# Architecture globale

## Type d’application

Application web full stack avec :

- backend Python / Django REST Framework
- frontend React (Create React App)
- base de données PostgreSQL
- conteneurisation avec Docker Compose
- fonctionnalité IA / machine learning pour prédictions cliniques

## Schéma simplifié

```text
Frontend React <--> Backend Django REST <--> PostgreSQL
                            |
                            +--> Module ML (scikit-learn, XGBoost, LightGBM, CatBoost)
```

## Couches principales

### Frontend

- Dossier : `frontend/`
- Technologies : React, React Router, Material UI, Axios
- But : interface utilisateur pour gestion des patients, connexion, dashboard et modèle IA
- Pages principales :
  - `src/pages/patients/PatientsManagement.js`
  - `src/pages/model-ai/ModelAI.js`
  - `src/pages/dashboard/Dashboard.js`
  - `src/pages/auth/Login.js`

### Backend

- Dossier : `backend/`
- Technologies : Django, Django REST Framework, SimpleJWT, Pandas, scikit-learn
- Applications Django :
  - `users` - authentification et gestion des utilisateurs
  - `patients` - gestion des données patient
  - `predictions` - API de prédiction et entraînement des modèles
  - `audit` - journalisation des actions
- Points d’entrée principaux :
  - `backend/config/urls.py`
  - `backend/manage.py`

### Base de données

- Service : PostgreSQL 16
- Configuration Docker : `docker-compose.yml`
- Base utilisée : `plateforme_medicale`
- Volume persistant : `postgres_data`

### Services et dépendances externes

- PostgreSQL pour le stockage relationnel
- Docker Compose pour orchestrer backend, frontend et base
- `django-cors-headers` pour autoriser le frontend à appeler le backend
- `python-dotenv` pour charger les variables d’environnement
- Le backend Django accepte les hôtes internes Docker (`backend`) et les hôtes locaux (`localhost`, `127.0.0.1`, `[::1]`) pour éviter les erreurs `DisallowedHost` en développement
- Le frontend en mode navigateur utilise `http://localhost:8000/api/` comme point d’accès API

## Structure des fichiers

### Racine du projet

- `docker-compose.yml` - orchestration des conteneurs
- `README.md` - documentation générale du projet
- `backend/` - application Django
- `frontend/` - application React
- `docs/` - documentation générée

### Backend

- `backend/config/` - configuration Django (urls, settings, wsgi, asgi)
- `backend/users/` - gestion des comptes et authentification
- `backend/patients/` - modèles, vues et routes des patients
- `backend/predictions/` - logique IA et routes de prédictions
- `backend/audit/` - suivi d’audit des actions métiers

### Frontend

- `frontend/src/App.js` - routes principales de l’application
- `frontend/src/context/AuthContext.js` - gestion de l’authentification JWT
- `frontend/src/services/` - fonctions d’appel API (probablement `api.js`)
- `frontend/src/pages/` - tableaux de bord et pages métiers
- `frontend/src/components/` - composants réutilisables

## Déploiement local

1. `docker-compose up --build`
2. Le backend est disponible sur `http://localhost:8000`
3. Le frontend est disponible sur `http://localhost:3000`

## Remarques techniques

- Le backend utilise `DB_HOST=db` pour atteindre PostgreSQL dans Docker
- Le frontend se connecte au backend via des appels API relatifs dans `api` (Axios)
- Le module ML est intégré dans le backend et n’est pas exposé en tant que microservice séparé
