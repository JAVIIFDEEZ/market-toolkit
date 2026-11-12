"""Tests de la interfaz web: la lógica sin servidor y la API con un servidor local real."""

import json
import threading
import urllib.error
import urllib.request

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

import market_toolkit.datos_demo as datos_demo  # noqa: E402
import market_toolkit.web.aplicacion as aplicacion  # noqa: E402
from market_toolkit.models import FinancialSeries, MacroSeries, TipoActivo  # noqa: E402
from market_toolkit.web import Aplicacion, crear_servidor  # noqa: E402
from market_toolkit.web.aplicacion import limpiar_json, separar_tickers  # noqa: E402

PESOS = {"AAPL": 35, "MSFT": 35, "JPM": 30}


@pytest.fixture
def app():
    app = Aplicacion(sin_red=True)
    app.cargar_datos("aapl, msft jpm", sintetico=True)
    return app


@pytest.fixture
def app_con_cartera(app):
    app.crear_cartera(PESOS)
    return app


@pytest.fixture
def servidor():
    servidor = crear_servidor(0, Aplicacion(sin_red=True))
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://localhost:{servidor.server_port}"
    servidor.shutdown()
    servidor.server_close()


def llamar(url, accion, datos, tipo="application/json"):
    peticion = urllib.request.Request(
        f"{url}/api/{accion}", json.dumps(datos).encode(), {"Content-Type": tipo}
    )
    try:
        with urllib.request.urlopen(peticion) as respuesta:
            return respuesta.status, json.load(respuesta)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_separar_tickers():
    assert separar_tickers("aapl, msft;jpm  aapl") == ["AAPL", "MSFT", "JPM"]
    assert separar_tickers([" a ", "", "b"]) == ["A", "B"]


def test_limpiar_json_convierte_tipos_de_numpy_y_pandas():
    valor = {"a": np.float64(1.5), "b": np.nan, "c": pd.Timestamp("2024-01-02"), "d": np.int64(3)}
    assert limpiar_json(valor) == {"a": 1.5, "b": None, "c": "2024-01-02", "d": 3}
    json.dumps(limpiar_json(pd.Series({"x": np.inf})), allow_nan=False)  # No debe fallar


def test_cargar_datos_sinteticos(app):
    assert app.activos == ["AAPL", "MSFT", "JPM"]
    assert app.indice is not None and app.indice.activo == "^GSPC"
    assert app.datos_reales is False


@pytest.mark.parametrize(
    "parametros",
    [
        {"tickers": "AAPL"},
        {"tickers": "AAPL, MSFT", "indice": "AAPL"},
        {"tickers": "AAPL, MSFT", "inicio": "2024-01-01", "fin": "2023-01-01"},
    ],
)
def test_cargar_datos_rechaza_entradas_no_validas(parametros):
    with pytest.raises(ValueError):
        Aplicacion().cargar_datos(sintetico=True, **parametros)


def test_crear_cartera(app):
    resultado = app.crear_cartera(PESOS)
    activos = {fila["activo"]: fila for fila in resultado["activos"]}
    assert activos["AAPL"]["peso_inicial"] == pytest.approx(0.35)
    assert sum(fila["peso_actual"] for fila in resultado["activos"]) == pytest.approx(1.0)
    assert resultado["resumen"]["rebalanceos"] == 0
    assert resultado["avisos"] == []  # Los pesos empiezan el primer día con datos
    assert set(resultado["evolucion"]["series"]) == {"Cartera", "^GSPC (sintético)"}
    assert max(resultado["drawdown"]["series"]["Drawdown (%)"]) <= 0


@pytest.mark.parametrize(("rebalanceo", "esperados"), [("anual", 2), ("trimestral", 11)])
def test_crear_cartera_con_rebalanceo_periodico(app, rebalanceo, esperados):
    resultado = app.crear_cartera(PESOS, rebalanceo=rebalanceo)
    assert resultado["resumen"]["rebalanceos"] == esperados
    sin_rebalanceo = app.crear_cartera(PESOS)
    assert resultado["resumen"]["volatilidad_anualizada"] != pytest.approx(
        sin_rebalanceo["resumen"]["volatilidad_anualizada"], rel=1e-9
    )


