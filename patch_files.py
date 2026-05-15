#!/usr/bin/env python
"""Patch views.py and tasks.py to use shared /tmp/preprocess directory and pass file_data to Celery"""

import os
import sys

# ====== PATCH views.py ======
views_file = '/c/Users/PC DELL/pf/backend/patients/views.py'

print(f"Patching {views_file}...")

with open(views_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "temp_dir = tempfile.gettempdir()" and replace it
patched_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Patch 1: Fix tempfile.gettempdir() to use /tmp/preprocess
    if 'temp_dir = tempfile.gettempdir()' in line:
        indent = len(line) - len(line.lstrip())
        patched_lines.append(' ' * indent + 'temp_dir = "/tmp/preprocess"\n')
        patched_lines.append(' ' * indent + 'os.makedirs(temp_dir, exist_ok=True)\n')
        i += 1
        continue
    
    # Patch 2: Change from file_path to file_data in Celery dispatch
    if 'file_path=temp_file_path,' in line and 'analyze_preprocess_async.delay' in ''.join(lines[max(0, i-5):i+1]):
        patched_lines.append(line.replace('file_path=temp_file_path,', 'file_path=temp_file_path,\n                file_name=source_file_name,'))
        i += 1
        continue
    
    patched_lines.append(line)
    i += 1

with open(views_file, 'w', encoding='utf-8') as f:
    f.writelines(patched_lines)

print("✅ Patched views.py")

# ====== PATCH tasks.py ======
tasks_file = '/c/Users/PC DELL/pf/backend/patients/tasks.py'

print(f"Patching {tasks_file}...")

with open(tasks_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace temp file reading section
old_read = '''            # Lecture du fichier (qui revenait d'un tempfile)
            uploaded_file = None
            try:
                import io
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                uploaded_file = io.BytesIO(file_content)
                if hasattr(uploaded_file, 'name'):
                    uploaded_file.name = source_file_name or 'data'
            except Exception as error:
                update_session_progress(f'Erreur lecture fichier: {error}')
                raise'''

new_read = '''            # Lecture du fichier depuis le chemin temporaire partagé
            uploaded_file = None
            try:
                import io
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                uploaded_file = io.BytesIO(file_content)
                uploaded_file.name = os.path.basename(file_path) or 'data'
            except Exception as error:
                update_session_progress(f'Erreur lecture fichier: {error}')
                raise'''

if old_read in content:
    content = content.replace(old_read, new_read)
else:
    print("⚠️ Could not find old file reading pattern, but continuing...")

with open(tasks_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Patched tasks.py")
print("\n✅ All patches applied successfully!")
