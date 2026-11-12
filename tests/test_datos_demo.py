"""Tests del módulo común de datos de la demo y de la web."""

import pandas as pd
import pytest

import market_toolkit.datos_demo as datos_demo
from market_toolkit.models import TipoActivo


def test_cada_ticker_tiene_siempre_la_misma_serie():
    primera = datos_demo.generar_sinteticos(["AAPL", "MSFT"], "^GSPC")
    segunda = datos_demo.generar_sinteticos(["KO", "MSFT", "AAPL"], "^GSPC")
    por_ticker = {serie.activo: serie.serie_temporal for serie in segunda}
    for serie in primera:
        pd.testing.assert_series_equal(serie.serie_temporal, por_ticker[serie.activo])


def test_activos_distintos_tienen_series_distintas():
    aapl, msft = datos_demo.generar_sinteticos(["AAPL", "MSFT"])
    assert not aapl.serie_temporal.equals(msft.serie_temporal)


def test_tipos_de_los_activos_sinteticos():
    series = datos_demo.generar_sinteticos(["SPY", "ORO", "AAPL"], "^GSPC", etfs=["SPY"])
    tipos = {serie.activo: serie.tipo_activo for serie in series}
    assert tipos == {
        "SPY": TipoActivo.ETF,
        "ORO": TipoActivo.COMMODITY,
        "AAPL": TipoActivo.ACCION,
        "^GSPC": TipoActivo.INDICE,
    }
    assert series[-1].activo == "^GSPC"  # El índice va al final


def test_el_indice_sigue_al_mercado_y_los_activos_se_correlacionan():
    series = datos_demo.generar_sinteticos(["AAPL", "MSFT"], "^GSPC")
    rendimientos = pd.DataFrame({s.activo: s.rendimientos() for s in series})
    assert rendimientos.corr().loc["AAPL", "^GSPC"] > 0.4


def test_es_materia_prima():
    assert datos_demo.es_materia_prima("oro")
    assert datos_demo.es_materia_prima("BRENT")
    assert not datos_demo.es_materia_prima("AAPL")


def test_sin_red_no_se_puede_pedir_una_materia_prima_sin_clave(monkeypatch):
    monkeypatch.setattr(datos_demo.config, "ALPHAVANTAGE_API_KEY", None)
    with pytest.raises(ValueError, match="ALPHAVANTAGE_API_KEY"):
        datos_demo.descargar_reales(["GOLD"])