def test_crear_cartera_rechaza_opciones_no_validas(app):
    with pytest.raises(ValueError, match="rebalanceo"):
        app.crear_cartera(PESOS, rebalanceo="semanal")
    with pytest.raises(ValueError, match="negativo"):
        app.crear_cartera({"AAPL": 110, "MSFT": -10, "JPM": 0})


def test_pesos_que_no_suman_100(app):
    with pytest.raises(ValueError, match="sumar 100"):
        app.crear_cartera({"AAPL": 50, "MSFT": 30, "JPM": 30})


def test_los_pasos_exigen_el_anterior():
    app = Aplicacion()
    with pytest.raises(ValueError, match="paso 1"):
        app.crear_cartera(PESOS)
    with pytest.raises(ValueError, match="paso 2"):
        app.monte_carlo()


def test_monte_carlo_con_comparacion(app_con_cartera):
    resultado = app_con_cartera.monte_carlo(
        n_simulaciones=300, horizonte=20, distribucion="t", grados_libertad=5
    )
    assert resultado["resumen"]["distribucion"] == "t"
    assert len(resultado["graficos"]) == 2
    assert resultado["graficos"][0]["imagen"].startswith("data:image/png;base64,")
    assert len(resultado["comparacion"]) == 3


def test_monte_carlo_con_supuestos_en_porcentaje(app_con_cartera):
    resultado = app_con_cartera.monte_carlo(
        n_simulaciones=200, horizonte=10, volatilidad=20, rentabilidad=5, comparar=False
    )
    volatilidades = resultado["resumen"]["volatilidad_anual_supuesta"]
    assert all(valor == pytest.approx(0.20) for valor in volatilidades.values())
    assert resultado["comparacion"] is None


def test_informe_html_y_markdown(app_con_cartera):
    html = app_con_cartera.informe(simulaciones=200)
    assert html["contenido"].startswith("<!DOCTYPE html>")
    markdown = app_con_cartera.informe(formato="markdown", incluir_montecarlo=False)
    assert markdown["contenido"].startswith("# Informe de cartera")
    with pytest.raises(ValueError, match="formato"):
        app_con_cartera.informe(formato="pdf")


def test_graficos_del_informe(app_con_cartera):
    assert len(app_con_cartera.graficos()["graficos"]) == 6


def test_la_pagina_se_sirve_y_marca_los_datos_sinteticos(servidor):
    with urllib.request.urlopen(servidor + "/") as respuesta:
        pagina = respuesta.read().decode("utf-8")
    assert "<title>market-toolkit</title>" in pagina
    assert 'id="sintetico" checked' in pagina


def test_api_completa(servidor):
    codigo, datos = llamar(servidor, "datos", {"tickers": "AAPL, MSFT, JPM", "sintetico": True})
    assert codigo == 200 and datos["activos"] == ["AAPL", "MSFT", "JPM"]
    codigo, cartera = llamar(servidor, "cartera", {"pesos": PESOS})
    assert codigo == 200 and cartera["resumen"]["observaciones"] > 100
    codigo, simulacion = llamar(
        servidor, "montecarlo", {"n_simulaciones": 200, "horizonte": 10, "comparar": False}
    )
    assert codigo == 200 and "var_95" in simulacion["resumen"]


def test_la_api_devuelve_los_errores_como_json(servidor):
    codigo, respuesta = llamar(servidor, "cartera", {"pesos": PESOS})
    assert codigo == 400 and "paso 1" in respuesta["error"]
    codigo, respuesta = llamar(servidor, "datos", {"parametro_inventado": 1})
    assert codigo == 400 and "TypeError" in respuesta["error"]
    codigo, _ = llamar(servidor, "no_existe", {})
    assert codigo == 404


def test_la_api_rechaza_peticiones_que_no_son_json(servidor):
    codigo, _ = llamar(servidor, "datos", {}, tipo="text/plain")
    assert codigo == 403


