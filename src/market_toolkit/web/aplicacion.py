"""
Lógica de la interfaz web. La clase `Aplicacion` guarda el estado de la sesión (datos, cartera)
y tiene un método por cada acción de la página. Cada método devuelve un diccionario listo para
convertirse en JSON, así que se puede probar sin servidor ni navegador.
"""

import math
import warnings
from enum import Enum

import numpy as np
import pandas as pd
import yfinance
from matplotlib.figure import Figure

import market_toolkit.analytics as analytics
from market_toolkit import config, datos_demo
from market_toolkit.datos_demo import FIN, INICIO, TIPO_LIBRE_RIESGO_POR_DEFECTO
from market_toolkit.models import FinancialSeries, Portfolio
from market_toolkit.models.informe import valor_cartera
from market_toolkit.providers.providers import AlphaVantageProvider, MacroProvider
from market_toolkit.reporting.html import TITULOS_GRAFICOS, figura_a_base64
from market_toolkit.simulation.montecarlo import COLORES, MonteCarlo
from market_toolkit.web import catalogo

MAX_PUNTOS_GRAFICO = 600  # Con más sesiones, los gráficos de la página usan datos semanales
# Rebalanceo periódico -> frecuencia de pandas para las fechas de los pesos
FRECUENCIAS_REBALANCEO = {"nunca": None, "mensual": "MS", "trimestral": "QS", "anual": "YS"}
# Tipos de Yahoo Finance que admite el buscador
TIPOS_BUSCADOR = {"EQUITY": "Acción", "ETF": "ETF", "INDEX": "Índice"}


def limpiar_json(valor):
    """Convierte los resultados del toolkit (numpy, pandas, enums) en tipos que admite JSON."""
    if isinstance(valor, dict):
        return {str(clave): limpiar_json(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, list | tuple):
        return [limpiar_json(elemento) for elemento in valor]
    if isinstance(valor, pd.Series):
        return limpiar_json(valor.to_dict())
    if isinstance(valor, pd.Timestamp):
        return str(valor.date())
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, bool | np.bool_):
        return bool(valor)
    if isinstance(valor, int | np.integer):
        return int(valor)
    if isinstance(valor, float | np.floating):
        valor = float(valor)
        return None if math.isnan(valor) or math.isinf(valor) else valor
    if valor is None or isinstance(valor, str):
        return valor
    return str(valor)  # Fechas (date) y cualquier otro tipo


def separar_tickers(texto) -> list[str]:
    """Convierte 'aapl, msft' (o una lista) en ['AAPL', 'MSFT'] sin repetidos."""
    if isinstance(texto, str):
        texto = texto.replace(";", ",").replace(" ", ",").split(",")
    tickers = []
    for ticker in texto:
        ticker = str(ticker).strip().upper()
        if ticker != "" and ticker not in tickers:
            tickers.append(ticker)
    return tickers


def a_fraccion(porcentaje):
    """Pasa un porcentaje (7 = 7 %) a tanto por uno. `None` y la cadena vacía no cambian."""
    if porcentaje is None or porcentaje == "":
        return None
    return float(porcentaje) / 100


def a_numero(valor, tipo):
    """Convierte a `int` o `float`, dejando `None` si el campo está vacío."""
    if valor is None or valor == "":
        return None
    return tipo(valor)


def imagen(figura: Figure) -> str:
    """Figura de matplotlib en una URL de datos (PNG en base64) para una etiqueta <img>."""
    return "data:image/png;base64," + figura_a_base64(figura)


def datos_grafico(datos: pd.DataFrame) -> dict:
    """
    Prepara un DataFrame para los gráficos interactivos de la página: fechas y una lista de
    valores por columna. Si hay muchas sesiones, se pasa a datos semanales.
    """
    if isinstance(datos.index, pd.DatetimeIndex) and len(datos) > MAX_PUNTOS_GRAFICO:
        datos = datos.resample("W-FRI").last()
    datos = datos.dropna(how="all")
    series = {}
    for columna in datos.columns:
        valores = []
        for valor in datos[columna]:
            valores.append(None if pd.isna(valor) else round(float(valor), 4))
        series[str(columna)] = valores
    etiquetas = []
    for fecha in datos.index:
        etiquetas.append(str(fecha.date()) if isinstance(fecha, pd.Timestamp) else str(fecha))
    return {"etiquetas": etiquetas, "series": series}


