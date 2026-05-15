from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and request.user.role.nom == 'super_admin'
        )

class IsChefService(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and request.user.role.nom == 'chef_service'
        )

class IsProfesseur(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and request.user.role.nom == 'professeur'
        )

class IsResident(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and request.user.role.nom == 'resident'
        )

# Permission combinée : accès pour plusieurs rôles
class IsAdminOrChefService(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and request.user.role.nom in ['super_admin', 'chef_service']
        )

class IsChefServiceOrBelow(BasePermission):
    """Chef de service, Professeur et Résident"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and request.user.role.nom in ['chef_service', 'professeur', 'resident']
        )

class IsAuthentifiedUser(BasePermission):
    """Tous les rôles authentifiés"""
    def has_permission(self, request, view):
        return request.user.is_authenticated

class CanViewPatients(BasePermission):
    """
    Permet à tous les utilisateurs authentifiés de lire les données des patients.
    Autorise la création (POST), la modification (PUT, PATCH) et la suppression (DELETE)
    pour tous les utilisateurs authentifiés.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Lecture autorisée pour tous
        if request.method == 'GET':
            return True
        
        # Autoriser la création (POST) et suppression (DELETE) pour tous les utilisateurs authentifiés
        if request.method in ['POST', 'DELETE']:
            return True

        # Modification autorisée pour tous les utilisateurs authentifiés
        if request.method in ['PUT', 'PATCH']:
            return True
        
        return False
