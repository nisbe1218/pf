from decimal import Decimal

from django import forms
from django.contrib import admin

from .models import Patient, PatientFormTemplate


SECTION_BUCKETS = [
	('demographie_', 'demographie_data'),
	('irc_', 'irc_data'),
	('comorbidite_', 'comorbidite_data'),
	('presentation_', 'presentation_data'),
	('biologie_', 'biologie_data'),
	('imagerie_', 'imagerie_data'),
	('dialyse_', 'dialyse_data'),
	('qualite_', 'qualite_data'),
	('complication_', 'complication_data'),
	('traitement_', 'traitement_data'),
	('devenir_', 'devenir_data'),
]

MODEL_FIELDS = {
	'id_patient',
	'id_enregistrement_source',
	'id_site',
	'statut_inclusion',
	'statut_consentement',
	'utilisateur_saisie',
	'derniere_mise_a_jour',
	'date_evaluation_initiale',
	'nom',
	'prenom',
	'age',
	'sexe',
	'maladie',
	'telephone',
	'adresse',
	'date_naissance',
	'date_admission',
}

MODEL_FORM_FIELDS = [
	'id_patient',
	'id_enregistrement_source',
	'id_site',
	'statut_inclusion',
	'statut_consentement',
	'date_evaluation_initiale',
	'utilisateur_saisie',
	'derniere_mise_a_jour',
	'nom',
	'prenom',
	'age',
	'sexe',
	'maladie',
	'telephone',
	'adresse',
	'date_naissance',
	'date_admission',
]


def get_active_template():
	return (
		PatientFormTemplate.objects.filter(name__iexact='template').order_by('-id').first()
		or PatientFormTemplate.objects.order_by('-id').first()
	)


def resolve_platform_value(obj, key):
	if key in MODEL_FIELDS:
		return getattr(obj, key, '')

	for prefix, bucket in SECTION_BUCKETS:
		if key.startswith(prefix):
			return (getattr(obj, bucket, {}) or {}).get(key, '')

	return (obj.extra_data or {}).get(key, '')


def resolve_bucket_name(key):
	for prefix, bucket in SECTION_BUCKETS:
		if key.startswith(prefix):
			return bucket
	return 'extra_data'


def is_empty_value(value):
	if value is None:
		return True
	if isinstance(value, str) and value.strip() == '':
		return True
	if isinstance(value, (list, tuple, set)) and len(value) == 0:
		return True
	return False


def normalize_for_json(value, field_type):
	if is_empty_value(value):
		return None

	if field_type == 'date':
		return value.isoformat() if hasattr(value, 'isoformat') else str(value)
	if field_type == 'decimal':
		if isinstance(value, Decimal):
			return str(value)
		return value
	if field_type == 'multiple_choice':
		if isinstance(value, (list, tuple)):
			return list(value)
		if isinstance(value, str):
			return [part.strip() for part in value.split(',') if part.strip()]

	return value


def build_dynamic_form_field(field_def):
	field_type = (field_def.field_type or '').strip().lower()
	required = bool(field_def.is_required)
	label = field_def.label or field_def.key

	if field_type == 'integer':
		return forms.IntegerField(label=label, required=required)
	if field_type == 'decimal':
		return forms.DecimalField(label=label, required=required)
	if field_type == 'date':
		return forms.DateField(label=label, required=required, widget=forms.DateInput(attrs={'type': 'date'}))
	if field_type == 'boolean':
		return forms.TypedChoiceField(
			label=label,
			required=required,
			choices=(('', '---------'), ('true', 'Oui'), ('false', 'Non')),
			coerce=lambda v: True if v == 'true' else (False if v == 'false' else None),
			empty_value=None,
		)
	if field_type == 'single_choice':
		choices = [('', '---------')]
		choices.extend((str(choice), str(choice)) for choice in (field_def.choices or []))
		return forms.ChoiceField(label=label, required=required, choices=choices)
	if field_type == 'multiple_choice':
		choices = [(str(choice), str(choice)) for choice in (field_def.choices or [])]
		if choices:
			return forms.MultipleChoiceField(label=label, required=required, choices=choices)
		return forms.CharField(label=label, required=required)
	if field_type == 'text_long':
		return forms.CharField(label=label, required=required, widget=forms.Textarea(attrs={'rows': 2}))

	return forms.CharField(label=label, required=required)


