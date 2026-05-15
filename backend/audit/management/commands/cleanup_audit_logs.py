from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditLog


class Command(BaseCommand):
    help = 'Supprime les logs d’audit plus anciens que le seuil configuré.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=15,
            help='Nombre de jours de rétention des logs d’audit (défaut: 15).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche le nombre de logs concernés sans les supprimer.',
        )

    def handle(self, *args, **options):
        days = max(int(options['days']), 0)
        cutoff = timezone.now() - timedelta(days=days)
        queryset = AuditLog.objects.filter(date__lt=cutoff)
        total = queryset.count()

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'{total} log(s) d’audit seraient supprimés (avant {cutoff:%Y-%m-%d %H:%M:%S %Z}).'
                )
            )
            return

        deleted_count, _ = queryset.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f'{deleted_count} log(s) d’audit supprimé(s). Rétention active: {days} jour(s).'
            )
        )
