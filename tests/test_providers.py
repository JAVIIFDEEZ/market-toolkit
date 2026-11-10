"""
Tests de los proveedores sin red ni claves: cada API se sustituye por un objeto falso que devuelve
respuestas con el mismo formato que la real.
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from massive.exceptions import BadResponse

import market_toolkit.providers.providers as providers
from market_toolkit.exceptions import DataNotFoundException, ProviderError, RateLimitError
from market_toolkit.models import FinancialSeries, MacroSeries, TipoActivo

FECHAS = pd.bdate_range("2024-01-02", periods=60)


def precios(semilla: int, n: int = len(FECHAS)) -> np.ndarray:
    """Precios positivos reproducibles."""
    rng = np.random.default_rng(semilla)
    return 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, n)))


# ---------- Yahoo Finance ----------


class TickerYahooFalso:
    """Imita `yfinance.Ticker`: una acción, un índice, un ETF y un fondo de inversión."""

    DATOS = {
        "AAPL": ("EQUITY", "America/New_York", "USD", "NasdaqGS", "Apple Inc."),
        "^GSPC": ("INDEX", "America/New_York", "USD", "SNP", "S&P 500"),
        "SPY": ("ETF", "America/New_York", "USD", "NYSEArca", "SPDR S&P 500 ETF"),
        "VFIAX": ("MUTUALFUND", "America/New_York", "USD", "Nasdaq", "Vanguard 500 Index"),
    }

    def __init__(self, ticker):
        self.ticker = ticker

    def get_fast_info(self):
        if self.ticker not in self.DATOS:
            raise KeyError("quote_type")
        return {"quote_type": self.DATOS[self.ticker][0]}

    def get_info(self):
        tipo, _, moneda, bolsa, nombre = self.DATOS[self.ticker]
        return {
            "quoteType": tipo,
            "currency": moneda,
            "fullExchangeName": bolsa,
            "longName": nombre,
        }

    def history(self, start=None, end=None, period=None, auto_adjust=True):
        assert auto_adjust is True  # Siempre precios ajustados
        indice = FECHAS.tz_localize(self.DATOS[self.ticker][1]) + pd.Timedelta(hours=9, minutes=30)
        cierres = precios(len(self.ticker))
        cierres[5] = np.nan  # Un dato perdido que la limpieza debe quitar
        return pd.DataFrame({"Open": cierres, "Close": cierres}, index=indice)


@pytest.fixture
def yahoo(monkeypatch):
    monkeypatch.setattr(providers.yfinance, "Ticker", TickerYahooFalso)


def test_yahoo_acepta_acciones_e_indices(yahoo):
    with pytest.warns(UserWarning, match="NOEXISTE"):
        proveedor = providers.YahooFinanceProvider(["aapl", "^gspc", "NOEXISTE"])
    assert sorted(proveedor.tickers) == ["AAPL", "^GSPC"]


def test_yahoo_descarta_otros_tipos_de_activo(yahoo):
    with pytest.warns(UserWarning, match="VFIAX"):
        proveedor = providers.YahooFinanceProvider(["AAPL", "VFIAX"])
    assert proveedor.tickers == ["AAPL"]


def test_yahoo_acepta_etf(yahoo):
    (serie,) = providers.YahooFinanceProvider(["SPY"]).download(inicio="2024-01-01")
    assert serie.tipo_activo == TipoActivo.ETF
    assert serie.nombre == "SPDR S&P 500 ETF"


def test_yahoo_descarga_series_limpias(yahoo):
    series = providers.YahooFinanceProvider(["AAPL", "^GSPC"]).download(inicio="2024-01-01")
    por_ticker = {serie.activo: serie for serie in series}
    accion, indice = por_ticker["AAPL"], por_ticker["^GSPC"]
    assert accion.tipo_activo == TipoActivo.ACCION
    assert indice.tipo_activo == TipoActivo.INDICE
    assert accion.nombre == "Apple Inc."
    assert accion.moneda == "USD"
    assert accion.observaciones == len(FECHAS) - 1  # Sin el dato perdido
    # Índice sin zona horaria ni hora, para poder alinear mercados distintos
    assert accion.serie_temporal.index.tz is None
    assert (accion.serie_temporal.index == accion.serie_temporal.index.normalize()).all()


def test_yahoo_desde_nombres(yahoo, monkeypatch):
    resultados = {
        "apple": [{"symbol": "AAPL", "quoteType": "EQUITY"}],
        # Se elige el primer resultado de un tipo admitido (acción, índice o ETF)
        "sp500": [
            {"symbol": "ES=F", "quoteType": "FUTURE"},
            {"symbol": "^GSPC", "quoteType": "INDEX"},
        ],
    }
    monkeypatch.setattr(
        providers.yfinance, "Search", lambda nombre: SimpleNamespace(quotes=resultados[nombre])
    )
    proveedor = providers.YahooFinanceProvider.desde_nombres(["apple", "sp500"])
    assert sorted(proveedor.tickers) == ["AAPL", "^GSPC"]


def test_yahoo_desde_nombres_sin_resultados(yahoo, monkeypatch):
    monkeypatch.setattr(providers.yfinance, "Search", lambda nombre: SimpleNamespace(quotes=[]))
    with pytest.warns(UserWarning), pytest.raises(DataNotFoundException):
        providers.YahooFinanceProvider.desde_nombres(["nada"])


def test_incorporar_y_eliminar_tickers(yahoo):
    proveedor = providers.YahooFinanceProvider(["AAPL"])
    proveedor.incorporar_tickers(["^gspc"])
    assert sorted(proveedor.tickers) == ["AAPL", "^GSPC"]
    proveedor.eliminar_tickers(["AAPL"])
    assert proveedor.tickers == ["^GSPC"]


# ---------- Polygon ----------


class ClientePolygonFalso:
    """Imita `massive.RESTClient`: AAPL es una acción, SPY un ETF y el resto no existe."""

    def __init__(self, api_key):
        self.api_key = api_key

    def get_ticker_details(self, ticker):
        if ticker == "AAPL":
            return SimpleNamespace(
                type="CS", currency_name="usd", primary_exchange="XNAS", name="Apple Inc."
            )
        if ticker == "SPY":
            return SimpleNamespace(type="ETF")
        if ticker == "LIMITE":
            raise BadResponse(
                '{"status": "ERROR", "error": "You\'ve exceeded the maximum requests"}'
            )
        raise BadResponse('{"status": "NOT_FOUND"}')

    def list_aggs(self, ticker, **parametros):
        assert parametros["adjusted"] is True
        milisegundos = (FECHAS - pd.Timestamp("1970-01-01")) // pd.Timedelta(milliseconds=1)
        return [
            SimpleNamespace(timestamp=int(ms), close=float(cierre))
            for ms, cierre in zip(milisegundos, precios(7), strict=True)
        ]


@pytest.fixture
def polygon(monkeypatch):
    monkeypatch.setattr(providers, "RESTClient", ClientePolygonFalso)


def test_polygon_valida_tickers(polygon):
    with pytest.warns(UserWarning, match="SPY"):
        proveedor = providers.PolygonProvider(["AAPL", "SPY", "XXXX"], pausa=0, api_key="falsa")
    assert proveedor.tickers == ["AAPL"]


def test_polygon_descarga_con_metadatos(polygon):
    proveedor = providers.PolygonProvider(["AAPL"], pausa=0, api_key="falsa")
    (serie,) = proveedor.download(periodo="1y")
    assert serie.proveedor == "Polygon"
    assert serie.moneda == "USD"
    assert serie.bolsa == "NASDAQ"
    assert serie.nombre == "Apple Inc."
    assert serie.observaciones == len(FECHAS)


def test_polygon_rechaza_periodos_no_validos(polygon):
    proveedor = providers.PolygonProvider(["AAPL"], pausa=0, api_key="falsa")
    with pytest.raises(ValueError, match="Periodo"):
        proveedor.download(periodo="1mo")


def test_polygon_limite_de_llamadas(polygon):
    with pytest.raises(RateLimitError):
        providers.PolygonProvider(["LIMITE"], pausa=0, api_key="falsa")


# ---------- Alpha Vantage ----------


class RespuestaFalsa:
    def __init__(self, contenido):
        self.contenido = contenido

    def raise_for_status(self):
        pass

    def json(self):
        return self.contenido


@pytest.fixture
def alpha_vantage(monkeypatch):
    def get(url, params, timeout):
        clave = "value" if params["function"] == "BRENT" else "price"
        filas = [
            {"date": fecha.strftime("%Y-%m-%d"), clave: str(round(precio, 2))}
            for fecha, precio in zip(FECHAS, precios(11), strict=True)
        ]
        return RespuestaFalsa({"data": filas})

    monkeypatch.setattr(providers.requests, "get", get)


def test_alpha_vantage_traduce_alias(alpha_vantage):
    proveedor = providers.AlphaVantageProvider(["oro", "XAU", "brent"], pausa=0, api_key="falsa")
    assert sorted(proveedor.tickers) == ["BRENT", "GOLD"]


def test_alpha_vantage_descarta_activos_no_admitidos(alpha_vantage):
    with pytest.warns(UserWarning, match="COBRE"):
        proveedor = providers.AlphaVantageProvider(["COBRE", "oro"], pausa=0, api_key="falsa")
    assert proveedor.tickers == ["GOLD"]


def test_alpha_vantage_descarga_materias_primas(alpha_vantage):
    series = providers.AlphaVantageProvider(["oro", "brent"], pausa=0, api_key="falsa").download()
    por_ticker = {serie.activo: serie for serie in series}
    assert por_ticker["GOLD"].nombre == "Oro"
    assert por_ticker["GOLD"].tipo_activo == TipoActivo.COMMODITY
    assert por_ticker["BRENT"].moneda == "USD"
    assert por_ticker["BRENT"].observaciones == len(FECHAS)


def test_alpha_vantage_mensaje_de_error_de_la_api(monkeypatch):
    def get(url, params, timeout):
        return RespuestaFalsa({"Information": "Límite diario de peticiones alcanzado."})

    monkeypatch.setattr(providers.requests, "get", get)
    proveedor = providers.AlphaVantageProvider(["oro"], pausa=0, api_key="falsa")
    with pytest.raises(ProviderError, match="Límite diario"):
        proveedor.download()


# ---------- FRED ----------


class FredFalso:
    """Imita `fredapi.Fred`: solo existe la serie DTB3 (letras del Tesoro a 3 meses)."""

    def __init__(self, api_key):
        self.api_key = api_key

    def get_series_info(self, serie):
        if serie != "DTB3":
            raise ValueError("Bad Request. The series does not exist.")
        return pd.Series(
            {"title": "3-Month Treasury Bill", "units_short": "%", "frequency": "Daily"}
        )

    def get_series(self, serie, desde=None, hasta=None, **parametros):
        valores = np.linspace(-0.5, 5.0, len(FECHAS))  # Los tipos pueden ser negativos
        valores[3] = np.nan
        return pd.Series(valores, index=FECHAS)


@pytest.fixture
def fred(monkeypatch):
    monkeypatch.setattr(providers, "Fred", FredFalso)


def test_fred_descarga_series_macro(fred):
    with pytest.warns(UserWarning, match="NOEXISTE"):
        proveedor = providers.MacroProvider(["dtb3", "NOEXISTE"], api_key="falsa")
    (serie,) = proveedor.download(inicio="2024-01-01")
    assert isinstance(serie, MacroSeries)
    assert serie.nombre == "3-Month Treasury Bill"
    assert serie.unidad == "%"
    assert serie.proveedor == "FRED"
    assert serie.serie_temporal.min() < 0  # Conserva los valores negativos
    assert serie.observaciones == len(FECHAS) - 1  # Sin el dato perdido


def test_fred_traduce_alias(fred, monkeypatch):
    monkeypatch.setitem(providers.MacroProvider.SERIES, "letras_3m", "DTB3")
    proveedor = providers.MacroProvider(["letras_3m"], api_key="falsa")
    assert proveedor.tickers == ["DTB3"]


def test_fred_rechaza_opciones_no_validas(fred):
    proveedor = providers.MacroProvider(["DTB3"], api_key="falsa")
    with pytest.raises(ValueError, match="Frecuencia"):
        proveedor.download(frecuencia="x")
    with pytest.raises(ValueError, match="Opciones no válidas"):
        proveedor.download(opcion_inventada=1)


# ---------- Contrato común: todas las fuentes dan objetos equivalentes (enunciado 4.2) ----------


def test_todas_las_fuentes_de_precios_devuelven_el_mismo_tipo_de_objeto(
    yahoo, polygon, alpha_vantage
):
    series = (
        providers.YahooFinanceProvider(["AAPL"]).download(inicio="2024-01-01")
        + providers.PolygonProvider(["AAPL"], pausa=0, api_key="falsa").download(periodo="1y")
        + providers.AlphaVantageProvider(["oro"], pausa=0, api_key="falsa").download()
    )
    assert [serie.proveedor for serie in series] == ["Yahoo Finance", "Polygon", "Alpha Vantage"]
    for serie in series:
        assert isinstance(serie, FinancialSeries)
        indice = serie.serie_temporal.index
        assert isinstance(indice, pd.DatetimeIndex)
        assert indice.tz is None
        assert (indice == indice.normalize()).all()
        assert serie.moneda == "USD"
        assert serie.volatilidad_anualizada > 0


# ---------- Funciones auxiliares ----------


def test_resolver_api_key_usa_la_indicada_o_la_del_env():
    assert providers._resolver_api_key(" clave ", None, "X") == "clave"
    assert providers._resolver_api_key(None, "del_env", "X") == "del_env"


def test_resolver_api_key_vacia(monkeypatch):
    monkeypatch.setattr(providers.getpass, "getpass", lambda mensaje: "  ")
    with pytest.raises(ValueError, match="API key"):
        providers._resolver_api_key(None, None, "X")


@pytest.mark.parametrize(
    ("inicio", "fin", "periodo", "esperado"),
    [
        ("2024-01-01", "2024-06-30", None, ("2024-01-01", "2024-06-30")),
        ("2024-01-01", "2024-06-30", "5y", ("2024-01-01", "2024-06-30")),  # Fechas mandan
        (None, "2024-06-30", "6mo", ("2023-12-30", "2024-06-30")),
        ("2024-01-01", None, "1y", ("2024-01-01", "2025-01-01")),
        (None, None, None, (None, None)),
    ],
)
def test_calcular_fechas(inicio, fin, periodo, esperado):
    desde, hasta = providers._calcular_fechas(inicio, fin, periodo)
    resultado = tuple(
        None if fecha is None else fecha.strftime("%Y-%m-%d") for fecha in (desde, hasta)
    )
    assert resultado == esperado


@pytest.mark.parametrize("periodo", ["10x", "0y"])
def test_calcular_fechas_periodo_no_valido(periodo):
    with pytest.raises(ValueError):
        providers._calcular_fechas(None, None, periodo)


def test_calcular_fechas_inicio_posterior_al_fin():
    with pytest.raises(ValueError, match="posterior"):
        providers._calcular_fechas("2024-06-30", "2024-01-01", None)
