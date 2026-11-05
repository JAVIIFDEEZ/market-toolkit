from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from market_toolkit.models import FinancialSeries


def limpiar_datos(
    datos: pd.DataFrame | pd.Series,
    permitir_negativos: bool = False,
    alineacion_temporal: Literal["relleno", "eliminacion"] | None = None
) -> pd.DataFrame | pd.Series:
    """
    Función para la limpieza de datos, tanto de series como de dataframes. Tratamiento de fechas
    duplicadas, valores nulos o no válidos y gestión de la alineación temporal.
    :param datos:Datos historicos a limpiar.
    :param permitir_negativos: `True` para conservar los valores negativos, que son válidos en
        series macroeconómicas (tipos de interés, spreads, variaciones...).
    :param alineacion_temporal: Establece cómo tratar los valores nulos causados por la
        alineación temporal de los activos para los DataFrames. `None` si no se desea hacer nada,
        `"relleno"` para reemplazarlos por los valores anteriores y
        `"eliminacion"` para eliminar esas fechas del dataframe.
    :return: Datos limpios.
    """
    if isinstance(datos, pd.DataFrame):
        return limpiar_dataframe(datos, permitir_negativos, alineacion_temporal)
    return limpiar_serie(datos, permitir_negativos)


def limpiar_dataframe(
    df: pd.DataFrame,
    permitir_negativos: bool = False,
    alineacion_temporal: Literal["relleno", "eliminacion"] | None = None
) -> pd.DataFrame:
    """
    Función para la limpieza de datos en DataFrames. Tratamiento de fechas duplicadas,
    valores nulos o no válidos y gestión de la alineación temporal.
    :param df: Dataframe con los datos históricos a limpiar.
    :param permitir_negativos: `True` para conservar los valores negativos, que son válidos en
        series macroeconómicas (tipos de interés, spreads, variaciones...).
    :param alineacion_temporal: Establece cómo tratar los valores nulos causados por la alineación
        temporal de los activos. `None` si no se desea hacer nada, `"relleno"` para reemplazarlos
        por los valores anteriores y `"eliminacion"` para eliminar esas fechas del dataframe.
    :return: Dataframe con los datos limpios.
    """
    df = df.sort_index()  # Ordenar de forma cronológica
    df = df.loc[~df.index.duplicated(keep="last")]  # Eliminar fechas duplicadas
    df = df.replace([np.inf, -np.inf], np.nan)  # Reemplazar valores infinitos por NaN
    if not permitir_negativos:
        df = df.where(df >= 0, np.nan)  # Reemplazar valores negativos por NaN
    # Eliminar las columnas (activos) que no tienen nigún dato
    df = df.dropna(axis=1, how="all")
    # Eliminar las filas (días) que no tienen nigun dato
    df = df.dropna(axis=0, how="all")
    if alineacion_temporal == "relleno":
        df = df.ffill()  # Rellenar con datos del día anterior
        # Si la diferencia es al inicio se toma como primer dia el del ultimo activo disponible
        df = df.dropna(axis=0, how="any")
    elif alineacion_temporal == "eliminacion":
        # Eliminar las filas (días) a las que le faltan algun dato
        df = df.dropna(axis=0, how="any")
    return df

def limpiar_serie(serie: pd.Series, permitir_negativos: bool = False) -> pd.Series:
    """
    Función para la limpieza de datos en Series. Tratamiento de fechas duplicadas,
    valores nulos o no válidos.
    :param serie: Serie con los datos historicos a limpiar.
    :param permitir_negativos: `True` para conservar los valores negativos, que son válidos en
        series macroeconómicas (tipos de interés, spreads, variaciones...).
    :return: Serie con los datos limpios.
    """
    serie = serie.sort_index()  # Ordenar de forma cronológica
    serie = serie.loc[~serie.index.duplicated(keep="last")]  # Eliminar fechas duplicadas
    serie = serie.replace([np.inf, -np.inf], np.nan)  # Reemplazar valores infinitos por NaN
    if not permitir_negativos:
        serie = serie.where(serie >= 0, np.nan)  # Reemplazar valores negativos por NaN
    serie = serie.dropna() # Eliminar las fechas sin datos
    return serie

def juntar_series(
        series: Sequence[FinancialSeries],
        permitir_negativos: bool = False,
        alineacion_temporal: Literal["relleno", "eliminacion"] | None = None
) -> pd.DataFrame:
    """
    Función para juntar series temporales con gestión de la alineación temporal.
    :param series: Lista de series temporales a juntar.
    :param permitir_negativos: `True` para conservar los valores negativos, que son válidos en
        series macroeconómicas (tipos de interés, spreads, variaciones...).
    :param alineacion_temporal: Establece cómo tratar los valores nulos causados por la alineación
        temporal de los activos. `None` si no se desea hacer nada, `"relleno"` para reemplazarlos
        por los valores anteriores y `"eliminacion"` para eliminar esas fechas del dataframe.
    :return: Dataframe con los datos juntos, limpios y alineados temporalmente.
    """
    df_series = pd.concat([serie.serie_temporal for serie in series], axis=1)
    return limpiar_dataframe(df_series, permitir_negativos, alineacion_temporal)


