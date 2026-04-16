# API REST du backend

Le backend expose une API REST via Django REST Framework.

## Préfixe commun

- Base : `/api/`

## Authentification

### `POST /api/auth/token/`

- Objectif : obtenir un token JWT
- Payload attendu : `email`, `password`
- Retour : `access`, `refresh`

### `GET /api/auth/profil/`

- Objectif : récupérer le profil de l’utilisateur connecté
- Nécessite un JWT valide

### `GET /api/auth/roles/`

- Objectif : récupérer les rôles disponibles

### `GET /api/auth/utilisateurs/`

- Objectif : récupérer la liste des utilisateurs

## Gestion des patients

### `GET /api/patients/`

- Objectif : lister les patients
- Possibilité de filtrer ou paginer selon l’implémentation backend

### `GET /api/patients/flat/`

- Objectif : retourner une vue plate des patients pour affichage

### `GET /api/patients/schema/`

- Objectif : obtenir le schéma dynamique des champs patient

### `POST /api/patients/`

- Objectif : créer un nouveau patient
- Payload : données cliniques et patient

### `PUT /api/patients/{id}/`

- Objectif : remplacer un patient existant

### `PATCH /api/patients/{id}/`

- Objectif : mettre à jour partiellement un patient

### `DELETE /api/patients/{id}/`

- Objectif : supprimer un patient

### `DELETE /api/patients/purge/`

- Objectif : purger les patients sélectionnés ou anciens

### `POST /api/patients/import/`

- Objectif : importer des patients depuis un CSV
- Payload : fichier multipart/form-data

### `POST /api/patients/import-excel/`

- Objectif : importer des patients depuis un fichier Excel

## Prédictions IA

### `POST /api/predictions/predict/`

- Objectif : exécuter une prédiction de risque
- Payload exemple :

```json
{
  "prediction_type": "mortalite",
  "model": "random_forest",
  "input": {
    "age": 65,
    "sexe": "M",
    "biologie_creatinine_mg_l": 120,
    "presentation_tas_mmhg": 130
  }
}
```

- Retour : score, risque estimé, facteurs et éventuelles explications

### `POST /api/predictions/train/`

- Objectif : entraîner un modèle ou évaluer un modèle existant
- Payload exemple :

```json
{
  "prediction_type": "coagulation",
  "model": "auto",
  "input": { ... }
}
```

- Retour : métriques de performance et rapport d’entraînement

### `GET /api/predictions/history/`

- Objectif : récupérer l’historique des prédictions
- Exemple : `GET /api/predictions/history/?days=30`

### `GET /api/predictions/metrics/`

- Objectif : récupérer les métriques de performance des modèles
- Exemple : `GET /api/predictions/metrics/?prediction_type=mortalite`

## Notes pratiques

- Les endpoints IA sont définis dans `projet-medical/backend/predictions/urls.py`
- Le backend expose aussi des routes `admin/` via Django Admin pour l’administration
- La plupart des appels frontend sont faits depuis `frontend/src/pages/*` et `frontend/src/context/AuthContext.js`
