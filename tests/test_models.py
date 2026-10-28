import dataclasses

import numpy as np
import pandas as pd
import pytest

from market_toolkit.config import DIAS_COTIZACION_ANUAL, MIN_OBSERVACIONES
from market_toolkit.exceptions import DataValidationError, InsufficientDataError
from market_toolkit.models import FinancialSeries, Fundamentales, MacroSeries, TipoActivo


@pytest.fixture
def serie_financiera(serie_precios):
    return FinancialSeries(
        serie_precios,
        {"nombre": "Acción AAA"},
        tipo_activo=TipoActivo.ACCION,
        moneda="USD",
        proveedor="Sintético",
    )


# ---------- FinancialSeries ----------


def test_properties(serie_financiera, serie_precios):
    assert serie_financiera.nombre == "Acción AAA"
    assert serie_financiera.activo == "AAA"
    assert serie_financiera.tipo == "acción"
    assert serie_financiera.inicio == serie_precios.index[0].date()
    assert serie_financiera.fin == serie_precios.index[-1].date()
    assert serie_financiera.duracion == (serie_financiera.fin - serie_financiera.inicio).days
    assert serie_financiera.observaciones == len(serie_precios)


def test_nombre_por_defecto_es_el_activo(serie_precios):
    serie = FinancialSeries(serie_precios)
    assert serie.nombre == "AAA"


def test_estadisticos_automaticos(serie_financiera, serie_precios):
    rendimientos = serie_precios.pct_change().dropna()
    media = rendimientos.mean()
    desviacion = rendimientos.std()
    assert serie_financiera.media == pytest.approx(media)
    assert serie_financiera.desviacion_tipica == pytest.approx(desviacion)
    assert serie_financiera.rentabilidad_anualizada == pytest.approx(
        (1 + media) ** DIAS_COTIZACION_ANUAL - 1
    )
    assert serie_financiera.volatilidad_anualizada == pytest.approx(
        desviacion * np.sqrt(DIAS_COTIZACION_ANUAL)
    )


def test_rendimientos_simple_y_log(serie_financiera, serie_precios):
    simples = serie_financiera.rendimientos("simple")
    logaritmicos = serie_financiera.rendimientos("log")
    assert len(simples) == len(serie_precios) - 1
    assert np.allclose(np.log(1 + simples), logaritmicos)
    with pytest.raises(ValueError):
        serie_financiera.rendimientos("otro")


def test_resumen(serie_financiera):
    resumen = serie_financiera.resumen()
    assert resumen["activo"] == "AAA"
    assert resumen["moneda"] == "USD"
    assert resumen["proveedor"] == "Sintético"
    assert resumen["volatilidad_anualizada"] == serie_financiera.volatilidad_anualizada


def test_es_inmutable_y_no_modifica_los_metadatos(serie_precios):
    metadatos = {"nombre": "AAA"}
    serie = FinancialSeries(serie_precios, metadatos)
    assert metadatos == {"nombre": "AAA"}
    with pytest.raises(dataclasses.FrozenInstanceError):
        serie.media = 0.0


def test_copia_la_serie(serie_precios):
    serie = FinancialSeries(serie_precios)
    original = serie.serie_temporal.iloc[0]
    serie_precios.iloc[0] = 1.0
    assert serie.serie_temporal.iloc[0] == original


def test_indice(serie_precios):
    serie = FinancialSeries(serie_precios, tipo_activo=TipoActivo.INDICE)
    assert serie.tipo == "índice"


# ---------- Validación ----------


def test_rechaza_indice_no_temporal(serie_precios):
    with pytest.raises(DataValidationError):
        FinancialSeries(serie_precios.reset_index(drop=True))


def test_rechaza_fechas_duplicadas(serie_precios):
    duplicada = pd.concat([serie_precios, serie_precios.iloc[-1:]])
    with pytest.raises(DataValidationError):
        FinancialSeries(duplicada)


def test_rechaza_fechas_desordenadas(serie_precios):
    with pytest.raises(DataValidationError):
        FinancialSeries(serie_precios.iloc[::-1])


@pytest.mark.parametrize("valor", [0.0, -1.0, np.nan, np.inf])
def test_rechaza_precios_no_validos(serie_precios, valor):
    serie = serie_precios.copy()
    serie.iloc[10] = valor
    with pytest.raises(DataValidationError):
        FinancialSeries(serie)


def test_rechaza_valores_no_numericos(serie_precios):
    texto = serie_precios.astype(str)
    with pytest.raises(DataValidationError):
        FinancialSeries(texto)


def test_rechaza_dataframe(precios_sinteticos):
    with pytest.raises(DataValidationError):
        FinancialSeries(precios_sinteticos)


def test_rechaza_series_cortas(serie_precios):
    with pytest.raises(InsufficientDataError):
        FinancialSeries(serie_precios.iloc[: MIN_OBSERVACIONES - 1])


def test_insufficient_data_es_un_error_de_validacion():
    assert issubclass(InsufficientDataError, DataValidationError)


# ---------- MacroSeries ----------


def test_macro_series_estadisticos_del_nivel():
    fechas = pd.date_range("2024-01-01", periods=12, freq="MS")
    tipos = pd.Series(np.linspace(-0.5, 5.0, 12), index=fechas, name="TIPO")
    macro = MacroSeries(tipos, {"nombre": "Tipo de interés"}, unidad="%", proveedor="Sintético")
    assert macro.nombre == "Tipo de interés"
    assert macro.media == pytest.approx(tipos.mean())
    assert macro.desviacion_tipica == pytest.approx(tipos.std())
    assert macro.ultimo_valor == pytest.approx(5.0)
    assert macro.resumen()["unidad"] == "%"


def test_macro_series_valida_el_indice():
    with pytest.raises(DataValidationError):
        MacroSeries(pd.Series([1.0, 2.0, 3.0]))


# ---------- Fundamentales ----------


def test_fundamentales_campos_opcionales():
    fundamentales = Fundamentales("AAA", roe=0.15)
    assert fundamentales.roe == 0.15
    assert fundamentales.per is None
    assert fundamentales.fecha_ejercicio is None
