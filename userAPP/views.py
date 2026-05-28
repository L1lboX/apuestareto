from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from userAPP.models import juegoResponsabe

# Create your views here.

@login_required
def autoexcluir(request):
    """Permite al usuario auto‑excluirse por 7, 30, 90 días o indefinidamente.
    La exclusión es irreversible hasta la fecha indicada.
    """
    perfil = juegoResponsabe.objects.get(user=request.user)
    # Si ya hay exclusión activa, impedir cambios
    if perfil.autoexclusion_fecha_fin and perfil.autoexclusion_fecha_fin > timezone.now().date():
        messages.error(request, f'Tu cuenta está autoexcluida hasta {perfil.autoexclusion_fecha_fin}. No puedes realizar apuestas.')
        return render(request, 'user/autoexcluir.html', {'perfil': perfil, 'blocked': True})
    if request.method == 'POST':
        opcion = request.POST.get('opcion')
        fecha_fin = None
        indefinido = False
        if opcion == '7':
            fecha_fin = timezone.now().date() + timedelta(days=7)
        elif opcion == '30':
            fecha_fin = timezone.now().date() + timedelta(days=30)
        elif opcion == '90':
            fecha_fin = timezone.now().date() + timedelta(days=90)
        elif opcion == 'indefinido':
            indefinido = True
        else:
            messages.error(request, 'Opción no válida.')
            return redirect('autoexcluir')
        # Guardar exclusión
        perfil.autoexclusion_fecha_fin = None if indefinido else fecha_fin
        perfil.autoexclusion_indefinida = indefinido
        perfil.save()
        if indefinido:
            messages.success(request, 'Has sido autoexcluido indefinidamente.')
        else:
            messages.success(request, f'Has sido autoexcluido hasta {fecha_fin}.')
        return redirect('autoexcluir')
    return render(request, 'user/autoexcluir.html', {'perfil': perfil, 'blocked': False})
