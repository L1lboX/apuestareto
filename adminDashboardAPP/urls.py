from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('eventos/', views.eventos_control, name='eventos_control'),
    path('reporte/csv/', views.reporte_csv, name='reporte_csv'),
]
