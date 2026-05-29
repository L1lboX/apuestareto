from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Prefetch
from eventoAPP.models import Evento, Mercado, Seleccion
from .forms import RegistroForm


def home(request):
    selecciones_ordenadas = Seleccion.objects.order_by('tipo')
    mercados_activos = Mercado.objects.filter(activo=True).prefetch_related(
        Prefetch('selecciones', queryset=selecciones_ordenadas, to_attr='selecciones_ordenadas')
    )
    eventos = Evento.objects.filter(
        estado__in=[Evento.EstadoEvento.PROGRAMADO, Evento.EstadoEvento.EN_VIVO]
    ).prefetch_related(
        Prefetch('mercados', queryset=mercados_activos, to_attr='mercados_activos')
    ).order_by('fecha_inicio')[:6]
    return render(request, 'home.html', {'eventos': eventos})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_staff or user.is_superuser:
                return redirect('admin_dashboard:dashboard_home')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Cuenta creada. Ya puedes apostar.')
            return redirect('home')
    else:
        form = RegistroForm()
    return render(request, 'register.html', {'form': form})
