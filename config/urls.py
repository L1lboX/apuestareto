"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

admin.site.site_header = 'Administración de Apuestas'
admin.site.site_title = 'Panel de Control'
admin.site.index_title = 'Gestión del Sistema'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('coreAPP.urls')),
    path('eventos/', include('eventoAPP.urls')),
    path('apuestas/', include('apuestaAPP.urls')),
    path('cuenta/', include('cuentaAPP.urls')),
    path('admin-dashboard/', include('adminDashboardAPP.urls')),
]
