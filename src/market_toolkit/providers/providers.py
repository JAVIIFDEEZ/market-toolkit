import warnings
import dataclasses
from abc import ABC, abstractmethod
from typing import Any
from datetime import date
import getpass
import time

from massive import RESTClient

import yfinance
import pandas as pd

from market_toolkit.exceptions import DataNotFoundException
from market_toolkit.preprocessing import limpiar_datos


@dataclasses.dataclass(frozen=True)
class FinancialSeries:
    serie_temporal: pd.Series
    metadatos: dict

    def __post_init__(self):
        self.metadatos["inicio"] = self.serie_temporal.index.min().date()
        self.metadatos["fin"] = self.serie_temporal.index.max().date()
        self.metadatos["activo"] = self.serie_temporal.name

    @property
    def nombre(self) -> str:
        return self.metadatos["nombre"]

    @property
    def activo(self) -> str:
        return self.metadatos["activo"]

    @property
    def inicio(self) -> date:
        return self.metadatos["inicio"]

    @property
    def fin(self) -> date:
        return self.metadatos["fin"]

    @property
    def duracion(self):
        return (self.fin - self.inicio).days

    @property
    def tipo(self) -> str:
        return self.metadatos["tipo"]


class Provider(ABC):
    """Clase base abstracta para los provedores de información bursátil."""
    tickers: list[str]

    def __init__(self, tickers: list[str]) -> None:
        """
        Inicializador de la clase abstracta base de los proveedores de información bursátil.
        :param tickers: Los tickers de los que se quiere ibtener la información.
        """
        self.tickers = self._validar_input(tickers)

    @abstractmethod
    def _validar_input(self, tickers: list[str]) -> list[str]:
        """Comprueba que los tickers configurados existen en la fuente de datos."""
        return list(set(map(lambda s: s.upper(), tickers)))

    @abstractmethod
    def download(self, *, inicio: Any = None, fin: Any = None, periodo: str | None = None, **opciones: Any) -> list[FinancialSeries]:
        """
        Descarga los datos financioneros durante el periodo especificado para los tickers configurados en este provedor.
        Si no se especifica ningún parámetro, se obtiene el histórico desde la fecha de cotización de los activos hasta el día actual.
        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico. Se ignora si se ha establecido una fecha de inicio y de fin.
        :param opciones: Opciones adicionales de descarga.
        :return: Un dataframe con la información bursatil correspondiente.
        """

    def incorporar_tickers(self, tickers_nuevos: list[str]) -> None:
        """
        Añade los tickers especificados al proveedor.
        :param tickers_nuevos: Los tickers a añadir.
        """

        self.tickers.extend(map(lambda s: s.upper(), tickers_nuevos))
        self.tickers = list(set(self.tickers))

    def eliminar_tickers(self, tickers_eliminar: list[str]) -> None:
        """
        Elimina los tickers especificados del proveedor.
        :param tickers_eliminar: Los tickers a eliminar.
        """
        tickers_eliminar = set(tickers_eliminar)
        self.tickers = [ticker for ticker in self.tickers if ticker not in tickers_eliminar]


