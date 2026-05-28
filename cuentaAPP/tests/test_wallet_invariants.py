"""
Tests de invariantes financieras para el wallet con partida doble.

Utiliza hypothesis para generar secuencias arbitrarias de operaciones
y verificar que las invariantes contables se mantienen en todo momento.

Invariantes probadas:
  1. Suma global de LibroMayor (créditos - débitos) == 0
  2. Ningún wallet_usuario termina con saldo negativo
  3. Payout de apuesta ganada == stake × odds (precisión Decimal exacta)
  4. Concurrencia: 10 hilos apostando el mismo saldo → solo 1 pasa
"""
import uuid
import threading
from decimal import Decimal, ROUND_DOWN

import pytest
from hypothesis import given, settings as hyp_settings, HealthCheck
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from django.db import connection
from django.db.models import Sum, Q
from django.test import TransactionTestCase

from cuentaAPP.models import Cuenta, LibroMayor
from cuentaAPP.servicio import (
    bloquear_fondos,
    liquidar_apuesta_ganada,
    liquidar_apuesta_perdida,
)
from apuestaAPP.models import ApuestaMaestra, ApuestaDetalle
from userAPP.models import User, juegoResponsabe
from eventoAPP.models import Evento, Mercado, Seleccion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crear_usuario_con_saldo(saldo_inicial=Decimal("10000.0000")):
    """
    Crea un usuario verificado con las 4 cuentas contables y un
    depósito inicial balanceado contablemente.

    Entradas de LibroMayor generadas:
      - CRÉDITO en wallet_usuario  por `saldo_inicial` (depósito)
      - DÉBITO  en casa            por `saldo_inicial` (la casa entrega fichas)

    Esto mantiene la invariante créditos == débitos desde el inicio.
    """
    email = f"test_{uuid.uuid4().hex[:8]}@fairbet.test"
    user = User.objects.create_user(
        username=f"u_{uuid.uuid4().hex[:6]}",
        email=email,
        password="Test12345!",
        nombre="Test",
        apellido="Invariante",
        telefono="999999999",
        dni=str(uuid.uuid4().int)[:8],
        dni_digito_verificador="1",
        estado=User.EstadoUser.VERIFICADO,
    )
    # El User.save() ya crea las 4 cuentas y el perfil de juego responsable.
    # Depositamos fichas con partida doble balanceada.
    wallet = Cuenta.objects.get(
        usuario=user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO
    )
    casa = Cuenta.objects.get(
        usuario=user, tipo_cuenta=Cuenta.TipoCuenta.CASA
    )
    tx_deposito = str(uuid.uuid4())

    # Crédito al wallet (el usuario recibe fichas)
    LibroMayor.objects.create(
        cuenta=wallet,
        tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
        monto=saldo_inicial,
        transaction_id=tx_deposito,
    )
    # Débito de la casa (la casa entrega fichas)
    LibroMayor.objects.create(
        cuenta=casa,
        tipo_movimiento=LibroMayor.TipoMovimiento.Debito,
        monto=saldo_inicial,
        transaction_id=tx_deposito,
    )
    return user


def _crear_evento_con_selecciones():
    """
    Crea un evento programado con un mercado 1X2 y 3 selecciones.
    Devuelve (evento, [seleccion_local, seleccion_empate, seleccion_visitante]).
    """
    from django.utils import timezone
    from datetime import timedelta

    evento = Evento.objects.create(
        local="Equipo A",
        visitante="Equipo B",
        fecha_inicio=timezone.now() + timedelta(days=1),
        estado=Evento.EstadoEvento.PROGRAMADO,
    )
    mercado = Mercado.objects.create(
        evento=evento,
        tipo=Mercado.TipoMercado.RESULTADO_FINAL,
    )
    sel_local = Seleccion.objects.create(
        mercado=mercado,
        tipo=Seleccion.TipoSeleccion.GANA_LOCAL,
        cuota=Decimal("2.50"),
    )
    sel_empate = Seleccion.objects.create(
        mercado=mercado,
        tipo=Seleccion.TipoSeleccion.EMPATE,
        cuota=Decimal("3.20"),
    )
    sel_visitante = Seleccion.objects.create(
        mercado=mercado,
        tipo=Seleccion.TipoSeleccion.GANA_VISITANTE,
        cuota=Decimal("2.80"),
    )
    return evento, [sel_local, sel_empate, sel_visitante]


