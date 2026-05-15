import React, { useContext, useEffect, useMemo, useState, useCallback } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  Grid,
  IconButton,
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AppSidebar from '../../components/common/AppSidebar';
import api from '../../services/api/axios';
import { AuthContext } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';

// ── Constantes ───────────────────────────────────────────────────────────────

const PREDICTION_TYPES = [
  {
    value: 'mortalite',
    label: 'Mortalité 1 an',
    detail: 'Prédit le risque de décès dans l\'année suivant l\'évaluation.',
  },
  {
    value: 'coagulation',
    label: 'Coagulation',
    detail: 'Détecte le risque de complications hémorragiques ou thrombotiques.',
  },
];

const MODEL_OPTIONS = [
  { value: 'random_forest', label: 'Random Forest', description: 'Recommandé par défaut — robuste et performant' },
  { value: 'extra_trees', label: 'Extra Trees', description: 'Ensemble robuste souvent plus stable que Random Forest' },
  { value: 'adaboost', label: 'AdaBoost', description: 'Renforce les faiblesses des arbres pour plus de précision' },
  { value: 'xgboost', label: 'XGBoost', description: 'Très performant sur données tabulaires' },
  { value: 'logistic_regression', label: 'Régression logistique', description: 'Interprétable, bon pour cas simples' },
  { value: 'svm', label: 'SVM', description: 'Efficace sur données complexes et non linéaires' },
  { value: 'gradient_boosting', label: 'Gradient Boosting', description: 'Robuste, stable, bons résultats' },
  { value: 'decision_tree', label: 'Arbre de décision', description: 'Explicable, idéal pour la formation médicale' },
];

const MODEL_RECOMMENDATIONS = {
  mortalite: ['random_forest', 'extra_trees', 'adaboost', 'gradient_boosting', 'xgboost'],
  coagulation: ['logistic_regression', 'svm', 'gradient_boosting'],
};

const ROSE_ACCENT = {
  soft: '#e8c4d4',
  mid: '#c97b99',
  deep: '#9e3d6a',
};

const SURFACE_CARD_SX = {
  borderRadius: 5,
  border: '1px solid rgba(201,123,153,0.18)',
  background: 'linear-gradient(180deg, rgba(255,255,255,.98), rgba(250,246,250,.92))',
  boxShadow: '0 18px 48px rgba(24,35,68,.08)',
  backdropFilter: 'blur(16px)',
  transition: 'transform .22s ease, box-shadow .22s ease',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 20px 52px rgba(158,61,106,.14)',
  },
};

const PANEL_SX = {
  borderRadius: 4,
  border: '1px solid rgba(201,123,153,0.16)',
  background: 'rgba(255,252,255,.84)',
  boxShadow: '0 14px 36px rgba(24,35,68,.06)',
};

const RISK_COLORS = {
  Faible: '#399776',
  Modéré: '#E4A330',
  Élevé: '#D4433D',
};

const RISK_THRESHOLDS = { Faible: 30, Modéré: 70 };

const VARIABLE_LABELS = {
  adresse: 'Adresse',
  age: 'Âge',
  age_years: 'Âge',
  sexe: 'Sexe',
  sex: 'Sexe',
  date_admission: 'Date d\'admission',
  date_evaluation_initiale: 'Date d\'évaluation initiale',
  date_naissance: 'Date de naissance',
  derniere_mise_a_jour: 'Dernière mise à jour',
  maladie: 'Maladie',
  telephone: 'Téléphone',
  statut_consentement: 'Statut consentement',
  utilisateur_saisie: 'Utilisateur saisie',
  id_patient: 'ID patient',
  id_enregistrement_source: 'ID enregistrement source',
  id_site: 'ID site',
  statut_inclusion: 'Statut inclusion',
  demographie_sexe: 'Démographie - sexe',
  demographie_date_naissance: 'Démographie - date de naissance',
  demographie_age_ans: 'Démographie - âge',
  demographie_statut_matrimonial: 'Démographie - statut matrimonial',
  demographie_mode_vie: 'Démographie - mode de vie',
  demographie_zone_residence: 'Démographie - zone de résidence',
  demographie_distance_centre_km: 'Démographie - distance au centre (km)',
  demographie_couverture_sociale: 'Démographie - couverture sociale',
  demographie_statut_professionnel: 'Démographie - statut professionnel',
  demographie_niveau_education: 'Démographie - niveau d\'éducation',
  demographie_tabagisme: 'Démographie - tabagisme',
  demographie_alcool: 'Démographie - alcool',
  irc_date_premier_contact_nephrologique: 'IRC - date premier contact',
  irc_etiologie_principale: 'IRC - étiologie principale',
  irc_etiologie_secondaire: 'IRC - étiologie secondaire',
  irc_maladie_renale_hereditaire: 'IRC - maladie rénale héréditaire',
  irc_antecedents_familiaux_renaux: 'IRC - antécédents familiaux',
  irc_statut_biopsie_renale: 'IRC - statut biopsie rénale',
  irc_resultat_biopsie_renale: 'IRC - résultat biopsie rénale',
  irc_connue_avant_dialyse: 'IRC - connue avant dialyse',
  irc_source_adressage: 'IRC - source adressage',
  irc_contexte_debut_dialyse: 'IRC - contexte début dialyse',
  irc_duree_suivi_predialytique_mois: 'IRC - durée suivi prédialytique (mois)',
  irc_themes_education_therapeutique: 'IRC - thèmes éducation',
  irc_niveau_comprehension_patient: 'IRC - niveau compréhension patient',
  irc_preference_therapie_renale: 'IRC - préférence thérapie rénale',
  comorbidite_statut_diabete: 'Comorbidités - statut diabète',
  comorbidite_liste: 'Comorbidités - liste',
  comorbidite_autre: 'Comorbidités - autre',
  comorbidite_exposition_toxique: 'Comorbidités - exposition toxique',
  comorbidite_antecedents_medicaments_nephrotoxiques: 'Comorbidités - médicaments néphrotoxiques',
  presentation_date_episode: 'Présentation - date épisode',
  presentation_lieu_debut: 'Présentation - lieu de début',
  presentation_raisons_debut: 'Présentation - raisons de début',
  presentation_symptomes: 'Présentation - symptômes',
  presentation_tas_mmhg: 'Présentation - TAS (mmHg)',
  presentation_tad_mmhg: 'Présentation - TAD (mmHg)',
  presentation_frequence_cardiaque_bpm: 'Présentation - fréquence cardiaque (bpm)',
  presentation_temperature_c: 'Présentation - température (°C)',
  presentation_poids_kg: 'Présentation - poids (kg)',
  presentation_taille_cm: 'Présentation - taille (cm)',
  presentation_statut_diurese: 'Présentation - statut diurèse',
  presentation_volume_urinaire_ml_j: 'Présentation - volume urinaire (ml/j)',
  presentation_autonomie_fonctionnelle: 'Présentation - autonomie fonctionnelle',
  presentation_notes_examen_clinique: 'Présentation - notes examen clinique',
  biologie_date_prelevement: 'Biologie - date prélèvement',
  biologie_dfg_mdrd_ml_min_1_73m2: 'Biologie - DFG MDRD (ml/min/1,73m²)',
  biologie_creatinine_mg_l: 'Biologie - créatinine (mg/L)',
  biologie_uree_g_l: 'Biologie - urée (g/L)',
  biologie_hemoglobine_g_dl: 'Biologie - hémoglobine (g/dL)',
  biologie_hba1c_pct: 'Biologie - HbA1c (%)',
  biologie_leucocytes_g_l: 'Biologie - leucocytes (G/L)',
  biologie_plaquettes_g_l: 'Biologie - plaquettes (G/L)',
  biologie_albumine_g_l: 'Biologie - albumine (g/L)',
  biologie_crp_mg_l: 'Biologie - CRP (mg/L)',
  biologie_sodium_mmol_l: 'Biologie - sodium (mmol/L)',
  biologie_potassium_mmol_l: 'Biologie - potassium (mmol/L)',
  biologie_bicarbonates_mmol_l: 'Biologie - bicarbonates (mmol/L)',
  biologie_calcium_corrige_mg_l: 'Biologie - calcium corrigé (mg/L)',
  biologie_phosphore_mg_l: 'Biologie - phosphore (mg/L)',
  biologie_pth_pg_ml: 'Biologie - PTH (pg/mL)',
  biologie_ferritine_ng_ml: 'Biologie - ferritine (ng/mL)',
  doietal_risk_score: 'Score de risque Doi',
  biologie_saturation_transferrine_pct: 'Biologie - saturation transferrine (%)',
  biologie_vitamine_d_ng_ml: 'Biologie - vitamine D (ng/mL)',
  biologie_proteinurie_g_24h: 'Biologie - protéinurie (g/24h)',
  biologie_hbsag: 'Biologie - HBsAg',
  biologie_vhc: 'Biologie - VHC',
  biologie_vih: 'Biologie - VIH',
  imagerie_date_echographie_renale: 'Imagerie - date échographie rénale',
  imagerie_taille_reins: 'Imagerie - taille reins',
  imagerie_echogenicite_renale: 'Imagerie - échogénicité rénale',
  imagerie_hydronephrose: 'Imagerie - hydronéphrose',
  imagerie_kystes_renaux: 'Imagerie - kystes rénaux',
  imagerie_lithiase: 'Imagerie - lithiase',
  imagerie_radiographie_thorax: 'Imagerie - radiographie thorax',
  imagerie_date_echocardiographie: 'Imagerie - date échocardiographie',
  imagerie_fevg_pct: 'Imagerie - FEVG (%)',
  imagerie_hypertrophie_ventriculaire_gauche: 'Imagerie - hypertrophie VG',
  imagerie_valvulopathie: 'Imagerie - valvulopathie',
  imagerie_autres_resultats: 'Imagerie - autres résultats',
  dialyse_date_debut: 'Dialyse - date de début',
  dialyse_modalite_initiale: 'Dialyse - modalité initiale',
  dialyse_modalite_actuelle: 'Dialyse - modalité actuelle',
  dialyse_type_acces_initial: 'Dialyse - type accès initial',
  dialyse_site_acces_initial: 'Dialyse - site accès initial',
  dialyse_seances_par_semaine: 'Dialyse - séances/semaine',
  dialyse_duree_seance_min: 'Dialyse - durée séance (min)',
  dialyse_debit_sanguin_ml_min: 'Dialyse - débit sanguin (ml/min)',
  dialyse_debit_dialysat_ml_min: 'Dialyse - débit dialysat (ml/min)',
  dialyse_potassium_dialysat_mmol_l: 'Dialyse - potassium dialysat (mmol/L)',
  dialyse_calcium_dialysat_mmol_l: 'Dialyse - calcium dialysat (mmol/L)',
  dialyse_type_anticoagulation: 'Dialyse - type anticoagulation',
  dialyse_statut_fonction_renale_residuelle: 'Dialyse - fonction rénale résiduelle',
  dialyse_type_regime_dp: 'Dialyse - type régime DP',
  dialyse_nombre_echanges_dp_jour: 'Dialyse - échanges DP/jour',
  dialyse_volume_stase_dp_ml: 'Dialyse - volume stase DP (ml)',
  dialyse_jours_entre_catheter_et_fav: 'Dialyse - jours cathéter→FAV',
  dialyse_acces_admission_tunnelise: 'Dialyse - accès tunnelisé',
  dialyse_acces_admission_femoral: 'Dialyse - accès fémoral',
  dialyse_acces_admission_fav: 'Dialyse - accès FAV',
  dialyse_acces_admission_peritoneale: 'Dialyse - accès péritonéal',
  dialyse_statut_liste_attente_transplantation: 'Dialyse - liste attente transplantation',
  qualite_date_evaluation: 'Qualité - date évaluation',
  qualite_spktv: 'Qualité - Sp.Kt/V',
  qualite_urr_pct: 'Qualité - URR (%)',
  qualite_prise_poids_interdialytique_kg: 'Qualité - prise poids interdialytique (kg)',
  qualite_taux_ultrafiltration_ml_kg_h: 'Qualité - ultrafiltration (ml/kg/h)',
  qualite_tas_predialyse_mmhg: 'Qualité - TAS prédialyse (mmHg)',
  qualite_tas_postdialyse_mmhg: 'Qualité - TAS postdialyse (mmHg)',
  qualite_poids_sec_kg: 'Qualité - poids sec (kg)',
  qualite_seances_manquees_30j: 'Qualité - séances manquées/30j',
  qualite_seances_raccourcies_30j: 'Qualité - séances raccourcies/30j',
  qualite_hypotensions_intradialytiques_30j: 'Qualité - hypotensions intradialytiques/30j',
  qualite_observance_declaree_patient: 'Qualité - observance patient',
  education_connaissance_pratique_dialyse: 'Éducation - pratique dialyse',
  education_soins_acces_vasculaire: 'Éducation - soins accès vasculaire',
  education_surveillance_poids_fluides: 'Éducation - surveillance poids/fluides',
  education_dietetique: 'Éducation - diététique',
  education_traitements_associes: 'Éducation - traitements associés',
  education_complications: 'Éducation - complications',
  traitement_medicaments_renaux_actuels: 'Traitement - médicaments rénaux',
  traitement_autres_notes: 'Traitement - autres notes',
  complication_debut_periode_suivi: 'Complication - début suivi',
  complication_fin_periode_suivi: 'Complication - fin suivi',
  complication_liste: 'Complication - liste',
  complication_date_premier_evenement: 'Complication - date premier événement',
  complication_nombre_hospitalisations: 'Complication - nombre hospitalisations',
  complication_jours_hospitalisation: 'Complication - jours hospitalisation',
  complication_motifs_hospitalisation: 'Complication - motifs hospitalisation',
  complication_changement_modalite_dialyse: 'Complication - changement modalité dialyse',
  complication_autres_notes: 'Complication - autres notes',
  devenir_date_dernier_suivi: 'Devenir - date dernier suivi',
  devenir_statut: 'Devenir - statut',
  devenir_date_deces: 'Devenir - date de décès',
  devenir_cause_deces: 'Devenir - cause décès',
  devenir_delai_deces_jours: 'Devenir - délai décès (jours)',
  devenir_date_transplantation: 'Devenir - date transplantation',
  devenir_qualite_vie: 'Devenir - qualité de vie',
  devenir_categorie_pronostique: 'Devenir - catégorie pronostique',
  devenir_notes: 'Devenir - notes',
  immunologie_transfusion_immunisation: 'Immunologie - transfusion/immunisation',
};