# ---------- Catálogo, buscador y datos ----------


def test_catalogo():
    catalogo = Aplicacion(sin_red=True).catalogo()
    assert catalogo["sin_red"] is True
    assert any(grupo["grupo"].startswith("IBEX") for grupo in catalogo["grupos"])
    assert {"ticker": "^GSPC", "nombre": "S&P 500"} in catalogo["indices"]
    assert set(catalogo["claves"]) == {"alphavantage", "fred"}


def test_buscar_en_el_catalogo_sin_red():
    resultado = Aplicacion().buscar("santander", local=True)
    assert resultado["resultados"][0]["ticker"] == "SAN.MC"
    assert Aplicacion().buscar("  ")["resultados"] == []


def test_buscar_en_yahoo(monkeypatch):
    class BusquedaFalsa:
        def __init__(self, texto, max_results=10):
            self.quotes = [
                {"symbol": "AAPL", "quoteType": "EQUITY", "longname": "Apple Inc."},
                {
                    "symbol": "APLE",
                    "quoteType": "EQUITY",
                    "shortname": "Apple Hospitality",
                    "exchDisp": "NYSE",
                },
                {"symbol": "AAPL240119C", "quoteType": "OPTION"},
            ]

    monkeypatch.setattr(aplicacion.yfinance, "Search", BusquedaFalsa)
    resultados = Aplicacion().buscar("apple")["resultados"]
    tickers = [resultado["ticker"] for resultado in resultados]
    assert tickers == ["AAPL", "APLE"]  # Sin repetir AAPL del catálogo ni opciones
    assert resultados[1]["grupo"] == "Acción · NYSE"


def test_buscar_sin_conexion(monkeypatch):
    def falla(texto, max_results=10):
        raise ConnectionError("sin red")

    monkeypatch.setattr(aplicacion.yfinance, "Search", falla)
    resultado = Aplicacion().buscar("micro")
    assert resultado["resultados"][0]["ticker"] == "MSFT"
    assert "catálogo" in resultado["aviso"]


def test_cargar_datos_devuelve_evolucion_y_estadisticos(app):
    resultado = app.cargar_datos(
        "AAPL, MSFT", indice="", inicio="2024-01-01", fin="2024-06-30", sintetico=True
    )
    assert resultado["indice"] is None
    assert set(resultado["evolucion"]["series"]) == {"AAPL", "MSFT"}
    assert resultado["evolucion"]["series"]["AAPL"][0] == 100
    assert all(serie["max_drawdown"] <= 0 for serie in resultado["series"])


def test_un_indice_no_puede_estar_en_la_cartera():
    with pytest.raises(ValueError, match="índice"):
        Aplicacion().cargar_datos("AAPL, ^IBEX", sintetico=True)


def test_materias_primas_sinteticas_con_su_nombre_de_alpha_vantage():
    app = Aplicacion()
    resultado = app.cargar_datos("AAPL, oro", sintetico=True)
    assert resultado["activos"] == ["AAPL", "GOLD"]
    tipos = {serie["activo"]: serie["tipo"] for serie in resultado["series"]}
    assert tipos["GOLD"] == "materia prima"


def serie_falsa(ticker, tipo=TipoActivo.ACCION):
    fechas = pd.bdate_range("2023-01-02", "2023-12-29")
    rng = np.random.default_rng(len(ticker))
    precios = pd.Series(
        100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(fechas)))), fechas, name=ticker
    )
    return FinancialSeries(precios, tipo, moneda="USD", proveedor="Prueba")


