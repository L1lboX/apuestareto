from django.urls import path
app_name = 'admin_dashboard'
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('eventos/', views.eventos_control, name='eventos_control'),
    path('reporte/csv/', views.reporte_csv, name='reporte_csv'),
    path('auditoria/', views.vista_auditoria, name='vista_auditoria'),
    path('alertas/', views.vista_alertas, name='vista_alertas'),
    path('usuarios/', views.vista_usuarios, name='vista_usuarios'),
    path('usuarios/<int:usuario_id>/apuestas/', views.vista_usuario_apuestas, name='vista_usuario_apuestas'),
    path('eventos/crear/', views.crear_evento, name='crear_evento'),
    path('eventos/<int:evento_id>/detalle/', views.detalle_evento, name='detalle_evento'),
    path('cuota/<int:seleccion_id>/editar/', views.editar_cuota, name='editar_cuota'),
    path('eventos/<int:evento_id>/estado/', views.actualizar_estado, name='actualizar_estado'),

]
