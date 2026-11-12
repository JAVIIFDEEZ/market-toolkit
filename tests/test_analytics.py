import math

import numpy as np
import pandas as pd
import pytest

from market_toolkit.analytics import (
    alfa_jensen,
    base_100,
    beta,
    caidas,
    drawdown_maximo,
    grados_libertad_t,
    information_ratio,
    metricas_benchmark,
    ratio_sharpe,
    rentabilidad_anualizada,
    tracking_error,
    volatilidad_anualizada,
)
from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.exceptions import InsufficientDataError

FECHAS = pd.bdate_range("2024-01-02", periods=500)


@pytest.fixture
def mercado():
    rng = np.random.default_rng(1)
    return pd.Series(rng.normal(0.0004, 0.01, len(FECHAS)), index=FECHAS)


# ---------- Benchmark ----------


def test_beta_de_una_cartera_apalancada(mercado):
    # Una cartera que se mueve 1,5 veces el mercado tiene beta 1,5
    assert beta(1.5 * mercado, mercado) == pytest.approx(1.5)


def test_alfa_de_una_cartera_con_rentabilidad_extra(mercado):
    extra_diario = 0.0002
    cartera = mercado + extra_diario
    assert alfa_jensen(cartera, mercado) == pytest.approx(extra_diario * DIAS_COTIZACION_ANUAL)


def test_tracking_error_e_information_ratio(mercado):
    rng = np.random.default_rng(2)
    diferencia = pd.Series(rng.normal(0.0001, 0.003, len(FECHAS)), index=FECHAS)
    cartera = mercado + diferencia
    error = diferencia.std() * np.sqrt(DIAS_COTIZACION_ANUAL)
    assert tracking_error(cartera, mercado) == pytest.approx(error)
    assert information_ratio(cartera, mercado) == pytest.approx(
        diferencia.mean() * DIAS_COTIZACION_ANUAL / error
    )


def test_replicar_el_benchmark(mercado):
    metricas = metricas_benchmark(mercado, mercado)
    assert metricas["beta"] == pytest.approx(1.0)
    assert metricas["alfa"] == pytest.approx(0.0, abs=1e-12)
    assert metricas["tracking_error"] == pytest.approx(0.0, abs=1e-12)
    assert math.isnan(metricas["information_ratio"])
    assert metricas["correlacion"] == pytest.approx(1.0)


def test_usa_solo_las_fechas_comunes(mercado):
    cartera = mercado.iloc[100:]
    metricas = metricas_benchmark(cartera, mercado)
    assert metricas["sesiones_comunes"] == len(cartera)
    assert metricas["rentabilidad_benchmark"] == pytest.approx((1 + mercado.iloc[100:]).prod() - 1)


def test_sin_fechas_comunes(mercado):
    otra = pd.Series([0.01, 0.02], index=pd.bdate_range("2030-01-01", periods=2))
    with pytest.raises(InsufficientDataError):
        metricas_benchmark(mercado, otra)


# ---------- Grados de libertad de la t ----------


def test_grados_libertad_de_una_t():
    rendimientos = np.random.default_rng(3).standard_t(5, 300_000)
    assert grados_libertad_t(rendimientos) == pytest.approx(5, abs=0.5)


def test_grados_libertad_de_una_normal_es_el_maximo():
    rendimientos = np.random.default_rng(4).standard_normal(100_000)
    assert grados_libertad_t(rendimientos) == 100.0


# ---------- Rendimientos ----------


def test_anualizar():
    assert rentabilidad_anualizada(0.0) == 0
    assert rentabilidad_anualizada(0.001) == pytest.approx(1.001**252 - 1)
    assert volatilidad_anualizada(0.01) == pytest.approx(0.01 * math.sqrt(252))
    medias = pd.Series({"A": 0.0, "B": 0.001})
    assert list(rentabilidad_anualizada(medias).index) == ["A", "B"]


def test_ratio_sharpe():
    rendimientos = pd.Series([0.01, -0.005, 0.002, 0.004, -0.001])
    esperado = (rendimientos.mean() - 0.02 / 252) / rendimientos.std() * math.sqrt(252)
    assert ratio_sharpe(rendimientos, 0.02) == pytest.approx(esperado)


def test_caidas_y_drawdown_maximo():
    valores = pd.Series([100.0, 120.0, 90.0, 110.0, 130.0, 117.0])
    assert list(caidas(valores).round(4)) == [0, 0, -0.25, -0.0833, 0, -0.1]
    assert drawdown_maximo(valores) == pytest.approx(0.25)


def test_base_100_desde_el_primer_precio_conocido():
    precios = pd.DataFrame({"A": [50.0, 55.0, 60.0], "B": [np.nan, 20.0, 10.0]})
    resultado = base_100(precios)
    assert list(resultado["A"]) == pytest.approx([100, 110, 120])
    assert np.isnan(resultado["B"].iloc[0])
    assert list(resultado["B"].iloc[1:]) == pytest.approx([100, 50])
    assert list(base_100(pd.Series([4.0, 5.0]))) == pytest.approx([100, 125])
