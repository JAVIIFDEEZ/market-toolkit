import matplotlib

matplotlib.use("Agg")  # Sin ventanas: los gráficos se generan pero no se muestran

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from market_toolkit.config import DIAS_COTIZACION_ANUAL  # noqa: E402
from market_toolkit.models import Portfolio  # noqa: E402

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
