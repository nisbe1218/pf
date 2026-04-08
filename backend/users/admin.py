from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Role, Utilisateur


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
	list_display = ('nom',)
	search_fields = ('nom',)


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
	model = Utilisateur
	ordering = ('-date_creation',)
	list_display = ('email', 'nom', 'prenom', 'role', 'is_active', 'is_staff', 'is_superuser')
	list_filter = ('is_active', 'is_staff', 'is_superuser', 'role')
	search_fields = ('email', 'nom', 'prenom', 'telephone')

	fieldsets = (
		(None, {'fields': ('email', 'password')}),
		('Informations personnelles', {'fields': ('nom', 'prenom', 'telephone', 'role')}),
		('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
		('Dates', {'fields': ('last_login', 'date_creation')}),
	)

	add_fieldsets = (
		(
			None,
			{
				'classes': ('wide',),
				'fields': ('email', 'nom', 'prenom', 'telephone', 'role', 'password1', 'password2', 'is_active', 'is_staff'),
			},
		),
	)

	readonly_fields = ('last_login', 'date_creation')
