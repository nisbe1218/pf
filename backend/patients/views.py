import unicodedata
import uuid
import json

import pandas as pd
from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from openpyxl import Workbook, load_workbook
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminOrChefService

from .models import Patient, PatientFormField, PatientFormTemplate
from .serializers import PatientFormTemplateSerializer, PatientSerializer


STANDARD_FIELD_ALIASES = {
	'nom': 'nom',
	'last_name': 'nom',
	'surname': 'nom',
	'prenom': 'prenom',
	'first_name': 'prenom',
	'prenom_patient': 'prenom',
	'id_patient_nom': 'nom',
	'id_patient': 'id_patient',
	'patient_id': 'id_patient',
	'id_enregistrement_source': 'id_enregistrement_source',
	'id_site': 'id_site',
	'statut_inclusion': 'statut_inclusion',
	'statut_consentement': 'statut_consentement',
	'date_evaluation_initiale': 'date_evaluation_initiale',
	'utilisateur_saisie': 'utilisateur_saisie',
	'derniere_mise_a_jour': 'derniere_mise_a_jour',
	'age': 'age',
	'age_years': 'age',
	'age_in_years': 'age',
	'patient_age': 'age',
	'years': 'age',
	'dob': 'date_naissance',
	'birthdate': 'date_naissance',
	'date_birth': 'date_naissance',
	'sexe': 'sexe',
	'sex': 'sexe',
	'gender': 'sexe',
	'genre': 'sexe',
	'demographie_sexe': 'sexe',
	'maladie': 'maladie',
	'diagnostic': 'maladie',
	'ckd_etiology': 'maladie',
	'irc_etiologie_principale': 'maladie',
	'telephone': 'telephone',
	'tel': 'telephone',
	'phone': 'telephone',
	'adresse': 'adresse',
	'address': 'adresse',
	'date_naissance': 'date_naissance',
	'demographie_date_naissance': 'date_naissance',
	'naissance': 'date_naissance',
	'date_de_naissance': 'date_naissance',
	'date_of_birth': 'date_naissance',
	'date_admission': 'date_admission',
	'date_d_admission': 'date_admission',
	'dialysis_start_date': 'date_admission',
	'presentation_date_debut_dialyse': 'date_admission',
}

SECTION_FIELD_ALIASES = {
	'age': 'demographie_age_ans',
	'age_years': 'demographie_age_ans',
	'age_in_years': 'demographie_age_ans',
	'patient_age': 'demographie_age_ans',
	'years': 'demographie_age_ans',
	'demographie_age': 'demographie_age_ans',
	'demographie_age_years': 'demographie_age_ans',
	'demographic_age': 'demographie_age_ans',
	'demographic_age_years': 'demographie_age_ans',
	'demography_age': 'demographie_age_ans',
	'demography_age_years': 'demographie_age_ans',
	'gender': 'demographie_sexe',
	'sex': 'demographie_sexe',
	'dob': 'demographie_date_naissance',
	'birth_date': 'demographie_date_naissance',
	'date_of_birth': 'demographie_date_naissance',
	'birthdate': 'demographie_date_naissance',
	'marital_status': 'demographie_statut_matrimonial',
	'residence_zone': 'demographie_zone_residence',
	'distance_to_center_km': 'demographie_distance_centre_km',
	'social_coverage': 'demographie_couverture_sociale',
	'lifestyle': 'demographie_mode_vie',
	'professional_status': 'demographie_statut_professionnel',
	'education_level': 'demographie_niveau_education',
	'smoking_status': 'demographie_tabagisme',
	'alcohol_status': 'demographie_alcool',
	'first_nephrology_contact_date': 'irc_date_premier_contact_nephrologique',
	'ckd_etiology': 'irc_etiologie_principale',
	'primary_etiology': 'irc_etiologie_principale',
	'secondary_etiology': 'irc_etiologie_secondaire',
	'hereditary_kidney_disease': 'irc_maladie_renale_hereditaire',
	'family_kidney_history': 'irc_antecedents_familiaux_renaux',
	'renal_biopsy_status': 'irc_statut_biopsie_renale',
	'renal_biopsy_result': 'irc_resultat_biopsie_renale',
	'known_before_dialysis': 'irc_connue_avant_dialyse',
	'diabetes_status': 'comorbidite_statut_diabete',
	'comorbidities': 'comorbidite_liste',
	'other_comorbidity': 'comorbidite_autre',
	'episode_date': 'presentation_date_episode',
	'start_location': 'presentation_lieu_debut',
	'start_reasons': 'presentation_raisons_debut',
	'symptoms': 'presentation_symptomes',
	'systolic_bp': 'presentation_tas_mmhg',
	'diastolic_bp': 'presentation_tad_mmhg',
	'heart_rate_bpm': 'presentation_frequence_cardiaque_bpm',
	'temperature_c': 'presentation_temperature_c',
	'weight_kg': 'presentation_poids_kg',
	'height_cm': 'presentation_taille_cm',
	'urine_output_ml_day': 'presentation_volume_urinaire_ml_j',
	'sample_date': 'biologie_date_prelevement',
	'urea_g_l': 'biologie_uree_g_l',
	'creatinine_mg_l': 'biologie_creatinine_mg_l',
	'hemoglobin_g_dl': 'biologie_hemoglobine_g_dl',
	'wbc_g_l': 'biologie_leucocytes_g_l',
	'platelets_g_l': 'biologie_plaquettes_g_l',
	'albumin_g_l': 'biologie_albumine_g_l',
	'crp_mg_l': 'biologie_crp_mg_l',
	'sodium_mmol_l': 'biologie_sodium_mmol_l',
	'potassium_mmol_l': 'biologie_potassium_mmol_l',
	'bicarbonate_mmol_l': 'biologie_bicarbonates_mmol_l',
	'calcium_corrected_mg_l': 'biologie_calcium_corrige_mg_l',
	'phosphorus_mg_l': 'biologie_phosphore_mg_l',
	'pth_pg_ml': 'biologie_pth_pg_ml',
	'ferritin_ng_ml': 'biologie_ferritine_ng_ml',
	'tsat_pct': 'biologie_saturation_transferrine_pct',
	'vitamin_d_ng_ml': 'biologie_vitamine_d_ng_ml',
	'proteinuria_g_24h': 'biologie_proteinurie_g_24h',
	'hba1c_pct': 'biologie_hba1c_pct',
	'dialysis_start_date': 'dialyse_date_debut',
	'initial_dialysis_modality': 'dialyse_modalite_initiale',
	'current_dialysis_modality': 'dialyse_modalite_actuelle',
	'sessions_per_week': 'dialyse_seances_par_semaine',
	'session_duration_min': 'dialyse_duree_seance_min',
	'outcome_status': 'devenir_statut',
	'last_followup_date': 'devenir_date_dernier_suivi',
	'death_date': 'devenir_date_deces',
	'cause_of_death': 'devenir_cause_deces',
	'death': 'devenir_statut',
	'transplantation': 'devenir_statut',
	'urea_baseline': 'biologie_uree_g_l',
	'creatinine_baseline': 'biologie_creatinine_mg_l',
	'hemoglobin_baseline': 'biologie_hemoglobine_g_dl',
	'sodium_baseline': 'biologie_sodium_mmol_l',
	'potassium_baseline': 'biologie_potassium_mmol_l',
	'bicarbonate_baseline': 'biologie_bicarbonates_mmol_l',
	'calcium_baseline': 'biologie_calcium_corrige_mg_l',
	'albumin_baseline': 'biologie_albumine_g_l',
	'phosphorus_baseline': 'biologie_phosphore_mg_l',
	'pth_baseline': 'biologie_pth_pg_ml',
	'ferritin_baseline': 'biologie_ferritine_ng_ml',
	'vitamin_d_baseline': 'biologie_vitamine_d_ng_ml',
	'initial_access_type': 'dialyse_type_acces_initial',
	'transplant_information': 'dialyse_information_transplantation_donnee',
	'kidney_biopsy': 'irc_statut_biopsie_renale',
	'dialysis_planned_start': 'irc_contexte_debut_dialyse',
	'dialysis_emergency_start': 'irc_contexte_debut_dialyse',
	'switch_hd_to_pd': 'complication_changement_modalite_dialyse',
	'switch_pd_to_hd': 'complication_changement_modalite_dialyse',
	'hospitalization_count': 'complication_nombre_hospitalisations',
	'urine_status': 'presentation_statut_diurese',
	'initial_vascular_access': 'dialyse_type_acces_initial',
	'death_cause': 'devenir_cause_deces',
	'ckd_etiology_grouped': 'irc_etiologie_principale',
}

