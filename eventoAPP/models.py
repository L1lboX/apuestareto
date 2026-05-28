from decimal import Decimal

from django.db import models

class Evento(models.Model):
    class EstadoEvento(models.TextChoices):
        PROGRAMADO = 'programado', 'Programado'
        EN_VIVO = 'en_vivo', 'En Vivo'
        FINALIZADO = 'finalizado', 'Finalizado'
        SUSPENDIDO = 'suspendido', 'Suspendido'
        ANULADO = 'anulado', 'Anulado'

    local = models.CharField(max_length=100)
    visitante = models.CharField(max_length=100)
    fecha_inicio = models.DateTimeField()

    estado = models.CharField(
        max_length=20,
        choices=EstadoEvento.choices,
        default=EstadoEvento.PROGRAMADO
    )

    def __str__(self):
        return f"{self.local} vs {self.visitante} [{self.get_estado_display()}]"
    

class Mercado(models.Model):
    class TipoMercado(models.TextChoices):
       RESULTADO_FINAL = '1x2', 'Gana local (1) / Empate (X) / Gana visitante (2)'
    
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='mercados')
    tipo = models.CharField(
        max_length=20,
        choices=TipoMercado.choices,
        default=TipoMercado.RESULTADO_FINAL
    )

    margen_operador = models.DecimalField(max_digits=5,
                                          decimal_places=2,
                                          default= Decimal('5.00'))
    
    activo = models.BooleanField(default=True)
    

    def __str__(self):
        return f"{self.evento.local} vs {self.evento.visitante} | {self.get_tipodisplay()}"

        
class Seleccion(models.Model):
    class TipoSeleccion(models.TextChoices):
        GANA_LOCAL = '1', 'Gana local'
        EMPATE = 'X', 'Empate'
        GANA_VISITANTE = '2', 'Gana visitante'
    
    mercado = models.ForeignKey(Mercado, on_delete=models.CASCADE, related_name='selecciones')
    tipo = models.CharField(
        max_length=2,
        choices=TipoSeleccion.choices,
    )

    cuota = models.DecimalField(max_digits=7, decimal_places=2)

    def __str__(self):
        return f"{self.get_tipo_display()} | Cuota: {self.cuota}"