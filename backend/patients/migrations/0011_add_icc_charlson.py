from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0010_alter_patient_id_alter_patientformfield_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='icc_charlson',
            field=models.TextField(blank=True),
        ),
    ]
