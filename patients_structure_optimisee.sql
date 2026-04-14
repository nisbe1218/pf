-- Table principale patient
CREATE TABLE patients_patient (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100),
    prenom VARCHAR(100),
    date_naissance DATE,
    sexe VARCHAR(10),
    extra_data JSONB
);

-- Table des templates de formulaire
CREATE TABLE patients_patientformtemplate (
    id SERIAL PRIMARY KEY,
    nom_template VARCHAR(100),
    date_version DATE,
    description TEXT
);

-- Table des champs de formulaire
CREATE TABLE patients_patientformfield (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES patients_patientformtemplate(id),
    nom_champ VARCHAR(100),
    type_champ VARCHAR(50),
    contraintes TEXT,
    ordre INTEGER
);

-- Table des réponses dynamiques
CREATE TABLE patients_patientformresponse (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients_patient(id),
    field_id INTEGER REFERENCES patients_patientformfield(id),
    valeur TEXT
);
