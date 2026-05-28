from django.db import models

class AuditoriaRegistro(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    tipo_evento = models.CharField(max_length=50)
    # Valores: 'APUESTA_CREADA', 'WALLET_MOVIMIENTO', 'ODDS_CAMBIO', 'LIQUIDACION'
    payload = models.JSONField()
    hash_anterior = models.CharField(max_length=64)
    hash_actual = models.CharField(max_length=64)

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        if self.pk:  # Si ya existe, es un update — prohibido
            raise ValueError('AuditoriaRegistro es append-only. No se puede modificar.')
        super().save(*args, **kwargs)


from django.conf import settings

class ActividadSospechosa(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tipo_alerta = models.CharField(max_length=100)
    # Valores: 'APUESTAS_REPETIDAS', 'APUESTA_ALTO_RIESGO'
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    revisado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tipo_alerta} - User: {self.usuario.email} - Revisado: {self.revisado}"

