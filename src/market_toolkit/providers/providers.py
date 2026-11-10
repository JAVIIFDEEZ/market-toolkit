import getpass
import json
import re
import time
import warnings
from abc import ABC, abstractmethod
from typing import Any, Self

import pandas as pd
import requests
import yfinance
from fredapi import Fred
from massive import RESTClient
from massive.exceptions import BadResponse
from urllib3.exceptions import MaxRetryError

from market_toolkit import config
from market_toolkit.exceptions import (
    DataNotFoundException,
    DataValidationError,
    ProviderError,
    RateLimitError,
)
from market_toolkit.models import FinancialSeries, MacroSeries, SerieTemporal, TipoActivo
from market_toolkit.preprocessing import limpiar_serie


def _resolver_api_key(api_key: str | None, api_key_config: str | None, proveedor: str) -> str:
    """
    Obtiene la API key de un proveedor: la indicada o, si no, la del fichero `.env` y, si
    tampoco está, la pide por pantalla.
    :param api_key: API key indicada por el usuario.
    :param api_key_config: API key cargada en `config` desde el `.env`.
    :param proveedor: Nombre del proveedor, para el mensaje por pantalla.
    :return: La API key sin espacios.
    """
    api_key = api_key or api_key_config
    if not api_key:
        api_key = getpass.getpass(f"Introduce tu API key de {proveedor}: ")
    api_key = api_key.strip()
    if api_key == "":
        raise ValueError("No se ha introducido ninguna API key.")
    return api_key

