from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Evento, Mercado, Seleccion


def evento_lista(request):
    eventos = Evento.objects.all().order_by('fecha_inicio')
    return render(request, 'eventos/lista.html', {'eventos': eventos})


def evento_detalle(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    mercados = evento.mercados.filter(activo=True)
    selecciones = Seleccion.objects.filter(mercado__in=mercados)
    return render(request, 'eventos/detalle.html', {
        'evento': evento,
        'mercados': mercados,
        'selecciones': selecciones,
    })
