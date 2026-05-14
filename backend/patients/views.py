import unicodedata
import re
import uuid
import json
import os
import io
from datetime import datetime, timedelta
from urllib import request as urllib_request
from urllib import error as urllib_error

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

from users.permissions import IsAdminOrChefService, CanViewPatients
from rest_framework.permissions import AllowAny
from audit.models import AuditLog

from .models import Patient, PatientFormField, PatientFormTemplate
from .serializers import PatientFormTemplateSerializer, PatientSerializer


# ============================================================
# FONCTIONS UTILITAIRES DE BASE
# ============================================================

def normalize_header(value):
    text = unicodedata.normalize('NFKD', str(value).strip().lower())
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def _format_patient_audit_value(value):
    if value in [None, '']:
        return '-'
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except Exception:
            return str(value)
    return str(value)


def _describe_patient_changes(before_data, after_data, max_changes=5):
    changes = []
    before_data = before_data or {}
    after_data = after_data or {}

    keys = sorted(set(before_data.keys()) | set(after_data.keys()))
    for key in keys:
        if key in {'id', 'created_at', 'updated_at'}:
            continue
        before_value = _format_patient_audit_value(before_data.get(key))
        after_value = _format_patient_audit_value(after_data.get(key))
        if before_value == after_value:
            continue
        changes.append(f"{key}: {before_value} -> {after_value}")
        if len(changes) >= max_changes:
            break

    if not changes:
        return "aucun champ notable modifié"

    remaining = max(0, len(keys) - len(changes))
    suffix = f" (+{remaining} autre(s) champ(s))" if remaining > 0 else ''
    return '; '.join(changes) + suffix


# Plage raisonnable de serial Excel : du 01/01/1990 au 31/12/2099
_EXCEL_SERIAL_MIN = 32874   # 01/01/1990
_EXCEL_SERIAL_MAX = 73050   # 31/12/2099
_EXCEL_EPOCH = datetime(1899, 12, 30)


def excel_serial_to_date_iso(value):
    """Convertit un serial Excel (entier) en chaîne ISO YYYY-MM-DD, ou None si hors plage."""
    try:
        ival = int(float(value))
        if _EXCEL_SERIAL_MIN <= ival <= _EXCEL_SERIAL_MAX:
            return (_EXCEL_EPOCH + timedelta(days=ival)).date().isoformat()
    except (ValueError, TypeError):
        pass
    return None


def convert_excel_value(value):
    if pd.isna(value):
        return None

    if hasattr(value, 'item') and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except Exception:
            pass

    # Objet datetime/date pandas ou Python
    if hasattr(value, 'to_pydatetime'):
        return value.to_pydatetime().date().isoformat()

    if hasattr(value, 'date') and not isinstance(value, str):
        try:
            return value.date().isoformat()
        except Exception:
            return str(value)

    # Entier ou flottant
    if isinstance(value, (int, float)):
        fval = float(value)
        if fval != fval:  # NaN
            return None
        if fval.is_integer():
            ival = int(fval)
            # Essayer la conversion serial Excel avant de retourner l'entier brut
            date_iso = excel_serial_to_date_iso(ival)
            if date_iso:
                return date_iso
            return ival
        return fval

    if hasattr(value, 'isoformat') and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            pass

    # Chaîne : tenter de détecter un serial ou une date texte
    if isinstance(value, str):
        stripped = value.strip()
        # Chaîne purement numérique → tester serial Excel
        if stripped.isdigit():
            date_iso = excel_serial_to_date_iso(int(stripped))
            if date_iso:
                return date_iso
        return stripped

    return value


def normalize_type(value):
    normalized = normalize_header(value).replace('_', ' ')
    TYPE_MAP = {
        'texte libre court': 'text_short',
        'texte libre long': 'text_long',
        'liste a choix unique': 'single_choice',
        'liste a choix multiple': 'multiple_choice',
        'selecteur de date': 'date',
        'nombre entier': 'integer',
        'nombre decimal': 'decimal',
        'oui/non': 'boolean',
        'genere automatiquement': 'auto',
    }
    return TYPE_MAP.get(normalized, 'text_short')


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
    target_year = timezone.localdate().year - normalized_age
    return f"{target_year}-01-01"


def normalize_sex_values(value):
    if value is None:
        return None, None

    value_str = str(value).strip().lower()

    if value_str in ['1', '1.0']:
        return 'M', 'homme'
    if value_str in ['0', '0.0']:
        return 'F', 'femme'

    normalized = normalize_header(value_str)
    if normalized in ['m', 'male', 'masculin', 'homme', 'man']:
        return 'M', 'homme'
    if normalized in ['f', 'female', 'feminin', 'femme', 'woman']:
        return 'F', 'femme'
    if normalized in ['i', 'intersex', 'intersexe']:
        return 'O', 'intersexe'
    if normalized in ['unknown', 'inconnu', 'na', 'n_a', 'none', 'null', '', '9', '9.0']:
        return 'O', 'inconnu'
    return 'O', 'inconnu'


# ============================================================
# DÉCODAGE DES VALEURS NUMÉRIQUES CODÉES
# ============================================================

# Tables de correspondance complètes (issues du fichier Excel de référence)
_DECODE_MAPS = {
    # Démographie
    'sexe': {1: 'homme', 0: 'femme'},
    'demographie_sexe': {1: 'homme', 0: 'femme'},
    'couverture_sociale': {
        0: 'auto_paiement',
        1: 'ramed',
        2: 'amo',
        3: 'autre_assurance_publique',
    },
    'demographie_couverture_sociale': {
        0: 'auto_paiement',
        1: 'ramed',
        2: 'amo',
        3: 'autre_assurance_publique',
    },

    # IRC / étiologie
    'etiologie_mrc': {
        1: 'nephropathie_diabetique',
        2: 'nephropathie_indeterminee',
        3: 'vascularite_anca',
        4: 'maladie_renale_polykystique',
        5: 'nephroangiosclerose',
        6: 'uropathie_obstructive',
        7: 'nephropathie_lupique',
        8: 'glomerulonephrite_membraneuse',
        9: 'nephropathie_a_iga',
        10: 'lgm_hsf',
        11: 'amylose_myelome',
        12: 'gn_crescentique',
        13: 'syndrome_hemolytique_et_uremique',
        14: 'glomerulopathie_c3',
        15: 'necrose_corticale',
    },
    'irc_etiologie_principale': {
        1: 'nephropathie_diabetique',
        2: 'nephropathie_indeterminee',
        3: 'vascularite_anca',
        4: 'maladie_renale_polykystique',
        5: 'nephroangiosclerose',
        6: 'uropathie_obstructive',
        7: 'nephropathie_lupique',
        8: 'glomerulonephrite_membraneuse',
        9: 'nephropathie_a_iga',
        10: 'lgm_hsf',
        11: 'amylose_myelome',
        12: 'gn_crescentique',
        13: 'syndrome_hemolytique_et_uremique',
        14: 'glomerulopathie_c3',
        15: 'necrose_corticale',
    },
    'groupe_etiologie_mrc': {
        1: 'diabete',
        2: 'nephroangiosclerose',
        3: 'polykystose',
        4: 'uropathie_obstructive',
        5: 'lupus',
        6: 'vascularite',
        7: 'autre_glomerulaire',
        8: 'autre',
        9: 'indeterminee',
    },

    # Dialyse
    'type_acces_initial': {
        1: 'cathetere_femoral',
        2: 'cathetere_tunnellise',
        3: 'fistule_arterioveineuse',
        4: 'cathetere_peritoneal',
    },
    'dialyse_type_acces_initial': {
        1: 'cathetere_femoral',
        2: 'cathetere_tunnellise',
        3: 'fistule_arterioveineuse',
        4: 'cathetere_peritoneal',
    },
    'fistule_arterioveineuse': {1: 'oui', 0: 'non'},
    'fistule_arterioveineuse_c': {1: 'oui', 0: 'non'},
    'groupe_jours_entre_cathetere': {
        0: 'pas_d_intervalle',
        1: '0_30_jours',
        2: '31_181_jours',
        3: 'plus_de_180_jours',
    },
    'dialyse_jours_entre_catheter_et_fav': {
        0: 'pas_d_intervalle',
        1: '0_30_jours',
        2: '31_181_jours',
        3: 'plus_de_180_jours',
    },

    # Statut diurèse
    'statut_diurese': {1: 'anurique', 2: 'diurese_preservee'},
    'presentation_statut_diurese': {1: 'anurique', 2: 'diurese_preservee'},

    # Devenir / décès
    'deces': {1: 'oui', 0: 'non', 9: 'inconnu'},
    'cause_deces': {
        1: 'cardiovasculaire',
        2: 'infection',
        3: 'hemorragique',
        4: 'autre',
        5: 'indeterminee',
    },
    'devenir_cause_deces': {
        1: 'cardiovasculaire',
        2: 'infection',
        3: 'hemorragique',
        4: 'autre',
        5: 'indeterminee',
    },
}

# Colonnes déjà fusionnées dans comorbidite_liste — ne doivent jamais apparaître
# comme colonnes séparées dans la structure de la plateforme
_COLUMNS_FUSED_INTO_COMORBIDITE_LISTE = {
    'exposition_toxique',
    'comorbidite_exposition_toxique',
    'antecedents_medicaments_nephrotoxiques',
    'comorbidite_antecedents_medicaments_nephrotoxiques',
}

# Colonnes booléennes simples (1 → oui, 0 → non)
_BOOLEAN_COLUMNS = {
    'hypertension', 'cardiopathie', 'hemodialyse', 'dialyse_peritoneale',
    'debut_dialyse_urgence', 'debut_dialyse_planifie',
    'cause_deces_cardiaque', 'cause_deces_infectieuse',
    'irc_maladie_renale_hereditaire', 'irc_antecedents_familiaux_renaux',
    'irc_connue_avant_dialyse',
    'dialyse_information_transplantation_donnee',
    'irc_themes_education_therapeutique',
    'biopsie_renale', 'maladie_renale_hereditaire',
    'uropathie_obstructive', 'goutte', 'exposition_toxique',
    'antecedents_medicaments_nephrotoxiques',
    'asthenie', 'douleur_abdominale', 'nausees', 'prurit',
    'asymptomatique', 'trouble_conscience',
    'infection', 'trouble_electrolytique', 'evenement_cardiovasculaire',
    'hemorragie', 'dysfonction_acces', 'crise_convulsive',
    'information_transplantation', 'information_transplantation_donnee',
    'liste_attente_transplantation', 'transplantation_renale',
    'immunisation_transfusion_sanguine', 'bilan_pretransplantation',
    'debut_dialyse_urgence', 'debut_dialyse_planifie',
    'changement_hd_vers_dp', 'changement_dp_vers_hd',
}

def is_binary_column(column_data):
    """
    Détermine si une colonne est binaire (contient uniquement 0/1 et variantes).
    column_data: liste des valeurs de la colonne (non None)
    Retourne True si toutes les valeurs non vides sont 0 ou 1 (ou 0.0/1.0)
    """
    if not column_data:
        return False
    
    for value in column_data:
        if value is None or value == '':
            continue
        
        try:
            # Convertir en float pour gérer 0.0 et 1.0
            num_value = float(value)
            if num_value not in (0.0, 1.0):
                return False
        except (ValueError, TypeError):
            # Si ce n'est pas un nombre, ce n'est pas binaire
            return False
    
    return True
def decode_numeric_value(column_name, value):
    """Convertit les valeurs numériques codées en libellés textuels."""
    if value is None or value == '':
        return value

    col = normalize_header(str(column_name))

    # Chercher dans les tables de décodage
    decode_map = _DECODE_MAPS.get(col)
    if decode_map:
        try:
            return decode_map.get(int(float(value)), value)
        except (ValueError, TypeError):
            return value

    # Colonnes booléennes simples
    if col in _BOOLEAN_COLUMNS:
        try:
            val_int = int(float(value))
            return 'oui' if val_int == 1 else 'non'
        except (ValueError, TypeError):
            return value

    # Détection générique : si la valeur est strictement 0 ou 1 (entier), convertir en oui/non
    try:
        val_str = str(value).strip()
        if val_str in ('0', '1'):
            return 'oui' if val_str == '1' else 'non'
    except Exception:
        pass

    return value


