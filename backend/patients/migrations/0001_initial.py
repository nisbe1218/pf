from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('prenom', models.CharField(max_length=100)),
                ('age', models.PositiveIntegerField(blank=True, null=True)),
                ('sexe', models.CharField(blank=True, choices=[('M', 'Masculin'), ('F', 'Féminin'), ('O', 'Autre')], max_length=1)),
                ('maladie', models.CharField(blank=True, max_length=200)),
                ('telephone', models.CharField(blank=True, max_length=20)),
                ('adresse', models.CharField(blank=True, max_length=255)),
                ('date_naissance', models.DateField(blank=True, null=True)),
                ('date_admission', models.DateField(default=django.utils.timezone.localdate)),
                ('extra_data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
