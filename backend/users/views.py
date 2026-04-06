from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
from .models import Utilisateur, Role
from .serializers import (
    UtilisateurSerializer, CreateUtilisateurSerializer, UpdateUtilisateurSerializer,
    CustomTokenSerializer, RolePublicSerializer
)
from .permissions import IsSuperAdmin, IsAdminOrChefService
from audit.models import AuditLog


def confirm_admin_password(request):
    password = request.data.get('confirmation_password')
    if not password:
        return False, Response({'error': 'Confirmation administrateur requise'}, status=400)
    if not check_password(password, request.user.password):
        return False, Response({'error': 'Confirmation refusée'}, status=403)
    return True, None

class LoginView(TokenObtainPairView):
    """Connexion — retourne le token JWT"""
    serializer_class = CustomTokenSerializer


class UtilisateurListView(APIView):
    """Lister et créer des utilisateurs"""
    permission_classes = [IsAdminOrChefService]

    def _manageable_queryset(self, request):
        if request.user.role and request.user.role.nom == 'super_admin':
            return Utilisateur.objects.all()
        return Utilisateur.objects.exclude(role__nom='super_admin').exclude(role__nom='chef_service')

    def _can_manage_role(self, request, role):
        if request.user.role and request.user.role.nom == 'super_admin':
            return True
        return role and role.nom in ['professeur', 'resident']

    def get(self, request):
        users = self._manageable_queryset(request)
        serializer = UtilisateurSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        confirmed, error_response = confirm_admin_password(request)
        if not confirmed:
            return error_response

        payload = request.data.copy()
        payload.pop('confirmation_password', None)
        serializer = CreateUtilisateurSerializer(data=payload)
        if serializer.is_valid():
            role = serializer.validated_data.get('role')
            if not self._can_manage_role(request, role):
                return Response({'error': 'Rôle non autorisé'}, status=403)
            user = serializer.save()
            AuditLog.objects.create(
                utilisateur=request.user,
                action='CREATION_UTILISATEUR',
                entite='Utilisateur',
                entite_id=user.id,
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            return Response(UtilisateurSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UtilisateurDetailView(APIView):
    """Modifier et supprimer un utilisateur"""
    permission_classes = [IsAdminOrChefService]

    def get_object(self, pk):
        try:
            return Utilisateur.objects.get(pk=pk)
        except Utilisateur.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({'error': 'Utilisateur introuvable'}, status=404)
        serializer = UtilisateurSerializer(user, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({'error': 'Utilisateur introuvable'}, status=404)
        if request.user.role and request.user.role.nom == 'chef_service' and user.role and user.role.nom in ['super_admin', 'chef_service']:
            return Response({'error': 'Action non autorisée'}, status=403)
        confirmed, error_response = confirm_admin_password(request)
        if not confirmed:
            return error_response

        payload = request.data.copy()
        payload.pop('confirmation_password', None)
        serializer = UpdateUtilisateurSerializer(user, data=payload, partial=True)
        if serializer.is_valid():
            new_role = serializer.validated_data.get('role', user.role)
            if request.user.role and request.user.role.nom == 'chef_service' and new_role and new_role.nom not in ['professeur', 'resident']:
                return Response({'error': 'Rôle non autorisé'}, status=403)
            serializer.save()
            AuditLog.objects.create(
                utilisateur=request.user,
                action='MODIFICATION_UTILISATEUR',
                entite='Utilisateur',
                entite_id=user.id,
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            return Response(UtilisateurSerializer(user, context={'request': request}).data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({'error': 'Utilisateur introuvable'}, status=404)
        confirmed, error_response = confirm_admin_password(request)
        if not confirmed:
            return error_response

        if request.user.role and request.user.role.nom == 'chef_service' and user.role and user.role.nom in ['super_admin', 'chef_service']:
            return Response({'error': 'Action non autorisée'}, status=403)
        if user.role and user.role.nom == 'super_admin' and (not request.user.role or request.user.role.nom != 'super_admin'):
            return Response({'error': 'Action non autorisée'}, status=403)
        AuditLog.objects.create(
            utilisateur=request.user,
            action='SUPPRESSION_UTILISATEUR',
            entite='Utilisateur',
            entite_id=user.id,
            adresse_ip=request.META.get('REMOTE_ADDR')
        )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleListView(APIView):
    permission_classes = [IsAdminOrChefService]

    def get(self, request):
        if request.user.role and request.user.role.nom == 'super_admin':
            roles = Role.objects.all()
        else:
            roles = Role.objects.filter(nom__in=['professeur', 'resident'])
        return Response(RolePublicSerializer(roles, many=True).data)


class MonProfilView(APIView):
    """Voir son propre profil"""
    def get(self, request):
        serializer = UtilisateurSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class ConfirmPasswordView(APIView):
    """Confirmer le mot de passe pour accéder aux données sensibles"""
    permission_classes = [IsAdminOrChefService]

    def post(self, request):
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Mot de passe requis'}, status=400)
        if check_password(password, request.user.password):
            return Response({'confirmed': True})
        return Response({'confirmed': False}, status=403)


class MotDePasseUtilisateurView(APIView):
    """Retourne le hash du mot de passe après confirmation du mot de passe de l'utilisateur connecté."""
    permission_classes = [IsAdminOrChefService]

    def post(self, request, pk):
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Mot de passe requis'}, status=400)

        if not check_password(password, request.user.password):
            return Response({'error': 'Confirmation refusée'}, status=403)

        utilisateur = get_object_or_404(Utilisateur, pk=pk)
        AuditLog.objects.create(
            utilisateur=request.user,
            action='CONSULTATION_MOT_DE_PASSE_HASH',
            entite='Utilisateur',
            entite_id=utilisateur.id,
            adresse_ip=request.META.get('REMOTE_ADDR')
        )
        return Response({
            'id': utilisateur.id,
            'email': utilisateur.email,
            'password_hash': utilisateur.password,
        })
