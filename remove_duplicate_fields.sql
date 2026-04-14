-- Supprimer les champs déjà présents dans la table principale du formulaire dynamique
DELETE FROM patients_patientformfield WHERE nom_champ IN ('âge', 'sexe', 'date_naissance', 'maladie');