class YahooFinanceProvider(Provider):
    """Proveedor para descargar datos financieros de Yahoo Finance."""

    def __init__(self, tickers: list[str]) -> None:
        """
        Initialize un objeto de proveedor de Yahoo Finance.
        :param tickers: Los tickers de los que se quiere obtener la información.
        """
        super().__init__(tickers)

    def _validar_input(self, tickers: list[str]) -> list[str]:
        """
        Funcion que comprueba que los tickers de acciones e índices bursátiles son válidos y se queda únicamente con éstos.
        :param tickers: Los tickers a comprobar.
        :return: Una lista formada por los tickers válidos.
        """
        inexistentes = []
        tickers = super()._validar_input(tickers)
        validos = []
        # Comprobar que los tickers son de acciones individuales
        for ticker in tickers:
            try:
                tipologia = yfinance.Ticker(ticker).info['quoteType']
            except KeyError:
                inexistentes.append(ticker)
            else:
                if tipologia == "EQUITY":
                    validos.append(ticker)
                else:
                    inexistentes.append(ticker)
        # Si algún ticker no es válido, mostrar un warning por pantalla y eliminarlo
        if inexistentes:
            warnings.warn(f"Los tickers {', '.join(inexistentes)} no son equities o no existen en Yahoo Finance. Se eliminan de los datos de busqueda.", UserWarning, stacklevel=2)
        return validos

    def download(self, *, inicio: str | None = None, fin: str | None = None, periodo: str | None = None, **opciones: Any) -> list[FinancialSeries]:
        """
        Descarga los datos financioneros durante el periodo especificado para los tickers configurados en este provedor.
        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico. Se ignora si se ha establecido una fecha de inicio y de fin.
        :return: Dataframe con los datos de cierre ajustados para cada uno de los tickers configurados en este proveedor.
        """
        if inicio is not None and fin is not None:
            periodo = None
        datos = yfinance.download(self.tickers, start=inicio, end=fin, period=periodo)
        if datos is None or datos.empty:
            raise DataNotFoundException(f"No se ha encontrado información para los tickers {", ".join(self.tickers)} en la base de datos de Yahoo Finance.")

        datos = datos["Close"] # Nos quedamos con los datos de cierre ajustados
        alineacion_temporal = opciones.get("alineacion_temporal", None)
        datos_limpios = limpiar_datos(datos, alineacion_temporal)
        series = []
        for ticker in self.tickers:
            series.append(FinancialSeries(datos_limpios[ticker], {"nombre": ticker, "proveedor": "Yahoo Finance", "tipo": "acción"}))
        return series


    def __repr__(self) -> str:
        return f"YahooFinanceProvider object tickers<{', '.join(self.tickers)}>"


