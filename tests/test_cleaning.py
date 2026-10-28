import numpy as np
import pandas as pd

from market_toolkit.preprocessing import limpiar_datos


def test_ordena_y_elimina_duplicados(precios_sinteticos):
    desordenados = pd.concat([precios_sinteticos.iloc[::-1], precios_sinteticos.iloc[:3]])
    limpios = limpiar_datos(desordenados)
    assert limpios.index.is_monotonic_increasing
    assert not limpios.index.duplicated().any()
    assert len(limpios) == len(precios_sinteticos)


def test_inf_y_negativos_pasan_a_nan(precios_sinteticos):
    sucios = precios_sinteticos.copy()
    sucios.iloc[0, 0] = np.inf
    sucios.iloc[1, 1] = -5.0
    limpios = limpiar_datos(sucios)
    assert np.isnan(limpios.iloc[0, 0])
    assert np.isnan(limpios.iloc[1, 1])


def test_alineacion_relleno(precios_calendarios_distintos):
    limpios = limpiar_datos(precios_calendarios_distintos, "relleno")
    assert not limpios.isna().any().any()
    assert len(limpios) == len(precios_calendarios_distintos)


def test_alineacion_eliminacion(precios_calendarios_distintos):
    limpios = limpiar_datos(precios_calendarios_distintos, "eliminacion")
    assert not limpios.isna().any().any()
    assert len(limpios) == len(precios_calendarios_distintos) - 3 - 5 - 1


def test_sin_alineacion_conserva_nan(precios_calendarios_distintos):
    limpios = limpiar_datos(precios_calendarios_distintos)
    assert limpios.isna().sum().sum() == 3 + 5 + 1
