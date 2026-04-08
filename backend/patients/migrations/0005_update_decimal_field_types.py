import unicodedata

from django.db import migrations


def _normalize_text(value):
    text = unicodedata.normalize('NFKD', str(value or '').strip().lower())
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text


def update_decimal_field_types(apps, schema_editor):
    PatientFormField = apps.get_model('patients', 'PatientFormField')

    fields = PatientFormField.objects.filter(field_type='text_short')
    for field in fields.iterator():
        normalized_hint = _normalize_text(field.source_hint)
        if normalized_hint == 'nombre decimal':
            field.field_type = 'decimal'
            field.save(update_fields=['field_type'])


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0004_seed_fixed_classeur1_template'),
    ]

    operations = [
        migrations.RunPython(update_decimal_field_types, noop_reverse),
    ]
