from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from apuestaAPP.models import ApuestaMaestra, ApuestaDetalle
from cuentaAPP.models import Cuenta
from eventoAPP.models import Evento, Seleccion
from cuentaAPP.servicio import realizar_transferencia

def crear_apuesta(usuario, monto, selecciones_ids):
    Minimo_apuesta = 1.0000
    Maximo_apuesta = 10000.0000

    with transaction.atomic():
        if monto < Minimo_apuesta or monto > Maximo_apuesta:
            raise ValueError(f"El monto de la apuesta debe estar entre {Minimo_apuesta} y {Maximo_apuesta}.")

        if usuario.estado != 'verificado':
            raise ValueError("El usuario no está verificado y no puede realizar apuestas.")
        
        perfil = usuario.juegoResponsabe

        if perfil.autoexclusion_indefinida:
            raise ValueError("El usuario está autoexcluido indefinidamente y no puede realizar apuestas.")
        
        if perfil.autoexclusion_fecha_fin and perfil.autoexclusion_fecha_fin > timezone.now().date():
           raise ValueError("Tu cuenta se encuentra autoexcluida temporalmente.")

        selecciones = Seleccion.objects.filter(id__in=selecciones_ids).select_related('mercado__evento')
        cuota_total = Decimal('1.0')

        for seleccion in selecciones:
            evento = seleccion.mercado.evento
            if evento.estado != Evento.EstadoEvento.PROGRAMADO:
                raise ValueError("el evento ya no está disponible para apostar.")
            
            if evento.fecha_inicio < timezone.now():
                raise ValueError("el evento ya ha comenzado. ")

            cuota_total *= seleccion.cuota    

        wallet = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.Wallet)
        if wallet.saldo_actual < monto:
            raise ValueError("Saldo insuficiente para realizar la apuesta.")      

        apuesta_pendiente = Cuenta.objects.get( usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.Pendiente)

        transferencia_id = realizar_transferencia(
                            cuenta_origen=wallet.id,
                            cuenta_destino=apuesta_pendiente.id,
                            monto=monto                        
                           )
        
        tipo = ApuestaMaestra.TipoApuesta.SIMPLE if len(selecciones) == 1 else ApuestaMaestra.TipoApuesta.COMBINADA
        ganancia_potencial = monto * cuota_total
        
        apuesta =  ApuestaMaestra.objects.create(
            usuario=usuario.id,
            tipo=tipo,
            monto_apostado=monto,
            cuota_total=cuota_total,
            ganancia_potencial=ganancia_potencial,
            transaction_id=transferencia_id
        )

        for sele in selecciones:
            ApuestaDetalle.objects.create(
                apuesta_maestra=apuesta,
                seleccion=sele,
                cuato_aplicada=sele.cuota
            )



