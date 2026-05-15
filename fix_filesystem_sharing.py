#!/usr/bin/env python
"""Fix filesystem sharing issue by passing file data directly to Celery instead of file path"""

import re
import os

backend_path = '/c/Users/PC DELL/pf/backend/patients'

# ============================================================
# FIX: Modify PatientPreprocessAnalyzeView.post() to pass file data to Celery
# ============================================================

views_file = os.path.join(backend_path, 'views.py')
with open(views_file, 'r', encoding='utf-8') as f:
    views_content = f.read()

# Find and replace the section that saves temp file and dispatches Celery
old_pattern = r'''        # Sauvegarder le fichier temporairement
        try:
            temp_dir = tempfile\.gettempdir\(\)
            temp_file_path = os\.path\.join\(temp_dir, f'\{session_id\}_\{source_file_name\}'\)
            with open\(temp_file_path, 'wb'\) as temp_file:
                for chunk in uploaded_file\.chunks\(\):
                    temp_file\.write\(chunk\)
        except Exception as error:
            return Response\(\{'error': f'Erreur lors de la sauvegarde du fichier: \{error\}'\}, status=status\.HTTP_400_BAD_REQUEST\)'''

new_code = '''        # Lire le fichier en mémoire (données brutes)
        try:
            uploaded_file.seek(0)
            file_data = uploaded_file.read()
        except Exception as error:
            return Response({'error': f'Erreur lors de la lecture du fichier: {error}'}, status=status.HTTP_400_BAD_REQUEST)'''

views_content = re.sub(old_pattern, new_code, views_content, count=1, flags=re.DOTALL)

# Now update the analyze_preprocess_async.delay() call to pass file_data instead of file_path
old_delay = r'''            analyze_preprocess_async\.delay\(
                session_id=session_id,
                file_path=temp_file_path,
                user_id=request\.user\.id,
                use_llm=str\(request\.data\.get\('use_llm', 'true'\)\)\.lower\(\) not in \['0', 'false', 'no', 'non'\]
            \)'''

new_delay = '''            analyze_preprocess_async.delay(
                session_id=session_id,
                file_data=file_data,
                file_name=source_file_name,
                user_id=request.user.id,
                use_llm=str(request.data.get('use_llm', 'true')).lower() not in ['0', 'false', 'no', 'non']
            )'''

views_content = re.sub(old_delay, new_delay, views_content, count=1, flags=re.DOTALL)

with open(views_file, 'w', encoding='utf-8') as f:
    f.write(views_content)

print("✅ Updated PatientPreprocessAnalyzeView")

# ============================================================
# FIX: Modify tasks.py to accept file_data instead of file_path
# ============================================================

tasks_file = os.path.join(backend_path, 'tasks.py')
with open(tasks_file, 'r', encoding='utf-8') as f:
    tasks_content = f.read()

# Update the @shared_task signature
old_sig = r'@shared_task\(bind=True, name=\'patients\.analyze_preprocess\'\)\s*def analyze_preprocess_async\(self, session_id, file_path, user_id, use_llm=True\):'

new_sig = '''@shared_task(bind=True, name='patients.analyze_preprocess')
def analyze_preprocess_async(self, session_id, file_data, file_name, user_id, use_llm=True):'''

tasks_content = re.sub(old_sig, new_sig, tasks_content, count=1, flags=re.DOTALL)

# Now find the part where we read the uploaded file and update it to use file_data
old_read = r'''        # Lire le fichier
        uploaded_file = uploaded_file
        if not uploaded_file:
            update_session_progress\('Erreur: fichier manquant'\)
            raise ValueError\('Fichier manquant'\)'''

new_read = '''        # Convertir file_data en objet de fichier simulé
        import io
        uploaded_file = io.BytesIO(file_data)
        uploaded_file.name = file_name'''

# This is a more general replacement - find where we read the file and replace it
if 'uploaded_file =' in tasks_content:
    # Find and replace in a simpler way
    tasks_content = tasks_content.replace(
        '        # Lire le fichier\n        uploaded_file = uploaded_file',
        '        # Convertir file_data en objet de fichier\n        import io\n        uploaded_file = io.BytesIO(file_data)\n        uploaded_file.name = file_name'
    )

with open(tasks_file, 'w', encoding='utf-8') as f:
    f.write(tasks_content)

print("✅ Updated analyze_preprocess_async task signature")
print("\n✅ All fixes applied! Restart Docker containers to test.")
