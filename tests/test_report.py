import matplotlib

matplotlib.use("Agg")  # Sin ventanas: los gráficos se generan pero no se muestran

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from market_toolkit.config import DIAS_COTIZACION_ANUAL  # noqa: E402
from market_toolkit.models import FinancialSeries, Portfolio, TipoActivo  # noqa: E402

SECCIONES = [
    "# Informe de cartera",
    "## Información general",
    "### Composición por activo",
    "## Rentabilidad",
    "## Riesgo",
    "## Diversificación y concentración",
    "## Diagnósticos y advertencias",
]
GRAFICOS = ["evolucion", "drawdown", "pesos", "riesgo_rentabilidad", "contribucion", "correlacion"]


def valor_metrica(informe: str, nombre: str) -> str:
    """Devuelve el valor de una línea `- **nombre:** valor` del informe."""
    for linea in informe.splitlines():
        if linea.startswith(f"- **{nombre}:**"):
            return linea.split(":**")[1].strip()
    raise AssertionError(f"El informe no tiene la métrica {nombre}")


# ---------- report() ----------


def test_report_tiene_todas_las_secciones(cartera):
    informe = cartera.report()
    assert isinstance(informe, str)
    for seccion in SECCIONES:
        assert seccion in informe.splitlines()


def test_report_usa_los_rendimientos_de_la_cartera(cartera):
    # Sharpe (sin tipo libre de riesgo) y drawdown calculados a mano con los rendimientos que
    # la cartera usa para sus estadísticos
    rendimientos = cartera._rendimientos_cartera()
    sharpe = rendimientos.mean() / rendimientos.std() * np.sqrt(DIAS_COTIZACION_ANUAL)
    crecimiento = (1 + rendimientos).cumprod()
    drawdown_maximo = -(crecimiento / crecimiento.cummax() - 1).min()
    informe = cartera.report()
    assert valor_metrica(informe, "Sharpe anualizado") == f"{sharpe:.2f}"
    assert valor_metrica(informe, "Drawdown máximo") == f"{drawdown_maximo:.2%}"
    assert valor_metrica(informe, "Volatilidad anualizada") == (
        f"{cartera.volatilidad_anualizada:.2%}"
    )


def test_report_muestra_los_pesos_al_cierre(cartera):
    informe = cartera.report()
    for activo, peso in cartera.pesos_actuales.items():
        assert f"| {activo} | {peso:.2%} |" in informe


def test_report_sin_advertencias(activos_usd, fechas_laborables):
    # Pesos repartidos para que ningún activo supere el 50 % aunque los pesos deriven
    pesos = pd.DataFrame({"AAA": [0.4], "BBB": [0.3], "CCC": [0.3]}, index=[fechas_laborables[0]])
    informe = Portfolio(activos_usd, pesos).report(max_volatilidad=10, max_drawdown=10)
    assert "Sin advertencias con los umbrales indicados." in informe


def test_report_advierte_de_volatilidad_y_drawdown(cartera):
    informe = cartera.report(max_volatilidad=0, max_drawdown=0)
    assert "La volatilidad anualizada" in informe
    assert "El drawdown máximo" in informe


def test_report_advierte_de_concentracion(activos_usd, fechas_laborables):
    pesos = pd.DataFrame({"AAA": [0.8], "BBB": [0.1], "CCC": [0.1]}, index=[fechas_laborables[0]])
    informe = Portfolio(activos_usd, pesos).report(max_volatilidad=10, max_drawdown=10)
    assert "Concentración elevada en **AAA**" in informe


@pytest.mark.parametrize(
    "parametros",
    [
        {"tasa_libre_riesgo": float("nan")},
        {"max_volatilidad": -0.1},
        {"max_drawdown": True},
        {"tasa_libre_riesgo": "2%"},
    ],
)
def test_report_rechaza_parametros_no_validos(cartera, parametros):
    with pytest.raises(ValueError):
        cartera.report(**parametros)


# ---------- plots_report() ----------


def test_plots_report_devuelve_todas_las_figuras(cartera):
    figuras = cartera.plots_report(mostrar=False, guardar=False)
    assert list(figuras) == GRAFICOS
    for figura in figuras.values():
        assert isinstance(figura, Figure)
        assert figura.axes  # Cada figura tiene al menos un eje dibujado


def test_plots_report_guarda_los_png(cartera, tmp_path):
    cartera.plots_report(mostrar=False, carpeta=tmp_path)
    guardados = sorted(ruta.stem for ruta in tmp_path.glob("*.png"))
    assert guardados == sorted(GRAFICOS)


