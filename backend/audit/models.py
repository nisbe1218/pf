from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=255)
    entite = models.CharField(max_length=100, blank=True)
    entite_id = models.IntegerField(null=True, blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.utilisateur} — {self.action} — {self.date}"
