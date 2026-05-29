from django.urls import path
from . import views

urlpatterns = [
    path('hacer/<int:seleccion_id>/', views.hacer_apuesta, name='hacer_apuesta'),
    path('combinada/', views.hacer_apuesta_combinada, name='hacer_apuesta_combinada'),
    path('mis-apuestas/', views.mis_apuestas, name='mis_apuestas'),
]