class PatientAdminForm(forms.ModelForm):
	_template_field_types = {}
	_template_keys = []
	_template_model_meta = {}

	class Meta:
		model = Patient
		fields = MODEL_FORM_FIELDS

	@classmethod
	def from_template(cls, template_fields):
		attrs = {}
		field_types = {}
		template_keys = []
		model_meta = {}

		for field_def in template_fields:
			key = field_def.key
			template_keys.append(key)
			field_types[key] = field_def.field_type
			if key in MODEL_FIELDS:
				model_meta[key] = {
					'label': field_def.label or key,
					'required': bool(field_def.is_required),
				}
				continue

			attrs[key] = build_dynamic_form_field(field_def)

		attrs['_template_field_types'] = field_types
		attrs['_template_keys'] = template_keys
		attrs['_template_model_meta'] = model_meta
		return type('DynamicPatientAdminForm', (cls,), attrs)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		for key, config in self._template_model_meta.items():
			if key in self.fields:
				self.fields[key].label = config['label']
				self.fields[key].required = config['required']

		if not self.instance or not self.instance.pk:
			return

		for key in self._template_keys:
			if key not in self.fields or key in MODEL_FIELDS:
				continue

			value = resolve_platform_value(self.instance, key)
			if isinstance(value, list):
				self.initial[key] = value
			else:
				self.initial[key] = value

	def save(self, commit=True):
		obj = super().save(commit=False)

		bucket_payloads = {bucket: dict(getattr(obj, bucket, {}) or {}) for _, bucket in SECTION_BUCKETS}
		extra_payload = dict(obj.extra_data or {})

		for key in self._template_keys:
			if key in MODEL_FIELDS or key not in self.fields:
				continue

			field_type = (self._template_field_types.get(key) or '').strip().lower()
			value = normalize_for_json(self.cleaned_data.get(key), field_type)
			bucket_name = resolve_bucket_name(key)

			if bucket_name == 'extra_data':
				if is_empty_value(value):
					extra_payload.pop(key, None)
				else:
					extra_payload[key] = value
				continue

			payload = bucket_payloads[bucket_name]
			if is_empty_value(value):
				payload.pop(key, None)
			else:
				payload[key] = value

		for _, bucket in SECTION_BUCKETS:
			setattr(obj, bucket, bucket_payloads[bucket])
		obj.extra_data = extra_payload

		if commit:
			obj.save()
			self.save_m2m()
		return obj


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
	form = PatientAdminForm
	list_display = ('id',)
	search_fields = (
		'id_patient',
		'nom',
		'prenom',
		'maladie',
		'telephone',
		'id_enregistrement_source',
	)
	list_filter = ('sexe', 'statut_inclusion', 'date_evaluation_initiale', 'date_admission')
	empty_value_display = ''
	readonly_fields = ('created_at', 'updated_at')

	def _get_template_fields(self):
		template = get_active_template()
		if not template:
			return []
		return list(template.fields.order_by('order', 'id'))

	def get_form(self, request, obj=None, change=False, **kwargs):
		template_fields = self._get_template_fields()
		self._current_template_keys = [field.key for field in template_fields]
		kwargs['form'] = PatientAdminForm.from_template(template_fields)
		return super().get_form(request, obj, change=change, **kwargs)

	def get_fields(self, request, obj=None):
		template_keys = getattr(self, '_current_template_keys', None)
		if template_keys is None:
			template_keys = [field.key for field in self._get_template_fields()]

		ordered = []
		seen = set()
		for key in template_keys:
			if key in seen:
				continue
			seen.add(key)
			ordered.append(key)

		for field_name in MODEL_FORM_FIELDS:
			if field_name in seen:
				continue
			seen.add(field_name)
			ordered.append(field_name)

		return ordered

	def _resolve_platform_value(self, obj, key):
		value = resolve_platform_value(obj, key)
		if key == 'sexe' and value:
			return obj.get_sexe_display() or value
		return value

	def _ensure_column_method(self, key):
		method_name = f'col_{key}'
		if hasattr(self.__class__, method_name):
			return method_name

		def _column(instance, obj, _key=key):
			return instance._resolve_platform_value(obj, _key)

		_column.short_description = key.upper()
		setattr(self.__class__, method_name, _column)
		return method_name

	def get_list_display(self, request):
		template = get_active_template()
		if not template:
			return ('id', 'id_patient', 'nom', 'prenom')

		keys = list(template.fields.order_by('order', 'id').values_list('key', flat=True))
		methods = [self._ensure_column_method(key) for key in keys]
		return ('id', *methods)
