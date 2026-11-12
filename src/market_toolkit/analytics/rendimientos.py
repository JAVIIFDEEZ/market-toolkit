"""
Cálculos básicos sobre rendimientos y valores, comunes a las series, la cartera, los gráficos y la
interfaz web. Están en un solo sitio para que todos usen exactamente la misma fórmula.
"""

import numpy as np
import pandas as pd

from market_toolkit.config import DIAS_COTIZACION_ANUAL


def rentabilidad_anualizada(media_diaria):
    """
    Rentabilidad anual compuesta a partir de la rentabilidad media diaria: (1 + media)^252 - 1.
    :param media_diaria: Un número o una Series (un valor por activo).
    """
    return (1 + media_diaria) ** DIAS_COTIZACION_ANUAL - 1


def volatilidad_anualizada(desviacion_diaria):
    """
    Volatilidad anual por la regla de la raíz del tiempo: desviación diaria por la raíz de 252.
    :param desviacion_diaria: Un número o una Series (un valor por activo).
    """
    return desviacion_diaria * np.sqrt(DIAS_COTIZACION_ANUAL)


def ratio_sharpe(rendimientos: pd.Series, tasa_libre_riesgo: float = 0.0) -> float:
    """
    Ratio de Sharpe anualizado a partir de los rendimientos diarios.
    :param rendimientos: Rendimientos diarios simples.
    :param tasa_libre_riesgo: Tasa anual en tanto por uno.
    """
    exceso_diario = rendimientos - tasa_libre_riesgo / DIAS_COTIZACION_ANUAL
    return float(exceso_diario.mean() / rendimientos.std() * np.sqrt(DIAS_COTIZACION_ANUAL))


def caidas(valores: pd.Series) -> pd.Series:
    """Caída desde el máximo anterior en cada fecha: 0 en los máximos y negativa en las caídas."""
    return valores / valores.cummax() - 1


def drawdown_maximo(valores: pd.Series) -> float:
    """Mayor caída desde un máximo anterior, en tanto por uno y en positivo (0.2 = 20 %)."""
    return float(-caidas(valores.dropna()).min())


def base_100(precios):
    """
    Pasa precios a base 100 desde el primer precio conocido de cada serie.
    :param precios: Una Series o un DataFrame (una columna por serie).
    """
    return precios / precios.bfill().iloc[0] * 100
