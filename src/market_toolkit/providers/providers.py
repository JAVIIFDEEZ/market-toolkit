import warnings
from abc import ABC, abstractmethod
from typing import Any

import yfinance
import pandas as pd

from market_toolkit.exceptions import DataNotFoundException
from market_toolkit.preprocessing import limpiar_datos


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
    def download(self, *, inicio: Any = None, fin: Any = None, periodo: str | None = None, **opciones: dict[str, Any]) -> pd.DataFrame:
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
        :param tickers: Los tickers de los que se quiere ibtener la información.
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

    def download(self, *, inicio: str | None = None, fin: str | None = None, periodo: str | None = None, **opciones: Any) -> pd.DataFrame:
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
            raise DataNotFoundException(f"No se ha encontrado información para los tickers {self.tickers} en la base de datos de Yahoo Finance.")

        datos = datos["Close"] # Nos quedamos con los datos de cierre ajustados
        alineacion_temporal = opciones.get("alineacion_temporal", None)
        return limpiar_datos(datos, alineacion_temporal)

    def __repr__(self) -> str:
        return f"YahooFinanceProvider object tickers<{','.join(self.tickers)}>"