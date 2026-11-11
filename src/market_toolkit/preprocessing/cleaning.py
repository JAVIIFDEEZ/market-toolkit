from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
import pandas as pd
import yfinance

import market_toolkit.models.series as series

# Monedas que Yahoo Finance da en centésimas: {subunidad: (moneda principal, valor en esa moneda)}
SUBUNIDADES_MONEDA = {
    "GBp": ("GBP", 0.01),
    "GBX": ("GBP", 0.01),
    "ZAc": ("ZAR", 0.01),
    "ILA": ("ILS", 0.01),
}


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
        # Se rellenan SOLO los activos con datos mensuales o más distanciados
        siguiente_dato = pd.DataFrame(
            {
                col: df.index.to_series().where(df[col].notna()).bfill()
                for col in df.columns
            },
            index=df.index
        )
        distancia = siguiente_dato.sub(df.index, axis=0)
        mascara = distancia <= pd.Timedelta(days=27)
        columnas = mascara.columns[distancia.median() > pd.Timedelta(days=10)]
        df.loc[:, columnas] = df[columnas].ffill(limit=7)
        # Eliminar las filas (días) a las que le faltan algun dato
        df = df.dropna(axis=0, how="any")
        # Determinar si al alguna serie mensual
        if len(columnas) >= 1:
            # Nos quedamos con la primera fecha del mes en la que todos los activos tienen datos
            df = df.groupby(df.index.to_period("M")).first()
            df.index = df.index.to_timestamp()
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
        series: Sequence[series.SerieTemporal],
        permitir_negativos: bool = False,
        alineacion_temporal: Literal["relleno", "eliminacion"] | None = None
) -> pd.DataFrame:
    """
    Función para juntar las rentabilidades de series temporales con gestión de la alineación
    temporal.
    :param series: Lista de series temporales a juntar.
    :param permitir_negativos: `True` para conservar los valores negativos, que son válidos en
        series macroeconómicas (tipos de interés, spreads, variaciones...).
    :param alineacion_temporal: Establece cómo tratar los valores nulos causados por la alineación
        temporal de los activos. `None` si no se desea hacer nada, `"relleno"` para reemplazarlos
        por los valores anteriores y `"eliminacion"` para eliminar esas fechas del dataframe.
    :return: Dataframe con los datos juntos, limpios y alineados temporalmente.
    """
    df_series = pd.concat([serie.serie_temporal for serie in series], axis=1)
    df_series = limpiar_dataframe(df_series, permitir_negativos, alineacion_temporal)

    # Pasar moneda a USD
    monedas_activos = pd.Series({
        # Si es MacroSerie, simulamos moneda USD que mantiene la serie temporal invariante
        serie.serie_temporal.name: getattr(serie, "moneda", "USD")
        for serie in series
    })
    # Cada moneda se cambia desde su moneda principal, ajustando la escala de las subunidades
    conversiones = {
        moneda: SUBUNIDADES_MONEDA.get(moneda, (moneda, 1.0))
        for moneda in set(monedas_activos.unique()) - {"USD"}
    }
    tickers_fx = sorted({f"{principal}USD=X" for principal, _ in conversiones.values()})
    if tickers_fx:
        datos_fx = yfinance.download(
            tickers=tickers_fx,
            start=df_series.index.min() - pd.Timedelta(days=7),
            end=df_series.index.max() + pd.Timedelta(days=1),
            progress=False,
        )
        df_fx = datos_fx["Close"]
        if isinstance(df_fx, pd.Series):
            df_fx = df_fx.to_frame(name=tickers_fx[0])
        df_fx.index = df_fx.index.tz_localize(None).normalize()
        # Los días sin tipo de cambio usan el último conocido, también si la fecha viene vacía
        df_fx = df_fx.reindex(columns=tickers_fx).sort_index().ffill()
        df_fx = df_fx.reindex(df_series.index, method="ffill")
        factores = pd.DataFrame(
            {
                activo: (
                    df_fx[f"{conversiones[moneda][0]}USD=X"] * conversiones[moneda][1]
                    if moneda != "USD"
                    else 1.0
                )
                for activo, moneda in monedas_activos.items()
            },
            index=df_series.index,
        )
        mascara = factores.notna().all(axis=1)
        df_series = df_series.loc[mascara]
        factores = factores.loc[mascara]
        df_series *= factores
    return df_series