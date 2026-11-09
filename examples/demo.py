"""
Demo de extremo a extremo de market-toolkit: descarga, cartera, Monte Carlo e informes.

Uso, desde la raíz del repositorio:
    python examples/demo.py              # datos reales (Yahoo Finance y, si hay claves, más)
    python examples/demo.py --sin-red    # datos sintéticos, sin conexión
    python examples/demo.py --mostrar    # además, muestra los gráficos por pantalla

Los resultados se guardan en la carpeta `outputs/` (ignorada por git):
    outputs/informe.md              informe en Markdown de la cartera
    outputs/graficos/*.png          gráficos del informe (plots_report)
    outputs/montecarlo/*.png        trayectorias y distribución de la simulación
"""

import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

if "--mostrar" not in sys.argv:
    matplotlib.use("Agg")  # Sin ventanas: los gráficos solo se guardan

import matplotlib.pyplot as plt  # noqa: E402

from market_toolkit import config  # noqa: E402
from market_toolkit.models import FinancialSeries, Portfolio, TipoActivo  # noqa: E402
from market_toolkit.simulation import MonteCarlo  # noqa: E402

CARPETA_SALIDA = Path("outputs")
ACCIONES = ["AAPL", "MSFT", "JPM"]  # Acciones de Yahoo Finance (en USD)
INDICE = "^GSPC"  # S&P 500, como referencia
INICIO = "2022-01-01"
FIN = "2024-12-31"
PESOS = {"AAPL": 0.35, "MSFT": 0.35, "JPM": 0.30}
TIPO_LIBRE_RIESGO_POR_DEFECTO = 0.04  # Si no hay clave de FRED


def titulo(texto):
    print()
    print("=" * 70)
    print(texto)
    print("=" * 70)


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
    from market_toolkit.providers.providers import (
        AlphaVantageProvider,
        MacroProvider,
        YahooFinanceProvider,
    )

    print("Yahoo Finance: acciones e índice...")
    series = YahooFinanceProvider(ACCIONES + [INDICE]).download(inicio=INICIO, fin=FIN)

    if config.ALPHAVANTAGE_API_KEY:
        print("Alpha Vantage: oro...")
        series = series + AlphaVantageProvider(["ORO"]).download(inicio=INICIO, fin=FIN)
    else:
        print("Alpha Vantage: sin ALPHAVANTAGE_API_KEY en el .env, se omite.")

    tipo_libre_riesgo = TIPO_LIBRE_RIESGO_POR_DEFECTO
    if config.FRED_API_KEY:
        print("FRED: letras del Tesoro a 3 meses (DTB3)...")
        letras = MacroProvider(["DTB3"]).download(inicio=INICIO, fin=FIN)[0]
        tipo_libre_riesgo = letras.ultimo_valor / 100  # Viene en porcentaje
    else:
        print("FRED: sin FRED_API_KEY en el .env, se usa un tipo libre de riesgo fijo.")
    return series, tipo_libre_riesgo


def generar_datos_sinteticos():
    """Genera series con el mismo formato que las descargadas, para usar la demo sin red."""
    fechas = pd.bdate_range(INICIO, FIN)
    rng = np.random.default_rng(42)
    series = []
    for ticker in ACCIONES + [INDICE]:
        rendimientos = rng.normal(0.0004, 0.015, len(fechas))
        precios = pd.Series(100 * np.exp(np.cumsum(rendimientos)), index=fechas, name=ticker)
        tipo = TipoActivo.INDICE if ticker == INDICE else TipoActivo.ACCION
        series.append(
            FinancialSeries(
                precios,
                tipo,
                moneda="USD",
                proveedor="Sintético",
                metadatos={"nombre": f"{ticker} (sintético)"},
            )
        )
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
    for serie in series:
        if serie.activo in PESOS:
            acciones.append(serie)
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

    # -----------------------------------------------------------------------
    # 4. Informes: Markdown y gráficos
    # -----------------------------------------------------------------------
    titulo("4. Informes")
    informe = cartera.report(tasa_libre_riesgo=tipo_libre_riesgo)
    ruta_informe = CARPETA_SALIDA / "informe.md"
    ruta_informe.write_text(informe, encoding="utf-8")
    print(f"Informe Markdown: {ruta_informe}")
    mostrar = "--mostrar" in sys.argv
    figuras = cartera.plots_report(mostrar=False, carpeta=CARPETA_SALIDA / "graficos")
    print(f"Gráficos del informe ({len(figuras)}): {CARPETA_SALIDA / 'graficos'}")
    print(f"Gráficos de Monte Carlo: {CARPETA_SALIDA / 'montecarlo'}")
    if mostrar:
        simulacion.graficar()
    plt.close("all")

    print()
    print(informe)


if __name__ == "__main__":
    main()
