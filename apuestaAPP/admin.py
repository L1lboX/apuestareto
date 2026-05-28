from django.contrib import admin
from .models import ApuestaMaestra, ApuestaDetalle

class ApuestaDetalleInline(admin.TabularInline):
    model = ApuestaDetalle
    extra = 0
    readonly_fields = ['apuesta_maestra', 'seleccion', 'cuato_aplicada', 'estado']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(ApuestaMaestra)
class ApuestaMaestraAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'usuario', 'tipo', 'estado', 'monto_apostado', 'ganancia_potencial', 'fecha_apuesta']
    list_filter = ['tipo', 'estado', 'fecha_apuesta']
    search_fields = ['transaction_id', 'usuario__email']
    readonly_fields = ['usuario', 'tipo', 'monto_apostado', 'cuota_total', 'ganancia_potencial', 'transaction_id']
    inlines = [ApuestaDetalleInline]

    def has_add_permission(self, request):
        return False

@admin.register(ApuestaDetalle)
class ApuestaDetalleAdmin(admin.ModelAdmin):
    list_display = ['id', 'apuesta_maestra', 'seleccion', 'cuato_aplicada', 'estado']
    list_filter = ['estado']
    search_fields = ['apuesta_maestra__transaction_id', 'seleccion__mercado__evento__local']
