# Processus Data de l’application

Ce document décrit précisément comment les données sont traitées dans l’application, sans service ETL séparé.
Le traitement est effectué directement dans le backend Django.

## Étapes principales

1. Import / ingestion
2. Normalisation et transformation
3. Enrichissement de schéma
4. Génération d’identifiants et métadonnées automatiques
5. Extraction des features pour le ML
6. Prétraitement dynamique pour l’entraînement et les prédictions

## 1. Import / ingestion

Le traitement des données commence dans `projet-medical/backend/patients/views.py`.
Les imports se font depuis des fichiers Excel ou CSV via des endpoints comme :

- `POST /api/patients/import/`
- `POST /api/patients/import-excel/`

Le backend utilise `pandas` et `openpyxl` pour lire le contenu des fichiers.

### Fonction clé

- `build_patient_payload(row)`

Cette fonction :

- lit chaque colonne du fichier importé
- convertit les valeurs Excel/CSV en types utilisables
- normalise les entêtes et les valeurs
- place les données dans des buckets de section (`demographie_data`, `biologie`, `dialyse`, etc.)
- stocke les champs inconnus dans `extra_data`

## 2. Normalisation et transformation

Après l’import, le backend normalise plusieurs champs critiques :

- `date_naissance`, `date_admission`, `date_evaluation_initiale`
  - parse flexible pour accepter plusieurs formats
- `age`
  - normalisation des valeurs numériques
- `sexe`
  - normalisation des valeurs en `M`, `F`, `O`, ou `inconnu`
- `demographie_data.demographie_age_ans`
  - calcul à partir d’`age` ou de `date_naissance`

La fonction `build_patient_payload` gère ces transformations.

## 3. Enrichissement de schéma

Le payload importé est enrichi :

- `age` et `date_naissance` sont dérivés l’un de l’autre si nécessaire
- les données démographiques sont synchronisées dans `demographie_data`
- les valeurs manquantes sont nettoyées ou supprimées si invalides
- les en-têtes inconnues sont conservées dans `extra_data`

Cela rend le schéma flexible tout en conservant les données originales.

## 4. Génération d’identifiants et métadonnées automatiques

Plusieurs fonctions ajoutent des champs automatiques :

- `ensure_required_identity_fields(payload)`
  - garantit la présence de `id_patient`, `nom`, `prenom`, `sexe`
- `ensure_incremental_identifiers(payload, ...)`
  - génère `id_patient` et `id_enregistrement_source` si nécessaire
- `apply_automatic_schema_fields(payload, auto_increment_state, current_user)`
  - remplit les champs automatiques définis par le template
  - ajoute `utilisateur_saisie`, `derniere_mise_a_jour`, et d’autres valeurs par défaut

Ces champs facilitent l’intégrité des données et l’historique des enregistrements.

## 5. Extraction des features pour le ML

Le traitement ML est réalisé dans `projet-medical/backend/predictions/views.py`.
Les principales étapes sont :

- `extract_features_from_payload(payload, feature_keys)`
  - extrait les variables envoyées par le frontend
  - normalise chaque clé selon son type (numérique, catégorielle, texte)
  - calcule des features dérivées via `compute_clinical_risk_indicators`
- `extract_features_from_patient(patient, feature_keys)`
  - extrait les mêmes variables depuis un objet ORM Patient
  - gère les champs stockés dans `extra_data`

## 6. Prétraitement dynamique pour l’entraînement / prédiction

Les données ML subissent un prétraitement dynamique :

- `is_numeric_feature(key)` identifie les variables numériques
- `normalize_value(value, is_numeric)` transforme les valeurs en formats cohérents
- `get_preprocessor(numeric_features, categorical_features)` construit un `ColumnTransformer`
  - valeurs numériques : imputation, transformation de puissance, standardisation
  - valeurs catégorielles : cast en string, imputation constante, encodage one-hot
- `get_pipeline(estimator, numeric_features, categorical_features)` assemble le préprocesseur et le modèle

## 7. Calcul des variables dérivées

Le module crée des indicateurs cliniques dérivés via `compute_clinical_risk_indicators(raw_values)`.
Il calcule par exemple :

- `risk_crp_eleve`
- `risk_phosphore_eleve`
- `risk_calcium_eleve`
- `risk_wbc_eleve`
- `risk_edema`
- `risk_low_bmi`
- `risk_marital_non_marie`
- `risk_egfr_paradox`
- `doietal_risk_score`

Ces variables dérivées sont utilisées dans le jeu de données ML et aident à améliorer la qualité des prédictions.

## 8. Synthèse du processus

### Flux global

1. Le fichier Excel/CSV est importé via un endpoint Django.
2. Le backend lit les lignes et construit un payload patient.
3. Les champs sont normalisés, nettoyés et augmentés.
4. Les identifiants et métadonnées sont générés automatiquement.
5. Les données sont sauvegardées en base PostgreSQL.
6. Pour les prédictions, les variables ML sont extraites et converties en features.
7. Un pipeline de prétraitement applique imputation, encodage et scalage.
8. Les modèles ML s’entraînent ou prédisent sur ces features.

## Conclusion

Il n’y a pas de service ETL séparé :
- le processus data est intégré dans le backend Django
- il couvre l’ingestion, la transformation, l’enrichissement et la préparation ML
- il est fortement couplé à la logique métier patient et aux fonctions de prédiction
