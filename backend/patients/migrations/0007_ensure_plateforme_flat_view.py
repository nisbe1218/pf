from django.db import migrations, connection


MODEL_FIELD_MAP = {
    'id_patient': 'id_patient',
    'id_enregistrement_source': 'id_enregistrement_source',
    'id_site': 'id_site',
    'statut_inclusion': 'statut_inclusion',
    'statut_consentement': 'statut_consentement',
    'utilisateur_saisie': 'utilisateur_saisie',
    'derniere_mise_a_jour': 'derniere_mise_a_jour',
    'date_evaluation_initiale': 'date_evaluation_initiale',
    'nom': 'nom',
    'prenom': 'prenom',
    'age': 'age',
    'sexe': 'sexe',
    'maladie': 'maladie',
    'telephone': 'telephone',
    'adresse': 'adresse',
    'date_naissance': 'date_naissance',
    'date_admission': 'date_admission',
}

SECTION_BUCKETS = [
    ('demographie_', 'demographie_data'),
    ('irc_', 'irc_data'),
    ('comorbidite_', 'comorbidite_data'),
    ('presentation_', 'presentation_data'),
    ('biologie_', 'biologie_data'),
    ('imagerie_', 'imagerie_data'),
    ('dialyse_', 'dialyse_data'),
    ('qualite_', 'qualite_data'),
    ('complication_', 'complication_data'),
    ('traitement_', 'traitement_data'),
    ('devenir_', 'devenir_data'),
]


def _quote_identifier(value):
    return '"' + str(value).replace('"', '""') + '"'


def _quote_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def ensure_plateforme_flat_view(apps, schema_editor):
    PatientFormTemplate = apps.get_model('patients', 'PatientFormTemplate')
    PatientFormField = apps.get_model('patients', 'PatientFormField')

    template = PatientFormTemplate.objects.filter(name__iexact='template').order_by('-id').first()
    if template is None:
        template = PatientFormTemplate.objects.order_by('-id').first()
    if template is None:
        return

    keys = list(
        PatientFormField.objects.filter(template=template)
        .order_by('order', 'id')
        .values_list('key', flat=True)
    )
    if not keys:
        return

    select_parts = ['p.id AS id']
    for key in keys:
        if key in MODEL_FIELD_MAP:
            expr = f"p.{MODEL_FIELD_MAP[key]}"
        else:
            bucket = None
            for prefix, column_name in SECTION_BUCKETS:
                if key.startswith(prefix):
                    bucket = column_name
                    break

            if bucket:
                expr = f"p.{bucket} ->> {_quote_literal(key)}"
            else:
                expr = f"p.extra_data ->> {_quote_literal(key)}"

        select_parts.append(f"{expr} AS {_quote_identifier(key)}")

    sql = (
        'CREATE OR REPLACE VIEW public.patients_plateforme_flat AS '
        'SELECT ' + ', '.join(select_parts) + ' FROM patients_patient p'
    )

    with connection.cursor() as cursor:
        cursor.execute(sql)


def drop_plateforme_flat_view(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute('DROP VIEW IF EXISTS public.patients_plateforme_flat')


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0006_refresh_fixed_schema_from_json'),
    ]

    operations = [
        migrations.RunPython(ensure_plateforme_flat_view, drop_plateforme_flat_view),
    ]