const VARIABLE_GROUPS = [
  {
    title: 'Données biologiques',
    description: 'Créatinine, urée, potassium, albumine, hémoglobine, CRP, protéinurie',
    fields: [
      'biologie_albumine_g_l', 'biologie_bicarbonates_mmol_l', 'biologie_calcium_corrige_mg_l',
      'biologie_creatinine_mg_l', 'biologie_crp_mg_l', 'biologie_dfg_mdrd_ml_min_1_73m2',
      'biologie_ferritine_ng_ml', 'biologie_hba1c_pct', 'biologie_hbsag',
      'biologie_hemoglobine_g_dl', 'biologie_leucocytes_g_l', 'biologie_phosphore_mg_l',
      'biologie_plaquettes_g_l', 'biologie_potassium_mmol_l', 'biologie_proteinurie_g_24h',
      'biologie_pth_pg_ml', 'biologie_saturation_transferrine_pct', 'biologie_sodium_mmol_l',
      'biologie_uree_g_l', 'biologie_vhc', 'biologie_vih', 'biologie_vitamine_d_ng_ml',
    ],
  },
  {
    title: 'Données cliniques',
    description: 'Signes vitaux, poids, température, diurèse',
    fields: [
      'presentation_autonomie_fonctionnelle', 'presentation_frequence_cardiaque_bpm',
      'presentation_notes_examen_clinique', 'presentation_poids_kg',
      'presentation_statut_diurese', 'presentation_symptomes', 'presentation_tad_mmhg',
      'presentation_taille_cm', 'presentation_tas_mmhg', 'presentation_temperature_c',
      'presentation_volume_urinaire_ml_j',
    ],
  },
  {
    title: 'Données démographiques',
    description: 'Âge, sexe, mode de vie, couverture sociale',
    fields: [
      'age', 'sexe', 'demographie_age_ans', 'demographie_alcool',
      'demographie_couverture_sociale', 'demographie_distance_centre_km',
      'demographie_mode_vie', 'demographie_niveau_education',
      'demographie_sexe', 'demographie_statut_matrimonial',
      'demographie_statut_professionnel', 'demographie_tabagisme',
      'demographie_zone_residence',
    ],
  },
  {
    title: 'Données d\'évaluation',
    description: 'Dates de l\'évaluation et du dossier patient',
    fields: ['date_evaluation_initiale'],
  },
  {
    title: 'Données dialyse',
    description: 'Modalité, accès, séances, débit, anticoagulation',
    fields: [
      'dialyse_acces_admission_fav', 'dialyse_acces_admission_femoral',
      'dialyse_acces_admission_peritoneale', 'dialyse_acces_admission_tunnelise',
      'dialyse_calcium_dialysat_mmol_l', 'dialyse_debit_dialysat_ml_min',
      'dialyse_debit_sanguin_ml_min', 'dialyse_duree_seance_min',
      'dialyse_jours_entre_catheter_et_fav', 'dialyse_modalite_actuelle',
      'dialyse_modalite_initiale', 'dialyse_nombre_echanges_dp_jour',
      'dialyse_potassium_dialysat_mmol_l', 'dialyse_seances_par_semaine',
      'dialyse_site_acces_initial', 'dialyse_statut_fonction_renale_residuelle',
      'dialyse_statut_liste_attente_transplantation', 'dialyse_type_acces_initial',
      'dialyse_type_anticoagulation', 'dialyse_type_regime_dp',
      'dialyse_volume_stase_dp_ml',
    ],
  },
  {
    title: 'Données néphropathie (IRC)',
    description: 'Étiologie, contexte, suivi pré-dialyse, biopsie',
    fields: [
      'irc_antecedents_familiaux_renaux', 'irc_connue_avant_dialyse',
      'irc_contexte_debut_dialyse', 'irc_duree_suivi_predialytique_mois',
      'irc_etiologie_principale', 'irc_etiologie_secondaire',
      'irc_maladie_renale_hereditaire', 'irc_niveau_comprehension_patient',
      'irc_preference_therapie_renale', 'irc_resultat_biopsie_renale',
      'irc_source_adressage', 'irc_statut_biopsie_renale',
    ],
  },
  {
    title: 'Données imagerie',
    description: 'Échographie rénale, échocardiographie, FEVG',
    fields: [
      'imagerie_autres_resultats', 'imagerie_echogenicite_renale',
      'imagerie_fevg_pct', 'imagerie_hydronephrose',
      'imagerie_hypertrophie_ventriculaire_gauche', 'imagerie_kystes_renaux',
      'imagerie_lithiase', 'imagerie_radiographie_thorax',
      'imagerie_taille_reins', 'imagerie_valvulopathie',
    ],
  },
  {
    title: 'Données qualité de dialyse',
    description: 'Indicateurs de qualité et observance',
    fields: [
      'qualite_hypotensions_intradialytiques_30j', 'qualite_observance_declaree_patient',
      'qualite_poids_sec_kg', 'qualite_prise_poids_interdialytique_kg',
      'qualite_seances_manquees_30j', 'qualite_seances_raccourcies_30j',
      'qualite_spktv', 'qualite_tas_postdialyse_mmhg', 'qualite_tas_predialyse_mmhg',
      'qualite_taux_ultrafiltration_ml_kg_h', 'qualite_urr_pct',
    ],
  },
  {
    title: 'Comorbidités',
    description: 'Diabète, autres comorbidités, expositions toxiques',
    fields: [
      'comorbidite_antecedents_medicaments_nephrotoxiques', 'comorbidite_autre',
      'comorbidite_exposition_toxique', 'comorbidite_liste',
      'comorbidite_statut_diabete',
    ],
  },
  {
    title: 'Données complications',
    description: 'Hospitalisations et complications',
    fields: [
      'complication_autres_notes', 'complication_changement_modalite_dialyse',
      'complication_date_premier_evenement', 'complication_jours_hospitalisation',
      'complication_liste', 'complication_motifs_hospitalisation',
      'complication_nombre_hospitalisations',
    ],
  },
  {
    title: 'Données devenir',
    description: 'Pronostic, décès, transplantation',
    fields: [
      'devenir_categorie_pronostique', 'devenir_cause_deces',
      'devenir_date_deces', 'devenir_date_dernier_suivi',
      'devenir_date_transplantation', 'devenir_delai_deces_jours',
      'devenir_notes', 'devenir_qualite_vie', 'devenir_statut',
    ],
  },
  {
    title: 'Traitement et éducation',
    description: 'Médicaments et éducation thérapeutique',
    fields: [
      'education_complications', 'education_connaissance_pratique_dialyse',
      'education_dietetique', 'education_soins_acces_vasculaire',
      'education_surveillance_poids_fluides', 'education_traitements_associes',
      'traitement_autres_notes', 'traitement_medicaments_renaux_actuels',
      'immunologie_transfusion_immunisation',
    ],
  },
];

