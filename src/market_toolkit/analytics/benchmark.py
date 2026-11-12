"""
Métricas de una cartera frente a un índice de referencia (benchmark).

Son funciones puras sobre rendimientos diarios: no dependen de los proveedores ni de los
modelos, así que se pueden usar con cualquier serie de rendimientos.
"""

import numpy as np
import pandas as pd

from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.exceptions import InsufficientDataError


def alinear_rendimientos(cartera: pd.Series, benchmark: pd.Series) -> pd.DataFrame:
    """
    Junta los rendimientos de la cartera y del benchmark en las fechas que tienen en común.
    :param cartera: Rendimientos diarios de la cartera.
    :param benchmark: Rendimientos diarios del benchmark.
    :return: DataFrame con las columnas `cartera` y `benchmark`.
    """
    juntos = pd.concat({"cartera": cartera, "benchmark": benchmark}, axis=1, sort=True).dropna()
    if len(juntos) < 2:
        raise InsufficientDataError(
            "La cartera y el índice de referencia no tienen suficientes fechas en común."
        )
    return juntos


def beta(cartera: pd.Series, benchmark: pd.Series) -> float:
    """
    Sensibilidad de la cartera a los movimientos del benchmark: covarianza / varianza.
    :return: Beta (1 = se mueve igual que el benchmark).
    """
    juntos = alinear_rendimientos(cartera, benchmark)
    varianza = juntos["benchmark"].var()
    if varianza == 0:
        return float("nan")
    return float(juntos["cartera"].cov(juntos["benchmark"]) / varianza)


def alfa_jensen(cartera: pd.Series, benchmark: pd.Series, tasa_libre_riesgo: float = 0.0) -> float:
    """
    Alfa de Jensen anualizada: rentabilidad de la cartera por encima de la que le corresponde
    según su beta (modelo CAPM).
    :param tasa_libre_riesgo: Tasa anual en tanto por uno.
    :return: Alfa anual en tanto por uno.
    """
    juntos = alinear_rendimientos(cartera, benchmark)
    libre_diaria = tasa_libre_riesgo / DIAS_COTIZACION_ANUAL
    exceso_cartera = juntos["cartera"].mean() - libre_diaria
    exceso_benchmark = juntos["benchmark"].mean() - libre_diaria
    alfa_diaria = exceso_cartera - beta(cartera, benchmark) * exceso_benchmark
    return float(alfa_diaria * DIAS_COTIZACION_ANUAL)


def tracking_error(cartera: pd.Series, benchmark: pd.Series) -> float:
    """
    Desviación típica anualizada de la diferencia de rendimientos con el benchmark.
    :return: Tracking error anual en tanto por uno.
    """
    juntos = alinear_rendimientos(cartera, benchmark)
    diferencia = juntos["cartera"] - juntos["benchmark"]
    return float(diferencia.std() * np.sqrt(DIAS_COTIZACION_ANUAL))


def information_ratio(cartera: pd.Series, benchmark: pd.Series) -> float:
    """
    Rentabilidad anual por encima del benchmark por cada unidad de tracking error.
    :return: Information ratio, o NaN si la cartera replica exactamente al benchmark.
    """
    juntos = alinear_rendimientos(cartera, benchmark)
    error = tracking_error(cartera, benchmark)
    if error == 0:
        return float("nan")
    exceso_anual = (juntos["cartera"] - juntos["benchmark"]).mean() * DIAS_COTIZACION_ANUAL
    return float(exceso_anual / error)


def metricas_benchmark(
    cartera: pd.Series, benchmark: pd.Series, tasa_libre_riesgo: float = 0.0
) -> dict[str, float | int]:
    """
    Calcula todas las métricas de la cartera frente al benchmark en sus fechas comunes.
    :param cartera: Rendimientos diarios de la cartera.
    :param benchmark: Rendimientos diarios del benchmark.
    :param tasa_libre_riesgo: Tasa anual en tanto por uno, para el alfa.
    :return: Diccionario con las rentabilidades acumuladas, beta, alfa, tracking error,
        information ratio, correlación y número de sesiones comunes.
    """
    juntos = alinear_rendimientos(cartera, benchmark)
    return {
        "sesiones_comunes": len(juntos),
        "rentabilidad_cartera": float((1 + juntos["cartera"]).prod() - 1),
        "rentabilidad_benchmark": float((1 + juntos["benchmark"]).prod() - 1),
        "beta": beta(cartera, benchmark),
        "alfa": alfa_jensen(cartera, benchmark, tasa_libre_riesgo),
        "tracking_error": tracking_error(cartera, benchmark),
        "information_ratio": information_ratio(cartera, benchmark),
        "correlacion": float(juntos["cartera"].corr(juntos["benchmark"])),
    }
