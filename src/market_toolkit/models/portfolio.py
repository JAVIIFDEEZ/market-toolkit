from __future__ import annotations

import hashlib
import warnings
from collections.abc import Mapping, Sequence
from itertools import combinations_with_replacement
from typing import TYPE_CHECKING, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

import market_toolkit.models.montecarlo as montecarlo
from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.exceptions import InsufficientDataError
from market_toolkit.preprocessing import juntar_series

if TYPE_CHECKING:
    from market_toolkit.models.series import FinancialSeries


class Portfolio:
    """
    Clase que modela una cartera de inversión.
    """
    TOLERANCIA_PESOS = 1e-6  # Margen para considerar que los pesos de una fecha suman 1

    activos: pd.DataFrame
    pesos: pd.DataFrame
    metadatos_activos: pd.DataFrame
    metadatos: dict
    rentabilidad_media: float
    desviacion_tipica: float
    rentabilidad_anualizada: float
    volatilidad_anualizada: float

    def __init__(self, activos: Sequence[FinancialSeries], pesos: pd.DataFrame, *,
                 alineacion_temporal: Literal["relleno", "eliminacion"] = "eliminacion"):
        """
        Inicializa un objeto de Portfolio.
        :param activos: Lista con las series temporales que forman la cartera.
        :param pesos: DataFrame con los pesos de cada uno de los activos de la cartera.
            Debe tener un índice temporal y cada fila se corresponde con los pesos del día
            correspondiente. Si el índice no es diario, cada fila indica los pesos en la ventana
            temporal que empieza en esa fecha y termina en la fecha de la próxima fila.
        :param alineacion_temporal: Establece cómo tratar las fechas en las que no cotizan todos
            los activos. `"eliminacion"` (por defecto) elimina esas fechas y `"relleno"` usa el
            último precio conocido de cada activo.
        """
        # Juntar activos
        self._series = list(activos)
        self.activos = juntar_series(activos, True, alineacion_temporal)
        # Validar pesos
        if not isinstance(pesos.index, pd.DatetimeIndex):
            raise ValueError("El índice de los pesos debe ser un DatetimeIndex.")
        # Cada peso se empareja con su activo por nombre, no por posición
        faltan = sorted(set(self.activos.columns) - set(pesos.columns))
        sobran = sorted(set(pesos.columns) - set(self.activos.columns))
        if faltan or sobran:
            raise ValueError(
                f"Las columnas de los pesos deben ser los activos de la cartera. "
                f"Faltan: {faltan or 'ninguno'}. Sobran: {sobran or 'ninguno'}.")
        pesos = pesos[list(self.activos.columns)].sort_index()  # Mismo orden que los activos
        pesos = pesos.dropna()  # Nos quedamos SOLO cuando todos los pesos son validos.
        if pesos.empty:
            raise ValueError("No se han proporcionado pesos válidos.")
        sumas = pesos.sum(axis=1)
        incorrectas = sumas[(sumas - 1).abs() > self.TOLERANCIA_PESOS]
        if not incorrectas.empty:
            raise ValueError(
                f"Los pesos de cada fecha deben sumar 1. El {incorrectas.index[0].date()} "
                f"suman {incorrectas.iloc[0]:.4f}.")
        # Los activos y pesos indicados identifican la cartera, aunque se añadan fechas de precios
        self._firma = hashlib.sha256(pesos.sort_index(axis=1).to_csv().encode()).hexdigest()
        # Pesos de los activos. Cada fila se mantiene hasta el siguiente cambio: se añaden las
        # fechas de los activos desde el primer peso para que unos pesos fijos (una sola fila)
        # se extiendan a todo el periodo de la cartera
        fechas_activos = self.activos.index[self.activos.index >= pesos.index[0]]
        self.pesos = pesos.reindex(pesos.index.union(fechas_activos)).ffill()
        # Ajuste temporal entre los pesos y los activos
        if self.pesos.index[0] < self.activos.index[0]:
            warnings.warn(
                "Hay pesos configurados para antes de la existencia de algunos activos. "
                "Se truncan para que el día de inicio coincida con el de los activos.",
                UserWarning,
                stacklevel=2,
            )
            self.pesos = self.pesos[self.activos.index[0]:]
        elif self.pesos.index[0] > self.activos.index[0]:
            warnings.warn(
                "Hay activos configurados para antes de la existencia de los pesos. "
                "Se truncan para que el día de inicio coincida con el de los pesos.",
                UserWarning,
                stacklevel=2,
            )
            self.activos = self.activos[self.pesos.index[0]:]
        if self.pesos.index[-1] > self.activos.index[-1]:
            warnings.warn(
                "Hay pesos configurados para después de la existencia de los activos. "
                "Se truncan para que el día de fin coincida con el de los activos.",
                UserWarning,
                stacklevel=2,
            )
            self.pesos = self.pesos[:self.activos.index[-1]]
        elif self.pesos.index[-1] < self.activos.index[-1]:
            self.pesos = self.pesos.reindex(self.activos.index).ffill()
        # Informacion de cada activo, sobre las fechas definitivas de la cartera
        self.metadatos_activos = self._calcular_metadatos_activos(activos)
        self.metadatos_activos.columns.name = None
        self.metadatos_activos.index.name = "Información"
        # Metadatos de los activos
        self.metadatos ={activo.activo: activo.metadatos for activo in activos}
        # Calcular estadisticos
        self._calcular_estadisticos()
        self._borrar_correlacion_si_cambia()

    def _calcular_metadatos_activos(self, activos: Sequence[FinancialSeries]) -> pd.DataFrame:
        """
        Recalcula los metadatos de los activos que forman la cartera tras la alineacion temporal.
        :param activos: Lista de series temporales de la cartera.
        :return: DataFrame en el que cada columna es un activo y cada fila un metadato
        """
        info = pd.DataFrame(
            [activo.resumen() for activo in activos]
        ).set_index("activo").T
        rentabilidades = self.activos.pct_change()
        medias = rentabilidades.mean()
        desviaciones = rentabilidades.std()
        rentabilidades_anual = (1 + medias) ** DIAS_COTIZACION_ANUAL - 1
        volatilidades_anual = desviaciones * np.sqrt(DIAS_COTIZACION_ANUAL)
        info.loc["moneda"] = "USD"
        info.loc["inicio"] = self.activos.index[0].date()
        info.loc["fin"] = self.activos.index[-1].date()
        info.loc["observaciones"] = len(self.activos)
        info.loc["media_diaria"] = medias
        info.loc["desviacion_tipica_diaria"] = desviaciones
        info.loc["rentabilidad_anualizada"] = rentabilidades_anual
        info.loc["volatilidad_anualizada"] = volatilidades_anual
        return info

    def _calcular_estadisticos(self):
        """
        Determina distintos estadísticos de la cartera, como la rentabilidad media diaria, la
        volatilidad, la rentabilidad media anualizada y la volatilidad anualizada.
        """
        # Rendimiento de la cartera: rendimiento de cada activo por el peso que tenía el capital
        # en él al cierre de la sesión anterior
        rendimientos_activos = self.activos.pct_change(fill_method=None)
        pesos = self.pesos.reindex(self.activos.index).ffill().shift(1)
        rendimientos = (rendimientos_activos * pesos).dropna().sum(axis=1)
        if len(rendimientos) < 2:
            raise InsufficientDataError(
                "La cartera no tiene suficientes fechas con precios de sus activos para "
                "calcular sus estadísticos.")
        self.rentabilidad_media = float(rendimientos.mean())
        self.desviacion_tipica = float(rendimientos.std())
        self.rentabilidad_anualizada = (1 + self.rentabilidad_media) ** DIAS_COTIZACION_ANUAL - 1
        self.volatilidad_anualizada = self.desviacion_tipica * np.sqrt(DIAS_COTIZACION_ANUAL)

    def correlacion(self, t: float) -> pd.DataFrame:
        """
        Calcula la correlación de los rendimientos diarios de los activos durante los últimos
        `t` años de la cartera y guarda la matriz como imagen en `models/graficos/correlacion.png`.
        Cada pareja de activos se calcula con sus propias fechas comunes, en USD.
        :param t: Años hacia atrás desde la última fecha de la cartera (admite fracciones).
        :return: DataFrame con la matriz de correlaciones.
        """
        if not t > 0:
            raise ValueError("El número de años `t` debe ser mayor que 0.")
        ultima_fecha = self.activos.index[-1]
        desde = ultima_fecha - pd.Timedelta(days=t * 365.25)
        if desde < self.activos.index[0]:
            warnings.warn(
                f"La cartera solo tiene datos desde {self.activos.index[0].date()}. "
                f"La correlación se calcula con ese periodo, más corto que {t} años.",
                UserWarning,
                stacklevel=2,
            )
        # Precios en USD de cada activo con su propio calendario, en el periodo de la cartera
        precios = juntar_series(self._series, True, None).loc[self.activos.index[0]:ultima_fecha]
        nombres = list(self.activos.columns)
        correlaciones = pd.DataFrame(np.eye(len(nombres)), index=nombres, columns=nombres)
        sesiones = []
        for activo_a, activo_b in combinations_with_replacement(nombres, 2):
            columnas = [activo_a] if activo_a == activo_b else [activo_a, activo_b]
            # Rendimientos de la pareja entre sus fechas comunes consecutivas
            rendimientos = precios[columnas].dropna().pct_change(fill_method=None).dropna()
            rendimientos = rendimientos[rendimientos.index > desde]
            if len(rendimientos) < 2:
                raise InsufficientDataError(
                    f"No hay suficientes sesiones comunes de {activo_a} y {activo_b} en los "
                    f"últimos {t} años para calcular la correlación.")
            sesiones.append(len(rendimientos))
            if activo_a != activo_b:
                valor = rendimientos[activo_a].corr(rendimientos[activo_b])
                correlaciones.loc[activo_a, activo_b] = valor
                correlaciones.loc[activo_b, activo_a] = valor
        inicio = max(desde, self.activos.index[0])
        self._guardar_grafico_correlacion(correlaciones, inicio, ultima_fecha, sesiones)
        return correlaciones

    def _borrar_correlacion_si_cambia(self) -> None:
        """Borra `correlacion.png` si se generó con una cartera distinta a esta."""
        grafico = montecarlo.CARPETA_GRAFICOS / "correlacion.png"
        firma = montecarlo.CARPETA_GRAFICOS / "correlacion.firma"
        if firma.exists() and firma.read_text() == self._firma:
            return
        grafico.unlink(missing_ok=True)
        firma.unlink(missing_ok=True)

    def _guardar_grafico_correlacion(self, correlaciones: pd.DataFrame, inicio: pd.Timestamp,
                                     fin: pd.Timestamp, sesiones: list[int]) -> None:
        """
        Guarda la matriz de correlaciones como una cuadrícula con escala de -1 a 1.
        :param correlaciones: Matriz de correlaciones.
        :param inicio: Primera fecha del periodo, para el título.
        :param fin: Última fecha del periodo, para el título.
        :param sesiones: Número de sesiones de cada pareja de activos, para el título.
        """
        n_activos = len(correlaciones)
        lado = max(5.0, 1.1 * n_activos + 2)
        figura = Figure(figsize=(lado + 1, lado), facecolor=montecarlo.COLORES["superficie"])
        eje = figura.subplots()
        mapa = plt.get_cmap("plasma")
        imagen = eje.imshow(correlaciones.to_numpy(), cmap=mapa, vmin=-1, vmax=1)
        posiciones = np.arange(n_activos)
        eje.set_xticks(posiciones, correlaciones.columns, rotation=45, ha="right")
        eje.set_yticks(posiciones, correlaciones.index)
        eje.tick_params(length=0, labelsize=10, colors=montecarlo.COLORES["texto_secundario"])
        # Separación entre celdas
        eje.set_xticks(posiciones[:-1] + 0.5, minor=True)
        eje.set_yticks(posiciones[:-1] + 0.5, minor=True)
        eje.grid(which="minor", color=montecarlo.COLORES["superficie"], linewidth=2)
        eje.tick_params(which="minor", length=0)
        for lado_eje in eje.spines.values():
            lado_eje.set_visible(False)
        # Valor en cada celda, en negro o blanco según lo claro que sea el color de fondo
        for fila, columna in np.ndindex(correlaciones.shape):
            valor = correlaciones.iat[fila, columna]
            rojo, verde, azul, _ = mapa(imagen.norm(valor))
            claro = 0.299 * rojo + 0.587 * verde + 0.114 * azul > 0.5
            eje.text(columna, fila, f"{valor:.2f}", ha="center", va="center", fontsize=10,
                     color="black" if claro else "white")
        barra = figura.colorbar(imagen, ax=eje, fraction=0.046, pad=0.04)
        barra.ax.tick_params(labelsize=9, colors=montecarlo.COLORES["texto_secundario"])
        barra.outline.set_visible(False)
        n_sesiones = (f"{min(sesiones)}" if min(sesiones) == max(sesiones)
                      else f"{min(sesiones)}-{max(sesiones)}")
        eje.set_title(
            f"Correlación de rendimientos diarios\n{inicio.date()} a {fin.date()} · "
            f"{n_sesiones} sesiones comunes por pareja",
            loc="left", color=montecarlo.COLORES["texto"], fontsize=12)
        montecarlo.CARPETA_GRAFICOS.mkdir(parents=True, exist_ok=True)
        figura.savefig(montecarlo.CARPETA_GRAFICOS / "correlacion.png", dpi=150,
                       bbox_inches="tight", facecolor=montecarlo.COLORES["superficie"])
        (montecarlo.CARPETA_GRAFICOS / "correlacion.firma").write_text(self._firma)

    def resumen(self) -> dict:
        """
        Devuelve la información principal de la cartera y sus estadísticos.
        :return: Diccionario con los activos, los pesos actuales y los estadísticos de la cartera.
        """
        return {
            "activos": list(self.activos.columns),
            "pesos_actuales": self.pesos.iloc[-1].to_dict(),
            "moneda": "USD",
            "inicio": self.activos.index[0].date(),
            "fin": self.activos.index[-1].date(),
            "observaciones": len(self.activos),
            "media_diaria": self.rentabilidad_media,
            "desviacion_tipica_diaria": self.desviacion_tipica,
            "rentabilidad_anualizada": self.rentabilidad_anualizada,
            "volatilidad_anualizada": self.volatilidad_anualizada,
        }

    def simulacion_monte_carlo(self, n_simulaciones: int = 1000,
             horizonte: int = DIAS_COTIZACION_ANUAL,
             rentabilidad: float | int | Mapping[str, float | int] | None = None,
             volatilidad: float | int | Mapping[str, float | int] | None = None,
             valor_inicial: float | int | None = None,
             rebalanceo: bool = True,
             semilla: int | None = None,
             guardar_graficos: bool = True) -> montecarlo.MonteCarlo:
        """
        Realiza el algoritmo de simulación de montecarlo sobre la cartera.
        :param n_simulaciones: Número de trayectorias (iteraciones) a simular.
        :param horizonte: Número de sesiones bursátiles a simular (252 = un año).
        :param rentabilidad: Rentabilidad anual esperada en tanto por uno (0.07 = 7 %). Si es
            `None` se usa la histórica. En una cartera puede ser un número (el mismo para todos
            los activos) o un diccionario {activo: rentabilidad} para cambiar solo algunos.
        :param volatilidad: Volatilidad anual en tanto por uno (0.20 = 20 %). Mismas opciones que
            `rentabilidad`.
        :param valor_inicial: Valor de partida. Por defecto, el último precio del activo o 100
            para una cartera.
        :param rebalanceo: Solo para carteras. `True` para mantener los pesos constantes cada
            día (rebalanceo diario) y `False` para comprar al inicio y no tocar la cartera.
        :param semilla: Semilla del generador aleatorio, para obtener resultados reproducibles.
        :param guardar_graficos: `True` para borrar los gráficos de la simulación anterior y
            guardar los de esta en `models/graficos/` (trayectorias.png y distribucion.png).
        :return: El objeto MonteCarlo con los resultados de la simulación.
        """
        sim = montecarlo.MonteCarlo(self,
                                    n_simulaciones=n_simulaciones,
                                    horizonte=horizonte,
                                    rentabilidad=rentabilidad,
                                    volatilidad=volatilidad,
                                    valor_inicial=valor_inicial,
                                    rebalanceo=rebalanceo,
                                    semilla=semilla,
                                    guardar_graficos=guardar_graficos
        )
        sim.graficar()
        return sim