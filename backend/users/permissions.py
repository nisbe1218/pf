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
