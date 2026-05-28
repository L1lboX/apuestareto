from django.urls import path
from . import views

urlpatterns = [
    path('wallet/', views.wallet, name='wallet'),
    path('recargar/', views.recargar, name='recargar'),
    path('retirar/', views.retirar, name='retirar'),
    path('actualizar_limites/', views.actualizar_limites, name='actualizar_limites'),
]
