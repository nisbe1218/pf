#!/usr/bin/env python
"""Quick fix: save temp files to app directory instead of /tmp"""

import os
import re

# Path to views.py
views_file = '/c/Users/PC DELL/pf/backend/patients/views.py'

with open(views_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the tempfile.gettempdir() with app directory
old = '''        # Sauvegarder le fichier temporairement
        try:
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f'{session_id}_{source_file_name}')'''

new = '''        # Sauvegarder le fichier temporairement dans app directory (partagé entre backend et worker)
        try:
            import os as os_module
            temp_dir = os_module.path.join(os_module.path.dirname(__file__), '..', '..', 'preprocess_temp')
            os_module.makedirs(temp_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_dir, f'{session_id}_{source_file_name}')'''

if old in content:
    content = content.replace(old, new)
    with open(views_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Fixed tempfile location in views.py")
else:
    print("❌ Could not find pattern in views.py")
    print("Showing context around tempfile...")
    if 'tempfile.gettempdir()' in content:
        idx = content.find('tempfile.gettempdir()')
        print(content[max(0, idx-200):min(len(content), idx+200)])
