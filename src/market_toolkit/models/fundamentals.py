from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Fundamentales:
    """
    Ratios fundamentales de una empresa en un ejercicio. Todos los ratios son opcionales porque
    las fuentes de datos no siempre los proporcionan; si falta alguno su valor es `None`.
    :param ticker: Ticker de la empresa.
    :param fecha_ejercicio: Fecha de cierre del ejercicio contable.
    :param roe: Rentabilidad sobre el patrimonio neto (beneficio neto / patrimonio neto).
    :param roa: Rentabilidad sobre el activo (beneficio neto / activo total).
    :param margen: Margen neto (beneficio neto / ingresos).
    :param rotacion: Rotación de activos (ingresos / activo total).
    :param per: Ratio precio / beneficio.
    :param price_to_book: Ratio precio / valor contable.
    """

    ticker: str
    fecha_ejercicio: date | None = None
    roe: float | None = None
    roa: float | None = None
    margen: float | None = None
    rotacion: float | None = None
    per: float | None = None
    price_to_book: float | None = None
