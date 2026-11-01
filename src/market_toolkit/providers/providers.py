import warnings
from abc import ABC, abstractmethod
from typing import Any, Self

import yfinance

from market_toolkit.exceptions import DataNotFoundException
from market_toolkit.models import FinancialSeries, TipoActivo
from market_toolkit.preprocessing import limpiar_serie


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
    def download(
        self, *, inicio: Any = None, fin: Any = None, periodo: str | None = None, **opciones: Any
    ) -> list[FinancialSeries]:
        """
        Descarga los datos financieros durante el periodo especificado para los
        tickers configurados en este proveedor.

        Si no se especifica ningún parámetro, se obtiene el histórico desde la
        fecha de cotización de los activos hasta el día actual.

        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico. Se ignora si se han establecido
            una fecha de inicio y de fin.
        :param opciones: Opciones adicionales de descarga.
        :return: Una lista de objetos FinancialSeries.
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
        Función que comprueba que los tickers de acciones e índices bursátiles
        son válidos y conserva únicamente aquellos que lo son.
        :param tickers: Los tickers a comprobar.
        :return: Una lista formada por los tickers válidos.
        """
        inexistentes = []
        tickers = super()._validar_input(tickers)
        validos = []
        # Comprobar que los tickers son de acciones individuales
        for ticker in tickers:
            try:
                tipologia = yfinance.Ticker(ticker).get_fast_info()["quote_type"]
            except KeyError:
                inexistentes.append(ticker)
            else:
                if tipologia == "EQUITY":
                    validos.append(ticker)
                elif tipologia == "INDEX":
                    validos.append(ticker)
                else:
                    inexistentes.append(ticker)
        # Si algún ticker no es válido, mostrar un warning por pantalla y eliminarlo
        if inexistentes:
            tickers_str = ", ".join(inexistentes)
            warnings.warn(
                f"Los tickers {tickers_str} no son equities o no existen en Yahoo Finance."
                f"Se eliminan de los datos de busqueda.",
                UserWarning,
                stacklevel=2,
            )
        return validos

    def download(
        self, *, inicio: Any = None, fin: Any = None, periodo: str | None = None, **opciones: Any
    ) -> list[FinancialSeries]:
        """
        Descarga los datos financioneros durante el periodo especificado para los tickers
        configurados en este provedor.
        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico.
        Se ignora si se ha establecido una fecha de inicio y de fin.
        :param opciones: Opciones de limpieza de datos (por ejemplo, alineacion_temporal)
        :return: Dataframe con los datos de cierre ajustados para cada uno de los tickers
        configurados en este proveedor.
        """
        if inicio is not None and fin is not None:
            periodo = None
        if not (inicio or fin or periodo):
            periodo = "max"
        series = []
        for ticker in self.tickers:
            yf_ticker = yfinance.Ticker(ticker)
            datos = yf_ticker.history(start=inicio, end=fin, period=periodo, auto_adjust=True)
            info = yf_ticker.get_info()
            datos = datos["Close"].rename(ticker)  # Nos quedamos con los datos de cierre ajustados
            datos_limpios = limpiar_serie(datos)
            series.append(
                FinancialSeries(
                    datos_limpios,
                    TipoActivo.INDICE if info["quoteType"] == "INDEX" else TipoActivo.ACCION,
                    proveedor = "Yahoo Finance",
                    moneda = info.get("currency"),
                    bolsa = info.get("fullExchangeName"),
                    metadatos = {"nombre": info.get("longName") or info.get("shortName")}
                )
            )
        return series

    @classmethod
    def desde_nombres(cls, nombres: list[str]) -> Self:
        tickers = []
        for nombre in nombres:
            candidatos = yfinance.Search(nombre).quotes
            try:
                elegido = next(candidato["symbol"]
                               for candidato in candidatos
                               if candidato["quoteType"] == "INDEX"
                               or candidato["quoteType"] == "EQUITY")
            except StopIteration:
                warnings.warn(
                    f'No se ha encontrado ningún activo con el nombre "{nombre}".',
                            UserWarning,
                            stacklevel=2
                )
            else:
                tickers.append(elegido)

        if len(tickers) == 0:
            raise DataNotFoundException(
                f"No se ha encontrado ningún activo que coincida con los nombres introducidos: "
                f"{', '.join(nombres)}"
            )
        return cls(tickers)

    def __repr__(self) -> str:
        return f"YahooFinanceProvider object tickers<{', '.join(self.tickers)}>"