ENGLISH_SECTION_PREFIX_MAP = {
	'demographic_': 'demographie_',
	'demographics_': 'demographie_',
	'ckd_': 'irc_',
	'comorbidity_': 'comorbidite_',
	'comorbidities_': 'comorbidite_',
	'presentation_': 'presentation_',
	'biology_': 'biologie_',
	'biological_': 'biologie_',
	'lab_': 'biologie_',
	'laboratory_': 'biologie_',
	'imaging_': 'imagerie_',
	'dialysis_': 'dialyse_',
	'quality_': 'qualite_',
	'complication_': 'complication_',
	'treatment_': 'traitement_',
	'outcome_': 'devenir_',
}

SECTION_SUFFIX_ALIASES = {
	'gender': 'sexe',
	'sex': 'sexe',
	'birth_date': 'date_naissance',
	'date_of_birth': 'date_naissance',
	'marital_status': 'statut_matrimonial',
	'residence_zone': 'zone_residence',
	'distance_to_center_km': 'distance_centre_km',
	'social_coverage': 'couverture_sociale',
	'lifestyle': 'mode_vie',
	'professional_status': 'statut_professionnel',
	'education_level': 'niveau_education',
	'smoking_status': 'tabagisme',
	'alcohol_status': 'alcool',
	'primary_etiology': 'etiologie_principale',
	'secondary_etiology': 'etiologie_secondaire',
	'start_location': 'lieu_debut',
	'start_reasons': 'raisons_debut',
	'systolic_bp': 'tas_mmhg',
	'diastolic_bp': 'tad_mmhg',
	'heart_rate_bpm': 'frequence_cardiaque_bpm',
	'weight_kg': 'poids_kg',
	'height_cm': 'taille_cm',
	'urine_output_ml_day': 'volume_urinaire_ml_j',
	'sample_date': 'date_prelevement',
	'hemoglobin_g_dl': 'hemoglobine_g_dl',
	'wbc_g_l': 'leucocytes_g_l',
	'platelets_g_l': 'plaquettes_g_l',
	'albumin_g_l': 'albumine_g_l',
	'bicarbonate_mmol_l': 'bicarbonates_mmol_l',
	'calcium_corrected_mg_l': 'calcium_corrige_mg_l',
	'phosphorus_mg_l': 'phosphore_mg_l',
	'tsat_pct': 'saturation_transferrine_pct',
	'vitamin_d_ng_ml': 'vitamine_d_ng_ml',
	'proteinuria_g_24h': 'proteinurie_g_24h',
	'outcome_status': 'statut',
	'last_followup_date': 'date_dernier_suivi',
	'death_date': 'date_deces',
	'cause_of_death': 'cause_deces',
}

SECTION_PREFIX_MAP = {
	'demographie_': 'demographie_data',
	'irc_': 'irc_data',
	'comorbidite_': 'comorbidite_data',
	'presentation_': 'presentation_data',
	'biologie_': 'biologie_data',
	'imagerie_': 'imagerie_data',
	'dialyse_': 'dialyse_data',
	'qualite_': 'qualite_data',
	'complication_': 'complication_data',
	'traitement_': 'traitement_data',
	'devenir_': 'devenir_data',
}

TYPE_MAP = {
	'texte libre court': 'text_short',
	'texte libre': 'text_short',
	'texte libre long': 'text_long',
	'liste a choix unique': 'single_choice',
	'liste a choix multiple': 'multiple_choice',
	'selecteur de date': 'date',
	'nombre entier': 'integer',
	'nombre decimal': 'decimal',
	'oui/non': 'boolean',
	'genere automatiquement': 'auto',
}

TEMPLATE_KEYWORDS = {
	'texte libre court',
	'texte libre long',
	'liste a choix unique',
	'liste a choix multiple',
	'selecteur de date',
	'nombre entier',
	'oui/non',
	'genere automatiquement',
}

SOCIAL_COVERAGE_CODE_MAP = {
	'0': 'auto_paiement',
	'1': 'assistance_publique',
	'2': 'amo',
	'3': 'autre',
	'self_pay': 'auto_paiement',
	'ramed': 'assistance_publique',
	'amo': 'amo',
	'public_insurance_other': 'autre',
}

