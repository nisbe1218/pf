# 📊 Pipeline Asynchrone de Prétraitement LLM - Résumé d'Implémentation

## ✅ Étapes Implémentées

### **1. Import du fichier (CSV / Excel)**
- ✅ UI React avec file input `.csv` et `.xlsx`
- ✅ Validation du type de fichier côté frontend
- ✅ Envoi multipart/form-data vers API

**Fichier:** [frontend/src/pages/preprocessing/Preprocessing.js](frontend/src/pages/preprocessing/Preprocessing.js)

---

### **2. Lecture technique (Pandas)**
- ✅ `_read_uploaded_dataframe()` - Parse CSV/Excel dans DataFrame
- ✅ Détection automatique des colonnes
- ✅ Support openpyxl et xlrd pour tous formats

**Code:** [backend/patients/views.py](backend/patients/views.py) - `_read_uploaded_dataframe()`

---

### **3. Analyse intelligente (Qwen + Ollama)**
- ✅ **Payload compaction** - Env vars contrôlent taille (OLLAMA_PREVIEW_ROWS, OLLAMA_COLUMN_SAMPLES, etc.)
- ✅ **Détection des anomalies médicales** - Format, incohérences logiques, valeurs manquantes, doublons
- ✅ **Qwen2.5:7b-instruct** - Modèle local sur http://ollama:11434
- ✅ **Timeout**: 300s (configurable via OLLAMA_TIMEOUT_SECONDS)
- ✅ **Gestion des erreurs** - Fallback intelligentes, messages d'erreur détaillés

**Code:** [backend/patients/views.py](backend/patients/views.py) - `_call_ollama_qwen_analysis()`

---

### **4. Génération des résultats IA**
LLM retourne JSON structuré avec :
- ✅ **quality_score** (0-100) - Évaluation dataset
- ✅ **issues** (liste) - Problèmes détectés {severity, category, column, rows, explanation}
- ✅ **recommendations** (liste) - Actions suggérées
- ✅ **correction_plan** (dict) - Règles applicables {rename_columns, drop_columns, value_mappings, fill_missing, type_casts, parse_dates, trim_whitespace}
- ✅ **corrected_preview_rows** - Aperçu après corrections

**Code:** [backend/patients/views.py](backend/patients/views.py) - `_parse_llm_analysis_response()`, `_build_preprocess_report()`

---

### **5. Génération des sorties**
- ✅ **Rapport JSON** - Session sauvegardée en `/backend/patients/preprocess_sessions/{uuid}.json`
- ✅ **Excel corrigé** - Export disponible via `/preprocess/{id}/export/`
- ✅ **Preview** - 20 lignes originales + 20 lignes corrigées affichées en UI

**Code:** [backend/patients/views.py](backend/patients/views.py) - `_build_preprocess_report()`, `PatientPreprocessExportView`

---

### **6. Interaction utilisateur (CRUD sur V1)**
- ✅ **Session management** - Stockage persistant de l'état d'analyse
- ✅ **Row editing** - Modification individuelle via `/preprocess/{id}/rows/{row_index}/`
- ✅ **Change log** - Suivi des modifications utilisateur
- ✅ **Preview live** - Affichage des corrections proposées

**Code:** [backend/patients/views.py](backend/patients/views.py) - `PatientPreprocessRowDetailView`, `PatientPreprocessRowsView`

---

### **7. Validation utilisateur**
- ✅ **Choix version** - Boutons "Exporter corrigé" vs "Intégrer" en UI
- ✅ **Confirmation** - Dialog avant intégration définitive
- ✅ **Audit trail** - Enregistrement de qui a fait quoi et quand

**Code:** [backend/patients/views.py](backend/patients/views.py) - `PatientPreprocessIntegrateView`

---

### **8. Transition vers Onglet Gestion**
- ✅ Après intégration, les rows sont importées dans table `patients_Patient`
- ✅ Redirection vers la gestion des patients
- ✅ Historique d'import traçable via audit logs

**Code:** [backend/patients/views.py](backend/patients/views.py) - `PatientPreprocessIntegrateView.post()`

---

