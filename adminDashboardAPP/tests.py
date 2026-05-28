from decimal import Decimal
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from userAPP.models import User
from apuestaAPP.models import ApuestaMaestra
from cuentaAPP.models import Cuenta, LibroMayor
from .models import AuditoriaRegistro, ActividadSospechosa
from eventoAPP.models import Evento, Mercado, Seleccion


class AuditoriaTestCase(TestCase):
    def setUp(self):
        # Create a staff user to login to admin dashboard
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password123',
            nombre='Admin',
            apellido='Test',
            telefono='999999999',
            dni='999999999',
            dni_digito_verificador='9',
            fecha_nacimiento='1990-01-01'
        )
        self.client = Client()
        self.client.login(email='admin@test.com', password='password123')

    def test_immutable_registro_save_fails_on_update(self):
        # Create record
        reg = AuditoriaRegistro.objects.create(
            tipo_evento='TEST',
            payload={},
            hash_anterior='0'*64,
            hash_actual='1'*64
        )
        # Attempting to save again (update) must raise ValueError
        with self.assertRaises(ValueError):
            reg.save()

    def test_apuesta_creacion_triggers_audit_signal(self):
        # We need a user to create a bet
        user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='password123',
            nombre='User',
            apellido='Test',
            telefono='988888888',
            dni='988888888',
            dni_digito_verificador='8',
            fecha_nacimiento='2000-01-01'
        )
        # Create a bet
        ApuestaMaestra.objects.create(
            usuario=user,
            tipo=ApuestaMaestra.TipoApuesta.SIMPLE,
            estado=ApuestaMaestra.EstadoApuesta.ACCEPTED,
            monto_apostado=Decimal('10.00'),
            cuota_total=Decimal('2.00'),
            ganancia_potencial=Decimal('20.00')
        )
        # Query AuditoriaRegistro
        logs = AuditoriaRegistro.objects.filter(tipo_evento='APUESTA_CREADA')
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.payload['usuario_id'], user.id)
        self.assertEqual(log.payload['monto'], '10.00')
        self.assertEqual(log.payload['cuota_total'], '2.00')
        self.assertEqual(log.payload['tipo'], 'simple')

    def test_libromayor_creacion_triggers_audit_signal(self):
        # Get user's wallet
        user = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='password123',
            nombre='User2',
            apellido='Test',
            telefono='977777777',
            dni='977777777',
            dni_digito_verificador='7',
            fecha_nacimiento='2000-01-01'
        )
        cuenta = user.cuentas.get(tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
        # Create transaction
        LibroMayor.objects.create(
            cuenta=cuenta,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=Decimal('50.00'),
            transaction_id='tx-12345'
        )
        # Query AuditoriaRegistro
        logs = AuditoriaRegistro.objects.filter(tipo_evento='WALLET_MOVIMIENTO')
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.payload['cuenta_id'], cuenta.id)
        self.assertEqual(log.payload['tipo_movimiento'], 'credito')
        self.assertEqual(log.payload['monto'], '50.00')
        self.assertEqual(log.payload['transaction_id'], 'tx-12345')

    def test_integrity_verification_success(self):
        user = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='password123',
            nombre='User3',
            apellido='Test',
            telefono='966666666',
            dni='966666666',
            dni_digito_verificador='6',
            fecha_nacimiento='2000-01-01'
        )
        # Trigger some signals
        ApuestaMaestra.objects.create(
            usuario=user,
            tipo=ApuestaMaestra.TipoApuesta.SIMPLE,
            estado=ApuestaMaestra.EstadoApuesta.ACCEPTED,
            monto_apostado=Decimal('15.00'),
            cuota_total=Decimal('3.00'),
            ganancia_potencial=Decimal('45.00')
        )
        # Verify via web view
        url = reverse('admin_dashboard:vista_auditoria')
        response = self.client.post(url, {'verificar': '1'})
        self.assertEqual(response.status_code, 200)
        res = response.context['verificacion_resultado']
        self.assertTrue(res['success'])
        self.assertIn("Cadena íntegra", res['message'])

    def test_integrity_verification_failure_when_corrupted(self):
        user = User.objects.create_user(
            username='user4',
            email='user4@test.com',
            password='password123',
            nombre='User4',
            apellido='Test',
            telefono='955555555',
            dni='955555555',
            dni_digito_verificador='5',
            fecha_nacimiento='2000-01-01'
        )
        ApuestaMaestra.objects.create(
            usuario=user,
            tipo=ApuestaMaestra.TipoApuesta.SIMPLE,
            monto_apostado=Decimal('10.00'),
            cuota_total=Decimal('2.00'),
            ganancia_potencial=Decimal('20.00')
        )
        
        # Corrupt the database directly bypassing the save() override using update()
        log = AuditoriaRegistro.objects.first()
        AuditoriaRegistro.objects.filter(id=log.id).update(hash_actual='corruptedhashvalue12345')
        
        # Verify via web view
        url = reverse('admin_dashboard:vista_auditoria')
        response = self.client.post(url, {'verificar': '1'})
        self.assertEqual(response.status_code, 200)
        res = response.context['verificacion_resultado']
        self.assertFalse(res['success'])
        self.assertIn(f"Registro corrupto encontrado en ID: {log.id}", res['message'])


