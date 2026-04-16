# Flux de données

## Vue d’ensemble

L’application suit un flux de données classique web :

1. L’utilisateur interagit avec l’interface React
2. Le frontend effectue des requêtes HTTP vers le backend Django
3. Le backend traite la requête, interagit avec PostgreSQL et/ou le module ML
4. La réponse est renvoyée au frontend et affichée à l’utilisateur

## Flux frontend → backend

### Authentification

- Frontend : `AuthContext.js` utilise JWT pour stocker le token dans le navigateur
- Backend : routes sous `api/auth/` gèrent l’identification, le profil et les rôles

### Gestion des patients

- Pages principales : `PatientsManagement.js`
- Requêtes API :
  - `GET /api/patients/`
  - `GET /api/patients/flat/`
  - `GET /api/patients/schema/`
  - `POST /api/patients/`
  - `PUT /api/patients/{id}/`
  - `PATCH /api/patients/{id}/`
  - `DELETE /api/patients/{id}/`
  - `DELETE /api/patients/purge/`
  - `POST /api/patients/import/`
  - `POST /api/patients/import-excel/`

### Prédictions IA

- Page : `ModelAI.js`
- Requêtes API :
  - `POST /api/predictions/predict/`
  - `POST /api/predictions/train/`
  - `GET /api/predictions/history/`
  - `GET /api/predictions/metrics/`

## Flux backend → base de données

### Modèles principaux

- `patients.models.Patient` : données patient et valeurs cliniques
- `predictions.models.PredictionLog` : historique des prédictions
- `users.models.Utilisateur` : informations de connexion et rôles
- `audit.models.AuditLog` : journalisation des actions utilisateur

### Logique de stockage

- Les données patient sont enregistrées dans PostgreSQL
- L’historique des prédictions peut être journalisé si l’application `predictions.models.PredictionLog` est disponible
- Les imports Excel et les fichiers `.csv` sont traités côté backend via `pandas`

## Flux de traitement machine learning

1. Le frontend demande une prédiction ou un entraînement
2. Le backend reçoit les données de features cliniques
3. Le backend fait :
   - nettoyage et transformation des features
   - sélection des variables valides
   - appel au modèle ML
4. Résultat renvoyé au frontend

## Exemples concrets

### Prédiction

```js
await api.post('predictions/predict/', {
  prediction_type: 'mortalite',
  model: 'random_forest',
  input: { age: 45, sexe: 'M', biologie_creatinine_mg_l: 120, ... }
});
```

### Entraînement

```js
await api.post('predictions/train/', {
  prediction_type: 'coagulation',
  model: 'auto',
  input: { ... }
});
```

## Communication entre composants

- Le frontend envoie du JSON au backend via Axios
- Le backend décode les données, exécute la logique métier et renvoie du JSON
- Le backend peut charger des modèles enregistrés sur disque dans `predictions/models/`
- Les endpoints ML sont encapsulés dans `backend/predictions/views.py`

## Indexation et gestion des données

- La structure de données patient est organisée autour d’un schéma large et flexible
- Les clés de features sont normalisées dans `predictions/views.py` via `ALL_KNOWN_FEATURES`
- Les variables numériques sont détectées selon des suffixes (`_mg_l`, `_mmhg`, `_kg`, etc.)
- Les données de fuite de variable sont filtrées avant l’entraînement pour éviter les biais