class PolygonProvider(Provider):
    """Proveedor para descargar datos financieros de Polygon.io del plan gratuito (ahora Massive)."""

    # Periodos admitidos y sus días equivalentes
    PERIODOS = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}
    DIAS_HISTORICO = 730  # El plan gratuito solo cubre 2 años

    def __init__(self, tickers: list[str], pausa: int = 12) -> None:
        """
        Inicializa un objeto de proveedor de Polygon. Pide la API key por pantalla.
        :param tickers: Los tickers de los que se quiere obtener la información.
        :param pausa: Segundos de espera entre llamadas (plan gratuito: 5 llamadas/minuto).
        """
        api_key = getpass.getpass("Introduce tu API key de Polygon: ").strip()
        if api_key == "":
            raise ValueError("No se ha introducido ninguna API key.")
        self.cliente = RESTClient(api_key)
        self.pausa = pausa
        super().__init__(tickers)

    def _validar_input(self, tickers: list[str]) -> list[str]:
        """
        Comprueba que los tickers existen en Polygon y son acciones, y se queda únicamente con éstos.
        :param tickers: Los tickers a comprobar.
        :return: Una lista formada por los tickers válidos.
        """
        inexistentes = []
        tickers = super()._validar_input(tickers)
        validos = []
        for i, ticker in enumerate(tickers):
            if i > 0:
                time.sleep(self.pausa)  # Esperar entre llamadas 
            try:
                tipologia = self.cliente.get_ticker_details(ticker).type
            except Exception:
                inexistentes.append(ticker)
            else:
                if tipologia == "CS":  # CS = Common Stock, el equivalente a "EQUITY" en Yahoo
                    validos.append(ticker)
                else:
                    inexistentes.append(ticker)
        if inexistentes:
            warnings.warn(f"Los tickers {', '.join(inexistentes)} no son equities o no existen en Polygon. Se eliminan de los datos de busqueda.", UserWarning, stacklevel=2)
        return validos

    def _calcular_fechas(self, inicio: str | None, fin: str | None, periodo: str | None) -> tuple[str, str]:
        """
        Calcula las fechas de inicio y fin, ya que Polygon necesita siempre las dos.
        Si la fecha de inicio es anterior a lo que cubre el plan, se recorta y se avisa.
        :return: Tupla (inicio, fin) en formato 'YYYY-MM-DD'.
        """
        hoy = pd.Timestamp.today().normalize()

        # Fecha de fin: la indicada o, por defecto, ayer (último día cerrado)
        if fin is None:
            fin = hoy - pd.Timedelta(days=1)
        else:
            fin = pd.Timestamp(fin)

        # Fecha de inicio: la indicada o, si no, fin menos el periodo (por defecto 2 años)
        if inicio is None:
            if periodo is None:
                periodo = "2y"
            if periodo not in self.PERIODOS:
                raise ValueError(f"Periodo '{periodo}' no válido. Usa uno de: {', '.join(self.PERIODOS)}.")
            inicio = fin - pd.Timedelta(days=self.PERIODOS[periodo])
        else:
            inicio = pd.Timestamp(inicio)

        # Comprobar el límite del plan gratuito (+1 día de margen)
        limite = hoy - pd.Timedelta(days=self.DIAS_HISTORICO - 1)
        if inicio < limite:
            warnings.warn(f"El plan de Polygon solo cubre desde {limite.date()}. Se recorta la fecha de inicio {inicio.date()}.", UserWarning, stacklevel=3)
            inicio = limite
        if inicio > fin:
            raise ValueError(f"El rango pedido termina el {fin.date()}, antes de lo que cubre el plan ({limite.date()}).")

        return inicio.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d")

    def download(self, *, inicio: str | None = None, fin: str | None = None, periodo: str | None = None, **opciones: Any) -> list[FinancialSeries]:
        """
        Descarga los datos financieros durante el periodo especificado para los tickers configurados en este proveedor.
        Si no se especifica ningún parámetro, se descargan los últimos 2 años (límite del plan gratuito).
        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico ("1mo", "3mo", "6mo", "1y", "2y"). Se ignora si se ha establecido una fecha de inicio.
        :return: Lista de FinancialSeries con los precios de cierre ajustados de cada ticker.
        """
        desde, hasta = self._calcular_fechas(inicio, fin, periodo)

        time.sleep(self.pausa) 
        cierres_por_ticker = {}
        errores = []
        for i, ticker in enumerate(self.tickers):
             
            if i > 0:
                time.sleep(self.pausa)
            try:
                aggs = self.cliente.list_aggs(ticker=ticker, multiplier=1, timespan="day", from_=desde, to=hasta, adjusted=True, limit=50000)
                fechas = []
                cierres = []
                for agg in aggs:
                    fechas.append(agg.timestamp)
                    cierres.append(agg.close)
            except Exception as e:
                errores.append(f"{ticker} ({e})")
                continue

            if len(cierres) == 0:
                errores.append(f"{ticker} (sin datos en el rango)")
            else:
                # normalize() deja solo la fecha, igual que el índice de Yahoo
                indice = pd.to_datetime(fechas, unit="ms").normalize()
                cierres_por_ticker[ticker] = pd.Series(cierres, index=indice, name=ticker)

        if errores:
            warnings.warn(f"No se han podido descargar: {', '.join(errores)}.", UserWarning, stacklevel=2)
        if len(cierres_por_ticker) == 0:
            raise DataNotFoundException(f"No se ha encontrado información para los tickers {', '.join(self.tickers)} en Polygon.")

        datos = pd.DataFrame(cierres_por_ticker)
        alineacion_temporal = opciones.get("alineacion_temporal", None)
        datos_limpios = limpiar_datos(datos, alineacion_temporal)
        series = []
        for ticker in datos_limpios.columns:
            series.append(FinancialSeries(datos_limpios[ticker], {"nombre": ticker, "proveedor": "Polygon", "tipo": "acción"}))
        return series

    def __repr__(self) -> str:
        return f"Polygon object tickers<{', '.join(self.tickers)}>"
