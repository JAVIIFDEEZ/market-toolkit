from __future__ import annotations

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

import market_toolkit.simulation.montecarlo as montecarlo

# Colores de identidad de los activos, en orden fijo. A partir del octavo activo, los de menor
# peso medio se agrupan en "Otros" para que no haya colores indistinguibles
COLORES_ACTIVOS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                   "#e87ba4", "#008300", "#6250d6", "#e34948")
COLOR_OTROS = "#c3c2b7"
ANCHO_CARTERA = 2.5
ANCHO_ACTIVO = 1.2
_PORCENTAJE = FuncFormatter(lambda valor, _: f"{valor:.0%}")


def colores_activos(pesos: pd.DataFrame) -> dict[str, str]:
    """
    Asigna un color fijo a cada activo con color propio.
    :param pesos: Pesos de la cartera, con una columna por activo.
    :return: Diccionario {activo: color} de los activos que no se agrupan en "Otros".
    """
    # Por orden alfabético: cada activo conserva su color aunque cambie el orden de descarga
    principales = sorted(pesos.mean().nlargest(len(COLORES_ACTIVOS)).index)
    return dict(zip(principales, COLORES_ACTIVOS, strict=False))


def valor_cartera(rendimientos: pd.Series, inicio: pd.Timestamp) -> pd.Series:
    """
    Reconstruye el valor de la cartera en base 100.
    :param rendimientos: Rendimientos diarios de la cartera.
    :param inicio: Fecha inicial, en la que la cartera vale 100.
    :return: Serie con el valor de la cartera en cada sesión.
    """
    valor = 100 * (1 + rendimientos).cumprod()
    return pd.concat([pd.Series([100.0], index=[inicio]), valor]).rename("Cartera")


def contribuciones(rendimientos_activos: pd.DataFrame, pesos: pd.DataFrame,
                   valor: pd.Series) -> pd.Series:
    """
    Calcula cuánto aporta cada activo a la rentabilidad total de la cartera. La suma de las
    contribuciones es exactamente la rentabilidad total.
    :param rendimientos_activos: Rendimientos diarios de cada activo.
    :param pesos: Pesos con los que empieza cada sesión.
    :param valor: Valor de la cartera en base 100.
    :return: Contribución de cada activo en tanto por uno, de menor a mayor.
    """
    aportaciones = (rendimientos_activos * pesos).dropna()
    capital_previo = valor.shift(1).reindex(aportaciones.index) / 100
    return aportaciones.mul(capital_previo, axis=0).sum().sort_values()


def _rematar_fechas(eje) -> None:
    """Formatea el eje de fechas y lo ajusta a los datos."""
    eje.margins(x=0)
    eje.xaxis.set_major_formatter(mdates.ConciseDateFormatter(eje.xaxis.get_major_locator()))


def _titulo(eje, titulo: str, subtitulo: str) -> None:
    """Escribe el título y la línea explicativa del gráfico."""
    eje.set_title(f"{titulo}\n{subtitulo}", loc="left", fontsize=12,
                  color=montecarlo.COLORES["texto"])


def _leyenda_lateral(eje) -> None:
    """Coloca la leyenda a la derecha, fuera de la zona de datos."""
    eje.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=9,
               labelcolor=montecarlo.COLORES["texto_secundario"])


def _periodo(indice: pd.DatetimeIndex) -> str:
    """Texto con las fechas extremas de un índice."""
    return f"{indice[0].date()} a {indice[-1].date()}"


def dibujar_evolucion(figura: Figure, precios: pd.DataFrame, valor: pd.Series,
                      colores: dict[str, str]) -> None:
    """
    Compara el valor de la cartera con el de cada activo, todos en base 100.
    :param figura: Figura vacía en la que dibujar.
    :param precios: Precios en USD de cada activo.
    :param valor: Valor de la cartera en base 100.
    :param colores: Color de cada activo con color propio.
    """
    eje = figura.subplots()
    montecarlo.MonteCarlo._preparar_eje(eje)
    base = precios.div(precios.bfill().iloc[0]).mul(100)
    otros = [activo for activo in base.columns if activo not in colores]
    if otros:
        eje.plot(base.index, base[otros].to_numpy(), color=COLOR_OTROS, linewidth=ANCHO_ACTIVO,
                 zorder=1)
        eje.plot([], [], color=COLOR_OTROS, linewidth=ANCHO_ACTIVO,
                 label=f"Otros activos ({len(otros)})")
    for activo, color in colores.items():
        eje.plot(base.index, base[activo], color=color, linewidth=ANCHO_ACTIVO, zorder=2,
                 label=activo)
    eje.plot(valor.index, valor, color=montecarlo.COLORES["texto"], linewidth=ANCHO_CARTERA,
             zorder=3, label="Cartera")
    eje.axhline(100, color=montecarlo.COLORES["eje"], linewidth=1, zorder=0)
    eje.annotate(f"Cartera {valor.iloc[-1]:,.1f}", (valor.index[-1], valor.iloc[-1]),
                 xytext=(-6, 10), textcoords="offset points", ha="right", fontsize=9,
                 fontweight="bold", color=montecarlo.COLORES["texto"], zorder=4,
                 bbox={"boxstyle": "round,pad=0.2", "facecolor": montecarlo.COLORES["superficie"],
                       "edgecolor": "none", "alpha": 0.85})
    _rematar_fechas(eje)
    eje.set_ylabel("Valor (base 100, USD)", color=montecarlo.COLORES["texto_secundario"])
    _titulo(eje, "Evolución de la cartera frente a sus activos", _periodo(precios.index))
    _leyenda_lateral(eje)


