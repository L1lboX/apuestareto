import uuid

from django.db import models
from django.conf import settings
from decimal import Decimal

class Cuenta(models.Model):
    class TipoCuenta(models.TextChoices):
       Casa = 'casa', 'Cuenta de Casa'
       Pendiente = 'pendiente', 'Apuestas Pendientes'
       Wallet = 'wallet', 'Cuenta de usuario'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name='cuentas',
        null=True, blank=True
    )

    tipo_cuenta = models.CharField(
        max_length=20,
        choices=TipoCuenta.choices
    )

    @property
    def saldo_actual(self):
        creditos = self.movimientos.filter(tipo_movimiento='credito').aggregate(total_creditos=models.Sum('monto'))['total_creditos'] or Decimal('0.0000')
        debitos = self.movimientos.filter(tipo_movimiento='debito').aggregate(total_debitos=models.Sum('monto'))['total_debitos'] or Decimal('0.0000')
        return creditos - debitos
    
    
class LibroMayor(models.Model):
    class TipoMovimiento(models.TextChoices):
        Credito = 'credito', 'Crédito'
        Debito = 'debito', 'Débito'

    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    monto = models.DecimalField(max_digits=10, decimal_places=4)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False
    )
       
