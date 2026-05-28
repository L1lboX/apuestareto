from .models import ActividadSospechosa, AuditoriaRegistro

def alertas_pendientes(request):
    if request.user.is_authenticated and request.user.is_staff:
        alertas_count = ActividadSospechosa.objects.filter(revisado=False).count()
        auditoria_count = AuditoriaRegistro.objects.count()
        return {
            'alertas_pendientes_count': alertas_count,
            'auditoria_registros_count': auditoria_count,
        }
    return {
        'alertas_pendientes_count': 0,
        'auditoria_registros_count': 0,
    }

