from decimal import Decimal, ROUND_DOWN
from django.db import transaction
from .models import Cuenta, LibroMayor

def bloquear_fondos(usuario, monto, transaction_id):
    """
    Bloquea fondos del usuario para una apuesta.
    Débito en wallet_usuario, Crédito en apuestas_pendientes.
    """
    monto = Decimal(str(monto))
    if LibroMayor.objects.filter(transaction_id=transaction_id).exists():
        return  # Idempotencia

    with transaction.atomic():
        # select_for_update() para bloquear concurrencia en estas cuentas
        wallet = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
        pendientes = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.APUESTAS_PENDIENTES)

        if wallet.saldo_actual < monto:
            raise ValueError("Fondos insuficientes")

        # Débito de wallet
        LibroMayor.objects.create(
            cuenta=wallet,
            tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
            monto=monto,
            transaction_id=transaction_id
        )

        # Crédito en pendientes
        LibroMayor.objects.create(
            cuenta=pendientes,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=monto,
            transaction_id=transaction_id
        )

def liquidar_apuesta_ganada(apuesta, transaction_id):
    """
    Liquida una apuesta ganada.
    Mueve fondos de apuestas_pendientes -> wallet_usuario con el payout = stake x cuota.
    """
    if LibroMayor.objects.filter(transaction_id=transaction_id).exists():
        return
    
    usuario = apuesta.usuario
    payout = (apuesta.monto_apostado * apuesta.cuota_total).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
    
    with transaction.atomic():
        pendientes = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.APUESTAS_PENDIENTES)
        wallet = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
        
        # Débito de pendientes
        LibroMayor.objects.create(
            cuenta=pendientes,
            tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
            monto=payout,
            transaction_id=transaction_id
        )

        # Crédito a wallet
        LibroMayor.objects.create(
            cuenta=wallet,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=payout,
            transaction_id=transaction_id
        )

def liquidar_apuesta_perdida(apuesta, transaction_id):
    """
    Liquida una apuesta perdida.
    Mueve fondos de apuestas_pendientes -> casa.
    """
    if LibroMayor.objects.filter(transaction_id=transaction_id).exists():
        return
    
    usuario = apuesta.usuario
    monto_apostado = apuesta.monto_apostado
    
    with transaction.atomic():
        pendientes = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.APUESTAS_PENDIENTES)
        casa = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.CASA)
        
        # Débito de pendientes
        LibroMayor.objects.create(
            cuenta=pendientes,
            tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
            monto=monto_apostado,
            transaction_id=transaction_id
        )

        # Crédito a casa
        LibroMayor.objects.create(
            cuenta=casa,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=monto_apostado,
            transaction_id=transaction_id
        )


def void_apuesta(apuesta, transaction_id):
    if LibroMayor.objects.filter(transaction_id=transaction_id).exists():
        return

    usuario = apuesta.usuario
    monto = apuesta.monto_apostado

    with transaction.atomic():
        pendientes = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.APUESTAS_PENDIENTES)
        wallet = Cuenta.objects.select_for_update().get(usuario=usuario, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)

        LibroMayor.objects.create(
            cuenta=pendientes,
            tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
            monto=monto,
            transaction_id=transaction_id
        )

        LibroMayor.objects.create(
            cuenta=wallet,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=monto,
            transaction_id=transaction_id
        )
