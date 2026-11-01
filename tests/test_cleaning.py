import numpy as np
import pandas as pd

from market_toolkit.preprocessing import limpiar_dataframe, limpiar_serie, limpiar_datos


def test_conserva_tipo(serie_precios, precios_sinteticos):
    assert isinstance(limpiar_datos(serie_precios), pd.Series)
    assert isinstance(limpiar_datos(precios_sinteticos), pd.DataFrame)


def test_limpiar_serie_ordena_y_elimina_duplicados(serie_precios):
    sucia = pd.concat([serie_precios.iloc[::-1], serie_precios.iloc[:3]])
    limpia = limpiar_serie(sucia)
    assert limpia.index.is_monotonic_increasing
    assert not limpia.index.duplicated().any()
    assert len(limpia) == len(serie_precios)


def test_limpiar_dataframe_ordena_y_elimina_duplicados(precios_sinteticos):
    sucio = pd.concat([precios_sinteticos.iloc[::-1], precios_sinteticos.iloc[:3]])
    limpio = limpiar_dataframe(sucio)
    assert limpio.index.is_monotonic_increasing
    assert not limpio.index.duplicated().any()
    assert len(limpio) == len(precios_sinteticos)


def test_limpiar_serie_elimina_infinitos_negativos_y_nulos(serie_precios):
    sucia = serie_precios.copy()
    sucia.iloc[0] = np.inf
    sucia.iloc[1] = -5.0
    sucia.iloc[2] = np.nan
    limpia = limpiar_serie(sucia)
    assert len(limpia) == len(serie_precios) - 3
    assert np.isfinite(limpia).all()
    assert (limpia >= 0).all()


def test_limpiar_dataframe_convierte_infinitos_y_negativos_en_nan(precios_sinteticos):
    sucio = precios_sinteticos.copy()
    sucio.iloc[0, 0] = np.inf
    sucio.iloc[1, 1] = -5.0
    limpio = limpiar_dataframe(sucio)
    assert pd.isna(limpio.iloc[0, 0])
    assert pd.isna(limpio.iloc[1, 1])


def test_limpiar_dataframe_elimina_filas_y_columnas_vacias(precios_sinteticos):
    sucio = precios_sinteticos.copy()
    sucio["VACIA"] = np.nan
    sucio.loc[sucio.index[0], :] = np.nan
    limpio = limpiar_dataframe(sucio)
    assert "VACIA" not in limpio.columns
    assert sucio.index[0] not in limpio.index
    assert limpio.notna().any(axis=1).all()
    assert limpio.notna().any(axis=0).all()


def test_limpiar_dataframe_rellena_nulos_de_alineacion(precios_calendarios_distintos):
    limpio = limpiar_dataframe(precios_calendarios_distintos, "relleno")
    assert not limpio.isna().any().any()
    assert len(limpio) == len(precios_calendarios_distintos)


def test_limpiar_dataframe_elimina_filas_con_nulos_de_alineacion(precios_calendarios_distintos):
    limpio = limpiar_dataframe(precios_calendarios_distintos, "eliminacion")
    assert not limpio.isna().any().any()
    assert len(limpio) == len(precios_calendarios_distintos) - 3 - 5 - 1


def test_limpiar_dataframe_sin_alineacion_conserva_nulos(precios_calendarios_distintos):
    limpio = limpiar_dataframe(precios_calendarios_distintos)
    assert limpio.isna().sum().sum() == 3 + 5 + 1
