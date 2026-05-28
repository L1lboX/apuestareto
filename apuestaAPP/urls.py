from django.urls import path
from . import views

urlpatterns = [
    path('hacer/<int:seleccion_id>/', views.hacer_apuesta, name='hacer_apuesta'),
    path('mis-apuestas/', views.mis_apuestas, name='mis_apuestas'),
]