from apuestaAPP.servicios import crear_apuesta
import uuid

class AntifraudeTestCase(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='suspect',
            email='suspect@test.com',
            password='password123',
            nombre='Suspect',
            apellido='Test',
            telefono='944444444',
            dni='944444444',
            dni_digito_verificador='4',
            fecha_nacimiento='2000-01-01',
            estado=User.EstadoUser.VERIFICADO
        )
        self.wallet = self.user.cuentas.get(tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO)
        LibroMayor.objects.create(
            cuenta=self.wallet,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
            monto=Decimal('1000.00'),
            transaction_id='initial-deposit'
        )
        
        self.evento = Evento.objects.create(
            local='Real Madrid',
            visitante='Barcelona',
            fecha_inicio=timezone.now() + timezone.timedelta(hours=5),
            estado=Evento.EstadoEvento.PROGRAMADO
        )
        self.mercado = Mercado.objects.create(
            evento=self.evento,
            tipo=Mercado.TipoMercado.RESULTADO_FINAL,
            activo=True
        )
        self.seleccion = Seleccion.objects.create(
            mercado=self.mercado,
            tipo=Seleccion.TipoSeleccion.GANA_LOCAL,
            cuota=Decimal('2.00')
        )

        self.admin_user = User.objects.create_superuser(
            username='admin_fraud',
            email='admin_fraud@test.com',
            password='password123',
            nombre='Admin',
            apellido='Test',
            telefono='933333333',
            dni='933333333',
            dni_digito_verificador='3',
            fecha_nacimiento='1990-01-01'
        )
        self.client = Client()
        self.client.login(email='admin_fraud@test.com', password='password123')

    def test_regla_alto_riesgo_triggered(self):
        crear_apuesta(self.user, Decimal('801.00'), [self.seleccion.id], str(uuid.uuid4()))
        
        alertas = ActividadSospechosa.objects.filter(usuario=self.user, tipo_alerta='APUESTA_ALTO_RIESGO')
        self.assertEqual(alertas.count(), 1)
        self.assertIn("supera el 80% del saldo total", alertas.first().descripcion)

    def test_regla_apuestas_repetidas_triggered(self):
        for i in range(4):
            crear_apuesta(self.user, Decimal('10.00'), [self.seleccion.id], str(uuid.uuid4()))
            
        alertas = ActividadSospechosa.objects.filter(usuario=self.user, tipo_alerta='APUESTAS_REPETIDAS')
        self.assertEqual(alertas.count(), 1)
        self.assertIn("realizado 4 apuestas del mismo monto", alertas.first().descripcion)

    def test_alerta_revisar_action(self):
        crear_apuesta(self.user, Decimal('900.00'), [self.seleccion.id], str(uuid.uuid4()))
        
        alerta = ActividadSospechosa.objects.filter(revisado=False).first()
        self.assertIsNotNone(alerta)
        
        url = reverse('admin_dashboard:vista_alertas')
        response = self.client.post(url, {'alerta_id': alerta.id})
        self.assertEqual(response.status_code, 302)
        
        alerta.refresh_from_db()
        self.assertTrue(alerta.revisado)