const SECTION_FIELD_PREFIXES = [
  'demographie_', 'irc_', 'comorbidite_', 'presentation_',
  'biologie_', 'imagerie_', 'dialyse_', 'qualite_',
  'complication_', 'traitement_', 'devenir_', 'education_',
];

const CORE_VARIABLE_KEYS = [
  'id_patient', 'id_enregistrement_source', 'id_site', 'statut_inclusion',
  'statut_consentement', 'utilisateur_saisie', 'derniere_mise_a_jour',
  'date_evaluation_initiale', 'nom', 'prenom', 'age', 'sexe',
  'maladie', 'telephone', 'adresse', 'date_naissance', 'date_admission',
];

// ── Composant carte module ────────────────────────────────────────────────────

function ModuleCard({ title, description, children }) {
  return (
    <Card elevation={0} sx={SURFACE_CARD_SX}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" fontWeight={900} sx={{ mb: 0.5, letterSpacing: '-.02em', color: '#15213d' }}>
          {title}
        </Typography>
        {description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 720 }}>
            {description}
          </Typography>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

// KPI Card amélioré - Taille réduite, design moderne
function KpiCard({ title, description, value, valueColor, icon: Icon }) {
  return (
    <Card
      elevation={0}
      sx={{
        ...SURFACE_CARD_SX,
        minHeight: 130,
        position: 'relative',
        overflow: 'hidden',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 24px 60px rgba(158,61,106,.18)',
        },
        '&::before': {
          content: '""',
          position: 'absolute',
          inset: '0 0 auto 0',
          height: 3,
          background: 'linear-gradient(90deg, rgba(61,90,138,.85), rgba(201,123,153,.8))',
        },
        '&::after': {
          content: '""',
          position: 'absolute',
          top: -35,
          right: -35,
          width: 100,
          height: 100,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(201,123,153,.08), transparent 70%)',
          pointerEvents: 'none',
        },
      }}
    >
      <CardContent sx={{ p: 2, position: 'relative', zIndex: 1 }}>
        <Stack spacing={0.5}>
          <Typography variant="overline" fontWeight={700} sx={{ color: '#62708b', letterSpacing: '0.05em', fontSize: '0.7rem' }}>
            {title}
          </Typography>
          <Typography variant="h4" fontWeight={900} sx={{ color: valueColor || '#1f6c8a', lineHeight: 1.1 }}>
            {value}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', lineHeight: 1.4 }}>
            {description}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}

// ── Composant principal ───────────────────────────────────────────────────────

