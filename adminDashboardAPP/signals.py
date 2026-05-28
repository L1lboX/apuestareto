from django.db.models.signals import post_save
from django.dispatch import receiver
from apuestaAPP.models import ApuestaMaestra, ApuestaDetalle
from cuentaAPP.models import LibroMayor
from .auditoria import registrar_auditoria
from .antifraude import verificar_alto_riesgo, verificar_apuestas_repetidas

@receiver(post_save, sender=ApuestaMaestra)
def auditoria_apuesta_creada(sender, instance, created, **kwargs):
    if created:
        payload = {
            'usuario_id': instance.usuario.id,
            'monto': str(instance.monto_apostado),
            'cuota_total': str(instance.cuota_total),
            'tipo': instance.tipo,
        }
        registrar_auditoria('APUESTA_CREADA', payload)
        verificar_alto_riesgo(instance)

@receiver(post_save, sender=ApuestaDetalle)
def antifraude_detalle_creado(sender, instance, created, **kwargs):
    if created:
        verificar_apuestas_repetidas(instance.apuesta_maestra, instance.seleccion)

@receiver(post_save, sender=LibroMayor)
def auditoria_movimiento_wallet(sender, instance, created, **kwargs):
    if created:
        payload = {
            'cuenta_id': instance.cuenta.id,
            'tipo_movimiento': instance.tipo_movimiento,
            'monto': str(instance.monto),
            'transaction_id': instance.transaction_id,
        }
        registrar_auditoria('WALLET_MOVIMIENTO', payload)
