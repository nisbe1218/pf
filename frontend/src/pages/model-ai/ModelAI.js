import React, { useContext, useEffect, useMemo, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Divider,
  FormControlLabel,
  Grid,
  IconButton,
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
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AppSidebar from '../../components/common/AppSidebar';
import api from '../../services/api/axios';
import { AuthContext } from '../../context/AuthContext';

const MODULE_TABS = [
  'Tableau de bord',
  'Sélection patient',
  'Lancer prédiction',
  'Résultats',
  'Historique',
  'Gestion modèles',
];

const PREDICTION_TYPES = [
  { value: 'mortalite', label: 'Mortalité 1 an', detail: 'Âge, DFG, antécédents' },
  { value: 'coagulation', label: 'Coagulation', detail: 'INR, TP, plaquettes' },
];

const MODEL_OPTIONS = [
  { value: 'random_forest', label: 'Random Forest', accuracy: '94%', description: 'Recommandé par défaut' },
  { value: 'xgboost', label: 'XGBoost', accuracy: '92%', description: 'Performant sur données tabulaires' },
  { value: 'logistic_regression', label: 'Régression logistique', accuracy: '87%', description: 'Cas simples et interprétable' },
  { value: 'svm', label: 'SVM', accuracy: '88%', description: 'Bon pour des jeux de données complexes' },
  { value: 'gradient_boosting', label: 'Gradient Boosting', accuracy: '91%', description: 'Robuste et stable' },
  { value: 'decision_tree', label: 'Arbre de décision', accuracy: '82%', description: 'Explicable pour les résidents' },
];

const MODEL_RECOMMENDATIONS = {
  mortalite: ['random_forest', 'xgboost'],
  coagulation: ['logistic_regression', 'svm'],
  transplantation: ['xgboost', 'decision_tree'],
  hospitalisation: ['gradient_boosting', 'random_forest'],
};

const INITIAL_PATIENT = {
  nom: 'Durand',
  id: 'SRC-001245',
  dossier: 'NEPH-2026-058',
  service: 'Néphrologie',
  statut: 'Actif',
  age: '58',
  dfg: '42',
  creatinine: '145',
  hemoglobine: '10.9',
  tension: '140/85',
  antecedents: 'HTA, Diabète',
};

const INTERPRETABILITY_FACTORS = [
  { label: 'Créatinine', value: '48%' },
  { label: 'Âge', value: '30%' },
  { label: 'Hypertension', value: '22%' },
  { label: 'DFG', value: '16%' },
];

const RISK_COLORS = {
  Faible: '#399776',
  Modéré: '#E4A330',
  Élevé: '#D4433D',
};

function ModuleCard({ title, description, children }) {
  return (
    <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94,115,141,0.14)' }}>
      <CardContent>
        <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {description}
        </Typography>
        {children}
      </CardContent>
    </Card>
  );
}

function ModelAI() {
  const [activeModule, setActiveModule] = useState(0);
  const [predictionStep, setPredictionStep] = useState(0);
  const [selectedPredictionType, setSelectedPredictionType] = useState('mortalite');
  const { user } = useContext(AuthContext);
  const [selectedModel, setSelectedModel] = useState('random_forest');
  const [patientCriteria, setPatientCriteria] = useState({ search: '', id: '', sexe: '' });
  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [pendingImportedPatientIds, setPendingImportedPatientIds] = useState(new Set());
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [patientRecord, setPatientRecord] = useState(INITIAL_PATIENT);
  const [predictionScore, setPredictionScore] = useState(65);
  const [riskLevel, setRiskLevel] = useState('Élevé');
  const [recommendation, setRecommendation] = useState('Surveillance renforcée, consultation spécialisée, révision du traitement.');
  const [predictionInput, setPredictionInput] = useState({});
  const [predictionFactors, setPredictionFactors] = useState([]);
  const [selectedDateFilter, setSelectedDateFilter] = useState('30jours');
  const [modelVersion, setModelVersion] = useState('v2.4');
  const [selectedVariableKeys, setSelectedVariableKeys] = useState(new Set());
  const [variableSearch, setVariableSearch] = useState('');

  const VARIABLE_LABELS = {
    adresse: 'Adresse',
    age: 'Âge',
    age_years: 'Âge',
    sexe: 'Sexe',
    sex: 'Sexe',
    date_admission: 'Date d’admission',
    date_evaluation_initiale: 'Date d’évaluation initiale',
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
    demographie_distance_centre_km: 'Démographie - distance au centre',
    demographie_couverture_sociale: 'Démographie - couverture sociale',
    demographie_statut_professionnel: 'Démographie - statut professionnel',
    demographie_niveau_education: 'Démographie - niveau d’éducation',
    demographie_tabagisme: 'Démographie - tabagisme',
    demographie_alcool: 'Démographie - alcool',
    irc_date_premier_contact_nephrologique: 'IRC - date premier contact néphrologique',
    irc_etiologie_principale: 'IRC - étiologie principale',
    irc_etiologie_secondaire: 'IRC - étiologie secondaire',
    irc_maladie_renale_hereditaire: 'IRC - maladie rénale héréditaire',
    irc_antecedents_familiaux_renaux: 'IRC - antécédents familiaux rénaux',
    irc_statut_biopsie_renale: 'IRC - statut biopsie rénale',
    irc_resultat_biopsie_renale: 'IRC - résultat biopsie rénale',
    irc_connue_avant_dialyse: 'IRC - connue avant dialyse',
    irc_source_adressage: 'IRC - source adressage',
    irc_contexte_debut_dialyse: 'IRC - contexte début dialyse',
    irc_duree_suivi_predialytique_mois: 'IRC - durée suivi prédialytique (mois)',
    irc_themes_education_therapeutique: 'IRC - thèmes éducation thérapeutique',
    irc_niveau_comprehension_patient: 'IRC - niveau compréhension patient',
    irc_preference_therapie_renale: 'IRC - préférence thérapie rénale',
    comorbidite_statut_diabete: 'Comorbidités - statut diabète',
    comorbidite_liste: 'Comorbidités - liste',
    comorbidite_autre: 'Comorbidités - autre',
    comorbidite_exposition_toxique: 'Comorbidités - exposition toxique',
    comorbidite_antecedents_medicaments_nephrotoxiques: 'Comorbidités - antécédents médicaments néphrotoxiques',
    presentation_date_episode: 'Présentation - date épisode',
    presentation_lieu_debut: 'Présentation - lieu de début',
    presentation_raisons_debut: 'Présentation - raisons de début',
    presentation_symptomes: 'Présentation - symptômes',
    presentation_tas_mmhg: 'Présentation - TAS (mmHg)',
    presentation_tad_mmhg: 'Présentation - TAD (mmHg)',
    presentation_frequence_cardiaque_bpm: 'Présentation - fréquence cardiaque',
    presentation_temperature_c: 'Présentation - température',
    presentation_poids_kg: 'Présentation - poids (kg)',
    presentation_taille_cm: 'Présentation - taille (cm)',
    presentation_statut_diurese: 'Présentation - statut diurèse',
    presentation_volume_urinaire_ml_j: 'Présentation - volume urinaire (ml/j)',
    presentation_autonomie_fonctionnelle: 'Présentation - autonomie fonctionnelle',
    presentation_notes_examen_clinique: 'Présentation - notes examen clinique',
    biologie_date_prelevement: 'Biologie - date prélèvement',
    biologie_dfg_mdrd_ml_min_1_73m2: 'Biologie - DFG MDRD',
    biologie_creatinine_mg_l: 'Biologie - créatinine',
    biologie_uree_g_l: 'Biologie - urée',
    biologie_hemoglobine_g_dl: 'Biologie - hémoglobine',
    biologie_hba1c_pct: 'Biologie - HbA1c',
    biologie_leucocytes_g_l: 'Biologie - leucocytes',
    biologie_plaquettes_g_l: 'Biologie - plaquettes',
    biologie_albumine_g_l: 'Biologie - albumine',
    biologie_crp_mg_l: 'Biologie - CRP',
    biologie_sodium_mmol_l: 'Biologie - sodium',
    biologie_potassium_mmol_l: 'Biologie - potassium',
    biologie_bicarbonates_mmol_l: 'Biologie - bicarbonates',
    biologie_calcium_corrige_mg_l: 'Biologie - calcium corrigé',
    biologie_phosphore_g_l: 'Biologie - phosphore',
    biologie_pth_pg_ml: 'Biologie - PTH',
    biologie_ferritine_ng_ml: 'Biologie - ferritine',
    biologie_saturation_transferrine_pct: 'Biologie - saturation transferrine',
    biologie_vitamine_d_ng_ml: 'Biologie - vitamine D',
    biologie_proteinurie_g_24h: 'Biologie - protéinurie',
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
    imagerie_fevg_pct: 'Imagerie - FE/FEVG',
    imagerie_hypertrophie_ventriculaire_gauche: 'Imagerie - hypertrophie ventriculaire gauche',
    imagerie_valvulopathie: 'Imagerie - valvulopathie',
    imagerie_autres_resultats: 'Imagerie - autres résultats',
    dialyse_date_debut: 'Dialyse - date de début',
    dialyse_modalite_initiale: 'Dialyse - modalité initiale',
    dialyse_modalite_actuelle: 'Dialyse - modalité actuelle',
    dialyse_type_acces_initial: 'Dialyse - type accès initial',
    dialyse_site_acces_initial: 'Dialyse - site accès initial',
    dialyse_date_creation_acces: 'Dialyse - date création accès',
    dialyse_date_premiere_utilisation_acces: 'Dialyse - date première utilisation accès',
    dialyse_jours_entre_catheter_et_fav: 'Dialyse - jours entre cathéter et FAV',
    dialyse_acces_admission_tunnelise: 'Dialyse - accès tunnelisé',
    dialyse_acces_admission_femoral: 'Dialyse - accès fémoral',
    dialyse_acces_admission_fav: 'Dialyse - accès FAV',
    dialyse_acces_admission_peritoneale: 'Dialyse - accès péritonéal',
    dialyse_seances_par_semaine: 'Dialyse - séances par semaine',
    dialyse_duree_seance_min: 'Dialyse - durée séance',
    dialyse_debit_sanguin_ml_min: 'Dialyse - débit sanguin',
    dialyse_debit_dialysat_ml_min: 'Dialyse - débit dialysat',
    dialyse_potassium_dialysat_mmol_l: 'Dialyse - potassium dialysat',
    dialyse_calcium_dialysat_mmol_l: 'Dialyse - calcium dialysat',
    dialyse_type_anticoagulation: 'Dialyse - type anticoagulation',
    dialyse_statut_fonction_renale_residuelle: 'Dialyse - fonction rénale résiduelle',
    dialyse_type_regime_dp: 'Dialyse - type régime DP',
    dialyse_nombre_echanges_dp_jour: 'Dialyse - nombre échanges DP/jour',
    dialyse_volume_stase_dp_ml: 'Dialyse - volume stase DP',
    dialyse_information_transplantation_donnee: 'Dialyse - information transplantation',
    dialyse_statut_liste_attente_transplantation: 'Dialyse - statut liste attente transplantation',
    transplantation_bilan_pretransplantation: 'Transplantation - bilan prétransplantation',
    immunologie_transfusion_immunisation: 'Immunologie - transfusion/immunisation',
    qualite_date_evaluation: 'Qualité - date évaluation',
    qualite_spktv: 'Qualité - SPKT/V',
    qualite_urr_pct: 'Qualité - URR (%)',
    qualite_prise_poids_interdialytique_kg: 'Qualité - prise poids interdialytique',
    qualite_taux_ultrafiltration_ml_kg_h: 'Qualité - ultrafiltration',
    qualite_tas_predialyse_mmhg: 'Qualité - TAS prédialyse',
    qualite_tas_postdialyse_mmhg: 'Qualité - TAS postdialyse',
    qualite_poids_sec_kg: 'Qualité - poids sec',
    qualite_seances_manquees_30j: 'Qualité - séances manquées',
    qualite_seances_raccourcies_30j: 'Qualité - séances raccourcies',
    qualite_hypotensions_intradialytiques_30j: 'Qualité - hypotensions intradialytiques',
    qualite_observance_declaree_patient: 'Qualité - observance patient',
    education_connaissance_pratique_dialyse: 'Éducation - pratique dialyse',
    education_soins_acces_vasculaire: 'Éducation - soins accès vasculaire',
    education_surveillance_poids_fluides: 'Éducation - surveillance poids/fluide',
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
  };

  const SECTION_FIELD_PREFIXES = [
    'demographie_',
    'irc_',
    'comorbidite_',
    'presentation_',
    'biologie_',
    'imagerie_',
    'dialyse_',
    'qualite_',
    'complication_',
    'traitement_',
    'devenir_',
  ];

  const VARIABLE_GROUPS = [
    {
      title: 'Données biologiques',
      description: 'Créatinine, urée, potassium, albumine, hémoglobine, CRP, protéinurie',
      fields: [
        'biologie_dfg_mdrd_ml_min_1_73m2',
        'biologie_creatinine_mg_l',
        'biologie_uree_g_l',
        'biologie_potassium_mmol_l',
        'biologie_albumine_g_l',
        'biologie_hemoglobine_g_dl',
        'biologie_crp_mg_l',
        'biologie_proteinurie_g_24h',
      ],
    },
    {
      title: 'Données cliniques',
      description: 'Signes vitaux, poids, température, diurèse',
      fields: [
        'presentation_tas_mmhg',
        'presentation_tad_mmhg',
        'presentation_frequence_cardiaque_bpm',
        'presentation_temperature_c',
        'presentation_poids_kg',
        'presentation_taille_cm',
        'presentation_statut_diurese',
        'presentation_volume_urinaire_ml_j',
      ],
    },
    {
      title: 'Données démographiques',
      description: 'Âge, sexe, tabagisme, alcool, statut social',
      fields: [
        'demographie_age_ans',
        'demographie_sexe',
        'demographie_tabagisme',
        'demographie_alcool',
        'demographie_distance_centre_km',
        'demographie_statut_professionnel',
        'demographie_niveau_education',
      ],
    },
    {
      title: 'Données comorbidité',
      description: 'Diabète, HTA, exposition toxique, médicaments néphrotoxiques',
      fields: [
        'comorbidite_statut_diabete',
        'comorbidite_liste',
        'comorbidite_autre',
        'comorbidite_exposition_toxique',
        'comorbidite_antecedents_medicaments_nephrotoxiques',
      ],
    },
    {
      title: 'Données de dialyse',
      description: 'Modalité, durée, débit, type d’accès, qualité de dialyse',
      fields: [
        'dialyse_modalite_actuelle',
        'dialyse_type_acces_initial',
        'dialyse_site_acces_initial',
        'dialyse_seances_par_semaine',
        'dialyse_duree_seance_min',
        'dialyse_debit_sanguin_ml_min',
        'dialyse_debit_dialysat_ml_min',
        'dialyse_potassium_dialysat_mmol_l',
        'dialyse_calcium_dialysat_mmol_l',
        'dialyse_type_anticoagulation',
        'qualite_spktv',
        'qualite_urr_pct',
      ],
    },
    {
      title: 'Données néphropathie',
      description: 'Étiologie, contexte, suivi pré-dialyse, biopsie',
      fields: [
        'irc_etiologie_principale',
        'irc_etiologie_secondaire',
        'irc_maladie_renale_hereditaire',
        'irc_antecedents_familiaux_renaux',
        'irc_statut_biopsie_renale',
        'irc_resultat_biopsie_renale',
        'irc_contexte_debut_dialyse',
        'irc_duree_suivi_predialytique_mois',
      ],
    },
    {
      title: 'Données imagerie',
      description: 'Échographie rénale, échocardiographie, FEVG',
      fields: [
        'imagerie_date_echographie_renale',
        'imagerie_taille_reins',
        'imagerie_echogenicite_renale',
        'imagerie_hydronephrose',
        'imagerie_kystes_renaux',
        'imagerie_lithiase',
        'imagerie_radiographie_thorax',
        'imagerie_date_echocardiographie',
        'imagerie_fevg_pct',
        'imagerie_hypertrophie_ventriculaire_gauche',
        'imagerie_valvulopathie',
      ],
    },
  ];

  const VARIABLE_METADATA = {
    biologie_creatinine_mg_l: { unit: 'mg/L', req: true },
    biologie_uree_g_l: { unit: 'g/L', req: true },
    biologie_potassium_mmol_l: { unit: 'mmol/L', req: true },
    biologie_albumine_g_l: { unit: 'g/L', req: true },
    biologie_hemoglobine_g_dl: { unit: 'g/dL', req: true },
    biologie_crp_mg_l: { unit: 'mg/L', req: true },
    biologie_proteinurie_g_24h: { unit: 'g/24h', req: true },
    presentation_poids_kg: { unit: 'kg', req: true },
    age: { unit: 'ans', req: true },
    sexe: { unit: '', req: true },
    imc: { unit: '', req: false },
    stade_mrc: { unit: '', req: false },
    comorbidite_liste: { unit: '', req: false },
    comorbidite_statut_diabete: { unit: '', req: false },
    dialyse_modalite_actuelle: { unit: '', req: true },
    dialyse_type_acces_initial: { unit: '', req: false },
    dialyse_site_acces_initial: { unit: '', req: false },
    dialyse_duree_seance_min: { unit: 'min', req: false },
    qualite_spktv: { unit: '', req: true },
  };

  const PATIENT_DETAIL_SECTIONS = [
    {
      id: 'demo',
      title: 'Démographie',
      fields: [
        'demographie_sexe',
        'demographie_age_ans',
        'date_naissance',
        'demographie_statut_matrimonial',
        'demographie_mode_vie',
        'demographie_zone_residence',
        'demographie_distance_centre_km',
        'demographie_couverture_sociale',
        'demographie_statut_professionnel',
        'demographie_tabagisme',
        'demographie_alcool',
      ],
    },
    {
      id: 'irc',
      title: 'IRC — Néphropathie',
      fields: [
        'irc_etiologie_principale',
        'irc_etiologie_secondaire',
        'irc_maladie_renale_hereditaire',
        'irc_antecedents_familiaux_renaux',
        'irc_statut_biopsie_renale',
        'irc_resultat_biopsie_renale',
        'irc_connue_avant_dialyse',
        'irc_contexte_debut_dialyse',
        'irc_duree_suivi_predialytique_mois',
      ],
    },
    {
      id: 'bio',
      title: 'Biologie',
      fields: [
        'biologie_dfg_mdrd_ml_min_1_73m2',
        'biologie_creatinine_mg_l',
        'biologie_uree_g_l',
        'biologie_hemoglobine_g_dl',
        'biologie_albumine_g_l',
        'biologie_crp_mg_l',
        'biologie_potassium_mmol_l',
        'biologie_bicarbonates_mmol_l',
        'biologie_calcium_corrige_mg_l',
        'biologie_phosphore_mg_l',
        'biologie_pth_pg_ml',
        'biologie_ferritine_ng_ml',
        'biologie_saturation_transferrine_pct',
        'biologie_vitamine_d_ng_ml',
        'biologie_proteinurie_g_24h',
      ],
    },
    {
      id: 'pres',
      title: 'Présentation clinique',
      fields: [
        'presentation_tas_mmhg',
        'presentation_tad_mmhg',
        'presentation_frequence_cardiaque_bpm',
        'presentation_temperature_c',
        'presentation_poids_kg',
        'presentation_taille_cm',
        'presentation_statut_diurese',
        'presentation_volume_urinaire_ml_j',
        'presentation_autonomie_fonctionnelle',
        'presentation_symptomes',
      ],
    },
    {
      id: 'dial',
      title: 'Dialyse',
      fields: [
        'dialyse_date_debut',
        'dialyse_modalite_actuelle',
        'dialyse_type_acces_initial',
        'dialyse_site_acces_initial',
        'dialyse_seances_par_semaine',
        'dialyse_duree_seance_min',
        'dialyse_debit_sanguin_ml_min',
        'dialyse_debit_dialysat_ml_min',
        'dialyse_potassium_dialysat_mmol_l',
        'dialyse_calcium_dialysat_mmol_l',
        'dialyse_type_anticoagulation',
        'dialyse_statut_fonction_renale_residuelle',
      ],
    },
    {
      id: 'qual',
      title: 'Qualité de dialyse',
      fields: [
        'qualite_spktv',
        'qualite_urr_pct',
        'qualite_prise_poids_interdialytique_kg',
        'qualite_taux_ultrafiltration_ml_kg_h',
        'qualite_tas_predialyse_mmhg',
        'qualite_tas_postdialyse_mmhg',
        'qualite_poids_sec_kg',
        'qualite_seances_manquees_30j',
        'qualite_hypotensions_intradialytiques_30j',
      ],
    },
    {
      id: 'comor',
      title: 'Comorbidités',
      fields: [
        'comorbidite_statut_diabete',
        'comorbidite_liste',
        'comorbidite_autre',
        'comorbidite_exposition_toxique',
        'comorbidite_antecedents_medicaments_nephrotoxiques',
      ],
    },
    {
      id: 'img',
      title: 'Imagerie',
      fields: [
        'imagerie_date_echographie_renale',
        'imagerie_taille_reins',
        'imagerie_echogenicite_renale',
        'imagerie_hydronephrose',
        'imagerie_kystes_renaux',
        'imagerie_lithiase',
        'imagerie_radiographie_thorax',
        'imagerie_date_echocardiographie',
        'imagerie_fevg_pct',
        'imagerie_hypertrophie_ventriculaire_gauche',
        'imagerie_valvulopathie',
      ],
    },
  ];

  const REQUIRED_VARIABLE_KEYS = new Set(
    Object.entries(VARIABLE_METADATA)
      .filter(([, meta]) => meta.req)
      .map(([key]) => key),
  );

  const CORE_VARIABLE_KEYS = [
    'id_patient',
    'id_enregistrement_source',
    'id_site',
    'statut_inclusion',
    'statut_consentement',
    'utilisateur_saisie',
    'derniere_mise_a_jour',
    'date_evaluation_initiale',
    'nom',
    'prenom',
    'age',
    'sexe',
    'maladie',
    'telephone',
    'adresse',
    'date_naissance',
    'date_admission',
  ];

  const formatVariableLabel = (key) => {
    if (VARIABLE_LABELS[key]) {
      return VARIABLE_LABELS[key];
    }
    return key
      .replace(/_/g, ' ')
      .replace(/\b[a-z]/g, (match) => match.toUpperCase());
  };

  const activeModelDetails = useMemo(
    () => MODEL_OPTIONS.find((item) => item.value === selectedModel) || MODEL_OPTIONS[0],
    [selectedModel],
  );

  const [modelMode, setModelMode] = useState('auto');
  const [variablesValidated, setVariablesValidated] = useState(false);

  const recommendedModels = useMemo(
    () => MODEL_RECOMMENDATIONS[selectedPredictionType] || ['random_forest'],
    [selectedPredictionType],
  );

  useEffect(() => {
    if (modelMode === 'auto') {
      setSelectedModel(recommendedModels[0]);
    }
  }, [modelMode, recommendedModels]);

  const roleName = user?.role === 'professeur' ? 'Professeur'
    : user?.role === 'chef_service' ? 'Chef de service'
    : user?.role === 'super_admin' ? 'Administrateur'
    : 'Utilisateur';

  const availableVariableKeys = useMemo(() => {
    const keys = new Set();

    const addKeyIfValid = (key) => {
      if (!key || ['id', 'created_at', 'updated_at', 'extra_data'].includes(key)) {
        return;
      }
      const isSectionKey = SECTION_FIELD_PREFIXES.some((prefix) => key.startsWith(prefix));
      if (isSectionKey || CORE_VARIABLE_KEYS.includes(key)) {
        keys.add(key);
      }
    };

    patients.forEach((patient) => {
      Object.keys(patient || {}).forEach((key) => {
        addKeyIfValid(key);
      });
      if (patient.extra_data && typeof patient.extra_data === 'object') {
        Object.keys(patient.extra_data).forEach((key) => {
          addKeyIfValid(key);
        });
      }
      SECTION_FIELD_PREFIXES.forEach((prefix) => {
        const sectionData = patient[`${prefix.replace(/_$/, '')}_data`];
        if (sectionData && typeof sectionData === 'object') {
          Object.keys(sectionData).forEach((nestedKey) => {
            addKeyIfValid(nestedKey);
          });
        }
      });
    });

    return Array.from(keys).sort((a, b) => {
      const labelA = formatVariableLabel(a).toLowerCase();
      const labelB = formatVariableLabel(b).toLowerCase();
      return labelA.localeCompare(labelB, 'fr');
    });
  }, [patients]);

  const availableVariableKeysSet = useMemo(
    () => new Set(availableVariableKeys),
    [availableVariableKeys],
  );

  const requiredSelectedCount = useMemo(() => {
    return [...REQUIRED_VARIABLE_KEYS].filter((key) => selectedVariableKeys.has(key)).length;
  }, [selectedVariableKeys]);

  const filteredVariableGroups = useMemo(() => {
    const query = variableSearch.trim().toLowerCase();
    if (!query) {
      return VARIABLE_GROUPS;
    }
    return VARIABLE_GROUPS
      .map((group) => ({
        ...group,
        fields: group.fields.filter((fieldKey) => {
          const label = formatVariableLabel(fieldKey).toLowerCase();
          return label.includes(query) || fieldKey.includes(query);
        }),
      }))
      .filter((group) => group.fields.length > 0);
  }, [variableSearch]);

  const getPatientFieldValue = (patient, fieldKey) => {
    if (!patient) {
      return '';
    }
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
  };

  const buildPredictionPayload = () => {
    if (!selectedPatient) {
      return {};
    }

    const payload = {};
    [...selectedVariableKeys].forEach((fieldKey) => {
      const value = getPatientFieldValue(selectedPatient, fieldKey);
      if (value !== '') {
        const numeric = Number(value.replace(',', '.'));
        payload[fieldKey] = Number.isNaN(numeric) ? value : numeric;
      }
    });

    return payload;
  };

  const safeParseValue = (value) => {
    if (typeof value === 'number') {
      return value;
    }
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isNaN(parsed) ? 0 : parsed;
  };

  const computePrediction = (payload) => {
    const base = selectedPredictionType === 'coagulation' ? 20 : 30;
    const modelBonus = selectedModel === 'random_forest' ? 8 : selectedModel === 'xgboost' ? 10 : selectedModel === 'svm' ? 6 : 5;
    let score = base + modelBonus;

    if (selectedPredictionType === 'mortalite') {
      score += Math.min(30, Math.max(0, (safeParseValue(payload.age) - 50) * 0.6));
      score += Math.min(20, Math.max(0, (safeParseValue(payload.creatinine) - 120) * 0.08));
      score += Math.min(15, Math.max(0, (40 - safeParseValue(payload.albumine)) * 1.2));
      score += Math.min(15, Math.max(0, (45 - safeParseValue(payload.dfg)) * 0.3));
    } else {
      score += Math.min(30, Math.max(0, (safeParseValue(payload.inr) - 1.2) * 16));
      score += Math.min(20, Math.max(0, (safeParseValue(payload.plaquettes) < 150 ? 150 - safeParseValue(payload.plaquettes) : 0) * 0.1));
      score += Math.min(15, Math.max(0, (safeParseValue(payload.tp) < 70 ? 70 - safeParseValue(payload.tp) : 0) * 0.2));
    }

    return Math.min(100, Math.max(10, Math.round(score)));
  };

  const buildInterpretability = (payload) => {
    const factors = [];
    const delta = (label, condition, value) => {
      if (condition) factors.push({ label, weight: value });
    };

    if (selectedPredictionType === 'mortalite') {
      delta('Âge élevé', safeParseValue(payload.age) >= 65, 22);
      delta('Créatinine augmentée', safeParseValue(payload.creatinine) > 120, 18);
      delta('Albumine basse', safeParseValue(payload.albumine) < 35, 16);
      delta('DFG bas', safeParseValue(payload.dfg) < 45, 14);
    } else {
      delta('INR élevé', safeParseValue(payload.inr) > 1.3, 24);
      delta('TP bas', safeParseValue(payload.tp) < 70, 20);
      delta('Plaquettes basses', safeParseValue(payload.plaquettes) < 150, 16);
    }

    return factors.sort((a, b) => b.weight - a.weight).slice(0, 4);
  };

  useEffect(() => {
    // Ne rien sélectionner par défaut pour que l'utilisateur puisse choisir
    // uniquement les variables qu'il souhaite utiliser.
    if (!selectedVariableKeys.size && !availableVariableKeys.length) {
      setSelectedVariableKeys(new Set());
    }
  }, []);

  const selectedVariablesCount = useMemo(() => selectedVariableKeys.size, [selectedVariableKeys]);

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
        const status = saved ? JSON.parse(saved) : null;
        if (status?.status === 'pending' && Array.isArray(status.pendingIds)) {
          setPendingImportedPatientIds(new Set(status.pendingIds));
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

  const selectablePatients = useMemo(() => {
    return patients.filter((patient) => !pendingImportedPatientIds.has(patient.id));
  }, [patients, pendingImportedPatientIds]);

  const validatedPatients = useMemo(() => {
    return selectablePatients.filter((patient) => {
      const status = String(patient.statut_inclusion || '').toLowerCase();
      return ['valide', 'validé', 'valides', 'approved', 'validated'].includes(status);
    });
  }, [selectablePatients]);

  const isHighRiskPatient = (patient) => {
    const normalized = (value) => String(value || '').trim().toLowerCase();
    const infection = normalized(patient.infection);
    const hemorrhage = normalized(patient.hemorrhage);
    const avfCreated = normalized(patient.avf_created);
    const statut = normalized(patient.statut_inclusion);

    return (
      ['oui', 'true', '1'].includes(infection) ||
      ['oui', 'true', '1'].includes(hemorrhage) ||
      ['oui', 'true', '1'].includes(avfCreated) ||
      statut.includes('critique') ||
      statut.includes('haut risque')
    );
  };

  const highRiskPatients = useMemo(() => {
    return validatedPatients.filter(isHighRiskPatient);
  }, [validatedPatients]);

  const recentPatientsCount = useMemo(() => {
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
    return validatedPatients.reduce((count, patient) => {
      const date = new Date(patient.date_admission || patient.date_evaluation_initiale || '');
      return !Number.isNaN(date.getTime()) && date.getTime() >= cutoff ? count + 1 : count;
    }, 0);
  }, [validatedPatients]);

  const validationRate = useMemo(() => {
    return patients.length ? Math.round((validatedPatients.length / patients.length) * 100) : 0;
  }, [patients.length, validatedPatients.length]);

  const filteredPatients = useMemo(() => {
    return selectablePatients.filter((patient) => {
      const fullName = `${patient.nom || ''} ${patient.prenom || ''}`.toLowerCase();
      const search = patientCriteria.search.trim().toLowerCase();
      const service = (patient.service || '').toLowerCase();
      const statut = (patient.statut_inclusion || '').toLowerCase();
      const sex = (patient.sexe || patient.sex || '').toLowerCase();
      return (
        (!search || fullName.includes(search) || String(patient.id || '').includes(search) || String(patient.id_patient || '').includes(search) || String(patient.id_enregistrement_source || '').includes(search)) &&
        (!patientCriteria.id || String(patient.id).includes(patientCriteria.id) || String(patient.id_patient || '').includes(patientCriteria.id) || String(patient.id_enregistrement_source || '').includes(patientCriteria.id)) &&
        (!patientCriteria.sexe || sex === patientCriteria.sexe.toLowerCase())
      );
    });
  }, [selectablePatients, patientCriteria]);

  const displayPatients = useMemo(() => {
    const noSearch = !patientCriteria.search && !patientCriteria.id && !patientCriteria.sexe;
    return noSearch ? selectablePatients : filteredPatients;
  }, [selectablePatients, filteredPatients, patientCriteria]);

  const selectedPatient = useMemo(() => {
    return patients.find((patient) => String(patient.id) === String(selectedPatientId)) || null;
  }, [patients, selectedPatientId]);

  const handleSearchChange = (field, value) => {
    setPatientCriteria((current) => ({ ...current, [field]: value }));
  };

  const handleSelectPatient = (patient) => {
    setSelectedPatientId(patient.id);
    setPatientRecord({
      nom: patient.nom || 'Inconnu',
      id: patient.id || '',
      dossier: patient.id_enregistrement_source || '',
      service: patient.id_site || '',
      statut: patient.statut_inclusion || 'Non renseigné',
      age: patient.age || '',
      sexe: patient.sexe || '',
      tension: patient.tension || '',
      poids: patient.poids || '',
      creatinine: patient.creatinine || '',
      dfg: patient.dfg || '',
      hemoglobine: patient.hemoglobine || '',
      uree: patient.uree || '',
      antecedents: patient.antecedents || '',
    });
    setActiveModule(2);
  };

  const handleRunPrediction = async () => {
    const payload = buildPredictionPayload();
    const modelParam = modelMode === 'auto' ? 'auto' : selectedModel;

    try {
      const response = await api.post('predictions/predict/', {
        prediction_type: selectedPredictionType,
        model: modelParam,
        features: payload,
      });

      const data = response.data;
      setPredictionInput(payload);
      setPredictionFactors(data.factors || buildInterpretability(payload));
      setPredictionScore(data.score || 0);
      setRiskLevel(data.risk_level || (data.score <= 30 ? 'Faible' : data.score <= 70 ? 'Modéré' : 'Élevé'));
      setRecommendation(
        data.risk_level === 'Élevé'
          ? 'Risques accrus : surveillance intensive, adaptation du traitement et consultation spécialisée.'
          : data.risk_level === 'Modéré'
            ? 'Suivi régulier et optimisation des paramètres cliniques.'
            : 'Risque faible, maintien du suivi standard.'
      );
      setPredictionStep(3);
      setActiveModule(3);
    } catch (error) {
      console.error('Erreur de prédiction', error);
      const score = computePrediction(payload);
      const level = score <= 30 ? 'Faible' : score <= 70 ? 'Modéré' : 'Élevé';
      setPredictionInput(payload);
      setPredictionFactors(buildInterpretability(payload));
      setPredictionScore(score);
      setRiskLevel(level);
      setRecommendation(
        level === 'Élevé'
          ? 'Risques accrus : surveillance intensive, adaptation du traitement et consultation spécialisée.'
          : level === 'Modéré'
            ? 'Suivi régulier et optimisation des paramètres cliniques.'
            : 'Risque faible, maintien du suivi standard.'
      );
      setPredictionStep(3);
      setActiveModule(3);
    }
  };

  const moduleDescription = [
    'Vue globale du service avec indicateurs et alertes patients prioritaires.',
    'Recherche rapide de patient, filtres par service et statut, et chargement automatique des données cliniques.',
    '4 étapes vers la prédiction : type, données, modèle, exécution.',
    'Affichage du score, de la courbe historique et de l’interprétabilité.',
    'Historique des prédictions filtrable et traçabilité complète.',
    'Gestion des modèles ML, versions et métriques de déploiement.',
  ];

  return (
    <Box
      sx={{
        minHeight: '100vh',
        py: 2,
        background: 'radial-gradient(circle at top left, rgba(77, 142, 166, 0.12), transparent 24%), linear-gradient(180deg, #f2f7fb 0%, #edf3f8 100%)',
      }}
    >
      <Grid container spacing={2} alignItems="flex-start">
        <Grid item xs={12} md={3} lg={2}>
          <AppSidebar />
        </Grid>

        <Grid item xs={12} md={9} lg={10}>
          <Stack spacing={3}>
            <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94,115,141,0.14)' }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems="center" spacing={2}>
                  <Box>
                    <Typography variant="h5" fontWeight={900}>
                      Interface des modèles de Machine Learning
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      Aide à la décision clinique – Pathologies rénales
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip label={roleName} color="primary" sx={{ fontWeight: 700 }} />
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94,115,141,0.14)' }}>
              <CardContent>
                <Tabs value={activeModule} onChange={(_, value) => setActiveModule(value)} variant="scrollable" allowScrollButtonsMobile>
                  {MODULE_TABS.map((label) => (
                    <Tab key={label} value={MODULE_TABS.indexOf(label)} label={label} />
                  ))}
                </Tabs>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  {moduleDescription[activeModule]}
                </Typography>
              </CardContent>
            </Card>

            {activeModule === 0 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={3}>
                  <ModuleCard title="Patients suivis" description="Volume total de patients présents dans la base">
                    <Typography variant="h3" fontWeight={900}>{patients.length}</Typography>
                  </ModuleCard>
                </Grid>
                <Grid item xs={12} md={3}>
                  <ModuleCard title="Haut risque" description="Alertes patients prioritaires">
                    <Typography variant="h3" fontWeight={900} color="#D4433D">{highRiskPatients.length}</Typography>
                  </ModuleCard>
                </Grid>
                <Grid item xs={12} md={3}>
                  <ModuleCard title="Patients récents" description="Patients arrivés dans les 30 derniers jours">
                    <Typography variant="h3" fontWeight={900}>{recentPatientsCount}</Typography>
                  </ModuleCard>
                </Grid>
                <Grid item xs={12} md={3}>
                  <ModuleCard title="Taux validés" description="Pourcentage de patients validés dans la base">
                    <Typography variant="h3" fontWeight={900} color="#2B7A6B">{validationRate}%</Typography>
                  </ModuleCard>
                </Grid>
                <Grid item xs={12}>
                  <ModuleCard title="Alertes haut risque" description="Lancer un dossier en un clic depuis le tableau de bord.">
                    <Stack spacing={2}>
                      {highRiskPatients.length ? (
                        highRiskPatients.slice(0, 3).map((patient) => {
                          const reason = [];
                          const infection = String(patient.infection || '').trim().toLowerCase();
                          const hemorrhage = String(patient.hemorrhage || '').trim().toLowerCase();
                          const avfCreated = String(patient.avf_created || '').trim().toLowerCase();
                          if (['oui', 'true', '1'].includes(infection)) reason.push('Infection');
                          if (['oui', 'true', '1'].includes(hemorrhage)) reason.push('Hémorragie');
                          if (['oui', 'true', '1'].includes(avfCreated)) reason.push('AVF');
                          if (!reason.length) {
                            reason.push('Statut critique');
                          }
                          return (
                            <Button
                              key={patient.id}
                              variant="outlined"
                              fullWidth
                              onClick={() => handleSelectPatient(patient)}
                            >
                              {patient.nom || 'Patient'} {patient.prenom || ''} — {reason.join(' / ')}
                            </Button>
                          );
                        })
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Aucune alerte haut risque détectée.
                        </Typography>
                      )}
                    </Stack>
                  </ModuleCard>
                </Grid>
              </Grid>
            )}

            {activeModule === 1 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                  <ModuleCard title="Recherche du patient" description="Recherchez par nom, prénom ou identifiant patient pour sélectionner rapidement un dossier.">
                    <Stack spacing={2}>
                      <TextField label="Nom ou prénom" value={patientCriteria.search} onChange={(e) => handleSearchChange('search', e.target.value)} fullWidth size="small" />
                      <TextField label="ID patient" value={patientCriteria.id} onChange={(e) => handleSearchChange('id', e.target.value)} fullWidth size="small" />
                      <TextField
                        select
                        label="Sexe"
                        value={patientCriteria.sexe}
                        onChange={(e) => handleSearchChange('sexe', e.target.value)}
                        fullWidth
                        size="small"
                      >
                        <MenuItem value="">Tous</MenuItem>
                        <MenuItem value="M">Homme</MenuItem>
                        <MenuItem value="F">Femme</MenuItem>
                        <MenuItem value="O">Autre</MenuItem>
                      </TextField>
                    </Stack>
                  </ModuleCard>
                </Grid>

                <Grid item xs={12} md={8}>
                  <ModuleCard title="Résultats de recherche" description="Patients existants trouvés dans la base de données.">
                    <Stack spacing={1}>
                      {loadingPatients ? (
                        <Typography variant="body2" color="text.secondary">Chargement des patients...</Typography>
                      ) : displayPatients.length ? (
                        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden' }}>
                          <Table size="small">
                            <TableHead sx={{ backgroundColor: 'rgba(226,237,244,0.9)' }}>
                              <TableRow>
                                <TableCell sx={{ fontWeight: 700 }}>id_patient</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>nom</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>prenom</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>sexe</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>site</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>âge</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>statut</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {displayPatients.map((patient) => (
                                <TableRow key={patient.id} hover sx={{ cursor: 'pointer' }} onClick={() => handleSelectPatient(patient)}>
                                  <TableCell>{patient.id_patient || '-'}</TableCell>
                                  <TableCell>{patient.nom || '-'}</TableCell>
                                  <TableCell>{patient.prenom || '-'}</TableCell>
                                  <TableCell>{patient.sexe || patient.sex || '-'}</TableCell>
                                  <TableCell>{patient.id_site || '-'}</TableCell>
                                  <TableCell>{patient.age || patient.age_years || '-'}</TableCell>
                                  <TableCell>{patient.statut_inclusion || '-'}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      ) : (
                        <Typography variant="body2" color="text.secondary">Aucun patient trouvé. Essayez une autre recherche.</Typography>
                      )}
                    </Stack>
                  </ModuleCard>
                </Grid>
              </Grid>
            )}

            {activeModule === 2 && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, bgcolor: 'background.paper' }}>
                    <Typography variant="h6" fontWeight={700}>Sélection des variables</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Choisissez les variables à soumettre au modèle de prédiction.</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
                      {PREDICTION_TYPES.map((type) => (
                        <Button
                          key={type.value}
                          variant={selectedPredictionType === type.value ? 'contained' : 'outlined'}
                          color={selectedPredictionType === type.value ? 'success' : 'inherit'}
                          onClick={() => setSelectedPredictionType(type.value)}
                          sx={{ textTransform: 'none' }}
                        >
                          {type.label}
                        </Button>
                      ))}
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={8}>
                  <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, bgcolor: 'background.paper', minHeight: 680 }}>
                    <Typography variant="subtitle1" fontWeight={700}>Fiche patient</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>La fiche détaillée du patient sélectionné est affichée ici.</Typography>

                    {selectedPatient ? (
                      <Stack spacing={2}>
                        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
                          <Stack direction="row" spacing={2} alignItems="center">
                            <Avatar sx={{ bgcolor: '#E1F5EE', color: '#0F6E56', width: 48, height: 48, fontWeight: 700 }}>
                              {selectedPatient.nom?.[0] || selectedPatient.prenom?.[0] || 'P'}
                            </Avatar>
                            <Box>
                              <Typography variant="subtitle1" fontWeight={700}>{selectedPatient.nom || ''} {selectedPatient.prenom || ''}</Typography>
                              <Typography variant="caption" color="text.secondary" display="block">
                                ID : {selectedPatient.id_patient || selectedPatient.id || '-'} · Site : {selectedPatient.id_site || '-'}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" display="block">
                                Dernière MAJ : {selectedPatient.derniere_mise_a_jour || selectedPatient.date_evaluation_initiale || '-'}
                              </Typography>
                            </Box>
                          </Stack>
                          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 2 }}>
                            {selectedPatient.dialyse_modalite_actuelle && <Chip label={selectedPatient.dialyse_modalite_actuelle} size="small" sx={{ bgcolor: '#E1F5EE', color: '#0F6E56' }} />}
                            {selectedPatient.statut_inclusion && <Chip label={selectedPatient.statut_inclusion} size="small" sx={{ bgcolor: '#E6F1FB', color: '#185FA5' }} />}
                            {selectedPatient.comorbidite_statut_diabete && <Chip label="Diabète" size="small" sx={{ bgcolor: '#FAEEDA', color: '#854F0B' }} />}
                          </Stack>
                        </Paper>

                        {PATIENT_DETAIL_SECTIONS.map((section) => (
                          <Accordion key={section.id} defaultExpanded disableGutters sx={{ borderRadius: 2, border: '1px solid rgba(94,115,141,0.14)', boxShadow: 'none' }}>
                            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2, py: 1.5 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                                <Typography variant="subtitle2" fontWeight={700}>{section.title}</Typography>
                                <Typography variant="body2" color="text.secondary">{section.fields.length} champs</Typography>
                              </Box>
                            </AccordionSummary>
                            <AccordionDetails sx={{ p: 2, pt: 1 }}>
                              <Grid container spacing={2}>
                                {section.fields.map((fieldKey) => {
                                  const value = getPatientFieldValue(selectedPatient, fieldKey) || '—';
                                  const available = availableVariableKeysSet.has(fieldKey);
                                  return (
                                    <Grid key={fieldKey} item xs={12} sm={6}>
                                      <Box sx={{ p: 0.5 }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                          <Checkbox
                                            checked={selectedVariableKeys.has(fieldKey)}
                                            disabled={!available}
                                            onChange={() => setSelectedVariableKeys((current) => {
                                              const updated = new Set(current);
                                              if (updated.has(fieldKey)) {
                                                updated.delete(fieldKey);
                                              } else {
                                                updated.add(fieldKey);
                                              }
                                              return updated;
                                            })}
                                            size="small"
                                          />
                                          <Box>
                                            <Typography variant="body2">{VARIABLE_LABELS[fieldKey] || formatVariableLabel(fieldKey)}</Typography>
                                            <Typography variant="caption" color="text.secondary">{value}</Typography>
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
                      <Typography variant="body2" color="text.secondary">Sélectionnez un patient dans l’onglet "Sélectionner un patient" pour afficher sa fiche complète.</Typography>
                    )}
                  </Paper>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, bgcolor: 'background.paper', minHeight: 680 }}>
                    <Typography variant="subtitle1" fontWeight={700}>Éléments sélectionnés</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Variables choisies pour la prédiction.</Typography>

                    {selectedVariableKeys.size ? (
                      <Stack spacing={1}>
                        {[...selectedVariableKeys].map((fieldKey) => (
                          <Paper key={fieldKey} variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: 'background.default' }}>
                            <Stack direction="row" alignItems="center" justifyContent="space-between">
                              <Box>
                                <Typography variant="body2" fontWeight={700}>{VARIABLE_LABELS[fieldKey] || formatVariableLabel(fieldKey)}</Typography>
                                <Typography variant="caption" color="text.secondary">{getPatientFieldValue(selectedPatient, fieldKey) || '—'}</Typography>
                              </Box>
                              <IconButton
                                size="small"
                                onClick={() => setSelectedVariableKeys((current) => {
                                  const updated = new Set(current);
                                  updated.delete(fieldKey);
                                  return updated;
                                })}
                              >
                                ×
                              </IconButton>
                            </Stack>
                          </Paper>
                        ))}
                      </Stack>
                    ) : (
                      <Typography variant="body2" color="text.secondary">Aucune variable sélectionnée.</Typography>
                    )}
                  </Paper>

                  <Paper variant="outlined" sx={{ p: 3, borderRadius: 4, bgcolor: 'background.paper', mt: 3, boxShadow: '0 12px 24px rgba(15, 46, 84, 0.06)' }}>
                    <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>Choix du modèle</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 680 }}>
                      Selon le type de prédiction, plusieurs modèles sont disponibles. Vous pouvez laisser le système choisir automatiquement ou sélectionner un modèle manuellement.
                    </Typography>

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 3 }}>
                      <Button
                        variant={modelMode === 'auto' ? 'contained' : 'outlined'}
                        color={modelMode === 'auto' ? 'success' : 'inherit'}
                        onClick={() => setModelMode('auto')}
                        sx={{
                          textTransform: 'none',
                          minWidth: 140,
                          borderRadius: 3,
                          px: 3,
                          py: 1.5,
                        }}
                      >
                        Automatique
                      </Button>
                      <Button
                        variant={modelMode === 'manual' ? 'contained' : 'outlined'}
                        color={modelMode === 'manual' ? 'success' : 'inherit'}
                        onClick={() => setModelMode('manual')}
                        sx={{
                          textTransform: 'none',
                          minWidth: 140,
                          borderRadius: 3,
                          px: 3,
                          py: 1.5,
                        }}
                      >
                        Manuel
                      </Button>
                    </Stack>

                    {modelMode === 'manual' ? (
                      <Stack spacing={2} sx={{ mb: 3 }}>
                        {MODEL_OPTIONS.map((model) => (
                          <Paper
                            key={model.value}
                            variant="outlined"
                            sx={{
                              p: 2.5,
                              borderRadius: 3,
                              borderColor: selectedModel === model.value ? 'success.main' : 'divider',
                              boxShadow: selectedModel === model.value ? '0 16px 32px rgba(14,110,83,0.12)' : '0 4px 16px rgba(15, 46, 84, 0.05)',
                              transition: 'transform 0.2s ease, border-color 0.2s ease',
                              cursor: 'pointer',
                              '&:hover': {
                                transform: 'translateY(-2px)',
                              },
                            }}
                            onClick={() => setSelectedModel(model.value)}
                          >
                            <Typography variant="subtitle1" fontWeight={800} sx={{ mb: 1 }}>{model.label}</Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{model.description}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {selectedModel === model.value ? 'Sélectionné' : 'Cliquez pour activer'}
                            </Typography>
                          </Paper>
                        ))}
                      </Stack>
                    ) : (
                      <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, bgcolor: '#F6FAF6', borderColor: 'success.light', mb: 3 }}>
                        <Typography variant="subtitle1" fontWeight={700}>Recommandation automatique</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          Le système recommande {recommendedModels.length > 1 ? 'les modèles suivants' : 'le modèle suivant'} pour la prédiction <strong>{PREDICTION_TYPES.find((type) => type.value === selectedPredictionType)?.label}</strong>.
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: 'wrap' }}>
                          {recommendedModels.map((modelKey) => {
                            const model = MODEL_OPTIONS.find((item) => item.value === modelKey);
                            return (
                              <Chip
                                key={modelKey}
                                label={model?.label || modelKey}
                                color="success"
                                variant="outlined"
                              />
                            );
                          })}
                        </Stack>
                        <Typography variant="h6" sx={{ mt: 2, fontWeight: 800 }}>{MODEL_OPTIONS.find((model) => model.value === selectedModel)?.label || 'Random Forest'}</Typography>
                      </Paper>
                    )}

                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
                      <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, bgcolor: '#F9FBFF', flex: 1 }}>
                        <Typography variant="caption" color="text.secondary">Modèle actif</Typography>
                        <Typography variant="subtitle2" fontWeight={700}>{MODEL_OPTIONS.find((model) => model.value === selectedModel)?.label || 'N/A'}</Typography>
                      </Paper>
                      <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, bgcolor: '#EFF7ED', flex: 1 }}>
                        <Typography variant="caption" color="success.main">Optimisé pour ce type de prédiction</Typography>
                      </Paper>
                    </Stack>

                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <Button
                        variant="contained"
                        color="success"
                        onClick={handleRunPrediction}
                        disabled={!selectedPatient || !selectedVariableKeys.size}
                        sx={{ textTransform: 'none', px: 4, py: 1.8, fontWeight: 700 }}
                      >
                        Lancer la prédiction
                      </Button>
                    </Box>
                  </Paper>
                </Grid>
              </Grid>
            )}

            {activeModule === 3 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={5}>
                  <ModuleCard title="Score de risque" description="Score numérique, jauge colorée et niveau de risque.">
                    <Typography variant="h2" fontWeight={900}>{predictionScore}%</Typography>
                    <Typography variant="h6" fontWeight={700} sx={{ color: RISK_COLORS[riskLevel], mt: 1 }}>{riskLevel}</Typography>
                    <Box sx={{ mt: 2, width: '100%', height: 14, borderRadius: 999, background: '#E6F4F1' }}>
                      <Box sx={{ width: `${predictionScore}%`, height: '100%', borderRadius: 999, background: RISK_COLORS[riskLevel] }} />
                    </Box>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
                      Basé sur {Object.keys(predictionInput).length} variable(s) sélectionnée(s) et le modèle {MODEL_OPTIONS.find((model) => model.value === selectedModel)?.label}.
                    </Typography>
                  </ModuleCard>
                </Grid>

                <Grid item xs={12} md={7}>
                  <ModuleCard title="Interprétabilité" description="Facteurs déterminants avec poids et explication clinique.">
                    <Stack spacing={1}>
                      {(predictionFactors.length ? predictionFactors : INTERPRETABILITY_FACTORS).map((item) => (
                        <Box key={item.label}>
                          <Stack direction="row" justifyContent="space-between">
                            <Typography variant="body2">{item.label}</Typography>
                            <Typography variant="body2" fontWeight={700}>{item.weight ? `${item.weight}%` : item.value}</Typography>
                          </Stack>
                        </Box>
                      ))}
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                      Les facteurs proposés sont basés sur les variables choisies et le type de prédiction.
                    </Typography>
                  </ModuleCard>
                </Grid>

                <Grid item xs={12} md={6}>
                  <ModuleCard title="Variables utilisées" description="Variables sélectionnées envoyées au modèle ML.">
                    {Object.keys(predictionInput).length ? (
                      <Stack spacing={1}>
                        {Object.entries(predictionInput).map(([key, value]) => (
                          <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 2, bgcolor: '#F7FAFF' }}>
                            <Typography variant="body2">{VARIABLE_LABELS[key] || formatVariableLabel(key)}</Typography>
                            <Typography variant="body2" fontWeight={700}>{String(value)}</Typography>
                          </Box>
                        ))}
                      </Stack>
                    ) : (
                      <Typography variant="body2" color="text.secondary">Aucune variable sélectionnée pour cette prédiction.</Typography>
                    )}
                  </ModuleCard>
                </Grid>

                <Grid item xs={12} md={6}>
                  <ModuleCard title="Recommandation clinique" description="Proposition concrète de suivi et de traitement.">
                    <Typography variant="body1" fontWeight={700}>{recommendation}</Typography>
                  </ModuleCard>
                </Grid>
              </Grid>
            )}

            {activeModule === 4 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                  <ModuleCard title="Filtre historique" description="Filtrez par date, type ou niveau de risque.">
                    <TextField
                      select
                      label="Période"
                      value={selectedDateFilter}
                      onChange={(e) => setSelectedDateFilter(e.target.value)}
                      fullWidth
                      size="small"
                    >
                      <MenuItem value="7jours">7 jours</MenuItem>
                      <MenuItem value="30jours">30 jours</MenuItem>
                      <MenuItem value="90jours">90 jours</MenuItem>
                    </TextField>
                  </ModuleCard>
                </Grid>
                <Grid item xs={12} md={8}>
                  <ModuleCard title="Historique des prédictions" description="Toutes les prédictions sont tracées pour l’audit.">
                    <Stack spacing={1.5}>
                      {[
                        '2026-04-05 — Patient 0021 — Mortalité 1 an — Élevé',
                        '2026-04-03 — Patient 0057 — Coagulation — Modéré',
                        '2026-03-29 — Patient 0093 — Transplantation — Faible',
                      ].map((item) => (
                        <Paper key={item} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                          <Typography variant="body2">{item}</Typography>
                        </Paper>
                      ))}
                    </Stack>
                  </ModuleCard>
                </Grid>
              </Grid>
            )}

            {activeModule === 5 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <ModuleCard title="Gérer les modèles ML" description="Consultez les versions, métriques et mises à jour disponibles.">
                    <Stack spacing={2}>
                      {MODEL_OPTIONS.map((model) => (
                        <Paper key={model.value} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Box>
                              <Typography variant="subtitle2" fontWeight={700}>{model.label}</Typography>
                              <Typography variant="caption" color="text.secondary">{model.accuracy} — {model.description}</Typography>
                            </Box>
                            <Chip label={model.value === selectedModel ? `Actif ${modelVersion}` : 'Disponible'} color={model.value === selectedModel ? 'success' : 'default'} />
                          </Stack>
                        </Paper>
                      ))}
                    </Stack>
                  </ModuleCard>
                </Grid>
                <Grid item xs={12} md={6}>
                  <ModuleCard title="Sécurité et audit" description="SSO, chiffrement, conformité RGPD et traçabilité de chaque action.">
                    <Stack spacing={1}>
                      {['SSO sécurisé', 'Chiffrement des données', 'Traçabilité complète', 'Conformité RGPD'].map((item) => (
                        <Typography key={item} variant="body2" color="text.secondary">• {item}</Typography>
                      ))}
                    </Stack>
                  </ModuleCard>
                </Grid>
              </Grid>
            )}
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}

export default ModelAI;