function ModelAI() {
  const { user } = useContext(AuthContext);
  const { language } = useLanguage();
  const isEnglish = language === 'en';
  const moduleTabs = isEnglish
    ? ['Dashboard', 'Patient selection', 'Run prediction', 'Results']
    : ['Tableau de bord', 'Sélection patient', 'Lancer prédiction', 'Résultats'];
  const moduleDescription = isEnglish
    ? [
        'Overview of the service with indicators and high-priority patient alerts.',
        'Fast patient search, filtered by service and status.',
        '4 steps: prediction type -> variable selection -> model choice -> execution.',
        'Displays the score, risk level, and variable-level explainability.',
      ]
    : [
        'Vue globale du service avec indicateurs et alertes patients prioritaires.',
        'Recherche rapide de patient, filtres par service et statut.',
        '4 étapes : type de prédiction → sélection des variables → choix du modèle → exécution.',
        'Affichage du score, du niveau de risque et de l\'interprétabilité par variable.',
      ];

  // Navigation
  const [activeModule, setActiveModule] = useState(0);

  // Patients
  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [pendingImportedPatientIds, setPendingImportedPatientIds] = useState(new Set());
  const [patientCriteria, setPatientCriteria] = useState({ search: '', id: '', sexe: '' });
  const [selectedPatientId, setSelectedPatientId] = useState(null);

  // Prédiction — configuration
  const [selectedPredictionType, setSelectedPredictionType] = useState('mortalite');
  const [selectedModel, setSelectedModel] = useState('random_forest');
  const [modelMode, setModelMode] = useState('auto');
  const [selectedVariableKeys, setSelectedVariableKeys] = useState(new Set());
  const [variableSearch, setVariableSearch] = useState('');

  // Prédiction — résultats
  const [predictionScore, setPredictionScore] = useState(null);
  const [riskLevel, setRiskLevel] = useState('');
  const [recommendation, setRecommendation] = useState('');
  const [predictionFactors, setPredictionFactors] = useState([]);
  const [predictionInput, setPredictionInput] = useState({});
  const [doiRiskScore, setDoiRiskScore] = useState(null);
  const [doiRiskCategory, setDoiRiskCategory] = useState('');
  const [selectedDataRiskScore, setSelectedDataRiskScore] = useState(null);
  const [selectedDataRiskCategory, setSelectedDataRiskCategory] = useState('');
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState('');
  const [missingVariables, setMissingVariables] = useState([]);

  // Métriques modèles
  const [modelMetrics, setModelMetrics] = useState({});
  const [xgboostAvailable, setXgboostAvailable] = useState(false);

  // Entraînement
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [trainingResult, setTrainingResult] = useState(null);
  const [trainingError, setTrainingError] = useState('');

  // ── Helpers ────────────────────────────────────────────────────────────────

  const roleName = isEnglish
    ? (user?.role === 'professeur' ? 'Professor'
      : user?.role === 'chef_service' ? 'Service head'
        : user?.role === 'super_admin' ? 'Administrator'
          : 'User')
    : (user?.role === 'professeur' ? 'Professeur'
      : user?.role === 'chef_service' ? 'Chef de service'
        : user?.role === 'super_admin' ? 'Administrateur'
          : 'Utilisateur');

  const formatVariableLabel = useCallback((key) => {
    if (VARIABLE_LABELS[key]) return VARIABLE_LABELS[key];
    return key.replace(/_/g, ' ').replace(/\b[a-z]/g, (m) => m.toUpperCase());
  }, []);

  // ── Patients dérivés ───────────────────────────────────────────────────────

  const selectablePatients = useMemo(
    () => patients.filter((p) => !pendingImportedPatientIds.has(p.id)),
    [patients, pendingImportedPatientIds],
  );

  const validatedPatients = useMemo(
    () => selectablePatients.filter((p) => {
      const st = String(p.statut_inclusion || '').toLowerCase();
      return ['valide', 'validé', 'valides', 'approved', 'validated'].includes(st);
    }),
    [selectablePatients],
  );

  const isHighRiskPatient = useCallback((patient) => {
    const n = (v) => String(v || '').trim().toLowerCase();
    return (
      ['oui', 'true', '1'].includes(n(patient.infection)) ||
      ['oui', 'true', '1'].includes(n(patient.hemorrhage)) ||
      ['oui', 'true', '1'].includes(n(patient.avf_created)) ||
      n(patient.statut_inclusion).includes('critique') ||
      n(patient.statut_inclusion).includes('haut risque')
    );
  }, []);

  const highRiskPatients = useMemo(
    () => validatedPatients.filter(isHighRiskPatient),
    [validatedPatients, isHighRiskPatient],
  );

  const recentPatientsCount = useMemo(() => {
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
    return validatedPatients.reduce((count, p) => {
      const d = new Date(p.date_admission || p.date_evaluation_initiale || '');
      return !Number.isNaN(d.getTime()) && d.getTime() >= cutoff ? count + 1 : count;
    }, 0);
  }, [validatedPatients]);

  const validationRate = useMemo(
    () => (patients.length ? Math.round((validatedPatients.length / patients.length) * 100) : 0),
    [patients.length, validatedPatients.length],
  );

  const filteredPatients = useMemo(() => {
    return selectablePatients.filter((p) => {
      const fullName = `${p.nom || ''} ${p.prenom || ''}`.toLowerCase();
      const search = patientCriteria.search.trim().toLowerCase();
      const sex = (p.sexe || p.sex || '').toLowerCase();
      return (
        (!search ||
          fullName.includes(search) ||
          String(p.id || '').includes(search) ||
          String(p.id_patient || '').includes(search) ||
          String(p.id_enregistrement_source || '').includes(search)) &&
        (!patientCriteria.id ||
          String(p.id).includes(patientCriteria.id) ||
          String(p.id_patient || '').includes(patientCriteria.id) ||
          String(p.id_enregistrement_source || '').includes(patientCriteria.id)) &&
        (!patientCriteria.sexe || sex === patientCriteria.sexe.toLowerCase())
      );
    });
  }, [selectablePatients, patientCriteria]);

  const displayPatients = useMemo(() => {
    const noSearch = !patientCriteria.search && !patientCriteria.id && !patientCriteria.sexe;
    return noSearch ? selectablePatients : filteredPatients;
  }, [selectablePatients, filteredPatients, patientCriteria]);

  const selectedPatient = useMemo(
    () => patients.find((p) => String(p.id) === String(selectedPatientId)) || null,
    [patients, selectedPatientId],
  );

  // ── Variables disponibles selon les données patients ──────────────────────

  const availableVariableKeys = useMemo(() => {
    const keys = new Set();
    const addKey = (key) => {
      if (!key || ['id', 'created_at', 'updated_at', 'extra_data'].includes(key)) return;
      const isSection = SECTION_FIELD_PREFIXES.some((p) => key.startsWith(p));
      if (isSection || CORE_VARIABLE_KEYS.includes(key)) keys.add(key);
    };
    patients.forEach((patient) => {
      Object.keys(patient || {}).forEach(addKey);
      if (patient.extra_data && typeof patient.extra_data === 'object') {
        Object.keys(patient.extra_data).forEach(addKey);
      }
      SECTION_FIELD_PREFIXES.forEach((prefix) => {
        const sectionKey = `${prefix.replace(/_$/, '')}_data`;
        if (patient[sectionKey] && typeof patient[sectionKey] === 'object') {
          Object.keys(patient[sectionKey]).forEach(addKey);
        }
      });
    });
    return new Set(keys);
  }, [patients]);

  const availableVariableKeysSet = useMemo(
    () => new Set(availableVariableKeys),
    [availableVariableKeys],
  );

  // ── Valeur d'un champ patient ──────────────────────────────────────────────

  const getPatientFieldValue = useCallback((patient, fieldKey) => {
    if (!patient) return '';
    if (patient[fieldKey] !== undefined && patient[fieldKey] !== null && patient[fieldKey] !== '') {
      return String(patient[fieldKey]);
    }
    if (patient.extra_data && typeof patient.extra_data === 'object' && patient.extra_data[fieldKey] !== undefined) {
      return String(patient.extra_data[fieldKey]);
    }
    for (const prefix of SECTION_FIELD_PREFIXES) {
      const sectionKey = `${prefix.replace(/_$/, '')}_data`;
      if (patient[sectionKey] && typeof patient[sectionKey] === 'object' && patient[sectionKey][fieldKey] !== undefined) {
        return String(patient[sectionKey][fieldKey]);
      }
    }
    return '';
  }, []);

  // ── Filtrage variable search ───────────────────────────────────────────────

  const filteredVariableGroups = useMemo(() => {
    if (!variableSearch) return VARIABLE_GROUPS;
    return VARIABLE_GROUPS
      .map((section) => ({
        ...section,
        fields: section.fields.filter((key) =>
          (VARIABLE_LABELS[key] || key).toLowerCase().includes(variableSearch.toLowerCase()),
        ),
      }))
      .filter((section) => section.fields.length > 0);
  }, [variableSearch]);

  // ── Modèle recommandé ──────────────────────────────────────────────────────

  const recommendedModels = useMemo(
    () => (MODEL_RECOMMENDATIONS[selectedPredictionType] || ['random_forest']).filter(
      (key) => key !== 'xgboost' || xgboostAvailable,
    ),
    [selectedPredictionType, xgboostAvailable],
  );

  const availableModelOptions = useMemo(
    () => MODEL_OPTIONS.filter((m) => m.value !== 'xgboost' || xgboostAvailable),
    [xgboostAvailable],
  );

  useEffect(() => {
    if (modelMode === 'auto') {
      setSelectedModel(recommendedModels[0]);
    }
  }, [modelMode, recommendedModels]);

  // ── Chargement initial des patients ───────────────────────────────────────

  useEffect(() => {
    const loadPatients = async () => {
      setLoadingPatients(true);
      try {
        const response = await api.get('patients/');
        const list = Array.isArray(response.data) ? response.data : response.data.results || [];
        setPatients(list);
      } catch (error) {
        console.error('Chargement patients', error);
      } finally {
        setLoadingPatients(false);
      }
    };

    const loadPendingIds = () => {
      try {
        const saved = localStorage.getItem('patients_insert_validation_status');
        const statusData = saved ? JSON.parse(saved) : null;
        if (statusData?.status === 'pending' && Array.isArray(statusData.pendingIds)) {
          setPendingImportedPatientIds(new Set(statusData.pendingIds));
        } else {
          setPendingImportedPatientIds(new Set());
        }
      } catch {
        setPendingImportedPatientIds(new Set());
      }
    };

    loadPatients();
    loadPendingIds();

    window.addEventListener('patientsInsertValidationUpdated', loadPendingIds);
    window.addEventListener('storage', loadPendingIds);
    return () => {
      window.removeEventListener('patientsInsertValidationUpdated', loadPendingIds);
      window.removeEventListener('storage', loadPendingIds);
    };
  }, []);

  // ── Chargement métriques modèles ──────────────────────────────────────────

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        const response = await api.get(`predictions/metrics/?prediction_type=${selectedPredictionType}`);
        const models = response.data.models || {};
        setModelMetrics(models);
        setXgboostAvailable(Object.prototype.hasOwnProperty.call(models, 'xgboost'));
      } catch {
        setModelMetrics({});
        setXgboostAvailable(false);
      }
    };
    loadMetrics();
  }, [selectedPredictionType]);

  const mergedModelMetrics = useMemo(() => {
    const merged = { ...modelMetrics };
    if (trainingResult?.report && Array.isArray(trainingResult.report)) {
      trainingResult.report.forEach((item) => {
        const existing = merged[item.model] || {};
        const reportMetrics = item.metrics || {
          accuracy: item.accuracy,
          precision: item.precision,
          recall: item.recall,
          f1: item.f1,
          pr_auc: item.pr_auc,
          auc: item.auc,
        };
        merged[item.model] = {
          trained: true,
          feature_count: existing.feature_count ?? item.feature_keys?.length ?? existing.feature_count,
          metrics: { ...existing.metrics, ...reportMetrics },
        };
      });
    }
    return merged;
  }, [modelMetrics, trainingResult]);

  useEffect(() => {
    if (!availableModelOptions.some((m) => m.value === selectedModel)) {
      setSelectedModel(availableModelOptions[0]?.value || 'random_forest');
    }
  }, [availableModelOptions, selectedModel]);

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleSearchChange = (field, value) => {
    setPatientCriteria((prev) => ({ ...prev, [field]: value }));
  };

  const handleSelectPatient = (patient) => {
    setSelectedPatientId(patient.id);
    setSelectedVariableKeys(new Set());
    setPredictionError('');
    setMissingVariables([]);
    setDoiRiskScore(null);
    setDoiRiskCategory('');
    setActiveModule(2);
  };

  const handleToggleVariable = (fieldKey) => {
    setSelectedVariableKeys((prev) => {
      const updated = new Set(prev);
      if (updated.has(fieldKey)) {
        updated.delete(fieldKey);
      } else {
        updated.add(fieldKey);
      }
      return updated;
    });
  };

  const handleSelectAllVariables = () => {
    if (!selectedPatient) return;
    setSelectedVariableKeys((prev) => {
      const updated = new Set(prev);
      filteredVariableGroups.forEach((section) => {
        section.fields.forEach((fieldKey) => {
          const rawValue = getPatientFieldValue(selectedPatient, fieldKey);
          if (rawValue !== '' && availableVariableKeysSet.has(fieldKey)) {
            updated.add(fieldKey);
          }
        });
      });
      return updated;
    });
  };

  const handleDeselectAllVariables = () => {
    setSelectedVariableKeys(new Set());
  };

  // ── Validation avant prédiction ────────────────────────────────────────────

  const validatePredictionInput = useCallback(() => {
    if (!selectedPatient) return false;
    if (selectedVariableKeys.size === 0) return false;
    for (const key of selectedVariableKeys) {
      const val = getPatientFieldValue(selectedPatient, key);
      if (val === null || val === undefined || val === '') return false;
    }
    return true;
  }, [selectedPatient, selectedVariableKeys, getPatientFieldValue]);

  // ── Construction du payload de prédiction ─────────────────────────────────

  const buildPredictionPayload = useCallback(() => {
    if (!selectedPatient) return {};
    const payload = {};
    for (const fieldKey of selectedVariableKeys) {
      const rawValue = getPatientFieldValue(selectedPatient, fieldKey);
      if (rawValue === '') continue;

      const targetKey =
        fieldKey === 'demographie_age_ans' ? 'age'
          : fieldKey === 'demographie_sexe' ? 'sexe'
            : fieldKey;

      const numeric = Number(String(rawValue).replace(',', '.'));
      payload[targetKey] = Number.isNaN(numeric) ? rawValue : numeric;
    }
    return payload;
  }, [selectedPatient, selectedVariableKeys, getPatientFieldValue]);

  // ── Lancer la prédiction via l'API backend ─────────────────────────────────

  const handleRunPrediction = async () => {
    setPredictionError('');
    setMissingVariables([]);

    if (!selectedPatient) {
      setPredictionError('Veuillez d\'abord sélectionner un patient.');
      return;
    }

    if (selectedVariableKeys.size === 0) {
      setPredictionError('Veuillez sélectionner au moins une variable pour la prédiction.');
      return;
    }

    const missing = [...selectedVariableKeys].filter(
      (key) => !getPatientFieldValue(selectedPatient, key),
    );
    if (missing.length > 0) {
      setMissingVariables(missing);
      setPredictionError(
        `${missing.length} variable(s) sélectionnée(s) n\'ont pas de valeur pour ce patient : ${missing.map(formatVariableLabel).join(', ')}.`,
      );
      return;
    }

    const payload = buildPredictionPayload();
    const modelParam = modelMode === 'auto' ? 'auto' : selectedModel;

    setPredictionLoading(true);
    setDoiRiskScore(null);
    setDoiRiskCategory('');
    setSelectedDataRiskScore(null);
    setSelectedDataRiskCategory('');

    try {
      const response = await api.post('predictions/predict/', {
        prediction_type: selectedPredictionType,
        model: modelParam,
        features: payload,
      });

      const data = response.data;

      const normalizeRiskLevel = (level) => {
        if (!level) return '';
        const map = {
          high: 'Élevé', haut: 'Élevé', eleve: 'Élevé', élevé: 'Élevé',
          moderate: 'Modéré', medium: 'Modéré', moyen: 'Modéré', modere: 'Modéré', modéré: 'Modéré',
          low: 'Faible', bas: 'Faible', faible: 'Faible',
        };
        return map[String(level).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')] || level;
      };

      const normalizedLevel = normalizeRiskLevel(data.risk_level);

      setPredictionInput(payload);
      setPredictionScore(data.score ?? 0);
      setRiskLevel(normalizedLevel);
      setRecommendation(data.recommendation || buildLocalRecommendation(normalizedLevel));
      setPredictionFactors(data.factors || []);
      setDoiRiskScore(data.doietal_risk_score ?? null);
      setDoiRiskCategory(data.doietal_risk_category || '');
      setSelectedDataRiskScore(data.selected_data_risk_score ?? null);
      setSelectedDataRiskCategory(data.selected_data_risk_category || '');
      setActiveModule(3);
    } catch (error) {
      const backendError = error.response?.data;
      const backendMessage =
        backendError?.error ||
        backendError?.detail ||
        (typeof backendError === 'string' ? backendError : (backendError ? JSON.stringify(backendError) : null));
      setPredictionError(
        error.response?.status === 401
          ? 'Authentification requise. Veuillez vous reconnecter.'
          : backendMessage || 'Erreur lors de la communication avec le serveur de prédiction.',
      );
    } finally {
      setPredictionLoading(false);
    }
  };

  // ── Entraînement du modèle ─────────────────────────────────────────────────

  const handleTrainModel = async () => {
    setTrainingLoading(true);
    setTrainingResult(null);
    setTrainingError('');

    try {
      const response = await api.post('predictions/train/', {
        prediction_type: selectedPredictionType,
        ...(selectedVariableKeys.size > 0 && {
          feature_keys: [...selectedVariableKeys],
        }),
      });
      const trainingData = response.data;
      setTrainingResult(trainingData);
      if (trainingData?.report) {
        const reportMetrics = trainingData.report.reduce((acc, item) => {
          acc[item.model] = {
            trained: true,
            metrics: item,
            feature_count: item.feature_keys?.length ?? null,
          };
          return acc;
        }, {});
        setModelMetrics((prev) => ({
          ...prev,
          ...reportMetrics,
        }));
      }
      if (trainingData?.prediction_type) {
        try {
          const metricsResponse = await api.get(`predictions/metrics/?prediction_type=${trainingData.prediction_type}`);
          setModelMetrics((prev) => ({
            ...prev,
            ...(metricsResponse.data.models || {}),
          }));
        } catch {
          // Conservation des métriques issues du rapport
        }
      }
    } catch (error) {
      const backendError = error.response?.data;
      const backendMessage =
        backendError?.error ||
        backendError?.detail ||
        (typeof backendError === 'string' ? backendError : (backendError ? JSON.stringify(backendError) : null));
      setTrainingError(
        error.response?.status === 401
          ? 'Authentification requise. Veuillez vous reconnecter.'
          : backendMessage || 'Erreur lors de l\'entraînement du modèle.',
      );
    } finally {
      setTrainingLoading(false);
    }
  };

  // ── Recommandation locale ──────────────────────────────────────────────────

  const buildLocalRecommendation = (level) => {
    if (level === 'Élevé') {
      return 'Risque élevé détecté : surveillance intensive recommandée, adaptation thérapeutique urgente et consultation spécialisée.';
    }
    if (level === 'Modéré') {
      return 'Risque modéré : suivi renforcé, optimisation des paramètres cliniques et réévaluation à court terme.';
    }
    return 'Risque faible : maintien du suivi standard avec contrôle périodique.';
  };

  // ── Rendu ─────────────────────────────────────────────────────────────────

  return (
    <Box
      sx={{
        minHeight: '100vh',
        py: 2,
        position: 'relative',
        overflow: 'hidden',
        background: [
          'radial-gradient(circle at top left, rgba(168,207,238,.42), transparent 30%)',
          'radial-gradient(circle at 85% 10%, rgba(158,61,106,.12), transparent 26%)',
          'radial-gradient(circle at 70% 92%, rgba(61,90,138,.10), transparent 24%)',
          'linear-gradient(160deg,#f5eef4 0%,#edf4fb 46%,#f7f4ff 100%)',
        ].join(', '),
        fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
        '&::before': {
          content: '""',
          position: 'absolute',
          inset: '12% auto auto -8%',
          width: 320,
          height: 320,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,255,255,.65), rgba(255,255,255,0) 68%)',
          filter: 'blur(8px)',
          pointerEvents: 'none',
        },
        '&::after': {
          content: '""',
          position: 'absolute',
          inset: 'auto -6% -10% auto',
          width: 420,
          height: 420,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,255,255,.52), rgba(255,255,255,0) 70%)',
          filter: 'blur(12px)',
          pointerEvents: 'none',
        },
      }}
    >
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');`}</style>
      <Box sx={{ width: '100%', position: 'relative', zIndex: 1 }}>
        <AppSidebar />

        <Box sx={{ minWidth: 0, pl: { xs: 1, md: '112px' }, pr: { xs: 1.5, md: 3 }, pb: 2 }}>
          <Box sx={{ width: '100%', maxWidth: 1680, mx: 'auto' }}>
            <Stack spacing={3}>
              {/* En-tête */}
              <Card elevation={0} sx={{
                ...SURFACE_CARD_SX,
                borderRadius: '30px',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  inset: '0 0 auto 0',
                  height: 5,
                  background: 'linear-gradient(90deg,#a8cfee,#3d5a8a,#9e3d6a,#e8c4d4)',
                },
                '&::after': {
                  content: '""',
                  position: 'absolute',
                  top: -60,
                  right: -60,
                  width: 190,
                  height: 190,
                  borderRadius: '50%',
                  background: 'radial-gradient(circle, rgba(158,61,106,.10), transparent 68%)',
                  pointerEvents: 'none',
                },
              }}>
                <CardContent sx={{ p: 3.5, position: 'relative' }}>
                  <Box
                    component="img"
                    src="/images/chatgpt-image-2026-04-23.png"
                    alt="decor"
                    sx={{
                      position: 'absolute',
                      left: 16,
                      top: 12,
                      width: 152,
                      maxWidth: '36%',
                      opacity: 0.16,
                      transform: 'translateZ(0)',
                      zIndex: 0,
                      pointerEvents: 'none',
                      filter: 'drop-shadow(0 8px 20px rgba(158,61,106,0.10)) saturate(1.05) contrast(1.04)',
                    }}
                  />
                  <Stack direction={{ xs: 'column', lg: 'row' }} justifyContent="space-between" spacing={2.5} sx={{ position: 'relative', zIndex: 1 }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h5" sx={{ fontWeight: 900, color: '#1e2d5a', letterSpacing: '-.02em', fontFamily: 'inherit' }}>
                        Des modèles de Machine Learning
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 0.5, color: '#3d5a8a', fontFamily: 'inherit' }}>
                        Aide à la décision clinique — Pathologies rénales
                      </Typography>
                    </Box>
                    <Chip
                      label={roleName}
                      sx={{
                        alignSelf: { xs: 'flex-start', lg: 'flex-end' },
                        fontWeight: 700,
                        background: `linear-gradient(135deg, ${ROSE_ACCENT.mid}, #3d5a8a)`,
                        color: '#fff',
                      }}
                    />
                  </Stack>
                </CardContent>
              </Card>

              {/* Navigation */}
              <Card elevation={0} sx={SURFACE_CARD_SX}>
                <CardContent sx={{ p: 2.5 }}>
                  <Tabs
                    value={activeModule}
                    onChange={(_, v) => setActiveModule(v)}
                    variant="scrollable"
                    allowScrollButtonsMobile
                    sx={{
                      minHeight: 42,
                      '& .MuiTabs-indicator': {
                        height: 3,
                        borderRadius: 999,
                        background: `linear-gradient(90deg, ${ROSE_ACCENT.mid}, #3d5a8a)`,
                      },
                      '& .MuiTab-root': {
                        minHeight: 42,
                        textTransform: 'none',
                        fontWeight: 700,
                        color: '#62708b',
                        px: 1.5,
                        borderRadius: 999,
                        transition: 'all 0.2s ease',
                      },
                      '& .MuiTab-root.Mui-selected': {
                        color: '#1e2d5a',
                        background: 'linear-gradient(135deg, rgba(201,123,153,0.16), rgba(61,90,138,0.10))',
                      },
                    }}
                  >
                    {moduleTabs.map((label, index) => (
                      <Tab key={label} value={index} label={label} />
                    ))}
                  </Tabs>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2.25 }}>
                    {moduleDescription[activeModule]}
                  </Typography>
                </CardContent>
              </Card>

              {/* ── TABLEAU DE BORD ── */}
              {activeModule === 0 && (
                <Grid container spacing={2}>
                  {/* KPI Cards — Réduites */}
                  <Grid item xs={12} sm={6} lg={2.4}>
                    <KpiCard
                      title={isEnglish ? 'Tracked patients' : 'Patients suivis'}
                      description={isEnglish ? 'Base total' : 'Total base'}
                      value={patients.length}
                      valueColor="#1f6c8a"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} lg={2.4}>
                    <KpiCard
                      title={isEnglish ? 'High risk' : 'Haut risque'}
                      description={isEnglish ? 'Alerts' : 'Alertes'}
                      value={highRiskPatients.length}
                      valueColor="#D4433D"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} lg={2.4}>
                    <KpiCard
                      title={isEnglish ? 'Recent' : 'Récents'}
                      description={isEnglish ? 'Last 30 days' : '30 derniers jours'}
                      value={recentPatientsCount}
                      valueColor="#1f6c8a"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} lg={2.4}>
                    <KpiCard
                      title={isEnglish ? 'Validated' : 'Validés'}
                      description={isEnglish ? '% of total' : '% du total'}
                      value={`${validationRate}%`}
                      valueColor="#2B7A6B"
                    />
                  </Grid>

                  {/* Espace à droite - Panel latéral */}
                  <Grid item xs={12} lg={2}>
                    <Card elevation={0} sx={{...SURFACE_CARD_SX, minHeight: 130, p: 2}}>
                      <Stack spacing={1}>
                        <Typography variant="overline" fontWeight={700} sx={{ color: '#62708b', letterSpacing: '0.05em', fontSize: '0.7rem' }}>
                          {isEnglish ? 'Status' : 'Statut'}
                        </Typography>
                        <Chip label={isEnglish ? 'Active' : 'Actif'} color="success" size="small" />
                        <Typography variant="caption" color="text.secondary">{isEnglish ? 'System online' : 'Système en ligne'}</Typography>
                      </Stack>
                    </Card>
                  </Grid>

                  {/* Alertes haut risque */}
                  <Grid item xs={12}>
                    <ModuleCard title={isEnglish ? 'High risk alerts' : 'Alertes haut risque'} description={isEnglish ? 'Open a record in one click.' : 'Lancer un dossier en un clic.'}>
                      <Stack spacing={2}>
                        {highRiskPatients.length ? (
                          highRiskPatients.slice(0, 3).map((patient) => {
                            const reason = [];
                            if (['oui', 'true', '1'].includes(String(patient.infection || '').toLowerCase())) reason.push(isEnglish ? 'Infection' : 'Infection');
                            if (['oui', 'true', '1'].includes(String(patient.hemorrhage || '').toLowerCase())) reason.push(isEnglish ? 'Hemorrhage' : 'Hémorragie');
                            if (['oui', 'true', '1'].includes(String(patient.avf_created || '').toLowerCase())) reason.push('AVF');
                            if (!reason.length) reason.push(isEnglish ? 'Critical status' : 'Statut critique');
                            return (
                              <Button key={patient.id} variant="outlined" fullWidth onClick={() => handleSelectPatient(patient)}>
                                {patient.nom || 'Patient'} {patient.prenom || ''} — {reason.join(' / ')}
                              </Button>
                            );
                          })
                        ) : (
                          <Typography variant="body2" color="text.secondary">{isEnglish ? 'No high-risk alert detected.' : 'Aucune alerte haut risque détectée.'}</Typography>
                        )}
                      </Stack>
                    </ModuleCard>
                  </Grid>
                </Grid>
              )}

              {/* ── SÉLECTION PATIENT ── */}
              {activeModule === 1 && (
                <Grid container spacing={3}>
                  <Grid item xs={12} md={4}>
                    <ModuleCard title={isEnglish ? 'Patient search' : 'Recherche du patient'} description={isEnglish ? 'Search by last name, first name, or ID.' : 'Recherchez par nom, prénom ou identifiant.'}>
                      <Stack spacing={2}>
                        <TextField label={isEnglish ? 'Last name or first name' : 'Nom ou prénom'} value={patientCriteria.search} onChange={(e) => handleSearchChange('search', e.target.value)} fullWidth size="small" />
                        <TextField label={isEnglish ? 'Patient ID' : 'ID patient'} value={patientCriteria.id} onChange={(e) => handleSearchChange('id', e.target.value)} fullWidth size="small" />
                        <TextField select label={isEnglish ? 'Sex' : 'Sexe'} value={patientCriteria.sexe} onChange={(e) => handleSearchChange('sexe', e.target.value)} fullWidth size="small">
                          <MenuItem value="">{isEnglish ? 'All' : 'Tous'}</MenuItem>
                          <MenuItem value="M">{isEnglish ? 'Male' : 'Homme'}</MenuItem>
                          <MenuItem value="F">{isEnglish ? 'Female' : 'Femme'}</MenuItem>
                          <MenuItem value="O">{isEnglish ? 'Other' : 'Autre'}</MenuItem>
                        </TextField>
                      </Stack>
                    </ModuleCard>
                  </Grid>
                  <Grid item xs={12} md={8}>
                    <ModuleCard title={isEnglish ? 'Search results' : 'Résultats de recherche'} description={isEnglish ? 'Click a patient to open their profile.' : 'Cliquez sur un patient pour accéder à sa fiche.'}>
                      {loadingPatients ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                          <CircularProgress size={32} />
                        </Box>
                      ) : displayPatients.length ? (
                        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
                          <Table size="small">
                            <TableHead sx={{ backgroundColor: 'rgba(226,237,244,0.9)' }}>
                              <TableRow>
                                <TableCell sx={{ fontWeight: 700 }}>{isEnglish ? 'Patient ID' : 'ID patient'}</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>{isEnglish ? 'Last name' : 'Nom'}</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>{isEnglish ? 'First name' : 'Prénom'}</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>{isEnglish ? 'Sex' : 'Sexe'}</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>{isEnglish ? 'Site' : 'Site'}</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>{isEnglish ? 'Age' : 'Âge'}</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>{isEnglish ? 'Status' : 'Statut'}</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {displayPatients.map((patient) => (
                                <TableRow
                                  key={patient.id}
                                  hover
                                  sx={{ cursor: 'pointer', bgcolor: String(patient.id) === String(selectedPatientId) ? 'rgba(57,151,118,0.08)' : 'inherit' }}
                                  onClick={() => handleSelectPatient(patient)}
                                >
                                  <TableCell>{patient.id_patient || '-'}</TableCell>
                                  <TableCell>{patient.nom || '-'}</TableCell>
                                  <TableCell>{patient.prenom || '-'}</TableCell>
                                  <TableCell>{patient.sexe || patient.sex || '-'}</TableCell>
                                  <TableCell>{patient.id_site || '-'}</TableCell>
                                  <TableCell>{patient.age || patient.demographie_age_ans || '-'}</TableCell>
                                  <TableCell>{patient.statut_inclusion || '-'}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      ) : (
                        <Typography variant="body2" color="text.secondary">{isEnglish ? 'No patient found.' : 'Aucun patient trouvé.'}</Typography>
                      )}
                    </ModuleCard>
                  </Grid>
                </Grid>
              )}

              {/* ── LANCER PRÉDICTION ── */}
              {activeModule === 2 && (
                <Grid container spacing={3}>
                  {/* Type de prédiction */}
                  <Grid item xs={12}>
                    <Paper variant="outlined" sx={{ ...PANEL_SX, p: 3 }}>
                      <Typography variant="h6" fontWeight={700}>{isEnglish ? 'Step 1 - Prediction type' : 'Étape 1 — Type de prédiction'}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
                        {isEnglish ? 'Choose the prediction type to run.' : 'Choisissez le type de prédiction à effectuer.'}
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {PREDICTION_TYPES.map((type) => (
                          <Tooltip key={type.value} title={type.detail} arrow>
                            <Button
                              variant={selectedPredictionType === type.value ? 'contained' : 'outlined'}
                              color={selectedPredictionType === type.value ? 'success' : 'inherit'}
                              onClick={() => setSelectedPredictionType(type.value)}
                              sx={{ textTransform: 'none' }}
                            >
                              {type.label}
                            </Button>
                          </Tooltip>
                        ))}
                      </Box>
                    </Paper>
                  </Grid>

                  {/* Fiche patient + sélection variables */}
                  <Grid item xs={12} md={8}>
                    <Paper variant="outlined" sx={{ ...PANEL_SX, p: 3, minHeight: 680 }}>
                      <Typography variant="subtitle1" fontWeight={700}>{isEnglish ? 'Step 2 - Variable selection' : 'Étape 2 — Sélection des variables'}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {isEnglish ? 'Check the patient variables you want to use for prediction. Only variables with a value are enabled.' : 'Cochez les variables disponibles du patient à utiliser pour la prédiction. Seules les variables avec une valeur sont activées.'}
                      </Typography>

                      {selectedPatient ? (
                        <Stack spacing={2}>
                          {/* Identité patient */}
                          <Paper variant="outlined" sx={{ ...PANEL_SX, p: 2, bgcolor: 'rgba(255,255,255,.9)' }}>
                            <Stack direction="row" spacing={2} alignItems="center">
                              <Avatar sx={{ bgcolor: '#E1F5EE', color: '#0F6E56', fontWeight: 700, width: 48, height: 48 }}>
                                {selectedPatient.nom?.[0] || 'P'}
                              </Avatar>
                              <Box>
                                <Typography variant="subtitle1" fontWeight={700}>
                                  {selectedPatient.nom || ''} {selectedPatient.prenom || ''}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" display="block">
                                  ID : {selectedPatient.id_patient || selectedPatient.id || '-'} · Site : {selectedPatient.id_site || '-'}
                                </Typography>
                              </Box>
                            </Stack>
                            <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1.5 }}>
                              {selectedPatient.dialyse_modalite_actuelle && (
                                <Chip label={selectedPatient.dialyse_modalite_actuelle} size="small" sx={{ bgcolor: '#E1F5EE', color: '#0F6E56' }} />
                              )}
                              {selectedPatient.statut_inclusion && (
                                <Chip label={selectedPatient.statut_inclusion} size="small" sx={{ bgcolor: '#E6F1FB', color: '#185FA5' }} />
                              )}
                            </Stack>
                          </Paper>

                          <TextField
                            label={isEnglish ? 'Search a variable' : 'Rechercher une variable'}
                            size="small"
                            value={variableSearch}
                            onChange={(e) => setVariableSearch(e.target.value)}
                            fullWidth
                            sx={{ mb: 2 }}
                          />

                          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={handleSelectAllVariables}
                              disabled={!selectedPatient || filteredVariableGroups.every((section) => section.fields.length === 0)}
                            >
                              {isEnglish ? 'Select all' : 'Tout sélectionner'}
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={handleDeselectAllVariables}
                              disabled={selectedVariableKeys.size === 0}
                            >
                              {isEnglish ? 'Deselect all' : 'Tout désélectionner'}
                            </Button>
                          </Stack>

                          {filteredVariableGroups.map((section) => (
                            <Accordion key={section.title} disableGutters sx={{ ...PANEL_SX, boxShadow: 'none' }}>
                              <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2, py: 1 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                                  <Typography variant="subtitle2" fontWeight={700}>{section.title}</Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {section.fields.filter((k) => selectedVariableKeys.has(k)).length} sélectionné(s) / {section.fields.length}
                                  </Typography>
                                </Box>
                              </AccordionSummary>
                              <AccordionDetails sx={{ p: 2, pt: 1 }}>
                                <Grid container spacing={1}>
                                  {section.fields.map((fieldKey) => {
                                    const rawValue = getPatientFieldValue(selectedPatient, fieldKey);
                                    const hasValue = rawValue !== '';
                                    const isSelected = selectedVariableKeys.has(fieldKey);
                                    const isMissing = missingVariables.includes(fieldKey);
                                    return (
                                      <Grid key={fieldKey} item xs={12} sm={6}>
                                        <Box
                                          sx={{
                                            p: 0.5,
                                            borderRadius: 1,
                                            bgcolor: isMissing ? 'rgba(212,67,61,0.06)' : isSelected ? 'rgba(57,151,118,0.06)' : 'transparent',
                                            border: isMissing ? '1px solid rgba(212,67,61,0.3)' : isSelected ? '1px solid rgba(57,151,118,0.3)' : '1px solid transparent',
                                          }}
                                        >
                                          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                                            <Checkbox
                                              checked={isSelected}
                                              disabled={!hasValue}
                                              onChange={() => handleToggleVariable(fieldKey)}
                                              size="small"
                                              color={isMissing ? 'error' : 'success'}
                                              sx={{ pt: 0.5 }}
                                            />
                                            <Box>
                                              <Typography variant="body2" color={!hasValue ? 'text.disabled' : 'text.primary'}>
                                                {VARIABLE_LABELS[fieldKey] || formatVariableLabel(fieldKey)}
                                              </Typography>
                                              <Typography variant="caption" color={hasValue ? 'text.secondary' : 'text.disabled'}>
                                                {hasValue ? rawValue : '— non renseigné'}
                                              </Typography>
                                            </Box>
                                          </Box>
                                        </Box>
                                      </Grid>
                                    );
                                  })}
                                </Grid>
                              </AccordionDetails>
                            </Accordion>
                          ))}
                        </Stack>
                      ) : (
                        <Alert severity="info" sx={{ mt: 2 }}>
                          {isEnglish ? 'Select a patient in the "Patient selection" tab to display their profile and choose variables.' : 'Sélectionnez un patient dans l\'onglet "Sélection patient" pour afficher sa fiche et choisir les variables.'}
                        </Alert>
                      )}
                    </Paper>
                  </Grid>

                  {/* Panneau droit : variables sélectionnées + modèle + action */}
                  <Grid item xs={12} md={4}>
                    <Stack spacing={2}>
                      {/* Récapitulatif variables */}
                      <Paper variant="outlined" sx={{ ...PANEL_SX, p: 2.5 }}>
                        <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                          {isEnglish ? `Selected variables (${selectedVariableKeys.size})` : `Variables sélectionnées (${selectedVariableKeys.size})`}
                        </Typography>
                        {selectedVariableKeys.size ? (
                          <Stack spacing={0.5} sx={{ maxHeight: 220, overflowY: 'auto' }}>
                            {[...selectedVariableKeys].map((fieldKey) => (
                              <Paper key={fieldKey} variant="outlined" sx={{ ...PANEL_SX, p: 1 }}>
                                <Stack direction="row" alignItems="center" justifyContent="space-between">
                                  <Box sx={{ flex: 1, minWidth: 0 }}>
                                    <Typography variant="caption" fontWeight={700} noWrap>
                                      {VARIABLE_LABELS[fieldKey] || formatVariableLabel(fieldKey)}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" display="block" noWrap>
                                      {selectedPatient ? getPatientFieldValue(selectedPatient, fieldKey) : '—'}
                                    </Typography>
                                  </Box>
                                  <IconButton size="small" onClick={() => handleToggleVariable(fieldKey)} sx={{ ml: 0.5 }}>
                                    <Typography variant="caption">✕</Typography>
                                  </IconButton>
                                </Stack>
                              </Paper>
                            ))}
                          </Stack>
                        ) : (
                          <Typography variant="body2" color="text.secondary">{isEnglish ? 'No variable selected.' : 'Aucune variable sélectionnée.'}</Typography>
                        )}
                      </Paper>

                      {/* Choix du modèle */}
                      <Paper variant="outlined" sx={{ ...PANEL_SX, p: 2.5 }}>
                        <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
                          {isEnglish ? 'Step 3 - Model choice' : 'Étape 3 — Choix du modèle'}
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                          <Button
                            variant={modelMode === 'auto' ? 'contained' : 'outlined'}
                            color={modelMode === 'auto' ? 'success' : 'inherit'}
                            onClick={() => setModelMode('auto')}
                            size="small"
                            sx={{ textTransform: 'none', flex: 1 }}
                          >
                            {isEnglish ? 'Automatic' : 'Automatique'}
                          </Button>
                          <Button
                            variant={modelMode === 'manual' ? 'contained' : 'outlined'}
                            color={modelMode === 'manual' ? 'success' : 'inherit'}
                            onClick={() => setModelMode('manual')}
                            size="small"
                            sx={{ textTransform: 'none', flex: 1 }}
                          >
                            {isEnglish ? 'Manual' : 'Manuel'}
                          </Button>
                        </Stack>

                        {modelMode === 'manual' ? (
                          <TextField
                            select
                            label={isEnglish ? 'Model' : 'Modèle'}
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            fullWidth
                            size="small"
                          >
                            {availableModelOptions.map((m) => (
                              <MenuItem key={m.value} value={m.value}>
                                {m.label}
                              </MenuItem>
                            ))}
                          </TextField>
                        ) : (
                          <Box sx={{ p: 1.5, bgcolor: 'rgba(57,151,118,0.07)', borderRadius: 2, border: '1px solid rgba(57,151,118,0.26)' }}>
                            <Typography variant="caption" color="success.main" fontWeight={700}>{isEnglish ? 'Recommended' : 'Recommandé'}</Typography>
                            <Typography variant="subtitle2" fontWeight={800} sx={{ mt: 0.5 }}>
                              {MODEL_OPTIONS.find((m) => m.value === selectedModel)?.label || 'Random Forest'}
                            </Typography>
                          </Box>
                        )}
                      </Paper>

                      {/* Erreurs */}
                      {predictionError && (
                        <Alert severity="error" onClose={() => setPredictionError('')}>
                          {predictionError}
                        </Alert>
                      )}

                      {/* Bouton lancement */}
                      <Button
                        variant="contained"
                        color="success"
                        onClick={handleRunPrediction}
                        disabled={predictionLoading || !validatePredictionInput()}
                        fullWidth
                        sx={{ py: 1.8, fontWeight: 700, textTransform: 'none', borderRadius: 3 }}
                      >
                        {predictionLoading ? (
                          <Stack direction="row" spacing={1} alignItems="center">
                            <CircularProgress size={18} color="inherit" />
                            <span>{isEnglish ? 'Running...' : 'En cours...'}</span>
                          </Stack>
                        ) : (isEnglish ? 'Run' : 'Lancer')}
                      </Button>

                      {!selectedPatient && (
                        <Alert severity="warning">{isEnglish ? 'Select a patient first.' : "Sélectionnez un patient d'abord."}</Alert>
                      )}
                      {selectedPatient && selectedVariableKeys.size === 0 && (
                        <Alert severity="info">{isEnglish ? 'Select at least one variable.' : 'Cochez au moins une variable.'}</Alert>
                      )}
                    </Stack>
                  </Grid>
                </Grid>
              )}

              {/* ── RÉSULTATS ── */}
              {activeModule === 3 && (
                <Grid container spacing={3}>
                  <Grid item xs={12} md={5}>
                    <ModuleCard title={isEnglish ? 'Risk score' : 'Score de risque'} description={isEnglish ? 'Score computed by the ML model.' : 'Score calculé par le modèle ML.'}>
                      {predictionScore !== null ? (
                        <>
                          <Typography variant="h2" fontWeight={900}>
                            {typeof predictionScore === 'number' ? predictionScore.toFixed(1) : 0}%
                          </Typography>
                          <Typography variant="h6" fontWeight={700} sx={{ color: RISK_COLORS[riskLevel] || '#666', mt: 1 }}>
                            {riskLevel || (isEnglish ? 'Unknown' : 'Inconnu')}
                          </Typography>
                          <Box sx={{ mt: 2, width: '100%', height: 14, borderRadius: 999, background: '#E6F4F1' }}>
                            <Box
                              sx={{
                                width: `${Math.min(100, Math.max(0, predictionScore))}%`,
                                height: '100%',
                                borderRadius: 999,
                                background: RISK_COLORS[riskLevel] || '#ccc',
                                transition: 'width 0.5s ease',
                              }}
                            />
                          </Box>

                          <Stack direction="row" justifyContent="space-between" sx={{ mt: 0.5 }}>
                            <Typography variant="caption" color="#399776">{isEnglish ? 'Low (≤30%)' : 'Faible (≤30%)'}</Typography>
                            <Typography variant="caption" color="#E4A330">{isEnglish ? 'Moderate (31–70%)' : 'Modéré (31–70%)'}</Typography>
                            <Typography variant="caption" color="#D4433D">{isEnglish ? 'High (&gt;70%)' : 'Élevé (&gt;70%)'}</Typography>
                          </Stack>

                          {doiRiskScore != null && (
                            <Box sx={{ mt: 2 }}>
                              <Typography variant="caption" color="text.secondary" display="block">
                                {isEnglish ? 'DOI score' : 'Score Doi'} : {doiRiskScore}
                              </Typography>
                            </Box>
                          )}
                        </>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          {isEnglish ? 'No prediction available.' : 'Aucune prédiction disponible.'}
                        </Typography>
                      )}
                    </ModuleCard>
                  </Grid>

                  <Grid item xs={12} md={7}>
                    <ModuleCard title={isEnglish ? 'Interpretability' : 'Interprétabilité'} description={isEnglish ? 'Key factors in the decision.' : 'Facteurs déterminants dans la décision.'}>
                      {predictionFactors.length > 0 ? (
                        <Stack spacing={1.5}>
                          {predictionFactors.map((item, idx) => (
                            <Box key={`${item.label}-${idx}`}>
                              <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                                <Typography variant="body2">{VARIABLE_LABELS[item.label] || item.label}</Typography>
                                <Typography variant="body2" fontWeight={700}>{item.weight}%</Typography>
                              </Stack>
                              <LinearProgress
                                variant="determinate"
                                value={Math.min(100, item.weight)}
                                sx={{ height: 6, borderRadius: 3, bgcolor: 'rgba(0,0,0,0.06)' }}
                                color="success"
                              />
                            </Box>
                          ))}
                        </Stack>
                      ) : (
                          <Typography variant="body2" color="text.secondary">
                          {isEnglish ? 'No factor available.' : 'Aucun facteur disponible.'}
                        </Typography>
                      )}
                    </ModuleCard>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <ModuleCard title={isEnglish ? 'Used variables' : 'Variables utilisées'} description={isEnglish ? 'Variables sent to the model.' : 'Variables envoyées au modèle.'}>
                      {Object.keys(predictionInput).length > 0 ? (
                        <Stack spacing={0.5} sx={{ maxHeight: 300, overflowY: 'auto' }}>
                          {Object.entries(predictionInput).map(([key, value]) => (
                            <Box
                              key={key}
                              sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 2, bgcolor: '#F7FAFF' }}
                            >
                              <Typography variant="body2">{VARIABLE_LABELS[key] || formatVariableLabel(key)}</Typography>
                              <Typography variant="body2" fontWeight={700}>{String(value)}</Typography>
                            </Box>
                          ))}
                        </Stack>
                      ) : (
                        <Typography variant="body2" color="text.secondary">{isEnglish ? 'No variable.' : 'Aucune variable.'}</Typography>
                      )}
                    </ModuleCard>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <ModuleCard title={isEnglish ? 'Recommendation' : 'Recommandation'} description={isEnglish ? 'Follow-up suggestion.' : 'Proposition de suivi.'}>
                      {recommendation ? (
                        <Alert severity={riskLevel === 'Élevé' ? 'error' : riskLevel === 'Modéré' ? 'warning' : 'success'} sx={{ borderRadius: 2 }}>
                          {recommendation}
                        </Alert>
                      ) : (
                        <Typography variant="body2" color="text.secondary">N/A</Typography>
                      )}
                    </ModuleCard>
                  </Grid>
                </Grid>
              )}

            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default ModelAI;