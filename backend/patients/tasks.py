import json
import os
import uuid
from celery import shared_task
from django.utils import timezone
from .views import (
    _load_preprocess_session,
    _read_uploaded_dataframe,
    _build_technical_profile,
    _determine_preprocess_route,
    _call_ollama_qwen_analysis,
    _build_preprocess_chunks,
    _build_retrieval_context,
    _apply_llm_correction_plan,
    _build_preprocess_report,
    _dataframe_to_rows,
    _save_preprocess_session,
    resolve_entry_user_label,
)


@shared_task(bind=True, name='patients.analyze_preprocess')
def analyze_preprocess_async(self, session_id, file_path, user_id, use_llm=True):
    """
    Async task to perform LLM analysis on uploaded file.
    Updates session with results or error status.
    """
    def update_session_progress(msg):
        """Update session with progress message"""
        try:
            session = _load_preprocess_session(session_id)
            session['progress_message'] = msg
            _save_preprocess_session(session)
        except Exception as e:
            print(f"Could not update progress: {e}")

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
    except Exception as e:
        print(f"Could not load user {user_id}: {e}")
        user = None

    try:
        update_session_progress("Lecture du fichier...")
        # Read file from temporary path
        with open(file_path, 'rb') as f:
            from django.core.files.uploadedfile import SimpleUploadedFile
            file_name = os.path.basename(file_path)
            uploaded_file = SimpleUploadedFile(file_name, f.read())

        update_session_progress("Profilage technique...")
        dataframe, source_file_name = _read_uploaded_dataframe(uploaded_file)
        technical_profile = _build_technical_profile(dataframe)

        update_session_progress("Découpage intelligent en chunks...")
        chunks = _build_preprocess_chunks(dataframe, technical_profile)
        update_session_progress(f"Chunks détectés: {len(chunks)}")
        retrieval_context = _build_retrieval_context(dataframe, chunks, technical_profile, progress_callback=update_session_progress)
        update_session_progress(f"Retrieval: {retrieval_context.get('retrieval_policy')}")

        # Call LLM (this might take time, hence async)
        if use_llm:
            route = _determine_preprocess_route(technical_profile)
            if route.get('mode') == 'deterministic':
                update_session_progress("Analyse déterministe (Pandas)...")
            else:
                update_session_progress(
                    f"Route LLM {route.get('label')} avec {route.get('primary_model')}..."
                )
            update_session_progress("Construction du contexte de retrieval...")
            llm_analysis = _call_ollama_qwen_analysis(
                dataframe,
                technical_profile,
                progress_callback=update_session_progress,
            )
        else:
            update_session_progress("Analyse LLM désactivée...")
            analysis_pack = {
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
            }
            llm_analysis = {
                'disabled': True,
                'issues': [],
                'recommendations': [],
                'correction_plan': {},
                'corrected_preview_rows': [],
                'column_assessment': [],
                'limitations': [],
                'analysis_pack': analysis_pack,
            }

        update_session_progress("Fusion des résultats déterministes et contextuels...")
        corrected_df, applied_actions = _apply_llm_correction_plan(dataframe, llm_analysis)
        
        update_session_progress("Génération du rapport final...")
        report = _build_preprocess_report(
            dataframe,
            technical_profile,
            llm_analysis=llm_analysis,
            corrected_df=corrected_df,
            applied_actions=applied_actions,
        )

        report['pipeline'] = llm_analysis.get('pipeline') if isinstance(llm_analysis, dict) else {}
        report['route'] = llm_analysis.get('route') if isinstance(llm_analysis, dict) else {}

        # Build and save session
        update_session_progress("Finalisation...")
        session = {
            'id': session_id,
            'created_at': timezone.now().isoformat(),
            'created_by': resolve_entry_user_label(user) if user else 'system',
            'source_file_name': source_file_name,
            'columns': [str(col) for col in corrected_df.columns.tolist()],
            'original_rows': _dataframe_to_rows(dataframe),
            'corrected_rows': _dataframe_to_rows(corrected_df),
            'report': report,
            'change_log': [],
            'status': 'completed',
            'error': None,
            'progress_message': 'Analyse terminée avec succès!',
        }
        _save_preprocess_session(session)

        # Clean up temp file
        try:
            os.remove(file_path)
        except Exception:
            pass

    except Exception as e:
        print(f"Error in analyze_preprocess_async for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error session
        try:
            session = _load_preprocess_session(session_id)
        except Exception:
            session = {}
        
        session.update({
            'id': session_id,
            'created_at': timezone.now().isoformat(),
            'created_by': resolve_entry_user_label(user) if user else 'system',
            'source_file_name': '',
            'columns': [],
            'original_rows': [],
            'corrected_rows': [],
            'report': {},
            'change_log': [],
            'status': 'error',
            'error': str(e),
            'progress_message': f'Erreur: {str(e)}',
        })
        _save_preprocess_session(session)

        # Clean up temp file
        try:
            os.remove(file_path)
        except Exception:
            pass

        raise
