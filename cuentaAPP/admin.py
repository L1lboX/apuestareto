from django.contrib import admin
from .models import Cuenta, LibroMayor

@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'tipo_cuenta', 'saldo_actual_display']
    list_filter = ['tipo_cuenta']
    search_fields = ['usuario__email']

    def saldo_actual_display(self, obj):
        return obj.saldo_actual
    saldo_actual_display.short_description = 'Saldo Actual'

@admin.register(LibroMayor)
class LibroMayorAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'cuenta', 'tipo_movimiento', 'monto', 'fecha_movimiento']
    list_filter = ['tipo_movimiento', 'fecha_movimiento']
    search_fields = ['transaction_id', 'cuenta__usuario__email']
    readonly_fields = ['cuenta', 'tipo_movimiento', 'monto', 'fecha_movimiento', 'transaction_id']

    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
