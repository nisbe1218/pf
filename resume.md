# 📋 **Vue d'ensemble - Plateforme Médicale**

## **Architecture générale**

```
┌─ Frontend React (http://localhost:3000)
│  └─ Pages: Dashboard, Gestion Patients, IA/Prédictions, Patient Monitoring Board, Profil
│
├─ Backend Django REST (http://localhost:8000/api/)
│  ├─ users → Authentification, rôles, permissions
│  ├─ patients → CRUD patients, import Excel/CSV, schémas
│  ├─ predictions → Modèles IA (mortalité, coagulation)
│  └─ audit → Journalisation des actions
│
└─ PostgreSQL (base: plateforme_medicale)
   └─ Données: utilisateurs, patients, prédictions, logs d'audit
```

---

## **🔐 Les 4 rôles & permissions**

| Rôle | Permissions | Accès |
|------|------------|-------|
| **Super Administrateur** | Gère tous les utilisateurs, comptes, rôles • Voit stats globales • Import/validation patients | **Dashboard admin** (tous compteurs visibles) |
| **Chef de Service** | Crée/modifie professeurs & résidents • Valide imports patients • Voit ses équipes | **Dashboard gestion** (stats équipe) |
| **Professeur** | Lit patients • Participe à prédictions IA • Évalue résidents | **Dashboard personnel** (mes patients, tâches pédagogiques) |
| **Résident** | Lit patients supervisés • Consulte modèles IA • Soumet rapports à prof | **Dashboard apprenti** (ma progression, cas à étudier) |

**Contrôle d'accès:**
- ✅ Lecture patients: **tous les rôles authentifiés**  
- ❌ Écriture/suppression patients: **super_admin + chef_service seulement**  
- ❌ Gestion utilisateurs: **super_admin + chef_service seulement**  

---

## **🔄 Workflows principaux**

### **1️⃣ Authentification**
```
Utilisateur → Login (email + mot de passe)
            → Token JWT généré & stocké (localStorage)
            → Redirigé vers dashboard selon rôle
            → À chaque requête API: header Authorization: Bearer {token}
```

### **2️⃣ Gestion des patients (Super Admin / Chef Service)**
```
Créer/Modifier/Supprimer
  → Formulaire dans PatientsManagement.js
  → POST/PUT/PATCH/DELETE /api/patients/
  → Backend valide + stocke PostgreSQL
  → Frontend rafraîchit liste

Import Excel/CSV
  → Upload fichier multipart
  → Backend: Pandas lit, normalise, valide colonnes
  → Patients créés en base (statut: "pending validation")
  → Chef Service/Admin valide l'import
  → AuditLog enregistre qui + quand + action
```

### **3️⃣ Prédictions IA (tous les rôles)**
```
Professeur/Résident → Sélectionne modèle (mortalité ou coagulation)
                    → Remplit variables cliniques
                    → POST /api/predictions/predict/
                    → Backend exécute modèle ML (scikit-learn, XGBoost, etc.)
                    → Retourne score risque + facteurs explicatifs
                    → Historique des prédictions loggé
```

### **4️⃣ Dashboard & visualisation**
```
Super Admin  → Stats globales: tous comptes, patients, imports, activités
Chef Service → Stats équipe: ses professeurs/résidents, leurs patients
Professeur   → Ses patients, demandes validation, feedback résidents
Résident     → Ma progression, cas à étudier, checkpoints de formation
```

---

## **📊 Flux de données**

### **Frontend → Backend → PostgreSQL**

```
1. Frontend (React)
   ├─ Récupère token JWT (AuthContext)
   ├─ Construits requête API avec header Authorization
   └─ Envoie: GET /api/patients/ ou POST /api/predictions/predict/

2. Backend (Django REST)
   ├─ Valide token + rôle utilisateur
   ├─ Applique CanViewPatients permission (lecture OK, écriture admin seulement)
   ├─ Récupère/traite données
   └─ Retourne JSON response

3. PostgreSQL
   ├─ Tables principales:
   │  ├─ users.Utilisateur (email, nom, prenom, role_id)
   │  ├─ patients.Patient (100+ colonnes cliniques)
   │  ├─ predictions.PredictionLog (prédictions historisées)
   │  └─ audit.AuditLog (qui a fait quoi, quand)
   └─ Index optimisés sur: user_id, created_at, patient_id

4. Frontend affiche résultat
```

