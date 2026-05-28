import csv
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import EventoForm, SeleccionFormSet, SeleccionForm
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
from .models import AuditoriaRegistro, ActividadSospechosa



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
    summary = None
    if request.method == 'POST':
        evento_id = request.POST.get('evento_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        seleccion_ganadora_id = request.POST.get('seleccion_ganadora_id')
        evento = get_object_or_404(Evento, id=evento_id)
        # Counters for post‑liquidación
        total_processed = 0
        total_won = 0
        total_paid_by_house = Decimal('0.0000')
        with transaction.atomic():
            evento.estado = nuevo_estado
            evento.save()
            if seleccion_ganadora_id and nuevo_estado == Evento.EstadoEvento.FINALIZADO:
                seleccion_ganadora = get_object_or_404(Seleccion, id=seleccion_ganadora_id)
                mercado = seleccion_ganadora.mercado
                # Marcar detalles pendientes del mercado
                detalles = ApuestaDetalle.objects.filter(
                    seleccion__mercado=mercado,
                    estado=ApuestaDetalle.EstadoApuestaDetalle.PENDING
                ).select_for_update()
                maestras_a_revisar = set()
                for detalle in detalles:
                    if str(detalle.seleccion.id) == seleccion_ganadora_id:
                        detalle.estado = ApuestaDetalle.EstadoApuestaDetalle.WON
                    else:
                        detalle.estado = ApuestaDetalle.EstadoApuestaDetalle.LOST
                    detalle.save()
                    maestras_a_revisar.add(detalle.apuesta_maestra)
                # Revisar cada apuesta maestra involucrada
                for maestra in maestras_a_revisar:
                    maestra.refresh_from_db()
                    if maestra.estado != ApuestaMaestra.EstadoApuesta.ACCEPTED:
                        continue
                    total_processed += 1
                    # Obtener todos los detalles de la maestra
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
                        total_won += 1
                        total_paid_by_house += maestra.ganancia_potencial
        # Build a summary message to show in the template
        summary = {
            'total_processed': total_processed,
            'total_won': total_won,
            'total_paid_by_house': total_paid_by_house,
        }
        return render(request, 'admin_dashboard/eventos_control.html', {'eventos': Evento.objects.filter(estado__in=[Evento.EstadoEvento.PROGRAMADO, Evento.EstadoEvento.EN_VIVO]).prefetch_related('mercados__selecciones').order_by('-fecha_inicio'), 'summary': summary})
    # Mostrar solo eventos programados o en vivo
    eventos = Evento.objects.filter(estado__in=[Evento.EstadoEvento.PROGRAMADO, Evento.EstadoEvento.EN_VIVO])\
        .prefetch_related('mercados__selecciones')\
        .order_by('-fecha_inicio')
    return render(request, 'admin_dashboard/eventos_control.html', {'eventos': eventos, 'summary': summary})

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


@user_passes_test(is_staff)
def vista_auditoria(request):
    registros = AuditoriaRegistro.objects.all().order_by('id')
    
    verificacion_resultado = None
    if request.method == 'POST' and 'verificar' in request.POST:
        import hashlib
        import json
        
        integra = True
        error_id = None
        count = 0
        expected_hash_anterior = '0' * 64
        
        for reg in registros:
            if reg.hash_anterior != expected_hash_anterior:
                integra = False
                error_id = reg.id
                break
                
            contenido = expected_hash_anterior + json.dumps(reg.payload, sort_keys=True, default=str)
            computed_hash_actual = hashlib.sha256(contenido.encode()).hexdigest()
            
            if reg.hash_actual != computed_hash_actual:
                integra = False
                error_id = reg.id
                break
                
            expected_hash_anterior = reg.hash_actual
            count += 1
            
        if integra:
            verificacion_resultado = {
                'success': True,
                'message': f"Cadena íntegra: {count} registros verificados"
            }
        else:
            verificacion_resultado = {
                'success': False,
                'message': f"Registro corrupto encontrado en ID: {error_id}"
            }
            
    registros_render = registros.order_by('-id')
    
    context = {
        'registros': registros_render,
        'verificacion_resultado': verificacion_resultado
    }
    return render(request, 'admin_dashboard/auditoria.html', context)


@user_passes_test(is_staff)
def vista_alertas(request):
    if request.method == 'POST' and 'alerta_id' in request.POST:
        alerta_id = request.POST.get('alerta_id')
        alerta = get_object_or_404(ActividadSospechosa, id=alerta_id)
        alerta.revisado = True
        alerta.save()
        return redirect('admin_dashboard:vista_alertas')
        
    alertas = ActividadSospechosa.objects.filter(revisado=False).order_by('-fecha')
    return render(request, 'admin_dashboard/alertas.html', {'alertas': alertas})


@user_passes_test(is_staff)
def vista_usuarios(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        accion = request.POST.get('accion')
        usuario_a_modificar = get_object_or_404(User, id=user_id)
        if accion == 'verificar':
            usuario_a_modificar.estado = User.EstadoUser.VERIFICADO
            usuario_a_modificar.save()
        elif accion == 'bloquear':
            usuario_a_modificar.estado = User.EstadoUser.BLOQUEADO
            usuario_a_modificar.save()
        return redirect('admin_dashboard:vista_usuarios')

    estado_filtro = request.GET.get('estado')
    usuarios = User.objects.all()
    
    if estado_filtro:
        usuarios = usuarios.filter(estado=estado_filtro)
        
    usuarios = usuarios.annotate(
        total_apostado=Sum('apuestas__monto_apostado')
    ).order_by('-date_joined')
    
    context = {
        'usuarios': usuarios,
        'estado_filtro': estado_filtro,
        'choices': User.EstadoUser.choices
    }
    return render(request, 'admin_dashboard/usuarios.html', context)


@user_passes_test(is_staff)
def vista_usuario_apuestas(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    apuestas = ApuestaMaestra.objects.filter(usuario=usuario).order_by('-fecha_apuesta')
    return render(request, 'admin_dashboard/usuario_apuestas.html', {
        'usuario': usuario,
        'apuestas': apuestas
    })

# ---------- NEW VIEWS ----------

@user_passes_test(is_staff)
def crear_evento(request):
    if request.method == 'POST':
        evento_form = EventoForm(request.POST)
        if evento_form.is_valid():
            evento = evento_form.save(commit=False)
            # Estado por defecto PROGRAMADO ya está en modelo
            evento.save()
            # Crear mercado 1X2 asociado al evento
            from eventoAPP.models import Mercado, Seleccion
            mercado = Mercado.objects.create(evento=evento, tipo=Mercado.TipoMercado.RESULTADO_FINAL)
            # Crear selecciones 1, X, 2 con cuotas enviadas en POST
            cuotas = {
                '1': request.POST.get('cuota_1'),
                'X': request.POST.get('cuota_X'),
                '2': request.POST.get('cuota_2'),
            }
            for tipo, cuota in cuotas.items():
                if cuota:
                    Seleccion.objects.create(mercado=mercado, tipo=tipo, cuota=cuota)
            messages.success(request, 'Evento creado correctamente')
            return redirect('admin_dashboard:eventos_control')
    else:
        evento_form = EventoForm()
    return render(request, 'admin_dashboard/eventos_crear.html', {'form': evento_form})

@user_passes_test(is_staff)
def detalle_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    mercado = evento.mercados.first()
    selecciones = mercado.selecciones.all() if mercado else []
    apuestas = ApuestaMaestra.objects.filter(evento=evento).select_related('usuario')
    return render(request, 'admin_dashboard/evento_detalle.html', {
        'evento': evento,
        'mercado': mercado,
        'selecciones': selecciones,
        'apuestas': apuestas,
    })

@user_passes_test(is_staff)
def editar_cuota(request, seleccion_id):
    seleccion = get_object_or_404(Seleccion, id=seleccion_id)
    if request.method == 'POST':
        form = SeleccionForm(request.POST, instance=seleccion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuota actualizada')
            return redirect('admin_dashboard:detalle_evento', evento_id=seleccion.mercado.evento.id)
    else:
        form = SeleccionForm(instance=seleccion)
    return render(request, 'admin_dashboard/eventos_editar.html', {'form': form, 'seleccion': seleccion})

@user_passes_test(is_staff)
def actualizar_estado(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in dict(Evento.EstadoEvento.choices):
            evento.estado = nuevo_estado
            evento.save()
            messages.success(request, f'Estado del evento actualizado a {evento.get_estado_display()}')
    return redirect('admin_dashboard:eventos_control')




