from django.urls import path
from . import views

urlpatterns = [
    path('', views.evento_lista, name='evento_lista'),
    path('<int:pk>/', views.evento_detalle, name='evento_detalle'),
]
