"""Funciones de análisis puras: no dependen de los proveedores ni de los modelos."""

from .benchmark import (
    alfa_jensen,
    alinear_rendimientos,
    beta,
    information_ratio,
    metricas_benchmark,
    tracking_error,
)
from .distribuciones import grados_libertad_t
from .rendimientos import (
    base_100,
    caidas,
    drawdown_maximo,
    ratio_sharpe,
    rentabilidad_anualizada,
    volatilidad_anualizada,
)

__all__ = [
    "alinear_rendimientos",
    "beta",
    "alfa_jensen",
    "tracking_error",
    "information_ratio",
    "metricas_benchmark",
    "grados_libertad_t",
    "rentabilidad_anualizada",
    "volatilidad_anualizada",
    "ratio_sharpe",
    "caidas",
    "drawdown_maximo",
    "base_100",
]