def _crear_apuesta_simple(usuario, monto, seleccion, tx_id=None):
    """
    Crea una ApuestaMaestra SIMPLE bloqueando fondos vía servicio contable.
    Devuelve la ApuestaMaestra creada.

    Entradas de LibroMayor generadas (por bloquear_fondos):
      - DÉBITO  en wallet_usuario        por `monto`
      - CRÉDITO en apuestas_pendientes   por `monto`
    """
    tx = tx_id or str(uuid.uuid4())
    monto = Decimal(str(monto))

    bloquear_fondos(usuario, monto, tx)

    cuota = seleccion.cuota
    ganancia = monto * cuota

    apuesta = ApuestaMaestra.objects.create(
        usuario=usuario,
        tipo=ApuestaMaestra.TipoApuesta.SIMPLE,
        estado=ApuestaMaestra.EstadoApuesta.ACCEPTED,
        monto_apostado=monto,
        cuota_total=cuota,
        ganancia_potencial=ganancia,
        transaction_id=tx,
    )
    ApuestaDetalle.objects.create(
        apuesta_maestra=apuesta,
        seleccion=seleccion,
        cuato_aplicada=cuota,
        estado=ApuestaDetalle.EstadoApuestaDetalle.PENDING,
    )
    return apuesta


def _limpiar_db():
    """Limpia todas las tablas relevantes para una ejecución aislada de Hypothesis."""
    LibroMayor.objects.all().delete()
    ApuestaDetalle.objects.all().delete()
    ApuestaMaestra.objects.all().delete()
    Seleccion.objects.all().delete()
    Mercado.objects.all().delete()
    Evento.objects.all().delete()
    Cuenta.objects.all().delete()
    juegoResponsabe.objects.all().delete()
    User.objects.filter(email__endswith="@fairbet.test").delete()


# ---------------------------------------------------------------------------
# INVARIANTE 1 — Suma global de LibroMayor == 0
# ---------------------------------------------------------------------------

