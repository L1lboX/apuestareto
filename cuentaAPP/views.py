from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Cuenta, LibroMayor
from .servicio import realizar_transferencia
from decimal import Decimal


@login_required
def wallet(request):
    wallet = Cuenta.objects.get(usuario=request.user, tipo_cuenta=Cuenta.TipoCuenta.Wallet)
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
                tipo_cuenta=Cuenta.TipoCuenta.Wallet
            )
            casa = Cuenta.objects.get(tipo_cuenta=Cuenta.TipoCuenta.Casa)
            realizar_transferencia(casa.id, wallet.id, monto)
            messages.success(request, f'Recarga de S/ {monto} exitosa.')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, 'Error al procesar la recarga.')
        return redirect('wallet')
    return redirect('wallet')