def extract_charlson_score(value):
    """Extrait le score Charlson d'une valeur potentiellement mal formatée."""
    if value is None or value == '':
        return None

    str_value = str(value).strip()

    try:
        return int(float(str_value))
    except (ValueError, TypeError):
        pass

    numbers = re.findall(r'\d+', str_value)
    if numbers:
        return int(numbers[0])

    return None


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


def _pg_quote_identifier(value):
    return '"' + str(value).replace('"', '""') + '"'


def _pg_quote_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


# ============================================================
# CHARGEMENT AUTOMATIQUE DU MAPPING DEPUIS column_mapping.json
# ============================================================

def load_column_mapping():
    """Charge le mapping depuis le fichier JSON."""
    mapping_file = os.path.join(os.path.dirname(__file__), 'column_mapping.json')
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_list = json.load(f)

        column_mapping = {}
        for item in mapping_list:
            main_key = normalize_header(item['main'])
            platform_key = normalize_header(item['platform'])
            transformation = item['transformation']

            if transformation == 'direct':
                transform_type = 'direct'
            elif transformation == 'calcul (age → date naissance estimée)':
                transform_type = 'calcul_age_to_birthdate'
            elif transformation in [
                'fusion (urgence/planifié → contexte)',
                'fusion (hd/dp → modalité)',
                'fusion (cardiaque/infectieux → cause)',
                'fusion (hd→dp / dp→hd → changement)',
            ]:
                transform_type = transformation
            elif 'fusion' in transformation or 'inclus dans' in transformation:
                transform_type = transformation
            else:
                transform_type = 'direct'

            column_mapping[main_key] = {
                'platform': platform_key,
                'type': transform_type,
                'original_main': item['main'],
                'original_platform': item['platform'],
            }

        return column_mapping
    except Exception as e:
        print(f"Erreur chargement mapping: {e}")
        return get_default_mapping()


def get_default_mapping():
    """Mapping par défaut — couvre les colonnes les plus fréquentes."""
    return {
        'identifiant_patient': {'platform': 'id_patient', 'type': 'direct'},
        'sexe': {'platform': 'demographie_sexe', 'type': 'direct'},
        'age_annees': {'platform': 'demographie_date_naissance', 'type': 'calcul_age_to_birthdate'},
        'distance_au_centre': {'platform': 'demographie_distance_centre_km', 'type': 'direct'},
        'etiologie_mrc': {'platform': 'irc_etiologie_principale', 'type': 'direct'},
        'charlson': {'platform': 'icc_charlson', 'type': 'direct'},
        'icc_charlson': {'platform': 'icc_charlson', 'type': 'direct'},
        # --- Dates de dialyse (variantes de nommage) ---
        'date_debut_dialyse': {'platform': 'dialyse_date_debut', 'type': 'direct'},
        'date_debut': {'platform': 'dialyse_date_debut', 'type': 'direct'},
        'dialyse_date_debut': {'platform': 'dialyse_date_debut', 'type': 'direct'},
        'date_demarrage_dialyse': {'platform': 'dialyse_date_debut', 'type': 'direct'},
        'debut_dialyse': {'platform': 'dialyse_date_debut', 'type': 'direct'},
        # --- Comorbidités ---
        'hypertension': {'platform': 'comorbidite_liste', 'type': 'fusion (valeurs multiples → liste)'},
        'cardiopathie': {'platform': 'comorbidite_liste', 'type': 'fusion (valeurs multiples → liste)'},
        # --- Dialyse modalité ---
        'hemodialyse': {'platform': 'dialyse_modalite_initiale', 'type': 'fusion (hd/dp → modalité)'},
        'dialyse_peritoneale': {'platform': 'dialyse_modalite_initiale', 'type': 'fusion (hd/dp → modalité)'},
        # --- Contexte début dialyse ---
        'debut_dialyse_urgence': {'platform': 'irc_contexte_debut_dialyse', 'type': 'fusion (urgence/planifié → contexte)'},
        'debut_dialyse_planifie': {'platform': 'irc_contexte_debut_dialyse', 'type': 'fusion (urgence/planifié → contexte)'},
        # --- Devenir ---
        'deces': {'platform': 'devenir_statut', 'type': 'inclus dans statut devenir'},
        'cause_deces_cardiaque': {'platform': 'devenir_cause_deces', 'type': 'fusion (cardiaque/infectieux → cause)'},
        'cause_deces_infectieuse': {'platform': 'devenir_cause_deces', 'type': 'fusion (cardiaque/infectieux → cause)'},
    }


# Charger le mapping au démarrage
COLUMN_MAPPING = load_column_mapping()

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

FIXED_CLASSEUR_TEMPLATE_NAMES = [
    'template',
    'template_patients_hd',
    'plateform_donnees_complete',
    'classeur1',
    'Main',
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


def refresh_postgres_flat_view(template=None):
    if template is None:
        template = PatientFormTemplate.objects.filter(name__iexact='template').order_by('-id').first()
        if template is None:
            template = PatientFormTemplate.objects.order_by('-id').first()

    if template is None:
        return

    keys = [
        key for key in template.fields.order_by('order', 'id').values_list('key', flat=True)
        if key and not key.startswith('unnamed')
    ]
    if not keys:
        return

    fixed_keys = [
        'id_patient', 'nom', 'prenom', 'age', 'sexe', 'maladie',
        'telephone', 'adresse', 'date_naissance', 'date_admission',
        'id_enregistrement_source', 'id_site', 'statut_inclusion',
        'statut_consentement', 'date_evaluation_initiale',
        'utilisateur_saisie', 'derniere_mise_a_jour',
    ]

    select_parts = ['p.id AS id']
    for key in fixed_keys:
        if key in POSTGRES_MODEL_FIELD_MAP:
            select_parts.append(f"p.{POSTGRES_MODEL_FIELD_MAP[key]} AS {_pg_quote_identifier(key)}")

    for key in keys:
        if key in fixed_keys:
            continue
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

    sql_create = (
        'CREATE VIEW public.patients_plateforme_flat AS '
        'SELECT ' + ', '.join(select_parts) + ' FROM patients_patient p'
    )

    with connection.cursor() as cursor:
        # DROP obligatoire : CREATE OR REPLACE ne peut pas renommer des colonnes existantes
        cursor.execute('DROP VIEW IF EXISTS public.patients_plateforme_flat CASCADE')
        cursor.execute(sql_create)


def get_active_template():
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
    return template


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
    try:
        refresh_postgres_flat_view(template)
    except Exception:
        pass
    return template, len(created_fields)


def upsert_template_from_headers(headers, worksheet, source_file_name, create_fields=True):
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

    if not create_fields:
        try:
            refresh_postgres_flat_view(template)
        except Exception:
            pass
        return template

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

        # Ne jamais créer de champ pour les colonnes fusionnées dans comorbidite_liste
        if key in _COLUMNS_FUSED_INTO_COMORBIDITE_LISTE:
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
    # DEBUG: afficher les colonnes une seule fois
    if not hasattr(build_patient_payload, '_cols_printed'):
        print("=== COLONNES DU FICHIER EXCEL ===")
        for i, col in enumerate(row.keys()):
            print(f'  {i}: "{col}"')
        build_patient_payload._cols_printed = True

    payload = {'extra_data': {}}

    # Initialiser les structures par section
    payload.setdefault('demographie_data', {})
    payload.setdefault('irc_data', {})
    payload.setdefault('comorbidite_data', {})
    payload.setdefault('presentation_data', {})
    payload.setdefault('biologie_data', {})
    payload.setdefault('dialyse_data', {})
    payload.setdefault('complication_data', {})
    payload.setdefault('devenir_data', {})

    comorbidite_list = []
    presentation_list = []
    complication_list = []

    contexte_dialyse = None
    modalite_dialyse = None
    date_transplantation = None
    cause_deces_value = None
    deces_statut = None
    changement_modalite = False
    age_value = None
    age_column_found = False

    # PARCOURIR TOUTES LES COLONNES
    for column_name, raw_value in row.items():
        value = convert_excel_value(raw_value)
        if value is None:
            continue

        # Décodage numérique AVANT toute autre logique
        value = decode_numeric_value(column_name, value)
        normalized = normalize_header(column_name)

        # === DÉTECTION DE L'ÂGE ===
        if not age_column_found and (
            'age' in normalized
            or normalized in ('ans', 'years', 'age_annees')
        ):
            age_value = normalize_age_value(value)
            if age_value is not None and 0 < age_value < 120:
                payload['age'] = age_value
                payload['demographie_data']['demographie_age_ans'] = age_value
                date_estimee = derive_date_of_birth_from_age(age_value)
                if date_estimee:
                    payload['demographie_data']['demographie_date_naissance'] = date_estimee
                    # Marquer que la date est estimée (calculée depuis l'âge, pas saisie réelle)
                    payload['extra_data']['demographie_date_naissance_estimee'] = True
                age_column_found = True
                print(f"Âge détecté: '{column_name}' = {age_value} ans")
            continue

        # === DÉTECTION CHARLSON ===
        col_name_lower = str(column_name).lower().strip()
        is_charlson = (
            col_name_lower in ['charlson', 'icc_charlson', 'icccharlson', 'score_charlson']
            or str(column_name).strip() in ['Charlson', 'ICC_Charlson', 'ICC_CHARLSON']
            or 'charlson' in col_name_lower
        )

        if is_charlson:
            charlson_val = extract_charlson_score(value)
            if charlson_val is not None:
                payload['icc_charlson'] = str(charlson_val)
                print(f"✅ CHARLSON CAPTURÉ: '{column_name}' → {charlson_val}")
            else:
                print(f"⚠️ Colonne Charlson trouvée mais valeur non extraite: '{raw_value}'")

        # === COLONNES DÉJÀ FUSIONNÉES DANS comorbidite_liste → IGNORER ===
        # (traitées via le mapping fusion, ne doivent pas créer de colonne séparée)
        if normalized in _COLUMNS_FUSED_INTO_COMORBIDITE_LISTE:
            # La fusion est gérée plus bas via COLUMN_MAPPING si la valeur est truthy
            pass

        # === MAPPING STANDARD ===
        mapping = COLUMN_MAPPING.get(normalized)

        if mapping:
            platform_field = mapping['platform']
            transform_type = mapping['type']

            if transform_type == 'direct':
                section_target = None
                for prefix, section_bucket in SECTION_PREFIX_MAP.items():
                    if platform_field.startswith(prefix):
                        section_target = section_bucket
                        break

                if section_target:
                    payload[section_target][platform_field] = value
                else:
                    payload[platform_field] = value

            elif transform_type == 'calcul_age_to_birthdate':
                if not age_column_found:
                    age_value = normalize_age_value(value)
                    if age_value is not None and 0 < age_value < 120:
                        payload['age'] = age_value
                        payload['demographie_data']['demographie_age_ans'] = age_value
                        date_estimee = derive_date_of_birth_from_age(age_value)
                        if date_estimee:
                            payload['demographie_data']['demographie_date_naissance'] = date_estimee
                            # Marquer que la date est estimée (calculée depuis l'âge, pas saisie réelle)
                            payload['extra_data']['demographie_date_naissance_estimee'] = True
                        age_column_found = True

            elif transform_type == 'fusion (urgence/planifié → contexte)':
                if _is_truthy(value):
                    contexte_dialyse = 'debut_en_urgence' if 'urgence' in normalized else 'debut_planifie'

            elif transform_type == 'fusion (hd/dp → modalité)':
                if _is_truthy(value):
                    modalite_dialyse = 'hemodialyse' if 'hemodialyse' in normalized else 'dialyse_peritoneale'

            elif transform_type == 'partiel (oui/non → date)':
                if _is_truthy(value):
                    date_transplantation = timezone.now().date().isoformat()

            elif transform_type == 'fusion (valeurs multiples → liste)' and platform_field == 'comorbidite_liste':
                if _is_truthy(value):
                    label = normalized.replace('_', ' ')
                    if label not in comorbidite_list:
                        comorbidite_list.append(label)
                        print(f"Comorbidité: {label}")

            elif 'symptome' in transform_type.lower() or (
                transform_type == 'fusion (valeurs multiples → liste)'
                and platform_field == 'presentation_symptomes'
            ):
                if _is_truthy(value):
                    label = normalized.replace('_', ' ')
                    if label not in presentation_list:
                        presentation_list.append(label)

            elif 'complication' in transform_type.lower() or (
                transform_type == 'fusion (valeurs multiples → liste)'
                and platform_field == 'complication_liste'
            ):
                if _is_truthy(value):
                    label = normalized.replace('_', ' ')
                    if label not in complication_list:
                        complication_list.append(label)

            elif 'inclus dans thèmes éducation' in transform_type:
                # Ces colonnes sont maintenant ignorées et iront dans extra_data
                # car elles n'ont plus d'entrée dans column_mapping.json
                # On ne fait rien ici, elles seront capturées par le else
                pass

            elif transform_type == 'fusion (cardiaque/infectieux → cause)':
                if _is_truthy(value):
                    if 'cardiaque' in normalized:
                        cause_deces_value = 'cardiovasculaire'
                    elif 'infectieuse' in normalized:
                        cause_deces_value = 'infection'

            elif transform_type == 'inclus dans statut devenir' and platform_field == 'devenir_statut':
                deces_statut = value

            elif 'changement' in transform_type.lower():
                if _is_truthy(value):
                    changement_modalite = True
        else:
            # Colonnes déjà fusionnées → ne jamais créer de colonne séparée
            if normalized in _COLUMNS_FUSED_INTO_COMORBIDITE_LISTE:
                pass
            else:
                # Colonnes non mappées → extra_data (devient une colonne dynamique)
                payload['extra_data'][normalized] = value
                # Mémoriser les noms de colonnes dynamiques pour le rapport d'import
                payload.setdefault('_dynamic_columns_detected', set()).add(normalized)
                print(f"🆕 Colonne dynamique ajoutée: '{column_name}' = {value}")

    # ── Appliquer les fusions ──────────────────────────────────────────────
    if comorbidite_list:
        payload['comorbidite_data']['comorbidite_liste'] = ', '.join(comorbidite_list)

    if presentation_list:
        payload['presentation_data']['presentation_symptomes'] = ', '.join(presentation_list)

    if complication_list:
        payload['complication_data']['complication_liste'] = ', '.join(complication_list)

    if contexte_dialyse:
        payload['irc_data']['irc_contexte_debut_dialyse'] = contexte_dialyse

    if modalite_dialyse:
        payload['dialyse_data']['dialyse_modalite_initiale'] = modalite_dialyse

    if date_transplantation:
        payload['devenir_data']['devenir_date_transplantation'] = date_transplantation

    if cause_deces_value:
        payload['devenir_data']['devenir_cause_deces'] = cause_deces_value

    if deces_statut is not None:
        payload['devenir_data']['devenir_statut'] = (
            'decede' if _is_truthy(deces_statut) else 'vivant_sous_dialyse'
        )

    if changement_modalite:
        payload['complication_data']['complication_changement_modalite_dialyse'] = 'oui'

    # ── Normalisation du sexe ─────────────────────────────────────────────
    if 'demographie_sexe' in payload['demographie_data']:
        dem_sexe = payload['demographie_data']['demographie_sexe']
        patient_sex, demo_sex = normalize_sex_values(dem_sexe)
        if patient_sex:
            payload['sexe'] = patient_sex
        if demo_sex:
            payload['demographie_data']['demographie_sexe'] = demo_sex

    # ── Récapitulatif ────────────────────────────────────────────────────
    if age_column_found:
        print(f"✓ Âge: {age_value} ans")

    if 'icc_charlson' in payload:
        print(f"✅ CHARLSON DANS LE PAYLOAD: {payload['icc_charlson']}")
    else:
        print("❌ Score Charlson NON trouvé dans ce fichier")

    return payload


def ensure_required_identity_fields(payload):
    extra_data = payload.get('extra_data') or {}
    identifier = payload.get('id_patient') or extra_data.get('id_patient')

    if not payload.get('id_patient') and identifier:
        payload['id_patient'] = str(identifier)

    nom_value = payload.get('nom')
    if nom_value is None or str(nom_value).strip() == '':
        payload['nom'] = 'Import_Automatique'

    prenom_value = payload.get('prenom')
    if prenom_value is None or str(prenom_value).strip() == '':
        payload['prenom'] = f"Patient_{payload.get('id_patient', '000')}"

    payload['extra_data'] = extra_data
    return payload


def _extract_numeric_suffix(value):
    """Extrait le dernier bloc de chiffres d'une chaîne (après le dernier tiret ou caractère non-numérique)."""
    if value is None:
        return None
    text = str(value).strip()
    
    # Chercher le dernier bloc de chiffres consécutifs
    digits = ''
    for char in reversed(text):
        if char.isdigit():
            digits = char + digits
        elif digits:
            # On a trouvé un bloc de chiffres, arrêter
            break
    
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
        patient_id = generate_next_numeric_patient_id(auto_increment_state=auto_increment_state)
        payload['id_patient'] = patient_id
        
        # Générer id_enregistrement_source basé sur id_patient pour assurer la synchronisation
        patient_num = _extract_numeric_suffix(patient_id)
        if patient_num is not None:
            payload['id_enregistrement_source'] = (
                f"{AUTO_INCREMENT_FIELD_PREFIX['id_enregistrement_source']}{patient_num:06d}"
            )
        else:
            # Fallback si extraction échoue
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
        if field.key in ['id_patient', 'id_enregistrement_source']:
            continue
    payload['extra_data'] = extra_data

    if 'utilisateur_saisie' not in payload:
        payload['utilisateur_saisie'] = resolve_entry_user_label(current_user)
    if 'derniere_mise_a_jour' not in payload:
        payload['derniere_mise_a_jour'] = timezone.now().isoformat()
    if 'date_evaluation_initiale' not in payload:
        payload['date_evaluation_initiale'] = timezone.now().date().isoformat()

    return payload


PREPROCESS_SESSION_DIR = os.path.join(os.path.dirname(__file__), 'preprocess_sessions')
CRITICAL_PREPROCESS_KEYS = ['nom', 'prenom', 'id_patient']


def _ensure_preprocess_session_dir():
    os.makedirs(PREPROCESS_SESSION_DIR, exist_ok=True)


def _preprocess_session_path(session_id):
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(session_id or ''))
    return os.path.join(PREPROCESS_SESSION_DIR, f'{safe_id}.json')


