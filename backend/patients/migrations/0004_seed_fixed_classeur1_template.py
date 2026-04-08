import json
import unicodedata
from pathlib import Path

from django.db import migrations


def _normalize_text(value):
    text = unicodedata.normalize('NFKD', str(value or '').strip().lower())
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text


def _map_field_type(raw_type):
    normalized = _normalize_text(raw_type)
    mapping = {
        'genere automatiquement': 'auto',
        'texte libre court': 'text_short',
        'texte libre': 'text_short',
        'texte libre long': 'text_long',
        'liste a choix unique': 'single_choice',
        'liste a choix multiple': 'multiple_choice',
        'selecteur de date': 'date',
        'nombre entier': 'integer',
        'nombre decimal': 'decimal',
        'oui/non': 'boolean',
    }
    return mapping.get(normalized, 'text_short')


def seed_fixed_classeur1_template(apps, schema_editor):
    PatientFormTemplate = apps.get_model('patients', 'PatientFormTemplate')
    PatientFormField = apps.get_model('patients', 'PatientFormField')

    schema_path = Path(__file__).resolve().parent.parent / 'schemas' / 'classeur1_schema.json'
    if not schema_path.exists():
        return

    with schema_path.open('r', encoding='utf-8') as handle:
        schema_data = json.load(handle)

    template_name = schema_data.get('sheet') or 'Plateform_donnees_complete'
    source_file_name = schema_data.get('workbook') or 'Classeur1.xlsx'

    template = PatientFormTemplate.objects.filter(name=template_name).order_by('-id').first()
    if template is None:
        template = PatientFormTemplate.objects.create(
            name=template_name,
            source_file_name=source_file_name,
            sheet_name=template_name,
        )
    else:
        template.source_file_name = source_file_name
        template.sheet_name = template_name
        template.save(update_fields=['source_file_name', 'sheet_name'])

    PatientFormField.objects.filter(template=template).delete()

    fields_to_create = []
    for item in schema_data.get('fields', []):
        key = str(item.get('key') or '').strip()
        if not key:
            continue

        raw_type = item.get('field_type') or ''
        field_type = _map_field_type(raw_type)
        possible_values = item.get('possible_values') or []
        if not isinstance(possible_values, list):
            possible_values = [str(possible_values)]

        choices = [str(value).strip() for value in possible_values if str(value).strip()]
        order = int(item.get('index') or 0)

        fields_to_create.append(
            PatientFormField(
                template=template,
                key=key,
                label=key,
                field_type=field_type,
                order=order,
                choices=choices,
                source_hint=str(raw_type),
                is_required=field_type != 'auto',
            )
        )

    PatientFormField.objects.bulk_create(fields_to_create)


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0003_patient_fixed_classeur1_structure'),
    ]

    operations = [
        migrations.RunPython(seed_fixed_classeur1_template, noop_reverse),
    ]
