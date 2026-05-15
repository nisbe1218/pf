from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_alter_role_id_alter_utilisateur_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='personal_notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
