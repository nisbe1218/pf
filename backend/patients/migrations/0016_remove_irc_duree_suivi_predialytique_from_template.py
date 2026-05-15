# Migration to remove irc_duree_suivi_predialytique_mois field from PatientFormField

from django.db import migrations


def delete_field(apps, schema_editor):
    PatientFormField = apps.get_model('patients', 'PatientFormField')
    PatientFormField.objects.filter(key='irc_duree_suivi_predialytique_mois').delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0015_merge_20260503_1437'),
    ]

    operations = [
        migrations.RunPython(delete_field, noop),
    ]