CKD_ETIOLOGY_CODE_MAP = {
	'1': 'nephropathie_diabetique',
	'2': 'indeterminee',
	'3': 'vascularite',
	'4': 'polykystose_renale',
	'5': 'nephroangiosclerose_hypertensive',
	'6': 'uropathie_obstructive',
	'7': 'nephrite_lupique',
	'8': 'glomerulonephrite_chronique',
	'9': 'glomerulonephrite_chronique',
	'10': 'glomerulonephrite_chronique',
	'11': 'amylose_ou_myelome',
	'12': 'glomerulonephrite_chronique',
	'13': 'autre',
	'14': 'glomerulonephrite_chronique',
	'15': 'autre',
	'diabetic_nephropathy': 'nephropathie_diabetique',
	'indeterminate_nephropathy': 'indeterminee',
	'anca_vasculitis': 'vascularite',
	'polycystic_kidney_disease': 'polykystose_renale',
	'nephroangiosclerosis': 'nephroangiosclerose_hypertensive',
	'obstructive_uropathy': 'uropathie_obstructive',
	'lupus_nephropathy': 'nephrite_lupique',
	'membranous_glomerulonephritis': 'glomerulonephrite_chronique',
	'iga_nephropathy': 'glomerulonephrite_chronique',
	'igm_hsf': 'glomerulonephrite_chronique',
	'amyloidosis_myeloma': 'amylose_ou_myelome',
	'crescentic_gn': 'glomerulonephrite_chronique',
	'hemolytic_uremic_syndrome': 'autre',
	'c3_glomerulopathy': 'glomerulonephrite_chronique',
	'cortical_necrosis': 'autre',
}

CKD_ETIOLOGY_GROUPED_CODE_MAP = {
	'1': 'nephropathie_diabetique',
	'2': 'nephroangiosclerose_hypertensive',
	'3': 'polykystose_renale',
	'4': 'uropathie_obstructive',
	'5': 'nephrite_lupique',
	'6': 'vascularite',
	'7': 'glomerulonephrite_chronique',
	'8': 'autre',
	'9': 'indeterminee',
	'diabetes': 'nephropathie_diabetique',
	'nas': 'nephroangiosclerose_hypertensive',
	'polycystic': 'polykystose_renale',
	'obstructive': 'uropathie_obstructive',
	'lupus': 'nephrite_lupique',
	'vasculitis': 'vascularite',
	'other_glomerular': 'glomerulonephrite_chronique',
	'other': 'autre',
	'indeterminate': 'indeterminee',
}

INITIAL_VASCULAR_ACCESS_CODE_MAP = {
	'1': 'cathetere_non_tunnellise',
	'2': 'cathetere_tunnellise',
	'3': 'fistule_arterioveineuse',
	'catheter': 'cathetere_non_tunnellise',
	'tunneled_catheter': 'cathetere_tunnellise',
	'arteriovenous_fistula': 'fistule_arterioveineuse',
}

URINE_STATUS_CODE_MAP = {
	'1': 'anurique',
	'2': 'diurese_preservee',
	'anuric': 'anurique',
	'preserved_diuresis': 'diurese_preservee',
}

DEATH_CAUSE_CODE_MAP = {
	'1': 'cardiovasculaire',
	'2': 'infection',
	'3': 'hemorragie',
	'4': 'autre',
	'5': 'inconnue',
	'cardiovascular': 'cardiovasculaire',
	'infection': 'infection',
	'hemorrhagic': 'hemorragie',
	'other': 'autre',
	'indeterminate': 'inconnue',
}

FIXED_CLASSEUR_TEMPLATE_NAMES = [
	'template',
	'template_patients_hd',
	'plateform_donnees_complete',
	'classeur1',
]

AUTO_INCREMENT_FIELD_PREFIX = {
	'id_patient': 'PAT',
	'id_enregistrement_source': 'SRC',
}

POSTGRES_MODEL_FIELD_MAP = {
	'id_patient': 'id_patient',
	'id_enregistrement_source': 'id_enregistrement_source',
	'id_site': 'id_site',
	'statut_inclusion': 'statut_inclusion',
	'statut_consentement': 'statut_consentement',
	'utilisateur_saisie': 'utilisateur_saisie',
	'derniere_mise_a_jour': 'derniere_mise_a_jour',
	'date_evaluation_initiale': 'date_evaluation_initiale',
	'nom': 'nom',
	'prenom': 'prenom',
	'age': 'age',
	'sexe': 'sexe',
	'maladie': 'maladie',
	'telephone': 'telephone',
	'adresse': 'adresse',
	'date_naissance': 'date_naissance',
	'date_admission': 'date_admission',
}

POSTGRES_SECTION_BUCKETS = [
	('demographie_', 'demographie_data'),
	('irc_', 'irc_data'),
	('comorbidite_', 'comorbidite_data'),
	('presentation_', 'presentation_data'),
	('biologie_', 'biologie_data'),
	('imagerie_', 'imagerie_data'),
	('dialyse_', 'dialyse_data'),
	('qualite_', 'qualite_data'),
	('complication_', 'complication_data'),
	('traitement_', 'traitement_data'),
	('devenir_', 'devenir_data'),
]


def _pg_quote_identifier(value):
	return '"' + str(value).replace('"', '""') + '"'


def _pg_quote_literal(value):
	return "'" + str(value).replace("'", "''") + "'"


def refresh_postgres_flat_view(template=None):
	if template is None:
		template = PatientFormTemplate.objects.filter(name__iexact='template').order_by('-id').first()
		if template is None:
			template = PatientFormTemplate.objects.order_by('-id').first()

	if template is None:
		return

	keys = list(template.fields.order_by('order', 'id').values_list('key', flat=True))
	if not keys:
		return

	select_parts = ['p.id AS id']
	for key in keys:
		if key in POSTGRES_MODEL_FIELD_MAP:
			expr = f"p.{POSTGRES_MODEL_FIELD_MAP[key]}"
		else:
			bucket = None
			for prefix, column_name in POSTGRES_SECTION_BUCKETS:
				if key.startswith(prefix):
					bucket = column_name
					break

			if bucket:
				expr = f"p.{bucket} ->> {_pg_quote_literal(key)}"
			else:
				expr = f"p.extra_data ->> {_pg_quote_literal(key)}"

		select_parts.append(f"{expr} AS {_pg_quote_identifier(key)}")

	sql = (
		'CREATE OR REPLACE VIEW public.patients_plateforme_flat AS '
		'SELECT ' + ', '.join(select_parts) + ' FROM patients_patient p'
	)

	with connection.cursor() as cursor:
		cursor.execute(sql)


def normalize_header(value):
	text = unicodedata.normalize('NFKD', str(value).strip().lower())
	text = text.encode('ascii', 'ignore').decode('ascii')
	return text.replace(' ', '_').replace('-', '_')


def convert_excel_value(value):
	if pd.isna(value):
		return None

	if hasattr(value, 'item') and not isinstance(value, (str, bytes)):
		try:
			value = value.item()
		except Exception:
			pass

	if hasattr(value, 'to_pydatetime'):
		return value.to_pydatetime().date().isoformat()

	if hasattr(value, 'date') and not isinstance(value, str):
		try:
			return value.date().isoformat()
		except Exception:
			return str(value)

	if isinstance(value, (int, float)) and float(value).is_integer():
		return int(value)

	if hasattr(value, 'isoformat') and not isinstance(value, str):
		try:
			return value.isoformat()
		except Exception:
			pass

	return value


def normalize_type(value):
	normalized = normalize_header(value).replace('_', ' ')
	return TYPE_MAP.get(normalized, 'text_short')


def resolve_mapped_field(normalized_key):
	if normalized_key in STANDARD_FIELD_ALIASES:
		return STANDARD_FIELD_ALIASES[normalized_key]

	# Similar-name fallback mapping for machine exports.
	if 'sex' in normalized_key or normalized_key.endswith('_sexe'):
		return 'sexe'
	if 'age' in normalized_key and any(token in normalized_key for token in ['year', 'ans', 'annee']):
		return 'age'
	if any(token in normalized_key for token in ['birth', 'naissance']) and 'date' in normalized_key:
		return 'date_naissance'
	if any(token in normalized_key for token in ['dialysis_start', 'debut_dialyse', 'admission']):
		return 'date_admission'
	if any(token in normalized_key for token in ['etiology', 'etiologie', 'diagnostic']):
		return 'maladie'

	return None


def resolve_section_field_key(normalized_key):
	if normalized_key in SECTION_FIELD_ALIASES:
		return SECTION_FIELD_ALIASES[normalized_key]

	for english_prefix, french_prefix in ENGLISH_SECTION_PREFIX_MAP.items():
		if normalized_key.startswith(english_prefix):
			suffix = normalized_key[len(english_prefix):]
			mapped_suffix = SECTION_SUFFIX_ALIASES.get(suffix, suffix)
			return f'{french_prefix}{mapped_suffix}'

	return None


def parse_flexible_date(value):
	if value is None:
		return None

	text = str(value).strip()
	if not text:
		return None

	parsed = parse_date(text)
	if parsed:
		return parsed.isoformat()

	for dayfirst in [True, False]:
		try:
			dt = pd.to_datetime(text, errors='coerce', dayfirst=dayfirst)
			if pd.notna(dt):
				return dt.date().isoformat()
		except Exception:
			continue

	return None


def normalize_age_value(value):
	if value in [None, '']:
		return None

	try:
		age_value = int(float(str(value).strip()))
		if age_value < 0:
			return None
		return age_value
	except Exception:
		return None


def derive_age_from_date_of_birth(date_iso):
	if not date_iso:
		return None

	birth_date = parse_date(str(date_iso))
	if not birth_date:
		return None

	today = timezone.localdate()
	age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
	return age if age >= 0 else None


def derive_date_of_birth_from_age(age_value):
	normalized_age = normalize_age_value(age_value)
	if normalized_age is None:
		return None

	# Age only provides a year estimate, not an exact birth date.
	# Avoid creating a misleading full date with today’s month/day.
	target_year = timezone.localdate().year - normalized_age
	return f"{target_year}-01-01"


def normalize_sex_values(value):
	if value is None:
		return None, None

	normalized = normalize_header(value)
	if normalized in ['1', 'm', 'male', 'masculin', 'homme', 'man']:
		return 'M', 'homme'
	if normalized in ['0', 'f', 'female', 'feminin', 'femme', 'woman']:
		return 'F', 'femme'
	if normalized in ['i', 'intersex', 'intersexe']:
		return 'O', 'intersexe'
	if normalized in ['unknown', 'inconnu', 'na', 'n_a', 'none', 'null', '']:
		return 'O', 'inconnu'

	return 'O', 'inconnu'


def _is_truthy(value):
	if isinstance(value, bool):
		return value
	normalized = normalize_header(value)
	return normalized in ['1', 'true', 'yes', 'oui', 'y']


def _is_falsey(value):
	if isinstance(value, bool):
		return not value
	normalized = normalize_header(value)
	return normalized in ['0', 'false', 'no', 'non', 'aucun', 'none', 'null', 'na', 'n_a', '']


def normalize_section_value(section_key, value, source_key=None):
	if value is None:
		return value

	source_key = source_key or ''
	normalized_value = normalize_header(value)
	if section_key == 'demographie_sexe':
		_, section_value = normalize_sex_values(value)
		return section_value

	if section_key == 'demographie_date_naissance':
		parsed_value = parse_flexible_date(value)
		return parsed_value or value

	if 'date' in section_key:
		parsed_value = parse_flexible_date(value)
		if parsed_value:
			return parsed_value
		if _is_falsey(value):
			return None
		return value

	if section_key == 'demographie_couverture_sociale' and source_key == 'social_coverage':
		return SOCIAL_COVERAGE_CODE_MAP.get(normalized_value, value)

	if section_key == 'irc_etiologie_principale':
		if source_key == 'ckd_etiology':
			return CKD_ETIOLOGY_CODE_MAP.get(normalized_value, value)
		if source_key == 'ckd_etiology_grouped':
			return CKD_ETIOLOGY_GROUPED_CODE_MAP.get(normalized_value, value)

	if section_key == 'dialyse_type_acces_initial':
		if source_key in ['initial_vascular_access', 'initial_access_type']:
			return INITIAL_VASCULAR_ACCESS_CODE_MAP.get(normalized_value, value)

	if section_key == 'presentation_statut_diurese' and source_key == 'urine_status':
		return URINE_STATUS_CODE_MAP.get(normalized_value, value)

	if section_key == 'devenir_cause_deces' and source_key in ['death_cause', 'cause_of_death']:
		return DEATH_CAUSE_CODE_MAP.get(normalized_value, value)

	if section_key == 'devenir_statut':
		if source_key == 'death':
			if normalized_value in ['9', 'unknown', 'inconnu']:
				return 'perdu_de_vue'
			return 'decede' if _is_truthy(value) else 'vivant_sous_dialyse'
		if source_key == 'transplantation':
			return 'transplante' if _is_truthy(value) else 'vivant_sous_dialyse'

	if section_key == 'irc_statut_biopsie_renale' and source_key == 'kidney_biopsy':
		return 'realisee_concluante' if _is_truthy(value) else 'non_realisee'

	if section_key == 'irc_contexte_debut_dialyse':
		if source_key == 'dialysis_planned_start' and _is_truthy(value):
			return 'debut_planifie'
		if source_key == 'dialysis_emergency_start' and _is_truthy(value):
			return 'debut_en_urgence'

	if section_key == 'complication_changement_modalite_dialyse':
		if source_key == 'switch_hd_to_pd':
			return 'hemodialyse_vers_dialyse_peritoneale' if _is_truthy(value) else 'aucun'
		if source_key == 'switch_pd_to_hd':
			return 'dialyse_peritoneale_vers_hemodialyse' if _is_truthy(value) else 'aucun'

	return value


def is_schema_template_sheet(worksheet):
	if worksheet.max_row < 2:
		return False

	type_cells = [worksheet.cell(2, col_index).value for col_index in range(1, worksheet.max_column + 1)]
	normalized_types = {
		normalize_header(cell).replace('_', ' ')
		for cell in type_cells
		if cell is not None and str(cell).strip()
	}
	return bool(normalized_types.intersection(TEMPLATE_KEYWORDS))


