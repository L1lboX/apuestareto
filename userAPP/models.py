from datetime import date
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
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
    dni_digito_verificador = models.CharField(
        "digito verificador DNI",
        max_length=1,
        default='',
        validators=[
            RegexValidator(
                regex=r'^\d$',
                message="El digito verificador debe ser un numero del 0 al 9."
            )
        ],
    )

    fecha_nacimiento = models.DateField(
        validators=[validar_edad],
        null=True, blank=True)
    
    estado = models.CharField(max_length=30, choices=EstadoUser.choices, default=EstadoUser.PENDIENTE)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'nombre', 'apellido', 'telefono', 'dni', 'dni_digito_verificador']

    def __str__(self):
        return f"{self.email} - {self.get_estado_display()}"

    @property
    def juegoResponsabe(self):
        try:
            return self.juegoresponsabe
        except juegoResponsabe.DoesNotExist:
            return None
    
    def save(self, *args, **kwargs):
        nuevo = self.pk is None
        super().save(*args, **kwargs)

        if nuevo:
            from cuentaAPP.models import Cuenta

            juegoResponsabe.objects.create(user=self)

            for tipo in Cuenta.TipoCuenta.values:
                Cuenta.objects.create(
                    usuario=self,
                    tipo_cuenta=tipo
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