def test_cargar_datos_reales_con_proveedores_simulados(monkeypatch):
    pedidos = {}

    class YahooFalso:
        def __init__(self, tickers):
            pedidos["yahoo"] = tickers

        def download(self, inicio=None, fin=None):
            return [
                serie_falsa(t, TipoActivo.INDICE if t.startswith("^") else TipoActivo.ACCION)
                for t in pedidos["yahoo"]
            ]

    class AlphaVantageFalso:
        COMMODITIES = datos_demo.AlphaVantageProvider.COMMODITIES

        def __init__(self, tickers):
            pedidos["alphavantage"] = tickers

        def download(self, inicio=None, fin=None):
            return [serie_falsa(t, TipoActivo.COMMODITY) for t in pedidos["alphavantage"]]

    class MacroFalso:
        def __init__(self, tickers):
            pass

        def download(self, inicio=None, fin=None):
            fechas = pd.bdate_range("2023-01-02", periods=5)
            return [MacroSeries(pd.Series([5.0, 5.1, 5.2, 5.3, 5.25], fechas, name="DTB3"))]

    monkeypatch.setattr(datos_demo, "YahooFinanceProvider", YahooFalso)
    monkeypatch.setattr(datos_demo, "AlphaVantageProvider", AlphaVantageFalso)
    monkeypatch.setattr(datos_demo, "MacroProvider", MacroFalso)
    monkeypatch.setattr(datos_demo.config, "ALPHAVANTAGE_API_KEY", "clave")
    monkeypatch.setattr(datos_demo.config, "FRED_API_KEY", "clave")
    app = Aplicacion()
    resultado = app.cargar_datos("AAPL, ORO", indice="^GSPC", inicio="2023-01-01", fin="2023-12-31")
    assert pedidos == {"yahoo": ["AAPL", "^GSPC"], "alphavantage": ["GOLD"]}
    assert resultado["datos_reales"] is True
    assert resultado["tasa_desde_fred"] is True
    assert resultado["tasa_libre_riesgo"] == pytest.approx(5.25)
    assert resultado["activos"] == ["AAPL", "GOLD"]


def test_materias_primas_reales_sin_clave(monkeypatch):
    monkeypatch.setattr(datos_demo.config, "ALPHAVANTAGE_API_KEY", None)
    monkeypatch.setattr(datos_demo.config, "FRED_API_KEY", None)

    class YahooFalso:
        def __init__(self, tickers):
            self.tickers = tickers

        def download(self, inicio=None, fin=None):
            return [serie_falsa(t) for t in self.tickers]

    monkeypatch.setattr(datos_demo, "YahooFinanceProvider", YahooFalso)
    with pytest.raises(ValueError, match="ALPHAVANTAGE_API_KEY"):
        Aplicacion().cargar_datos("AAPL, GOLD", indice="")


def test_precios_csv(app):
    csv = app.precios_csv()["csv"].splitlines()
    assert csv[0] == "fecha,AAPL,MSFT,JPM,^GSPC"
    assert len(csv) > 700


def test_correlacion(app_con_cartera):
    resultado = app_con_cartera.correlacion(1)
    assert resultado["activos"] == ["AAPL", "MSFT", "JPM"]
    assert resultado["matriz"][0][0] == pytest.approx(1.0)
    assert resultado["avisos"] == []
    assert "más corto" in app_con_cartera.correlacion(10)["avisos"][0]


# ---------- Monte Carlo, informe y macro ----------


def test_monte_carlo_de_un_activo_con_supuestos(app_con_cartera):
    resultado = app_con_cartera.monte_carlo(
        objetivo="MSFT",
        n_simulaciones=200,
        horizonte=20,
        valor_inicial=1000,
        supuestos={"MSFT": {"volatilidad": 30}},
        comparar=False,
    )
    assert resultado["resumen"]["objetivo"] == "MSFT"
    assert resultado["resumen"]["valor_inicial"] == 1000
    assert resultado["resumen"]["volatilidad_anual_supuesta"] == {"MSFT": pytest.approx(0.30)}
    assert len(resultado["percentiles"]["etiquetas"]) == 21
    assert sum(resultado["histograma"]["conteos"]) == 200


def test_supuestos_por_activo_mandan_sobre_el_general(app_con_cartera):
    resultado = app_con_cartera.monte_carlo(
        n_simulaciones=100,
        horizonte=5,
        volatilidad=20,
        supuestos={"AAPL": {"volatilidad": 50}},
        comparar=False,
    )
    assert resultado["resumen"]["volatilidad_anual_supuesta"] == {
        "AAPL": pytest.approx(0.5),
        "MSFT": pytest.approx(0.2),
        "JPM": pytest.approx(0.2),
    }