def dibujar_drawdown(figura: Figure, valor: pd.Series) -> None:
    """
    Dibuja la caída de la cartera desde su máximo anterior.
    :param figura: Figura vacía en la que dibujar.
    :param valor: Valor de la cartera en base 100.
    """
    eje = figura.subplots()
    montecarlo.MonteCarlo._preparar_eje(eje)
    caidas = valor.div(valor.cummax()).sub(1)
    color = montecarlo.COLORES["perdida"]
    eje.fill_between(caidas.index, caidas, 0, color=color, alpha=0.3, linewidth=0)
    eje.plot(caidas.index, caidas, color=color, linewidth=1.5)
    eje.axhline(0, color=montecarlo.COLORES["eje"], linewidth=1)
    fecha_minimo = caidas.idxmin()
    posicion = (fecha_minimo - caidas.index[0]) / (caidas.index[-1] - caidas.index[0])
    al_final = posicion > 0.75
    eje.annotate(f"Máximo {caidas.min():.1%} ({fecha_minimo.date()})",
                 (fecha_minimo, caidas.min()), xytext=(-8 if al_final else 8, -4),
                 textcoords="offset points", ha="right" if al_final else "left", va="center",
                 fontsize=9, color=montecarlo.COLORES["texto_secundario"])
    eje.set_ylim(min(caidas.min() * 1.15, -0.01), 0.002)
    eje.yaxis.set_major_formatter(_PORCENTAJE)
    _rematar_fechas(eje)
    eje.set_ylabel("Caída desde el máximo", color=montecarlo.COLORES["texto_secundario"])
    _titulo(eje, "Drawdown de la cartera", _periodo(caidas.index))


def dibujar_pesos(figura: Figure, pesos: pd.DataFrame, colores: dict[str, str],
                  cambios: pd.DatetimeIndex) -> None:
    """
    Dibuja cómo se reparte la cartera en el tiempo.
    :param figura: Figura vacía en la que dibujar.
    :param pesos: Pesos con los que empieza cada sesión.
    :param colores: Color de cada activo con color propio.
    :param cambios: Sesiones en las que se cambian los pesos.
    """
    eje = figura.subplots()
    montecarlo.MonteCarlo._preparar_eje(eje)
    tramos = pesos[list(colores)].copy()
    tonos = list(colores.values())
    otros = [activo for activo in pesos.columns if activo not in colores]
    if otros:
        tramos[f"Otros ({len(otros)})"] = pesos[otros].sum(axis=1)
        tonos.append(COLOR_OTROS)
    eje.stackplot(tramos.index, tramos.to_numpy().T, labels=list(tramos.columns), colors=tonos,
                  edgecolor=montecarlo.COLORES["superficie"], linewidth=0.8)
    for numero, fecha in enumerate(cambios):
        eje.axvline(fecha, color=montecarlo.COLORES["texto"], linewidth=1.2,
                    label="Cambio de pesos" if numero == 0 else None)
    eje.set_ylim(0, 1)
    eje.yaxis.set_major_formatter(_PORCENTAJE)
    _rematar_fechas(eje)
    eje.set_ylabel("Peso en la cartera", color=montecarlo.COLORES["texto_secundario"])
    _titulo(eje, "Evolución de los pesos", "Peso de cada activo al empezar cada sesión")
    # Leyenda en el mismo orden visual que las capas, de arriba abajo
    elementos, nombres = eje.get_legend_handles_labels()
    capas = tramos.shape[1]
    eje.legend(elementos[:capas][::-1] + elementos[capas:], nombres[:capas][::-1] + nombres[capas:],
               loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=9,
               labelcolor=montecarlo.COLORES["texto_secundario"])


