# Modèles IA et logique machine learning

## Contexte

Le backend contient un module de prédiction ML intégré dans `projet-medical/backend/predictions/views.py`.
Ce module permet :

- d’entraîner des modèles de classification
- de prédire des risques cliniques
- de calculer des métriques de performance
- de stocker éventuellement l’historique des prédictions

## Types de prédiction

- `mortalite` : prédiction du risque de décès dans l’année
- `coagulation` : prédiction des complications hémorragiques ou thrombotiques

## Algorithmes supportés

Le projet propose un catalogue de modèles :

- `random_forest`
- `extra_trees`
- `gradient_boosting`
- `decision_tree`
- `logistic_regression`
- `svm`
- `adaboost`
- `xgboost` (si installé)
- `lightgbm` (si installé)
- `catboost` (si installé)

## Prétraitement des données

### Sélection des features

- Les clés de données attendues sont listées dans `ALL_KNOWN_FEATURES`
- Seules les variables présentes dans cette liste sont conservées
- Les variables susceptibles de provoquer une fuite de données sont exclues selon le type de prédiction :
  - `MORTALITY_LEAKAGE_FEATURES`
  - `COAGULATION_LEAKAGE_FEATURES`

### Détection des types de variables

- Les variables numériques sont identifiées par des suffixes comme :
  - `_mg_l`, `_g_l`, `_mmol_l`, `_ml_min`, `_mmhg`, `_kg`, `_cm`
- Certaines variables sont forcées numériques :
  - `age`, `demographie_age_ans`, `demographie_distance_centre_km`
- Certaines variables sont forcées catégorielles :
  - `sexe`, `demographie_sexe`

### Prétraitements standards

- Imputation des valeurs manquantes avec `SimpleImputer`
- Encodage des catégories avec `OneHotEncoder`
- Normalisation / scalage avec `StandardScaler` et `PowerTransformer`
- Pipeline dynamique avec `ColumnTransformer`

## Logique de classification

### Construction des modèles

Le mapping des modèles se fait dans `get_model_map()`, avec des paramètres adaptés :

- `RandomForestClassifier` : `class_weight='balanced_subsample'`, `n_estimators=200`
- `GradientBoostingClassifier` : `learning_rate=0.05`, `max_depth=4`
- `LogisticRegression` : `solver='saga'`, `class_weight='balanced'`
- `LinearSVC` pour SVM via `CalibratedClassifierCV`
- `AdaBoostClassifier` sur un arbre de décision peu profond

### Paramètres optionnels

- XGBoost, LightGBM et CatBoost sont détectés à l’import
- Si ces bibliothèques sont présentes, elles sont ajoutées au catalogue de modèles

## Algorithme de calibration de seuil

- `find_best_threshold(y_true, y_prob)` teste plusieurs seuils de classification
- Il maximise le score F1 sur les probabilités de sortie
- Cela permet de mieux ajuster la conversion probabilité → classe binaire

## Endpoints ML

- `POST /api/predictions/predict/` - exécution d’une prédiction
- `POST /api/predictions/train/` - entraînement d’un modèle ou évaluation
- `GET /api/predictions/history/` - historique des prédictions
- `GET /api/predictions/metrics/` - métriques par type de modèle

## Exemple de flux ML

1. Le frontend construit un payload d’entrée à partir des variables cliniques sélectionnées
2. Le backend filtre les variables invalides
3. Le backend charge ou entraîne un modèle
4. Les scores et le statut de risque sont renvoyés au frontend
5. Le frontend affiche score, facteurs contributeurs et recommandation

## Points de vigilance

- Vérifier l’absence de fuite de données lors de l’entraînement
- Utiliser des valeurs normalisées et cohérentes pour les champs cliniques
- Prévoir des valeurs par défaut si le frontend n’envoie pas toutes les clés
- Contrôler la présence ou l’absence de XGBoost/LightGBM/CatBoost

## Fichiers clés

- `projet-medical/backend/predictions/views.py`
- `projet-medical/backend/predictions/urls.py`
- `projet-medical/backend/predictions/models.py` (si présent pour les logs)
- `projet-medical/frontend/src/pages/model-ai/ModelAI.js`
