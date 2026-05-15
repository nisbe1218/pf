from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.TextField()
    entite = models.CharField(max_length=100, blank=True)
    entite_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(blank=True, default='')
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.utilisateur} — {self.action} — {self.date}"


class HiddenAuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hidden_audit_logs',
    )
    audit_log = models.ForeignKey(
        AuditLog,
        on_delete=models.CASCADE,
        related_name='hidden_by_users',
    )
    hidden_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'audit_log'], name='unique_hidden_audit_log_per_user')
        ]

    def __str__(self):
        return f"{self.user} — hidden {self.audit_log_id}"
