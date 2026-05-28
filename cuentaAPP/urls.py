from django.urls import path
from . import views

urlpatterns = [
    path('wallet/', views.wallet, name='wallet'),
    path('recargar/', views.recargar, name='recargar'),
]
