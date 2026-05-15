from django.core.management.base import BaseCommand
import os
import json

from patients.views import (
    _read_uploaded_dataframe,
    _build_technical_profile,
    _build_preprocess_chunks,
    _build_retrieval_context,
    _determine_preprocess_route,
)


class Command(BaseCommand):
    help = 'Run a quick end-to-end preprocess RAG smoke test on a sample CSV.'

    def add_arguments(self, parser):
        parser.add_argument('--file', help='Path to CSV file relative to project root', default='sample_preprocess.csv')

    def handle(self, *args, **options):
        project_root = os.getcwd()
        file_path = os.path.join(project_root, options['file'])
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"Reading file: {file_path}")
        df, src = _read_uploaded_dataframe(file_path)
        self.stdout.write(f"Rows: {len(df)} Columns: {len(df.columns)} Source: {src}")

        self.stdout.write("Building technical profile...")
        tech = _build_technical_profile(df)
        self.stdout.write(json.dumps(tech, ensure_ascii=False, indent=2))

        self.stdout.write("Building chunks...")
        chunks = _build_preprocess_chunks(df, tech)
        self.stdout.write(f"Chunks: {len(chunks)}")
        for i, c in enumerate(chunks[:5]):
            self.stdout.write(f" - Chunk {i}: section={c.get('section')} rows={c.get('row_count')} cols={len(c.get('columns', []))}")

        self.stdout.write("Building retrieval context (RAG)...")
        rag = _build_retrieval_context(df, chunks, tech, stage_name='smoke_test', max_chunks=4)
        self.stdout.write(json.dumps(rag.get('vector_store', {}) or {k:v for k,v in rag.items() if k!='retrieved_chunks'}, ensure_ascii=False, indent=2))

        self.stdout.write("Estimate route:")
        route = _determine_preprocess_route(tech)
        self.stdout.write(json.dumps(route, ensure_ascii=False, indent=2))

        self.stdout.write(self.style.SUCCESS('Smoke test complete.'))
