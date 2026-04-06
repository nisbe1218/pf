from .models import AuditLog

def log_action(request, action, entite='', entite_id=None):
    ip = request.META.get('HTTP_X_FORWARDED_FOR')
    if ip:
        ip = ip.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    AuditLog.objects.create(
        utilisateur=request.user if request.user.is_authenticated else None,
        action=action,
        entite=entite,
        entite_id=entite_id,
        adresse_ip=ip
    )