def _calcular_fechas(
    inicio: Any,
    fin: Any,
    periodo: str | None
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Calcula un rango inclusivo y devuelve siempre sus dos fechas.

    Los periodos admitidos por el cálculo son ``max``, ``ytd`` y cantidades con sufijo
    ``d``, ``mo`` o ``y``. Cada provider aporta la primera fecha histórica disponible y
    valida las restricciones particulares de su API.
    """
    desde = pd.Timestamp(inicio).normalize() if inicio is not None else None
    hasta = pd.Timestamp(fin).normalize() if fin is not None else None

    if desde is not None and hasta is not None:
        periodo = None
    elif periodo is None and desde is None:
        periodo = None

    if periodo not in (None, "max"):
        coincidencia = re.fullmatch(r"(\d+)(d|mo|y)", periodo)
        if coincidencia is None:
            raise ValueError(
                f"Periodo '{periodo}' no válido. Usa 'max' o una cantidad "
                "seguida de 'd', 'mo' o 'y'."
            )
        cantidad, unidad = int(coincidencia[1]), coincidencia[2]
        if cantidad < 1:
            raise ValueError("La duración de periodo debe ser mayor que cero.")
        if unidad == "d":
            desplazamiento = pd.DateOffset(days=cantidad)
        elif unidad == "mo":
            desplazamiento = pd.DateOffset(months=cantidad)
        else:
            desplazamiento = pd.DateOffset(years=cantidad)

        if hasta is not None:
            desde = hasta - desplazamiento
        elif desde is not None:
            hasta = desde + desplazamiento
        else:
            hasta = pd.Timestamp.now().normalize()
            desde = hasta - desplazamiento

    if desde is not None and hasta is not None and desde > hasta:
        raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin.")
    return desde, hasta


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
    ) -> list[SerieTemporal]:
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
        Inicializa un objeto de proveedor de Yahoo Finance.
        :param tickers: Los tickers de los que se quiere obtener la información.
        """
        super().__init__(tickers)

    def _validar_input(self, tickers: list[str]) -> list[str]:
        """
        Función que comprueba que los tickers sean de acciones e índices bursátiles
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
                if tipologia == "EQUITY" or tipologia == "INDEX" or tipologia == "ETF":
                    validos.append(ticker)
                else:
                    inexistentes.append(ticker)
        # Si algún ticker no es válido, mostrar un warning por pantalla y eliminarlo
        if inexistentes:
            tickers_str = ", ".join(inexistentes)
            warnings.warn(
                f"Los tickers {tickers_str} no son equities, índices o ETFs, o no existen "
                f"en Yahoo Finance. Se eliminan de los datos de busqueda.",
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
            # Ajustar a la misma zona horaria
            datos.index = datos.index.tz_localize(None).normalize()
            info = yf_ticker.get_info()
            datos = datos["Close"].rename(ticker)  # Nos quedamos con los datos de cierre ajustados
            datos_limpios = limpiar_serie(datos)
            if info["quoteType"] == "EQUITY":
                tipo = TipoActivo.ACCION
            elif info["quoteType"] == "INDEX":
                tipo = TipoActivo.INDICE
            else:
                tipo = TipoActivo.ETF
            series.append(
                FinancialSeries(
                    datos_limpios,
                    tipo,
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
                               or candidato["quoteType"] == "EQUITY"
                               or candidato["quoteType"] == "ETF")
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


class PolygonProvider(Provider):
    """
    Proveedor para descargar datos financieros de Polygon.io del plan gratuito (ahora Massive).
    """

    # Periodos admitidos. No hay "1mo" ni periodos en días porque no llegan al mínimo de
    # observaciones de FinancialSeries (MIN_OBSERVACIONES), ni más de 2 años por el plan
    PERIODOS = ("3mo", "6mo", "1y", "2y", "max")
    ANIOS_HISTORICO = 2  # El plan gratuito solo cubre 2 años
    # Nombres de las bolsas a partir del código MIC que devuelve Polygon en `primary_exchange`
    BOLSAS = {
        "XNAS": "NASDAQ",
        "XNYS": "NYSE",
        "XASE": "NYSE American",
        "ARCX": "NYSE Arca",
        "BATS": "Cboe BZX",
        "IEXG": "IEX",
    }

    def __init__(self, tickers: list[str], pausa: int = 12, api_key: str | None = None) -> None:
        """
        Inicializa un objeto de proveedor de Polygon.
        :param tickers: Los tickers de los que se quiere obtener la información.
        :param pausa: Segundos de espera entre llamadas (plan gratuito: 5 llamadas/minuto).
        :param api_key: API key de Polygon. Si no se indica, se usa `POLYGON_API_KEY` del
            fichero `.env` y, si tampoco está, se pide por pantalla.
        """
        self.cliente = RESTClient(_resolver_api_key(api_key, config.POLYGON_API_KEY, "Polygon"))
        self.pausa = pausa
        self.info: dict[str, Any] = {}  # Detalles de Polygon de cada ticker validado
        super().__init__(tickers)

    def _validar_input(self, tickers: list[str]) -> list[str]:
        """
        Comprueba que los tickers existen en Polygon y son acciones,
        y se queda únicamente con éstos.
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
                detalles = self.cliente.get_ticker_details(ticker)
            except BadResponse as e:
                # Solo NOT_FOUND significa que el ticker no existe. Con una API key no válida
                # fallarían todos los tickers y no se debe confundir con que no existan
                if self._respuesta_error(e).get("status") != "NOT_FOUND":
                    raise self._error_proveedor(e) from e
                inexistentes.append(ticker)
            except MaxRetryError as e:  # Reintentos agotados (límite de llamadas o servidor)
                raise self._error_proveedor(e) from e
            else:
                if detalles.type == "CS":  # CS = Common Stock, el equivalente a "EQUITY" en Yahoo
                    validos.append(ticker)
                    self.info[ticker] = detalles  # Se reutilizan en download() sin otra llamada
                else:
                    inexistentes.append(ticker)
        if inexistentes:
            warnings.warn(
                f"Los tickers {', '.join(inexistentes)} no son equities o no existen "
                f"en Polygon. Se eliminan de los datos de busqueda.",
                UserWarning, stacklevel=2)
        return validos

    def _metadatos(self, ticker: str) -> dict[str, str | None]:
        """
        Obtiene la moneda, la bolsa y el nombre del activo a partir de sus detalles en Polygon.
        Si el ticker se añadió con `incorporar_tickers`, se piden los detalles en ese momento.
        :param ticker: El ticker del activo.
        :return: Diccionario con `moneda`, `bolsa` y `nombre`.
        """
        if ticker not in self.info:
            time.sleep(self.pausa)
            self.info[ticker] = self.cliente.get_ticker_details(ticker)
        detalles = self.info[ticker]
        moneda = detalles.currency_name.upper() if detalles.currency_name else None
        # Polygon da la bolsa principal de cotización. Si no la indica, el activo cotiza en
        # varias sin una principal
        mic = detalles.primary_exchange
        bolsa = self.BOLSAS.get(mic, mic) if mic else "Desconocido"
        return {"moneda": moneda, "bolsa": bolsa, "nombre": detalles.name or ticker}

    @staticmethod
    def _respuesta_error(error: BadResponse) -> dict:
        """
        Lee el JSON que devuelve Polygon en una respuesta de error.
        :return: Diccionario con la respuesta (`status`, `error`, `message`...) o vacío si no es
            un JSON.
        """
        try:
            respuesta = json.loads(str(error))
        except ValueError:
            return {}
        return respuesta if isinstance(respuesta, dict) else {}

    def _error_proveedor(self, error: Exception) -> ProviderError:
        """
        Traduce un error de Polygon a una excepción del paquete.
        :param error: El error lanzado por el cliente de Polygon.
        :return: `RateLimitError` si se ha superado el límite de llamadas, o `ProviderError`.
        """
        if isinstance(error, BadResponse):
            respuesta = self._respuesta_error(error)
            mensaje = respuesta.get("error") or respuesta.get("message") or str(error)
        else:
            mensaje = str(error)
        # 429 en los reintentos agotados de urllib3 o el mensaje de Polygon: "You've exceeded
        # the maximum requests per minute..."
        if "429" in mensaje or "maximum requests" in mensaje.lower():
            return RateLimitError(
                f"Se ha superado el límite de llamadas de Polygon (plan gratuito: 5/minuto). "
                f"Prueba a aumentar `pausa` (ahora {self.pausa} s). Detalle: {mensaje}")
        if "api key" in mensaje.lower():
            return ProviderError(f"Polygon ha rechazado la API key: {mensaje}")
        return ProviderError(f"Error de Polygon: {mensaje}")

    def download(self, *, inicio: str | None = None, fin: str | None = None,
                 periodo: str | None = None, **opciones: Any) -> list[FinancialSeries]:
        """
        Descarga los datos financieros durante el periodo especificado para los tickers
        configurados en este proveedor. Si no se especifica ningún parámetro, se descargan los
        últimos 2 años (límite del plan gratuito).
        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico ("3mo", "6mo", "1y", "2y", "max"). Si solo se indica
            una fecha, el periodo calcula el otro límite; con ambas fechas se ignora.
        :return: Lista de FinancialSeries con los precios de cierre ajustados de cada ticker.
        """
        # Se comprueba antes de llamar a la API para no esperar las pausas en balde
        if periodo is not None and periodo not in self.PERIODOS:
            raise ValueError(
                f"Periodo '{periodo}' no válido. Usa uno de: {', '.join(self.PERIODOS)}.")
        hoy = pd.Timestamp.today().normalize()
        limite = hoy - pd.DateOffset(years=self.ANIOS_HISTORICO)
        desde, hasta = _calcular_fechas(inicio, fin, periodo)
        # Primero el fin: si el rango queda entero fuera del plan no tiene sentido recortar
        if hasta is None:
            hasta = hoy
        elif hasta < limite:
            raise ValueError(
                f"El rango pedido termina el {hasta.date()}, "
                f"antes de lo que cubre el plan ({limite.date()}).")
        if desde is None:
            desde = limite
        elif desde < limite:
            warnings.warn(
                f"El plan de Polygon solo cubre desde {limite.date()}. "
                f"Se recorta la fecha de inicio {desde.date()}.",
                UserWarning, stacklevel=2)
            desde = limite
        desde, hasta = desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d")

        time.sleep(self.pausa)
        cierres_por_ticker = {}
        errores = []
        for i, ticker in enumerate(self.tickers):

            if i > 0:
                time.sleep(self.pausa)
            try:
                aggs = self.cliente.list_aggs(ticker=ticker, multiplier=1, timespan="day",
                                              from_=desde, to=hasta, adjusted=True, limit=50000)
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

        series = []
        for ticker, datos in cierres_por_ticker.items():
            datos_limpios = limpiar_serie(datos)
            try:
                metadatos = self._metadatos(ticker)
                series.append(
                    FinancialSeries(
                        datos_limpios,
                        TipoActivo.ACCION,
                        proveedor="Polygon",
                        moneda=metadatos["moneda"],
                        bolsa=metadatos["bolsa"],
                        metadatos={"nombre": metadatos["nombre"]}
                    )
                )
            except (DataValidationError, BadResponse) as e:  # Incluye InsufficientDataError
                errores.append(f"{ticker} ({e})")

        if errores:
            warnings.warn(f"No se han podido descargar: {', '.join(errores)}.", UserWarning,
                          stacklevel=2)
        if len(series) == 0:
            tickers = ', '.join(self.tickers)
            raise DataNotFoundException(
                f"No se ha encontrado información válida para los tickers {tickers} en Polygon.")
        return series

    def __repr__(self) -> str:
        return f"Polygon object tickers<{', '.join(self.tickers)}>"


class MacroProvider(Provider):
    """
    Proveedor para descargar series macroeconómicas de FRED. Con la opción `vintage` descarga
    los datos tal y como se publicaron en el pasado (ALFRED), sin las revisiones posteriores.
    Los "tickers" son los IDs de las series de FRED (por ejemplo "DGS10") o sus alias en `SERIES`.
    """

    # Alias de series habituales. También se puede usar cualquier ID de FRED directamente
    SERIES = {
        "us10y": "DGS10",  # Bono EE.UU. 10 años, % diario
        "us2y": "DGS2",  # Bono EE.UU. 2 años, % diario
        "us10y_2y": "T10Y2Y",  # Spread 10Y-2Y EE.UU., p.p. diario
        "ipc_eurozona": "CP0000EZ19M086NEST",  # HICP Eurozona, índice 2015=100 mensual
        "pib_espana": "CLVMNACSCAB1GQES",  # PIB real España, M€ encadenados trimestral
        "es10y": "IRLTLT01ESM156N",  # Bono España 10 años, % mensual
        "de10y": "IRLTLT01DEM156N",  # Bund 10 años, % mensual
        "bce_depo": "ECBDFR",  # Facilidad de depósito del BCE, %
        "fed_funds": "DFF",  # Fed Funds efectivo, % diario
        "cpi_eeuu": "CPIAUCSL",  # IPC EE.UU., índice mensual
        "pib_eeuu": "GDPC1",  # PIB real EE.UU., trimestral
        "paro_eeuu": "UNRATE",  # Tasa de paro EE.UU., %
        "eurusd": "DEXUSEU",  # Dólares por euro, diario
        "vix": "VIXCLS",  # Índice de volatilidad VIX, diario
        "hy_spread": "BAMLH0A0HYM2",  # Spread High Yield EE.UU., %
        "wti": "DCOILWTICO",  # Petróleo WTI, $/barril
        "breakeven10y": "T10YIE",  # Inflación implícita a 10 años EE.UU., %
    }
    # Frecuencias y métodos de agregación que admite la API de FRED
    FRECUENCIAS = ("d", "w", "bw", "m", "q", "sa", "a")
    AGREGACIONES = ("avg", "sum", "eop")

    def __init__(self, tickers: list[str], api_key: str | None = None) -> None:
        """
        Inicializa un objeto de proveedor de FRED.
        :param tickers: IDs de FRED o alias de `SERIES` de las series que se quieren obtener.
        :param api_key: API key de FRED. Si no se indica, se usa `FRED_API_KEY` del
            fichero `.env` y, si tampoco está, se pide por pantalla.
        """
        self.cliente = Fred(api_key=_resolver_api_key(api_key, config.FRED_API_KEY, "FRED"))
        self.info: dict[str, pd.Series] = {}  # Metadatos de FRED de cada serie validada
        super().__init__(tickers)

    def _validar_input(self, tickers: list[str]) -> list[str]:
        """
        Traduce los alias a IDs de FRED, comprueba que las series existen y guarda sus metadatos.
        :param tickers: IDs de FRED o alias de las series a comprobar.
        :return: Una lista formada por los IDs de las series válidas.
        """
        inexistentes = []
        tickers = super()._validar_input([self.SERIES.get(t.lower(), t) for t in tickers])
        validos = []
        for ticker in tickers:
            try:
                self.info[ticker] = self.cliente.get_series_info(ticker)
            except ValueError as e:
                # Con una API key no válida fallarían todas las series: no es que no existan
                if "api_key" in str(e).lower():
                    raise ProviderError(f"FRED ha rechazado la API key: {e}") from e
                inexistentes.append(ticker)
            else:
                validos.append(ticker)
        if inexistentes:
            warnings.warn(
                f"Las series {', '.join(inexistentes)} no existen en FRED. "
                f"Se eliminan de los datos de busqueda.",
                UserWarning, stacklevel=2)
        return validos

    def _parametros_frecuencia(self, frecuencia: str | None, agregacion: str | None,
                               vintage: str | None) -> dict[str, str]:
        """
        Comprueba las opciones de frecuencia y las traduce a los parámetros de la API de FRED.
        :return: Diccionario con los parámetros `frequency` y `aggregation_method`.
        """
        parametros = {}
        if frecuencia is not None:
            if frecuencia not in self.FRECUENCIAS:
                raise ValueError(
                    f"Frecuencia '{frecuencia}' no válida. Usa una de: "
                    f"{', '.join(self.FRECUENCIAS)}.")
            if vintage == "first":
                raise ValueError("No se puede cambiar la frecuencia con vintage='first'.")
            parametros["frequency"] = frecuencia
        if agregacion is not None:
            if frecuencia is None:
                raise ValueError("La opción 'agregacion' necesita indicar una 'frecuencia'.")
            if agregacion not in self.AGREGACIONES:
                raise ValueError(
                    f"Agregación '{agregacion}' no válida. Usa una de: "
                    f"{', '.join(self.AGREGACIONES)}.")
            parametros["aggregation_method"] = agregacion
        return parametros

    def _descargar_serie(self, ticker: str, desde: pd.Timestamp | None,
                         hasta: pd.Timestamp | None, vintage: str | None,
                         parametros: dict[str, str]) -> pd.Series:
        """
        Descarga una serie de FRED o, si se indica un vintage, de ALFRED.
        :return: Serie sin limpiar con los valores de cada fecha.
        """
        if vintage is None:
            return self.cliente.get_series(ticker, desde, hasta, **parametros)
        if vintage == "first":
            # Primera publicación de cada dato. FRED no permite filtrar fechas, se hace aquí
            serie = self.cliente.get_series_first_release(ticker)
            serie.index = pd.to_datetime(serie.index)
            return pd.to_numeric(serie, errors="coerce").loc[desde:hasta]
        # Datos tal y como se conocían en la fecha indicada
        fecha = pd.Timestamp(vintage).strftime("%Y-%m-%d")
        return self.cliente.get_series(ticker, desde, hasta, realtime_start=fecha,
                                       realtime_end=fecha, **parametros)

    def download(self, *, inicio: Any = None, fin: Any = None, periodo: str | None = None,
                 **opciones: Any) -> list[MacroSeries]:
        """
        Descarga las series macroeconómicas configuradas en este proveedor durante el periodo
        especificado. Si no se especifica ningún parámetro, se descarga todo el histórico.
        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico: "max" o una duracion en meses o años,
        por ejemplo "6mo" o "5y". Si solo se indica una fecha, el periodo calcula el otro
        límite y con ambas fechas se ignora.
        :param opciones: Opciones de descarga:
            - `vintage`: `None` para los últimos datos publicados, `"first"` para la primera
              publicación de cada dato o una fecha para los datos tal y como se conocían ese
              día. Usa ALFRED.
            - `frecuencia`: agrega la serie en FRED a una frecuencia menor
              ("d", "w", "bw", "m", "q", "sa", "a").
            - `agregacion`: cómo agregar al cambiar la frecuencia: "avg" (media, por defecto
              en FRED), "sum" (suma) o "eop" (último valor del periodo).
        :return: Lista de MacroSeries con los valores de cada serie.
        """
        vintage = opciones.pop("vintage", None)
        frecuencia = opciones.pop("frecuencia", None)
        agregacion = opciones.pop("agregacion", None)
        if opciones:
            raise ValueError(f"Opciones no válidas: {', '.join(opciones)}.")
        parametros = self._parametros_frecuencia(frecuencia, agregacion, vintage)
        desde, hasta = _calcular_fechas(inicio, fin, periodo)

        series = []
        errores = []
        for ticker in self.tickers:
            try:
                datos = self._descargar_serie(ticker, desde, hasta, vintage, parametros)
                if ticker not in self.info:  # Series añadidas con incorporar_tickers
                    self.info[ticker] = self.cliente.get_series_info(ticker)
                info = self.info[ticker]
                # Los valores negativos son válidos en macro (tipos de interés, spreads...)
                datos_limpios = limpiar_serie(datos.rename(ticker), permitir_negativos=True)
                series.append(
                    MacroSeries(
                        datos_limpios,
                        unidad=info.get("units_short"),
                        proveedor="FRED" if vintage is None else "ALFRED",
                        metadatos={
                            "nombre": info.get("title", ticker),
                            "frecuencia": info.get("frequency"),
                            "ajuste_estacional": info.get("seasonal_adjustment_short"),
                            "ultima_actualizacion": info.get("last_updated"),
                            "vintage": vintage,
                        }
                    )
                )
            except (ValueError, DataValidationError) as e:
                errores.append(f"{ticker} ({e})")

        if errores:
            warnings.warn(f"No se han podido descargar: {', '.join(errores)}.", UserWarning,
                          stacklevel=2)
        if len(series) == 0:
            tickers = ', '.join(self.tickers)
            raise DataNotFoundException(
                f"No se ha encontrado información válida para las series {tickers} en FRED.")
        return series

    def __repr__(self) -> str:
        return f"MacroProvider object series<{', '.join(self.tickers)}>"

class AlphaVantageProvider(Provider):
    """Proveedor de precios diarios de oro, plata y petróleo Brent."""

    URL = "https://www.alphavantage.co/query"
    TIMEOUT = 30
    COMMODITIES = {
        "ORO": "GOLD",
        "GOLD": "GOLD",
        "XAU": "GOLD",
        "PLATA": "SILVER",
        "SILVER": "SILVER",
        "XAG": "SILVER",
        "PETRÓLEO": "BRENT",
        "PETROLEO": "BRENT",
        "BRENT": "BRENT",
    }
    NOMBRE_KEY = {"GOLD": ("Oro", "price"), "SILVER": ("Plata", "price"),
                  "BRENT": ("Barril de petróleo crudo Brent", "value")}
    PERIODOS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}

    def __init__(self, tickers: list[str], pausa: float = 1.1, api_key: str | None = None) -> None:
        """
        Inicializa un objeto de proveedor de Alpha Vantage. Busca la API key en el entorno
        o en el fichero .env. En caso de no encontrarla la pide por pantalla.
        :param tickers: Los tickers de los que se quiere obtener la información.
        :param pausa: Pausa temporal entre las descargas en lote para respetar el límite de
        peticiones por segundo del proveedor.
        :param api_key: Key persoal para acceder a la API. Si no se proporciona se busca en
        el entorno o se pide por pantalla.
        """
        self.api_key = _resolver_api_key(api_key, config.ALPHAVANTAGE_API_KEY, "Alpha Vantage")
        self.pausa = pausa
        super().__init__(tickers)

    def _validar_input(self, tickers: list[str]) -> list[str]:
        """
        Función que comprueba que los tickers introducidos son válidos y conserva únicamente
        aquellos que lo son.
        :param tickers: Los tickers a comprobar.
        :return: Una lista formada por los tickers válidos.
        """
        tickers = super()._validar_input(tickers)
        invalidos = set(tickers) - self.COMMODITIES.keys()
        if invalidos:
            warnings.warn(
                f"Los tickers {', '.join(invalidos)} no son commodities admitidos."
                f" Usa: {', '.join(self.COMMODITIES)}.",
                UserWarning, stacklevel=2)

        return list(
            dict.fromkeys(self.COMMODITIES[ticker] for ticker in tickers if ticker not in invalidos)
        )

    def download(
        self,
        *,
        inicio: Any = None,
        fin: Any = None,
        periodo: str | None = None,
        **opciones: Any,
    ) -> list[FinancialSeries]:
        """
        Descarga los datos financioneros durante el periodo especificado para los tickers
        (Oro, Plata y Barril de Brent) configurados en este provedor.
        :param inicio: Fecha de inicio del histórico.
        :param fin: Fecha de fin del histórico.
        :param periodo: Duración del histórico: "max" o una duracion en días, meses o años,
        por ejemplo "3d", "6mo" o "5y". Si solo se indica una fecha, el periodo calcula el otro
        límite y con ambas fechas se ignora.
        :param opciones: Opciones extra.
        :return: Dataframe con los datos de cierre ajustados para cada uno de los tickers
        configurados en este proveedor.
        """
        resultados = []
        sin_datos = []
        for i, ticker in enumerate(self.tickers):
            if i > 0:
                time.sleep(self.pausa)
            params: dict[str, str] = {"apikey": self.api_key, "interval": "daily"}
            if ticker in {"GOLD", "SILVER"}:
                params.update({"function": "GOLD_SILVER_HISTORY", "symbol": ticker})
            else:
                params["function"] = "BRENT"

            try:
                response = requests.get(self.URL, params=params, timeout=self.TIMEOUT)
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as e:
                raise ProviderError(f"Error al descargar {ticker} de Alpha Vantage: {e}") from e

            mensaje_error = (payload.get("Error Message") or payload.get("Information"))
            if mensaje_error:
                raise ProviderError(f"Alpha Vantage no pudo descargar {ticker}: {mensaje_error}")

            datos = payload.get("data")
            if not isinstance(datos, list):
                raise ProviderError(f"Respuesta sin serie temporal válida para {ticker}.")
            nombre, llave = self.NOMBRE_KEY[ticker]
            serie = pd.Series(
                {pd.Timestamp(fila["date"]): pd.to_numeric(fila[llave], errors="coerce")
                 for fila in datos},
                name=ticker,
                dtype=float,
            )
            serie = limpiar_serie(serie)
            if serie.empty:
                sin_datos.append(ticker)
                continue
            desde, hasta = _calcular_fechas(inicio, fin, periodo)
            serie = serie.loc[desde:hasta]
            resultados.append(
                FinancialSeries(
                    serie,
                    TipoActivo.COMMODITY,
                    moneda="USD",
                    proveedor="Alpha Vantage",
                    metadatos={"nombre": nombre},
                )
            )
        if sin_datos:
            warnings.warn(
                f"No hay datos de Alpha Vantage para {', '.join(sin_datos)} "
                f"en el rango solicitado.",
                UserWarning,
                stacklevel=2,
            )
        if not resultados:
            raise DataNotFoundException(
                f"No se ha encontrado información para {', '.join(self.tickers)} en Alpha Vantage."
            )
        return resultados

    def __repr__(self) -> str:
        return f"AlphaVantageProvider object tickers<{', '.join(self.tickers)}>"