def test_monte_carlo_de_un_ticker_que_no_existe(app_con_cartera):
    with pytest.raises(ValueError, match="XXXX"):
        app_con_cartera.monte_carlo(objetivo="XXXX")


def test_informe_con_umbrales(app_con_cartera):
    estricto = app_con_cartera.informe(
        formato="markdown", incluir_montecarlo=False, max_volatilidad=1, max_drawdown=1
    )["contenido"]
    normal = app_con_cartera.informe(formato="markdown", incluir_montecarlo=False)["contenido"]
    assert estricto.count("- ") > normal.count("- ")  # Más advertencias con umbrales estrictos


def test_macro_sin_clave(monkeypatch):
    monkeypatch.setattr(aplicacion.config, "FRED_API_KEY", None)
    with pytest.raises(ValueError, match="FRED_API_KEY"):
        Aplicacion().macro(["vix"])
    with pytest.raises(ValueError, match="al menos una"):
        Aplicacion().macro([])


def test_macro_con_fred_simulado(monkeypatch):
    class MacroFalso:
        def __init__(self, tickers):
            self.tickers = tickers

        def download(self, inicio=None, fin=None):
            fechas = pd.bdate_range("2024-01-01", periods=30)
            return [
                MacroSeries(
                    pd.Series(np.linspace(15, 20, 30), fechas, name="VIXCLS"),
                    unidad="índice",
                    metadatos={"nombre": "VIX"},
                )
            ]

    monkeypatch.setattr(aplicacion, "MacroProvider", MacroFalso)
    monkeypatch.setattr(aplicacion.config, "FRED_API_KEY", "clave")
    resultado = Aplicacion().macro(["vix"], inicio="2024-01-01", fin="2024-03-01")
    serie = resultado["series"][0]
    assert serie["id"] == "VIXCLS" and serie["nombre"] == "VIX"
    assert serie["ultimo_valor"] == pytest.approx(20)
    assert len(serie["grafico"]["series"]["VIXCLS"]) == 30


def test_api_catalogo_y_buscar(servidor):
    codigo, catalogo = llamar(servidor, "catalogo", {})
    assert codigo == 200 and catalogo["sin_red"] is True
    codigo, busqueda = llamar(servidor, "buscar", {"texto": "inditex", "local": True})
    assert codigo == 200 and busqueda["resultados"][0]["ticker"] == "ITX.MC"


def test_informe_con_rebalanceo_mensual():
    # Varios rebalanceos caen en fin de semana (por ejemplo, el 1-11-2026, domingo)
    app = Aplicacion()
    app.cargar_datos("AAPL, MSFT", inicio="2026-01-01", fin="2026-11-11", sintetico=True)
    app.crear_cartera({"AAPL": 50, "MSFT": 50}, rebalanceo="mensual")
    contenido = app.informe(formato="markdown", incluir_montecarlo=False)["contenido"]
    assert "**Último rebalanceo explícito:** 2026-11-01" in contenido
    assert "  - AAPL: 50.00%" in contenido


def test_web_y_report_dan_el_mismo_sharpe_y_drawdown(app_con_cartera):
    resumen = app_con_cartera.crear_cartera(PESOS)["resumen"]
    informe = app_con_cartera.informe(formato="markdown", incluir_montecarlo=False)["contenido"]
    assert f"**Sharpe anualizado:** {resumen['sharpe']:.2f}" in informe
    assert f"**Drawdown máximo:** {-resumen['max_drawdown']:.2%}" in informe


def test_datos_sinteticos_marcan_los_etf():
    resultado = Aplicacion().cargar_datos("SPY, AAPL", indice="", sintetico=True)
    tipos = {serie["activo"]: serie["tipo"] for serie in resultado["series"]}
    assert tipos == {"SPY": "ETF", "AAPL": "acción"}
