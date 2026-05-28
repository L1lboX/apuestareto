from django.core.management.base import BaseCommand
from cuentaAPP.models import Cuenta

class Command(BaseCommand):

    def handle(self, *args, **options):
        # Crear cuentas de ejemplo
        Cuenta.objects.create(
            tipo_cuenta=Cuenta.TipoCuenta.Casa,
            usuario = None)
        
        Cuenta.objects.create(
            tipo_cuenta=Cuenta.TipoCuenta.Pendiente,
            usuario = None)
        

        self.stdout.write(self.style.SUCCESS('Cuentas del sistema creadas exitosamente.'))