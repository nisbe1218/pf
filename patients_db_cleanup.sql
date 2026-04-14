-- Nettoyage et organisation de la base de données patients

-- 1. Supprimer les tables redondantes (hors tables principales)
DROP TABLE IF EXISTS patients_plateforme CASCADE;
DROP TABLE IF EXISTS patients_patientformresponse CASCADE;

-- 2. Corriger la structure de la table principale patient
DROP TABLE IF EXISTS patients_patient CASCADE;
CREATE TABLE patients_patient (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100),
    prenom VARCHAR(100),
    date_naissance DATE,
    sexe VARCHAR(10),
    extra_data JSONB
);

-- 3. Corriger/Créer la table des templates de formulaire
DROP TABLE IF EXISTS patients_patientformtemplate CASCADE;
CREATE TABLE patients_patientformtemplate (
    id SERIAL PRIMARY KEY,
    nom_template VARCHAR(100),
    date_version DATE,
    description TEXT
);

-- 4. Corriger/Créer la table des champs de formulaire
DROP TABLE IF EXISTS patients_patientformfield CASCADE;
CREATE TABLE patients_patientformfield (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES patients_patientformtemplate(id),
    nom_champ VARCHAR(100),
    type_champ VARCHAR(50),
    contraintes TEXT,
    ordre INTEGER
);

-- 5. Créer la table des réponses dynamiques
CREATE TABLE patients_patientformresponse (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients_patient(id),
    field_id INTEGER REFERENCES patients_patientformfield(id),
    valeur TEXT
);

-- 6. (Optionnel) Recréer la table d'export si besoin
-- CREATE TABLE patients_plateforme (...)
-- (à utiliser uniquement pour l'export ou les vues "flat")
