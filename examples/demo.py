"""
Demo de extremo a extremo de market-toolkit: descarga, cartera, Monte Carlo e informes.

Uso, desde la raíz del repositorio:
    python examples/demo.py                 # datos reales (Yahoo Finance y, si hay claves, más)
    python examples/demo.py --sin-red       # datos sintéticos, sin conexión
    python examples/demo.py --sin-ventanas  # no abre los gráficos, solo los guarda

Por defecto, los gráficos se abren en ventanas en el paso al que corresponden: la demo sigue
cuando se cierran. Además, todos los resultados se guardan en la carpeta `outputs/` (ignorada
por git):
    outputs/informe.md              informe en Markdown de la cartera
    outputs/informe.html            el mismo informe en HTML, con los gráficos incrustados
    outputs/graficos/*.png          gráficos del informe (plots_report)
    outputs/montecarlo/*.png        trayectorias y distribución de la simulación
"""

import sys
import warnings
from pathlib import Path

import matplotlib
import pandas as pd

MOSTRAR_GRAFICOS = "--sin-ventanas" not in sys.argv
if not MOSTRAR_GRAFICOS:
    matplotlib.use("Agg")  # Sin ventanas: los gráficos solo se guardan

import matplotlib.pyplot as plt  # noqa: E402

from market_toolkit import config, datos_demo  # noqa: E402
from market_toolkit.datos_demo import (  # noqa: E402
    FIN,
    INICIO,
    TIPO_LIBRE_RIESGO_POR_DEFECTO,
)
from market_toolkit.models import Portfolio  # noqa: E402
from market_toolkit.simulation import MonteCarlo  # noqa: E402

CARPETA_SALIDA = Path("outputs")
ACCIONES = ["AAPL", "MSFT", "JPM"]  # Acciones de Yahoo Finance (en USD)
INDICE = "^GSPC"  # S&P 500, como referencia
PESOS = {"AAPL": 0.35, "MSFT": 0.35, "JPM": 0.30}


def titulo(texto):
    print()
    print("=" * 70)
    print(texto)
    print("=" * 70)


def avisar_ventanas(cantidad):
    print()
    print(f"Se abren {cantidad} gráficos. Cierra las ventanas para continuar con la demo...")


def mostrar_resumen(serie):
    resumen = serie.resumen()
    print(
        f"  {resumen['activo']:<8} {str(resumen['nombre'])[:28]:<28} "
        f"{resumen['tipo']:<14} {resumen['proveedor']:<14} "
        f"rent. {resumen['rentabilidad_anualizada']:>7.2%}   "
        f"vol. {resumen['volatilidad_anualizada']:>7.2%}"
    )


# ---------------------------------------------------------------------------
# 1. Ingesta: varias fuentes, el mismo tipo de objeto (FinancialSeries)
# ---------------------------------------------------------------------------
def descargar_datos_reales():
    """Descarga acciones e índice de Yahoo y, si hay claves en el .env, oro y tipo libre."""
    print("Yahoo Finance: acciones e índice...")
    tickers = list(ACCIONES)
    if config.ALPHAVANTAGE_API_KEY:
        print("Alpha Vantage: oro...")
        tickers.append("ORO")
    else:
        print("Alpha Vantage: sin ALPHAVANTAGE_API_KEY en el .env, se omite.")
    if config.FRED_API_KEY:
        print("FRED: letras del Tesoro a 3 meses (DTB3)...")
    else:
        print("FRED: sin FRED_API_KEY en el .env, se usa un tipo libre de riesgo fijo.")
    series, tasa = datos_demo.descargar_reales(tickers, INDICE, INICIO, FIN)
    if tasa is None:
        tasa = TIPO_LIBRE_RIESGO_POR_DEFECTO
    return series, tasa


def generar_datos_sinteticos():
    """Genera series con el mismo formato que las descargadas, para usar la demo sin red."""
    series = datos_demo.generar_sinteticos(ACCIONES, INDICE, INICIO, FIN)
    return series, TIPO_LIBRE_RIESGO_POR_DEFECTO


