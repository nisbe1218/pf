import json
import logging
import os
from urllib import error as urllib_error
from urllib import request as urllib_request

import litellm

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Tu es un système expert de prétraitement intelligent de données médicales orienté néphrologie, "
    "dialyse et analyse clinique avancée.\n\n"
    "Ton rôle est de :\n"
    "- analyser un dataset médical importé dans son intégralité ;\n"
    "- détecter les incohérences ;\n"
    "- corriger les anomalies ;\n"
    "- standardiser les données ;\n"
    "- enrichir l’analyse métier ;\n"
    "- produire un rapport technique et médical détaillé ;\n"
    "- générer une version propre et exploitable pour le Machine Learning.\n\n"
    "Tu travailles dans une architecture locale utilisant :\n"
    "- vLLM comme moteur d’inférence ;\n"
    "- LiteLLM comme client d’orchestration ;\n"
    "- traitement chunké avec mémoire de contexte ;\n"
    "- pipeline RAG local ;\n"
    "- exécution backend asynchrone via Celery.\n\n"
    "IMPORTANT :\n"
    "- Tu ne dois jamais halluciner des données.\n"
    "- Toute correction doit être justifiée.\n"
    "- Si une valeur est ambiguë, marque-la comme \"suspecte\" au lieu d’inventer.\n"
    "- Les valeurs médicales doivent respecter la cohérence biologique réelle.\n"
    "- Les colonnes doivent être homogénéisées.\n"
    "- Les types doivent être corrigés intelligemment.\n"
    "- Les doublons doivent être détectés.\n"
    "- Les données impossibles doivent être signalées.\n"
    "- Tu dois raisonner comme :\n"
    "  - un expert en Big Data,\n"
    "  - un Data Engineer,\n"
    "  - un Data Scientist,\n"
    "  - et un néphrologue clinique senior.\n\n"
    "OBJECTIF GLOBAL : analyser entièrement le dataset fourni afin de comprendre sa structure, détecter les erreurs, "
    "identifier les incohérences médicales, corriger les problèmes de qualité, produire un dataset propre, générer un rapport détaillé, "
    "et préparer les données pour ML/Deep Learning/Analytics/prédiction clinique.\n\n"
    "EXIGENCES DE SORTIE : toujours répondre avec un JSON STRICTEMENT VALIDE, sans texte hors JSON. Le JSON doit contenir les sections attendues "
    "(dataset_summary, quality_score, medical_analysis, missing_values_analysis, outliers_analysis, duplicate_analysis, corrections_applied, remaining_risks, recommendations, ml_readiness, critical_alerts, column_profiles, processing_statistics).\n\n"
    "Contraintes techniques : optimiser réponses pour traitement chunké; ne jamais renvoyer tout le dataset; résumer intelligemment; réduire consommation mémoire; produire réponses déterministes; priorité à la stabilité JSON.\n\n"
    "Comportement en cas d'erreur : indiquer les informations manquantes, ne pas halluciner, marquer ambiguïtés comme suspectes, réduire niveau de confiance si contexte insuffisant.\n\n"
    "Tu dois appliquer étapes structurées (analyse structurelle, analyse médicale avancée, normalisation, gestion des missing, détection outliers, correction automatique traçable, préparation ML, génération rapport final) et fournir toujours des justifications et niveaux de confiance."
)


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return int(default)


def _normalize_base_url(value):
    return str(value or '').rstrip('/')


def get_llm_base_url():
    base_url = (
        os.environ.get('LITELLM_BASE_URL')
        or os.environ.get('VLLM_BASE_URL')
        or os.environ.get('OPENAI_API_BASE')
        or os.environ.get('OPENAI_BASE_URL')
        or 'http://127.0.0.1:8000/v1'
    )
    return _normalize_base_url(base_url)


def get_llm_model_name(default_model='meta-llama/Meta-Llama-3.1-8B-Instruct'):
    return (
        os.environ.get('LITELLM_MODEL')
        or os.environ.get('VLLM_MODEL')
        or os.environ.get('OPENAI_MODEL')
        or default_model
    )


