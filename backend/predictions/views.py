import re
from datetime import date, datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import LinearSVC

from patients.models import Patient

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

MODEL_DIRECTORY = settings.BASE_DIR / 'predictions' / 'models'
MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)

FEATURE_KEYS = [
    'age',
    'sexe',
    'comorbidite_statut_diabete',
    'biologie_creatinine_mg_l',
    'biologie_dfg_mdrd_ml_min_1_73m2',
    'biologie_albumine_g_l',
    'biologie_crp_mg_l',
    'biologie_plaquettes_g_l',
    'dialyse_seances_par_semaine',
    'dialyse_duree_seance_min',
    'presentation_tas_mmhg',
    'presentation_tad_mmhg',
]

NUMERIC_FEATURES = [
    'age',
    'biologie_creatinine_mg_l',
    'biologie_dfg_mdrd_ml_min_1_73m2',
    'biologie_albumine_g_l',
    'biologie_crp_mg_l',
    'biologie_plaquettes_g_l',
    'dialyse_seances_par_semaine',
    'dialyse_duree_seance_min',
    'presentation_tas_mmhg',
    'presentation_tad_mmhg',
]

CATEGORICAL_FEATURES = [
    'sexe',
    'comorbidite_statut_diabete',
]

REQUIRED_NUMERIC_KEYS = [
    'age',
    'biologie_creatinine_mg_l',
    'biologie_dfg_mdrd_ml_min_1_73m2',
    'biologie_albumine_g_l',
]

MODEL_MAP = {
    'random_forest': RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'),
    'gradient_boosting': GradientBoostingClassifier(random_state=42),
    'logistic_regression': LogisticRegression(max_iter=1000, solver='liblinear', class_weight='balanced'),
    'svm': CalibratedClassifierCV(LinearSVC(max_iter=5000, dual=False), cv=3),
}
if XGBOOST_AVAILABLE:
    MODEL_MAP['xgboost'] = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)

RECOMMENDATIONS = {
    'mortalite': ['random_forest', 'gradient_boosting'] + (['xgboost'] if XGBOOST_AVAILABLE else []),
    'coagulation': ['logistic_regression', 'svm', 'gradient_boosting'],
}

KEYWORDS_COAGULATION = re.compile(r'hemorrag|thromb|thrombo|saign|ecchym|hematome', re.IGNORECASE)


def normalize_value(value):
    if value is None:
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(',', '.').lower()
    if text == '':
        return np.nan
    if text in ['m', 'f', 'o']:
        return text
    try:
        return float(text)
    except ValueError:
        return np.nan


def encode_sexe(value):
    if not isinstance(value, str):
        return 0
    value = value.strip().upper()
    return 1 if value == 'F' else 2 if value == 'O' else 0


def extract_features(patient):
    features = {}
    for key in FEATURE_KEYS:
        value = getattr(patient, key, None)
        if value is None and hasattr(patient, 'extra_data') and isinstance(patient.extra_data, dict):
            value = patient.extra_data.get(key)
        if key == 'sexe':
            features[key] = str(value).strip().upper() if value is not None else np.nan
            continue
        if key == 'comorbidite_statut_diabete':
            features[key] = 'oui' if str(value).strip().lower() in ['oui', 'true', '1', 'yes'] else 'non'
            continue
        features[key] = normalize_value(value)
    return features


def mortality_label(patient):
    death_date = getattr(patient, 'devenir_date_deces', '')
    evaluation_date = getattr(patient, 'date_evaluation_initiale', None)
    if not death_date or not evaluation_date:
        return 0

    if isinstance(evaluation_date, datetime):
        eval_dt = evaluation_date
    elif isinstance(evaluation_date, date):
        eval_dt = datetime.combine(evaluation_date, datetime.min.time())
    else:
        try:
            eval_dt = datetime.fromisoformat(str(evaluation_date))
        except Exception:
            return 0

    try:
        parsed = datetime.fromisoformat(death_date)
    except ValueError:
        try:
            parsed = datetime.strptime(death_date, '%Y-%m-%d')
        except Exception:
            return 0

    return 1 if parsed <= eval_dt + timedelta(days=365) else 0


