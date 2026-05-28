from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from eventoAPP.models import Evento
from .forms import RegistroForm


def home(request):
    eventos = Evento.objects.filter(estado__in=['programado', 'en_vivo'])[:6]
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