class TestInvarianteSumaGlobalCero(HypothesisTestCase):
    """
    Dado cualquier conjunto de operaciones válidas, la suma global
    de todos los registros en LibroMayor (créditos − débitos) siempre
    debe ser CERO.
    """

    @given(
        montos=st.lists(
            st.decimals(
                min_value=Decimal("1.0000"),
                max_value=Decimal("500.0000"),
                places=4,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @hyp_settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_suma_global_siempre_cero(self, montos):
        """
        Genera N apuestas con montos aleatorios, liquida aleatoriamente
        como ganadas o perdidas, y verifica que la suma neta del libro
        mayor sea cero.
        """
        _limpiar_db()

        user = _crear_usuario_con_saldo()
        _, selecciones = _crear_evento_con_selecciones()
        sel = selecciones[0]

        apuestas = []
        for monto in montos:
            monto = monto.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
            if monto < Decimal("1.0000"):
                monto = Decimal("1.0000")
            try:
                ap = _crear_apuesta_simple(user, monto, sel)
                apuestas.append(ap)
            except ValueError:
                break  # Saldo insuficiente

        # Liquidar: alternamos ganada/perdida
        for i, ap in enumerate(apuestas):
            tx = str(uuid.uuid4())
            if i % 2 == 0:
                ap.estado = ApuestaMaestra.EstadoApuesta.WON
                ap.save()
                liquidar_apuesta_ganada(ap, tx)
            else:
                ap.estado = ApuestaMaestra.EstadoApuesta.LOAST
                ap.save()
                liquidar_apuesta_perdida(ap, tx)

        # INVARIANTE: créditos - débitos == 0
        totales = LibroMayor.objects.aggregate(
            creditos=Sum("monto", filter=Q(tipo_movimiento="credito")),
            debitos=Sum("monto", filter=Q(tipo_movimiento="debito")),
        )
        total_creditos = totales["creditos"] or Decimal("0.0000")
        total_debitos = totales["debitos"] or Decimal("0.0000")

        assert total_creditos == total_debitos, (
            f"Invariante violada: créditos={total_creditos} ≠ débitos={total_debitos} "
            f"(diferencia={total_creditos - total_debitos})"
        )


# ---------------------------------------------------------------------------
# INVARIANTE 2 — Ningún wallet queda negativo
# ---------------------------------------------------------------------------

class TestInvarianteWalletNoNegativo(HypothesisTestCase):
    """
    Ningún wallet_usuario debe terminar con saldo negativo después
    de una secuencia de apuestas.
    """

    @given(
        montos=st.lists(
            st.decimals(
                min_value=Decimal("1.0000"),
                max_value=Decimal("2000.0000"),
                places=4,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=1,
            max_size=8,
        ),
    )
    @hyp_settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_wallet_nunca_negativo(self, montos):
        """
        Intenta apostar montos aleatorios secuencialmente.
        Verifica que bloquear_fondos rechace correctamente cuando
        no hay saldo, y que el wallet nunca sea negativo.
        """
        _limpiar_db()

        user = _crear_usuario_con_saldo()
        _, selecciones = _crear_evento_con_selecciones()
        sel = selecciones[0]

        for monto in montos:
            monto = monto.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
            if monto < Decimal("1.0000"):
                monto = Decimal("1.0000")
            try:
                _crear_apuesta_simple(user, monto, sel)
            except ValueError:
                pass  # Fondos insuficientes — esperado

        # INVARIANTE: saldo del wallet >= 0
        wallet = Cuenta.objects.get(
            usuario=user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO
        )
        saldo = wallet.saldo_actual
        assert saldo >= Decimal("0"), (
            f"Invariante violada: wallet de {user.email} tiene saldo negativo: {saldo}"
        )


# ---------------------------------------------------------------------------
# INVARIANTE 3 — Payout == stake × odds (precisión Decimal exacta)
# ---------------------------------------------------------------------------

class TestInvariantePayoutExacto(HypothesisTestCase):
    """
    El payout de una apuesta ganadora siempre es exactamente
    stake × odds sin pérdida de precisión decimal.
    """

    @given(
        stake=st.decimals(
            min_value=Decimal("1.0000"),
            max_value=Decimal("5000.0000"),
            places=4,
            allow_nan=False,
            allow_infinity=False,
        ),
        odds=st.decimals(
            min_value=Decimal("1.01"),
            max_value=Decimal("100.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @hyp_settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_payout_precision_exacta(self, stake, odds):
        """
        Crea una apuesta con stake y cuota generados por Hypothesis,
        la liquida como ganada, y verifica que los créditos en el
        wallet del usuario reflejen exactamente stake × odds.
        """
        _limpiar_db()

        stake = stake.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
        odds = odds.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        if stake < Decimal("1.0000"):
            stake = Decimal("1.0000")
        if odds < Decimal("1.01"):
            odds = Decimal("1.01")

        payout_esperado = (stake * odds).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

        user = _crear_usuario_con_saldo()

        # Crear evento con cuota personalizada
        from django.utils import timezone
        from datetime import timedelta

        evento = Evento.objects.create(
            local="Equipo Test",
            visitante="Rival Test",
            fecha_inicio=timezone.now() + timedelta(days=1),
            estado=Evento.EstadoEvento.PROGRAMADO,
        )
        mercado = Mercado.objects.create(
            evento=evento,
            tipo=Mercado.TipoMercado.RESULTADO_FINAL,
        )
        sel = Seleccion.objects.create(
            mercado=mercado,
            tipo=Seleccion.TipoSeleccion.GANA_LOCAL,
            cuota=odds,
        )

        tx_bloqueo = str(uuid.uuid4())
        bloquear_fondos(user, stake, tx_bloqueo)

        apuesta = ApuestaMaestra.objects.create(
            usuario=user,
            tipo=ApuestaMaestra.TipoApuesta.SIMPLE,
            estado=ApuestaMaestra.EstadoApuesta.ACCEPTED,
            monto_apostado=stake,
            cuota_total=odds,
            ganancia_potencial=payout_esperado,
            transaction_id=tx_bloqueo,
        )

        # Liquidar como ganada
        tx_liquidacion = str(uuid.uuid4())
        apuesta.estado = ApuestaMaestra.EstadoApuesta.WON
        apuesta.save()
        liquidar_apuesta_ganada(apuesta, tx_liquidacion)

        # Verificar que el crédito de liquidación sea exactamente payout_esperado
        credito_liquidacion = LibroMayor.objects.get(
            transaction_id=tx_liquidacion,
            tipo_movimiento=LibroMayor.TipoMovimiento.Credito,
        )

        assert credito_liquidacion.monto == payout_esperado, (
            f"Payout incorrecto: esperado={payout_esperado}, "
            f"recibido={credito_liquidacion.monto}, "
            f"stake={stake}, odds={odds}"
        )

        # Verificar tipo Decimal, nunca float
        assert isinstance(credito_liquidacion.monto, Decimal), (
            f"El monto no es Decimal: {type(credito_liquidacion.monto)}"
        )


# ---------------------------------------------------------------------------
# TEST DE CONCURRENCIA — Sin doble gasto
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestConcurrenciaDobleGasto(TransactionTestCase):
    """
    Simula 10 requests simultáneos apostando el mismo saldo total
    del usuario y verifica que solo UNO pase (los otros fallen con
    error de saldo insuficiente). Ningún doble gasto debe ocurrir.

    Usa TransactionTestCase (no HypothesisTestCase) porque necesita
    threading real con commits visibles entre hilos.
    """

    def test_10_hilos_solo_uno_pasa(self):
        """
        Crea un usuario con exactamente 100.0000 fichas.
        Lanza 10 hilos, cada uno intentando apostar 100.0000.
        Solo 1 debe tener éxito; los otros 9 deben fallar.

        Verifica:
          - Exactamente 1 éxito de bloqueo de fondos.
          - Wallet queda en 0 (no negativo).
          - Suma global de LibroMayor == 0.
        """
        _limpiar_db()

        user = _crear_usuario_con_saldo(saldo_inicial=Decimal("100.0000"))
        _, selecciones = _crear_evento_con_selecciones()

        resultados = {"exitos": 0, "fallos": 0}
        lock = threading.Lock()
        barrier = threading.Barrier(10)

        def intentar_apostar():
            """Cada hilo intenta bloquear 100.0000 fichas."""
            try:
                barrier.wait(timeout=10)
                tx = str(uuid.uuid4())
                bloquear_fondos(user, Decimal("100.0000"), tx)
                with lock:
                    resultados["exitos"] += 1
            except (ValueError, Exception):
                with lock:
                    resultados["fallos"] += 1
            finally:
                connection.close()

        hilos = [threading.Thread(target=intentar_apostar) for _ in range(10)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=30)

        # VERIFICACIONES
        # 1. Solo 1 éxito
        assert resultados["exitos"] == 1, (
            f"Se esperaba 1 éxito, pero hubo {resultados['exitos']}. "
            f"Posible doble gasto detectado."
        )

        # 2. Wallet no negativo
        wallet = Cuenta.objects.get(
            usuario=user, tipo_cuenta=Cuenta.TipoCuenta.WALLET_USUARIO
        )
        saldo_final = wallet.saldo_actual
        assert saldo_final >= Decimal("0"), (
            f"Wallet negativo: {saldo_final}. ¡DOBLE GASTO!"
        )

        # 3. Suma global == 0
        totales = LibroMayor.objects.aggregate(
            creditos=Sum("monto", filter=Q(tipo_movimiento="credito")),
            debitos=Sum("monto", filter=Q(tipo_movimiento="debito")),
        )
        total_c = totales["creditos"] or Decimal("0.0000")
        total_d = totales["debitos"] or Decimal("0.0000")
        assert total_c == total_d, (
            f"Suma global inconsistente: créditos={total_c}, débitos={total_d}"
        )
