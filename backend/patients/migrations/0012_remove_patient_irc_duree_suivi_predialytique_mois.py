# Generated migration to remove irc_duree_suivi_predialytique_mois field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0011_add_icc_charlson'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patient',
            name='irc_duree_suivi_predialytique_mois',
        ),
    ]
