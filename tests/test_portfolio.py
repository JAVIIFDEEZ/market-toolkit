import numpy as np
import pandas as pd
import pytest

from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.models import Portfolio


def test_cartera_basica(cartera, precios_sinteticos):
    assert list(cartera.precio_activos.columns) == ["AAA", "BBB", "CCC"]
    assert len(cartera.precio_activos) == len(precios_sinteticos)
    assert cartera.pesos.sum(axis=1).to_numpy() == pytest.approx(1.0)


def test_pesos_derivan_sin_rebalanceo(cartera, precios_sinteticos):
    # Sin rebalanceos, cada peso crece con su activo (buy and hold)
    pesos = pd.Series({"AAA": 0.5, "BBB": 0.3, "CCC": 0.2})
    crecimiento = precios_sinteticos.iloc[-1] / precios_sinteticos.iloc[0]
    esperados = pesos * crecimiento / (pesos * crecimiento).sum()
    # `pesos` guarda los pesos al empezar cada sesión y `pesos_actuales` los del último cierre
    assert cartera.pesos.iloc[0].to_numpy() == pytest.approx(pesos.to_numpy())
    assert cartera.pesos_actuales.to_numpy() == pytest.approx(esperados.to_numpy())


def test_rebalanceo_en_las_fechas_indicadas(activos_usd, fechas_laborables):
    fecha_rebalanceo = fechas_laborables[100]
    pesos = pd.DataFrame(
        {"AAA": [0.5, 0.2], "BBB": [0.3, 0.4], "CCC": [0.2, 0.4]},
        index=[fechas_laborables[0], fecha_rebalanceo],
    )
    cartera = Portfolio(activos_usd, pesos)
    assert cartera.pesos.loc[fecha_rebalanceo].to_numpy() == pytest.approx([0.2, 0.4, 0.4])


def test_estadisticos_de_la_cartera(cartera, precios_sinteticos):
    # Valor de una cartera comprada al inicio y nunca rebalanceada
    pesos = pd.Series({"AAA": 0.5, "BBB": 0.3, "CCC": 0.2})
    valor = (precios_sinteticos / precios_sinteticos.iloc[0] * pesos).sum(axis=1)
    rendimientos = valor.pct_change().dropna()
    media = rendimientos.mean()
    assert cartera.rentabilidad_media == pytest.approx(media)
    assert cartera.desviacion_tipica == pytest.approx(rendimientos.std())
    assert cartera.rentabilidad_anualizada == pytest.approx(
        (1 + media) ** DIAS_COTIZACION_ANUAL - 1
    )
    assert cartera.volatilidad_anualizada == pytest.approx(
        rendimientos.std() * np.sqrt(DIAS_COTIZACION_ANUAL)
    )


def test_resumen(cartera):
    resumen = cartera.resumen()
    assert resumen["moneda"] == "USD"
    assert resumen["volatilidad_anualizada"] == cartera.volatilidad_anualizada
    assert sum(resumen["pesos_actuales"].values()) == pytest.approx(1.0)


def test_rechaza_pesos_que_no_suman_uno(activos_usd, fechas_laborables):
    pesos = pd.DataFrame({"AAA": [0.5], "BBB": [0.3], "CCC": [0.3]}, index=[fechas_laborables[0]])
    with pytest.raises(ValueError, match="sumar 1"):
        Portfolio(activos_usd, pesos)


def test_rechaza_pesos_de_activos_que_no_estan(activos_usd, fechas_laborables):
    pesos = pd.DataFrame({"AAA": [0.5], "BBB": [0.5], "ZZZ": [0.0]}, index=[fechas_laborables[0]])
    with pytest.raises(ValueError, match="Faltan"):
        Portfolio(activos_usd, pesos)


def test_rechaza_pesos_sin_indice_temporal(activos_usd):
    pesos = pd.DataFrame({"AAA": [0.5], "BBB": [0.3], "CCC": [0.2]})
    with pytest.raises(ValueError, match="DatetimeIndex"):
        Portfolio(activos_usd, pesos)


def test_pesos_anteriores_a_los_activos(activos_usd, fechas_laborables):
    # La cartera empieza en la primera sesión con los pesos indicados hasta entonces
    fecha_anterior = fechas_laborables[0] - pd.Timedelta(days=30)
    pesos = pd.DataFrame({"AAA": [0.5], "BBB": [0.3], "CCC": [0.2]}, index=[fecha_anterior])
    with pytest.warns(UserWarning, match="antes de la existencia de algunos activos"):
        cartera = Portfolio(activos_usd, pesos)
    assert cartera.pesos.iloc[0].to_numpy() == pytest.approx([0.5, 0.3, 0.2])
