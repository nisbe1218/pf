from django.db import models
from django.utils import timezone


class Patient(models.Model):
	SEXE_CHOICES = [
		('M', 'Masculin'),
		('F', 'Féminin'),
		('O', 'Autre'),
	]

	nom = models.CharField(max_length=100)
	prenom = models.CharField(max_length=100)
	age = models.PositiveIntegerField(null=True, blank=True)
	sexe = models.CharField(max_length=1, choices=SEXE_CHOICES, blank=True)
	maladie = models.CharField(max_length=200, blank=True)
	telephone = models.CharField(max_length=20, blank=True)
	adresse = models.CharField(max_length=255, blank=True)
	date_naissance = models.DateField(null=True, blank=True)
	date_admission = models.DateField(default=timezone.localdate)
	id_patient = models.CharField(max_length=120, blank=True)
	id_enregistrement_source = models.CharField(max_length=120, blank=True)
	id_site = models.CharField(max_length=120, blank=True)
	statut_inclusion = models.CharField(max_length=80, blank=True)
	statut_consentement = models.CharField(max_length=80, blank=True)
	date_evaluation_initiale = models.DateField(null=True, blank=True)
	utilisateur_saisie = models.CharField(max_length=120, blank=True)
	derniere_mise_a_jour = models.CharField(max_length=120, blank=True)
	demographie_data = models.JSONField(default=dict, blank=True)
	irc_data = models.JSONField(default=dict, blank=True)
	comorbidite_data = models.JSONField(default=dict, blank=True)
	presentation_data = models.JSONField(default=dict, blank=True)
	biologie_data = models.JSONField(default=dict, blank=True)
	imagerie_data = models.JSONField(default=dict, blank=True)
	dialyse_data = models.JSONField(default=dict, blank=True)
	qualite_data = models.JSONField(default=dict, blank=True)
	complication_data = models.JSONField(default=dict, blank=True)
	traitement_data = models.JSONField(default=dict, blank=True)
	devenir_data = models.JSONField(default=dict, blank=True)
	extra_data = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at', '-id']

	def __str__(self):
		return f"{self.prenom} {self.nom}"


class PatientFormTemplate(models.Model):
	name = models.CharField(max_length=150)
	source_file_name = models.CharField(max_length=255, blank=True)
	sheet_name = models.CharField(max_length=150, blank=True)
	imported_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.name


class PatientFormField(models.Model):
	FIELD_TYPES = [
		('text_short', 'Texte libre court'),
		('text_long', 'Texte libre long'),
		('single_choice', 'Choix unique'),
		('multiple_choice', 'Choix multiple'),
		('date', 'Sélecteur de date'),
		('integer', 'Nombre entier'),
		('boolean', 'Oui / Non'),
		('auto', 'Automatique'),
	]

	template = models.ForeignKey(PatientFormTemplate, related_name='fields', on_delete=models.CASCADE)
	key = models.CharField(max_length=150)
	label = models.CharField(max_length=255)
	field_type = models.CharField(max_length=30, choices=FIELD_TYPES)
	order = models.PositiveIntegerField()
	choices = models.JSONField(default=list, blank=True)
	source_hint = models.CharField(max_length=255, blank=True)
	is_required = models.BooleanField(default=False)

	class Meta:
		unique_together = ('template', 'key')
		ordering = ['order', 'id']

	def __str__(self):
		return f"{self.template.name} - {self.label}"
