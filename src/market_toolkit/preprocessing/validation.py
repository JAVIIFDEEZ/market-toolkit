"""
Validación estricta de las series temporales que reciben los modelos.

Estas funciones no corrigen los datos, solo comprueban que son válidos. La limpieza
(`limpiar_datos`) es responsabilidad previa de los proveedores.
"""

import pandas as pd

from market_toolkit.config import MIN_OBSERVACIONES
from market_toolkit.exceptions import DataValidationError, InsufficientDataError


def validar_indice_temporal(serie: pd.Series) -> None:
    """
    Comprueba que la serie tiene un índice de fechas ordenado y sin duplicados.
    :param serie: La serie a comprobar.
    """
    if not isinstance(serie, pd.Series):
        raise DataValidationError(f"Se esperaba un pd.Series y se ha recibido {type(serie)}.")
    if not isinstance(serie.index, pd.DatetimeIndex):
        raise DataValidationError("El índice de la serie debe ser un DatetimeIndex.")
    if serie.index.has_duplicates:
        raise DataValidationError("La serie tiene fechas duplicadas.")
    if not serie.index.is_monotonic_increasing:
        raise DataValidationError("Las fechas de la serie no están ordenadas cronológicamente.")


def validar_valores_numericos(serie: pd.Series) -> None:
    """
    Comprueba que todos los valores de la serie son números válidos (sin NaN ni infinitos).
    :param serie: La serie a comprobar.
    """
    if pd.api.types.is_bool_dtype(serie) or not pd.api.types.is_numeric_dtype(serie):
        raise DataValidationError(f"La serie debe ser numérica y es de tipo {serie.dtype}.")
    if serie.isna().any():
        raise DataValidationError("La serie tiene valores nulos (NaN).")
    infinitos = serie.isin([float("inf"), float("-inf")])
    if infinitos.any():
        raise DataValidationError("La serie tiene valores infinitos.")


def validar_precios_positivos(serie: pd.Series) -> None:
    """
    Comprueba que todos los precios de la serie son estrictamente positivos.
    :param serie: La serie de precios a comprobar.
    """
    if (serie <= 0).any():
        raise DataValidationError("La serie tiene precios menores o iguales que 0.")


def validar_longitud(serie: pd.Series, minimo: int = MIN_OBSERVACIONES) -> None:
    """
    Comprueba que la serie tiene suficientes observaciones.
    :param serie: La serie a comprobar.
    :param minimo: Número mínimo de observaciones exigido.
    """
    if len(serie) < minimo:
        raise InsufficientDataError(
            f"La serie tiene {len(serie)} observaciones y se necesitan al menos {minimo}."
        )


def validar_serie_precios(serie: pd.Series, minimo: int = MIN_OBSERVACIONES) -> None:
    """
    Aplica todas las comprobaciones que debe cumplir una serie de precios.
    :param serie: La serie de precios a comprobar.
    :param minimo: Número mínimo de observaciones exigido.
    """
    validar_indice_temporal(serie)
    validar_valores_numericos(serie)
    validar_precios_positivos(serie)
    validar_longitud(serie, minimo)


def validar_serie_macro(serie: pd.Series, minimo: int = 2) -> None:
    """
    Aplica las comprobaciones de una serie que no es de precios (por ejemplo, tipos de interés).
    Admite valores negativos o nulos y, por defecto, menos observaciones que una serie de precios
    porque muchas series macroeconómicas son mensuales o anuales.
    :param serie: La serie a comprobar.
    :param minimo: Número mínimo de observaciones exigido.
    """
    validar_indice_temporal(serie)
    validar_valores_numericos(serie)
    validar_longitud(serie, minimo)
