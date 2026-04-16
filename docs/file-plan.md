# Plan des fichiers du projet

Ce document décrit le rôle principal de chaque fichier important du projet et la structure générale du code.

## Racine du projet

- `docker-compose.yml`
  - Orchestration Docker pour les services PostgreSQL, backend Django et frontend React.
  - Définit les ports, volumes, variables d’environnement et dépendances de service.

- `README.md`
  - Documentation centrale du projet.
  - Résume l’objectif général, les instructions de démarrage et les composants principaux.

- `docs/`
  - Contient la documentation générée pour l’architecture, les workflows, l’API, les dépendances et l’IA.

## Dossier `docs/`

- `docs/README.md`
  - Point d’entrée de la documentation.
  - Liste des documents disponibles et de leur usage.

- `docs/architecture.md`
  - Explique l’architecture globale de l’application.
  - Décrit les couches frontend, backend, base de données et l’infrastructure Docker.

- `docs/data-flow.md`
  - Décrit les flux de données entre le frontend, le backend et PostgreSQL.
  - Explique notamment le traitement ML et les endpoints utilisés.

- `docs/workflows.md`
  - Décrit les parcours utilisateurs et les principaux cas d’usage.
  - Explique les workflows de création, mise à jour, suppression et import de patients.

- `docs/api.md`
  - Liste des routes de l’API REST.
  - Contient des exemples de payloads et de comportements des endpoints.

- `docs/dependencies.md`
  - Liste des dépendances backend et frontend.
  - Décrit les services externes et contraintes techniques.

- `docs/model-ai.md`
  - Explique la logique machine learning.
  - Décrit les modèles supportés, le prétraitement des données et les endpoints ML.

- `docs/data-process.md`
  - Décrit le processus data appliqué dans l’application.
  - Explique l’ingestion Excel/CSV, la normalisation, l’enrichissement de schéma et la préparation ML.

- `docs/file-plan.md`
  - Ce fichier.
  - Donne une vue d’ensemble sur le rôle de chaque fichier important.

## Backend `backend/`

- `backend/manage.py`
  - Script de gestion Django utilisé pour démarrer le serveur, appliquer les migrations et exécuter les commandes.

- `backend/requirements.txt`
  - Liste des dépendances Python nécessaires au backend.

- `backend/config/settings.py`
  - Paramètres principaux de Django et configuration des applications, base de données, JWT, CORS, etc.

- `backend/config/urls.py`
  - Routeur principal du backend.
  - Inclut les URLs pour `auth`, `patients` et `predictions`.

- `backend/config/wsgi.py` et `backend/config/asgi.py`
  - Points d’entrée pour le déploiement WSGI/ASGI.

- `backend/users/`
  - Gestion des utilisateurs, rôles et authentification.
  - `models.py` définit l’utilisateur personnalisé et les rôles.
  - `views.py` gère l’authentification et les profils.

- `backend/patients/`
  - Gestion des données patient.
  - Contient les modèles, les vues, les serializers et les routes.

- `backend/predictions/`
  - Logique IA et endpoints de prédiction.
  - `views.py` contient l’implémentation des modèles ML et du traitement des requêtes ML.
  - `urls.py` définit les endpoints `predict`, `train`, `history` et `metrics`.

- `backend/audit/`
  - Journalisation des actions utilisateurs.
  - `models.py` définit le modèle d’audit.

## Frontend `frontend/`

- `frontend/package.json`
  - Liste des dépendances JavaScript et scripts npm.

- `frontend/Dockerfile`
  - Instructions Docker pour builder et démarrer l’application React.

- `frontend/src/index.js`
  - Point d’entrée React.

- `frontend/src/App.js`
  - Définition des routes principales de l’application et intégration du router.

- `frontend/src/context/AuthContext.js`
  - Gestion de l’authentification JWT côté client.
  - Charge le profil utilisateur et protège les routes.

- `frontend/src/pages/model-ai/ModelAI.js`
  - Interface d’utilisation des modèles IA.
  - Sélection des modèles, construction du payload, affichage des résultats, historique et métriques.

- `frontend/src/pages/patients/PatientsManagement.js`
  - Interface de gestion des patients.
  - Gère l’affichage, la création, la modification, la suppression et l’import des patients.

- `frontend/src/pages/dashboard/Dashboard.js`
  - Page d’accueil avec statistiques et navigation vers les sections métier.

- `frontend/src/services/`
  - Contient les services d’appel à l’API REST (par exemple Axios).

## Autres fichiers notables

- `classeur1_schema.json`
  - Schéma des champs patient utilisés par l’application et les imports.

- `patients_structure_optimisee.sql`, `patients_plateforme.sql`, etc.
  - Scripts SQL utiles pour la base de données et l’optimisation des structures.

## Usage recommandé

- Lire d’abord `docs/README.md` pour comprendre l’organisation de la documentation.
- Consulter `docs/architecture.md` pour la structure globale.
- Se référer à `docs/api.md` pour l’API.
- Lire `docs/model-ai.md` pour tout ce qui concerne l’IA.

---

Ce plan de fichiers est conçu pour aider à naviguer rapidement dans le projet et comprendre le rôle de chaque zone du code.