def dibujar_riesgo_rentabilidad(figura: Figure, volatilidades: pd.Series,
                                rentabilidades: pd.Series, volatilidad_cartera: float,
                                rentabilidad_cartera: float) -> None:
    """
    Compara el riesgo y la rentabilidad anualizados de la cartera y de sus activos.
    :param figura: Figura vacía en la que dibujar.
    :param volatilidades: Volatilidad anualizada de cada activo.
    :param rentabilidades: Rentabilidad anualizada de cada activo.
    :param volatilidad_cartera: Volatilidad anualizada de la cartera.
    :param rentabilidad_cartera: Rentabilidad anualizada de la cartera.
    """
    eje = figura.subplots()
    montecarlo.MonteCarlo._preparar_eje(eje)
    eje.grid(axis="x", color=montecarlo.COLORES["rejilla"], linewidth=0.8)
    eje.scatter(volatilidades, rentabilidades, s=70, color=montecarlo.COLORES["texto_tenue"],
                edgecolor=montecarlo.COLORES["superficie"], linewidth=1.5, zorder=2)
    eje.scatter([volatilidad_cartera], [rentabilidad_cartera], s=130,
                color=montecarlo.COLORES["texto"], edgecolor=montecarlo.COLORES["superficie"],
                linewidth=1.5, zorder=3)
    if min(rentabilidades.min(), rentabilidad_cartera) < 0:
        eje.axhline(0, color=montecarlo.COLORES["eje"], linewidth=1, zorder=1)
    puntos = [(float(rentabilidades[activo]), float(volatilidades[activo]), str(activo), False)
              for activo in rentabilidades.index]
    puntos.append((rentabilidad_cartera, volatilidad_cartera, "Cartera", True))
    eje.margins(x=0.14, y=0.12)
    # Cada etiqueta se coloca junto a su punto, en la primera posición libre. Las distancias se
    # calculan en puntos tipográficos, aproximando el tamaño de la zona de datos y del texto
    ancho_figura, alto_figura = figura.get_size_inches() * 72
    escala_x = 0.85 * ancho_figura / (eje.get_xlim()[1] - eje.get_xlim()[0])
    escala_y = 0.80 * alto_figura / (eje.get_ylim()[1] - eje.get_ylim()[0])
    centros = [(volatilidad * escala_x, rentabilidad * escala_y)
               for rentabilidad, volatilidad, _, _ in puntos]
    ocupadas = [(x - 8, y - 8, x + 8, y + 8) for x, y in centros]
    for (x, y), (_, _, nombre, es_cartera), (rentabilidad, volatilidad, _, _) in zip(
            centros, puntos, puntos, strict=True):
        ancho_texto = 7.0 * len(nombre)
        for dx, dy in ((10, 0), (-10, 0), (10, 13), (10, -13), (-10, 13), (-10, -13)):
            izquierda = x + dx if dx > 0 else x + dx - ancho_texto
            caja = (izquierda, y + dy - 7, izquierda + ancho_texto, y + dy + 7)
            # La marca de su propio punto no cuenta como obstáculo
            libre = not any(
                caja[0] < otra[2] and otra[0] < caja[2] and caja[1] < otra[3] and otra[1] < caja[3]
                for otra in ocupadas if otra != (x - 8, y - 8, x + 8, y + 8)
            )
            if libre:
                break
        ocupadas.append(caja)
        eje.annotate(nombre, (volatilidad, rentabilidad), xytext=(dx, dy),
                     textcoords="offset points", va="center", ha="left" if dx > 0 else "right",
                     fontsize=10, fontweight="bold" if es_cartera else "normal",
                     color=montecarlo.COLORES["texto" if es_cartera
                                              else "texto_secundario"])
    eje.xaxis.set_major_formatter(_PORCENTAJE)
    eje.yaxis.set_major_formatter(_PORCENTAJE)
    eje.set_xlabel("Volatilidad anualizada", color=montecarlo.COLORES["texto_secundario"])
    eje.set_ylabel("Rentabilidad anualizada", color=montecarlo.COLORES["texto_secundario"])
    _titulo(eje, "Riesgo y rentabilidad", "Cartera frente a cada activo, en USD")


def dibujar_contribuciones(figura: Figure, aportes: pd.Series, inicio: pd.Timestamp,
                           fin: pd.Timestamp) -> None:
    """
    Dibuja cuánto aporta cada activo a la rentabilidad total de la cartera.
    :param figura: Figura vacía en la que dibujar.
    :param aportes: Contribución de cada activo en tanto por uno, de menor a mayor.
    :param inicio: Primera fecha del periodo, para el título.
    :param fin: Última fecha del periodo, para el título.
    """
    eje = figura.subplots()
    montecarlo.MonteCarlo._preparar_eje(eje)
    eje.grid(False)
    eje.grid(axis="x", color=montecarlo.COLORES["rejilla"], linewidth=0.8)
    posiciones = np.arange(len(aportes))
    tonos = [montecarlo.COLORES["ganancia" if valor >= 0 else "perdida"] for valor in aportes]
    eje.barh(posiciones, aportes.to_numpy(), height=0.62, color=tonos, zorder=2)
    eje.axvline(0, color=montecarlo.COLORES["eje"], linewidth=1, zorder=3)
    eje.set_yticks(posiciones, aportes.index)
    for posicion, valor in zip(posiciones, aportes, strict=True):
        eje.annotate(f"{valor * 100:+.1f} pp", (valor, posicion),
                     xytext=(6 if valor >= 0 else -6, 0), textcoords="offset points",
                     ha="left" if valor >= 0 else "right", va="center", fontsize=9,
                     color=montecarlo.COLORES["texto_secundario"])
    eje.margins(x=0.14)
    eje.xaxis.set_major_formatter(_PORCENTAJE)
    eje.set_xlabel("Aportación a la rentabilidad total",
                   color=montecarlo.COLORES["texto_secundario"])
    _titulo(eje, f"Contribución por activo · rentabilidad total {aportes.sum():+.1%}",
            f"{inicio.date()} a {fin.date()}")
