from django.urls import path

from .views import PatientAuditHistoryHideView, PatientAuditHistoryView


urlpatterns = [
    path('patients/<int:pk>/history/', PatientAuditHistoryView.as_view(), name='patient-audit-history'),
    path('patients/<int:pk>/history/<int:log_id>/hide/', PatientAuditHistoryHideView.as_view(), name='patient-audit-history-hide'),
]