import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import Utilisateur
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate
from patients.views import PatientListCreateView
from patients.models import Patient

# Récupérer l'utilisateur professeur
prof = Utilisateur.objects.get(email='prof@hopital.com')
admin = Utilisateur.objects.get(email='admin@hopital.com')

# Vérifier qu'il y a des patients
patient_count = Patient.objects.count()
print(f"Total patients in DB: {patient_count}")

# Créer une requête GET simulée pour professeur
factory = APIRequestFactory()
request = factory.get('/api/patients/')
force_authenticate(request, user=prof)

# Tester la view avec professeur
view = PatientListCreateView.as_view()
response = view(request)

print(f"\nProfesseur - Status: {response.status_code}")
if hasattr(response, 'data'):
    print(f"Professeur - Data count: {len(response.data)}")
    if response.data:
        print(f"Professeur - First patient: {response.data[0].get('nom', 'N/A')}")
else:
    print(f"Professeur - Error: {response}")

# Tester avec admin
request2 = factory.get('/api/patients/')
force_authenticate(request2, user=admin)
response2 = view(request2)

print(f"\nAdmin - Status: {response2.status_code}")
if hasattr(response2, 'data'):
    print(f"Admin - Data count: {len(response2.data)}")
    if response2.data:
        print(f"Admin - First patient: {response2.data[0].get('nom', 'N/A')}")
else:
    print(f"Admin - Error: {response2}")
