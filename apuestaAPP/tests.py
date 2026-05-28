import uuid
from decimal import Decimal
from django.test import TransactionTestCase
from django.utils import timezone
from datetime import timedelta

from userAPP.models import User, juegoResponsabe
from eventoAPP.models import Evento, Mercado, Seleccion
from cuentaAPP.models import Cuenta, LibroMayor
from cuentaAPP.servicio import bloquear_fondos, liquidar_apuesta_ganada, liquidar_apuesta_perdida
from apuestaAPP.models import ApuestaMaestra, ApuestaDetalle
from apuestaAPP.servicios import crear_apuesta


class TestApuestaServicios(TransactionTestCase):
    def setUp(self):
        # Limpieza inicial
        LibroMayor.objects.all().delete()
        ApuestaDetalle.objects.all().delete()
        ApuestaMaestra.objects.all().delete()
        Seleccion.objects.all().delete()
        Mercado.objects.all().delete()
        Evento.objects.all().delete()
        Cuenta.objects.all().delete()
        juegoResponsabe.objects.all().delete()
        User.objects.all().delete()

        # Crear usuario verificado
        self.user = User.objects.create_user(
            username="bet_user",
            email="bet_user@fairbet.test",
            password="Password123!",
            nombre="Bet",
            apellido="User",
            telefono="987654321",
            dni="12345678",
            dni_digito_verificador="9",
            estado=User.EstadoUser.VERIFICADO,
        )

        # Cargar saldo
        self.wallet = Cuenta.objects.get(usuario=self.user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
        self.casa = Cuenta.objects.get(usuario=self.user, tipo_cuenta=Cuenta.TipoCuenta.CASA)
        self.pendientes = Cuenta.objects.get(usuario=self.user, tipo_cuenta=Cuenta.TipoCuenta.APUESTAS_PENDIENTES)

        # Cargar 1000 fichas en wallet
        tx_id = str(uuid.uuid4())
        LibroMayor.objects.create(
            cuenta=self.wallet,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=Decimal("1000.0000"),
            transaction_id=tx_id
        )
        LibroMayor.objects.create(
            cuenta=self.casa,
            tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
            monto=Decimal("1000.0000"),
            transaction_id=tx_id
        )

        # Crear evento, mercado y selección
        self.evento = Evento.objects.create(
            local="Real Madrid",
            visitante="Barcelona",
            fecha_inicio=timezone.now() + timedelta(days=1),
            estado=Evento.EstadoEvento.PROGRAMADO
        )
        self.mercado = Mercado.objects.create(
            evento=self.evento,
            tipo=Mercado.TipoMercado.RESULTADO_FINAL
        )
        self.seleccion = Seleccion.objects.create(
            mercado=self.mercado,
            tipo=Seleccion.TipoSeleccion.GANA_LOCAL,
            cuota=Decimal("2.00")
        )

    def test_crear_apuesta_exitoso(self):
        """Verifica que crear_apuesta funcione de forma exitosa."""
        tx_id = str(uuid.uuid4())
        apuesta = crear_apuesta(self.user, Decimal("100.0000"), [self.seleccion.id], tx_id)
        
        self.assertIsNotNone(apuesta)
        self.assertEqual(apuesta.monto_apostado, Decimal("100.0000"))
        self.assertEqual(apuesta.cuota_total, Decimal("2.00"))
        self.assertEqual(apuesta.ganancia_potencial, Decimal("200.0000"))
        self.assertEqual(apuesta.estado, ApuestaMaestra.EstadoApuesta.ACCEPTED)

        # Verificar wallet disminuido
        self.assertEqual(self.wallet.saldo_actual, Decimal("900.0000"))
        # Verificar pendientes aumentados
        self.assertEqual(self.pendientes.saldo_actual, Decimal("100.0000"))

    def test_crear_apuesta_idempotencia(self):
        """Verifica que llamar a crear_apuesta dos veces con el mismo tx_id sea idempotente."""
        tx_id = str(uuid.uuid4())
        ap1 = crear_apuesta(self.user, Decimal("100.0000"), [self.seleccion.id], tx_id)
        ap2 = crear_apuesta(self.user, Decimal("100.0000"), [self.seleccion.id], tx_id)

        self.assertEqual(ap1.id, ap2.id)
        self.assertEqual(self.wallet.saldo_actual, Decimal("900.0000"))
        
        # Deben haber exactamente 2 entradas en el LibroMayor para esta transacción
        movs = LibroMayor.objects.filter(transaction_id=tx_id)
        self.assertEqual(movs.count(), 2)

    def test_bloquear_fondos_idempotencia(self):
        """Verifica que bloquear_fondos sea estrictamente idempotente con el mismo transaction_id."""
        tx_id = str(uuid.uuid4())
        
        # Primera llamada
        bloquear_fondos(self.user, Decimal("50.0000"), tx_id)
        self.assertEqual(self.wallet.saldo_actual, Decimal("950.0000"))
        
        # Segunda llamada con el mismo tx_id
        bloquear_fondos(self.user, Decimal("50.0000"), tx_id)
        self.assertEqual(self.wallet.saldo_actual, Decimal("950.0000"))  # No debe descontarse de nuevo

        # Total de movimientos para esa tx debe ser exactamente 2
        self.assertEqual(LibroMayor.objects.filter(transaction_id=tx_id).count(), 2)

    def test_liquidar_apuesta_ganada_idempotencia(self):
        """Verifica que liquidar_apuesta_ganada sea idempotente."""
        tx_bloqueo = str(uuid.uuid4())
        apuesta = crear_apuesta(self.user, Decimal("100.0000"), [self.seleccion.id], tx_bloqueo)

        tx_liq = str(uuid.uuid4())
        apuesta.estado = ApuestaMaestra.EstadoApuesta.WON
        apuesta.save()

        # Primera liquidación
        liquidar_apuesta_ganada(apuesta, tx_liq)
        # 900 anterior + 200 de ganancia = 1100
        self.assertEqual(self.wallet.saldo_actual, Decimal("1100.0000"))

        # Segunda liquidación con la misma tx
        liquidar_apuesta_ganada(apuesta, tx_liq)
        self.assertEqual(self.wallet.saldo_actual, Decimal("1100.0000"))  # No cambia

    def test_liquidar_apuesta_perdida_idempotencia(self):
        """Verifica que liquidar_apuesta_perdida sea idempotente."""
        tx_bloqueo = str(uuid.uuid4())
        apuesta = crear_apuesta(self.user, Decimal("100.0000"), [self.seleccion.id], tx_bloqueo)

        tx_liq = str(uuid.uuid4())
        apuesta.estado = ApuestaMaestra.EstadoApuesta.LOAST
        apuesta.save()

        # Primera liquidación
        liquidar_apuesta_perdida(apuesta, tx_liq)
        self.assertEqual(self.wallet.saldo_actual, Decimal("900.0000"))  # Queda igual
        self.assertEqual(self.casa.saldo_actual, Decimal("-900.0000"))   # Casa recibe +100 (tenía -1000 inicial, -1000 + 100 = -900)

        # Segunda liquidación con la misma tx
        liquidar_apuesta_perdida(apuesta, tx_liq)
        self.assertEqual(self.casa.saldo_actual, Decimal("-900.0000"))  # No cambia

    def test_limite_diario_excedido(self):
        """Verifica que no se pueda apostar superando el límite diario."""
        perfil = self.user.juegoResponsabe
        perfil.limite_diario = Decimal("50.0000")
        perfil.save()

        tx_id = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("60.0000"), [self.seleccion.id], tx_id)
        self.assertIn("Límite diario excedido", str(ctx.exception))

    def test_autoexclusion_indefinida(self):
        """Verifica que un usuario autoexcluido indefinidamente no pueda apostar."""
        perfil = self.user.juegoResponsabe
        perfil.autoexclusion_indefinida = True
        perfil.save()

        tx_id = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("10.0000"), [self.seleccion.id], tx_id)
        self.assertIn("autoexcluido indefinidamente", str(ctx.exception))

    def test_autoexclusion_temporal(self):
        """Verifica que un usuario autoexcluido temporalmente no pueda apostar."""
        perfil = self.user.juegoResponsabe
        perfil.autoexclusion_fecha_fin = timezone.now().date() + timedelta(days=5)
        perfil.save()

        tx_id = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("10.0000"), [self.seleccion.id], tx_id)
        self.assertIn("autoexcluida temporalmente", str(ctx.exception))

    def test_usuario_no_verificado(self):
        """Verifica que un usuario no verificado no pueda apostar."""
        self.user.estado = User.EstadoUser.PENDIENTE
        self.user.save()

        tx_id = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("10.0000"), [self.seleccion.id], tx_id)
        self.assertIn("no está verificado", str(ctx.exception))

    def test_evento_ya_comenzo(self):
        """Verifica que no se pueda apostar si el evento ya comenzó."""
        self.evento.fecha_inicio = timezone.now() - timedelta(minutes=10)
        self.evento.save()

        tx_id = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("10.0000"), [self.seleccion.id], tx_id)
        self.assertIn("ya ha comenzado", str(ctx.exception))

    def test_monto_fuera_de_rango(self):
        """Verifica que el monto de la apuesta debe estar en el rango válido."""
        tx_id = str(uuid.uuid4())
        # Menor al mínimo
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("0.5000"), [self.seleccion.id], tx_id)
        self.assertIn("debe estar entre", str(ctx.exception))

        # Mayor al máximo
        tx_id2 = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("20000.0000"), [self.seleccion.id], tx_id2)
        self.assertIn("debe estar entre", str(ctx.exception))

    def test_saldo_insuficiente(self):
        """Verifica que falle si el usuario no tiene suficiente saldo."""
        tx_id = str(uuid.uuid4())
        # Saldo actual es 1000. Intentar apostar 1001.
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("1001.0000"), [self.seleccion.id], tx_id)
        self.assertIn("Saldo insuficiente", str(ctx.exception))

    def test_limite_semanal_excedido(self):
        """Verifica que falle si se supera el límite semanal."""
        perfil = self.user.juegoResponsabe
        perfil.limite_semanal = Decimal("150.0000")
        perfil.save()

        # Realizamos una apuesta de 100.00
        tx1 = str(uuid.uuid4())
        crear_apuesta(self.user, Decimal("100.0000"), [self.seleccion.id], tx1)

        # La siguiente de 60.00 excede el límite semanal
        tx2 = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("60.0000"), [self.seleccion.id], tx2)
        self.assertIn("Límite semanal excedido", str(ctx.exception))

    def test_limite_mensual_excedido(self):
        """Verifica que falle si se supera el límite mensual."""
        perfil = self.user.juegoResponsabe
        perfil.limite_mensual = Decimal("150.0000")
        perfil.save()

        # Realizamos una apuesta de 100.00
        tx1 = str(uuid.uuid4())
        crear_apuesta(self.user, Decimal("100.0000"), [self.seleccion.id], tx1)

        # La siguiente de 60.00 excede el límite mensual
        tx2 = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("60.0000"), [self.seleccion.id], tx2)
        self.assertIn("Límite mensual excedido", str(ctx.exception))

    def test_evento_no_programado(self):
        """Verifica que no se pueda apostar si el evento no está en estado PROGRAMADO."""
        self.evento.estado = Evento.EstadoEvento.EN_VIVO
        self.evento.save()

        tx_id = str(uuid.uuid4())
        with self.assertRaises(ValueError) as ctx:
            crear_apuesta(self.user, Decimal("10.0000"), [self.seleccion.id], tx_id)
        self.assertIn("ya no está disponible para apostar", str(ctx.exception))