def get_embedding_model_name(default_model='nomic-embed-text'):
    return (
        os.environ.get('LITELLM_EMBEDDING_MODEL')
        or os.environ.get('VLLM_EMBEDDING_MODEL')
        or os.environ.get('OPENAI_EMBEDDING_MODEL')
        or default_model
    )


def get_llm_api_key():
    return os.environ.get('LITELLM_API_KEY') or os.environ.get('OPENAI_API_KEY')


def get_system_prompt():
    # Prefer loading prompt from external file specified by env var
    file_path = os.environ.get('LLM_SYSTEM_PROMPT_FILE')
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning('Failed to load LLM system prompt from file %s: %s', file_path, e)

    # Next, allow overriding via raw env var
    return os.environ.get('LLM_SYSTEM_PROMPT', DEFAULT_SYSTEM_PROMPT)


def check_llm_health(timeout_seconds=8):
    base_url = get_llm_base_url()
    if not base_url:
        return {
            'connected': False,
            'base_url': None,
            'endpoint': None,
            'models_count': 0,
            'models': [],
            'errors': ['Base URL LLM non configuree.'],
        }

    endpoints = [
        f'{base_url}/models',
        f'{base_url}/v1/models',
        f'{base_url}/health',
    ]

    errors = []
    for endpoint in endpoints:
        req = urllib_request.Request(endpoint, method='GET')
        try:
            with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
                body = response.read().decode('utf-8')
            payload = json.loads(body) if body else {}
            models = []
            if isinstance(payload, dict):
                data = payload.get('data')
                if isinstance(data, list):
                    models = [item.get('id') for item in data if isinstance(item, dict) and item.get('id')]
                elif payload.get('model'):
                    models = [payload.get('model')]
            return {
                'connected': True,
                'base_url': base_url,
                'endpoint': endpoint,
                'models_count': len(models),
                'models': models[:20],
                'errors': [],
            }
        except urllib_error.HTTPError as error:
            error_body = ''
            try:
                error_body = error.read().decode('utf-8')
            except Exception:
                error_body = ''
            errors.append(f'{endpoint} -> HTTP {error.code}: {error_body or str(error)}')
        except (urllib_error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            errors.append(f'{endpoint} -> {error}')

    return {
        'connected': False,
        'base_url': base_url,
        'endpoint': None,
        'models_count': 0,
        'models': [],
        'errors': errors,
    }


def run_json_completion(messages, model=None, max_tokens=None, timeout_seconds=60):
    base_url = get_llm_base_url()
    api_key = get_llm_api_key()
    selected_model = model or get_llm_model_name()
    response = None

    request_kwargs = {
        'model': selected_model,
        'messages': messages,
        'api_base': base_url,
        'api_key': api_key,
        'temperature': 0.0,
        'max_tokens': max_tokens,
        'timeout': timeout_seconds,
        'stream': False,
    }

    try:
        response = litellm.completion(
            **{**request_kwargs, 'response_format': {'type': 'json_object'}}
        )
    except Exception as error:
        logger.warning('LLM JSON mode failed, retrying without response_format: %s', error)
        response = litellm.completion(**request_kwargs)

    content = None
    if response and response.choices:
        message = response.choices[0].message
        if isinstance(message, dict):
            content = message.get('content')
        else:
            content = getattr(message, 'content', None)

    return {
        'content': content,
        'model_used': selected_model,
        'raw_response': response,
    }


def run_embeddings(texts, model=None, timeout_seconds=60):
    base_url = get_llm_base_url()
    api_key = get_llm_api_key()
    selected_model = model or get_embedding_model_name()

    try:
        response = litellm.embedding(
            model=selected_model,
            input=texts,
            api_base=base_url,
            api_key=api_key,
            timeout=timeout_seconds,
        )
    except Exception as error:
        logger.warning('LLM embeddings failed: %s', error)
        return []

    embeddings = []
    data = getattr(response, 'data', None) if response is not None else None
    if data is None and isinstance(response, dict):
        data = response.get('data')

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and isinstance(item.get('embedding'), list):
                embeddings.append([float(value) for value in item['embedding']])
    return embeddings
