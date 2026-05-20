# Architecture du pipeline de prétraitement médical

Cette documentation décrit le flux de traitement demandé pour le prétraitement intelligent des datasets médicaux en néphrologie, dialyse et analyse clinique.

## Flux demandé

1. Frontend
2. Django + DRF
3. Upload dataset
4. Celery Task
5. Chunking Engine
6. RAG Retrieval
7. Ollama + Qwen2.5 7B
8. Analyse médicale JSON
9. Fusion des résultats
10. Dataset corrigé
11. Rapport final JSON

## Stack technique

- Frontend: React / Next.js
- Backend API: Django + DRF
- LLM principal: Ollama
- Modèle: Qwen2.5 7B Instruct
- RAG: ChromaDB
- Embeddings: nomic-embed-text
- Mémoire: Redis
- Async: Celery

## Principes métier obligatoires

- Analyser tout le dataset avant toute décision
- Détecter les incohérences structurelles et médicales
- Corriger uniquement les anomalies fiables et traçables
- Standardiser les colonnes, dates, booléens, catégories et encodages texte
- Conserver les valeurs critiques ambiguës comme suspectes plutôt que les modifier silencieusement
- Produire un JSON strictement valide en sortie finale

## Structure logique du pipeline

### 1. Frontend
- L'utilisateur sélectionne et envoie le dataset.
- L'interface affiche l'état du traitement et le résultat final.

### 2. Django + DRF
- L'API reçoit le fichier.
- La demande est enregistrée et une session de traitement est créée.

### 3. Upload dataset
- Le dataset est stocké temporairement.
- Les métadonnées initiales sont enregistrées.

### 4. Celery Task
- Une tâche asynchrone est déclenchée.
- Le traitement est isolé du cycle HTTP.

### 5. Chunking Engine
- Le dataset est découpé en chunks cohérents.
- Les colonnes critiques sont priorisées.

### 6. RAG Retrieval
- Les chunks sont indexés localement.
- ChromaDB assure la recherche contextuelle.
- Les embeddings sont générés avec `nomic-embed-text`.

### 7. Ollama + Qwen2.5 7B
- Analyse globale du dataset.
- Détection des anomalies.
- Proposition de corrections prudentes.
- Standardisation des formats.

### 8. Analyse médicale JSON
- Le modèle produit un JSON structuré.
- Les anomalies, risques et corrections sont détaillés.

### 9. Fusion des résultats
- Les résultats des passes sont consolidés.
- Les corrections validées sont appliquées.

### 10. Dataset corrigé
- Une version nettoyée et exploitable est produite.

### 11. Rapport final JSON
- Le rapport final est sérialisé en JSON strictement valide.
- Le rapport contient les anomalies, corrections, risques et recommandations.

## Remarques d'implémentation

- Le dépôt actuel conserve son backend Django + DRF, mais le flux métier de prétraitement est aligné sur cette architecture cible.
- Les traitements doivent rester traçables et limités aux cas fiables.
- Les sorties intermédiaires doivent rester compactes pour supporter les datasets volumineux.
