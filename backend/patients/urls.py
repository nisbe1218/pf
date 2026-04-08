from django.urls import path

from .views import (
    PatientBulkPurgeView,
    PatientDetailView,
    PatientExportExcelView,
    PatientImportExcelView,
    PatientListCreateView,
    PatientSchemaView,
)

urlpatterns = [
    path('', PatientListCreateView.as_view(), name='patient_list_create'),
    path('purge/', PatientBulkPurgeView.as_view(), name='patient_bulk_purge'),
    path('<int:pk>/', PatientDetailView.as_view(), name='patient_detail'),
    path('import/', PatientImportExcelView.as_view(), name='patient_import_excel'),
    path('import-excel/', PatientImportExcelView.as_view(), name='patient_import_excel_legacy'),
    path('export/', PatientExportExcelView.as_view(), name='patient_export_excel'),
    path('schema/', PatientSchemaView.as_view(), name='patient_schema'),
]