# ---------- Métricas del informe, comparadas con un cálculo a mano ----------


def test_report_rentabilidad_y_cagr(cartera):
    rendimientos = cartera.rendimiento
    valor_final = (1 + rendimientos).prod()
    cagr = valor_final ** (DIAS_COTIZACION_ANUAL / len(cartera.precio_activos)) - 1
    informe = cartera.report()
    assert valor_metrica(informe, "Rentabilidad acumulada") == f"{valor_final - 1:.2%}"
    assert valor_metrica(informe, "CAGR").startswith(f"{cagr:.2%}")
    assert valor_metrica(informe, "Valor final de 100 iniciales") == f"{valor_final * 100:.2f}"
    assert valor_metrica(informe, "Mejor día") == (
        f"{rendimientos.idxmax().date()} ({rendimientos.max():.2%})"
    )
    assert valor_metrica(informe, "Peor día") == (
        f"{rendimientos.idxmin().date()} ({rendimientos.min():.2%})"
    )


def test_report_sortino_y_expected_shortfall(cartera):
    tasa = 0.04
    exceso = cartera.rendimiento - tasa / DIAS_COTIZACION_ANUAL
    desviacion_bajista = np.sqrt((exceso.clip(upper=0) ** 2).mean())
    sortino = exceso.mean() / desviacion_bajista * np.sqrt(DIAS_COTIZACION_ANUAL)
    cola = cartera.rendimiento[cartera.rendimiento <= cartera.rendimiento.quantile(0.05)]
    informe = cartera.report(tasa_libre_riesgo=tasa)
    assert valor_metrica(informe, "Sortino anualizado") == f"{sortino:.2f}"
    assert valor_metrica(informe, "Expected Shortfall (95%, histórico diario)") == (
        f"{-cola.mean():.2%}"
    )


def test_report_concentracion_hhi(cartera):
    pesos = cartera.pesos_actuales / cartera.pesos_actuales.sum()
    hhi = (pesos**2).sum()
    informe = cartera.report()
    assert valor_metrica(informe, "Índice HHI") == f"{hhi:.2f}"
    assert valor_metrica(informe, "Número efectivo de activos") == f"{1 / hhi:.2f}"
    assert valor_metrica(informe, "Mayor exposición absoluta") == f"{pesos.max():.2%}"


def test_report_contribuciones_suman_la_rentabilidad_total(cartera):
    informe = cartera.report()
    total = float(valor_metrica(informe, "Rentabilidad acumulada").rstrip("%"))
    contribuciones = []
    for linea in informe.splitlines():
        celdas = [celda.strip() for celda in linea.strip("|").split("|")]
        if len(celdas) == 5 and celdas[0] in cartera.precio_activos.columns:
            contribuciones.append(float(celdas[4].rstrip("%")))
    assert len(contribuciones) == len(cartera.precio_activos.columns)
    # Cada valor se muestra redondeado a dos decimales: la suma solo puede diferir por ese
    # redondeo, como mucho media centésima por cada contribución
    assert sum(contribuciones) == pytest.approx(total, abs=0.005 * len(contribuciones))


def test_report_advierte_de_historial_corto(cartera):
    informe = cartera.report(min_historial=10_000)
    assert "Historial corto" in informe


def test_report_advierte_de_correlacion_alta(activos_usd, fechas_laborables, serie_precios):
    # Un activo que replica a otro: correlación de 1
    replica = FinancialSeries(
        (serie_precios * 2).rename("REPLICA"), TipoActivo.ACCION, moneda="USD"
    )
    pesos = pd.DataFrame(
        {"AAA": [0.25], "BBB": [0.25], "CCC": [0.25], "REPLICA": [0.25]},
        index=[fechas_laborables[0]],
    )
    informe = Portfolio([*activos_usd, replica], pesos).report()
    assert "Correlación elevada entre **AAA** y **REPLICA**: 1.00." in informe


def test_report_fortalezas(cartera):
    informe = cartera.report(
        max_drawdown=1,
        min_activos_efectivos=1,
        max_correlacion_diversificada=1,
        min_sharpe=-100,
    )
    seccion = informe.split("## Fortalezas")[1]
    assert "Diversificación por pesos" in seccion
    assert "Correlación media reducida" in seccion
    assert "Drawdown histórico moderado" in seccion
    assert "Sharpe elevado" in seccion


def test_report_sin_fortalezas(cartera):
    informe = cartera.report(
        max_drawdown=0,
        min_activos_efectivos=100,
        max_correlacion_diversificada=-1,
        min_sharpe=100,
    )
    assert "No se han detectado fortalezas según los umbrales configurados." in informe