---

## **📱 Pages principales par rôle**

### **Dashboard** (`frontend/src/pages/dashboard/Dashboard.js`)
```
Super Admin:
  - 0 Comptes visibles | 0 Actifs | 0 Inactifs | 0 Professeurs | 0 Résidents | 0 Rôles
  - Boutons: Créer user, Éditer, Supprimer, Modifier rôle
  - Gestion complète utilisateurs

Chef Service:
  - Stats équipe (ses prof/résidents)
  - Validation imports patients
  - Gestion de ses utilisateurs

Professeur / Résident:
  - Mes patients personnels
  - Mes tâches de formation
  - Alertes / notifications
  - (Admin visible auparavant → CORRECTIF APPLIQUÉ ✅)
```

### **Gestion Patients** (`PatientsManagement.js`)
```
- Liste filtrable des patients (CRUD)
- Import Excel/CSV avec détection colonnes dynamiques
- Validation d'import (2 niveaux: chef service/admin)
- Graphiques trend (analyse onglet)
- Schéma patient flexible (dynamique)
```

### **Modèles IA** (`ModelAI.js`)
```
- Sélection du type de prédiction (mortalité, coagulation)
- Sélection du modèle (Random Forest, XGBoost, LightGBM, CatBoost)
- Remplissage des variables cliniques
- Lancement prédiction + résultats (score + interprétation)
- Historique prédictions par patient
```

### **Profil utilisateur** (`frontend/src/pages/profile/Profile.js`)
```
- Consultation des informations du compte connecté
- Changement du mot de passe avec confirmation du mot de passe actuel
- Historique des actions liées aux utilisateurs et aux mots de passe
- Affichage détaillé de ces actions pour Super Admin / Chef de service
- La bascule de langue FR/EN n'est pas encore implémentée dans le code actuel
```

### **Patient Monitoring Board** (`vue patient centree`)
```
- Recherche d'un patient par identifiant ou nom
- Vue centrée sur un seul dossier patient
- 3 colonnes: informations cliniques, historique des actions, résultats IA
- Colonne historique complete pour Super Admin / Chef de service
- Timeline simplifiee pour Professeur / Resident
- Section IA affichee seulement si une prediction existe
- Chargement a la demande pour garder une interface legere
```

Documentation dediee: [monitor.md](monitor.md)

---

## **🔍 Exemple: Workflow complet (Professeur utilisant IA)**

```
1. Prof se connecte (email + pass)
   → JWT token généré + stocké

2. Arrive sur Dashboard Prof
   → Affiche: mes patients (20), tâches pédagogiques (3), cas du jour
   → N'affiche PAS: gestion user, stats globales

3. Clique "Prédictions" → Page IA
   → Sélectionne un patient
   → Choisit modèle "Mortalité - Random Forest"
   → Remplit variables (âge, créatinine, etc.)
   → POST /api/predictions/predict/
   
4. Backend reçoit:
   → Valide token = rôle "professeur" = OK pour lire
   → Exécute modèle Random Forest
   → Retourne: score=0.72, statut="RISQUE ÉLEVÉ", facteurs=[créatinine, âge]
   → Log audit: "Prof X a lancé prédiction patient Y"

5. Frontend affiche résultat
   → Graphique risk score
   → Liste facteurs explicatifs
   → Historique des prédictions
```

---

## **🛡️ Sécurité & contrôle d'accès**

- **Authentification**: JWT (stateless)
- **Routes protégées**: ProtectedRoute.js vérifie `user.role` avant accès
- **Permissions backend**: Décorateurs `@permission_classes` sur chaque endpoint
- **CORS**: django-cors-headers autorise frontend → backend
- **Audit**: Chaque action écrite dans `AuditLog` (user, action, timestamp)
- **Secrets**: Variables d'env (.env) pour SECRET_KEY, DB_PASSWORD, etc.

---

## **🚀 Déploiement local**

```bash
docker-compose up --build
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# PostgreSQL: accessible via connexion interne (host=db)
```

---

**La plateforme est une application médicale collaborative où chaque rôle a un accès granulaire aux données patients et aux outils IA, avec audit complet des actions.**
