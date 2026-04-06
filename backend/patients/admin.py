from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
	list_display = ('nom', 'prenom', 'age', 'sexe', 'maladie', 'telephone', 'date_admission')
	search_fields = ('nom', 'prenom', 'maladie', 'telephone')
	list_filter = ('sexe', 'date_admission')
