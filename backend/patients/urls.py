from django.urls import path

from .views import (
    PatientDetailView,
    PatientExportExcelView,
    PatientImportExcelView,
    PatientListCreateView,
    PatientSchemaView,
)

urlpatterns = [
    path('', PatientListCreateView.as_view(), name='patient_list_create'),
    path('<int:pk>/', PatientDetailView.as_view(), name='patient_detail'),
    path('import/', PatientImportExcelView.as_view(), name='patient_import_excel'),
    path('export/', PatientExportExcelView.as_view(), name='patient_export_excel'),
    path('schema/', PatientSchemaView.as_view(), name='patient_schema'),
]
