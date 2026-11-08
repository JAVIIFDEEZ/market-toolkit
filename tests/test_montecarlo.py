import matplotlib

matplotlib.use("Agg")  # Sin ventanas: los gráficos se generan pero no se muestran

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from market_toolkit.models import FinancialSeries, MonteCarlo, TipoActivo  # noqa: E402


@pytest.fixture
def activo(serie_precios):
    return FinancialSeries(serie_precios, TipoActivo.ACCION, moneda="USD")


def simular(objetivo, **parametros):
    """Lanza una simulación sin guardar gráficos en disco."""
    return MonteCarlo(objetivo, guardar_graficos=False, **parametros)


def test_dimensiones_de_las_trayectorias(activo):
    simulacion = simular(activo, n_simulaciones=50, horizonte=20, semilla=1)
    assert simulacion.trayectorias.shape == (21, 50)  # La primera fila es el valor inicial
    assert (simulacion.trayectorias.iloc[0] == simulacion.valor_inicial).all()


def test_reproducible_con_semilla(activo):
    primera = simular(activo, n_simulaciones=100, horizonte=30, semilla=7)
    segunda = simular(activo, n_simulaciones=100, horizonte=30, semilla=7)
    otra = simular(activo, n_simulaciones=100, horizonte=30, semilla=8)
    pd.testing.assert_frame_equal(primera.trayectorias, segunda.trayectorias)
    assert not primera.trayectorias.equals(otra.trayectorias)


def test_media_simulada_cercana_a_la_teorica(activo):
    # Con un 10 % anual, el valor esperado a un año es el inicial por 1,10
    simulacion = simular(
        activo,
        n_simulaciones=20000,
        rentabilidad=0.10,
        volatilidad=0.20,
        valor_inicial=100,
        semilla=42,
    )
    assert simulacion.valores_finales.mean() == pytest.approx(110, rel=0.01)


def test_cvar_es_al_menos_el_var(activo):
    simulacion = simular(activo, n_simulaciones=2000, semilla=3)
    assert simulacion.cvar(0.95) >= simulacion.var(0.95)
    assert 0 <= simulacion.resumen()["probabilidad_perdida"] <= 1


def test_simula_una_cartera(cartera):
    simulacion = simular(cartera, n_simulaciones=200, horizonte=50, semilla=1)
    assert simulacion.trayectorias.shape == (51, 200)
    assert simulacion.valor_inicial == 100
    assert simulacion.pesos.sum() == pytest.approx(1.0)


def test_metodo_monte_carlo_de_la_cartera(cartera):
    simulacion = cartera.simulacion_monte_carlo(
        n_simulaciones=100, horizonte=20, semilla=1, guardar_graficos=False
    )
    plt.close("all")
    assert isinstance(simulacion, MonteCarlo)


def test_rebalanceo_cambia_el_resultado(cartera):
    con_rebalanceo = simular(cartera, n_simulaciones=500, semilla=1, rebalanceo=True)
    sin_rebalanceo = simular(cartera, n_simulaciones=500, semilla=1, rebalanceo=False)
    assert not np.allclose(con_rebalanceo.valores_finales, sin_rebalanceo.valores_finales)


@pytest.mark.parametrize(
    "parametros",
    [{"n_simulaciones": 0}, {"horizonte": 0}, {"valor_inicial": -1}, {"volatilidad": -0.1}],
)
def test_rechaza_parametros_no_validos(activo, parametros):
    with pytest.raises(ValueError):
        simular(activo, **parametros)


def test_rechaza_objetivos_que_no_son_series_ni_carteras(serie_precios):
    with pytest.raises(TypeError):
        simular(serie_precios)