def coagulation_label(patient):
    fields = [
        getattr(patient, 'complication_liste', ''),
        getattr(patient, 'complication_motifs_hospitalisation', ''),
        getattr(patient, 'presentation_symptomes', ''),
        getattr(patient, 'presentation_notes_examen_clinique', ''),
    ]
    text = ' '.join(str(value) for value in fields if value)
    return 1 if KEYWORDS_COAGULATION.search(text) else 0


def is_valid_patient_for_training(features):
    numeric_values = [features.get(key, np.nan) for key in NUMERIC_FEATURES]
    non_missing_numeric = [value for value in numeric_values if not np.isnan(value)]
    if len(non_missing_numeric) < 5:
        return False
    if all(np.isnan(features.get(key, np.nan)) for key in REQUIRED_NUMERIC_KEYS):
        return False
    return True


def build_dataset(target_type):
    patients = Patient.objects.all()
    rows = []
    labels = []
    for patient in patients:
        features = extract_features(patient)
        if not is_valid_patient_for_training(features):
            continue
        if target_type == 'mortalite':
            label = mortality_label(patient)
        else:
            label = coagulation_label(patient)
        rows.append(features)
        labels.append(label)
    df = pd.DataFrame(rows)
    y = np.array(labels, dtype=int)
    return df, y