def _save_preprocess_session(session_payload):
    _ensure_preprocess_session_dir()
    session_id = session_payload.get('id') or uuid.uuid4().hex
    session_payload['id'] = session_id
    session_payload['updated_at'] = timezone.now().isoformat()
    session_path = _preprocess_session_path(session_id)
    with open(session_path, 'w', encoding='utf-8') as handle:
        json.dump(session_payload, handle, ensure_ascii=False)
    return session_payload


def _load_preprocess_session(session_id):
    session_path = _preprocess_session_path(session_id)
    if not os.path.exists(session_path):
        return None
    with open(session_path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def _to_json_compatible(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    return str(value)


def _dataframe_to_rows(dataframe):
    rows = []
    for _, row in dataframe.iterrows():
        payload = {}
        for column in dataframe.columns:
            payload[str(column)] = _to_json_compatible(row[column])
        rows.append(payload)
    return rows


def _rows_to_dataframe(rows, columns=None):
    if not rows:
        return pd.DataFrame(columns=columns or [])
    dataframe = pd.DataFrame(rows)
    if columns:
        for column in columns:
            if column not in dataframe.columns:
                dataframe[column] = None
        dataframe = dataframe[columns]
    return dataframe


def _read_uploaded_dataframe(uploaded_file):
    source_file_name = getattr(uploaded_file, 'name', 'uploaded_file')
    lower_name = str(source_file_name).lower()

    if lower_name.endswith('.csv'):
        uploaded_file.seek(0)
        dataframe = pd.read_csv(uploaded_file)
    elif lower_name.endswith('.xls'):
        uploaded_file.seek(0)
        dataframe = pd.read_excel(uploaded_file, engine='xlrd')
    else:
        uploaded_file.seek(0)
        dataframe = pd.read_excel(uploaded_file, parse_dates=True)

    dataframe = dataframe.loc[:, ~dataframe.columns.astype(str).str.match(r'^(Unnamed|unnamed)(:.*)?$')]
    return dataframe, source_file_name


def _build_technical_profile(dataframe):
    columns_profile = []
    numeric_columns_profile = []
    categorical_columns_profile = []
    total_rows = int(len(dataframe.index))
    total_columns = int(len(dataframe.columns))
    total_cells = total_rows * total_columns
    missing_cells = int(dataframe.isna().sum().sum()) if total_cells else 0
    duplicate_rows = int(dataframe.duplicated().sum()) if total_rows else 0
    duplicate_ratio = round((duplicate_rows / total_rows) * 100, 2) if total_rows else 0.0

    for column in dataframe.columns:
        series = dataframe[column]
        non_null_series = series.dropna()
        missing_count = int(series.isna().sum())
        non_null_count = int(series.notna().sum())
        sample_values = []
        for value in non_null_series.astype(str).head(3).tolist():
            if value not in sample_values:
                sample_values.append(value)

        column_profile = {
            'column': str(column),
            'dtype': str(series.dtype),
            'non_null_count': non_null_count,
            'missing_count': missing_count,
            'missing_pct': round((missing_count / total_rows) * 100, 2) if total_rows else 0.0,
            'sample_values': sample_values,
        }
        columns_profile.append(column_profile)

        if pd.api.types.is_numeric_dtype(series):
            numeric_series = pd.to_numeric(series, errors='coerce').dropna()
            if not numeric_series.empty:
                q1 = float(numeric_series.quantile(0.25))
                q3 = float(numeric_series.quantile(0.75))
                iqr = q3 - q1
                lower_bound = q1 - (1.5 * iqr)
                upper_bound = q3 + (1.5 * iqr)
                outlier_count = int(((numeric_series < lower_bound) | (numeric_series > upper_bound)).sum())
                numeric_columns_profile.append({
                    'column': str(column),
                    'count': int(numeric_series.count()),
                    'mean': round(float(numeric_series.mean()), 4),
                    'std': round(float(numeric_series.std(ddof=0)), 4) if numeric_series.count() > 1 else 0.0,
                    'min': round(float(numeric_series.min()), 4),
                    'q1': round(q1, 4),
                    'median': round(float(numeric_series.median()), 4),
                    'q3': round(q3, 4),
                    'max': round(float(numeric_series.max()), 4),
                    'outlier_count': outlier_count,
                })
        else:
            top_values = non_null_series.astype(str).value_counts().head(5)
            categorical_columns_profile.append({
                'column': str(column),
                'unique_count': int(non_null_series.astype(str).nunique()),
                'top_values': [
                    {'value': str(index), 'count': int(count)}
                    for index, count in top_values.items()
                ],
            })

    return {
        'rows': total_rows,
        'columns': total_columns,
        'total_cells': total_cells,
        'missing_cells': missing_cells,
        'missing_pct': round((missing_cells / total_cells) * 100, 2) if total_cells else 0.0,
        'duplicate_rows': duplicate_rows,
        'duplicate_pct': duplicate_ratio,
        'column_names': [str(column) for column in dataframe.columns.tolist()],
        'columns_profile': columns_profile,
        'numeric_columns_profile': numeric_columns_profile,
        'categorical_columns_profile': categorical_columns_profile,
        'preview_rows': _dataframe_to_rows(dataframe.head(3)),
    }


def _determine_preprocess_route(technical_profile):
    rows = int(technical_profile.get('rows') or 0)
    columns = int(technical_profile.get('columns') or 0)
    missing_pct = float(technical_profile.get('missing_pct') or 0.0)
    duplicate_rows = int(technical_profile.get('duplicate_rows') or 0)
    outlier_total = sum(int(item.get('outlier_count') or 0) for item in (technical_profile.get('numeric_columns_profile') or []))

    fast_model = os.environ.get('OLLAMA_FAST_MODEL', 'qwen2.5:3b-instruct')
    balanced_model = os.environ.get('OLLAMA_BALANCED_MODEL', os.environ.get('OLLAMA_PREPROCESS_MODEL', os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b-instruct')))
    advanced_model = os.environ.get('OLLAMA_ADVANCED_MODEL', 'qwen2.5:14b-instruct')

    timeout_seconds = int(os.environ.get('OLLAMA_TIMEOUT_SECONDS', '420'))
    primary_timeout_seconds = int(os.environ.get('OLLAMA_PRIMARY_TIMEOUT_SECONDS', str(min(timeout_seconds, 180))))
    fallback_timeout_seconds = int(os.environ.get('OLLAMA_FALLBACK_TIMEOUT_SECONDS', str(timeout_seconds)))

    if rows <= 50 and columns <= 15 and missing_pct == 0 and duplicate_rows == 0 and outlier_total == 0:
        return {
            'mode': 'deterministic',
            'label': 'deterministic_only',
            'reason': 'Dataset simple: pas de LLM necessaire.',
            'primary_model': None,
            'fallback_model': None,
            'primary_timeout_seconds': 0,
            'fallback_timeout_seconds': 0,
            'primary_num_predict': 0,
            'fallback_num_predict': 0,
        }

    if rows > 300 or columns > 40 or missing_pct >= 10 or duplicate_rows > 0 or outlier_total > 5:
        return {
            'mode': 'advanced',
            'label': 'advanced_medical',
            'reason': 'Dataset complexe: modele avancé priorisé.',
            'primary_model': advanced_model,
            'fallback_model': balanced_model,
            'primary_timeout_seconds': int(os.environ.get('OLLAMA_ADVANCED_TIMEOUT_SECONDS', str(primary_timeout_seconds))),
            'fallback_timeout_seconds': fallback_timeout_seconds,
            'primary_num_predict': int(os.environ.get('OLLAMA_ADVANCED_NUM_PREDICT', os.environ.get('OLLAMA_NUM_PREDICT', '32'))),
            'fallback_num_predict': int(os.environ.get('OLLAMA_NUM_PREDICT', '32')),
        }

    return {
        'mode': 'balanced',
        'label': 'balanced_default',
        'reason': 'Dataset standard: modele equilibré priorisé.',
        'primary_model': balanced_model,
        'fallback_model': fast_model,
        'primary_timeout_seconds': primary_timeout_seconds,
        'fallback_timeout_seconds': fallback_timeout_seconds,
        'primary_num_predict': int(os.environ.get('OLLAMA_NUM_PREDICT', '32')),
        'fallback_num_predict': int(os.environ.get('OLLAMA_RETRY_NUM_PREDICT', '24')),
    }


def _strip_json_wrappers(response_text):
    text = str(response_text or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*```\s*$', '', text)
    return text.strip()


def _extract_balanced_json_candidate(response_text):
    text = str(response_text or '')
    start_index = None
    stack = []
    in_string = False
    escape_next = False

    for index, character in enumerate(text):
        if start_index is None:
            if character in '{[':
                start_index = index
                stack.append(character)
            continue

        if in_string:
            if escape_next:
                escape_next = False
                continue
            if character == '\\':
                escape_next = True
                continue
            if character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
            continue

        if character in '{[':
            stack.append(character)
            continue

        if character in '}]' and stack:
            opening = stack[-1]
            if (opening == '{' and character == '}') or (opening == '[' and character == ']'):
                stack.pop()
                if not stack:
                    return text[start_index:index + 1]

    return None


def _repair_json_text(response_text):
    cleaned_text = _strip_json_wrappers(response_text)
    candidate_texts = [cleaned_text]

    extracted = _extract_balanced_json_candidate(cleaned_text)
    if extracted and extracted not in candidate_texts:
        candidate_texts.insert(0, extracted)

    repaired_candidates = []
    for candidate in candidate_texts:
        normalized_candidate = candidate.strip()
        repaired_candidates.append(normalized_candidate)
        repaired_candidates.append(re.sub(r',\s*([}\]])', r'\1', normalized_candidate))

    for candidate in repaired_candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    return None


def _parse_llm_analysis_response(raw_response):
    if isinstance(raw_response, dict):
        return raw_response

    response_text = str(raw_response or '').strip()
    if not response_text:
        return {
            'summary': 'Le modele n a retourne aucun contenu exploitable.',
            'issues': [],
            'recommendations': [],
            'correction_plan': {},
            'corrected_preview_rows': [],
            'column_assessment': [],
            'limitations': ['Reponse vide du modele.'],
        }

    parsed = _repair_json_text(response_text)
    if parsed is not None:
        return parsed

    # Dernier recours: tenter de récupérer uniquement la première structure JSON fermée.
    extracted = _extract_balanced_json_candidate(response_text)
    if extracted:
        parsed = _repair_json_text(extracted)
        if parsed is not None:
            return parsed

    return {
        'summary': response_text[:1200],
        'issues': [],
        'recommendations': [],
        'correction_plan': {},
        'corrected_preview_rows': [],
        'column_assessment': [],
        'limitations': ['Le modele a repondu, mais le JSON est invalide.'],
    }


def _build_llm_payload(dataframe, technical_profile):
    max_preview_rows = int(os.environ.get('OLLAMA_PREVIEW_ROWS', '3'))
    max_column_samples = int(os.environ.get('OLLAMA_COLUMN_SAMPLES', '1'))
    max_columns = int(os.environ.get('OLLAMA_MAX_COLUMNS', '40'))
    max_value_chars = int(os.environ.get('OLLAMA_MAX_VALUE_CHARS', '50'))

    def _llm_compact_value(value):
        normalized = _to_json_compatible(value)
        if isinstance(normalized, str) and len(normalized) > max_value_chars:
            return normalized[:max_value_chars] + '...'
        return normalized

    selected_columns = [str(column) for column in list(dataframe.columns)[:max_columns]]
    selected_df = dataframe[selected_columns] if selected_columns else dataframe

    preview_rows = _dataframe_to_rows(selected_df.head(max_preview_rows))
    for row in preview_rows:
        if isinstance(row, dict):
            for key in list(row.keys()):
                row[key] = _llm_compact_value(row.get(key))

    column_samples = {
        str(column): [
            _llm_compact_value(value)
            for value in selected_df[column].dropna().head(max_column_samples).tolist()
        ]
        for column in selected_df.columns
    }

    compact_columns_profile = []
    for column_meta in technical_profile.get('columns_profile', []):
        column_name = str(column_meta.get('name', ''))
        if column_name not in selected_columns:
            continue
        compact_columns_profile.append({
            'name': column_name,
            'dtype': column_meta.get('dtype'),
            'missing_count': column_meta.get('missing_count'),
            'missing_ratio': column_meta.get('missing_ratio'),
            'unique_values': column_meta.get('unique_values'),
        })

    compact_profile = {
        'rows': technical_profile.get('rows'),
        'columns': technical_profile.get('columns'),
        'missing_cells': technical_profile.get('missing_cells'),
        'missing_pct': technical_profile.get('missing_pct'),
        'duplicate_rows': technical_profile.get('duplicate_rows'),
        'duplicate_pct': technical_profile.get('duplicate_pct'),
        'columns_profile': compact_columns_profile,
        'numeric_columns_profile': technical_profile.get('numeric_columns_profile', [])[:12],
        'categorical_columns_profile': technical_profile.get('categorical_columns_profile', [])[:12],
        'preview_rows': technical_profile.get('preview_rows', [])[:max_preview_rows],
    }

    return {
        'pack_type': 'structured_analysis_pack',
        'technical_profile': compact_profile,
        'preview_rows': preview_rows,
        'column_samples': column_samples,
        'meta': {
            'selected_columns_count': len(selected_columns),
            'total_columns_count': int(len(dataframe.columns)),
            'preview_rows_count': len(preview_rows),
            'column_samples_per_column': max_column_samples,
        },
    }


def _shrink_llm_payload(payload, max_columns=20, max_preview_rows=2, max_samples_per_column=1):
    if not isinstance(payload, dict):
        return payload

    shrunk = json.loads(json.dumps(payload, default=str))

    technical_profile = shrunk.get('technical_profile') or {}
    columns_profile = technical_profile.get('columns_profile') or []
    selected_column_names = [
        str(item.get('name'))
        for item in columns_profile[:max_columns]
        if isinstance(item, dict) and item.get('name')
    ]

    technical_profile['columns_profile'] = columns_profile[:max_columns]
    technical_profile['numeric_columns_profile'] = (technical_profile.get('numeric_columns_profile') or [])[:max_columns]
    technical_profile['categorical_columns_profile'] = (technical_profile.get('categorical_columns_profile') or [])[:max_columns]
    technical_profile['preview_rows'] = (technical_profile.get('preview_rows') or [])[:max_preview_rows]

    preview_rows = shrunk.get('preview_rows') or []
    shrunk['preview_rows'] = preview_rows[:max_preview_rows]

    column_samples = shrunk.get('column_samples') or {}
    if selected_column_names:
        filtered_samples = {
            name: (column_samples.get(name) or [])[:max_samples_per_column]
            for name in selected_column_names
        }
    else:
        filtered_samples = {
            str(name): (values or [])[:max_samples_per_column]
            for name, values in list(column_samples.items())[:max_columns]
        }
    shrunk['column_samples'] = filtered_samples

    meta = shrunk.get('meta') or {}
    meta['selected_columns_count'] = len(filtered_samples)
    meta['preview_rows_count'] = len(shrunk['preview_rows'])
    meta['column_samples_per_column'] = max_samples_per_column
    shrunk['meta'] = meta

    return shrunk


def _get_ollama_candidate_bases():
    configured_base = str(os.environ.get('OLLAMA_URL', '')).rstrip('/')
    fallback_base = str(os.environ.get('OLLAMA_FALLBACK_URL', '')).rstrip('/')
    running_in_docker = os.path.exists('/.dockerenv')
    default_base = 'http://ollama:11434' if running_in_docker else 'http://127.0.0.1:11434'

    candidate_bases = []
    for base in [configured_base, fallback_base, default_base]:
        normalized_base = str(base).rstrip('/')
        if normalized_base and normalized_base not in candidate_bases:
            candidate_bases.append(normalized_base)
    return candidate_bases


def _check_ollama_health(timeout_seconds=8):
    endpoint_errors = []
    for ollama_base in _get_ollama_candidate_bases():
        ollama_endpoint = f'{ollama_base}/api/tags'
        req = urllib_request.Request(ollama_endpoint, method='GET')
        try:
            with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
                body = response.read().decode('utf-8')
            payload = json.loads(body)
            models = payload.get('models') if isinstance(payload, dict) else []
            model_names = []
            if isinstance(models, list):
                model_names = [item.get('name') for item in models if isinstance(item, dict) and item.get('name')]
            return {
                'connected': True,
                'base_url': ollama_base,
                'endpoint': ollama_endpoint,
                'models_count': len(model_names),
                'models': model_names[:20],
                'errors': [],
            }
        except urllib_error.HTTPError as error:
            error_body = ''
            try:
                error_body = error.read().decode('utf-8')
            except Exception:
                error_body = ''
            endpoint_errors.append(f'{ollama_endpoint} -> HTTP {error.code}: {error_body or str(error)}')
        except (urllib_error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            endpoint_errors.append(f'{ollama_endpoint} -> {error}')

    return {
        'connected': False,
        'base_url': None,
        'endpoint': None,
        'models_count': 0,
        'models': [],
        'errors': endpoint_errors,
    }


def _build_deterministic_analysis_fallback(dataframe, technical_profile, reason_message):
    rows_count = int(len(dataframe.index))
    issues = []
    recommendations = []

    missing_pct = float(technical_profile.get('missing_pct') or 0.0)
    duplicate_rows = int(technical_profile.get('duplicate_rows') or 0)

    if missing_pct > 0:
        issues.append({
            'severity': 'warning',
            'category': 'missing_values',
            'column': '*',
            'rows': max(1, int(round(rows_count * (missing_pct / 100.0)))) if rows_count else 0,
            'explanation': f'Taux de valeurs manquantes detecte: {round(missing_pct, 2)}%.',
        })
        recommendations.append('Completer les valeurs manquantes par strategie deterministe (median/mode).')

    if duplicate_rows > 0:
        issues.append({
            'severity': 'warning',
            'category': 'duplicates',
            'column': '*',
            'rows': duplicate_rows,
            'explanation': f'{duplicate_rows} ligne(s) dupliquee(s) detectee(s).',
        })
        recommendations.append('Verifier et dedoublonner les lignes identiques avant integration.')

    outlier_total = 0
    for numeric_meta in technical_profile.get('numeric_columns_profile', []):
        outlier_total += int(numeric_meta.get('outlier_count') or 0)
    if outlier_total > 0:
        issues.append({
            'severity': 'info',
            'category': 'outliers',
            'column': '*',
            'rows': outlier_total,
            'explanation': f'{outlier_total} valeur(s) numerique(s) potentiellement aberrante(s) detectee(s) (regle IQR).',
        })
        recommendations.append('Examiner les valeurs numeriques extremes avant validation clinique.')

    fill_missing = {}
    trim_columns = []
    parse_dates = []

    for column_meta in technical_profile.get('columns_profile', []):
        column_name = str(column_meta.get('column') or '')
        if not column_name:
            continue
        missing_count = int(column_meta.get('missing_count') or 0)
        dtype_name = str(column_meta.get('dtype') or '').lower()
        if missing_count > 0:
            if 'int' in dtype_name or 'float' in dtype_name:
                fill_missing[column_name] = {'strategy': 'median'}
            else:
                fill_missing[column_name] = {'strategy': 'mode'}
        if dtype_name in {'object', 'string'}:
            trim_columns.append(column_name)
        lowered = column_name.lower()
        if 'date' in lowered or 'naissance' in lowered or 'visite' in lowered:
            parse_dates.append(column_name)

    correction_plan = {
        'fill_missing': fill_missing,
        'parse_dates': parse_dates[:15],
        'type_casts': {},
        'trim_whitespace_columns': trim_columns[:20],
    }

    if not recommendations:
        recommendations.append('Dataset globalement stable selon les controles deterministes locaux.')

    quality_score = max(5, min(100, int(round(100 - (missing_pct * 0.5) - (duplicate_rows * 2) - min(outlier_total, 20)))))

    return {
        'quality_score': quality_score,
        'summary': 'Analyse realisee via fallback deterministe local (Pandas) suite a indisponibilite LLM.',
        'issues': issues[:6],
        'recommendations': recommendations[:5],
        'correction_plan': correction_plan,
        'corrected_preview_rows': [],
        'column_assessment': [],
        'limitations': [
            'LLM indisponible: fallback deterministe applique.',
            reason_message,
        ],
        'analysis_pack': {
            'pack_type': 'structured_analysis_pack',
            'technical_profile': technical_profile,
            'preview_rows': _dataframe_to_rows(dataframe.head(3)),
            'column_samples': {},
            'meta': {
                'selected_columns_count': int(len(dataframe.columns)),
                'total_columns_count': int(len(dataframe.columns)),
                'preview_rows_count': min(3, int(len(dataframe.index))),
                'column_samples_per_column': 0,
            },
        },
        'model_used': 'deterministic_fallback',
        'attempt': 'fallback_local',
        'stage': 'pass1_diagnostic',
        'second_pass': {'status': 'skipped_fallback'},
        'route': {'mode': 'deterministic', 'label': 'deterministic_only', 'reason': reason_message},
    }


def _call_ollama_qwen_analysis(dataframe, technical_profile, progress_callback=None):
    route = _determine_preprocess_route(technical_profile)
    if route.get('mode') == 'deterministic':
        deterministic_result = _build_deterministic_analysis_fallback(
            dataframe,
            technical_profile,
            route.get('reason', 'Dataset simple: pas de LLM necessaire.'),
        )
        deterministic_result['route'] = route
        return deterministic_result

    model_name = route.get('primary_model') or os.environ.get('OLLAMA_PREPROCESS_MODEL', os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b-instruct'))
    timeout_seconds = int(os.environ.get('OLLAMA_TIMEOUT_SECONDS', '420'))
    primary_timeout_seconds = int(route.get('primary_timeout_seconds') or int(os.environ.get('OLLAMA_PRIMARY_TIMEOUT_SECONDS', str(min(timeout_seconds, 180)))))
    fallback_model = route.get('fallback_model') or os.environ.get('OLLAMA_FALLBACK_MODEL', 'qwen2.5:3b-instruct')
    fallback_timeout_seconds = int(route.get('fallback_timeout_seconds') or int(os.environ.get('OLLAMA_FALLBACK_TIMEOUT_SECONDS', str(timeout_seconds))))
    retry_max_columns = int(os.environ.get('OLLAMA_RETRY_MAX_COLUMNS', '20'))
    retry_preview_rows = int(os.environ.get('OLLAMA_RETRY_PREVIEW_ROWS', '2'))
    retry_num_predict = int(route.get('fallback_num_predict') or os.environ.get('OLLAMA_RETRY_NUM_PREDICT', '24'))
    pass2_num_predict = int(os.environ.get('OLLAMA_PASS2_NUM_PREDICT', str(retry_num_predict)))
    candidate_bases = _get_ollama_candidate_bases()

    prompt_payload = _build_llm_payload(dataframe, technical_profile)
    fallback_payload = _shrink_llm_payload(
        prompt_payload,
        max_columns=retry_max_columns,
        max_preview_rows=retry_preview_rows,
        max_samples_per_column=1,
    )

    def _notify_progress(message):
        if callable(progress_callback):
            try:
                progress_callback(message)
            except Exception:
                pass

    def _build_pass1_prompt(payload_for_prompt):
        return (
            'Analyse la qualite de ce dataset medical et retourne STRICTEMENT un JSON valide (sans texte hors JSON). '
            'Schema attendu: '
            '{quality_score:number(0-100), summary:string, issues:[{severity,category,column,rows,explanation}], '
            'recommendations:[string], needs_correction_plan:boolean, limitations:[string]}. '
            'Contraintes: max 6 issues, max 5 recommendations, explications courtes. '
            'Contexte: ' + json.dumps(payload_for_prompt, ensure_ascii=False, default=str)
        )

    def _build_pass2_prompt(payload_for_prompt):
        return (
            'Tu es dans la passe 2. Retourne STRICTEMENT un JSON valide (sans texte hors JSON). '
            'Objectif: proposer un plan de correction deterministe et minimal a appliquer par Pandas. '
            'Schema attendu: '
            '{correction_plan:{rename_columns,drop_columns,value_mappings,fill_missing,type_casts,parse_dates,trim_whitespace_columns,default_values}, limitations:[string]}. '
            'Contraintes: max 20 operations au total, actions prudentes, aucune invention de colonnes absentes. '
            'Contexte: ' + json.dumps(payload_for_prompt, ensure_ascii=False, default=str)
        )

    def _run_stage(stage_name, primary_prompt, fallback_prompt, primary_pack, fallback_pack, primary_predict, fallback_predict):
        attempts = [
            {
                'label': 'primary',
                'model': model_name,
                'timeout_seconds': primary_timeout_seconds,
                'num_predict': primary_predict,
                'analysis_pack': primary_pack,
                'prompt': primary_prompt,
            }
        ]

        if fallback_model and fallback_model != model_name:
            attempts.append(
                {
                    'label': 'fallback',
                    'model': fallback_model,
                    'timeout_seconds': fallback_timeout_seconds,
                    'num_predict': fallback_predict,
                    'analysis_pack': fallback_pack,
                    'prompt': fallback_prompt,
                }
            )

        stage_errors = []
        for attempt in attempts:
            request_payload = {
                'model': attempt['model'],
                'prompt': attempt['prompt'],
                'stream': False,
                'format': 'json',
                'options': {
                    'temperature': 0.1,
                    'num_predict': attempt['num_predict'],
                },
            }
            request_data = json.dumps(request_payload).encode('utf-8')

            for ollama_base in candidate_bases:
                ollama_endpoint = f'{ollama_base}/api/generate'
                req = urllib_request.Request(
                    ollama_endpoint,
                    data=request_data,
                    headers={'Content-Type': 'application/json'},
                    method='POST',
                )

                try:
                    with urllib_request.urlopen(req, timeout=attempt['timeout_seconds']) as response:
                        body = response.read().decode('utf-8')
                    payload = json.loads(body)
                    raw_response = payload.get('response', '{}')
                    parsed_response = _parse_llm_analysis_response(raw_response)
                    parsed_response['analysis_pack'] = attempt['analysis_pack']
                    parsed_response['model_used'] = attempt['model']
                    parsed_response['attempt'] = attempt['label']
                    parsed_response['stage'] = stage_name
                    return parsed_response
                except urllib_error.HTTPError as error:
                    error_body = ''
                    try:
                        error_body = error.read().decode('utf-8')
                    except Exception:
                        error_body = ''
                    stage_errors.append(
                        f"[{stage_name}:{attempt['label']}:{attempt['model']}] {ollama_endpoint} -> HTTP {error.code}: {error_body or str(error)}"
                    )
                except (urllib_error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
                    stage_errors.append(
                        f"[{stage_name}:{attempt['label']}:{attempt['model']}] {ollama_endpoint} -> {error}"
                    )

        error_summary = '; '.join(stage_errors) if stage_errors else 'Aucune reponse recue'
        lower_errors = error_summary.lower()
        limitations = []
        if 'timed out' in lower_errors or 'timeout' in lower_errors:
            limitations.append(
                f'Delai depasse: Ollama n a pas repondu dans la fenetre configured (primary={primary_timeout_seconds}s, fallback={fallback_timeout_seconds}s, plafond={timeout_seconds}s).'
            )
        if 'connection refused' in lower_errors or 'errno 111' in lower_errors:
            limitations.append(
                'Connexion refusee: l URL Ollama ciblee n est pas joignable depuis le backend. Verifier OLLAMA_URL et le reseau Docker.'
            )
        if '405' in lower_errors or 'method not allowed' in lower_errors:
            limitations.append('Methode invalide detectee: /api/generate doit etre appele en POST.')
        if not limitations:
            limitations.append('Aucun diagnostic automatique supplementaire disponible.')

        return {
            'unavailable': True,
            'summary': f'Analyse LLM indisponible ({stage_name}): {error_summary}',
            'issues': [],
            'recommendations': [],
            'correction_plan': {},
            'corrected_preview_rows': [],
            'column_assessment': [],
            'limitations': limitations,
            'analysis_pack': primary_pack,
            'model_used': model_name,
            'stage': stage_name,
        }

    _notify_progress('Analyse LLM - passe 1/2 (diagnostic)...')
    pass1_result = _run_stage(
        stage_name='pass1_diagnostic',
        primary_prompt=_build_pass1_prompt(prompt_payload),
        fallback_prompt=_build_pass1_prompt(fallback_payload),
        primary_pack=prompt_payload,
        fallback_pack=fallback_payload,
        primary_predict=int(os.environ.get('OLLAMA_NUM_PREDICT', '32')),
        fallback_predict=retry_num_predict,
    )

    if pass1_result.get('unavailable'):
        return _build_deterministic_analysis_fallback(
            dataframe,
            technical_profile,
            pass1_result.get('summary', 'Passe 1 indisponible.'),
        )

    pass1_issues = pass1_result.get('issues') if isinstance(pass1_result.get('issues'), list) else []
    pass1_recommendations = pass1_result.get('recommendations') if isinstance(pass1_result.get('recommendations'), list) else []
    pass1_limitations = pass1_result.get('limitations') if isinstance(pass1_result.get('limitations'), list) else []

    needs_correction_plan = bool(pass1_result.get('needs_correction_plan')) or bool(pass1_issues)

    if not needs_correction_plan:
        pass1_result['correction_plan'] = pass1_result.get('correction_plan') if isinstance(pass1_result.get('correction_plan'), dict) else {}
        pass1_result['second_pass'] = {'status': 'skipped'}
        pass1_result['route'] = route
        return pass1_result

    _notify_progress('Analyse LLM - passe 2/2 (plan de correction)...')
    pass2_primary_payload = {
        'analysis_pack': prompt_payload,
        'diagnostic': {
            'quality_score': pass1_result.get('quality_score'),
            'summary': pass1_result.get('summary'),
            'issues': pass1_issues[:6],
            'recommendations': pass1_recommendations[:5],
        },
    }
    pass2_fallback_payload = {
        'analysis_pack': fallback_payload,
        'diagnostic': pass2_primary_payload['diagnostic'],
    }

    pass2_result = _run_stage(
        stage_name='pass2_correction_plan',
        primary_prompt=_build_pass2_prompt(pass2_primary_payload),
        fallback_prompt=_build_pass2_prompt(pass2_fallback_payload),
        primary_pack=pass2_primary_payload,
        fallback_pack=pass2_fallback_payload,
        primary_predict=pass2_num_predict,
        fallback_predict=min(pass2_num_predict, retry_num_predict),
    )

    final_result = {
        'quality_score': pass1_result.get('quality_score'),
        'summary': pass1_result.get('summary'),
        'issues': pass1_issues,
        'recommendations': pass1_recommendations,
        'correction_plan': {},
        'corrected_preview_rows': pass1_result.get('corrected_preview_rows', []),
        'column_assessment': pass1_result.get('column_assessment', []),
        'limitations': pass1_limitations,
        'analysis_pack': pass1_result.get('analysis_pack', prompt_payload),
        'model_used': pass1_result.get('model_used'),
        'attempt': pass1_result.get('attempt'),
        'second_pass': {},
        'route': route,
    }

    if pass2_result.get('unavailable'):
        final_result['limitations'] = list(dict.fromkeys(final_result['limitations'] + [
            'Passe 2 indisponible: plan de correction vide utilise.'
        ] + (pass2_result.get('limitations') if isinstance(pass2_result.get('limitations'), list) else [])))
        final_result['second_pass'] = {
            'status': 'failed',
            'model_used': pass2_result.get('model_used'),
            'attempt': pass2_result.get('attempt'),
        }
        return final_result

    correction_plan = pass2_result.get('correction_plan') if isinstance(pass2_result.get('correction_plan'), dict) else {}
    final_result['correction_plan'] = correction_plan
    final_result['second_pass'] = {
        'status': 'completed',
        'model_used': pass2_result.get('model_used'),
        'attempt': pass2_result.get('attempt'),
    }
    if isinstance(pass2_result.get('limitations'), list) and pass2_result.get('limitations'):
        final_result['limitations'] = list(dict.fromkeys(final_result['limitations'] + pass2_result.get('limitations')))

    return final_result


def _resolve_llm_column_name(column_name, rename_map, available_columns):
    if column_name in available_columns:
        return column_name
    if column_name in rename_map:
        renamed = rename_map[column_name]
        if renamed in available_columns:
            return renamed
    normalized_target = normalize_header(column_name)
    for candidate in available_columns:
        if normalize_header(candidate) == normalized_target:
            return candidate
    return None


def _apply_llm_fill_strategy(series, strategy_spec):
    if strategy_spec in [None, '']:
        return series
    if not isinstance(strategy_spec, dict):
        return series.fillna(strategy_spec)

    strategy = str(strategy_spec.get('strategy', '')).lower()
    value = strategy_spec.get('value')

    if strategy == 'constant':
        return series.fillna(value)
    if strategy == 'mode':
        mode_values = series.mode(dropna=True)
        if not mode_values.empty:
            return series.fillna(mode_values.iloc[0])
        return series
    if strategy == 'mean':
        numeric = pd.to_numeric(series, errors='coerce')
        if numeric.notna().any():
            return series.fillna(float(numeric.mean()))
        return series
    if strategy == 'median':
        numeric = pd.to_numeric(series, errors='coerce')
        if numeric.notna().any():
            return series.fillna(float(numeric.median()))
        return series
    if strategy == 'forward_fill':
        return series.fillna(method='ffill')
    if strategy == 'backward_fill':
        return series.fillna(method='bfill')

    return series.fillna(value)


def _apply_llm_correction_plan(dataframe, llm_analysis):
    if not isinstance(llm_analysis, dict):
        return dataframe.copy(), []

    correction_plan = llm_analysis.get('correction_plan') or {}
    if not isinstance(correction_plan, dict):
        return dataframe.copy(), []

    corrected = dataframe.copy()
    applied_actions = []

    rename_columns = correction_plan.get('rename_columns') or {}
    rename_map = {}
    if isinstance(rename_columns, dict):
        rename_map = {str(source): str(target) for source, target in rename_columns.items() if source and target}
        if rename_map:
            existing_renames = {source: target for source, target in rename_map.items() if source in corrected.columns}
            if existing_renames:
                corrected = corrected.rename(columns=existing_renames)
                applied_actions.append({'action': 'rename_columns', 'count': len(existing_renames)})

    available_columns = list(corrected.columns)

    drop_columns = correction_plan.get('drop_columns') or []
    if isinstance(drop_columns, list):
        columns_to_drop = [column for column in drop_columns if column in available_columns]
        if columns_to_drop:
            corrected = corrected.drop(columns=columns_to_drop)
            applied_actions.append({'action': 'drop_columns', 'count': len(columns_to_drop)})
            available_columns = list(corrected.columns)

    trim_columns = correction_plan.get('trim_whitespace_columns') or []
    if isinstance(trim_columns, list):
        trimmed_count = 0
        for column_name in trim_columns:
            resolved = _resolve_llm_column_name(str(column_name), rename_map, available_columns)
            if not resolved or corrected[resolved].dtype != object:
                continue
            corrected[resolved] = corrected[resolved].apply(lambda value: value.strip() if isinstance(value, str) else value)
            trimmed_count += 1
        if trimmed_count:
            applied_actions.append({'action': 'trim_whitespace', 'count': trimmed_count})

    value_mappings = correction_plan.get('value_mappings') or {}
    if isinstance(value_mappings, dict):
        mapping_count = 0
        for column_name, mapping in value_mappings.items():
            resolved = _resolve_llm_column_name(str(column_name), rename_map, available_columns)
            if not resolved or not isinstance(mapping, dict):
                continue
            corrected[resolved] = corrected[resolved].replace(mapping)
            mapping_count += 1
        if mapping_count:
            applied_actions.append({'action': 'value_mappings', 'count': mapping_count})

    type_casts = correction_plan.get('type_casts') or {}
    if isinstance(type_casts, dict):
        cast_count = 0
        for column_name, target_type in type_casts.items():
            resolved = _resolve_llm_column_name(str(column_name), rename_map, available_columns)
            if not resolved:
                continue
            target = str(target_type).lower()
            if target in {'numeric', 'number', 'float', 'decimal'}:
                corrected[resolved] = pd.to_numeric(corrected[resolved], errors='coerce')
            elif target in {'integer', 'int'}:
                numeric = pd.to_numeric(corrected[resolved], errors='coerce')
                corrected[resolved] = numeric.round().astype('Int64')
            elif target in {'date', 'datetime'}:
                parsed = pd.to_datetime(corrected[resolved], errors='coerce', dayfirst=True)
                corrected[resolved] = parsed.dt.date
            elif target in {'string', 'text'}:
                corrected[resolved] = corrected[resolved].astype('string')
            cast_count += 1
        if cast_count:
            applied_actions.append({'action': 'type_casts', 'count': cast_count})

    parse_dates = correction_plan.get('parse_dates') or []
    if isinstance(parse_dates, list):
        parsed_count = 0
        for column_name in parse_dates:
            resolved = _resolve_llm_column_name(str(column_name), rename_map, available_columns)
            if not resolved:
                continue
            corrected[resolved] = pd.to_datetime(corrected[resolved], errors='coerce', dayfirst=True).dt.date
            parsed_count += 1
        if parsed_count:
            applied_actions.append({'action': 'parse_dates', 'count': parsed_count})

    fill_missing = correction_plan.get('fill_missing') or {}
    if isinstance(fill_missing, dict):
        filled_count = 0
        for column_name, strategy_spec in fill_missing.items():
            resolved = _resolve_llm_column_name(str(column_name), rename_map, available_columns)
            if not resolved:
                continue
            corrected[resolved] = _apply_llm_fill_strategy(corrected[resolved], strategy_spec)
            filled_count += 1
        if filled_count:
            applied_actions.append({'action': 'fill_missing', 'count': filled_count})

    default_values = correction_plan.get('default_values') or {}
    if isinstance(default_values, dict):
        default_count = 0
        for column_name, default_value in default_values.items():
            resolved = _resolve_llm_column_name(str(column_name), rename_map, available_columns)
            if not resolved:
                continue
            corrected[resolved] = corrected[resolved].fillna(default_value)
            default_count += 1
        if default_count:
            applied_actions.append({'action': 'default_values', 'count': default_count})

    return corrected, applied_actions


def _build_preprocess_report(dataframe, technical_profile, llm_analysis=None, corrected_df=None, applied_actions=None):
    llm_analysis = llm_analysis or {}
    corrected_df = corrected_df if isinstance(corrected_df, pd.DataFrame) else dataframe
    applied_actions = applied_actions or []

    issues = llm_analysis.get('issues') if isinstance(llm_analysis, dict) else []
    if not isinstance(issues, list):
        issues = []

    severity_count = {'critical': 0, 'warning': 0, 'info': 0}
    for item in issues:
        severity = str(item.get('severity', 'info')).lower()
        severity_count[severity] = severity_count.get(severity, 0) + 1

    quality_score = llm_analysis.get('quality_score') if isinstance(llm_analysis, dict) else None
    if not isinstance(quality_score, (int, float)):
        raw_score = 100 - (severity_count.get('critical', 0) * 15) - (severity_count.get('warning', 0) * 6) - (severity_count.get('info', 0) * 2)
        quality_score = max(5, min(100, int(raw_score)))
    else:
        quality_score = max(0, min(100, int(round(float(quality_score)))))

    recommendations = []
    for recommendation in (llm_analysis.get('recommendations') or []):
        recommendation_text = str(recommendation)
        if recommendation_text not in recommendations:
            recommendations.append(recommendation_text)

    if not recommendations:
        recommendations.append('Aucune recommandation fournie par le modele.')

    corrected_preview_rows = _dataframe_to_rows(corrected_df.head(20))

    return {
        'summary': {
            'rows': int(len(dataframe.index)),
            'columns': int(len(dataframe.columns)),
            'quality_score': quality_score,
            'total_issues': len(issues),
            'severity_count': severity_count,
            'corrected_rows': int(len(corrected_df.index)),
            'applied_corrections_count': len(applied_actions),
        },
        'dataset_profile': technical_profile,
        'issues': issues,
        'recommendations': recommendations,
        'correction_plan': llm_analysis.get('correction_plan') or {},
        'applied_corrections': applied_actions,
        'llm_analysis': llm_analysis,
        'corrected_preview_rows': corrected_preview_rows,
        'llm_preview_rows': llm_analysis.get('corrected_preview_rows') if isinstance(llm_analysis, dict) else [],
        'analysis_pack': llm_analysis.get('analysis_pack') if isinstance(llm_analysis, dict) else None,
    }


def _integrate_dataframe_into_patients(dataframe, request_user=None, source_file_name='preprocessed_dataset'):
    headers = list(dataframe.columns)
    template = upsert_template_from_headers(headers, None, source_file_name, create_fields=False)

    created_count = 0
    row_errors = []
    auto_increment_state = initialize_auto_increment_state()
    all_dynamic_columns = {}
    existing_template_keys = set(template.fields.values_list('key', flat=True)) if template else set()

    for header in headers:
        header_str = str(header).strip()
        if not header_str:
            continue
        normalized = normalize_header(header_str)
        if not normalized or normalized in existing_template_keys:
            continue
        if normalized in _COLUMNS_FUSED_INTO_COMORBIDITE_LISTE or normalized in COLUMN_MAPPING:
            continue
        all_dynamic_columns.setdefault(normalized, header_str)

    for index, row in dataframe.iterrows():
        payload = build_patient_payload(row)
        detected = payload.pop('_dynamic_columns_detected', set())
        for norm_key in detected:
            if norm_key not in all_dynamic_columns:
                original_name = next(
                    (str(h).strip() for h in headers if normalize_header(str(h).strip()) == norm_key),
                    norm_key,
                )
                all_dynamic_columns[norm_key] = original_name

        payload = apply_automatic_schema_fields(
            payload,
            auto_increment_state=auto_increment_state,
            current_user=request_user,
        )
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

    dynamic_columns_info = []
    if all_dynamic_columns and template:
        existing_keys = set(template.fields.values_list('key', flat=True))
        new_fields = []
        for norm_key, original_name in all_dynamic_columns.items():
            if norm_key in existing_keys:
                template.fields.filter(key=norm_key).update(source_hint='dynamic_column')
            else:
                new_fields.append(
                    PatientFormField(
                        template=template,
                        key=norm_key,
                        label=original_name,
                        field_type='text_short',
                        order=10000 + len(new_fields),
                        choices=[],
                        source_hint='dynamic_column',
                        is_required=False,
                    )
                )
            dynamic_columns_info.append({
                'key': norm_key,
                'label': original_name,
                'is_new': norm_key not in existing_keys,
            })

        if new_fields:
            PatientFormField.objects.bulk_create(new_fields)

    if created_count > 0 or all_dynamic_columns:
        try:
            refresh_postgres_flat_view(template)
        except Exception:
            pass

    template_data = PatientFormTemplateSerializer(template).data
    status_code = status.HTTP_201_CREATED if created_count else status.HTTP_200_OK
    return {
        'mode': 'data',
        'template': template_data,
        'fields_created': len(template_data.get('fields', [])),
        'patients_created': created_count,
        'errors': row_errors,
        'dynamic_columns': dynamic_columns_info,
        'dynamic_columns_count': len(dynamic_columns_info),
        'new_dynamic_columns_count': sum(1 for c in dynamic_columns_info if c.get('is_new')),
    }, status_code


# ============================================================
# VUES API
# ============================================================

class PatientListCreateView(APIView):
    permission_classes = [CanViewPatients]

    def get_queryset(self, request):
        queryset = Patient.objects.all()
        search = request.query_params.get('search', '').strip()
        id_patient = request.query_params.get('id_patient', '').strip()
        sexe = request.query_params.get('sexe', '').strip()
        age_min = request.query_params.get('age_min', '').strip()
        age_max = request.query_params.get('age_max', '').strip()
        date_naissance = request.query_params.get('date_naissance', '').strip()
        statut_inclusion = request.query_params.get('statut_inclusion', '').strip()
        infection = request.query_params.get('infection', '').strip().lower()
        hemorrhage = request.query_params.get('hemorrhage', '').strip().lower()
        avf_created = request.query_params.get('avf_created', '').strip().lower()

        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | Q(prenom__icontains=search) |
                Q(id_patient__icontains=search) | Q(maladie__icontains=search) |
                Q(telephone__icontains=search) | Q(adresse__icontains=search)
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
        if statut_inclusion:
            queryset = queryset.filter(statut_inclusion__icontains=statut_inclusion)

        return queryset

    def get(self, request):
        serializer = PatientSerializer(self.get_queryset(request), many=True)
        return Response(serializer.data)

    def post(self, request):
        before_data = None
        payload = request.data.copy()
        payload = apply_automatic_schema_fields(payload, current_user=request.user)
        payload = ensure_incremental_identifiers(payload)
        serializer = PatientSerializer(data=payload)
        if serializer.is_valid():
            patient = serializer.save()
            AuditLog.objects.create(
                utilisateur=request.user if request.user.is_authenticated else None,
                action=f"CREATION_PATIENT: patient {patient.id_patient or patient.id} cree",
                entite='Patient',
                entite_id=patient.id,
                adresse_ip=request.META.get('REMOTE_ADDR'),
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatientExportExcelView(APIView):
    permission_classes = [CanViewPatients]

    def get(self, request):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'patients'

        headers = [
            'id_patient', 'nom', 'prenom', 'age', 'sexe',
            'demographie_sexe', 'demographie_age_ans', 'demographie_date_naissance',
            'irc_etiologie_principale', 'dialyse_modalite_initiale', 'dialyse_date_debut',
            'devenir_statut', 'devenir_date_deces', 'devenir_cause_deces',
        ]
        worksheet.append(headers)

        for patient in Patient.objects.all():
            row = [
                patient.id_patient, patient.nom, patient.prenom, patient.age, patient.sexe,
                patient.demographie_sexe, patient.demographie_age_ans,
                patient.demographie_date_naissance,
                patient.irc_etiologie_principale, patient.dialyse_modalite_initiale,
                patient.dialyse_date_debut,
                patient.devenir_statut, patient.devenir_date_deces, patient.devenir_cause_deces,
            ]
            worksheet.append(row)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="patients_export.xlsx"'
        workbook.save(response)
        return response


class PatientDetailView(APIView):
    permission_classes = [CanViewPatients]

    def get_object(self, pk):
        return get_object_or_404(Patient, pk=pk)

    def get(self, request, pk):
        serializer = PatientSerializer(self.get_object(pk))
        return Response(serializer.data)

    def put(self, request, pk):
        patient = self.get_object(pk)
        before_data = PatientSerializer(patient).data
        serializer = PatientSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            updated_patient = serializer.save()
            after_data = PatientSerializer(updated_patient).data
            AuditLog.objects.create(
                utilisateur=request.user if request.user.is_authenticated else None,
                action=f"MODIFICATION_PATIENT: {_describe_patient_changes(before_data, after_data)}",
                entite='Patient',
                entite_id=updated_patient.id,
                adresse_ip=request.META.get('REMOTE_ADDR'),
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        patient = self.get_object(pk)
        before_data = PatientSerializer(patient).data
        serializer = PatientSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            updated_patient = serializer.save()
            after_data = PatientSerializer(updated_patient).data
            AuditLog.objects.create(
                utilisateur=request.user if request.user.is_authenticated else None,
                action=f"MODIFICATION_PATIENT: {_describe_patient_changes(before_data, after_data)}",
                entite='Patient',
                entite_id=updated_patient.id,
                adresse_ip=request.META.get('REMOTE_ADDR'),
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        patient = self.get_object(pk)
        AuditLog.objects.create(
            utilisateur=request.user if request.user.is_authenticated else None,
            action=f"SUPPRESSION_PATIENT: patient {patient.id_patient or patient.id} supprime",
            entite='Patient',
            entite_id=patient.id,
            adresse_ip=request.META.get('REMOTE_ADDR'),
        )
        patient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PatientBulkPurgeView(APIView):
    permission_classes = [IsAdminOrChefService]

    def delete(self, request):
        deleted_count, _ = Patient.objects.all().delete()
        return Response({'deleted_count': deleted_count}, status=status.HTTP_200_OK)


class PatientDynamicColumnsCleanupView(APIView):
    permission_classes = [IsAdminOrChefService]

    def post(self, request):
        template = get_active_template()
        if not template:
            return Response(
                {
                    'template_found': False,
                    'removed_count': 0,
                    'removed_keys': [],
                },
                status=status.HTTP_200_OK,
            )

        dynamic_fields = template.fields.filter(
            source_hint__in=['dynamic_column', 'auto_detected_from_data_import']
        )
        if not dynamic_fields.exists():
            return Response(
                {
                    'template_found': True,
                    'removed_count': 0,
                    'removed_keys': [],
                },
                status=status.HTTP_200_OK,
            )

        used_extra_keys = set()
        for extra_payload in Patient.objects.values_list('extra_data', flat=True):
            if isinstance(extra_payload, dict):
                used_extra_keys.update(extra_payload.keys())

        stale_fields_qs = dynamic_fields.exclude(key__in=used_extra_keys)
        removed_keys = list(stale_fields_qs.values_list('key', flat=True))
        removed_count = len(removed_keys)
        if removed_count > 0:
            stale_fields_qs.delete()
            try:
                refresh_postgres_flat_view(template)
            except Exception:
                pass

        return Response(
            {
                'template_found': True,
                'removed_count': removed_count,
                'removed_keys': removed_keys,
            },
            status=status.HTTP_200_OK,
        )


class PatientPreprocessAnalyzeView(APIView):
    permission_classes = [CanViewPatients]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from patients.tasks import analyze_preprocess_async
        import tempfile

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'Fichier CSV/Excel requis.'}, status=status.HTTP_400_BAD_REQUEST)

        # Créer un ID unique pour cette session
        session_id = uuid.uuid4().hex
        source_file_name = uploaded_file.name

        # Sauvegarder le fichier temporairement
        try:
            temp_dir = '/tmp/preprocess'
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_dir, f'{session_id}_{source_file_name}')
            with open(temp_file_path, 'wb') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
        except Exception as error:
            return Response({'error': f'Erreur lors de la sauvegarde du fichier: {error}'}, status=status.HTTP_400_BAD_REQUEST)

        # Initialiser la session avec statut "pending"
        session = {
            'id': session_id,
            'created_at': timezone.now().isoformat(),
            'created_by': resolve_entry_user_label(request.user),
            'source_file_name': source_file_name,
            'columns': [],
            'original_rows': [],
            'corrected_rows': [],
            'report': {},
            'change_log': [],
            'status': 'pending',
            'error': None,
            'progress_message': 'Initialisation du traitement...',
        }
        _save_preprocess_session(session)

        # Dispatcher la task Celery de manière asynchrone
        try:
            analyze_preprocess_async.delay(
                session_id=session_id,
                file_path=temp_file_path,
                user_id=request.user.id,
                use_llm=str(request.data.get('use_llm', 'true')).lower() not in ['0', 'false', 'no', 'non']
            )
        except Exception as error:
            print(f"Erreur lors du lancement de la task Celery: {error}")
            session['status'] = 'error'
            session['error'] = f'Erreur Celery: {error}'
            _save_preprocess_session(session)
            return Response({'error': f'Erreur lors du lancement du traitement: {error}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                'preprocess_id': session_id,
                'status': 'pending',
                'message': 'Analyse en cours... Veuillez vérifier le statut.',
                'source_file_name': source_file_name,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PatientPreprocessStatusView(APIView):
    """Track the status of an ongoing preprocessing job."""
    permission_classes = [CanViewPatients]

    def get(self, request, preprocess_id):
        try:
            session = _load_preprocess_session(preprocess_id)
        except Exception:
            return Response({'error': 'Session non trouvée.'}, status=status.HTTP_404_NOT_FOUND)

        if session.get('status') == 'completed':
            report = session.get('report', {})
            return Response(
                {
                    'preprocess_id': preprocess_id,
                    'status': 'completed',
                    'report': report,
                    'columns': session.get('columns', []),
                    'row_count': len(session.get('corrected_rows', [])),
                    'original_preview_rows': session.get('original_rows', [])[:20],
                    'preview_rows': session.get('corrected_rows', [])[:20],
                    'corrected_preview_rows': report.get('corrected_preview_rows', [])[:20],
                    'dataset_profile': {'columns': len(session.get('columns', [])), 'rows': len(session.get('corrected_rows', []))},
                    'source_file_name': session.get('source_file_name'),
                },
                status=status.HTTP_200_OK,
            )
        elif session.get('status') == 'error':
            return Response(
                {
                    'preprocess_id': preprocess_id,
                    'status': 'error',
                    'error': session.get('error', 'Erreur inconnue'),
                    'message': f"Erreur lors de l'analyse: {session.get('error')}",
                },
                status=status.HTTP_200_OK,
            )
        else:  # pending or in_progress
            return Response(
                {
                    'preprocess_id': preprocess_id,
                    'status': session.get('status', 'pending'),
                    'progress_message': session.get('progress_message', 'Traitement en cours...'),
                    'message': 'Analyse en cours, veuillez patienter...',
                },
                status=status.HTTP_200_OK,
            )


class PatientPreprocessHealthView(APIView):
    # Allow unauthenticated access so the UI can display Ollama status before login
    permission_classes = [AllowAny]

    def get(self, request):
        timeout_seconds = int(os.environ.get('OLLAMA_HEALTH_TIMEOUT_SECONDS', '8'))
        health = _check_ollama_health(timeout_seconds=timeout_seconds)
        model_name = os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b-instruct')
        if health.get('connected'):
            return Response(
                {
                    'connected': True,
                    'configured_model': model_name,
                    'base_url': health.get('base_url'),
                    'endpoint': health.get('endpoint'),
                    'models_count': health.get('models_count', 0),
                    'models': health.get('models', []),
                    'message': 'Ollama connecté.',
                },
                status=status.HTTP_200_OK,
            )

        errors = health.get('errors') or []
        return Response(
            {
                'connected': False,
                'configured_model': model_name,
                'base_url': None,
                'endpoint': None,
                'models_count': 0,
                'models': [],
                'message': 'Ollama indisponible depuis le backend.',
                'errors': errors,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class PatientPreprocessSessionView(APIView):
    permission_classes = [CanViewPatients]

    def get(self, request, session_id):
        session = _load_preprocess_session(session_id)
        if not session:
            return Response({'error': 'Session de pretraitement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                'preprocess_id': session.get('id'),
                'source_file_name': session.get('source_file_name'),
                'report': session.get('report', {}),
                'columns': session.get('columns', []),
                'row_count': len(session.get('corrected_rows', [])),
                'preview_rows': session.get('corrected_rows', [])[:50],
                'change_log': session.get('change_log', [])[-20:],
            },
            status=status.HTTP_200_OK,
        )


class PatientPreprocessRowsView(APIView):
    permission_classes = [CanViewPatients]

    def post(self, request, session_id):
        session = _load_preprocess_session(session_id)
        if not session:
            return Response({'error': 'Session de pretraitement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        row_payload = request.data.get('row') or {}
        columns = session.get('columns', [])
        row = {column: row_payload.get(column) for column in columns}

        for key, value in row_payload.items():
            if key not in row:
                row[key] = value
                if key not in columns:
                    columns.append(key)

        session.setdefault('corrected_rows', []).append(row)
        session['columns'] = columns
        session.setdefault('change_log', []).append(
            {
                'timestamp': timezone.now().isoformat(),
                'user': resolve_entry_user_label(request.user),
                'action': 'create_row',
                'row_index': len(session['corrected_rows']) - 1,
            }
        )
        _save_preprocess_session(session)
        return Response({'row_count': len(session['corrected_rows'])}, status=status.HTTP_200_OK)


class PatientPreprocessRowDetailView(APIView):
    permission_classes = [CanViewPatients]

    def patch(self, request, session_id, row_index):
        session = _load_preprocess_session(session_id)
        if not session:
            return Response({'error': 'Session de pretraitement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        rows = session.get('corrected_rows', [])
        if row_index < 0 or row_index >= len(rows):
            return Response({'error': 'Index de ligne invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        row_payload = request.data.get('row') or {}
        current_row = rows[row_index]
        for key, value in row_payload.items():
            current_row[key] = value
            if key not in session.get('columns', []):
                session['columns'].append(key)

        session.setdefault('change_log', []).append(
            {
                'timestamp': timezone.now().isoformat(),
                'user': resolve_entry_user_label(request.user),
                'action': 'update_row',
                'row_index': row_index,
            }
        )
        _save_preprocess_session(session)
        return Response({'row': current_row}, status=status.HTTP_200_OK)

    def delete(self, request, session_id, row_index):
        session = _load_preprocess_session(session_id)
        if not session:
            return Response({'error': 'Session de pretraitement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        rows = session.get('corrected_rows', [])
        if row_index < 0 or row_index >= len(rows):
            return Response({'error': 'Index de ligne invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        rows.pop(row_index)
        session.setdefault('change_log', []).append(
            {
                'timestamp': timezone.now().isoformat(),
                'user': resolve_entry_user_label(request.user),
                'action': 'delete_row',
                'row_index': row_index,
            }
        )
        _save_preprocess_session(session)
        return Response({'row_count': len(rows)}, status=status.HTTP_200_OK)


class PatientPreprocessExportView(APIView):
    permission_classes = [CanViewPatients]

    def get(self, request, session_id):
        session = _load_preprocess_session(session_id)
        if not session:
            return Response({'error': 'Session de pretraitement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        source = str(request.query_params.get('source', 'corrected')).lower()
        rows_key = 'original_rows' if source == 'original' else 'corrected_rows'
        rows = session.get(rows_key, [])
        columns = session.get('columns', [])
        dataframe = _rows_to_dataframe(rows, columns=columns)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='preprocess_dataset')
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="preprocess_{session_id}_{source}.xlsx"'
        return response


class PatientPreprocessIntegrateView(APIView):
    permission_classes = [CanViewPatients]

    def post(self, request, session_id):
        session = _load_preprocess_session(session_id)
        if not session:
            return Response({'error': 'Session de pretraitement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        source = str(request.data.get('source', 'corrected')).lower()
        rows_key = 'original_rows' if source == 'original' else 'corrected_rows'
        rows = session.get(rows_key, [])
        columns = session.get('columns', [])
        dataframe = _rows_to_dataframe(rows, columns=columns)

        result_payload, result_status = _integrate_dataframe_into_patients(
            dataframe,
            request_user=request.user,
            source_file_name=session.get('source_file_name') or f'preprocess_{session_id}.xlsx',
        )
        result_payload['preprocess_id'] = session_id
        result_payload['integration_source'] = source
        result_payload['quality_score'] = session.get('report', {}).get('summary', {}).get('quality_score')
        return Response(result_payload, status=result_status)


class PatientImportExcelView(APIView):
    permission_classes = [CanViewPatients]
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
                return Response(
                    {'error': f'Impossible de lire le fichier Excel (.xls): {error}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            try:
                excel_file.seek(0)
                workbook = load_workbook(excel_file, data_only=False)
            except Exception as error:
                return Response(
                    {'error': f'Impossible de lire le fichier Excel: {error}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
                # parse_dates=True aide pandas à reconnaître les colonnes de dates
                dataframe = pd.read_excel(excel_file, parse_dates=True)
            except Exception as error:
                return Response(
                    {'error': f'Impossible de lire les donnees du fichier Excel: {error}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if dataframe is not None:
            dataframe = dataframe.loc[
                :, ~dataframe.columns.astype(str).str.match(r'^(Unnamed|unnamed)(:.*)?$')
            ]

        headers = list(dataframe.columns)
        template = upsert_template_from_headers(headers, worksheet, source_file_name, create_fields=False)

        created_count = 0
        row_errors = []
        auto_increment_state = initialize_auto_increment_state()
        # Accumuler toutes les colonnes dynamiques rencontrées sur l'ensemble des lignes
        # Pré-détecter les colonnes non-mappées/non-fixes à partir des headers
        all_dynamic_columns = {}  # normalized_key -> original_column_name
        if template:
            existing_template_keys = set(template.fields.values_list('key', flat=True))
        else:
            existing_template_keys = set()

        for h in headers:
            try:
                header_str = str(h).strip()
            except Exception:
                continue
            if not header_str:
                continue
            norm = normalize_header(header_str)
            if not norm:
                continue
            # Ne pas créer si déjà présent dans le template
            if norm in existing_template_keys:
                continue
            # Ne jamais créer de champ pour les colonnes fusionnées
            if norm in _COLUMNS_FUSED_INTO_COMORBIDITE_LISTE:
                continue
            # Si la colonne est mappée dans COLUMN_MAPPING, ce n'est pas une dynamique
            if norm in COLUMN_MAPPING:
                continue
            # Pré-enregistrer comme colonne dynamique (sera marquée/créée plus tard)
            all_dynamic_columns.setdefault(norm, header_str)

        for index, row in dataframe.iterrows():
            payload = build_patient_payload(row)

            # Récupérer les colonnes dynamiques détectées pour cette ligne
            detected = payload.pop('_dynamic_columns_detected', set())
            for norm_key in detected:
                if norm_key not in all_dynamic_columns:
                    # Chercher le nom original dans les headers du dataframe
                    original_name = next(
                        (str(h).strip() for h in headers
                         if normalize_header(str(h).strip()) == norm_key),
                        norm_key,
                    )
                    all_dynamic_columns[norm_key] = original_name

            payload = apply_automatic_schema_fields(
                payload, auto_increment_state=auto_increment_state, current_user=request.user
            )
            payload = ensure_required_identity_fields(payload)
            payload = ensure_incremental_identifiers(
                payload, auto_increment_state=auto_increment_state, force_generated=True
            )

            serializer = PatientSerializer(data=payload)
            if serializer.is_valid():
                serializer.save()
                created_count += 1
            else:
                row_errors.append({'row': index + 2, 'errors': serializer.errors})
                print(f"ERREUR ligne {index + 2}: {serializer.errors}")

        # ── Enregistrer les colonnes dynamiques dans le template ──────────────
        dynamic_columns_info = []
        if all_dynamic_columns and template:
            existing_keys = set(template.fields.values_list('key', flat=True))
            new_fields = []
            for norm_key, original_name in all_dynamic_columns.items():
                if norm_key in existing_keys:
                    # Déjà connue : mettre à jour le source_hint pour marquer comme dynamique
                    template.fields.filter(key=norm_key).update(
                        source_hint='dynamic_column'
                    )
                else:
                    new_fields.append(
                        PatientFormField(
                            template=template,
                            key=norm_key,
                            label=original_name,
                            field_type='text_short',
                            order=10000 + len(new_fields),
                            choices=[],
                            source_hint='dynamic_column',
                            is_required=False,
                        )
                    )
                dynamic_columns_info.append({
                    'key': norm_key,
                    'label': original_name,
                    'is_new': norm_key not in existing_keys,
                })

            if new_fields:
                PatientFormField.objects.bulk_create(new_fields)
                print(f"✅ {len(new_fields)} nouvelle(s) colonne(s) dynamique(s) enregistrée(s): "
                      f"{[f.key for f in new_fields]}")

        if created_count > 0 or all_dynamic_columns:
            try:
                refresh_postgres_flat_view(template)
            except Exception as e:
                print(f"Erreur rafraîchissement vue: {e}")

        template_data = PatientFormTemplateSerializer(template).data
        status_code = status.HTTP_201_CREATED if created_count else status.HTTP_200_OK

        print(f"\n{'='*80}")
        print(f"IMPORT TERMINÉ: {created_count} patients créés, {len(row_errors)} erreurs")
        print(f"Colonnes dynamiques: {list(all_dynamic_columns.keys())}")
        print(f"{'='*80}\n")

        return Response(
            {
                'mode': 'data',
                'template': template_data,
                'fields_created': len(template_data.get('fields', [])),
                'patients_created': created_count,
                'errors': row_errors,
                'dynamic_columns': dynamic_columns_info,
                'dynamic_columns_count': len(dynamic_columns_info),
                'new_dynamic_columns_count': sum(1 for c in dynamic_columns_info if c.get('is_new')),
            },
            status=status_code,
        )


class PatientSchemaView(APIView):
    permission_classes = [CanViewPatients]

    def get(self, request):
        template = get_active_template()
        if not template:
            return Response({'template': None})

        # Supprimer définitivement les colonnes déjà fusionnées dans comorbidite_liste
        template.fields.filter(key__in=_COLUMNS_FUSED_INTO_COMORBIDITE_LISTE).delete()

        return Response({'template': PatientFormTemplateSerializer(template).data})


class PatientPlateformeFlatView(APIView):
    permission_classes = [CanViewPatients]

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM patients_plateforme_flat')
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return Response(rows)