from datetime import date
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

def validar_edad(fecha_nac):
    fecha_actual = date.today()
    edad = fecha_actual.year - fecha_nac.year - ((fecha_actual.month, fecha_actual.day) < (fecha_nac.month, fecha_nac.day))
    if edad < 18:
        raise ValidationError("El usuario debe ser mayor de edad.")



class User(AbstractUser):
    class EstadoUser(models.TextChoices):
        PENDIENTE = 'pendiente_verificacion', 'Pendiente de Verificación'
        VERIFICADO = 'verificado', 'Verificado'
        BLOQUEADO = 'bloqueado', 'Bloqueado'
        AUTOEXCLUIDO = 'autoexcluido', 'Autoexcluido'

    nombre = models.CharField(max_length=20)
    apellido = models.CharField(max_length=50)
    email = models.EmailField(unique=True, max_length=255)
    telefono = models.CharField(max_length=9)
    dni = models.CharField(max_length=9, unique=True)

    fecha_nacimiento = models.DateField(
        validators=[validar_edad],
        null=True, blank=True)
    
    estado = models.CharField(max_length=30, choices=EstadoUser.choices, default=EstadoUser.PENDIENTE)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'nombre', 'apellido', 'telefono', 'dni']

    def __str__(self):
        return f"{self.email} - {self.get_estado_display()}"
    
    def save(self, *args, **kwargs):
        nuevo = self.pk is None
        super().save(*args, **kwargs)

        if nuevo:
            from cuentaAPP.models import Cuenta

            juegoResponsabe.objects.create(user=self)

            Cuenta.objects.create(
                usuario = self,
                tipo_cuenta = Cuenta.TipoCuenta.Wallet
            )


    

class juegoResponsabe(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    limite_diario = models.DecimalField(max_digits=18, decimal_places=4, default= Decimal('1000.0000'))
    limite_semanal = models.DecimalField(max_digits=18, decimal_places=4, default= Decimal('7000.0000'))
    limite_mensual = models.DecimalField(max_digits=18, decimal_places=4, default= Decimal('15000.0000'))

    ultima_modificacion_limite = models.DateTimeField(default=timezone.now)

    autoexclusion_fecha_fin = models.DateField(null=True, blank=True)
    autoexclusion_indefinida = models.BooleanField(default=False)

    def __str__(self):
        return f"Límites de Juego - {self.user.email}"