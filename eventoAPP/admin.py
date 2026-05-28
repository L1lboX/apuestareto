from django.contrib import admin
from .models import Evento, Mercado, Seleccion

class SeleccionInline(admin.TabularInline):
    model = Seleccion
    extra = 3

class MercadoInline(admin.TabularInline):
    model = Mercado
    extra = 1

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['id', 'local', 'visitante', 'estado', 'fecha_inicio']
    list_filter = ['estado', 'fecha_inicio']
    search_fields = ['local', 'visitante']
    inlines = [MercadoInline]

@admin.register(Mercado)
class MercadoAdmin(admin.ModelAdmin):
    list_display = ['id', 'evento', 'tipo', 'margen_operador', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['evento__local', 'evento__visitante']
    inlines = [SeleccionInline]

@admin.register(Seleccion)
class SeleccionAdmin(admin.ModelAdmin):
    list_display = ['id', 'mercado', 'tipo', 'cuota']
    list_filter = ['tipo']
    search_fields = ['mercado__evento__local', 'mercado__evento__visitante']
