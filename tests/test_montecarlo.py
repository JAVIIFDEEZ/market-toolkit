import matplotlib

matplotlib.use("Agg")  # Sin ventanas: los gráficos se generan pero no se muestran

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from market_toolkit.models import FinancialSeries, TipoActivo  # noqa: E402
from market_toolkit.simulation import MonteCarlo  # noqa: E402


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


# ---------- Distribuciones: normal, t de Student y bootstrap ----------


@pytest.fixture
def activo_colas_gruesas(fechas_laborables):
    """Un activo cuyos rendimientos históricos siguen una t de 4 grados (colas gruesas)."""
    rng = np.random.default_rng(11)
    rendimientos = 0.0003 + 0.01 * rng.standard_t(4, len(fechas_laborables)) / np.sqrt(2)
    precios = pd.Series(100 * np.exp(np.cumsum(rendimientos)), index=fechas_laborables, name="TT")
    return FinancialSeries(precios, TipoActivo.ACCION, moneda="USD")


def rendimientos_un_dia(objetivo, **parametros):
    """Rendimientos logarítmicos simulados de una sola sesión."""
    simulacion = simular(objetivo, n_simulaciones=60_000, horizonte=1, semilla=5, **parametros)
    return np.log(simulacion.valores_finales / simulacion.valor_inicial)


def test_normal_es_la_distribucion_por_defecto(activo):
    por_defecto = simular(activo, n_simulaciones=100, horizonte=10, semilla=1)
    normal = simular(activo, n_simulaciones=100, horizonte=10, semilla=1, distribucion="normal")
    pd.testing.assert_frame_equal(por_defecto.trayectorias, normal.trayectorias)


def test_t_tiene_colas_mas_gruesas_con_la_misma_volatilidad(activo):
    normal = rendimientos_un_dia(activo, volatilidad=0.2)
    t = rendimientos_un_dia(activo, volatilidad=0.2, distribucion="t", grados_libertad=4)
    assert t.std() == pytest.approx(normal.std(), rel=0.05)
    assert t.kurt() > normal.kurt() + 1  # Curtosis en exceso: 0 en la normal


def test_t_estima_los_grados_de_libertad(activo_colas_gruesas):
    simulacion = simular(activo_colas_gruesas, n_simulaciones=10, distribucion="t")
    assert 4 < simulacion.grados_libertad < 15
    assert simulacion.resumen()["grados_libertad"] == simulacion.grados_libertad


def test_bootstrap_respeta_la_volatilidad_indicada(activo):
    rendimientos = rendimientos_un_dia(activo, volatilidad=0.3, distribucion="bootstrap")
    assert rendimientos.std() == pytest.approx(0.3 / np.sqrt(252), rel=0.05)


def test_bootstrap_conserva_las_colas_del_historico(activo_colas_gruesas):
    normal = rendimientos_un_dia(activo_colas_gruesas)
    bootstrap = rendimientos_un_dia(activo_colas_gruesas, distribucion="bootstrap")
    assert bootstrap.kurt() > normal.kurt() + 1


def test_bootstrap_de_una_cartera(cartera):
    simulacion = simular(
        cartera, n_simulaciones=200, horizonte=30, semilla=1, distribucion="bootstrap"
    )
    assert simulacion.trayectorias.shape == (31, 200)
    assert simulacion.resumen()["distribucion"] == "bootstrap"


def test_comparar_distribuciones(cartera):
    tabla = MonteCarlo.comparar_distribuciones(cartera, n_simulaciones=500, horizonte=20)
    assert len(tabla) == 3
    assert tabla.index[0] == "Normal"
    assert tabla.index[2] == "Bootstrap histórico"
    assert tabla.index[1].startswith("t de Student")
    assert (tabla["cvar_99"] >= tabla["var_99"]).all()


def test_simulacion_de_la_cartera_con_t(cartera):
    simulacion = cartera.simulacion_monte_carlo(
        n_simulaciones=100,
        horizonte=10,
        semilla=1,
        guardar_graficos=False,
        distribucion="t",
        grados_libertad=6,
    )
    plt.close("all")
    assert simulacion.grados_libertad == 6


@pytest.mark.parametrize(
    "parametros",
    [
        {"distribucion": "lognormal"},
        {"distribucion": "normal", "grados_libertad": 5},
        {"distribucion": "t", "grados_libertad": 2},
    ],
)
def test_rechaza_distribuciones_no_validas(activo, parametros):
    with pytest.raises(ValueError):
        simular(activo, **parametros)
