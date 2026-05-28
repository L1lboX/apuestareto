from .models import Cuenta, LibroMayor
from django.db import transaction
from decimal import Decimal
import uuid

def realizar_transferencia(cuenta_origen_id, cuenta_destino_id, monto):
    
    if monto <= Decimal('0.0000'):
        raise ValueError("El monto de la transferencia debe ser mayor a cero.")
    
    with transaction.atomic():
        
        cuentas = Cuenta.objects.select_for_update().filter(
            id__in = [cuenta_origen_id, cuenta_destino_id]
        )

        cuenta_origen = cuentas.get(id=cuenta_origen_id)
        cuenta_destino = cuentas.get(id=cuenta_destino_id)

        if cuenta_origen.tipo_cuenta == Cuenta.TipoCuenta.Wallet:
            if cuenta_origen.saldo < monto:
                raise ValueError("Saldo insuficiente para la transferencia.")
        
        id_transaccion = uuid.uuid4()

        LibroMayor.objects.create(
            cuenta=cuenta_origen,
            tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
            monto=monto,
            transaction_id=id_transaccion
        )

        LibroMayor.objects.create(
            cuenta=cuenta_destino,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=monto,
            transaction_id=id_transaccion
        )

        return id_transaccion