def get_preprocessor():
    numeric_transformer = Pipeline(
        [
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        [
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore')),
        ]
    )
    return ColumnTransformer(
        [
            ('numeric', numeric_transformer, NUMERIC_FEATURES),
            ('categorical', categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder='drop',
        sparse_threshold=0,
    )


def get_model_path(target_type, model_name):
    return MODEL_DIRECTORY / f'{target_type}_{model_name}.joblib'


def get_best_path(target_type):
    return MODEL_DIRECTORY / f'{target_type}_best.joblib'


def select_best_model(results):
    sorted_models = sorted(results, key=lambda item: (item['auc'] if item['auc'] is not None else item['accuracy']), reverse=True)
    return sorted_models[0]


def get_pipeline(estimator):
    return Pipeline(
        [
            ('preprocessor', get_preprocessor()),
            ('classifier', estimator),
        ]
    )


def train_models(target_type):
    X, y = build_dataset(target_type)
    if X.empty or len(np.unique(y)) < 2:
        raise ValueError('Pas assez de donnees ou signal invalide pour entrainer le modele.')

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    report = []
    best_model_instance = None
    best_score = -1.0

    for name, estimator in MODEL_MAP.items():
        pipeline = get_pipeline(estimator)
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1] if hasattr(pipeline, 'predict_proba') else None
        accuracy = float(accuracy_score(y_test, y_pred))
        precision = float(precision_score(y_test, y_pred, zero_division=0))
        recall = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        pr_auc = float(average_precision_score(y_test, y_prob)) if y_prob is not None and len(np.unique(y_test)) > 1 else None
        auc = float(roc_auc_score(y_test, y_prob)) if y_prob is not None and len(np.unique(y_test)) > 1 else None
        if auc is not None:
            score = auc
        else:
            score = precision
        if score > best_score:
            best_score = score
            best_model_instance = pipeline
        joblib.dump(pipeline, get_model_path(target_type, name))
        report.append({'model': name, 'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1, 'pr_auc': pr_auc, 'auc': auc})

    if best_model_instance is not None:
        joblib.dump(best_model_instance, get_best_path(target_type))

    return report


class PredictionTrainView(APIView):
    def post(self, request):
        target_type = request.data.get('prediction_type')
        if target_type not in ['mortalite', 'coagulation']:
            return Response({'error': 'prediction_type must be mortalite or coagulation'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            report = train_models(target_type)
        except ValueError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        best = select_best_model(report)
        return Response({'status': 'trained', 'best_model': best, 'report': report}, status=status.HTTP_200_OK)


class PredictionPredictView(APIView):
    def post(self, request):
        prediction_type = request.data.get('prediction_type')
        selected_model = request.data.get('model')
        features = request.data.get('features', {})

        if prediction_type not in ['mortalite', 'coagulation']:
            return Response({'error': 'prediction_type must be mortalite or coagulation'}, status=status.HTTP_400_BAD_REQUEST)

        if selected_model == 'auto' or not selected_model:
            best_path = get_best_path(prediction_type)
            if not best_path.exists():
                return Response({'error': 'Aucun modele entraine trouve. Lancez d\'abord l\'entrainement.'}, status=status.HTTP_400_BAD_REQUEST)
            clf = joblib.load(best_path)
            selected_model = best_path.stem.replace(f'{prediction_type}_', '')
        else:
            model_path = get_model_path(prediction_type, selected_model)
            if not model_path.exists():
                return Response({'error': f'Modele {selected_model} non entraine pour {prediction_type}.'}, status=status.HTTP_400_BAD_REQUEST)
            clf = joblib.load(model_path)

        input_df = pd.DataFrame([extract_features_from_payload(features)])
        for col in FEATURE_KEYS:
            if col not in input_df.columns:
                input_df[col] = np.nan

        try:
            probability = float(clf.predict_proba(input_df)[:, 1][0])
        except Exception:
            probability = float(clf.decision_function(input_df)[0])
            probability = 1 / (1 + np.exp(-probability))

        score = round(float(np.clip(probability * 100, 0, 100)), 1)
        level = 'Faible' if score <= 30 else 'Mod\u00e9r\u00e9' if score <= 70 else '\u00c9lev\u00e9'
        factors = build_interpretation(clf, features)

        return Response({
            'prediction_type': prediction_type,
            'model': selected_model,
            'score': score,
            'risk_level': level,
            'probability': probability,
            'factors': factors,
            'selected_features': features,
        }, status=status.HTTP_200_OK)


def extract_features_from_payload(payload):
    row = {}
    for key in FEATURE_KEYS:
        value = payload.get(key)
        if key == 'sexe':
            row[key] = str(value).strip().upper() if value is not None else np.nan
        elif key == 'comorbidite_statut_diabete':
            row[key] = 'oui' if str(value).strip().lower() in ['oui', 'true', '1', 'yes'] else 'non'
        else:
            row[key] = normalize_value(value)
    return row


def get_feature_names(preprocessor):
    try:
        return preprocessor.get_feature_names_out()
    except Exception:
        return FEATURE_KEYS


def extract_importances(model, feature_names):
    estimator = model
    if hasattr(model, 'named_steps'):
        estimator = model.named_steps['classifier']
    if hasattr(estimator, 'feature_importances_'):
        importances = estimator.feature_importances_
    elif hasattr(estimator, 'coef_'):
        coef = estimator.coef_
        if coef.ndim > 1:
            importances = np.mean(np.abs(coef), axis=0)
        else:
            importances = np.abs(coef)
    elif hasattr(estimator, 'base_estimator') and hasattr(estimator.base_estimator, 'coef_'):
        coef = estimator.base_estimator.coef_
        importances = np.mean(np.abs(coef), axis=0)
    else:
        return []

    names = list(feature_names)
    if len(importances) != len(names):
        return []

    ranked = sorted(
        [{'label': name, 'weight': float(round(value * 100, 1))} for name, value in zip(names, importances)],
        key=lambda item: item['weight'],
        reverse=True,
    )
    return ranked[:4]


def build_interpretation(clf, features):
    preprocessor = None
    if hasattr(clf, 'named_steps'):
        preprocessor = clf.named_steps.get('preprocessor')
    if not preprocessor:
        return []

    feature_names = get_feature_names(preprocessor)
    importances = extract_importances(clf, feature_names)
    if not importances:
        return []

    selected = []
    for item in importances:
        raw_name = item['label']
        if raw_name in features:
            selected.append(item)
            continue
        if raw_name.startswith('numeric__'):
            feature_name = raw_name.split('__', 1)[1]
            if feature_name in features:
                item['label'] = feature_name
                selected.append(item)
            continue
        if raw_name.startswith('categorical__'):
            suffix = raw_name.split('__', 1)[1]
            if '_' in suffix:
                feature_name, category = suffix.split('_', 1)
                if feature_name in features:
                    item['label'] = f'{feature_name}={category}'
                    selected.append(item)
    return selected[:4]
