from rest_framework import serializers
from .models import Utilisateur, Role
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class PersonalNotesSerializer(serializers.Serializer):
    notes = serializers.CharField(allow_blank=True, required=False, max_length=100000)

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'nom']


class RolePublicSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='get_nom_display', read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'nom', 'label']

class UtilisateurSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', write_only=True
    )

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'email', 'nom', 'prenom',
            'telephone', 'role', 'role_id',
            'is_active', 'date_creation'
        ]
        read_only_fields = ['date_creation']

class CreateUtilisateurSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role'
    )

    class Meta:
        model = Utilisateur
        fields = ['email', 'nom', 'prenom', 'telephone', 'password', 'role_id']

    def create(self, validated_data):
        return Utilisateur.objects.create_user(**validated_data)


class UpdateUtilisateurSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, min_length=8)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', required=False, allow_null=True
    )

    class Meta:
        model = Utilisateur
        fields = ['email', 'nom', 'prenom', 'telephone', 'role_id', 'is_active', 'password']

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        password = validated_data.pop('password', None)
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        if role is not None:
            instance.role = role
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class CustomTokenSerializer(TokenObtainPairSerializer):
    """Ajoute le rôle et les infos utilisateur dans le token JWT"""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['id'] = user.id
        token['email'] = user.email
        token['nom'] = user.nom
        token['prenom'] = user.prenom
        token['telephone'] = user.telephone
        token['role'] = user.role.nom if user.role else None
        return token
