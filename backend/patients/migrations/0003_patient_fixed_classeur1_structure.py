from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_patientformtemplate_patientformfield'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='id_patient',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='patient',
            name='id_enregistrement_source',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='patient',
            name='id_site',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='patient',
            name='statut_inclusion',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='patient',
            name='statut_consentement',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='patient',
            name='date_evaluation_initiale',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='patient',
            name='utilisateur_saisie',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='patient',
            name='derniere_mise_a_jour',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='patient',
            name='demographie_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='irc_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='comorbidite_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='presentation_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='biologie_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='imagerie_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='dialyse_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='qualite_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='complication_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='traitement_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='patient',
            name='devenir_data',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
