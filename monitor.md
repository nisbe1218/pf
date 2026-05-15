# Patient Monitoring Board

Le Patient Monitoring Board est une interface centree sur un seul patient, accessible apres recherche par identifiant ou par nom.

## Objectif

Fournir une vue clinique unifiee qui regroupe:
- les informations generales du patient,
- l'historique des actions et des evenements,
- les resultats d'intelligence artificielle lies au patient.

## Structure

### Colonne 1 - Informations cliniques
- Identite du patient
- Donnees demographiques
- Parametres biologiques essentiels
- Score de risque a 1 an si une prediction existe

### Colonne 2 - Historique des actions
- Consultation du dossier
- Ajout ou modification des donnees
- Lancement de predictions
- Validations medicales

Affichage selon le role:
- Super Administrateur et Chef de service: audit complet avec utilisateur, role, action et horodatage
- Professeur et Resident: timeline simplifiee, orientee lecture clinique

### Colonne 3 - Intelligence artificielle
- Score de risque
- Principaux facteurs de risque
- Elements explicatifs du modele
- Section vide ou informative si aucune prediction n'a encore ete lancee

## Principes

- Chargement a la demande apres selection du patient
- Affichage conditionnel selon l'existence des donnees
- Respect strict des droits d'acces par role
- Interface legere, lisible et centree sur le parcours clinique du patient