def avisos_de(registro) -> list[str]:
    """Textos de los avisos capturados con `warnings.catch_warnings(record=True)`, sin repetir."""
    textos = []
    for aviso in registro:
        texto = str(aviso.message)
        if texto not in textos:
            textos.append(texto)
    return textos


class Aplicacion:
    """Estado de la sesión y acciones de la interfaz web."""

    def __init__(self, sin_red: bool = False):
        self.sin_red = sin_red
        self.series: list[FinancialSeries] = []
        self.activos: list[str] = []
        self.indice: FinancialSeries | None = None
        self.cartera: Portfolio | None = None
        self.inicio = INICIO
        self.fin = FIN
        self.datos_reales = False
        self.tasa_libre_riesgo = TIPO_LIBRE_RIESGO_POR_DEFECTO

    # ------------------------------------------------------------------
    # Catálogo y buscador
    # ------------------------------------------------------------------
    def catalogo(self):
        """Activos e índices sugeridos, series macro y qué claves hay en el `.env`."""
        grupos = []
        for grupo, activos in catalogo.ACTIVOS.items():
            grupos.append(
                {
                    "grupo": grupo,
                    "activos": [{"ticker": ticker, "nombre": nombre} for ticker, nombre in activos],
                }
            )
        return {
            "grupos": grupos,
            "indices": [
                {"ticker": ticker, "nombre": nombre} for ticker, nombre in catalogo.INDICES
            ],
            "macro": [
                {"alias": alias, "nombre": nombre}
                for alias, nombre in catalogo.SERIES_MACRO.items()
            ],
            "claves": {
                "alphavantage": bool(config.ALPHAVANTAGE_API_KEY),
                "fred": bool(config.FRED_API_KEY),
            },
            "sin_red": self.sin_red,
        }

    def buscar(self, texto, local=False):
        """
        Busca activos por nombre o ticker: primero en el catálogo y, si `local` es `False`, también
        en Yahoo Finance (acciones, ETF e índices).
        """
        texto = str(texto or "").strip()
        if texto == "":
            return {"resultados": [], "aviso": None}
        resultados = catalogo.buscar_en_catalogo(texto)
        aviso = None
        if not local:
            try:
                cotizaciones = yfinance.Search(texto, max_results=10).quotes
            except Exception:  # Sin conexión: se usa solo el catálogo
                cotizaciones = []
                aviso = "No se ha podido buscar en Yahoo Finance: solo se muestra el catálogo."
            for cotizacion in cotizaciones:
                tipo = cotizacion.get("quoteType")
                ticker = cotizacion.get("symbol")
                if tipo not in TIPOS_BUSCADOR or ticker is None:
                    continue
                repetido = False
                for resultado in resultados:
                    if resultado["ticker"] == ticker:
                        repetido = True
                if repetido:
                    continue
                nombre = cotizacion.get("longname") or cotizacion.get("shortname") or ticker
                grupo = TIPOS_BUSCADOR[tipo]
                if cotizacion.get("exchDisp"):
                    grupo = grupo + " · " + cotizacion["exchDisp"]
                resultados.append({"ticker": ticker, "nombre": nombre, "grupo": grupo})
        return {"resultados": resultados[:15], "aviso": aviso}

    # ------------------------------------------------------------------
    # 1. Datos
    # ------------------------------------------------------------------
    def cargar_datos(self, tickers, indice="^GSPC", inicio=INICIO, fin=FIN, sintetico=False):
        """
        Descarga (o genera) las series de los activos y del índice de referencia.
        :param tickers: Tickers de los activos, separados por comas. Las materias primas (GOLD,
            SILVER, BRENT u ORO, PLATA, PETRÓLEO) se descargan de Alpha Vantage.
        :param indice: Ticker del índice de referencia (no entra en la cartera). Puede ir vacío.
        :param inicio: Fecha de inicio, `AAAA-MM-DD`.
        :param fin: Fecha de fin, `AAAA-MM-DD`.
        :param sintetico: `True` para usar datos sintéticos, sin conexión.
        """
        tickers = separar_tickers(tickers)
        # Las materias primas se guardan con el nombre que usa Alpha Vantage (ORO -> GOLD)
        tickers = [AlphaVantageProvider.COMMODITIES.get(ticker, ticker) for ticker in tickers]
        tickers = separar_tickers(tickers)
        indice = str(indice or "").strip().upper()
        if len(tickers) < 2:
            raise ValueError("Elige al menos dos activos para formar una cartera.")
        for ticker in tickers:
            if ticker.startswith("^"):
                raise ValueError(
                    f"{ticker} es un índice: no puede formar parte de la cartera. Úsalo como "
                    f"índice de referencia o elige un ETF que lo replique."
                )
        if indice in tickers:
            raise ValueError("El índice de referencia no puede ser también un activo.")
        if pd.Timestamp(inicio) >= pd.Timestamp(fin):
            raise ValueError("La fecha de inicio debe ser anterior a la de fin.")

        tasa = None
        with warnings.catch_warnings(record=True) as registro:
            warnings.simplefilter("always")
            if sintetico:
                series = datos_demo.generar_sinteticos(
                    tickers, indice, inicio, fin, etfs=catalogo.tickers_del_grupo("ETF")
                )
            else:
                series, tasa = datos_demo.descargar_reales(tickers, indice, inicio, fin)
        activos = []
        indice_encontrado = None
        for serie in series:
            if serie.activo in tickers:
                activos.append(serie.activo)
            elif indice != "" and serie.activo == indice:
                indice_encontrado = serie
        if len(activos) < 2:
            raise ValueError("Se han obtenido menos de dos activos. Revisa los tickers.")
        self.series = series
        self.activos = activos
        self.indice = indice_encontrado
        self.cartera = None  # Con datos nuevos, la cartera anterior ya no vale
        self.inicio = inicio
        self.fin = fin
        self.datos_reales = not sintetico
        self.tasa_libre_riesgo = TIPO_LIBRE_RIESGO_POR_DEFECTO if tasa is None else tasa

        resumenes = []
        for serie in series:
            resumen = serie.resumen()
            resumen["max_drawdown"] = -analytics.drawdown_maximo(serie.serie_temporal)
            resumen["ultimo_precio"] = float(serie.serie_temporal.iloc[-1])
            resumen["en_cartera"] = serie.activo in activos
            resumenes.append(resumen)
        return limpiar_json(
            {
                "series": resumenes,
                "activos": self.activos,
                "indice": None if self.indice is None else self.indice.activo,
                "datos_reales": self.datos_reales,
                "tasa_libre_riesgo": self.tasa_libre_riesgo * 100,
                "tasa_desde_fred": tasa is not None,
                "evolucion": datos_grafico(analytics.base_100(self._tabla_precios())),
                "avisos": avisos_de(registro),
            }
        )

    def _tabla_precios(self) -> pd.DataFrame:
        """Precios de todas las series cargadas, una columna por serie."""
        if not self.series:
            raise ValueError("Primero carga los datos (paso 1).")
        columnas = {}
        for serie in self.series:
            columnas[serie.activo] = serie.serie_temporal
        return pd.DataFrame(columnas).sort_index()

    def precios_csv(self):
        """Los precios cargados en formato CSV, para descargarlos desde la página."""
        tabla = self._tabla_precios()
        tabla.index.name = "fecha"
        return {"nombre": "precios.csv", "csv": tabla.to_csv()}

    # ------------------------------------------------------------------
    # 2. Cartera
    # ------------------------------------------------------------------
    def crear_cartera(self, pesos, rebalanceo="nunca", alineacion="eliminacion"):
        """
        Crea la cartera con los pesos iniciales indicados.
        :param pesos: Diccionario {ticker: peso en %}. Tienen que sumar 100.
        :param rebalanceo: `nunca`, `mensual`, `trimestral` o `anual`: cada cuánto se vuelve a
            los pesos iniciales. Sin rebalanceo, los pesos derivan con los precios.
        :param alineacion: `eliminacion` o `relleno`, para las fechas en que no cotizan todos.
        """
        if not self.activos:
            raise ValueError("Primero carga los datos (paso 1).")
        if rebalanceo not in FRECUENCIAS_REBALANCEO:
            raise ValueError("El rebalanceo debe ser: " + ", ".join(FRECUENCIAS_REBALANCEO) + ".")
        total = 0.0
        for ticker in self.activos:
            peso = float(pesos.get(ticker, 0))
            if peso < 0:
                raise ValueError(f"El peso de {ticker} no puede ser negativo.")
            total += peso
        if abs(total - 100) > 0.011:
            raise ValueError(f"Los pesos deben sumar 100 %, ahora suman {total:.2f} %.")
        # Se reparte entre el total para que sumen 1 exacto (el margen de 0.011 es de redondeo)
        iniciales = {ticker: float(pesos.get(ticker, 0)) / total for ticker in self.activos}

        # Una fila de pesos por cada rebalanceo, siempre con los pesos iniciales. La primera, el
        # primer día en que cotizan todos los activos
        acciones = [serie for serie in self.series if serie.activo in self.activos]
        primer_dia = acciones[0].serie_temporal.index[0]
        for serie in acciones:
            primer_dia = max(primer_dia, serie.serie_temporal.index[0])
        fechas = [primer_dia]
        frecuencia = FRECUENCIAS_REBALANCEO[rebalanceo]
        if frecuencia is not None:
            for fecha in pd.date_range(self.inicio, self.fin, freq=frecuencia):
                if fecha > fechas[0]:
                    fechas.append(fecha)
        filas = {ticker: [peso] * len(fechas) for ticker, peso in iniciales.items()}
        tabla_pesos = pd.DataFrame(filas, index=pd.DatetimeIndex(fechas))

        with warnings.catch_warnings(record=True) as registro:
            warnings.simplefilter("always")
            self.cartera = Portfolio(acciones, tabla_pesos, alineacion_temporal=alineacion)
        cartera = self.cartera

        # Evolución en base 100 frente al índice y drawdown
        inicio = cartera.precio_activos.index[0]
        valor = valor_cartera(cartera.rendimiento, inicio)
        evolucion = pd.DataFrame({"Cartera": valor})
        if self.indice is not None:
            precios_indice = self.indice.serie_temporal.reindex(valor.index).ffill().bfill()
            evolucion[self.indice.nombre] = analytics.base_100(precios_indice)
        drawdown = pd.DataFrame({"Drawdown (%)": analytics.caidas(valor) * 100})
        pesos_cartera = cartera.pesos.dropna(how="all") * 100

        activos = []
        for ticker in cartera.precio_activos.columns:
            activos.append(
                {
                    "activo": ticker,
                    "peso_inicial": iniciales[ticker],
                    "peso_actual": float(cartera.pesos_actuales[ticker]),
                    "rentabilidad_anualizada": cartera.metadatos_activos.loc[
                        "rentabilidad_anualizada", ticker
                    ],
                    "volatilidad_anualizada": cartera.metadatos_activos.loc[
                        "volatilidad_anualizada", ticker
                    ],
                }
            )
        resumen = cartera.resumen()
        # Las mismas fórmulas que usa Portfolio.report()
        resumen["sharpe"] = analytics.ratio_sharpe(cartera.rendimiento, self.tasa_libre_riesgo)
        resumen["max_drawdown"] = -analytics.drawdown_maximo(valor)
        resumen["rentabilidad_total"] = float(valor.iloc[-1] / 100 - 1)
        resumen["rebalanceos"] = len(fechas) - 1
        return limpiar_json(
            {
                "resumen": resumen,
                "activos": activos,
                "evolucion": datos_grafico(evolucion),
                "drawdown": datos_grafico(drawdown),
                "pesos": datos_grafico(pesos_cartera),
                "avisos": avisos_de(registro),
            }
        )

    def _exigir_cartera(self) -> Portfolio:
        if self.cartera is None:
            raise ValueError("Primero crea la cartera (paso 2).")
        return self.cartera

    def correlacion(self, anios=1):
        """Matriz de correlaciones de los rendimientos diarios de los últimos `anios` años."""
        cartera = self._exigir_cartera()
        with warnings.catch_warnings(record=True) as registro:
            warnings.simplefilter("always")
            matriz = cartera.correlacion(float(anios), guardar=False)
        return limpiar_json(
            {
                "activos": list(matriz.columns),
                "matriz": [list(matriz.loc[fila]) for fila in matriz.index],
                "avisos": avisos_de(registro),
            }
        )

    # ------------------------------------------------------------------
    # 3. Monte Carlo
    # ------------------------------------------------------------------
    def _objetivo(self, objetivo):
        """La cartera o una de las series cargadas, según el valor del selector."""
        if objetivo in (None, "", "cartera"):
            return self._exigir_cartera()
        for serie in self.series:
            if serie.activo == objetivo:
                return serie
        raise ValueError(f"No hay ninguna serie cargada con el ticker {objetivo}.")

    @staticmethod
    def _supuesto(general, por_activo, clave, activos):
        """
        Junta el supuesto general (para todos) y los de cada activo (que mandan sobre el
        general). Devuelve `None` si no se ha indicado nada, para usar el histórico.
        """
        general = a_fraccion(general)
        valores = {}
        for activo in activos:
            dato = None
            if por_activo and activo in por_activo:
                dato = por_activo[activo].get(clave)
            if dato is not None and dato != "":
                valores[activo] = float(dato) / 100
            elif general is not None:
                valores[activo] = general
        if not valores:
            return None
        return valores

    def monte_carlo(
        self,
        objetivo="cartera",
        n_simulaciones=5000,
        horizonte=252,
        distribucion="normal",
        grados_libertad=None,
        rebalanceo=False,
        semilla=42,
        rentabilidad=None,
        volatilidad=None,
        supuestos=None,
        valor_inicial=None,
        comparar=True,
    ):
        """
        Simula la cartera o un activo. Devuelve el resumen, los percentiles de cada sesión (para
        el abanico interactivo), los dos gráficos y, si se pide, la comparación del riesgo de cola
        entre la normal, la t de Student y el bootstrap.
        :param rentabilidad: Rentabilidad anual supuesta en %, para todos los activos.
        :param volatilidad: Volatilidad anual supuesta en %, para todos los activos.
        :param supuestos: Supuestos por activo {ticker: {"rentabilidad": %, "volatilidad": %}},
            que mandan sobre los generales.
        """
        elegido = self._objetivo(objetivo)
        if isinstance(elegido, Portfolio):
            activos = list(elegido.precio_activos.columns)
        else:
            activos = [elegido.activo]
        rentabilidades = self._supuesto(rentabilidad, supuestos, "rentabilidad", activos)
        volatilidades = self._supuesto(volatilidad, supuestos, "volatilidad", activos)
        if isinstance(elegido, FinancialSeries):  # Un activo: el supuesto es un número
            if rentabilidades is not None:
                rentabilidades = rentabilidades[elegido.activo]
            if volatilidades is not None:
                volatilidades = volatilidades[elegido.activo]
        opciones = {"rentabilidad": rentabilidades, "volatilidad": volatilidades}
        if isinstance(elegido, Portfolio):
            opciones["rebalanceo"] = bool(rebalanceo)
        n_simulaciones = int(n_simulaciones)
        horizonte = int(horizonte)
        semilla = a_numero(semilla, int)
        simulacion = MonteCarlo(
            elegido,
            n_simulaciones=n_simulaciones,
            horizonte=horizonte,
            semilla=semilla,
            guardar_graficos=False,
            distribucion=distribucion,
            grados_libertad=a_numero(grados_libertad, float),
            valor_inicial=a_numero(valor_inicial, float),
            **opciones,
        )
        fondo = COLORES["superficie"]
        trayectorias = simulacion._dibujar_trayectorias(
            Figure(figsize=(11, 6), facecolor=fondo), 50
        )
        histograma = simulacion._dibujar_distribucion(Figure(figsize=(10, 5.5), facecolor=fondo))
        percentiles = simulacion.percentiles()
        if len(percentiles) > MAX_PUNTOS_GRAFICO:  # Horizontes largos: una de cada n sesiones
            paso = len(percentiles) // MAX_PUNTOS_GRAFICO + 1
            percentiles = percentiles.iloc[::paso]
        finales = simulacion.valores_finales
        histograma_valores, bordes = np.histogram(finales, bins=40)
        resultado = {
            "resumen": simulacion.resumen(),
            "var_99": simulacion.var(0.99),
            "cvar_99": simulacion.cvar(0.99),
            "percentiles": datos_grafico(percentiles),
            "histograma": {
                "conteos": list(histograma_valores),
                "bordes": list(bordes),
                "valor_inicial": simulacion.valor_inicial,
            },
            "graficos": [
                {"titulo": "Trayectorias simuladas", "imagen": imagen(trayectorias)},
                {"titulo": "Distribución del valor final", "imagen": imagen(histograma)},
            ],
            "comparacion": None,
        }
        if comparar:
            tabla = MonteCarlo.comparar_distribuciones(
                elegido,
                n_simulaciones=n_simulaciones,
                horizonte=horizonte,
                semilla=semilla,
                valor_inicial=a_numero(valor_inicial, float),
                **opciones,
            )
            resultado["comparacion"] = [
                {"distribucion": nombre, **fila.to_dict()} for nombre, fila in tabla.iterrows()
            ]
        return limpiar_json(resultado)

    # ------------------------------------------------------------------
    # 4. Informes y gráficos
    # ------------------------------------------------------------------
    def informe(
        self,
        formato="html",
        tasa_libre_riesgo=None,
        usar_indice=True,
        incluir_montecarlo=True,
        simulaciones=5000,
        incluir_graficos=True,
        max_volatilidad=None,
        max_drawdown=None,
        min_sharpe=None,
        max_concentracion=None,
        max_correlacion=None,
        confianza_es=None,
    ):
        """
        Genera el informe de la cartera en Markdown o en HTML.
        :param tasa_libre_riesgo: Tipo libre de riesgo anual en %. Si es `None`, el de los datos.
        :param max_volatilidad: Umbrales de las advertencias, en %. Si son `None`, los de
            `Portfolio.report()`. `min_sharpe` es un número, no un porcentaje.
        """
        cartera = self._exigir_cartera()
        if formato not in ("html", "markdown"):
            raise ValueError("El formato debe ser 'html' o 'markdown'.")
        tasa = a_fraccion(tasa_libre_riesgo)
        if tasa is not None:
            self.tasa_libre_riesgo = tasa
        umbrales = {
            "max_volatilidad": a_fraccion(max_volatilidad),
            "max_drawdown": a_fraccion(max_drawdown),
            "min_sharpe": a_numero(min_sharpe, float),
            "max_concentracion": a_fraccion(max_concentracion),
            "max_correlacion": a_fraccion(max_correlacion),
            "confianza_es": a_fraccion(confianza_es),
        }
        opciones = {}
        for nombre, valor in umbrales.items():
            if valor is not None:
                opciones[nombre] = valor
        texto = cartera.report(
            tasa_libre_riesgo=self.tasa_libre_riesgo,
            benchmark=self.indice if usar_indice else None,
            incluir_montecarlo=bool(incluir_montecarlo),
            simulaciones_montecarlo=int(simulaciones),
            formato=formato,
            incluir_graficos=bool(incluir_graficos),
            **opciones,
        )
        return {"formato": formato, "contenido": texto}

    def graficos(self, usar_indice=True):
        """Los seis gráficos del informe (evolución, drawdown, pesos, riesgo...)."""
        cartera = self._exigir_cartera()
        figuras = cartera.plots_report(
            mostrar=False, guardar=False, benchmark=self.indice if usar_indice else None
        )
        return {
            "graficos": [
                {"titulo": TITULOS_GRAFICOS.get(nombre, nombre), "imagen": imagen(figura)}
                for nombre, figura in figuras.items()
            ]
        }

    # ------------------------------------------------------------------
    # 5. Datos macro (FRED)
    # ------------------------------------------------------------------
    def macro(self, series, inicio=INICIO, fin=FIN):
        """
        Descarga series macroeconómicas de FRED (necesita FRED_API_KEY en el `.env`).
        :param series: Alias de `MacroProvider.SERIES` o IDs de FRED.
        """
        if not series:
            raise ValueError("Elige al menos una serie macro.")
        if not config.FRED_API_KEY:
            raise ValueError("Para descargar series de FRED hace falta FRED_API_KEY en el .env.")
        with warnings.catch_warnings(record=True) as registro:
            warnings.simplefilter("always")
            descargadas = MacroProvider(list(series)).download(inicio=inicio, fin=fin)
        resultado = []
        for serie in descargadas:
            identificador = str(serie.serie_temporal.name)
            datos = serie.serie_temporal.dropna().to_frame(identificador)
            resultado.append(
                {
                    "id": identificador,
                    "nombre": serie.nombre,
                    "unidad": serie.unidad,
                    "ultimo_valor": serie.ultimo_valor,
                    "media": serie.media,
                    "desviacion_tipica": serie.desviacion_tipica,
                    "inicio": serie.serie_temporal.index[0],
                    "fin": serie.serie_temporal.index[-1],
                    "grafico": datos_grafico(datos),
                }
            )
        return limpiar_json({"series": resultado, "avisos": avisos_de(registro)})
