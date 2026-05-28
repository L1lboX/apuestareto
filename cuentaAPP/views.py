from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Cuenta, LibroMayor
import uuid
from decimal import Decimal


@login_required
def wallet(request):
    wallet = Cuenta.objects.get(usuario=request.user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
    movimientos = wallet.movimientos.order_by('-fecha_movimiento')[:20]
    return render(request, 'cuenta/wallet.html', {
        'wallet': wallet,
        'movimientos': movimientos,
    })


@login_required
def recargar(request):
    if request.method == 'POST':
        monto = request.POST.get('monto')
        try:
            monto = Decimal(monto)
            wallet = Cuenta.objects.get(
                usuario=request.user,
                tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO
            )
            casa = Cuenta.objects.get(usuario=request.user, tipo_cuenta=Cuenta.TipoCuenta.CASA)
            tx_id = str(uuid.uuid4())
            LibroMayor.objects.create(cuenta=casa, tipo_movimiento=LibroMayor.TipoMovimiento.Debito, monto=monto, transaction_id=tx_id)
            LibroMayor.objects.create(cuenta=wallet, tipo_movimiento=LibroMayor.TipoMovimiento.Credito, monto=monto, transaction_id=tx_id)
            messages.success(request, f'Recarga de S/ {monto} exitosa.')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, 'Error al procesar la recarga.')
        return redirect('wallet')
    return redirect('wallet')
