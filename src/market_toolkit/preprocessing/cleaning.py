from typing import Literal

import numpy as np
import pandas as pd


def limpiar_datos(
    datos: pd.DataFrame, alineacion_temporal: Literal["relleno", "eliminacion"] | None = None
) -> pd.DataFrame:
    """
    Función para la limpieza de datos. Tratamiento de fechas duplicadas, valores nulos o no
    válidos y gestión de la alineación temporal.
    :param datos: Dataframe con los datos históricos a limpiar.
    :param alineacion_temporal: Establece cómo tratar los valores nulos causados por la alineación
    temporal de los activos. `None` si no se desea hacer nada, `"relleno"` para reemplazarlos por
    los valores anteriores y `"eliminacion"` para eliminar esas fechas del dataframe.
    :return: Dataframe con los datos limpios.
    """
    datos = datos.sort_index()  # Ordenar de forma cronológica
    datos = datos.loc[~datos.index.duplicated(keep="last")]  # Eliminar fechas duplicadas
    datos = datos.replace([np.inf, -np.inf], np.nan)  # Reemplazar valores infinitos por NaN
    datos = datos.where(datos >= 0, np.nan)  # Reemplazar valores negativos por NaN
    # Eliminar las columnas (activos) que no tienen nigún dato
    datos = datos.dropna(axis=1, how="all")
    # Eliminar las filas (días) que no tienen nigun dato
    datos = datos.dropna(axis=0, how="all")
    if alineacion_temporal == "relleno":
        datos = datos.ffill()  # Rellenar con datos del día anterior
        # Si la diferencia es al inicio se rellena con los datos del dia de apertura
        datos = datos.bfill()
    elif alineacion_temporal == "eliminacion":
        # Eliminar las filas (días) a las que le faltan algun dato
        datos = datos.dropna(axis=0, how="any")
    return datos
