from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd

from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.preprocessing.validation import validar_serie_macro, validar_serie_precios


class TipoActivo(Enum):
    """Tipos de activo que puede representar una `FinancialSeries`."""

    ACCION = "acción"
    INDICE = "índice"


@dataclass(frozen=True, eq=False)
class SerieTemporal:
    """
    Clase base de las series temporales del paquete. Es inmutable: los campos derivados se
    calculan una sola vez al crear el objeto.
    :param serie_temporal: Serie de pandas con un índice de fechas.
    :param metadatos: Información adicional de la serie (por ejemplo, su nombre).
    """

    serie_temporal: pd.Series = field(repr=False)
    metadatos: dict = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        # Se guardan copias para que los cambios externos no afecten al objeto
        object.__setattr__(self, "serie_temporal", self.serie_temporal.copy())
        object.__setattr__(self, "metadatos", dict(self.metadatos))
        self._validar()
        self._calcular_estadisticos()

    def _validar(self) -> None:
        """Comprueba que la serie es válida. Lanza `DataValidationError` si no lo es."""
        validar_serie_macro(self.serie_temporal)

    def _calcular_estadisticos(self) -> None:
        """Calcula los estadísticos de la serie. Cada subclase define los suyos."""

    @property
    def nombre(self) -> str:
        return self.metadatos.get("nombre", str(self.serie_temporal.name))

    @property
    def inicio(self) -> date:
        return self.serie_temporal.index.min().date()

    @property
    def fin(self) -> date:
        return self.serie_temporal.index.max().date()

    @property
    def duracion(self) -> int:
        return (self.fin - self.inicio).days

    @property
    def observaciones(self) -> int:
        return len(self.serie_temporal)


@dataclass(frozen=True, eq=False)
class FinancialSeries(SerieTemporal):
    """
    Serie de precios de un activo (acción o índice). Al crearla se valida la serie y se calculan
    automáticamente los estadísticos de sus rendimientos diarios.
    :param serie_temporal: Serie de precios con un índice de fechas.
    :param metadatos: Información adicional de la serie (por ejemplo, su nombre).
    :param tipo_activo: Si la serie es de una acción o de un índice.
    :param moneda: Moneda en la que cotiza el activo.
    :param proveedor: Fuente de la que se han obtenido los datos.
    """

    tipo_activo: TipoActivo = TipoActivo.ACCION
    moneda: str | None = None
    proveedor: str | None = None
    media: float = field(init=False)
    desviacion_tipica: float = field(init=False)
    rentabilidad_anualizada: float = field(init=False)
    volatilidad_anualizada: float = field(init=False)

    def _validar(self) -> None:
        validar_serie_precios(self.serie_temporal)

    def _calcular_estadisticos(self) -> None:
        rendimientos = self.rendimientos()
        media = float(rendimientos.mean())
        desviacion = float(rendimientos.std())
        # Rentabilidad compuesta a partir de la media diaria y volatilidad por la regla de la raíz
        rentabilidad_anual = (1 + media) ** DIAS_COTIZACION_ANUAL - 1
        volatilidad_anual = desviacion * np.sqrt(DIAS_COTIZACION_ANUAL)
        object.__setattr__(self, "media", media)
        object.__setattr__(self, "desviacion_tipica", desviacion)
        object.__setattr__(self, "rentabilidad_anualizada", rentabilidad_anual)
        object.__setattr__(self, "volatilidad_anualizada", float(volatilidad_anual))

    @property
    def activo(self) -> str:
        return str(self.serie_temporal.name)

    @property
    def tipo(self) -> str:
        return self.tipo_activo.value

    def rendimientos(self, tipo: Literal["simple", "log"] = "simple") -> pd.Series:
        """
        Calcula los rendimientos diarios de la serie de precios.
        :param tipo: `"simple"` para rendimientos aritméticos y `"log"` para logarítmicos.
        :return: Serie con los rendimientos diarios (sin el primer día, que no tiene rendimiento).
        """
        precios = self.serie_temporal
        if tipo == "simple":
            rendimientos = precios / precios.shift(1) - 1
        elif tipo == "log":
            rendimientos = np.log(precios / precios.shift(1))
        else:
            raise ValueError(f"Tipo de rendimiento no válido: {tipo}. Usa 'simple' o 'log'.")
        return rendimientos.dropna()

    def resumen(self) -> dict:
        """
        Devuelve la información principal de la serie y sus estadísticos.
        :return: Diccionario con los metadatos y los estadísticos de la serie.
        """
        return {
            "nombre": self.nombre,
            "activo": self.activo,
            "tipo": self.tipo,
            "moneda": self.moneda,
            "proveedor": self.proveedor,
            "inicio": self.inicio,
            "fin": self.fin,
            "observaciones": self.observaciones,
            "media_diaria": self.media,
            "desviacion_tipica_diaria": self.desviacion_tipica,
            "rentabilidad_anualizada": self.rentabilidad_anualizada,
            "volatilidad_anualizada": self.volatilidad_anualizada,
        }


@dataclass(frozen=True, eq=False)
class MacroSeries(SerieTemporal):
    """
    Serie que no es de precios, como un tipo de interés o un indicador macroeconómico. Sus
    estadísticos son la media y la desviación típica del nivel de la serie, no de rendimientos.
    :param serie_temporal: Serie de valores con un índice de fechas.
    :param metadatos: Información adicional de la serie (por ejemplo, su nombre).
    :param unidad: Unidad en la que se expresan los valores (por ejemplo, "%").
    :param proveedor: Fuente de la que se han obtenido los datos.
    """

    unidad: str | None = None
    proveedor: str | None = None
    media: float = field(init=False)
    desviacion_tipica: float = field(init=False)

    def _calcular_estadisticos(self) -> None:
        object.__setattr__(self, "media", float(self.serie_temporal.mean()))
        object.__setattr__(self, "desviacion_tipica", float(self.serie_temporal.std()))

    @property
    def ultimo_valor(self) -> float:
        return float(self.serie_temporal.iloc[-1])

    def resumen(self) -> dict:
        """
        Devuelve la información principal de la serie y sus estadísticos.
        :return: Diccionario con los metadatos y los estadísticos de la serie.
        """
        return {
            "nombre": self.nombre,
            "unidad": self.unidad,
            "proveedor": self.proveedor,
            "inicio": self.inicio,
            "fin": self.fin,
            "observaciones": self.observaciones,
            "media": self.media,
            "desviacion_tipica": self.desviacion_tipica,
            "ultimo_valor": self.ultimo_valor,
        }
