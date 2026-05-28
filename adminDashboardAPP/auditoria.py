import hashlib
import json
from django.db import transaction
from .models import AuditoriaRegistro

def registrar_auditoria(tipo_evento, payload_dict):
    """
    Crea un registro inmutable encadenado por hash SHA256.
    hash_actual = SHA256(hash_anterior + json.dumps(payload, sort_keys=True))
    """
    with transaction.atomic():
        ultimo = AuditoriaRegistro.objects.select_for_update().order_by('-id').first()
        hash_anterior = ultimo.hash_actual if ultimo else '0' * 64
        contenido = hash_anterior + json.dumps(payload_dict, sort_keys=True, default=str)
        hash_actual = hashlib.sha256(contenido.encode()).hexdigest()
        AuditoriaRegistro.objects.create(
            tipo_evento=tipo_evento,
            payload=payload_dict,
            hash_anterior=hash_anterior,
            hash_actual=hash_actual
        )
