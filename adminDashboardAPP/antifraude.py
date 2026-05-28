from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from cuentaAPP.models import Cuenta
from apuestaAPP.models import ApuestaMaestra
from .models import ActividadSospechosa

def verificar_alto_riesgo(apuesta):
    usuario = apuesta.usuario
    monto_apostado = apuesta.monto_apostado
    try:
        wallet = Cuenta.objects.get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
        # El saldo previo a la apuesta es el saldo actual + el monto apostado
        saldo_previo = wallet.saldo_actual + monto_apostado
        if saldo_previo > 0 and monto_apostado > (Decimal('0.8') * saldo_previo):
            ActividadSospechosa.objects.get_or_create(
                usuario=usuario,
                tipo_alerta='APUESTA_ALTO_RIESGO',
                descripcion=f"La apuesta de S/ {monto_apostado} supera el 80% del saldo total del usuario (S/ {saldo_previo}) previo a la apuesta."
            )
    except Cuenta.DoesNotExist:
        pass

def verificar_apuestas_repetidas(apuesta, seleccion):
    usuario = apuesta.usuario
    monto_apostado = apuesta.monto_apostado
    ahora = timezone.now()
    diez_minutos_atras = ahora - timedelta(minutes=10)

    # Contamos cuántas apuestas del mismo usuario con el mismo monto y misma selección hay en los últimos 10 minutos
    cantidad_repetidas = ApuestaMaestra.objects.filter(
        usuario=usuario,
        monto_apostado=monto_apostado,
        fecha_apuesta__gte=diez_minutos_atras,
        detalles__seleccion=seleccion
    ).distinct().count()
    
    if cantidad_repetidas > 3:
        ActividadSospechosa.objects.get_or_create(
            usuario=usuario,
            tipo_alerta='APUESTAS_REPETIDAS',
            descripcion=f"El usuario ha realizado {cantidad_repetidas} apuestas del mismo monto (S/ {monto_apostado}) a la selección '{seleccion}' en los últimos 10 minutos."
        )
