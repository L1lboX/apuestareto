import csv
import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.db.models import Sum, F, Count
from django.utils import timezone
from django.db import transaction

from apuestaAPP.models import ApuestaMaestra, ApuestaDetalle
from eventoAPP.models import Evento, Seleccion
from cuentaAPP.servicio import liquidar_apuesta_ganada, liquidar_apuesta_perdida
from userAPP.models import User


def is_staff(user):
    return user.is_staff

@user_passes_test(is_staff)
def dashboard_home(request):
    hoy = timezone.now().date()
    
    # GGR = SUM(monto_apostado of liquidated bets) - SUM(ganancia_potencial of won bets)
    liquidated_bets = ApuestaMaestra.objects.filter(estado__in=[ApuestaMaestra.EstadoApuesta.WON, ApuestaMaestra.EstadoApuesta.LOAST])
    
    total_apostado_liquidado = liquidated_bets.aggregate(Sum('monto_apostado'))['monto_apostado__sum'] or Decimal('0.0000')
    won_bets = ApuestaMaestra.objects.filter(estado=ApuestaMaestra.EstadoApuesta.WON)
    total_ganado_usuarios = won_bets.aggregate(Sum('ganancia_potencial'))['ganancia_potencial__sum'] or Decimal('0.0000')
    
    ggr = total_apostado_liquidado - total_ganado_usuarios

    # Exposure por selección (Solo apuestas aceptadas)
    # SUM(monto_apostado * cuota_aplicada) for each selection in active bets
    # We approximate exposure by selecting the pending details
    pendientes = ApuestaDetalle.objects.filter(estado=ApuestaDetalle.EstadoApuestaDetalle.PENDING)
    exposure_list = pendientes.values(
        'seleccion__tipo', 'seleccion__mercado__evento__local', 'seleccion__mercado__evento__visitante'
    ).annotate(
        total_exposure=Sum(F('apuesta_maestra__monto_apostado') * F('cuato_aplicada'))
    ).order_by('-total_exposure')[:10]

    apuestas_activas = ApuestaMaestra.objects.filter(estado=ApuestaMaestra.EstadoApuesta.ACCEPTED).count()
    usuarios_hoy = User.objects.filter(date_joined__date=hoy).count()
    volumen_hoy = ApuestaMaestra.objects.filter(fecha_apuesta__date=hoy).aggregate(Sum('monto_apostado'))['monto_apostado__sum'] or Decimal('0.0000')

    context = {
        'ggr': ggr,
        'exposure_list': exposure_list,
        'apuestas_activas': apuestas_activas,
        'usuarios_hoy': usuarios_hoy,
        'volumen_hoy': volumen_hoy,
    }
    return render(request, 'admin_dashboard/index.html', context)

@user_passes_test(is_staff)
def eventos_control(request):
    if request.method == 'POST':
        evento_id = request.POST.get('evento_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        seleccion_ganadora_id = request.POST.get('seleccion_ganadora_id')

        evento = get_object_or_404(Evento, id=evento_id)
        
        with transaction.atomic():
            evento.estado = nuevo_estado
            evento.save()

            if seleccion_ganadora_id and nuevo_estado == Evento.EstadoEvento.FINALIZADO:
                seleccion_ganadora = get_object_or_404(Seleccion, id=seleccion_ganadora_id)
                mercado = seleccion_ganadora.mercado
                
                # Marcar detalles
                detalles = ApuestaDetalle.objects.filter(seleccion__mercado=mercado, estado=ApuestaDetalle.EstadoApuestaDetalle.PENDING).select_for_update()
                
                maestras_a_revisar = set()
                
                for detalle in detalles:
                    if str(detalle.seleccion.id) == seleccion_ganadora_id:
                        detalle.estado = ApuestaDetalle.EstadoApuestaDetalle.WON
                    else:
                        detalle.estado = ApuestaDetalle.EstadoApuestaDetalle.LOST
                    detalle.save()
                    maestras_a_revisar.add(detalle.apuesta_maestra)
                
                # Revisar Apuestas Maestras
                for maestra in maestras_a_revisar:
                    # Refresh from db
                    maestra.refresh_from_db()
                    
                    if maestra.estado != ApuestaMaestra.EstadoApuesta.ACCEPTED:
                        continue
                    
                    todos_detalles = maestra.detalles.all()
                    hay_perdida = any(d.estado == ApuestaDetalle.EstadoApuestaDetalle.LOST for d in todos_detalles)
                    todos_ganados = all(d.estado == ApuestaDetalle.EstadoApuestaDetalle.WON for d in todos_detalles)
                    
                    tx_id = str(uuid.uuid4())
                    
                    if hay_perdida:
                        maestra.estado = ApuestaMaestra.EstadoApuesta.LOAST
                        maestra.save()
                        liquidar_apuesta_perdida(maestra, tx_id)
                    elif todos_ganados:
                        maestra.estado = ApuestaMaestra.EstadoApuesta.WON
                        maestra.save()
                        liquidar_apuesta_ganada(maestra, tx_id)

        return redirect('eventos_control')

    eventos = Evento.objects.prefetch_related('mercados__selecciones').order_by('-fecha_inicio')
    return render(request, 'admin_dashboard/eventos_control.html', {'eventos': eventos})

@user_passes_test(is_staff)
def reporte_csv(request):
    mes = request.GET.get('mes') # YYYY-MM
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_apuestas_{mes}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Usuario ID', 'Email', 'Tipo', 'Monto Apostado', 'Cuota Total', 'Ganancia Potencial', 'Estado'])

    if mes:
        año, m = mes.split('-')
        apuestas = ApuestaMaestra.objects.filter(fecha_apuesta__year=año, fecha_apuesta__month=m).select_related('usuario')
    else:
        apuestas = ApuestaMaestra.objects.all().select_related('usuario')

    for ap in apuestas:
        writer.writerow([
            ap.fecha_apuesta.strftime("%Y-%m-%d %H:%M:%S"),
            ap.usuario.id,
            ap.usuario.email,
            ap.get_tipo_display(),
            ap.monto_apostado,
            ap.cuota_total,
            ap.ganancia_potencial,
            ap.get_estado_display(),
        ])

    return response