### **9. Application du column_mapping.json**
- ✅ Mapping colonnes CSV → schéma interne
- ✅ Application lors de l'intégration (relinking colonnes dynamiques)
- ✅ Support de colonnes custom via `column_mapping.json`

**Fichier:** [backend/patients/column_mapping.json](backend/patients/column_mapping.json)

**Code:** [backend/patients/views.py](backend/patients/views.py) - `_apply_column_mapping()`

---

### **10. Intégration dans la plateforme**
- ✅ Insertion bulk dans PostgreSQL
- ✅ Relations avec modèles existants (Patient, PatientFormTemplate, etc.)
- ✅ Gestion des conflits (doublons, clés primaires)
- ✅ Transaction rollback en cas d'erreur

**Code:** [backend/patients/views.py](backend/patients/views.py) - `PatientPreprocessIntegrateView`

---

## 🚀 Architecture Asynchrone

### **Avant (Synchrone):**
```
User Upload → API → LLM Analysis (5-10min) → Response → TIMEOUT
               ❌ Bloquer l'UI pendant l'analyse
```

### **Après (Asynchrone avec Celery):**
```
User Upload → API (202 ACCEPTED) → Dispatch Task → Return session_id
               ↓
              UI affiche "En attente..."
               ↓
              Poll /status/ toutes les 2s
               ↓
         Celery Worker (backend)
               ├→ Lit fichier
               ├→ Profilage Pandas
               ├→ Appelle LLM (long)
               ├→ Applique corrections
               ├→ Sauvegarde session (status=completed)
               ↓
              UI reçoit rapport → Affiche résultats
```

### **Services:**
- ✅ **Redis** (port 6379) - Message broker + result backend
- ✅ **Celery Worker** - Traite tasks asynchrones
- ✅ **Backend Django** - API dispatcher
- ✅ **Ollama** (port 11434) - Inférence LLM
- ✅ **PostgreSQL** (port 5432) - Persistance

---

## 📡 Endpoints API

| Endpoint | Méthode | Statut | Rôle |
|----------|---------|--------|------|
| `/preprocess/health/` | GET | 200 | Vérifier Ollama |
| `/preprocess/analyze/` | POST | **202** | Dispatcher job async |
| `/preprocess/{id}/status/` | GET | 200 | Tracker progression |
| `/preprocess/{id}/` | GET | 200 | Charger session |
| `/preprocess/{id}/rows/` | GET | 200 | Lister rows |
| `/preprocess/{id}/rows/{idx}/` | GET/PATCH | 200 | Modifier row |
| `/preprocess/{id}/export/` | GET | 200 | Exporter Excel |
| `/preprocess/{id}/integrate/` | POST | 200 | Intégrer patients |

---

## 📊 Flux Utilisateur Complet

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Upload fichier CSV/Excel via UI                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ POST /preprocess/   │
        │ analyze/            │
        │ (multipart file)    │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────────────────────────┐
        │ Backend:                                     │
        │ - Crée session {id, status=pending}        │
        │ - Sauvegarde fichier temp                  │
        │ - Dispatch task Celery                     │
        │ Return 202 ACCEPTED + preprocess_id        │
        └──────────┬──────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ UI affiche          │
        │ "En attente..."     │
        │ Lance polling       │
        │ toutes les 2s       │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────────────────────────┐
        │ Celery Worker (bg):                          │
        │ 2. Lit DataFrame                            │
        │ 3. Profilage Pandas                         │
        │ 4. Appelle Ollama /api/generate            │
        │    (peut prendre 1-5 min)                  │
        │ 5. Applique corrections                    │
        │ 6. Sauvegarde rapport                      │
        │ Update session {status=completed, report}  │
        └──────────┬──────────────────────────────────┘
                   │
        ┌──────────▼────────────────────┐
        │ UI polling reçoit completed   │
        │ GET /preprocess/{id}/status/  │
        │ Affiche:                       │
        │ - Score qualité               │
        │ - Issues détectées            │
        │ - Recommandations            │
        │ - Preview avant/après        │
        └──────────┬────────────────────┘
                   │
        ┌──────────▼────────────────────┐
        │ User valide corrections ou    │
        │ exporte Excel                 │
        └──────────┬────────────────────┘
                   │
        ┌──────────▼─────────────────────────────────┐
        │ User clique "Intégrer"                      │
        │ POST /preprocess/{id}/integrate/           │
        │ Backend:                                    │
        │ - Import rows dans Patient table          │
        │ - Apply column_mapping.json               │
        │ - Création audit logs                     │
        └──────────┬─────────────────────────────────┘
                   │
        ┌──────────▼────────────────────┐
        │ Redirection vers Gestion tab  │
        │ Patients visibles dans liste  │
        └────────────────────────────────┘
```

---

## 🛠️ Configuration

### **Env Vars Backend** (docker-compose.yml)
```bash
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_TIMEOUT_SECONDS=300
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### **Payload Sizing** (ajustables via env)
```bash
OLLAMA_PREVIEW_ROWS=10
OLLAMA_COLUMN_SAMPLES=5
OLLAMA_MAX_COLUMNS=30
OLLAMA_MAX_VALUE_CHARS=100
```

---

## 📈 Performance

| Taille Dataset | Temps Analyse | Notes |
|---|---|---|
| <50 rows, <10 cols | ~10-15s | Très rapide |
| 100 rows, 20 cols | ~20-30s | Normal |
| 478 rows, 85 cols | ~2-5min | CPU-bound (Qwen) |
| >1000 rows | + Config Ollama | Scaling needed |

**Optimisations possibles:**
- Réduire `num_predict` de 120 → 30 (plus rapide)
- Réduire `OLLAMA_PREVIEW_ROWS` de 10 → 5
- Utiliser qwen2.5:3b-instruct (léger) au lieu de 7b
- Scaler Celery workers (multiply dans docker-compose)

---

## ✨ Cas d'Usage Supportés

- ✅ **Import CSV basique** (patient_id, nom, age, diagnostic, date_visite)
- ✅ **Import Excel complexe** (multiples feuilles, types mixtes)
- ✅ **Données médicales** (détection anomalies domaine-spécifiques)
- ✅ **Gestion des valeurs manquantes** (NaN/NULL detection)
- ✅ **Nettoyage de colonnes** (trim whitespace, case normalization)
- ✅ **Type casting** (text→date, string→numeric)
- ✅ **Mapping personnalisé** (colonnes dynamiques)
- ✅ **Audit trail complet** (qui, quand, quoi)

---

## 🐛 Débogage

### **Voir les tasks en cours:**
```bash
docker compose logs celery-worker --tail 50
```

### **Vérifier Redis:**
```bash
docker compose exec redis redis-cli KEYS "*"
```

### **Tester Ollama directement:**
```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:7b-instruct","prompt":"Hello","stream":false}'
```

### **Vérifier health API:**
```bash
curl http://localhost:8000/api/patients/preprocess/health/
```

---

## 📝 Prochaines Étapes (Optionnelles)

1. **Monitoring** - Ajouter Flower pour visualiser tasks Celery
2. **Webhooks** - Notifier utilisateur quand analyse terminée
3. **Batch imports** - Traiter plusieurs fichiers en parallèle
4. **Caching** - Mettre en cache résultats LLM pour datasets similaires
5. **Version models** - Historique des modèles Ollama utilisés
6. **Export formats** - Ajouter CSV, JSON, Parquet en sortie
7. **Scheduling** - Plannifier imports récurrents via Celery Beat

---

## ✅ Status Complet

```
✅ Backend infrastructure (Django + DRF + Celery)
✅ Frontend UI (React + MUI)
✅ LLM integration (Ollama + Qwen)
✅ Async job processing (Redis + Celery)
✅ Database persistence (PostgreSQL)
✅ File handling (Pandas + openpyxl + xlrd)
✅ Error handling & logging
✅ Audit trail
✅ Docker Compose orchestration
✅ API endpoints
✅ Health checks
```

## 🎯 Test End-to-End

**Command:** `npm run test:preprocessing`

**What it does:**
1. Upload 50-row CSV
2. Wait for Ollama analysis (2-5 min)
3. Verify quality_score > 50
4. Export Excel
5. Integrate into Patients table
6. Confirm rows in database

**Status:** ✅ Ready to test