def main():
    CARPETA_SALIDA.mkdir(exist_ok=True)

    titulo("1. Ingesta de datos")
    if "--sin-red" in sys.argv:
        series, tipo_libre_riesgo = generar_datos_sinteticos()
    else:
        try:
            series, tipo_libre_riesgo = descargar_datos_reales()
        except Exception as error:  # Sin red o API caída: la demo sigue con datos sintéticos
            print(f"No se han podido descargar los datos ({type(error).__name__}: {error}).")
            print("Se continúa con datos sintéticos.")
            series, tipo_libre_riesgo = generar_datos_sinteticos()

    print()
    print("Series obtenidas (todas son FinancialSeries con estadísticos automáticos):")
    for serie in series:
        mostrar_resumen(serie)
    print(f"Tipo libre de riesgo: {tipo_libre_riesgo:.2%}")

    # -----------------------------------------------------------------------
    # 2. Cartera: solo con las acciones; el índice queda como referencia
    # -----------------------------------------------------------------------
    titulo("2. Cartera")
    acciones = []
    indice = None
    for serie in series:
        if serie.activo in PESOS:
            acciones.append(serie)
        elif serie.activo == INDICE:
            indice = serie  # El índice no entra en la cartera: es la referencia
    pesos = pd.DataFrame(PESOS, index=[pd.Timestamp(INICIO)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # Avisos de ajuste de fechas
        cartera = Portfolio(acciones, pesos)
    resumen = cartera.resumen()
    print(f"Periodo: {resumen['inicio']} a {resumen['fin']} ({resumen['observaciones']} sesiones)")
    print(f"Rentabilidad anualizada: {resumen['rentabilidad_anualizada']:.2%}")
    print(f"Volatilidad anualizada:  {resumen['volatilidad_anualizada']:.2%}")
    print("Pesos al inicio y al cierre (sin rebalanceo, los pesos derivan):")
    for activo in PESOS:
        print(f"  {activo:<6} {PESOS[activo]:>7.2%} -> {resumen['pesos_actuales'][activo]:>7.2%}")

    # -----------------------------------------------------------------------
    # 3. Simulación de Monte Carlo de la cartera
    # -----------------------------------------------------------------------
    titulo("3. Monte Carlo (1 año, 5.000 simulaciones)")
    simulacion = MonteCarlo(cartera, n_simulaciones=5000, semilla=42, guardar_graficos=False)
    simulacion.guardar_graficos(carpeta=CARPETA_SALIDA / "montecarlo")
    resultado = simulacion.resumen()
    print(f"Valor inicial:            {resultado['valor_inicial']:.2f}")
    print(f"Valor final mediano:      {resultado['valor_final_mediano']:.2f}")
    print(f"Probabilidad de pérdida:  {resultado['probabilidad_perdida']:.1%}")
    print(f"VaR 95 %:                 {resultado['var_95']:.1%}")
    print(f"CVaR 95 %:                {resultado['cvar_95']:.1%}")
    print(f"Gráficos guardados en: {CARPETA_SALIDA / 'montecarlo'}")
    if MOSTRAR_GRAFICOS:
        avisar_ventanas(2)
        simulacion.graficar()  # Trayectorias y distribución del valor final
        plt.close("all")

    # La normal subestima las caídas extremas: se compara con t de Student y bootstrap
    print()
    print("Riesgo de cola según la distribución (1 año):")
    comparacion = MonteCarlo.comparar_distribuciones(cartera, n_simulaciones=5000)
    cabecera = ["VaR 95 %", "CVaR 95 %", "VaR 99 %", "CVaR 99 %"]
    print(f"  {'Distribución':<26} " + " ".join(f"{texto:>10}" for texto in cabecera))
    for distribucion, fila in comparacion.iterrows():
        valores = [fila["var_95"], fila["cvar_95"], fila["var_99"], fila["cvar_99"]]
        print(f"  {distribucion:<26} " + " ".join(f"{valor:>10.1%}" for valor in valores))

    # -----------------------------------------------------------------------
    # 4. Informes: Markdown y gráficos
    # -----------------------------------------------------------------------
    titulo("4. Informes")
    opciones_informe = {
        "tasa_libre_riesgo": tipo_libre_riesgo,
        "benchmark": indice,
        "incluir_montecarlo": True,
    }
    informe = cartera.report(ruta=str(CARPETA_SALIDA / "informe.md"), **opciones_informe)
    cartera.report(formato="html", ruta=str(CARPETA_SALIDA / "informe.html"), **opciones_informe)
    print(f"Informe Markdown: {CARPETA_SALIDA / 'informe.md'}")
    print(f"Informe HTML (ábrelo en el navegador): {CARPETA_SALIDA / 'informe.html'}")
    print()
    print(informe)

    # Evolución, drawdown, pesos, riesgo-rentabilidad, contribución y correlación
    print()
    print(f"Gráficos del informe guardados en: {CARPETA_SALIDA / 'graficos'}")
    if MOSTRAR_GRAFICOS:
        avisar_ventanas(6)
    cartera.plots_report(
        mostrar=MOSTRAR_GRAFICOS, carpeta=CARPETA_SALIDA / "graficos", benchmark=indice
    )
    plt.close("all")
    print()
    print(f"Demo terminada. Todos los resultados están en la carpeta {CARPETA_SALIDA}/")


if __name__ == "__main__":
    main()