def create_or_update_template(worksheet, source_file_name):
	template_name = (worksheet.title if worksheet else None) or 'Patient Schema'
	template, _ = PatientFormTemplate.objects.update_or_create(
		name=template_name,
		defaults={
			'source_file_name': source_file_name or template_name,
			'sheet_name': worksheet.title if worksheet else template_name,
		},
	)
	return template


def parse_schema_from_template_sheet(worksheet, source_file_name):
	template = create_or_update_template(worksheet, source_file_name)
	template.fields.all().delete()

	created_fields = []
	for column_index in range(1, worksheet.max_column + 1):
		header = worksheet.cell(1, column_index).value
		type_label = worksheet.cell(2, column_index).value
		if not header:
			continue

		choices = []
		for row_index in range(3, worksheet.max_row + 1):
			value = worksheet.cell(row_index, column_index).value
			if value is not None and str(value).strip():
				choices.append(str(value).strip())

		field_type = normalize_type(type_label)
		created_fields.append(
			PatientFormField(
				template=template,
				key=normalize_header(header),
				label=str(header).strip(),
				field_type=field_type,
				order=column_index,
				choices=choices,
				source_hint=str(type_label or ''),
				is_required=field_type not in ['auto'],
			)
		)

	PatientFormField.objects.bulk_create(created_fields)
	# Keep the SQL projection aligned with current Django/template columns.
	try:
		refresh_postgres_flat_view(template)
	except Exception:
		pass
	return template, len(created_fields)


def upsert_template_from_headers(headers, worksheet, source_file_name):
	template = None
	for template_name in FIXED_CLASSEUR_TEMPLATE_NAMES:
		template = (
			PatientFormTemplate.objects.filter(name__iexact=template_name).order_by('-id').first()
			or PatientFormTemplate.objects.filter(sheet_name__iexact=template_name).order_by('-id').first()
		)
		if template:
			break

	if template is None:
		template = create_or_update_template(worksheet, source_file_name)
	else:
		if source_file_name:
			template.source_file_name = source_file_name
		if worksheet and getattr(worksheet, 'title', None):
			template.sheet_name = worksheet.title
		template.save(update_fields=['source_file_name', 'sheet_name'])

	existing_fields = {field.key: field for field in template.fields.all()}

	for index, header in enumerate(headers, start=1):
		if not header:
			continue

		header_str = str(header).strip()
		if not header_str or header_str.lower().startswith('unnamed'):
			continue

		key = normalize_header(header_str)
		if not key or key.startswith('unnamed') or key in existing_fields:
			continue

		PatientFormField.objects.create(
			template=template,
			key=key,
			label=str(header).strip(),
			field_type='text_short',
			order=index,
			choices=[],
			source_hint='auto_detected_from_data_import',
			is_required=False,
		)

	try:
		refresh_postgres_flat_view(template)
	except Exception:
		pass

	return template


def build_patient_payload(row):
	payload = {'extra_data': {}}

	for column_name, raw_value in row.items():
		value = convert_excel_value(raw_value)
		if value is None:
			continue

		normalized = normalize_header(column_name)
		section_field = None
		for prefix, section_bucket in SECTION_PREFIX_MAP.items():
			if normalized.startswith(prefix):
				section_field = section_bucket
				break

		resolved_section_key = resolve_section_field_key(normalized)
		if resolved_section_key and not section_field:
			for prefix, section_bucket in SECTION_PREFIX_MAP.items():
				if resolved_section_key.startswith(prefix):
					section_field = section_bucket
					break

		# Keep section-specific keys filled so Classeur1 columns always get their values.
		if section_field:
			payload.setdefault(section_field, {})
			target_key = resolved_section_key or normalized
			payload[section_field][target_key] = normalize_section_value(target_key, value, normalized)

		if normalized.startswith('unnamed'):
			continue

		mapped_field = resolve_mapped_field(normalized)
		if not mapped_field and resolved_section_key:
			mapped_field = resolve_mapped_field(resolved_section_key)

		if mapped_field:
			payload[mapped_field] = value
		elif not section_field:
			payload['extra_data'][normalized] = value

	if 'date_naissance' in payload:
		parsed_date = parse_flexible_date(payload.get('date_naissance'))
		if parsed_date:
			payload['date_naissance'] = parsed_date
		else:
			payload.pop('date_naissance', None)

	if 'age' in payload:
		normalized_age = normalize_age_value(payload.get('age'))
		if normalized_age is not None:
			payload['age'] = normalized_age
		else:
			payload.pop('age', None)

	if payload.get('age') is not None and not payload.get('date_naissance'):
		derived_birth_date = derive_date_of_birth_from_age(payload.get('age'))
		if derived_birth_date:
			payload['date_naissance'] = derived_birth_date
			payload['_date_naissance_estimee'] = True

	if payload.get('date_naissance') and 'age' not in payload:
		derived_age = derive_age_from_date_of_birth(payload.get('date_naissance'))
		if derived_age is not None:
			payload['age'] = derived_age

	demographie_data = payload.get('demographie_data') or {}
	demographie_age = normalize_age_value(demographie_data.get('demographie_age_ans'))
	if demographie_age is not None:
		demographie_data['demographie_age_ans'] = demographie_age
		payload['age'] = demographie_age
	elif payload.get('age') is not None:
		demographie_data['demographie_age_ans'] = payload['age']
	if demographie_data:
		payload['demographie_data'] = demographie_data

	if payload.get('date_naissance'):
		demographie_data = payload.get('demographie_data') or {}
		if not demographie_data.get('demographie_date_naissance'):
			if payload.get('_date_naissance_estimee'):
				demographie_data['demographie_date_naissance'] = str(payload['date_naissance'])[:4]
			else:
				demographie_data['demographie_date_naissance'] = payload['date_naissance']
		payload['demographie_data'] = demographie_data
		payload.pop('_date_naissance_estimee', None)

	if 'date_admission' in payload:
		parsed_date = parse_flexible_date(payload.get('date_admission'))
		if parsed_date:
			payload['date_admission'] = parsed_date
		else:
			payload.pop('date_admission', None)

	if 'date_evaluation_initiale' in payload:
		parsed_date = parse_flexible_date(payload.get('date_evaluation_initiale'))
		if parsed_date:
			payload['date_evaluation_initiale'] = parsed_date
		else:
			payload.pop('date_evaluation_initiale', None)

	if 'sexe' in payload:
		patient_sex, _ = normalize_sex_values(payload.get('sexe'))
		if patient_sex:
			payload['sexe'] = patient_sex
		else:
			payload.pop('sexe', None)

	return payload


