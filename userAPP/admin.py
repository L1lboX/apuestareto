from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, juegoResponsabe

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'nombre', 'apellido', 'dni', 'telefono', 'estado']
    list_filter = ['estado', 'is_staff', 'is_active']
    search_fields = ['email', 'nombre', 'apellido', 'dni']
    ordering = ['email']
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('dni', 'dni_digito_verificador', 'telefono', 'fecha_nacimiento', 'estado')}),
    )

@admin.register(juegoResponsabe)
class JuegoResponsableAdmin(admin.ModelAdmin):
    list_display = ['user', 'limite_diario', 'limite_semanal', 'limite_mensual', 'autoexclusion_fecha_fin', 'autoexclusion_indefinida']
    search_fields = ['user__email']
    list_filter = ['autoexclusion_indefinida']