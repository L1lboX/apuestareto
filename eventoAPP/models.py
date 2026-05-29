from decimal import Decimal

from django.db import models


class Evento(models.Model):
    class Deporte(models.TextChoices):
        FUTBOL = 'futbol', 'Futbol'
        BALONCESTO = 'baloncesto', 'Baloncesto'
        VOLEIBOL = 'voleibol', 'Voleibol'
        TENIS = 'tenis', 'Tenis'

    class EstadoEvento(models.TextChoices):
        PROGRAMADO = 'programado', 'Programado'
        EN_VIVO = 'en_vivo', 'En Vivo'
        FINALIZADO = 'finalizado', 'Finalizado'
        SUSPENDIDO = 'suspendido', 'Suspendido'
        ANULADO = 'anulado', 'Anulado'

    local = models.CharField(max_length=100)
    visitante = models.CharField(max_length=100)
    fecha_inicio = models.DateTimeField()
    deporte = models.CharField(
        max_length=20,
        choices=Deporte.choices,
        default=Deporte.FUTBOL
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoEvento.choices,
        default=EstadoEvento.PROGRAMADO
    )

    def __str__(self):
        return f"{self.local} vs {self.visitante} [{self.get_estado_display()}]"


class Mercado(models.Model):
    class TipoMercado(models.TextChoices):
        RESULTADO_FINAL = 'resultado_final', 'Resultado Final (1X2)'
        GANADOR_PARTIDO = 'ganador_partido', 'Ganador del Partido (1-2)'
        GANADOR_SETS = 'ganador_sets', 'Marcador Exacto de Sets'

    SELECCIONES_POR_MERCADO = {
        'resultado_final': [
            ('1', 'Gana local'),
            ('X', 'Empate'),
            ('2', 'Gana visitante'),
        ],
        'ganador_partido': [
            ('1', 'Gana local'),
            ('2', 'Gana visitante'),
        ],
        'ganador_sets': [
            ('3-0', '3-0'),
            ('3-1', '3-1'),
            ('3-2', '3-2'),
            ('2-3', '2-3'),
            ('1-3', '1-3'),
            ('0-3', '0-3'),
        ],
    }

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='mercados')
    tipo = models.CharField(
        max_length=30,
        choices=TipoMercado.choices,
        default=TipoMercado.RESULTADO_FINAL
    )
    margen_operador = models.DecimalField(max_digits=5,
                                          decimal_places=2,
                                          default=Decimal('5.00'))
    activo = models.BooleanField(default=True)
    suspension_hasta = models.DateTimeField(null=True, blank=True)

    @property
    def esta_suspendido(self):
        from django.utils import timezone
        return self.suspension_hasta and timezone.now() < self.suspension_hasta

    @property
    def selecciones_disponibles(self):
        return self.SELECCIONES_POR_MERCADO.get(self.tipo, [])

    def __str__(self):
        return f"{self.evento.local} vs {self.evento.visitante} | {self.get_tipo_display()}"


class Seleccion(models.Model):
    class TipoSeleccion(models.TextChoices):
        GANA_LOCAL = '1', 'Gana local'
        EMPATE = 'X', 'Empate'
        GANA_VISITANTE = '2', 'Gana visitante'
        SETS_30 = '3-0', '3-0'
        SETS_31 = '3-1', '3-1'
        SETS_32 = '3-2', '3-2'
        SETS_23 = '2-3', '2-3'
        SETS_13 = '1-3', '1-3'
        SETS_03 = '0-3', '0-3'

    mercado = models.ForeignKey(Mercado, on_delete=models.CASCADE, related_name='selecciones')
    tipo = models.CharField(
        max_length=3,
        choices=TipoSeleccion.choices,
    )
    cuota = models.DecimalField(max_digits=7, decimal_places=2)

    def __str__(self):
        return f"{self.get_tipo_display()} | Cuota: {self.cuota}"
