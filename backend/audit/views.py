from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from patients.models import Patient
from users.permissions import CanViewPatients

from .models import AuditLog, HiddenAuditLog


def _humanize_action(action):
    if not action:
        return 'Action'
    return action.split(':', 1)[0].replace('_', ' ').title()


class PatientAuditHistoryView(APIView):
    permission_classes = [CanViewPatients]

    def get(self, request, pk):
        patient = Patient.objects.filter(pk=pk).first()
        if not patient:
            return Response([], status=200)

        entries = AuditLog.objects.filter(
            entite='Patient',
            entite_id=patient.id,
        ).exclude(
            hidden_by_users__user=request.user,
        ).order_by('-date')[:50]
        # Determine caller role name (Role is a FK with attribute `nom`) — handle both string and FK cases
        role_obj = getattr(request.user, 'role', None)
        role_name = None
        if role_obj is None:
            role_name = None
        elif isinstance(role_obj, str):
            role_name = role_obj
        else:
            role_name = getattr(role_obj, 'nom', None)

        can_see_actor = role_name in ('super_admin', 'chef_service')

        def _actor_name(user_obj):
            if not user_obj:
                return None
            # Prefer full name, fallback to email
            first = getattr(user_obj, 'prenom', None) or ''
            last = getattr(user_obj, 'nom', None) or ''
            full = f"{first} {last}".strip()
            return full or getattr(user_obj, 'email', None)

        payload = [
            {
                'id': entry.id,
                'label': _humanize_action(entry.action),
                'detail': entry.action,
                'date': entry.date,
                'user': (_actor_name(entry.utilisateur) if can_see_actor else None),
                'ip': entry.adresse_ip,
            }
            for entry in entries
        ]
        return Response(payload)


class PatientAuditHistoryHideView(APIView):
    permission_classes = [CanViewPatients]

    def post(self, request, pk, log_id):
        patient = get_object_or_404(Patient, pk=pk)
        audit_log = get_object_or_404(AuditLog, pk=log_id, entite='Patient', entite_id=patient.id)
        HiddenAuditLog.objects.get_or_create(user=request.user, audit_log=audit_log)
        return Response({'hidden': True, 'audit_log_id': audit_log.id})