def test_report_guarda_el_informe_en_un_fichero(cartera, tmp_path):
    ruta = tmp_path / "informe.md"
    informe = cartera.report(ruta=str(ruta))
    assert ruta.read_text(encoding="utf-8") == informe


# ---------- Índice de referencia, Monte Carlo y HTML ----------


@pytest.fixture
def indice(precios_sinteticos):
    """Índice de referencia: la media de los tres activos de la cartera."""
    precios = precios_sinteticos.mean(axis=1).rename("IDX")
    return FinancialSeries(precios, TipoActivo.INDICE, moneda="USD", metadatos={"nombre": "Índice"})


def test_report_con_benchmark(cartera, indice):
    from market_toolkit.analytics import metricas_benchmark

    metricas = metricas_benchmark(cartera.rendimiento, indice.rendimientos(), 0.04)
    informe = cartera.report(tasa_libre_riesgo=0.04, benchmark=indice)
    assert "## Comparación con el índice de referencia (IDX)" in informe
    assert valor_metrica(informe, "Beta") == f"{metricas['beta']:.2f}"
    assert valor_metrica(informe, "Alfa de Jensen anual") == f"{metricas['alfa']:.2%}"
    assert valor_metrica(informe, "Tracking error anual") == f"{metricas['tracking_error']:.2%}"


def test_report_advierte_si_la_cartera_rinde_menos_que_el_indice(cartera, precios_sinteticos):
    # Un índice que sube un 0,2 % cada día: la cartera siempre rinde menos
    fechas = precios_sinteticos.index
    precios = pd.Series(100 * 1.002 ** np.arange(len(fechas)), index=fechas, name="SUBE")
    indice = FinancialSeries(precios, TipoActivo.INDICE, moneda="USD")
    assert "La cartera ha rendido" in cartera.report(benchmark=indice)


def test_report_rechaza_un_benchmark_que_no_es_una_serie(cartera, serie_precios):
    with pytest.raises(ValueError, match="benchmark"):
        cartera.report(benchmark=serie_precios)


def test_report_con_montecarlo(cartera):
    informe = cartera.report(incluir_montecarlo=True, simulaciones_montecarlo=300)
    seccion = informe.split("## Simulación de Monte Carlo (1 año)")[1].split("##")[0]
    filas = [linea for linea in seccion.splitlines() if linea.startswith("| ")]
    assert len(filas) == 5  # Cabecera, separador y una fila por distribución
    assert "| Normal |" in seccion
    assert "| Bootstrap histórico |" in seccion


def test_report_en_html(cartera, indice):
    pagina = cartera.report(benchmark=indice, formato="html")
    assert pagina.startswith("<!DOCTYPE html>")
    assert "<h1>Informe de cartera</h1>" in pagina
    assert pagina.count("<table>") == 2  # Composición y correlaciones
    assert pagina.count('src="data:image/png;base64,') == 6  # Los seis gráficos incrustados
    assert "Comparación con el índice de referencia" in pagina


def test_report_en_html_sin_graficos(cartera):
    pagina = cartera.report(formato="html", incluir_graficos=False)
    assert "<img" not in pagina
    assert "<h2>Riesgo</h2>" in pagina


def test_report_html_guarda_el_fichero(cartera, tmp_path):
    ruta = tmp_path / "informe.html"
    pagina = cartera.report(formato="html", incluir_graficos=False, ruta=str(ruta))
    assert ruta.read_text(encoding="utf-8") == pagina


def test_report_rechaza_formatos_no_validos(cartera):
    with pytest.raises(ValueError, match="Formato"):
        cartera.report(formato="pdf")


def test_plots_report_con_benchmark(cartera, indice):
    figuras = cartera.plots_report(mostrar=False, guardar=False, benchmark=indice)
    leyenda = [texto.get_text() for texto in figuras["evolucion"].axes[0].get_legend().get_texts()]
    assert "Referencia: Índice" in leyenda


def test_report_con_un_rebalanceo_en_un_dia_sin_sesion(activos_usd, fechas_laborables):
    # 2024-06-01 es sábado: los pesos nuevos se aplican el lunes 3 y el informe debe mostrarlos
    pesos = pd.DataFrame(
        {"AAA": [0.5, 0.2], "BBB": [0.3, 0.4], "CCC": [0.2, 0.4]},
        index=[fechas_laborables[0], pd.Timestamp("2024-06-01")],
    )
    informe = Portfolio(activos_usd, pesos).report()
    assert "**Último rebalanceo explícito:** 2024-06-01" in informe
    assert "  - AAA: 20.00%" in informe
