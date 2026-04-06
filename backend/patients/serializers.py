from rest_framework import serializers

from .models import Patient, PatientFormTemplate, PatientFormField


class PatientSerializer(serializers.ModelSerializer):
    extra_data = serializers.JSONField(required=False, default=dict)
    nom = serializers.CharField(required=False, allow_blank=True)
    prenom = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Patient
        fields = [
            'id',
            'nom',
            'prenom',
            'age',
            'sexe',
            'maladie',
            'telephone',
            'adresse',
            'date_naissance',
            'date_admission',
            'id_patient',
            'id_enregistrement_source',
            'id_site',
            'statut_inclusion',
            'statut_consentement',
            'date_evaluation_initiale',
            'utilisateur_saisie',
            'derniere_mise_a_jour',
            'demographie_data',
            'irc_data',
            'comorbidite_data',
            'presentation_data',
            'biologie_data',
            'imagerie_data',
            'dialyse_data',
            'qualite_data',
            'complication_data',
            'traitement_data',
            'devenir_data',
            'extra_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class PatientFormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientFormField
        fields = [
            'id', 'key', 'label', 'field_type', 'order',
            'choices', 'source_hint', 'is_required',
        ]


class PatientFormTemplateSerializer(serializers.ModelSerializer):
    fields = PatientFormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = PatientFormTemplate
        fields = ['id', 'name', 'source_file_name', 'sheet_name', 'imported_at', 'fields']
