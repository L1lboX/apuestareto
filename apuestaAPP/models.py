from django.db import models
import uuid

from django.conf import settings

class ApuestaMaestra(models.Model):
    class EstadoApuesta(models.TextChoices):
        ACCEPTED = 'accepted', 'Aceptada'
        WON = 'won', 'Ganada'
        LOAST = 'loast', 'Perdida'
        CASHED_OUT = 'cashed_out', 'Cerrada Anticipadamente'

    class TipoApuesta(models.TextChoices):
        SIMPLE = 'simple', 'Simple'
        COMBINADA = 'combinada', 'Combinada'
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='apuestas')
    tipo = models.CharField(
        max_length=20,
        choices=TipoApuesta.choices,
        default=TipoApuesta.SIMPLE
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoApuesta.choices,
        default=EstadoApuesta.ACCEPTED
    )

    monto_apostado = models.DecimalField(max_digits=18, decimal_places=4)
    cuota_total = models.DecimalField(max_digits=10, decimal_places=4)
    ganancia_potencial = models.DecimalField(max_digits=18, decimal_places=4)
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Apuesta {self.id} - Usuario: {self.usuario.email} - Tipo: {self.get_tipo_display()}"
    

class ApuestaDetalle(models.Model):
    class EstadoApuestaDetalle(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        WON = 'won', 'Ganada'
        LOST = 'lost', 'Perdida'
        VOID = 'void', 'Anulada/Devuelta'

    apuesta_maestra = models.ForeignKey(ApuestaMaestra, on_delete=models.CASCADE, related_name='detalles')
    seleccion = models.ForeignKey('eventoAPP.Seleccion', on_delete=models.CASCADE, related_name='apuestas_detalle')
    cuato_aplicada = models.DecimalField(max_digits=7, decimal_places=2)
    estado = models.CharField(
        max_length=20,
        choices=EstadoApuestaDetalle.choices,
        default=EstadoApuestaDetalle.PENDING
    )

    def __str__(self):
        return f"Detalle de Ticket #{self.apuesta_maestra.id} -> {self.seleccion}"
