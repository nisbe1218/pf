from django.core.management.base import BaseCommand
from users.models import Role, Utilisateur

class Command(BaseCommand):
    help = 'Initialise les rôles et le compte Super Administrateur de la plateforme médicale'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Initialisation des rôles en cours...'))

        # Création des rôles
        for role_code, role_nom in Role.ROLES:
            Role.objects.get_or_create(nom=role_code)
            self.stdout.write(self.style.SUCCESS(f'Rôle vérifié/créé: {role_nom}'))

        # Création du Super Admin
        role_admin = Role.objects.get(nom='super_admin')
        if not Utilisateur.objects.filter(email='admin@hopital.com').exists():
            Utilisateur.objects.create_superuser(
                email='admin@hopital.com',
                password='MotDePasseSecurise123',
                nom='Admin',
                prenom='Super',
                role=role_admin
            )
            self.stdout.write(self.style.SUCCESS('✅ Super Admin créé avec succès !'))
        else:
            self.stdout.write(self.style.WARNING('Le compte Super Admin existe déjà.'))

        self.stdout.write(self.style.SUCCESS('✅ Initialisation de la base de données terminée !'))
