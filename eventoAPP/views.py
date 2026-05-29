from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Evento, Mercado, Seleccion


def evento_lista(request):
    selecciones_ordenadas = Seleccion.objects.order_by('tipo')
    mercados_activos = Mercado.objects.filter(activo=True).prefetch_related(
        Prefetch('selecciones', queryset=selecciones_ordenadas, to_attr='selecciones_ordenadas')
    )
    eventos = Evento.objects.prefetch_related(
        Prefetch('mercados', queryset=mercados_activos, to_attr='mercados_activos')
    ).order_by('fecha_inicio')
    paginator = Paginator(eventos, 6)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'eventos/lista.html', {
        'eventos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })


def evento_detalle(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    mercados = evento.mercados.filter(activo=True)
    selecciones = Seleccion.objects.filter(mercado__in=mercados)
    return render(request, 'eventos/detalle.html', {
        'evento': evento,
        'mercados': mercados,
        'selecciones': selecciones,
    })