def ensure_required_identity_fields(payload):
	extra_data = payload.get('extra_data') or {}
	identifier = payload.get('id_patient') or payload.get('id_enregistrement_source') or extra_data.get('id_patient')

	if not payload.get('id_patient') and identifier:
		payload['id_patient'] = str(identifier)

	nom_value = payload.get('nom')
	if nom_value is None or str(nom_value).strip() == '':
		payload['nom'] = ''

	prenom_value = payload.get('prenom')
	if prenom_value is None or str(prenom_value).strip() == '':
		payload['prenom'] = ''

	if payload.get('sexe'):
		normalized_patient_sex, _ = normalize_sex_values(payload.get('sexe'))
		payload['sexe'] = normalized_patient_sex or 'O'

	demo_data = payload.get('demographie_data') or {}
	if demo_data.get('demographie_sexe'):
		_, normalized_demo_sex = normalize_sex_values(demo_data.get('demographie_sexe'))
		demo_data['demographie_sexe'] = normalized_demo_sex
	payload['demographie_data'] = demo_data

	payload['extra_data'] = extra_data
	return payload


def _extract_numeric_suffix(value):
	if value is None:
		return None

	text = str(value).strip()
	digits = ''.join(character for character in text if character.isdigit())
	if not digits:
		return None

	try:
		return int(digits)
	except ValueError:
		return None


def generate_next_incremental_identifier(model_field, prefix):
	max_number = 0
	for current_value in Patient.objects.values_list(model_field, flat=True):
		numeric_value = _extract_numeric_suffix(current_value)
		if numeric_value and numeric_value > max_number:
			max_number = numeric_value

	next_number = max_number + 1
	return f"{prefix}{next_number:06d}"


def generate_next_numeric_patient_id(auto_increment_state=None):
	if auto_increment_state is not None:
		auto_increment_state['id_patient'] = auto_increment_state.get('id_patient', 0) + 1
		return str(auto_increment_state['id_patient'])

	max_number = 0
	for current_value in Patient.objects.values_list('id_patient', flat=True):
		numeric_value = _extract_numeric_suffix(current_value)
		if numeric_value and numeric_value > max_number:
			max_number = numeric_value

	return str(max_number + 1)


def initialize_auto_increment_state():
	state = {}
	for model_field in AUTO_INCREMENT_FIELD_PREFIX:
		max_number = 0
		for current_value in Patient.objects.values_list(model_field, flat=True):
			numeric_value = _extract_numeric_suffix(current_value)
			if numeric_value and numeric_value > max_number:
				max_number = numeric_value
		state[model_field] = max_number
	return state


def resolve_entry_user_label(user):
	if not user or not getattr(user, 'is_authenticated', False):
		return 'system_import'

	for attr in ['username', 'email']:
		value = getattr(user, attr, None)
		if value:
			return str(value)

	return str(getattr(user, 'id', 'system_import'))


def ensure_incremental_identifiers(payload, auto_increment_state=None, force_generated=False):
	if force_generated:
		payload['id_patient'] = generate_next_numeric_patient_id(auto_increment_state=auto_increment_state)
		if auto_increment_state is not None:
			auto_increment_state['id_enregistrement_source'] = auto_increment_state.get('id_enregistrement_source', 0) + 1
			payload['id_enregistrement_source'] = f"{AUTO_INCREMENT_FIELD_PREFIX['id_enregistrement_source']}{auto_increment_state['id_enregistrement_source']:06d}"
		else:
			payload['id_enregistrement_source'] = generate_next_incremental_identifier(
				'id_enregistrement_source',
				AUTO_INCREMENT_FIELD_PREFIX['id_enregistrement_source'],
			)
		return payload

	if not payload.get('id_patient'):
		payload['id_patient'] = generate_next_numeric_patient_id(auto_increment_state=auto_increment_state)

	return payload


def apply_automatic_schema_fields(payload, auto_increment_state=None, current_user=None):
	template = PatientFormTemplate.objects.order_by('-id').first()
	if not template:
		return payload

	extra_data = payload.get('extra_data') or {}
	for field in template.fields.filter(field_type='auto'):
		if field.key in STANDARD_FIELD_ALIASES:
			mapped = STANDARD_FIELD_ALIASES[field.key]
			if not payload.get(mapped):
				if mapped in AUTO_INCREMENT_FIELD_PREFIX:
					if mapped == 'id_patient':
						payload[mapped] = generate_next_numeric_patient_id(auto_increment_state=auto_increment_state)
					elif auto_increment_state is not None:
						auto_increment_state[mapped] = auto_increment_state.get(mapped, 0) + 1
						payload[mapped] = f"{AUTO_INCREMENT_FIELD_PREFIX[mapped]}{auto_increment_state[mapped]:06d}"
					else:
						payload[mapped] = generate_next_incremental_identifier(mapped, AUTO_INCREMENT_FIELD_PREFIX[mapped])
				elif mapped == 'utilisateur_saisie':
						payload[mapped] = resolve_entry_user_label(current_user)
				elif mapped == 'derniere_mise_a_jour':
					payload[mapped] = timezone.now().isoformat()
				else:
					payload[mapped] = f"{field.key}_{uuid.uuid4().hex[:10]}"
		else:
			section_field = None
			for prefix, section_bucket in SECTION_PREFIX_MAP.items():
				if field.key.startswith(prefix):
					section_field = section_bucket
					break

			if section_field:
				payload.setdefault(section_field, {})
				if not payload[section_field].get(field.key):
					payload[section_field][field.key] = f"{field.key}_{uuid.uuid4().hex[:10]}"
			elif not extra_data.get(field.key):
				extra_data[field.key] = f"{field.key}_{uuid.uuid4().hex[:10]}"

	payload['extra_data'] = extra_data
	return payload


