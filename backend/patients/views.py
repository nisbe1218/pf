import unicodedata
import re
import uuid
import json
import os
import io
import logging
from datetime import datetime, timedelta
from http.client import RemoteDisconnected
from urllib import request as urllib_request
from urllib import error as urllib_error
from patients.tasks import analyze_preprocess_async
import pandas as pd
import numpy as np
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
from .preprocess_rag import build_rag_context, estimate_route, should_use_llm
from .llm_client import check_llm_health, get_llm_model_name, get_system_prompt, run_json_completion

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.impute import SimpleImputer
except Exception:  # pragma: no cover - optional dependency
    IsolationForest = None
    SimpleImputer = None


logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, datetime):
            return obj.isoformat()
        obj_module = getattr(obj.__class__, '__module__', '')
        if obj_module.startswith('numpy'):
            if hasattr(obj, 'tolist'):
                try:
                    return obj.tolist()
                except Exception:
                    pass
            if hasattr(obj, 'item'):
                try:
                    return obj.item()
                except Exception:
                    pass
            return str(obj)
        return super().default(obj)


def _safe_json_value(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return None if value != value else value

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return {str(key): _safe_json_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_safe_json_value(item) for item in value]

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    if isinstance(value, pd.Series):
        return [_safe_json_value(item) for item in value.tolist()]

    if isinstance(value, pd.DataFrame):
        return [_safe_json_value(row) for row in value.to_dict(orient='records')]

    value_module = getattr(value.__class__, '__module__', '')
    if value_module.startswith('numpy'):
        if hasattr(value, 'tolist'):
            try:
                return _safe_json_value(value.tolist())
            except Exception:
                pass
        if hasattr(value, 'item'):
            try:
                return _safe_json_value(value.item())
            except Exception:
                pass

    if hasattr(value, 'to_pydatetime'):
        try:
            return value.to_pydatetime().isoformat()
        except Exception:
            pass

    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except Exception:
            pass

    if hasattr(value, 'to_dict'):
        try:
            return _safe_json_value(value.to_dict())
        except Exception:
            pass

    return str(value)


# ============================================================
# FONCTIONS UTILITAIRES DE BASE
# ============================================================

def normalize_header(value):
    text = unicodedata.normalize('NFKD', str(value).strip().lower())
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def anomaly_score(column_name, value, anomaly_type=None):
    score = 0
    if value is None or (isinstance(value, float) and value != value):
        score += 1

    normalized = normalize_header(column_name)
    critical_tokens = ['creatinine', 'potassium', 'sodium', 'hemoglobine', 'albumine', 'uree', 'age', 'dialyse', 'deces']
    if any(token in normalized for token in critical_tokens):
        score += 5

    numeric_value = None
    if value is not None:
        try:
            numeric_value = float(str(value).replace(',', '.'))
        except Exception:
            numeric_value = None

    medical_limits = {
        'creatinine': {'low': 0.0, 'high': 200.0},
        'potassium': {'low': 2.5, 'high': 6.5},
        'sodium': {'low': 125.0, 'high': 155.0},
        'age': {'low': 0.0, 'high': 120.0},
        'hemoglobine': {'low': 7.0, 'high': 20.0},
        'albumine': {'low': 25.0, 'high': 55.0},
        'uree': {'low': 0.0, 'high': 100.0},
    }
    for token, limits in medical_limits.items():
        if token not in normalized or numeric_value is None:
            continue
        if numeric_value < 0:
            score += 10
        if numeric_value < limits['low'] or numeric_value > limits['high']:
            score += 8
        break

    if anomaly_type == 'invalid_value':
        score += 2

    return score


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
        json.dump(_safe_json_value(session_payload), handle, ensure_ascii=False)
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
    suspect_columns = []
    anomaly_records = []
    missing_data_rate = {}
    statistics = {}
    numeric_matrix_columns = []
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
        missing_data_rate[str(column)] = round((missing_count / total_rows), 4) if total_rows else 0.0

        normalized_column = normalize_header(str(column))
        if column_profile['missing_pct'] >= 30.0 or (non_null_count > 0 and series.astype(str).nunique(dropna=True) <= 1):
            suspect_columns.append(str(column))

        if pd.api.types.is_numeric_dtype(series):
            numeric_series = pd.to_numeric(series, errors='coerce').dropna()
            if not numeric_series.empty:
                numeric_matrix_columns.append(str(column))
                numeric_values = numeric_series.to_numpy(dtype=float)
                numeric_mean = float(numeric_series.mean())
                numeric_std = float(numeric_series.std(ddof=0)) if numeric_series.count() > 1 else 0.0
                numeric_median = float(numeric_series.median())
                q1 = float(numeric_series.quantile(0.25))
                q3 = float(numeric_series.quantile(0.75))
                iqr = q3 - q1
                lower_bound = q1 - (1.5 * iqr)
                upper_bound = q3 + (1.5 * iqr)
                outlier_count = int(((numeric_series < lower_bound) | (numeric_series > upper_bound)).sum())
                mad = float(np.median(np.abs(numeric_values - numeric_median))) if numeric_values.size else 0.0
                robust_outlier_count = 0
                if mad > 0.0:
                    robust_outlier_count = int(np.sum(np.abs(numeric_values - numeric_median) / (1.4826 * mad) > 3.5))
                zscore_outlier_count = 0
                if numeric_std > 0.0:
                    zscore_outlier_count = int(np.sum(np.abs((numeric_values - numeric_mean) / numeric_std) > 3.0))
                numeric_columns_profile.append({
                    'column': str(column),
                    'count': int(numeric_series.count()),
                    'mean': round(numeric_mean, 4),
                    'std': round(numeric_std, 4),
                    'min': round(float(numeric_series.min()), 4),
                    'q1': round(q1, 4),
                    'median': round(numeric_median, 4),
                    'q3': round(q3, 4),
                    'max': round(float(numeric_series.max()), 4),
                    'outlier_count': outlier_count,
                    'robust_outlier_count': robust_outlier_count,
                    'zscore_outlier_count': zscore_outlier_count,
                })
                statistics[str(column)] = {
                    'min': round(float(numeric_series.min()), 4),
                    'max': round(float(numeric_series.max()), 4),
                    'mean': round(numeric_mean, 4),
                    'median': round(numeric_median, 4),
                }

                biological_rules = [
                    ('creatinine', 0.0, 200.0, 'invalid_value'),
                    ('potassium', 2.5, 6.5, 'biological_outlier'),
                    ('sodium', 125.0, 155.0, 'biological_outlier'),
                    ('age', 0.0, 120.0, 'invalid_value'),
                    ('hemoglobine', 7.0, 20.0, 'biological_outlier'),
                    ('albumine', 25.0, 55.0, 'biological_outlier'),
                    ('uree', 0.0, 100.0, 'biological_outlier'),
                ]
                for token, low_bound, high_bound, anomaly_type in biological_rules:
                    if token not in normalized_column:
                        continue
                    invalid_mask = (numeric_series < low_bound) | (numeric_series > high_bound)
                    if invalid_mask.any():
                        for row_index, value in numeric_series[invalid_mask].head(12).items():
                            anomaly_records.append({
                                'row': int(row_index) + 1,
                                'column': str(column),
                                'value': _to_json_compatible(value),
                                'type': anomaly_type,
                                'score': anomaly_score(str(column), value, anomaly_type),
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

            numeric_like_tokens = ['creatinine', 'potassium', 'sodium', 'age', 'hemoglobine', 'albumine', 'uree']
            if any(token in normalized_column for token in numeric_like_tokens):
                for row_index, value in series.items():
                    if pd.isna(value):
                        continue
                    value_text = str(value).strip()
                    if not value_text:
                        continue
                    try:
                        float(value_text.replace(',', '.'))
                        continue
                    except Exception:
                        anomaly_records.append({
                            'row': int(row_index) + 1,
                            'column': str(column),
                            'value': _to_json_compatible(value),
                            'type': 'invalid_value',
                            'score': anomaly_score(str(column), value, 'invalid_value'),
                        })
                        if str(column) not in suspect_columns:
                            suspect_columns.append(str(column))
                        break

    sklearn_anomaly_count = 0
    sklearn_anomaly_ratio = 0.0
    if IsolationForest is not None and SimpleImputer is not None and len(numeric_matrix_columns) >= 2 and total_rows >= 8:
        try:
            numeric_frame = dataframe[numeric_matrix_columns].apply(pd.to_numeric, errors='coerce')
            if numeric_frame.notna().any().any():
                imputer = SimpleImputer(strategy='median')
                matrix = imputer.fit_transform(numeric_frame)
                if matrix.size:
                    forest = IsolationForest(random_state=42, contamination='auto', n_estimators=100)
                    labels = forest.fit_predict(matrix)
                    sklearn_anomaly_count = int((labels == -1).sum())
                    sklearn_anomaly_ratio = round((sklearn_anomaly_count / len(labels)) * 100, 2) if len(labels) else 0.0
        except Exception:
            sklearn_anomaly_count = 0
            sklearn_anomaly_ratio = 0.0

    anomalies_by_severity = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': [],
    }
    column_stats = {}
    for record in anomaly_records:
        score = int(record.get('score') or 0)
        if score >= 10:
            bucket = 'critical'
        elif score >= 7:
            bucket = 'high'
        elif score >= 4:
            bucket = 'medium'
        else:
            bucket = 'low'
        anomalies_by_severity[bucket].append(record)

        column_name = str(record.get('column') or '')
        if not column_name:
            continue
        column_stats.setdefault(column_name, {
            'error_rate': 0.0,
            'max': statistics.get(column_name, {}).get('max'),
            'min': statistics.get(column_name, {}).get('min'),
            'anomalies': 0,
            'score_total': 0,
        })
        column_stats[column_name]['anomalies'] += 1
        column_stats[column_name]['score_total'] += score

    for column_name, stats in column_stats.items():
        stats['error_rate'] = round((stats['anomalies'] / total_rows), 4) if total_rows else 0.0
        if stats.get('score_total') is not None:
            stats['avg_score'] = round((stats['score_total'] / stats['anomalies']), 2) if stats['anomalies'] else 0.0

    suspect_column_stats = sorted(
        (
            {
                'name': column_name,
                'error_rate': stats.get('error_rate', 0.0),
                'anomalies': stats.get('anomalies', 0),
            }
            for column_name, stats in column_stats.items()
        ),
        key=lambda item: (item.get('error_rate') or 0.0, item.get('anomalies') or 0),
        reverse=True,
    )
    suspect_column_stats = suspect_column_stats[:20]

    critical_anomalies = sorted(anomalies_by_severity['critical'], key=lambda item: int(item.get('score') or 0), reverse=True)
    high_anomalies = sorted(anomalies_by_severity['high'], key=lambda item: int(item.get('score') or 0), reverse=True)
    medium_anomalies = sorted(anomalies_by_severity['medium'], key=lambda item: int(item.get('score') or 0), reverse=True)
    low_anomalies = sorted(anomalies_by_severity['low'], key=lambda item: int(item.get('score') or 0), reverse=True)

    if suspect_column_stats:
        suspect_columns = [item['name'] for item in suspect_column_stats[:10]]

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
        'sklearn_anomaly_count': sklearn_anomaly_count,
        'sklearn_anomaly_ratio': sklearn_anomaly_ratio,
        'suspect_columns': list(dict.fromkeys([str(column) for column in suspect_columns if column])),
        'column_stats': column_stats,
        'anomalies': anomalies_by_severity,
        'critical_anomalies': critical_anomalies[:100],
        'high_anomalies': high_anomalies[:100],
        'medium_anomalies': medium_anomalies[:100],
        'low_anomalies': low_anomalies[:100],
        'missing_data_rate': missing_data_rate,
        'statistics': statistics,
        'analysis_stack': {
            'deterministic': ['pandas', 'numpy'],
            'statistical_ml': ['sklearn'] if IsolationForest is not None and SimpleImputer is not None else [],
        },
        'preview_rows': _dataframe_to_rows(dataframe.head(3)),
    }


def _build_rule_validation_summary(technical_profile):
    issues = []
    recommendations = []

    missing_pct = float(technical_profile.get('missing_pct') or 0.0)
    duplicate_rows = int(technical_profile.get('duplicate_rows') or 0)
    sklearn_anomaly_count = int(technical_profile.get('sklearn_anomaly_count') or 0)
    outlier_total = sum(int(item.get('outlier_count') or 0) for item in (technical_profile.get('numeric_columns_profile') or []))

    critical_threshold = 15.0
    for column_meta in technical_profile.get('columns_profile', []):
        column_name = str(column_meta.get('column') or '')
        if not column_name:
            continue
        column_missing_pct = float(column_meta.get('missing_pct') or 0.0)
        normalized = normalize_header(column_name)
        if any(token in normalized for token in ['deces', 'dialyse', 'biologie', 'albumine', 'hemoglobine', 'creatinine', 'phosphore', 'calcium', 'infection', 'transplant']):
            if column_missing_pct >= critical_threshold:
                issues.append({
                    'severity': 'warning',
                    'rule': 'critical_column_missingness',
                    'column': column_name,
                    'explanation': f'Colonne critique avec {round(column_missing_pct, 2)}% de valeurs manquantes.',
                })
                recommendations.append(f'Contrôler la cohérence clinique de {column_name} avant export.')

    if missing_pct > 0:
        issues.append({
            'severity': 'warning',
            'rule': 'global_missingness',
            'column': '*',
            'explanation': f'Taux global de valeurs manquantes: {round(missing_pct, 2)}%.',
        })
        recommendations.append('Appliquer une stratégie d imputation explicable sur les colonnes concernées.')

    if duplicate_rows > 0:
        issues.append({
            'severity': 'warning',
            'rule': 'duplicates',
            'column': '*',
            'explanation': f'{duplicate_rows} ligne(s) dupliquée(s) détectée(s).',
        })
        recommendations.append('Dédoublonner les lignes avant intégration médicale.')

    if outlier_total > 0 or sklearn_anomaly_count > 0:
        issues.append({
            'severity': 'info',
            'rule': 'statistical_anomalies',
            'column': '*',
            'explanation': f'{outlier_total} outlier(s) IQR et {sklearn_anomaly_count} anomalie(s) sklearn détecté(s).',
        })
        recommendations.append('Faire valider les extrêmes numériques par une expertise clinique.')

    if not issues:
        recommendations.append('Profil statistique cohérent: aucune règle métier bloquante détectée.')

    return {
        'status': 'pass' if not issues else 'review',
        'issues': issues[:12],
        'recommendations': list(dict.fromkeys(recommendations))[:8],
        'summary': 'Validation règles métier et profilage statistique terminés.',
        'signals': {
            'missing_pct': missing_pct,
            'duplicate_rows': duplicate_rows,
            'outlier_total': outlier_total,
            'sklearn_anomaly_count': sklearn_anomaly_count,
        },
    }


def _build_compact_llm_summary(dataframe, technical_profile):
    missing_pct = float(technical_profile.get('missing_pct') or 0.0)
    duplicate_rows = int(technical_profile.get('duplicate_rows') or 0)
    anomalies = technical_profile.get('anomalies') or {}
    column_stats = technical_profile.get('column_stats') or {}
    rule_validation = _build_rule_validation_summary(technical_profile)

    critical_selected = list(anomalies.get('critical') or [])[:10]
    high_selected = list(anomalies.get('high') or [])[:5]
    suspect_columns = sorted(
        (
            {
                'name': column_name,
                'error_rate': float(stats.get('error_rate') or 0.0),
                'anomalies': int(stats.get('anomalies') or 0),
            }
            for column_name, stats in column_stats.items()
        ),
        key=lambda item: (item.get('error_rate') or 0.0, item.get('anomalies') or 0),
        reverse=True,
    )[:3]

    total_anomalies = sum(len(items or []) for items in anomalies.values())
    quality_score = max(0, min(100, int(round(100 - (missing_pct * 0.5) - (duplicate_rows * 2) - min(total_anomalies, 20)))))

    return {
        'dataset_quality_score': quality_score,
        'critical_anomalies': critical_selected,
        'high_anomalies': high_selected,
        'suspect_columns': suspect_columns,
        'missing_data_rate': {str(key): float(value) for key, value in list((technical_profile.get('missing_data_rate') or {}).items())[:40]},
        'statistics': {str(key): value for key, value in list((technical_profile.get('statistics') or {}).items())[:40]},
        'rule_validation': rule_validation,
        'technical_profile': {
            'rows': int(technical_profile.get('rows') or len(dataframe.index)),
            'columns': int(technical_profile.get('columns') or len(dataframe.columns)),
            'missing_cells': int(technical_profile.get('missing_cells') or 0),
            'missing_pct': missing_pct,
            'duplicate_rows': duplicate_rows,
            'duplicate_pct': float(technical_profile.get('duplicate_pct') or 0.0),
        },
        'global_stats': {
            'rows': int(technical_profile.get('rows') or len(dataframe.index)),
            'anomalies': total_anomalies,
        },
        'rag': {},
    }


MAX_ANOMALIES = 15
MAX_COLUMNS = 5
REQUIRED_PREPROCESS_KEYS = ['critical_anomalies', 'high_anomalies', 'suspect_columns', 'dataset_quality_score']
PIPELINE_VERSION = os.environ.get('PREPROCESS_PIPELINE_VERSION', '2026.05.18-v2')
SCHEMA_GUARD_VERSION = 'v1'
LLM_FILTER_VERSION = 'v2'
ALLOWED_MEDICAL_COLUMNS = {
    'creatinine',
    'creatinine_basale',
    'potassium',
    'potassium_basale',
    'sodium',
    'sodium_basale',
    'hemoglobine',
    'hemoglobine_basale',
    'albumine',
    'albumine_basale',
    'phosphore',
    'phosphore_basale',
    'calcium',
    'calcium_basale',
    'uree',
    'uree_basale',
    'dfg',
    'dfg_basale',
    'age',
    'age_annees',
    'creatininemie',
    'kaliemie',
}

MEDICAL_COLUMN_ALIASES = {
    'creatinine_basale': 'creatinine',
    'creatininemie': 'creatinine',
    'creatinine': 'creatinine',
    'potassium_basale': 'potassium',
    'potassium_basal': 'potassium',
    'kaliemie': 'potassium',
    'sodium_basale': 'sodium',
    'sodium_basal': 'sodium',
    'hemoglobine_basale': 'hemoglobine',
    'albumine_basale': 'albumine',
    'phosphore_basale': 'phosphore',
    'calcium_basale': 'calcium',
    'uree_basale': 'uree',
    'dfg_basale': 'dfg',
    'age_annees': 'age',
}


def estimate_size(data):
    return len(str(data))


def _extract_payload_column_name(column_entry):
    if isinstance(column_entry, dict):
        for key in ('column', 'col', 'name', 'field', 'label'):
            value = column_entry.get(key)
            if value not in [None, '']:
                return str(value).strip()
        return ''
    return str(column_entry or '').strip()


def _normalize_medical_column_name(column_name):
    normalized = normalize_header(column_name)
    return MEDICAL_COLUMN_ALIASES.get(normalized, normalized)


def _normalize_preprocess_payload_columns(payload):
    payload = dict(payload or {})

    for key in ('critical_anomalies', 'high_anomalies'):
        normalized_items = []
        for item in list(payload.get(key) or []):
            if not isinstance(item, dict):
                normalized_items.append(item)
                continue

            anomaly = dict(item)
            raw_column = _extract_payload_column_name(anomaly)
            if raw_column:
                canonical_column = _normalize_medical_column_name(raw_column)
                if canonical_column != raw_column:
                    anomaly.setdefault('raw_column', raw_column)
                anomaly['column'] = canonical_column
            normalized_items.append(anomaly)
        payload[key] = normalized_items

    normalized_suspect_columns = []
    seen_columns = set()
    for item in list(payload.get('suspect_columns') or []):
        if isinstance(item, dict):
            suspect_column = dict(item)
            raw_column = _extract_payload_column_name(suspect_column)
            if raw_column:
                canonical_column = _normalize_medical_column_name(raw_column)
                if canonical_column != raw_column:
                    suspect_column.setdefault('raw_column', raw_column)
                suspect_column['name'] = canonical_column
                suspect_column['column'] = canonical_column
                seen_key = canonical_column
            else:
                seen_key = str(suspect_column)
            if seen_key in seen_columns:
                continue
            seen_columns.add(seen_key)
            normalized_suspect_columns.append(suspect_column)
            continue

        raw_column = _extract_payload_column_name(item)
        if not raw_column:
            continue
        canonical_column = _normalize_medical_column_name(raw_column)
        if canonical_column in seen_columns:
            continue
        seen_columns.add(canonical_column)
        normalized_suspect_columns.append(canonical_column)

    payload['suspect_columns'] = normalized_suspect_columns
    return payload


def _reduce_preprocess_payload_more(payload):
    payload = dict(payload or {})
    payload['critical_anomalies'] = list(payload.get('critical_anomalies') or [])[:10]
    payload['high_anomalies'] = list(payload.get('high_anomalies') or [])[:5]
    payload['suspect_columns'] = list(payload.get('suspect_columns') or [])[:3]
    payload['missing_data_rate'] = dict(list((payload.get('missing_data_rate') or {}).items())[:15])
    payload['statistics'] = dict(list((payload.get('statistics') or {}).items())[:15])
    payload['rule_validation'] = {
        'status': (payload.get('rule_validation') or {}).get('status'),
        'summary': (payload.get('rule_validation') or {}).get('summary'),
        'issues': list((payload.get('rule_validation') or {}).get('issues') or [])[:5],
        'recommendations': list((payload.get('rule_validation') or {}).get('recommendations') or [])[:5],
    }
    payload['rag'] = {
        'chunk_count': int((payload.get('rag') or {}).get('chunk_count') or 0),
        'retrieved_chunks_count': int((payload.get('rag') or {}).get('retrieved_chunks_count') or 0),
        'section_fusion': list((payload.get('rag') or {}).get('section_fusion') or [])[:5],
        'retrieved_chunks': list((payload.get('rag') or {}).get('retrieved_chunks') or [])[:3],
    }
    payload['technical_profile'] = {
        'rows': (payload.get('technical_profile') or {}).get('rows'),
        'columns': (payload.get('technical_profile') or {}).get('columns'),
        'missing_cells': (payload.get('technical_profile') or {}).get('missing_cells'),
        'missing_pct': (payload.get('technical_profile') or {}).get('missing_pct'),
        'duplicate_rows': (payload.get('technical_profile') or {}).get('duplicate_rows'),
        'duplicate_pct': (payload.get('technical_profile') or {}).get('duplicate_pct'),
        'columns_profile': list((payload.get('technical_profile') or {}).get('columns_profile') or [])[:MAX_COLUMNS],
        'numeric_columns_profile': list((payload.get('technical_profile') or {}).get('numeric_columns_profile') or [])[:MAX_COLUMNS],
        'categorical_columns_profile': list((payload.get('technical_profile') or {}).get('categorical_columns_profile') or [])[:MAX_COLUMNS],
    }
    payload['global_stats'] = {
        'rows': (payload.get('global_stats') or {}).get('rows'),
        'anomalies': (payload.get('global_stats') or {}).get('anomalies'),
    }
    return payload


def _prepare_preprocess_llm_payload(payload):
    payload = dict(payload or {})
    payload = _normalize_preprocess_payload_columns(payload)
    payload_size_before = estimate_size(payload)
    payload['critical_anomalies'] = list(payload.get('critical_anomalies') or [])[:10]
    payload['high_anomalies'] = list(payload.get('high_anomalies') or [])[:5]
    payload['suspect_columns'] = list(payload.get('suspect_columns') or [])[:3]

    def _collect_llm_candidate_columns(source_payload):
        source_payload = source_payload if isinstance(source_payload, dict) else {}
        candidates = set()
        for anomaly in list(source_payload.get('critical_anomalies') or []) + list(source_payload.get('high_anomalies') or []):
            if isinstance(anomaly, dict):
                column_name = _extract_payload_column_name(anomaly)
                if column_name:
                    candidates.add(normalize_header(column_name))
        for column_name in list(source_payload.get('suspect_columns') or []):
            extracted = _extract_payload_column_name(column_name)
            if extracted:
                candidates.add(normalize_header(extracted))
        for column_name in (source_payload.get('missing_data_rate') or {}).keys():
            candidates.add(normalize_header(column_name))
        for column_name in (source_payload.get('statistics') or {}).keys():
            candidates.add(normalize_header(column_name))
        return candidates

    # Build an LLM-safe reduced view to avoid sending technical/noise columns
    LLM_INCLUDE_TOKENS = {
        'creatinine', 'potassium', 'sodium', 'hemoglobine', 'albumine', 'uree', 'dfg', 'age',
        'phosphore', 'calcium', 'gfr', 'outcome', 'mortality', 'deces', 'dialyse', 'transplant'
    }
    LLM_EXCLUDE_TOKENS = {'id', 'uuid', 'row', 'index', 'file', 'filename', 'checksum', 'technical', 'flag', 'is_valid'}

    def _is_llm_column(name):
        norm = normalize_header(str(name))
        if any(tok in norm for tok in LLM_EXCLUDE_TOKENS):
            return False
        # include if matches known clinical tokens or medical aliases
        if norm in MEDICAL_COLUMN_ALIASES:
            return True
        return any(tok in norm for tok in LLM_INCLUDE_TOKENS)

    llm_safe = {}
    # keep same top-level small lists but filtered
    llm_safe['critical_anomalies'] = [a for a in payload.get('critical_anomalies') or [] if _is_llm_column(a.get('column') or '')][:MAX_ANOMALIES]
    llm_safe['high_anomalies'] = [a for a in payload.get('high_anomalies') or [] if _is_llm_column(a.get('column') or '')][:5]
    llm_safe['suspect_columns'] = [c for c in payload.get('suspect_columns') or [] if _is_llm_column(c if isinstance(c, str) else (c.get('column') or c.get('name') or ''))][:MAX_COLUMNS]

    # filter missing_data_rate and statistics to llm columns
    missing = payload.get('missing_data_rate') or {}
    stats = payload.get('statistics') or {}
    llm_safe['missing_data_rate'] = {k: v for k, v in (missing.items() if isinstance(missing, dict) else []) if _is_llm_column(k)}
    llm_safe['statistics'] = {k: v for k, v in (stats.items() if isinstance(stats, dict) else []) if _is_llm_column(k)}

    # keep a compact technical_profile for context but not full columns
    tp = payload.get('technical_profile') or {}
    llm_safe['technical_profile'] = {
        'rows': tp.get('rows'),
        'columns': tp.get('columns'),
        'missing_pct': tp.get('missing_pct'),
    }

    llm_candidates = _collect_llm_candidate_columns(payload)
    llm_kept_candidates = set()
    for anomaly in list(llm_safe.get('critical_anomalies') or []) + list(llm_safe.get('high_anomalies') or []):
        if isinstance(anomaly, dict):
            column_name = _extract_payload_column_name(anomaly)
            if column_name:
                llm_kept_candidates.add(normalize_header(column_name))
    for column_name in list(llm_safe.get('suspect_columns') or []):
        extracted = _extract_payload_column_name(column_name)
        if extracted:
            llm_kept_candidates.add(normalize_header(extracted))
    for column_name in (llm_safe.get('missing_data_rate') or {}).keys():
        llm_kept_candidates.add(normalize_header(column_name))
    for column_name in (llm_safe.get('statistics') or {}).keys():
        llm_kept_candidates.add(normalize_header(column_name))

    llm_filter_ratio = 0.0
    if llm_candidates:
        llm_filter_ratio = round(1.0 - (len(llm_kept_candidates) / float(len(llm_candidates))), 3)
        llm_filter_ratio = max(0.0, min(1.0, llm_filter_ratio))

    # attach the reduced view while keeping full payload for pandas consumers
    payload['llm_safe'] = llm_safe
    payload['llm_filter_ratio'] = llm_filter_ratio
    payload['reduction_applied'] = False

    logger.info('Preprocess LLM-safe payload prepared', extra={
        'llm_filter_ratio': llm_filter_ratio,
        'llm_candidates_count': len(llm_candidates),
        'llm_kept_candidates_count': len(llm_kept_candidates),
    })

    if estimate_size(payload) > 6000:
        payload = _reduce_preprocess_payload_more(payload)
        payload['reduction_applied'] = True

    payload['critical_anomalies'] = list(payload.get('critical_anomalies') or [])[:MAX_ANOMALIES]
    payload['high_anomalies'] = list(payload.get('high_anomalies') or [])[:5]
    payload['suspect_columns'] = list(payload.get('suspect_columns') or [])[:3]

    assert len(payload.get('critical_anomalies') or []) <= MAX_ANOMALIES
    assert len(payload.get('suspect_columns') or []) <= MAX_COLUMNS

    payload['audit'] = {
        'payload_size_before': payload_size_before,
        'payload_size_after': estimate_size(payload),
        'reduction_applied': bool(payload.get('reduction_applied')),
    }

    logger.info('Preprocess payload prepared', extra={
        'payload_size': estimate_size(payload),
        'critical_count': len(payload.get('critical_anomalies') or []),
        'suspect_count': len(payload.get('suspect_columns') or []),
        'llm_filter_ratio': payload.get('llm_filter_ratio', 0.0),
        'payload_stage': 'prepared_before_validation',
    })
    return payload


def validate_payload_schema_only(payload):
    if not isinstance(payload, dict):
        raise ValueError('Payload invalide: dictionnaire attendu.')

    for key in REQUIRED_PREPROCESS_KEYS:
        if key not in payload:
            raise ValueError(f'Payload invalide: cle manquante {key}.')

    if not isinstance(payload.get('critical_anomalies'), list) or not isinstance(payload.get('high_anomalies'), list):
        raise ValueError('Payload invalide: listes attendues pour les anomalies.')
    if not isinstance(payload.get('suspect_columns'), list):
        raise ValueError('Payload invalide: liste attendue pour les colonnes suspectes.')

    dataset_quality_score = payload.get('dataset_quality_score')
    if not isinstance(dataset_quality_score, (int, float)) or dataset_quality_score < 0:
        raise ValueError('Invalid dataset score')

    return True


def validate_preprocess_payload_consistency(payload):
    if not isinstance(payload, dict):
        raise ValueError('Payload invalide: dictionnaire attendu pour le controle final.')

    validate_payload_schema_only(payload)

    llm_safe = payload.get('llm_safe')
    if not isinstance(llm_safe, dict):
        raise ValueError('Payload invalide: vue llm_safe manquante.')

    for key in ('critical_anomalies', 'high_anomalies', 'suspect_columns', 'technical_profile'):
        if key not in llm_safe:
            raise ValueError(f'Payload invalide: cle llm_safe manquante {key}.')

    if not isinstance(payload.get('llm_filter_ratio'), (int, float)):
        raise ValueError('Payload invalide: ratio de filtrage llm invalide.')

    llm_safe_size = estimate_size(llm_safe)
    if llm_safe_size > 12000:
        raise ValueError('Payload invalide: taille llm_safe trop elevee apres reduction.')

    return True


def _build_preprocess_audit_event(session_id, stage, payload, technical_profile, validation_mode='dataset_first', model=None, schema_pass=True, dataset_pass=True, error=None):
    payload = payload if isinstance(payload, dict) else {}
    technical_profile = technical_profile if isinstance(technical_profile, dict) else {}
    audit_meta = payload.get('audit') if isinstance(payload.get('audit'), dict) else {}
    payload_size_before = audit_meta.get('payload_size_before')
    payload_size_after = audit_meta.get('payload_size_after')
    if not isinstance(payload_size_before, int):
        payload_size_before = estimate_size(payload)
    if not isinstance(payload_size_after, int):
        payload_size_after = estimate_size(payload)

    event = {
        'session_id': session_id,
        'patient_id': payload.get('id_patient') or technical_profile.get('id_patient') or session_id,
        'pipeline_version': PIPELINE_VERSION,
        'stage': stage,
        'schema_pass': bool(schema_pass),
        'dataset_pass': bool(dataset_pass),
        'llm_safe_ratio': round(float(payload.get('llm_filter_ratio') or 0.0), 3),
        'reduction_applied': bool(payload.get('reduction_applied') or audit_meta.get('reduction_applied')),
        'payload_size_before': int(payload_size_before),
        'payload_size_after': int(payload_size_after),
        'validation_mode': validation_mode,
        'model': model,
        'decision': 'fallback' if error is not None else 'llm',
        'fallback_used': bool(error is not None),
        'pipeline': {
            'version': PIPELINE_VERSION,
            'schema_version': SCHEMA_GUARD_VERSION,
            'llm_filter_version': LLM_FILTER_VERSION,
            'validation_mode_version': 'v1',
        },
    }
    if error is not None:
        event['error'] = str(error)
    logger.info('PREPROCESS_AUDIT %s', json.dumps(event, ensure_ascii=False, default=str))
    return event


def replay_preprocess_pipeline(audit_event, progress_callback=None, force_mode='replay'):
    audit_event = audit_event if isinstance(audit_event, dict) else {}
    session_id = audit_event.get('session_id') or audit_event.get('preprocess_id') or audit_event.get('patient_id')
    if not session_id:
        raise ValueError('Audit invalide: session_id manquant pour le replay.')

    session = _load_preprocess_session(session_id)
    if isinstance(session, dict) and session.get('report'):
        report = dict(session.get('report') or {})
        report['replayed_from_audit'] = True
        report['replay_mode'] = force_mode
        report['replay_source'] = {
            'session_id': session_id,
            'pipeline_version': audit_event.get('pipeline_version') or report.get('pipeline', {}).get('version') or PIPELINE_VERSION,
            'decision': audit_event.get('decision') or ('fallback' if audit_event.get('fallback_used') else 'llm'),
            'fallback_used': bool(audit_event.get('fallback_used')),
        }
        return report

    input_snapshot = audit_event.get('input_snapshot') if isinstance(audit_event.get('input_snapshot'), dict) else {}
    original_rows = input_snapshot.get('original_rows') if isinstance(input_snapshot.get('original_rows'), list) else []
    columns = input_snapshot.get('columns') if isinstance(input_snapshot.get('columns'), list) else []
    dataframe = _rows_to_dataframe(original_rows, columns=columns)
    technical_profile = input_snapshot.get('technical_profile') if isinstance(input_snapshot.get('technical_profile'), dict) else _build_technical_profile(dataframe)

    if audit_event.get('fallback_used'):
        return _build_deterministic_analysis_fallback(
            dataframe,
            technical_profile,
            'Replay from audit event: fallback-used snapshot.',
        )

    return _call_ollama_qwen_analysis(
        dataframe,
        technical_profile,
        session_id=session_id,
        progress_callback=progress_callback,
    )


def validate_payload(payload, technical_profile=None, validation_mode='dataset_first'):
    if not isinstance(payload, dict):
        raise ValueError('Payload invalide: dictionnaire attendu.')

    validate_payload_schema_only(payload)

    validation_mode = str(validation_mode or 'dataset_first').lower()
    if validation_mode not in {'dataset_first', 'soft', 'strict'}:
        validation_mode = 'dataset_first'

    normalized_payload = _normalize_preprocess_payload_columns(payload)
    payload.clear()
    payload.update(normalized_payload)
    technical_profile = technical_profile if isinstance(technical_profile, dict) else {}
    # Dataset-first: only enforce column-name membership when metadata explicitly
    # provides a dataset column list. If metadata is absent, do not infer it from
    # the payload because that can create a false source of truth.
    tp_columns = technical_profile.get('column_names') if isinstance(technical_profile.get('column_names'), (list, tuple)) else None
    known_columns = None
    if tp_columns:
        known_columns = {
            normalize_header(str(column))
            for column in tp_columns
            if column is not None and str(column).strip()
        }

    critical_anomalies = payload.get('critical_anomalies') or []
    suspect_columns = payload.get('suspect_columns') or []

    if not isinstance(critical_anomalies, list) or not isinstance(suspect_columns, list):
        raise ValueError('Payload invalide: listes attendues pour anomalies et colonnes suspectes.')

    unknown_columns = []

    for anomaly in critical_anomalies:
        if not isinstance(anomaly, dict):
            raise ValueError('Payload invalide: anomalie critique non structuree.')
        column_name = _extract_payload_column_name(anomaly)
        if not column_name:
            raise ValueError('Payload invalide: colonne d anomalie manquante.')
        normalized_column = _normalize_medical_column_name(column_name)
        anomaly['column'] = normalized_column
        # If metadata exists, log mismatches but never block validation.
        if validation_mode == 'strict' and known_columns is not None and normalized_column not in known_columns and normalized_column not in unknown_columns:
            unknown_columns.append(normalized_column)
        if 'value' not in anomaly:
            raise ValueError('Payload invalide: valeur d anomalie manquante.')
        value = anomaly.get('value')
        if isinstance(value, (dict, list, set, tuple)):
            raise ValueError('Payload invalide: valeur d anomalie mal typee.')

    for column_name in suspect_columns:
        normalized_column = _extract_payload_column_name(column_name)
        if not normalized_column:
            raise ValueError('Payload invalide: colonne suspecte manquante.')
        normalized_column = _normalize_medical_column_name(normalized_column)
        # Same logic for suspect columns: metadata can warn, but cannot reject.
        if validation_mode == 'strict' and known_columns is not None and normalized_column not in known_columns and normalized_column not in unknown_columns:
            unknown_columns.append(normalized_column)

    if unknown_columns:
        logger.info('Payload preprocess: columns not present in metadata allowed under dataset-first mode', extra={
            'schema_pass': True,
            'dataset_pass': True,
            'validation_mode': validation_mode,
            'unknown_columns_count': len(dict.fromkeys(unknown_columns)),
        })
        logger.warning('Payload preprocess: colonnes medicales non reconnues conservees', extra={
            'columns': list(dict.fromkeys(unknown_columns)),
        })
    else:
        logger.info('Payload preprocess validation completed', extra={
            'schema_pass': True,
            'dataset_pass': True,
            'validation_mode': validation_mode,
            'unknown_columns_count': 0,
        })

    if len(critical_anomalies) > MAX_ANOMALIES:
        raise ValueError('Payload invalide: trop danomalies critiques.')
    if len(suspect_columns) > MAX_COLUMNS:
        raise ValueError('Payload invalide: trop de colonnes suspectes.')

    return True


def _compute_final_confidence(technical_profile, issues=None, compact_summary=None):
    technical_profile = technical_profile if isinstance(technical_profile, dict) else {}
    issues = issues if isinstance(issues, list) else []
    compact_summary = compact_summary if isinstance(compact_summary, dict) else {}

    confidence = 1.0
    missing_pct = float(technical_profile.get('missing_pct') or 0.0)
    duplicate_rows = int(technical_profile.get('duplicate_rows') or 0)
    anomaly_total = len(compact_summary.get('critical_anomalies') or []) + len(compact_summary.get('high_anomalies') or [])
    severity_count = {'critical': 0, 'warning': 0, 'info': 0}

    for item in issues:
        severity = str((item or {}).get('severity', 'info')).lower()
        if severity in severity_count:
            severity_count[severity] += 1

    if anomaly_total > 20:
        confidence -= 0.25
    elif anomaly_total > 10:
        confidence -= 0.15
    elif anomaly_total > 0:
        confidence -= 0.05

    if missing_pct > 30:
        confidence -= 0.30
    elif missing_pct > 15:
        confidence -= 0.20
    elif missing_pct > 5:
        confidence -= 0.10

    if duplicate_rows > 0:
        confidence -= min(0.10, duplicate_rows * 0.01)

    confidence -= min(0.25, severity_count['critical'] * 0.08)
    confidence -= min(0.10, severity_count['warning'] * 0.03)

    confidence = max(0.0, min(1.0, round(confidence, 2)))
    if confidence >= 0.85:
        label = 'elevee'
    elif confidence >= 0.65:
        label = 'bonne'
    elif confidence >= 0.45:
        label = 'moderee'
    else:
        label = 'faible'

    return {
        'confidence_score': confidence,
        'confidence_pct': int(round(confidence * 100)),
        'confidence_label': label,
        'signals': {
            'missing_pct': missing_pct,
            'duplicate_rows': duplicate_rows,
            'anomaly_total': anomaly_total,
            'critical_issues': severity_count['critical'],
            'warning_issues': severity_count['warning'],
        },
    }


def _get_section_prefix_for_column(column_name):
    normalized = normalize_header(column_name)
    for prefix, section_name in SECTION_PREFIX_MAP.items():
        if normalized.startswith(prefix):
            return section_name
    return 'generic_data'


def _build_preprocess_chunks(dataframe, technical_profile, max_rows_per_chunk=20):
    chunks = []
    columns = [str(column) for column in dataframe.columns.tolist()]
    grouped_columns = {}

    for column in columns:
        grouped_columns.setdefault(_get_section_prefix_for_column(column), []).append(column)

    for section_name, section_columns in grouped_columns.items():
        if not section_columns:
            continue
        section_frame = dataframe[section_columns]
        if len(section_frame.index) <= max_rows_per_chunk:
            chunks.append({
                'chunk_id': f'{section_name}:full',
                'kind': 'section',
                'section': section_name,
                'columns': section_columns,
                'rows_range': [0, max(0, len(section_frame.index) - 1)],
                'row_count': int(len(section_frame.index)),
                'preview_rows': _dataframe_to_rows(section_frame.head(3)),
            })
        else:
            for start_index in range(0, len(section_frame.index), max_rows_per_chunk):
                end_index = min(start_index + max_rows_per_chunk, len(section_frame.index))
                chunk_frame = section_frame.iloc[start_index:end_index]
                chunks.append({
                    'chunk_id': f'{section_name}:rows:{start_index}-{end_index - 1}',
                    'kind': 'row_batch',
                    'section': section_name,
                    'columns': section_columns,
                    'rows_range': [start_index, end_index - 1],
                    'row_count': int(len(chunk_frame.index)),
                    'preview_rows': _dataframe_to_rows(chunk_frame.head(3)),
                })

    if not chunks:
        chunks.append({
            'chunk_id': 'generic:empty',
            'kind': 'fallback',
            'section': 'generic_data',
            'columns': columns,
            'rows_range': [0, 0],
            'row_count': 0,
            'preview_rows': [],
        })

    technical_profile['chunk_count'] = len(chunks)
    technical_profile['chunks'] = [
        {
            'chunk_id': chunk['chunk_id'],
            'kind': chunk['kind'],
            'section': chunk['section'],
            'row_count': chunk['row_count'],
            'columns_count': len(chunk['columns']),
        }
        for chunk in chunks
    ]
    return chunks


def _build_retrieval_context(dataframe, chunks, technical_profile, stage_name='diagnostic', max_chunks=4, progress_callback=None):
    return build_rag_context(
        dataframe,
        chunks,
        technical_profile,
        stage_name=stage_name,
        max_chunks=max_chunks,
        progress_callback=progress_callback,
    )


def _determine_preprocess_route(technical_profile):
    return estimate_route(technical_profile)


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
        repaired_candidates.append(normalized_candidate.replace('“', '"').replace('”', '"').replace('’', "'").replace('`', '"'))

    permissive_candidates = []
    for candidate in repaired_candidates:
        compact_candidate = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]+', ' ', candidate)
        permissive_candidates.append(compact_candidate)
        permissive_candidates.append(re.sub(r'\bNone\b', 'null', compact_candidate))
        permissive_candidates.append(re.sub(r'\bTrue\b', 'true', compact_candidate))
        permissive_candidates.append(re.sub(r'\bFalse\b', 'false', compact_candidate))

    for candidate in repaired_candidates + permissive_candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    try:
        import ast

        for candidate in permissive_candidates:
            try:
                parsed = ast.literal_eval(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue
    except Exception:
        pass

    return None


def _repair_llm_text(value):
    if isinstance(value, dict):
        return {str(key): _repair_llm_text(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_repair_llm_text(item) for item in value]

    if not isinstance(value, str):
        return value

    text = value
    if not text:
        return text

    mojibake_candidates = [text]
    for source_encoding in ('latin1', 'cp1252', 'cp437', 'cp850', 'iso-8859-1'):
        try:
            repaired = text.encode(source_encoding).decode('utf-8')
        except Exception:
            continue
        if repaired not in mojibake_candidates:
            mojibake_candidates.append(repaired)

    suspicious_markers = '├┤╡╢╖╕╣║╗╝▒■�ÃÂ'

    def _score(candidate):
        return sum(1 for character in candidate if character in suspicious_markers)

    best_candidate = min(mojibake_candidates, key=_score)
    return best_candidate


def _parse_llm_analysis_response(raw_response):
    if isinstance(raw_response, dict):
        return _repair_llm_text(raw_response)

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
        return _repair_llm_text(parsed)

    # Dernier recours: tenter de récupérer uniquement la première structure JSON fermée.
    extracted = _extract_balanced_json_candidate(response_text)
    if extracted:
        parsed = _repair_json_text(extracted)
        if parsed is not None:
            return _repair_llm_text(parsed)

    return {
        'summary': _repair_llm_text(response_text[:1200]),
        'issues': [],
        'recommendations': [],
        'correction_plan': {},
        'corrected_preview_rows': [],
        'column_assessment': [],
        'limitations': ['Le modele a repondu, mais le JSON est invalide.'],
    }


def _build_llm_payload(dataframe, technical_profile):
    return _build_compact_llm_summary(dataframe, technical_profile)


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


def _check_ollama_health(timeout_seconds=8):
    return check_llm_health(timeout_seconds=timeout_seconds)


def _build_deterministic_analysis_fallback(dataframe, technical_profile, reason_message):
    rows_count = int(len(dataframe.index))
    issues = []
    recommendations = []
    rule_validation = _build_rule_validation_summary(technical_profile)

    missing_pct = float(technical_profile.get('missing_pct') or 0.0)
    duplicate_rows = int(technical_profile.get('duplicate_rows') or 0)
    sklearn_anomaly_count = int(technical_profile.get('sklearn_anomaly_count') or 0)

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

    if sklearn_anomaly_count > 0:
        issues.append({
            'severity': 'info',
            'category': 'sklearn_anomalies',
            'column': '*',
            'rows': sklearn_anomaly_count,
            'explanation': f'{sklearn_anomaly_count} anomalie(s) detectee(s) par IsolationForest.',
        })
        recommendations.append('Comparer les anomalies IsolationForest avec le contexte clinique.')

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

    recommendations.extend(rule_validation.get('recommendations') or [])
    recommendations = list(dict.fromkeys(recommendations))

    quality_score = max(5, min(100, int(round(100 - (missing_pct * 0.5) - (duplicate_rows * 2) - min(outlier_total, 20)))))

    return {
        'quality_score': quality_score,
        'summary': 'Analyse realisee via profilage local (pandas/numpy/sklearn) et validation des regles metier suite a indisponibilite LLM.',
        'issues': issues[:6],
        'recommendations': recommendations[:5],
        'correction_plan': correction_plan,
        'corrected_preview_rows': [],
        'column_assessment': [],
        'limitations': [
            'LLM indisponible: fallback deterministe applique.',
            reason_message,
        ],
        'rule_validation': rule_validation,
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
        'compact_summary': _build_compact_llm_summary(dataframe, technical_profile),
        'model_used': 'deterministic_fallback',
        'attempt': 'fallback_local',
        'stage': 'pass1_diagnostic',
        'second_pass': {'status': 'skipped_fallback'},
        'route': {'mode': 'analytics_rules', 'label': 'deterministic_profiling_rules', 'reason': reason_message},
        'pipeline': {
            'stage': 'profiling_and_rules',
            'chunks_count': technical_profile.get('chunk_count', 0),
            'retrieval': 'skipped',
        },
    }


def _call_ollama_qwen_analysis(dataframe, technical_profile, session_id=None, progress_callback=None):
    route = _determine_preprocess_route(technical_profile)
    chunks = _build_preprocess_chunks(dataframe, technical_profile)
    retrieval_context = _build_retrieval_context(
        dataframe,
        chunks,
        technical_profile,
        stage_name='diagnostic',
        max_chunks=int(os.environ.get('RAG_MAX_CHUNKS', '4')),
        progress_callback=progress_callback,
    )
    technical_profile['chunk_count'] = len(chunks)
    technical_profile['chunks'] = retrieval_context.get('chunk_summaries', [])
    technical_profile['retrieved_chunks'] = retrieval_context.get('retrieved_chunks', [])

    model_name = route.get('primary_model') or get_llm_model_name()
    timeout_seconds = int(os.environ.get('LLM_TIMEOUT_SECONDS', os.environ.get('OLLAMA_TIMEOUT_SECONDS', '300')))
    primary_timeout_seconds = int(
        route.get('primary_timeout_seconds')
        or os.environ.get('LLM_PRIMARY_TIMEOUT_SECONDS', os.environ.get('OLLAMA_PRIMARY_TIMEOUT_SECONDS', str(min(timeout_seconds, 180))))
    )
    primary_timeout_seconds = min(primary_timeout_seconds, 240)
    fallback_timeout_seconds = int(
        route.get('fallback_timeout_seconds')
        or os.environ.get('LLM_FALLBACK_TIMEOUT_SECONDS', os.environ.get('OLLAMA_FALLBACK_TIMEOUT_SECONDS', str(min(timeout_seconds, 300))))
    )
    fallback_timeout_seconds = min(fallback_timeout_seconds, 300)
    retry_max_columns = int(os.environ.get('LLM_RETRY_MAX_COLUMNS', os.environ.get('OLLAMA_RETRY_MAX_COLUMNS', '20')))
    retry_preview_rows = int(os.environ.get('LLM_RETRY_PREVIEW_ROWS', os.environ.get('OLLAMA_RETRY_PREVIEW_ROWS', '2')))
    pass1_num_predict = int(os.environ.get('LLM_PASS1_MAX_TOKENS', os.environ.get('OLLAMA_PASS1_NUM_PREDICT', os.environ.get('OLLAMA_NUM_PREDICT', '8192'))))
    pass2_num_predict = int(os.environ.get('LLM_PASS2_MAX_TOKENS', os.environ.get('OLLAMA_PASS2_NUM_PREDICT', os.environ.get('OLLAMA_NUM_PREDICT', '16384'))))
    retry_num_predict = int(os.environ.get('LLM_RETRY_MAX_TOKENS', os.environ.get('OLLAMA_RETRY_NUM_PREDICT', str(pass2_num_predict))))
    pass1_num_predict = min(pass1_num_predict, 512)
    pass2_num_predict = min(pass2_num_predict, 768)
    retry_num_predict = min(retry_num_predict, 768)

    prompt_payload = _build_llm_payload(dataframe, technical_profile)
    prompt_payload['rag'] = {
        'chunk_count': len(chunks),
        'retrieved_chunks': [
            {
                'chunk_id': chunk.get('chunk_id'),
                'section': chunk.get('section'),
                'kind': chunk.get('kind'),
                'row_count': chunk.get('row_count'),
                'column_count': chunk.get('column_count'),
                'missing_pct': chunk.get('missing_pct'),
                'duplicate_rows': chunk.get('duplicate_rows'),
                'critical_signals': chunk.get('critical_signals', [])[:6],
                'deterministic_summary': chunk.get('deterministic_summary'),
            }
            for chunk in retrieval_context.get('retrieved_chunks', [])
            if isinstance(chunk, dict)
        ],
        'retrieved_chunks_count': retrieval_context.get('retrieved_chunks_count', 0),
        'section_fusion': [
            item if isinstance(item, str) else json.dumps(item, ensure_ascii=False, default=str)
            for item in (retrieval_context.get('section_fusion', []) or [])[:20]
        ],
        'vector_store': retrieval_context.get('vector_store', {}),
    }
    prompt_payload = _prepare_preprocess_llm_payload(prompt_payload)
    fallback_payload = prompt_payload

    if not should_use_llm(technical_profile, prompt_payload):
        audit_event = _build_preprocess_audit_event(
            session_id,
            'llm_sla_gate',
            prompt_payload,
            technical_profile,
            validation_mode='deterministic_first',
            model=model_name,
            schema_pass=True,
            dataset_pass=True,
            error='LLM SLA threshold reached',
        )
        deterministic_result = _build_deterministic_analysis_fallback(
            dataframe,
            technical_profile,
            'LLM SLA gate: payload trop lourd pour un appel LLM fiable.',
        )
        deterministic_result['audit_log'] = [audit_event]
        deterministic_result['route'] = {
            'mode': 'deterministic_first',
            'label': 'deterministic_first_sla',
            'reason': 'LLM SLA gate reached before LLM call.',
        }
        return deterministic_result

    logger.info('Preprocess payload validation stage', extra={
        'payload_stage': 'after_reduce_before_final_guard',
        'payload_size': estimate_size(prompt_payload),
        'has_llm_safe': 'llm_safe' in prompt_payload,
        'llm_filter_ratio': prompt_payload.get('llm_filter_ratio', 0.0),
        'reduction_applied': bool(prompt_payload.get('reduction_applied')),
    })
    try:
        validate_preprocess_payload_consistency(prompt_payload)
    except Exception as error:
        audit_event = _build_preprocess_audit_event(
            session_id,
            'final_guard',
            prompt_payload,
            technical_profile,
            validation_mode='final_consistency_guard',
            model=model_name,
            schema_pass=True,
            dataset_pass=False,
            error=error,
        )
        logger.warning('Preprocess payload final consistency check failed, using deterministic fallback', extra={
            'error': str(error),
            'payload_size': estimate_size(prompt_payload),
            'payload_stage': 'final_consistency_guard_failed',
        })
        deterministic_result = _build_deterministic_analysis_fallback(dataframe, technical_profile, f'Final consistency check failed: {error}')
        deterministic_result['limitations'] = list(dict.fromkeys([
            'Final consistency guard failed: payload llm_safe trop volumineux ou incomplet.',
            f'Final consistency check failed: {error}',
        ] + (deterministic_result.get('limitations') if isinstance(deterministic_result.get('limitations'), list) else [])))
        deterministic_result['audit_log'] = [audit_event]
        return deterministic_result
    try:
        validate_payload(prompt_payload, technical_profile=technical_profile)
    except Exception as error:
        audit_event = _build_preprocess_audit_event(
            session_id,
            'final_guard',
            prompt_payload,
            technical_profile,
            validation_mode='dataset_first',
            model=model_name,
            schema_pass=True,
            dataset_pass=False,
            error=error,
        )
        logger.warning('Payload validation failed, using deterministic fallback', extra={
            'error': str(error),
            'payload_size': estimate_size(prompt_payload),
            'payload_stage': 'validation_failed_before_llm',
        })
        deterministic_result = _build_deterministic_analysis_fallback(dataframe, technical_profile, f'Payload validation failed: {error}')
        deterministic_result['audit_log'] = [audit_event]
        return deterministic_result

    audit_event = _build_preprocess_audit_event(
        session_id,
        'final_guard',
        prompt_payload,
        technical_profile,
        validation_mode='dataset_first',
        model=model_name,
        schema_pass=True,
        dataset_pass=True,
    )

    logger.info('Preprocess payload validated before LLM', extra={
        'payload_stage': 'after_validate_payload',
        'payload_size': estimate_size(prompt_payload),
        'llm_filter_ratio': prompt_payload.get('llm_filter_ratio', 0.0),
        'reduction_applied': bool(prompt_payload.get('reduction_applied')),
    })
    def _notify_progress(message):
        if callable(progress_callback):
            try:
                progress_callback(message)
            except Exception:
                pass

    def _build_pass1_prompt(payload_for_prompt):
        llm_input = payload_for_prompt.get('llm_safe') if isinstance(payload_for_prompt, dict) and 'llm_safe' in payload_for_prompt else payload_for_prompt
        return (
            'Tu es un expert nephrologue. Analyse uniquement ce JSON. '
            'Taches : detecter erreurs de saisie, verifier coherence biologique, evaluer gravite medicale, juger fiabilite du dataset, produire rapport structure. '
            'Important : ne pas inventer de donnees, ne pas demander plus d informations, se baser uniquement sur le JSON. '
            'Retourne STRICTEMENT un JSON valide, sans texte autour. '
            'Format obligatoire: {"résumé_global":string,"anomalies_critiques":[],"erreurs_de_saisie_probables":[],"incoherences_biologiques":[],"colonnes_suspectes":[],"conclusion_medicale":string}. '
            'JSON d entree: ' + json.dumps(llm_input, ensure_ascii=False, default=str)
        )

    def _build_pass2_prompt(payload_for_prompt):
        llm_input = payload_for_prompt.get('llm_safe') if isinstance(payload_for_prompt, dict) and 'llm_safe' in payload_for_prompt else payload_for_prompt
        return (
            'Tu es un expert nephrologue en correction de dataset medical. Analyse uniquement ce JSON. '
            'Taches : detecter erreurs de saisie, verifier coherence biologique, evaluer gravite medicale, juger fiabilite du dataset, produire rapport structure. '
            'Important : ne pas inventer de donnees, ne pas demander plus d informations, se baser uniquement sur le JSON. '
            'Retourne STRICTEMENT un JSON valide, sans texte hors JSON. '
            'Format obligatoire: {"correction_plan":{"outlier_corrections":[],"biological_rules":[],"fill_missing":{},"parse_dates":[],"rename_columns":{},"type_casts":{}},"corrected_preview_rows":[],"recommendations":[],"issues_found":[],"clinical_interpretation":string,"nephrology_consistency":string}. '
            'Le JSON d entree est: ' + json.dumps(llm_input, ensure_ascii=False, default=str)
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

        stage_errors = []
        system_prompt = get_system_prompt()
        for attempt in attempts:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': attempt['prompt']},
            ]
            print(f"[LLM] start stage={stage_name} attempt={attempt['label']} model={attempt['model']}")
            logger.info(
                'Preprocess LLM call start',
                extra={
                    'stage': stage_name,
                    'attempt': attempt['label'],
                    'model': attempt['model'],
                    'timeout_seconds': attempt['timeout_seconds'],
                    'max_tokens': attempt['num_predict'],
                },
            )
            try:
                result = run_json_completion(
                    messages,
                    model=attempt['model'],
                    max_tokens=attempt['num_predict'],
                    timeout_seconds=attempt['timeout_seconds'],
                )
                raw_response = result.get('content')
                parsed_response = _parse_llm_analysis_response(raw_response)
                parsed_response['analysis_pack'] = attempt['analysis_pack']
                parsed_response['model_used'] = result.get('model_used') or attempt['model']
                parsed_response['attempt'] = attempt['label']
                parsed_response['stage'] = stage_name
                return parsed_response
            except Exception as error:
                logger.warning(
                    'Preprocess LLM call failed',
                    extra={
                        'stage': stage_name,
                        'attempt': attempt['label'],
                        'model': attempt['model'],
                        'error': str(error),
                    },
                )
                stage_errors.append(
                    f"[{stage_name}:{attempt['label']}:{attempt['model']}] LLM error: {error}"
                )

        error_summary = '; '.join(stage_errors) if stage_errors else 'Aucune reponse recue'
        lower_errors = error_summary.lower()
        limitations = []
        if 'timed out' in lower_errors or 'timeout' in lower_errors:
            limitations.append(
                f'Delai depasse: le moteur LLM n a pas repondu dans la fenetre configured (primary={primary_timeout_seconds}s, fallback={fallback_timeout_seconds}s, plafond={timeout_seconds}s).'
            )
        if 'connection refused' in lower_errors or 'errno 111' in lower_errors:
            limitations.append(
                'Connexion refusee: l URL LLM ciblee n est pas joignable depuis le backend. Verifier la configuration VLLM/LITELLM et le reseau Docker.'
            )
        if '405' in lower_errors or 'method not allowed' in lower_errors:
            limitations.append('Methode invalide detectee: endpoint LLM incompatible (verifier /v1/chat/completions).')
        if not limitations:
            limitations.append('Aucun diagnostic automatique supplementaire disponible.')

        return {
            'unavailable': True,
            'summary': f'Analyse LLM indisponible ({stage_name}): {error_summary}',
            'issues': [],
            'recommendations': ['Verifier la connexion au moteur LLM et reessayer'],
            'correction_plan': {},
            'corrected_preview_rows': [],
            'column_assessment': [],
            'limitations': limitations,
            'analysis_pack': primary_pack,
            'model_used': model_name,
            'stage': stage_name,
            'needs_correction_plan': True,
        }

    _notify_progress('Analyse LLM - passe 1/2 (diagnostic)...')
    pass1_result = _run_stage(
        stage_name='pass1_diagnostic',
        primary_prompt=_build_pass1_prompt(prompt_payload),
        fallback_prompt=_build_pass1_prompt(fallback_payload),
        primary_pack=prompt_payload,
        fallback_pack=fallback_payload,
        primary_predict=pass1_num_predict,
        fallback_predict=retry_num_predict,
    )

    if pass1_result.get('unavailable'):
        deterministic_result = _build_deterministic_analysis_fallback(
            dataframe,
            technical_profile,
            pass1_result.get('summary', 'Passe 1 indisponible.'),
        )
        deterministic_result['section_analyses'] = retrieval_context.get('section_fusion', [])
        deterministic_result['rag_context'] = retrieval_context
        deterministic_result['audit_log'] = [audit_event]
        return deterministic_result

    pass1_issues = pass1_result.get('issues') if isinstance(pass1_result.get('issues'), list) else []
    pass1_recommendations = pass1_result.get('recommendations') if isinstance(pass1_result.get('recommendations'), list) else []
    pass1_limitations = pass1_result.get('limitations') if isinstance(pass1_result.get('limitations'), list) else []

    # FORCER l'exécution de la passe 2 - MODIFICATION ICI
    needs_correction_plan = True  # Toujours exécuter la passe 2

    if not needs_correction_plan:
        pass1_result['correction_plan'] = pass1_result.get('correction_plan') if isinstance(pass1_result.get('correction_plan'), dict) else {}
        pass1_result['second_pass'] = {'status': 'skipped'}
        pass1_result['route'] = route
        pass1_result['section_analyses'] = retrieval_context.get('section_fusion', [])
        pass1_result['rag_context'] = retrieval_context
        pass1_result['pipeline'] = {
            'stage': 'pass1_diagnostic_completed',
            'chunks_count': len(chunks),
            'retrieved_chunks_count': retrieval_context.get('retrieved_chunks_count', 0),
            'retrieval': retrieval_context.get('retrieval_policy'),
            'vector_store': retrieval_context.get('vector_store', {}),
        }
        return pass1_result

    _notify_progress('Analyse LLM - passe 2/2 (plan de correction)...')
    pass2_primary_payload = {
        'analysis_pack': prompt_payload,
    'rag_context': retrieval_context, 
    'diagnostic': {
        'quality_score': pass1_result.get('quality_score'),
        'summary': pass1_result.get('summary'),
        'issues': pass1_issues[:6],
        'recommendations': pass1_recommendations[:5]
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
        'section_analyses': retrieval_context.get('section_fusion', []),
        'rag_context': retrieval_context,
        'pipeline': {
            'stage': 'pass2_correction_plan',
            'chunks_count': len(chunks),
            'retrieved_chunks_count': retrieval_context.get('retrieved_chunks_count', 0),
            'retrieval': retrieval_context.get('retrieval_policy'),
            'vector_store': retrieval_context.get('vector_store', {}),
        },
        'audit_log': [audit_event],
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
        # Ajouter un plan de correction par défaut
        final_result['correction_plan'] = {
            'fill_missing': {},
            'parse_dates': ['date_debut_dialyse', 'date_naissance'],
            'outlier_corrections': [
                {'column': 'hemoglobine_basale', 'lower_bound': 5, 'upper_bound': 20},
                {'column': 'creatinine_basale', 'lower_bound': 50, 'upper_bound': 500},
                {'column': 'albumine_basale', 'lower_bound': 15, 'upper_bound': 60},
                {'column': 'potassium_basale', 'lower_bound': 2.5, 'upper_bound': 7.0},
            ]
        }
        if not final_result.get('recommendations'):
            final_result['recommendations'] = [
                "Nettoyer les valeurs aberrantes biologiques",
                "Standardiser les formats de date",
                "Imputer les valeurs manquantes par médiane/mode"
            ]
        final_result['audit_log'] = [audit_event]
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
        if issues:
            for issue in issues[:5]:
                category = str(issue.get('category') or '').lower()
                column_name = str(issue.get('column') or '*')
                if category == 'missing_values':
                    recommendations.append(f'Completer ou imputer les valeurs manquantes pour {column_name}.')
                elif category == 'duplicates':
                    recommendations.append(f'Dedoublonner les lignes concernees autour de {column_name}.')
                elif category == 'outliers':
                    recommendations.append(f'Verifier les valeurs extremes detectees dans {column_name}.')
                else:
                    recommendations.append(f'Reviser manuellement le point de controle signale sur {column_name}.')
        if not recommendations:
            recommendations = [
                'Verifier la qualite globale du dataset.',
                'Controler les colonnes critiques avant integration.',
                'Appliquer une normalisation et une validation metier avant import.',
            ]

    corrected_preview_rows = _dataframe_to_rows(corrected_df.head(20))
    compact_summary = llm_analysis.get('compact_summary') if isinstance(llm_analysis, dict) else {}
    compact_summary = compact_summary if isinstance(compact_summary, dict) else {}
    final_confidence = _compute_final_confidence(technical_profile, issues=issues, compact_summary=compact_summary)
    suspect_columns = compact_summary.get('suspect_columns') or technical_profile.get('suspect_columns') or []
    critical_anomalies = compact_summary.get('critical_anomalies') or technical_profile.get('critical_anomalies') or []
    high_anomalies = compact_summary.get('high_anomalies') or technical_profile.get('high_anomalies') or []
    medical_report = {
        'resume_global': llm_analysis.get('summary') if isinstance(llm_analysis, dict) else '',
        'anomalies_critiques': critical_anomalies[:20],
        'erreurs_de_saisie_probables': [
            item for item in critical_anomalies[:20]
            if str(item.get('type') or '').lower() == 'invalid_value'
        ],
        'incoherences_biologiques': [
            item for item in critical_anomalies[:20]
            if str(item.get('type') or '').lower() != 'invalid_value'
        ],
        'colonnes_suspectes': list(dict.fromkeys([str(column) for column in suspect_columns if column]))[:20],
        'conclusion_medicale': llm_analysis.get('conclusion_medicale') if isinstance(llm_analysis, dict) else '',
        'high_anomalies': high_anomalies[:10],
        'score_confiance': final_confidence,
    }

    return {
        'summary': {
            'rows': int(len(dataframe.index)),
            'columns': int(len(dataframe.columns)),
            'quality_score': quality_score,
            'confidence_score': final_confidence['confidence_score'],
            'confidence_pct': final_confidence['confidence_pct'],
            'confidence_label': final_confidence['confidence_label'],
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
        'medical_report': medical_report,
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
    # Allow unauthenticated access so the UI can display LLM status before login
    permission_classes = [AllowAny]

    def get(self, request):
        timeout_seconds = int(os.environ.get('LLM_HEALTH_TIMEOUT_SECONDS', os.environ.get('OLLAMA_HEALTH_TIMEOUT_SECONDS', '8')))
        health = _check_ollama_health(timeout_seconds=timeout_seconds)
        model_name = get_llm_model_name()
        if health.get('connected'):
            return Response(
                {
                    'connected': True,
                    'configured_model': model_name,
                    'base_url': health.get('base_url'),
                    'endpoint': health.get('endpoint'),
                    'models_count': health.get('models_count', 0),
                    'models': health.get('models', []),
                    'message': 'Moteur LLM connecté.',
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
                'message': 'Moteur LLM indisponible depuis le backend.',
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


class PatientPreprocessReplayView(APIView):
    permission_classes = [CanViewPatients]

    def post(self, request, session_id):
        session = _load_preprocess_session(session_id)
        if not session:
            return Response({'error': 'Session de pretraitement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        audit_event = request.data.get('audit_event')
        if not isinstance(audit_event, dict):
            audit_log = session.get('report', {}).get('audit_log') if isinstance(session.get('report'), dict) else []
            audit_event = audit_log[0] if isinstance(audit_log, list) and audit_log else {'session_id': session_id}

        try:
            replayed_report = replay_preprocess_pipeline(audit_event)
        except Exception as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'preprocess_id': session_id,
                'replayed': True,
                'report': replayed_report,
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