import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from cuentaAPP.models import Cuenta, LibroMayor
from eventoAPP.models import Evento, Mercado, Seleccion
from userAPP.models import User, juegoResponsabe


class Command(BaseCommand):
    help = "Seeds database with system accounts, initial events, and admin balance."

    def handle(self, *args, **options):
        # 1. Cuentas del sistema
        casa_cuenta, _ = Cuenta.objects.get_or_create(
            tipo_cuenta=Cuenta.TipoCuenta.CASA,
            usuario=None
        )
        pendientes_cuenta, _ = Cuenta.objects.get_or_create(
            tipo_cuenta=Cuenta.TipoCuenta.APUESTAS_PENDIENTES,
            usuario=None
        )
        self.stdout.write(self.style.SUCCESS("✅ Cuentas del sistema OK"))

        # 2. Eventos
        partidos = [
            ("Real Madrid", "Barcelona", 1.85, 3.20, 4.10),
            ("Man. City", "Liverpool", 2.05, 3.45, 3.60),
            ("Bayern", "Dortmund", 1.70, 3.80, 4.50),
            ("PSG", "Marseille", 1.60, 3.90, 5.00),
        ]

        for local, visitante, c1, cx, c2 in partidos:
            e, creado = Evento.objects.get_or_create(
                local=local,
                visitante=visitante,
                defaults={
                    'fecha_inicio': timezone.now() + timedelta(hours=3),
                    'estado': Evento.EstadoEvento.PROGRAMADO
                }
            )
            if creado:
                m = Mercado.objects.create(evento=e, margen_operador=5, activo=True)
                Seleccion.objects.create(mercado=m, tipo=Seleccion.TipoSeleccion.GANA_LOCAL, cuota=c1)
                Seleccion.objects.create(mercado=m, tipo=Seleccion.TipoSeleccion.EMPATE, cuota=cx)
                Seleccion.objects.create(mercado=m, tipo=Seleccion.TipoSeleccion.GANA_VISITANTE, cuota=c2)

        self.stdout.write(self.style.SUCCESS(f"✅ Eventos creados: {Evento.objects.count()}"))

        # 3. Recargar saldo al usuario admin
        try:
            admin = User.objects.get(email='admin@admin.com')
            
            # Garantizar que el admin tenga perfil de juego responsable
            juegoResponsabe.objects.get_or_create(user=admin)

            # Garantizar que el admin tenga las 4 cuentas
            for tipo in Cuenta.TipoCuenta.values:
                Cuenta.objects.get_or_create(usuario=admin, tipo_cuenta=tipo)

            wallet = Cuenta.objects.get(usuario=admin, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
            
            # Generamos transacción balanceada
            tx_id = str(uuid.uuid4())
            monto = Decimal('1000.0000')

            # Crédito al wallet del admin
            LibroMayor.objects.create(
                cuenta=wallet,
                tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
                monto=monto,
                transaction_id=tx_id
            )
            # Débito de la cuenta de la Casa
            LibroMayor.objects.create(
                cuenta=casa_cuenta,
                tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
                monto=monto,
                transaction_id=tx_id
            )

            self.stdout.write(
                self.style.SUCCESS(f"✅ Saldo recargado: {wallet.saldo_actual} fichas")
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("⚠️ No se pudo recargar saldo: El usuario admin@admin.com no existe.")
            )
        except Exception as ex:
            self.stdout.write(
                self.style.ERROR(f"⚠️ No se pudo recargar saldo: {ex}")
            )

        self.stdout.write(self.style.SUCCESS("🎉 Seed completado"))