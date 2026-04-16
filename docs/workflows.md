# Workflows et parcours utilisateurs

## Objectif

Décrire les cas d’usage principaux et les parcours utilisateurs de l’application.

## Parcours utilisateur principal

### 1. Connexion

- L’utilisateur saisit son email et son mot de passe
- Le frontend appelle `POST /api/auth/token/` ou équivalent
- Si l’authentification réussit, le token JWT est stocké dans le navigateur
- L’utilisateur est redirigé vers le dashboard

### 2. Accès au dashboard

- Le dashboard affiche des statistiques globales
- Il charge des données via des routes API (utilisateurs, rôles, patients)
- Le tableau de bord permet de naviguer vers les pages de gestion et IA

### 3. Gestion des patients

#### Création d’un patient

- L’utilisateur clique sur « Ajouter patient »
- Le formulaire est rempli dans `PatientsManagement.js`
- Le frontend appelle `POST /api/patients/`
- Le backend valide, crée le patient et retourne l’objet créé
- Le frontend rafraîchit la liste

#### Mise à jour d’un patient

- L’utilisateur modifie un patient existant
- Envoi `PUT /api/patients/{id}/` ou `PATCH /api/patients/{id}/`
- Le backend met à jour la ligne correspondante dans PostgreSQL
- Le frontend met à jour la liste et les détails

#### Suppression d’un patient

- L’utilisateur sélectionne un ou plusieurs patients
- Envoi `DELETE /api/patients/{id}/` ou `DELETE /api/patients/purge/`
- Le backend supprime les enregistrements requis
- Le frontend supprime les entrées de l’interface

#### Import de données

- L’utilisateur importe un fichier CSV ou Excel
- Le frontend envoie un formulaire multipart avec `POST /api/patients/import/` ou `POST /api/patients/import-excel/`
- Le backend utilise `pandas` pour lire et normaliser les données
- Les enregistrements sont stockés en base

## Parcours IA

### 1. Sélection du type de prédiction

- L’utilisateur choisit un type de prédiction : `mortalite` ou `coagulation`
- La page IA propose une sélection de modèles
- Les modèles disponibles sont filtrés selon la prise en charge des bibliothèques installées

### 2. Construction du payload

- L’utilisateur ou le frontend alimente les champs de variables cliniques
- `ModelAI.js` mappe les variables pour construire le payload d’entrée

### 3. Lancement de la prédiction

- Le frontend appelle `POST /api/predictions/predict/`
- Le backend prépare les features et exécute le modèle choisi
- La réponse contient un score, un statut de risque et des facteurs explicatifs

### 4. Entraînement d’un modèle

- L’utilisateur demande `POST /api/predictions/train/`
- Le backend entraîne un modèle sur les données fournies ou historisées
- Les métriques de performance sont renvoyées au frontend

## Cas d’usage importants

### Visualisation des métriques ML

- Le modèle IA fournit des métriques via `GET /api/predictions/metrics/`
- Ces métriques permettent de vérifier la disponibilité de XGBoost, LightGBM ou CatBoost
- Le frontend présente un tableau des performances par type de modèle

### Historique des prédictions

- Le frontend récupère `GET /api/predictions/history/?days=30`
- L’historique est affiché dans la page IA
- Permet de suivre les prédictions passées et les résultats

## Flux de traitement critiques

### Création d’un patient

1. Formulaire soumis dans React
2. Requête API vers backend
3. Validation côté serveur
4. Écriture en base PostgreSQL
5. Réponse renvoyée et liste actualisée

### Prédiction / Entraînement

1. Payload JSON envoyé
2. Filtrage des variables invalides
3. Prétraitement (imputation, encodage, normalisation)
4. Exécution du modèle
5. Calcul des scores et métriques
6. Résultat renvoyé au frontend
