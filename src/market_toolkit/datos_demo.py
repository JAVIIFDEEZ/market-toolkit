"""
Datos de la demo y de la interfaz web: descarga de datos reales (Yahoo Finance, Alpha Vantage y
FRED) y generación de datos sintéticos para usarlas sin conexión. Está en el paquete para que la
demo y la web usen exactamente el mismo código.
"""

import zlib

import numpy as np
import pandas as pd

from market_toolkit import config
from market_toolkit.models import FinancialSeries, TipoActivo
from market_toolkit.providers.providers import (
    AlphaVantageProvider,
    MacroProvider,
    YahooFinanceProvider,
)

INICIO = "2022-01-01"
FIN = "2024-12-31"
TIPO_LIBRE_RIESGO_POR_DEFECTO = 0.04  # Si no hay clave de FRED
SERIE_TIPO_LIBRE_RIESGO = "DTB3"  # Letras del Tesoro de EE. UU. a 3 meses, en %


def es_materia_prima(ticker: str) -> bool:
    """`True` si el ticker es una materia prima de Alpha Vantage (ORO, GOLD, PLATA, BRENT...)."""
    return ticker.upper() in AlphaVantageProvider.COMMODITIES


def descargar_reales(tickers, indice="", inicio=INICIO, fin=FIN):
    """
    Descarga las series de Yahoo Finance y, para las materias primas, de Alpha Vantage. Si hay
    clave de FRED, descarga también el tipo libre de riesgo.
    :param tickers: Tickers de los activos.
    :param indice: Ticker del índice de referencia. Puede ir vacío.
    :param inicio: Fecha de inicio, `AAAA-MM-DD`.
    :param fin: Fecha de fin, `AAAA-MM-DD`.
    :return: La lista de series y el tipo libre de riesgo en tanto por uno (`None` si no hay clave
        de FRED o no se ha podido descargar).
    """
    materias_primas = []
    de_yahoo = []
    for ticker in tickers:
        if es_materia_prima(ticker):
            materias_primas.append(ticker)
        else:
            de_yahoo.append(ticker)
    if indice:
        de_yahoo.append(indice)
    series = []
    if de_yahoo:
        series = YahooFinanceProvider(de_yahoo).download(inicio=inicio, fin=fin)
    if materias_primas:
        if not config.ALPHAVANTAGE_API_KEY:
            raise ValueError(
                "Para descargar materias primas hace falta ALPHAVANTAGE_API_KEY en el .env."
            )
        series = series + AlphaVantageProvider(materias_primas).download(inicio=inicio, fin=fin)
    tasa = None
    if config.FRED_API_KEY:
        try:
            letras = MacroProvider([SERIE_TIPO_LIBRE_RIESGO]).download(inicio=inicio, fin=fin)[0]
            tasa = letras.ultimo_valor / 100  # Viene en porcentaje
        except Exception:  # Sin el tipo de FRED se usa el valor por defecto
            tasa = None
    return series, tasa


def generar_sinteticos(tickers, indice="", inicio=INICIO, fin=FIN, etfs=(), semilla=42):
    """
    Genera series con el mismo formato que las descargadas, para trabajar sin conexión. Cada
    activo depende de un factor de mercado común (con una beta distinta) más un ruido propio, así
    que las correlaciones y las rentabilidades varían como en un mercado real. Cada ticker tiene
    siempre la misma serie, sin importar el orden ni qué otros activos se elijan.
    :param tickers: Tickers de los activos.
    :param indice: Ticker del índice de referencia, que sigue al factor de mercado. Puede ir vacío.
    :param inicio: Fecha de inicio, `AAAA-MM-DD`.
    :param fin: Fecha de fin, `AAAA-MM-DD`.
    :param etfs: Tickers que se marcan como ETF en lugar de como acción.
    :param semilla: Semilla del generador, para que los datos sean reproducibles.
    :return: Lista de `FinancialSeries`, con el índice al final.
    """
    fechas = pd.bdate_range(inicio, fin)
    mercado = np.random.default_rng(semilla).normal(0.0003, 0.010, len(fechas))
    series = []
    todos = list(tickers) + ([indice] if indice else [])
    for ticker in todos:
        # Un generador por ticker: la serie de cada ticker no depende de los demás
        rng = np.random.default_rng([semilla, zlib.crc32(ticker.encode("utf-8"))])
        if ticker == indice:
            rendimientos = mercado
            tipo = TipoActivo.INDICE
        else:
            if es_materia_prima(ticker):
                beta = rng.uniform(-0.2, 0.3)  # Las materias primas apenas siguen a la bolsa
                tipo = TipoActivo.COMMODITY
            else:
                beta = rng.uniform(0.6, 1.4)
                tipo = TipoActivo.ETF if ticker in etfs else TipoActivo.ACCION
            alfa = rng.uniform(-0.0003, 0.0004)
            ruido = rng.normal(0, rng.uniform(0.006, 0.016), len(fechas))
            rendimientos = alfa + beta * mercado + ruido
        precios = pd.Series(100 * np.exp(np.cumsum(rendimientos)), index=fechas, name=ticker)
        series.append(
            FinancialSeries(
                precios,
                tipo,
                moneda="USD",
                proveedor="Sintético",
                metadatos={"nombre": f"{ticker} (sintético)"},
            )
        )
    return series
