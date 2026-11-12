"""
Estimaciones sobre la forma de la distribución de los rendimientos, para la simulación.
"""

import numpy as np
import pandas as pd

GRADOS_LIBERTAD_MAXIMOS = 100.0  # Con más grados de libertad la t es prácticamente una normal


def grados_libertad_t(rendimientos: pd.Series | np.ndarray) -> float:
    """
    Estima los grados de libertad (ν) de una t de Student a partir de la curtosis de los
    rendimientos, por el método de los momentos: la curtosis en exceso de una t es 6 / (ν - 4),
    así que ν = 6 / curtosis + 4.

    Cuanto más bajo es ν, más gruesas son las colas (más probables las caídas extremas). Con una
    curtosis nula o negativa los rendimientos no tienen colas gruesas y se devuelve el máximo,
    que equivale en la práctica a una normal.
    :param rendimientos: Rendimientos diarios (simples o logarítmicos).
    :return: Grados de libertad, siempre mayores que 4 (la varianza y la curtosis son finitas).
    """
    curtosis = pd.Series(np.asarray(rendimientos, dtype=float)).dropna().kurt()
    if not np.isfinite(curtosis) or curtosis <= 0:
        return GRADOS_LIBERTAD_MAXIMOS
    return float(min(6 / curtosis + 4, GRADOS_LIBERTAD_MAXIMOS))
