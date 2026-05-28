from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from apuestaAPP.models import ApuestaMaestra, ApuestaDetalle
from cuentaAPP.models import Cuenta
from eventoAPP.models import Evento, Seleccion
from cuentaAPP.servicio import bloquear_fondos

def crear_apuesta(usuario, monto, selecciones_ids, transaction_id):
    Minimo_apuesta = Decimal('1.0000')
    Maximo_apuesta = Decimal('10000.0000')

    # Idempotencia
    if ApuestaMaestra.objects.filter(transaction_id=transaction_id).exists():
        return ApuestaMaestra.objects.get(transaction_id=transaction_id)

    with transaction.atomic():
        # Hacer select_for_update() sobre la cuenta wallet_usuario del usuario antes de verificar saldo.
        wallet = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
        
        monto = Decimal(str(monto))
        if monto < Minimo_apuesta or monto > Maximo_apuesta:
            raise ValueError(f"El monto de la apuesta debe estar entre {Minimo_apuesta} y {Maximo_apuesta}.")

        if wallet.saldo_actual < monto:
            raise ValueError("Saldo insuficiente para realizar la apuesta.")

        if usuario.estado != 'verificado':
            raise ValueError("El usuario no está verificado y no puede realizar apuestas.")
        
        perfil = usuario.juegoResponsabe

        if perfil.autoexclusion_indefinida:
            raise ValueError("El usuario está autoexcluido indefinidamente y no puede realizar apuestas.")
        
        if perfil.autoexclusion_fecha_fin and perfil.autoexclusion_fecha_fin > timezone.now().date():
           raise ValueError("Tu cuenta se encuentra autoexcluida temporalmente.")

        # Verificar que no haya superado sus límites de JuegoResponsable
        hoy = timezone.now()
        inicio_dia = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        inicio_semana = inicio_dia - timedelta(days=hoy.weekday())
        inicio_mes = inicio_dia.replace(day=1)

        total_diario = ApuestaMaestra.objects.filter(usuario=usuario, fecha_apuesta__gte=inicio_dia).aggregate(Sum('monto_apostado'))['monto_apostado__sum'] or Decimal('0.0000')
        total_semanal = ApuestaMaestra.objects.filter(usuario=usuario, fecha_apuesta__gte=inicio_semana).aggregate(Sum('monto_apostado'))['monto_apostado__sum'] or Decimal('0.0000')
        total_mensual = ApuestaMaestra.objects.filter(usuario=usuario, fecha_apuesta__gte=inicio_mes).aggregate(Sum('monto_apostado'))['monto_apostado__sum'] or Decimal('0.0000')

        if total_diario + monto > perfil.limite_diario:
            raise ValueError(f"Límite diario excedido. Tienes disponible: S/ {perfil.limite_diario - total_diario}")
        if total_semanal + monto > perfil.limite_semanal:
            raise ValueError(f"Límite semanal excedido. Tienes disponible: S/ {perfil.limite_semanal - total_semanal}")
        if total_mensual + monto > perfil.limite_mensual:
            raise ValueError(f"Límite mensual excedido. Tienes disponible: S/ {perfil.limite_mensual - total_mensual}")

        selecciones = Seleccion.objects.filter(id__in=selecciones_ids).select_related('mercado__evento')
        cuota_total = Decimal('1.0')

        for seleccion in selecciones:
            evento = seleccion.mercado.evento
            if evento.estado != Evento.EstadoEvento.PROGRAMADO:
                raise ValueError("El evento ya no está disponible para apostar.")
            
            if evento.fecha_inicio < timezone.now():
                raise ValueError("El evento ya ha comenzado.")

            cuota_total *= seleccion.cuota    

        # Llamar a bloquear_fondos de la Tarea 1
        bloquear_fondos(usuario, monto, transaction_id)
        
        tipo = ApuestaMaestra.TipoApuesta.SIMPLE if len(selecciones) == 1 else ApuestaMaestra.TipoApuesta.COMBINADA
        ganancia_potencial = monto * cuota_total
        
        apuesta = ApuestaMaestra.objects.create(
            usuario=usuario,
            tipo=tipo,
            monto_apostado=monto,
            cuota_total=cuota_total,
            ganancia_potencial=ganancia_potencial,
            transaction_id=transaction_id
        )

        for sele in selecciones:
            ApuestaDetalle.objects.create(
                apuesta_maestra=apuesta,
                seleccion=sele,
                cuato_aplicada=sele.cuota
            )
            
        return apuesta