class PatientListCreateView(APIView):
	permission_classes = [IsAdminOrChefService]

	def get_queryset(self, request):
		queryset = Patient.objects.all()

		search = request.query_params.get('search', '').strip()
		id_patient = request.query_params.get('id_patient', '').strip()
		sexe = request.query_params.get('sexe', '').strip()
		age_min = request.query_params.get('age_min', '').strip()
		age_max = request.query_params.get('age_max', '').strip()
		date_naissance = request.query_params.get('date_naissance', '').strip()
		date_naissance_from = request.query_params.get('date_naissance_from', '').strip()
		date_naissance_to = request.query_params.get('date_naissance_to', '').strip()
		statut_inclusion = request.query_params.get('statut_inclusion', '').strip()
		infection = request.query_params.get('infection', '').strip().lower()
		hemorrhage = request.query_params.get('hemorrhage', '').strip().lower()
		avf_created = request.query_params.get('avf_created', '').strip().lower()

		if search:
			queryset = queryset.filter(
				Q(nom__icontains=search)
				| Q(prenom__icontains=search)
				| Q(id_patient__icontains=search)
				| Q(maladie__icontains=search)
				| Q(telephone__icontains=search)
				| Q(adresse__icontains=search)
			)

		if id_patient:
			queryset = queryset.filter(id_patient__icontains=id_patient)

		if sexe:
			queryset = queryset.filter(sexe__iexact=sexe)

		if age_min:
			queryset = queryset.filter(age__gte=age_min)

		if age_max:
			queryset = queryset.filter(age__lte=age_max)

		if date_naissance:
			queryset = queryset.filter(date_naissance=date_naissance)

		if date_naissance_from:
			queryset = queryset.filter(date_naissance__gte=date_naissance_from)

		if date_naissance_to:
			queryset = queryset.filter(date_naissance__lte=date_naissance_to)

		if statut_inclusion:
			queryset = queryset.filter(statut_inclusion__icontains=statut_inclusion)

		def apply_boolean_extra_filter(current_queryset, key, value):
			if value == 'oui':
				return current_queryset.filter(
					Q(**{f'extra_data__{key}': 1})
					| Q(**{f'extra_data__{key}': '1'})
					| Q(**{f'extra_data__{key}': True})
					| Q(**{f'extra_data__{key}__iexact': 'true'})
					| Q(**{f'extra_data__{key}__iexact': 'yes'})
					| Q(**{f'extra_data__{key}__iexact': 'oui'})
				)
			if value == 'non':
				return current_queryset.filter(
					Q(**{f'extra_data__{key}': 0})
					| Q(**{f'extra_data__{key}': '0'})
					| Q(**{f'extra_data__{key}': False})
					| Q(**{f'extra_data__{key}__iexact': 'false'})
					| Q(**{f'extra_data__{key}__iexact': 'no'})
					| Q(**{f'extra_data__{key}__iexact': 'non'})
				)
			return current_queryset

		queryset = apply_boolean_extra_filter(queryset, 'infection', infection)
		queryset = apply_boolean_extra_filter(queryset, 'hemorrhage', hemorrhage)
		queryset = apply_boolean_extra_filter(queryset, 'avf_created', avf_created)

		return queryset

	def get(self, request):
		serializer = PatientSerializer(self.get_queryset(request), many=True)
		return Response(serializer.data)

	def post(self, request):
		payload = request.data.copy()
		payload = apply_automatic_schema_fields(payload, current_user=request.user)
		payload = ensure_incremental_identifiers(payload)
		serializer = PatientSerializer(data=payload)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatientExportExcelView(APIView):
	permission_classes = [IsAdminOrChefService]

	def get_queryset(self, request):
		queryset = Patient.objects.all()

		search = request.query_params.get('search', '').strip()
		id_patient = request.query_params.get('id_patient', '').strip()
		sexe = request.query_params.get('sexe', '').strip()
		age_min = request.query_params.get('age_min', '').strip()
		age_max = request.query_params.get('age_max', '').strip()
		date_naissance = request.query_params.get('date_naissance', '').strip()
		date_naissance_from = request.query_params.get('date_naissance_from', '').strip()
		date_naissance_to = request.query_params.get('date_naissance_to', '').strip()
		statut_inclusion = request.query_params.get('statut_inclusion', '').strip()
		infection = request.query_params.get('infection', '').strip().lower()
		hemorrhage = request.query_params.get('hemorrhage', '').strip().lower()
		avf_created = request.query_params.get('avf_created', '').strip().lower()

		if search:
			queryset = queryset.filter(
				Q(nom__icontains=search)
				| Q(prenom__icontains=search)
				| Q(id_patient__icontains=search)
				| Q(maladie__icontains=search)
				| Q(telephone__icontains=search)
				| Q(adresse__icontains=search)
			)

		if id_patient:
			queryset = queryset.filter(id_patient__icontains=id_patient)

		if sexe:
			queryset = queryset.filter(sexe__iexact=sexe)

		if age_min:
			queryset = queryset.filter(age__gte=age_min)

		if age_max:
			queryset = queryset.filter(age__lte=age_max)

		if date_naissance:
			queryset = queryset.filter(date_naissance=date_naissance)

		if date_naissance_from:
			queryset = queryset.filter(date_naissance__gte=date_naissance_from)

		if date_naissance_to:
			queryset = queryset.filter(date_naissance__lte=date_naissance_to)

		if statut_inclusion:
			queryset = queryset.filter(statut_inclusion__icontains=statut_inclusion)

		def apply_boolean_extra_filter(current_queryset, key, value):
			if value == 'oui':
				return current_queryset.filter(
					Q(**{f'extra_data__{key}': 1})
					| Q(**{f'extra_data__{key}': '1'})
					| Q(**{f'extra_data__{key}': True})
					| Q(**{f'extra_data__{key}__iexact': 'true'})
					| Q(**{f'extra_data__{key}__iexact': 'yes'})
					| Q(**{f'extra_data__{key}__iexact': 'oui'})
				)
			if value == 'non':
				return current_queryset.filter(
					Q(**{f'extra_data__{key}': 0})
					| Q(**{f'extra_data__{key}': '0'})
					| Q(**{f'extra_data__{key}': False})
					| Q(**{f'extra_data__{key}__iexact': 'false'})
					| Q(**{f'extra_data__{key}__iexact': 'no'})
					| Q(**{f'extra_data__{key}__iexact': 'non'})
				)
			return current_queryset

		queryset = apply_boolean_extra_filter(queryset, 'infection', infection)
		queryset = apply_boolean_extra_filter(queryset, 'hemorrhage', hemorrhage)
		queryset = apply_boolean_extra_filter(queryset, 'avf_created', avf_created)

		return queryset

	def get(self, request):
		queryset = self.get_queryset(request)

		workbook = Workbook()
		worksheet = workbook.active
		worksheet.title = 'patients'

		template = None
		for template_name in FIXED_CLASSEUR_TEMPLATE_NAMES:
			template = (
				PatientFormTemplate.objects.filter(name__iexact=template_name).order_by('-id').first()
				or PatientFormTemplate.objects.filter(sheet_name__iexact=template_name).order_by('-id').first()
			)
			if template:
				break

		if not template:
			template = PatientFormTemplate.objects.order_by('-id').first()

		schema_keys = []
		if template:
			schema_keys = [field.key for field in template.fields.order_by('order', 'id')]

		extra_keys = set()
		for patient in queryset.iterator():
			for key in (patient.extra_data or {}).keys():
				if key not in schema_keys:
					extra_keys.add(key)

		dynamic_keys = sorted(extra_keys)

		base_keys = [
			'id',
			'id_patient',
			'nom',
			'prenom',
			'age',
		]

		headers = base_keys + [key for key in schema_keys if key not in base_keys] + dynamic_keys
		worksheet.append(headers)

		model_field_map = {
			'nom': 'nom',
			'prenom': 'prenom',
			'age': 'age',
			'sexe': 'sexe',
			'maladie': 'maladie',
			'telephone': 'telephone',
			'adresse': 'adresse',
			'date_naissance': 'date_naissance',
			'date_admission': 'date_admission',
			'id_patient': 'id_patient',
			'id_enregistrement_source': 'id_enregistrement_source',
			'id_site': 'id_site',
			'statut_inclusion': 'statut_inclusion',
			'statut_consentement': 'statut_consentement',
			'date_evaluation_initiale': 'date_evaluation_initiale',
			'utilisateur_saisie': 'utilisateur_saisie',
			'derniere_mise_a_jour': 'derniere_mise_a_jour',
		}

		def serialize_cell(value):
			if value is None:
				return ''
			if hasattr(value, 'isoformat'):
				try:
					return value.isoformat()
				except Exception:
					return str(value)
			if isinstance(value, (dict, list)):
				return json.dumps(value, ensure_ascii=False)
			return value

		def resolve_schema_value(patient, key):
			if key == 'id':
				return patient.id

			if key in model_field_map:
				return getattr(patient, model_field_map[key], '')

			for prefix, section_bucket in SECTION_PREFIX_MAP.items():
				if key.startswith(prefix):
					return (getattr(patient, section_bucket, {}) or {}).get(key, '')

			return (patient.extra_data or {}).get(key, '')

		for patient in queryset.iterator():
			row = [serialize_cell(resolve_schema_value(patient, key)) for key in headers]
			worksheet.append(row)

		response = HttpResponse(
			content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		)
		response['Content-Disposition'] = f'attachment; filename="patients_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
		workbook.save(response)
		return response


