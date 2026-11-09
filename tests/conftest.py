"""Fixtures compartidas: precios sintéticos generados sin acceso a red."""

import numpy as np
import pandas as pd
import pytest

SEMILLA = 42


def generar_precios(
    tickers: list[str],
    fechas: pd.DatetimeIndex,
    *,
    mu: float = 0.0005,
    sigma: float = 0.01,
    precio_inicial: float = 100.0,
    semilla: int = SEMILLA,
) -> pd.DataFrame:
    """
    Genera precios con un random walk lognormal reproducible.
    :param tickers: Nombres de las columnas (activos).
    :param fechas: Índice temporal de los precios.
    :param mu: Media diaria de los rendimientos logarítmicos.
    :param sigma: Desviación típica diaria de los rendimientos logarítmicos.
    :param precio_inicial: Precio de partida de todos los activos.
    :param semilla: Semilla del generador aleatorio.
    :return: Dataframe con una columna de precios por activo.
    """
    rng = np.random.default_rng(semilla)
    log_rendimientos = rng.normal(mu, sigma, size=(len(fechas), len(tickers)))
    precios = precio_inicial * np.exp(np.cumsum(log_rendimientos, axis=0))
    return pd.DataFrame(precios, index=fechas, columns=tickers)


@pytest.fixture
def fechas_laborables() -> pd.DatetimeIndex:
    """Un año de días laborables."""
    return pd.bdate_range("2024-01-01", periods=252, name="Date")


@pytest.fixture
def precios_sinteticos(fechas_laborables: pd.DatetimeIndex) -> pd.DataFrame:
    """Precios limpios y alineados de tres acciones."""
    return generar_precios(["AAA", "BBB", "CCC"], fechas_laborables)


@pytest.fixture
def serie_precios(precios_sinteticos: pd.DataFrame) -> pd.Series:
    """Serie de precios limpia de un único activo."""
    return precios_sinteticos["AAA"]


@pytest.fixture
def precios_calendarios_distintos(fechas_laborables: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Precios de dos activos con calendarios distintos y algún NaN, como los que devuelve una API:
    `USA` no cotiza algunos días en los que `EUR` sí lo hace y `EUR` empieza más tarde.
    """
    precios = generar_precios(["USA", "EUR"], fechas_laborables)
    precios.iloc[[10, 50, 100], 0] = np.nan  # festivos de un mercado
    precios.iloc[:5, 1] = np.nan  # el segundo activo empieza a cotizar más tarde
    precios.iloc[200, 1] = np.nan  # dato perdido
    return precios


@pytest.fixture(autouse=True)
def carpeta_graficos_temporal(tmp_path, monkeypatch):
    """Los gráficos que se guardan durante los tests van a una carpeta temporal, no al repo."""
    import market_toolkit.simulation.montecarlo as montecarlo
    monkeypatch.setattr(montecarlo, "CARPETA_GRAFICOS", tmp_path / "graficos")


@pytest.fixture
def activos_usd(precios_sinteticos: pd.DataFrame) -> list:
    """Tres acciones en USD, para que la cartera no tenga que descargar tipos de cambio."""
    from market_toolkit.models import FinancialSeries, TipoActivo

    activos = []
    for ticker in precios_sinteticos.columns:
        activos.append(FinancialSeries(precios_sinteticos[ticker], TipoActivo.ACCION, moneda="USD"))
    return activos


@pytest.fixture
def pesos_iniciales(fechas_laborables: pd.DatetimeIndex) -> pd.DataFrame:
    """Pesos 50/30/20 fijados el primer día, sin rebalanceos posteriores."""
    return pd.DataFrame({"AAA": [0.5], "BBB": [0.3], "CCC": [0.2]}, index=[fechas_laborables[0]])


@pytest.fixture
def cartera(activos_usd: list, pesos_iniciales: pd.DataFrame):
    """Cartera de tres acciones en USD con pesos 50/30/20."""
    from market_toolkit.models import Portfolio

    return Portfolio(activos_usd, pesos_iniciales)
