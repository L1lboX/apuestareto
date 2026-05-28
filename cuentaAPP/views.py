from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import Cuenta, LibroMayor
from userAPP.models import juegoResponsabe
import uuid
from decimal import Decimal


@login_required
def wallet(request):
    # Obtain wallet with lock for display consistency (read-only)
    wallet = Cuenta.objects.get(usuario=request.user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
    movimientos = wallet.movimientos.select_related('cuenta').order_by('-fecha_movimiento')[:20]
    # Juego responsable limits
    juego = juegoResponsabe.objects.get(user=request.user)
    return render(request, 'cuenta/wallet.html', {
        'wallet': wallet,
        'movimientos': movimientos,
        'juego': juego,
    })


@login_required
def recargar(request):
    if request.method == 'POST':
        monto_str = request.POST.get('monto')
        tx_id = request.POST.get('transaction_id')
        try:
            monto = Decimal(monto_str)
            if monto <= 0:
                raise ValueError('El monto debe ser positivo')
            with transaction.atomic():
                # Lock rows
                wallet = Cuenta.objects.select_for_update().get(usuario=request.user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
                casa = Cuenta.objects.select_for_update().get(usuario=None, tipo_cuenta=Cuenta.TipoCuenta.CASA)
                # Idempotency check
                if LibroMayor.objects.filter(transaction_id=tx_id).exists():
                    messages.success(request, f'Recarga ya procesada (idempotente).')
                else:
                    LibroMayor.objects.create(cuenta=casa, tipo_movimiento=LibroMayor.TipoMovimiento.Debito, monto=monto, transaction_id=tx_id)
                    LibroMayor.objects.create(cuenta=wallet, tipo_movimiento=LibroMayor.TipoMovimiento.Credito, monto=monto, transaction_id=tx_id)
                    messages.success(request, f'Recarga de S/ {monto} exitosa.')
        except Exception as e:
            messages.error(request, f'Error al procesar la recarga: {e}')
        return redirect('wallet')
    return redirect('wallet')


@login_required
def retirar(request):
    if request.method == 'POST':
        monto_str = request.POST.get('monto')
        tx_id = request.POST.get('transaction_id')
        try:
            monto = Decimal(monto_str)
            if monto <= 0:
                raise ValueError('El monto debe ser positivo')
            with transaction.atomic():
                wallet = Cuenta.objects.select_for_update().get(usuario=request.user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
                casa = Cuenta.objects.select_for_update().get(usuario=None, tipo_cuenta=Cuenta.TipoCuenta.CASA)
                if wallet.saldo_actual < monto:
                    messages.error(request, 'Saldo insuficiente para retirar.')
                else:
                    if LibroMayor.objects.filter(transaction_id=tx_id).exists():
                        messages.success(request, 'Retiro ya procesado (idempotente).')
                    else:
                        LibroMayor.objects.create(cuenta=wallet, tipo_movimiento=LibroMayor.TipoMovimiento.Debito, monto=monto, transaction_id=tx_id)
                        LibroMayor.objects.create(cuenta=casa, tipo_movimiento=LibroMayor.TipoMovimiento.Credito, monto=monto, transaction_id=tx_id)
                        messages.success(request, f'Retiro de S/ {monto} exitoso.')
        except Exception as e:
            messages.error(request, f'Error al procesar el retiro: {e}')
        return redirect('wallet')
    return redirect('wallet')


@login_required
def actualizar_limites(request):
    if request.method == 'POST':
        diario_str = request.POST.get('limite_diario')
        semanal_str = request.POST.get('limite_semanal')
        mensual_str = request.POST.get('limite_mensual')
        try:
            diario = Decimal(diario_str) if diario_str else None
            semanal = Decimal(semanal_str) if semanal_str else None
            mensual = Decimal(mensual_str) if mensual_str else None
            with transaction.atomic():
                juego = juegoResponsabe.objects.select_for_update().get(user=request.user)
                ahora = timezone.now()
                # Helper to apply limit change with cooldown when increasing
                def apply_change(current, new, attr):
                    if new is None:
                        return
                    if new < getattr(juego, attr):
                        setattr(juego, attr, new)
                    else:
                        # increase: enforce 24h cooldown
                        delta = ahora - juego.ultima_modificacion_limite
                        if delta.total_seconds() >= 24*3600:
                            setattr(juego, attr, new)
                            juego.ultima_modificacion_limite = ahora
                        else:
                            raise ValueError(f'No se puede subir el límite de {attr} antes de 24h desde la última actualización.')
                apply_change(juego.limite_diario, diario, 'limite_diario')
                apply_change(juego.limite_semanal, semanal, 'limite_semanal')
                apply_change(juego.limite_mensual, mensual, 'limite_mensual')
                juego.save()
                messages.success(request, 'Límites actualizados correctamente.')
        except Exception as e:
            messages.error(request, f'Error al actualizar límites: {e}')
        return redirect('wallet')
    return redirect('wallet')