class PatientDetailView(APIView):
	permission_classes = [IsAdminOrChefService]

	def get_object(self, pk):
		return get_object_or_404(Patient, pk=pk)

	def get(self, request, pk):
		serializer = PatientSerializer(self.get_object(pk))
		return Response(serializer.data)

	def put(self, request, pk):
		serializer = PatientSerializer(self.get_object(pk), data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def patch(self, request, pk):
		serializer = PatientSerializer(self.get_object(pk), data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request, pk):
		self.get_object(pk).delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class PatientBulkPurgeView(APIView):
	permission_classes = [IsAdminOrChefService]

	def delete(self, request):
		deleted_count, _ = Patient.objects.all().delete()
		return Response({'deleted_count': deleted_count}, status=status.HTTP_200_OK)


class PatientImportExcelView(APIView):
	permission_classes = [IsAdminOrChefService]
	parser_classes = [MultiPartParser, FormParser]

	def post(self, request):
		excel_file = request.FILES.get('file')
		if not excel_file:
			return Response({'error': 'Fichier Excel requis'}, status=status.HTTP_400_BAD_REQUEST)

		source_file_name = getattr(excel_file, 'name', '')
		lower_name = str(source_file_name).lower()
		worksheet = None
		dataframe = None

		if lower_name.endswith('.xls'):
			try:
				excel_file.seek(0)
				dataframe = pd.read_excel(excel_file, engine='xlrd')
			except Exception as error:
				return Response({'error': f'Impossible de lire le fichier Excel (.xls): {error}'}, status=status.HTTP_400_BAD_REQUEST)
		else:
			try:
				excel_file.seek(0)
				workbook = load_workbook(excel_file, data_only=False)
			except Exception as error:
				return Response({'error': f'Impossible de lire le fichier Excel: {error}'}, status=status.HTTP_400_BAD_REQUEST)

			worksheet = workbook[workbook.sheetnames[0]]

			if is_schema_template_sheet(worksheet):
				template, fields_created = parse_schema_from_template_sheet(worksheet, source_file_name)
				template_data = PatientFormTemplateSerializer(template).data
				return Response(
					{
						'mode': 'schema',
						'template': template_data,
						'fields_created': fields_created,
						'patients_created': 0,
						'errors': [],
					},
					status=status.HTTP_201_CREATED,
				)

			try:
				excel_file.seek(0)
				dataframe = pd.read_excel(excel_file)
			except Exception as error:
				return Response({'error': f'Impossible de lire les donnees du fichier Excel: {error}'}, status=status.HTTP_400_BAD_REQUEST)
		if dataframe is not None:
			dataframe = dataframe.loc[:, ~dataframe.columns.astype(str).str.match(r'^(Unnamed|unnamed)(:.*)?$')]

		headers = list(dataframe.columns)
		template = upsert_template_from_headers(headers, worksheet, source_file_name)

		created_count = 0
		row_errors = []
		auto_increment_state = initialize_auto_increment_state()
		for index, row in dataframe.iterrows():
			payload = build_patient_payload(row)
			payload = apply_automatic_schema_fields(payload, auto_increment_state=auto_increment_state, current_user=request.user)
			payload = ensure_required_identity_fields(payload)
			payload = ensure_incremental_identifiers(
				payload,
				auto_increment_state=auto_increment_state,
				force_generated=True,
			)
			serializer = PatientSerializer(data=payload)
			if serializer.is_valid():
				serializer.save()
				created_count += 1
			else:
				row_errors.append({'row': index + 2, 'errors': serializer.errors})

		template_data = PatientFormTemplateSerializer(template).data
		status_code = status.HTTP_201_CREATED if created_count else status.HTTP_200_OK
		return Response(
			{
				'mode': 'data',
				'template': template_data,
				'fields_created': len(template_data.get('fields', [])),
				'patients_created': created_count,
				'errors': row_errors,
			},
			status=status_code,
		)


class PatientSchemaView(APIView):
	permission_classes = [IsAdminOrChefService]

	def get(self, request):
		template = None
		for template_name in FIXED_CLASSEUR_TEMPLATE_NAMES:
			template = (
				PatientFormTemplate.objects.filter(name__iexact=template_name).order_by('-id').first()
				or PatientFormTemplate.objects.filter(sheet_name__iexact=template_name).order_by('-id').first()
			)
			if template:
				break

		if not template:
			template = PatientFormTemplate.objects.order_by('-id').first()

		if not template:
			return Response({'template': None})
		return Response({'template': PatientFormTemplateSerializer(template).data})


class PatientPlateformeFlatView(APIView):
	permission_classes = [IsAdminOrChefService]

	def get(self, request):
		limit = request.query_params.get('limit')
		try:
			limit = int(limit) if limit is not None else None
		except ValueError:
			limit = None

		with connection.cursor() as cursor:
			if limit is None:
				cursor.execute('SELECT * FROM patients_plateforme_flat')
			else:
				cursor.execute('SELECT * FROM patients_plateforme_flat LIMIT %s', [limit])
			columns = [col[0] for col in cursor.description]
			rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

		return Response(rows)
