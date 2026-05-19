import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import requests

@csrf_exempt
def analyze_file(request):
    """Endpoint pour analyser un fichier CSV/XLSX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file provided'}, status=400)
    
    # Sauvegarder temporairement le fichier
    file_path = default_storage.save(f'temp/{file.name}', file)
    
    # Ici, lancer la tâche Celery (à créer)
    # Pour l'instant, retourner un ID fictif
    
    return JsonResponse({
        'preprocess_id': 'demo-123',
        'status': 'pending',
        'message': 'Analyse démarrée avec Ollama (qwen2.5:7b)'
    })

def health_check(request):
    """Vérifier la connexion à Ollama"""
    try:
        ollama_url = os.environ.get('OLLAMA_BASE_URL', 'http://medical_ollama:11434')
        resp = requests.post(
            f'{ollama_url}/api/generate',
            json={'model': 'qwen2.5:7b', 'prompt': 'test', 'stream': False},
            timeout=15
        )
        return JsonResponse({
            'status': 'ok',
            'ollama': 'connected',
            'model': 'qwen2.5:7b',
            'embedding_model': 'nomic-embed-text'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'ollama': 'disconnected',
            'error': str(e)
        }, status=500)

def get_status(request, preprocess_id):
    """Récupérer le statut d'une analyse"""
    return JsonResponse({
        'status': 'processing',
        'progress_message': 'Analyse en cours...'
    })

def get_report(request, preprocess_id):
    """Récupérer le rapport JSON"""
    return JsonResponse({
        'error': 'Report not ready yet',
        'preprocess_id': preprocess_id
    }, status=404)

def export_corrected(request, preprocess_id):
    """Exporter le fichier corrigé"""
    return JsonResponse({'error': 'Not implemented yet'}, status=501)

def integrate_data(request, preprocess_id):
    """Intégrer les données dans la plateforme"""
    return JsonResponse({'error': 'Not implemented yet'}, status=501)