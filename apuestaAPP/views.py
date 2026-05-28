from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from eventoAPP.models import Seleccion
from apuestaAPP.models import ApuestaMaestra
from .servicios import crear_apuesta


@login_required
def hacer_apuesta(request, seleccion_id):
    seleccion = get_object_or_404(Seleccion, pk=seleccion_id)
    evento = seleccion.mercado.evento

    if request.method == 'POST':
        try:
            monto = request.POST.get('monto')
            from decimal import Decimal
            monto = Decimal(monto)
            crear_apuesta(request.user, monto, [seleccion.id])
            messages.success(request, 'Apuesta realizada con exito.')
            return redirect('mis_apuestas')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, 'Ocurrio un error al procesar la apuesta.')

    return render(request, 'apuestas/hacer.html', {
        'seleccion': seleccion,
        'evento': evento,
    })


@login_required
def mis_apuestas(request):
    apuestas = ApuestaMaestra.objects.filter(
        usuario=request.user
    ).order_by('-fecha_apuesta')

    return render(request, 'apuestas/mis_apuestas.html', {
        'apuestas': apuestas,
    })
