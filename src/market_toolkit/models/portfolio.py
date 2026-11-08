from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd

import market_toolkit.models.montecarlo as montecarlo
from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.exceptions import InsufficientDataError
from market_toolkit.preprocessing import juntar_series

if TYPE_CHECKING:
    from market_toolkit.models.series import FinancialSeries


class Portfolio:
    """
    Clase que modela una cartera de inversión.
    """
    TOLERANCIA_PESOS = 1e-6  # Margen para considerar que los pesos de una fecha suman 1

    activos: pd.DataFrame
    pesos: pd.DataFrame
    metadatos_activos: pd.DataFrame
    metadatos: dict
    rentabilidad_media: float
    desviacion_tipica: float
    rentabilidad_anualizada: float
    volatilidad_anualizada: float

    def __init__(self, activos: Sequence[FinancialSeries], pesos: pd.DataFrame, *,
                 alineacion_temporal: Literal["relleno", "eliminacion"] = "eliminacion"):
        """
        Inicializa un objeto de Portfolio.
        :param activos: Lista con las series temporales que forman la cartera.
        :param pesos: DataFrame con los pesos de cada uno de los activos de la cartera.
            Debe tener un índice temporal y cada fila se corresponde con los pesos del día
            correspondiente. Si el índice no es diario, cada fila indica los pesos en la ventana
            temporal que empieza en esa fecha y termina en la fecha de la próxima fila.
        :param alineacion_temporal: Establece cómo tratar las fechas en las que no cotizan todos
            los activos. `"eliminacion"` (por defecto) elimina esas fechas y `"relleno"` usa el
            último precio conocido de cada activo.
        """
        # Juntar activos
        self.activos = juntar_series(activos, True, alineacion_temporal)
        # Validar pesos
        if not isinstance(pesos.index, pd.DatetimeIndex):
            raise ValueError("El índice de los pesos debe ser un DatetimeIndex.")
        # Cada peso se empareja con su activo por nombre, no por posición
        faltan = sorted(set(self.activos.columns) - set(pesos.columns))
        sobran = sorted(set(pesos.columns) - set(self.activos.columns))
        if faltan or sobran:
            raise ValueError(
                f"Las columnas de los pesos deben ser los activos de la cartera. "
                f"Faltan: {faltan or 'ninguno'}. Sobran: {sobran or 'ninguno'}.")
        pesos = pesos[list(self.activos.columns)].sort_index()  # Mismo orden que los activos
        pesos = pesos.dropna()  # Nos quedamos SOLO cuando todos los pesos son validos.
        if pesos.empty:
            raise ValueError("No se han proporcionado pesos válidos.")
        sumas = pesos.sum(axis=1)
        incorrectas = sumas[(sumas - 1).abs() > self.TOLERANCIA_PESOS]
        if not incorrectas.empty:
            raise ValueError(
                f"Los pesos de cada fecha deben sumar 1. El {incorrectas.index[0].date()} "
                f"suman {incorrectas.iloc[0]:.4f}.")
        # Pesos de los activos. Cada fila se mantiene hasta el siguiente cambio: se añaden las
        # fechas de los activos desde el primer peso para que unos pesos fijos (una sola fila)
        # se extiendan a todo el periodo de la cartera
        fechas_activos = self.activos.index[self.activos.index >= pesos.index[0]]
        self.pesos = pesos.reindex(pesos.index.union(fechas_activos)).ffill()
        # Ajuste temporal entre los pesos y los activos
        if self.pesos.index[0] < self.activos.index[0]:
            warnings.warn(
                "Hay pesos configurados para antes de la existencia de algunos activos. "
                "Se truncan para que el día de inicio coincida con el de los activos.",
                UserWarning,
                stacklevel=2,
            )
            self.pesos = self.pesos[self.activos.index[0]:]
        elif self.pesos.index[0] > self.activos.index[0]:
            warnings.warn(
                "Hay activos configurados para antes de la existencia de los pesos. "
                "Se truncan para que el día de inicio coincida con el de los pesos.",
                UserWarning,
                stacklevel=2,
            )
            self.activos = self.activos[self.pesos.index[0]:]
        if self.pesos.index[-1] > self.activos.index[-1]:
            warnings.warn(
                "Hay pesos configurados para después de la existencia de los activos. "
                "Se truncan para que el día de fin coincida con el de los activos.",
                UserWarning,
                stacklevel=2,
            )
            self.pesos = self.pesos[:self.activos.index[-1]]
        elif self.pesos.index[-1] < self.activos.index[-1]:
            self.pesos = self.pesos.reindex(self.activos.index).ffill()
        # Informacion de cada activo, sobre las fechas definitivas de la cartera
        self.metadatos_activos = self._calcular_metadatos_activos(activos)
        self.metadatos_activos.columns.name = None
        self.metadatos_activos.index.name = "Información"
        # Metadatos de los activos
        self.metadatos ={activo.activo: activo.metadatos for activo in activos}
        # Calcular estadisticos
        self._calcular_estadisticos()

    def _calcular_metadatos_activos(self, activos: Sequence[FinancialSeries]) -> pd.DataFrame:
        """
        Recalcula los metadatos de los activos que forman la cartera tras la alineacion temporal.
        :param activos: Lista de series temporales de la cartera.
        :return: DataFrame en el que cada columna es un activo y cada fila un metadato
        """
        info = pd.DataFrame(
            [activo.resumen() for activo in activos]
        ).set_index("activo").T
        rentabilidades = self.activos.pct_change()
        medias = rentabilidades.mean()
        desviaciones = rentabilidades.std()
        rentabilidades_anual = (1 + medias) ** DIAS_COTIZACION_ANUAL - 1
        volatilidades_anual = desviaciones * np.sqrt(DIAS_COTIZACION_ANUAL)
        info.loc["moneda"] = "USD"
        info.loc["inicio"] = self.activos.index[0].date()
        info.loc["fin"] = self.activos.index[-1].date()
        info.loc["observaciones"] = len(self.activos)
        info.loc["media_diaria"] = medias
        info.loc["desviacion_tipica_diaria"] = desviaciones
        info.loc["rentabilidad_anualizada"] = rentabilidades_anual
        info.loc["volatilidad_anualizada"] = volatilidades_anual
        return info

    def _calcular_estadisticos(self):
        """
        Determina distintos estadísticos de la cartera, como la rentabilidad media diaria, la
        volatilidad, la rentabilidad media anualizada y la volatilidad anualizada.
        """
        # Rendimiento de la cartera: rendimiento de cada activo por el peso que tenía el capital
        # en él al cierre de la sesión anterior
        rendimientos_activos = self.activos.pct_change(fill_method=None)
        pesos = self.pesos.reindex(self.activos.index).ffill().shift(1)
        rendimientos = (rendimientos_activos * pesos).dropna().sum(axis=1)
        if len(rendimientos) < 2:
            raise InsufficientDataError(
                "La cartera no tiene suficientes fechas con precios de sus activos para "
                "calcular sus estadísticos.")
        self.rentabilidad_media = float(rendimientos.mean())
        self.desviacion_tipica = float(rendimientos.std())
        self.rentabilidad_anualizada = (1 + self.rentabilidad_media) ** DIAS_COTIZACION_ANUAL - 1
        self.volatilidad_anualizada = self.desviacion_tipica * np.sqrt(DIAS_COTIZACION_ANUAL)

    def resumen(self) -> dict:
        """
        Devuelve la información principal de la cartera y sus estadísticos.
        :return: Diccionario con los activos, los pesos actuales y los estadísticos de la cartera.
        """
        return {
            "activos": list(self.activos.columns),
            "pesos_actuales": self.pesos.iloc[-1].to_dict(),
            "moneda": "USD",
            "inicio": self.activos.index[0].date(),
            "fin": self.activos.index[-1].date(),
            "observaciones": len(self.activos),
            "media_diaria": self.rentabilidad_media,
            "desviacion_tipica_diaria": self.desviacion_tipica,
            "rentabilidad_anualizada": self.rentabilidad_anualizada,
            "volatilidad_anualizada": self.volatilidad_anualizada,
        }

    def simulacion_monte_carlo(self, n_simulaciones: int = 1000,
             horizonte: int = DIAS_COTIZACION_ANUAL,
             rentabilidad: float | int | Mapping[str, float | int] | None = None,
             volatilidad: float | int | Mapping[str, float | int] | None = None,
             valor_inicial: float | int | None = None,
             rebalanceo: bool = True,
             semilla: int | None = None,
             guardar_graficos: bool = True) -> montecarlo.MonteCarlo:
        """
        Realiza el algoritmo de simulación de montecarlo sobre la cartera.
        :param n_simulaciones: Número de trayectorias (iteraciones) a simular.
        :param horizonte: Número de sesiones bursátiles a simular (252 = un año).
        :param rentabilidad: Rentabilidad anual esperada en tanto por uno (0.07 = 7 %). Si es
            `None` se usa la histórica. En una cartera puede ser un número (el mismo para todos
            los activos) o un diccionario {activo: rentabilidad} para cambiar solo algunos.
        :param volatilidad: Volatilidad anual en tanto por uno (0.20 = 20 %). Mismas opciones que
            `rentabilidad`.
        :param valor_inicial: Valor de partida. Por defecto, el último precio del activo o 100
            para una cartera.
        :param rebalanceo: Solo para carteras. `True` para mantener los pesos constantes cada
            día (rebalanceo diario) y `False` para comprar al inicio y no tocar la cartera.
        :param semilla: Semilla del generador aleatorio, para obtener resultados reproducibles.
        :param guardar_graficos: `True` para borrar los gráficos de la simulación anterior y
            guardar los de esta en `models/graficos/` (trayectorias.png y distribucion.png).
        :return: El objeto MonteCarlo con los resultados de la simulación.
        """
        sim = montecarlo.MonteCarlo(self,
                                    n_simulaciones=n_simulaciones,
                                    horizonte=horizonte,
                                    rentabilidad=rentabilidad,
                                    volatilidad=volatilidad,
                                    valor_inicial=valor_inicial,
                                    rebalanceo=rebalanceo,
                                    semilla=semilla,
                                    guardar_graficos=guardar_graficos
        )
        sim.graficar()
        return sim