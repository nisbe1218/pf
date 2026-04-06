from django.urls import path
from .views import (
    LoginView, UtilisateurListView,
    UtilisateurDetailView, MonProfilView, ConfirmPasswordView,
    MotDePasseUtilisateurView, RoleListView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/',         LoginView.as_view(),           name='login'),
    path('token/refresh/', TokenRefreshView.as_view(),    name='token_refresh'),
    path('roles/',        RoleListView.as_view(),         name='role_list'),
    path('utilisateurs/',  UtilisateurListView.as_view(), name='users_list'),
    path('utilisateurs/<int:pk>/', UtilisateurDetailView.as_view(), name='user_detail'),
    path('utilisateurs/<int:pk>/mot-de-passe/', MotDePasseUtilisateurView.as_view(), name='user_password_hash'),
    path('profil/',        MonProfilView.as_view(),        name='profil'),
    path('confirm-password/', ConfirmPasswordView.as_view(), name='confirm_password'),
]