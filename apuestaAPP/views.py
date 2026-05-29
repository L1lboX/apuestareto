from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import uuid
from decimal import Decimal
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
            monto = Decimal(monto)
            tx_id = request.POST.get('transaction_id') or str(uuid.uuid4())
            crear_apuesta(request.user, monto, [seleccion.id], tx_id)
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
@csrf_exempt
@require_POST
def hacer_apuesta_combinada(request):
    try:
        data = json.loads(request.body)
        selecciones_ids = data.get('selecciones_ids', [])
        monto_str = data.get('monto')
        tx_id = data.get('transaction_id') or str(uuid.uuid4())

        if not selecciones_ids or len(selecciones_ids) < 1:
            return JsonResponse({'success': False, 'error': 'Selecciona al menos un resultado.'}, status=400)

        monto = Decimal(monto_str)

        crear_apuesta(request.user, monto, selecciones_ids, tx_id)
        return JsonResponse({'success': True, 'redirect': '/apuestas/mis-apuestas/'})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def mis_apuestas(request):
    apuestas = ApuestaMaestra.objects.filter(
        usuario=request.user
    ).prefetch_related(
        'detalles__seleccion__mercado__evento'
    ).order_by('-fecha_apuesta')

    paginator = Paginator(apuestas, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'apuestas/mis_apuestas.html', {
        'apuestas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })
