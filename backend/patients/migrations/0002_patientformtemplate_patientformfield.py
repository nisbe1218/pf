from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PatientFormTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('source_file_name', models.CharField(blank=True, max_length=255)),
                ('sheet_name', models.CharField(blank=True, max_length=150)),
                ('imported_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='PatientFormField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=150)),
                ('label', models.CharField(max_length=255)),
                ('field_type', models.CharField(choices=[('text_short', 'Texte libre court'), ('text_long', 'Texte libre long'), ('single_choice', 'Choix unique'), ('multiple_choice', 'Choix multiple'), ('date', 'Sélecteur de date'), ('integer', 'Nombre entier'), ('boolean', 'Oui / Non'), ('auto', 'Automatique')], max_length=30)),
                ('order', models.PositiveIntegerField()),
                ('choices', models.JSONField(blank=True, default=list)),
                ('source_hint', models.CharField(blank=True, max_length=255)),
                ('is_required', models.BooleanField(default=False)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='patients.patientformtemplate')),
            ],
            options={
                'ordering': ['order', 'id'],
                'unique_together': {('template', 'key')},
            },
        ),
    ]
