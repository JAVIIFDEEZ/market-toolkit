from __future__ import annotations

import hashlib
import warnings
from collections.abc import Mapping, Sequence
from itertools import combinations_with_replacement
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

import market_toolkit.models.informe as informe
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

    precio_activos: pd.DataFrame
    rendimiento: pd.Series
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
        self.precio_activos = juntar_series(activos, True, alineacion_temporal)
        # Validar pesos
        if not isinstance(pesos.index, pd.DatetimeIndex):
            raise ValueError("El índice de los pesos debe ser un DatetimeIndex.")
        # Cada peso se empareja con su activo por nombre, no por posición
        faltan = sorted(set(self.precio_activos.columns) - set(pesos.columns))
        sobran = sorted(set(pesos.columns) - set(self.precio_activos.columns))
        if faltan or sobran:
            raise ValueError(
                f"Las columnas de los pesos deben ser los activos de la cartera. "
                f"Faltan: {faltan or 'ninguno'}. Sobran: {sobran or 'ninguno'}.")
        pesos = pesos[list(self.precio_activos.columns)].sort_index()  # Mismo orden que los activos
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
        # Ajuste temporal entre los pesos y los activos
        fechas_activos = self.precio_activos.index[self.precio_activos.index >= pesos.index[0]]
        pesos = pesos.reindex(pesos.index.union(fechas_activos))
        if pesos.index[0] < self.precio_activos.index[0]:
            warnings.warn(
                "Hay pesos configurados para antes de la existencia de algunos activos. "
                "La cartera empieza en la primera sesión con los últimos pesos indicados "
                "hasta entonces.",
                UserWarning,
                stacklevel=2,
            )
        elif pesos.index[0] > self.precio_activos.index[0]:
            warnings.warn(
                "Hay activos configurados para antes de la existencia de los pesos. "
                "Se truncan para que el día de inicio coincida con el de los pesos.",
                UserWarning,
                stacklevel=2,
            )
            self.precio_activos = self.precio_activos[pesos.index[0]:]
        if pesos.index[-1] > self.precio_activos.index[-1]:
            warnings.warn(
                "Hay pesos configurados para después de la existencia de los activos. "
                "Se truncan para que el día de fin coincida con el de los activos.",
                UserWarning,
                stacklevel=2,
            )
            pesos = pesos[:self.precio_activos.index[-1]]
        elif pesos.index[-1] < self.precio_activos.index[-1]:
            pesos = pesos.reindex(self.precio_activos.index).ffill()
        # Informacion de cada activo, sobre las fechas definitivas de la cartera
        self.metadatos_activos = self._calcular_metadatos_activos(activos)
        self.metadatos_activos.columns.name = None
        self.metadatos_activos.index.name = "Información"
        # Pesos de los activos. Cada fila introducida por el usuario representa un rebalanceo de
        # los pesos. Para el resto del tiempo, se simula la evolución de los pesos según las
        # rentabilidades de los activos asociados.
        self.pesos = self._calcular_pesos_activos(
            pesos,
            self.precio_activos.pct_change(fill_method=None)
        )
        # Metadatos de los activos
        self.metadatos = {activo.activo: activo.metadatos for activo in activos}
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
        rentabilidades = self.precio_activos.pct_change(fill_method=None)
        medias = rentabilidades.mean()
        desviaciones = rentabilidades.std()
        rentabilidades_anual = (1 + medias) ** DIAS_COTIZACION_ANUAL - 1
        volatilidades_anual = desviaciones * np.sqrt(DIAS_COTIZACION_ANUAL)
        info.loc["moneda"] = "USD"
        info.loc["inicio"] = self.precio_activos.index[0].date()
        info.loc["fin"] = self.precio_activos.index[-1].date()
        info.loc["observaciones"] = len(self.precio_activos)
        info.loc["media_diaria"] = medias
        info.loc["desviacion_tipica_diaria"] = desviaciones
        info.loc["rentabilidad_anualizada"] = rentabilidades_anual
        info.loc["volatilidad_anualizada"] = volatilidades_anual
        return info

    def _calcular_pesos_activos(
            self,
            pesos: pd.DataFrame,
            rentabilidades: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Cálculo automatico de los pesos de la cartera en función de la evolución de sus activos
        asociados.
        :param pesos: Pesos con los rebalances introducidos con el usuaio. El resto de días son NaN.
        :param rentabilidades: Rentabilidades de los activos asociados.
        :return: Los pesos con los que empieza cada sesión de los activos. Los pesos nuevos se
            aplican ya al rendimiento de su propia fecha o, si no hay sesión ese día, al de la
            siguiente sesión.
        """
        # Cada cambio de pesos se traslada a la primera sesión igual o posterior a su fecha
        cambios = pesos.dropna()
        posiciones = rentabilidades.index.searchsorted(cambios.index)
        con_sesion = posiciones < len(rentabilidades.index)
        cambios = cambios[con_sesion]
        cambios.index = rentabilidades.index[posiciones[con_sesion]]
        cambios = cambios[~cambios.index.duplicated(keep="last")]
        self._sesiones_cambio = cambios.index
        # Tramos entre cambios de pesos
        tramos = pd.Series(
            rentabilidades.index.isin(cambios.index),
            index=rentabilidades.index
        ).cumsum()
        # Evolución de cada activo dentro del tramo hasta el cierre de la sesión anterior
        crecimiento = (1 + rentabilidades.fillna(0)).groupby(tramos).cumprod()
        factores = crecimiento.groupby(tramos).shift(1).fillna(1)
        # Evolución de los pesos, normalizados para que sumen 1
        pesos_evolucionados = cambios.reindex(rentabilidades.index).ffill() * factores
        return pesos_evolucionados.div(pesos_evolucionados.sum(axis=1), axis=0)

    @property
    def pesos_actuales(self) -> pd.Series:
        """Pesos de la cartera al cierre de su última sesión."""
        rendimientos = self.precio_activos.pct_change(fill_method=None).iloc[-1].fillna(0)
        pesos = self.pesos.iloc[-1] * (1 + rendimientos)
        return pesos / pesos.sum()

    def _rendimientos_cartera(self) -> pd.Series:
        """
        Calcula el rendimiento diario de la cartera: el rendimiento de cada activo por el peso
        con el que empieza la sesión.
        :return: Serie con los rendimientos diarios de la cartera.
        """
        rendimientos_activos = self.precio_activos.pct_change(fill_method=None)
        return (rendimientos_activos * self.pesos).dropna().sum(axis=1)

    def _calcular_estadisticos(self):
        """
        Determina distintos estadísticos de la cartera, como la rentabilidad media diaria, la
        volatilidad, la rentabilidad media anualizada y la volatilidad anualizada.
        """
        rendimientos = self._rendimientos_cartera()
        if len(rendimientos) < 2:
            raise InsufficientDataError(
                "La cartera no tiene suficientes fechas con precios de sus activos para "
                "calcular sus estadísticos.")
        self.rentabilidad_media = float(rendimientos.mean())
        self.desviacion_tipica = float(rendimientos.std())
        self.rentabilidad_anualizada = (1 + self.rentabilidad_media) ** DIAS_COTIZACION_ANUAL - 1
        self.volatilidad_anualizada = self.desviacion_tipica * np.sqrt(DIAS_COTIZACION_ANUAL)

    def correlacion(self, t: float, guardar: bool = True) -> pd.DataFrame:
        """
        Calcula la correlación de los rendimientos diarios de los activos durante los últimos
        `t` años de la cartera. Cada pareja de activos se calcula con sus propias fechas comunes,
        en USD.
        :param t: Años hacia atrás desde la última fecha de la cartera (admite fracciones).
        :param guardar: `True` para guardar la matriz como imagen en
            `models/graficos/correlacion.png`.
        :return: DataFrame con la matriz de correlaciones.
        """
        if not t > 0:
            raise ValueError("El número de años `t` debe ser mayor que 0.")
        ultima_fecha = self.precio_activos.index[-1]
        desde = ultima_fecha - pd.Timedelta(days=t * 365.25)
        if desde < self.precio_activos.index[0]:
            warnings.warn(
                f"La cartera solo tiene datos desde {self.precio_activos.index[0].date()}. "
                f"La correlación se calcula con ese periodo, más corto que {t} años.",
                UserWarning,
                stacklevel=2,
            )
        correlaciones, sesiones = self._matriz_correlacion(desde)
        if guardar:
            inicio = max(desde, self.precio_activos.index[0])
            self._guardar_grafico_correlacion(correlaciones, inicio, ultima_fecha, sesiones)
        return correlaciones

    def _matriz_correlacion(self, desde: pd.Timestamp) -> tuple[pd.DataFrame, list[int]]:
        """
        Calcula la correlación de los rendimientos diarios en USD posteriores a una fecha, con
        las fechas comunes de cada pareja de activos.
        :param desde: Fecha a partir de la cual se cuentan los rendimientos.
        :return: Matriz de correlaciones y número de sesiones de cada pareja.
        """
        ultima_fecha = self.precio_activos.index[-1]
        # Precios en USD de cada activo con su propio calendario, en el periodo de la cartera
        precios = juntar_series(
            self._series,
            True,
            None
        ).loc[self.precio_activos.index[0]:ultima_fecha]
        nombres = list(self.precio_activos.columns)
        correlaciones = pd.DataFrame(np.eye(len(nombres)), index=nombres, columns=nombres)
        sesiones = []
        for activo_a, activo_b in combinations_with_replacement(nombres, 2):
            columnas = [activo_a] if activo_a == activo_b else [activo_a, activo_b]
            # Rendimientos de la pareja entre sus fechas comunes consecutivas
            rendimientos = precios[columnas].dropna().pct_change(fill_method=None).dropna()
            rendimientos = rendimientos[rendimientos.index > desde]
            if len(rendimientos) < 2:
                raise InsufficientDataError(
                    f"No hay suficientes sesiones comunes de {activo_a} y {activo_b} desde "
                    f"{desde.date()} para calcular la correlación.")
            sesiones.append(len(rendimientos))
            if activo_a != activo_b:
                valor = rendimientos[activo_a].corr(rendimientos[activo_b])
                correlaciones.loc[activo_a, activo_b] = valor
                correlaciones.loc[activo_b, activo_a] = valor
        return correlaciones, sesiones

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
        Guarda la matriz de correlaciones en `models/graficos/correlacion.png`.
        :param correlaciones: Matriz de correlaciones.
        :param inicio: Primera fecha del periodo, para el título.
        :param fin: Última fecha del periodo, para el título.
        :param sesiones: Número de sesiones de cada pareja de activos, para el título.
        """
        figura = Figure(figsize=self._tamano_correlacion(len(correlaciones)),
                        facecolor=montecarlo.COLORES["superficie"])
        self._dibujar_correlacion(figura, correlaciones, inicio, fin, sesiones)
        montecarlo.CARPETA_GRAFICOS.mkdir(parents=True, exist_ok=True)
        figura.savefig(montecarlo.CARPETA_GRAFICOS / "correlacion.png", dpi=150,
                       bbox_inches="tight", facecolor=montecarlo.COLORES["superficie"])
        (montecarlo.CARPETA_GRAFICOS / "correlacion.firma").write_text(self._firma)

    @staticmethod
    def _tamano_correlacion(n_activos: int) -> tuple[float, float]:
        """Tamaño de la figura de correlación según el número de activos."""
        lado = max(5.0, 1.1 * n_activos + 2)
        return lado + 1, lado

    @staticmethod
    def _dibujar_correlacion(figura: Figure, correlaciones: pd.DataFrame, inicio: pd.Timestamp,
                             fin: pd.Timestamp, sesiones: list[int]) -> None:
        """
        Dibuja la matriz de correlaciones como una cuadrícula con escala de -1 a 1.
        :param figura: Figura vacía en la que dibujar.
        :param correlaciones: Matriz de correlaciones.
        :param inicio: Primera fecha del periodo, para el título.
        :param fin: Última fecha del periodo, para el título.
        :param sesiones: Número de sesiones de cada pareja de activos, para el título.
        """
        n_activos = len(correlaciones)
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

    def plots_report(self, mostrar: bool = True, carpeta: str | Path | None = None,
                     guardar: bool = True) -> dict[str, Figure]:
        """
        Genera el informe gráfico de la cartera en todo su periodo: evolución frente a sus
        activos, drawdown, evolución de los pesos, riesgo y rentabilidad, contribución de cada
        activo y correlaciones. Al guardarlos, cada PNG sustituye al del informe anterior; no
        afecta a `correlacion.png` ni a los gráficos de la simulación.
        :param mostrar: `True` para mostrar los gráficos por pantalla.
        :param carpeta: Carpeta de destino. Por defecto, `models/graficos/informe/`.
        :param guardar: `True` para guardar los gráficos como PNG.
        :return: Diccionario {nombre: figura} con los gráficos.
        """
        carpeta = Path(carpeta) if carpeta is not None else (
            montecarlo.CARPETA_GRAFICOS / "informe")
        fondo = montecarlo.COLORES["superficie"]
        crear = plt.figure if mostrar else Figure

        def nueva(tamano: tuple[float, float]) -> Figure:
            return crear(figsize=tamano, facecolor=fondo, layout="constrained")

        inicio, fin = self.precio_activos.index[[0, -1]]
        valor = informe.valor_cartera(self._rendimientos_cartera(), inicio)
        colores = informe.colores_activos(self.pesos)
        figuras = {nombre: nueva(tamano) for nombre, tamano in {
            "evolucion": (11, 6),
            "drawdown": (11, 4),
            "pesos": (11, 5),
            "riesgo_rentabilidad": (9, 6),
            "contribucion": (9, max(3.5, 0.5 * self.precio_activos.shape[1] + 1.5)),
            "correlacion": self._tamano_correlacion(self.precio_activos.shape[1]),
        }.items()}
        informe.dibujar_evolucion(figuras["evolucion"], self.precio_activos, valor, colores)
        informe.dibujar_drawdown(figuras["drawdown"], valor)
        informe.dibujar_pesos(figuras["pesos"], self.pesos, colores,
                              self._sesiones_cambio[self._sesiones_cambio > inicio])
        informe.dibujar_riesgo_rentabilidad(
            figuras["riesgo_rentabilidad"],
            self.metadatos_activos.loc["volatilidad_anualizada"].astype(float),
            self.metadatos_activos.loc["rentabilidad_anualizada"].astype(float),
            self.volatilidad_anualizada,
            self.rentabilidad_anualizada,
        )
        rendimientos_activos = self.precio_activos.pct_change(fill_method=None)
        informe.dibujar_contribuciones(
            figuras["contribucion"],
            informe.contribuciones(rendimientos_activos, self.pesos, valor),
            inicio,
            fin,
        )
        correlaciones, sesiones = self._matriz_correlacion(inicio)
        self._dibujar_correlacion(figuras["correlacion"], correlaciones, inicio, fin, sesiones)
        if guardar:
            carpeta.mkdir(parents=True, exist_ok=True)
            for nombre, figura in figuras.items():
                figura.savefig(carpeta / f"{nombre}.png", dpi=150, facecolor=fondo)
        if mostrar:
            plt.show()
        return figuras

    def resumen(self) -> dict:
        """
        Devuelve la información principal de la cartera y sus estadísticos.
        :return: Diccionario con los activos, los pesos actuales y los estadísticos de la cartera.
        """
        return {
            "precio_activos": list(self.precio_activos.columns),
            "pesos_actuales": self.pesos_actuales.to_dict(),
            "moneda": "USD",
            "inicio": self.precio_activos.index[0].date(),
            "fin": self.precio_activos.index[-1].date(),
            "observaciones": len(self.precio_activos),
            "media_diaria": self.rentabilidad_media,
            "desviacion_tipica_diaria": self.desviacion_tipica,
            "rentabilidad_anualizada": self.rentabilidad_anualizada,
            "volatilidad_anualizada": self.volatilidad_anualizada,
        }

    def report(self, tasa_libre_riesgo: float = 0.0, max_volatilidad: float = 0.30,
               max_drawdown: float = 0.20) -> str:
        """Genera un informe Markdown con métricas y advertencias de riesgo.
        :param tasa_libre_riesgo: Tasa libre de riesgo anual en tanto por uno.
        :param max_volatilidad: Umbral anual de volatilidad que genera una advertencia.
        :param max_drawdown: Umbral de drawdown máximo que genera una advertencia.
        :return: Informe de la cartera en Markdown.
        """
        parametros = {
            "tasa_libre_riesgo": tasa_libre_riesgo,
            "max_volatilidad": max_volatilidad,
            "max_drawdown": max_drawdown,
        }
        for nombre, valor in parametros.items():
            if (isinstance(valor, bool)
                    or not isinstance(valor, (int, float, np.integer, np.floating))
                    or not np.isfinite(valor)):
                raise ValueError(f"`{nombre}` debe ser un número finito.")
        if max_volatilidad < 0 or max_drawdown < 0:
            raise ValueError("Los umbrales de volatilidad y drawdown deben ser no negativos.")

        rendimientos_activos = self.precio_activos.pct_change(fill_method=None)
        pesos_anteriores = self.pesos.reindex(self.precio_activos.index).ffill().shift(1)
        rendimientos = (rendimientos_activos * pesos_anteriores).dropna().sum(axis=1)
        crecimiento = (1 + rendimientos).cumprod()
        drawdowns = crecimiento.div(crecimiento.cummax()).sub(1)
        drawdown_maximo = float(-drawdowns.min())
        volatilidad_diaria = float(rendimientos.std())
        if volatilidad_diaria == 0:
            sharpe = None
        else:
            exceso_diario = rendimientos - tasa_libre_riesgo / DIAS_COTIZACION_ANUAL
            sharpe = float(
                exceso_diario.mean() / volatilidad_diaria * np.sqrt(DIAS_COTIZACION_ANUAL)
            )

        pesos_actuales = self.pesos.iloc[-1]
        advertencias = []
        if self.volatilidad_anualizada > max_volatilidad:
            advertencias.append(
                f"La volatilidad anualizada ({self.volatilidad_anualizada:.2%}) supera "
                f"el umbral de {max_volatilidad:.2%}."
            )
        if drawdown_maximo > max_drawdown:
            advertencias.append(
                f"El drawdown maximo ({drawdown_maximo:.2%}) supera "
                f"el umbral de {max_drawdown:.2%}."
            )
        for activo, peso in pesos_actuales[pesos_actuales > 0.50].items():
            advertencias.append(
                f"Concentracion elevada en **{activo}**: peso actual de {peso:.2%} "
                "(umbral: 50.00%)."
            )

        sharpe_texto = "No disponible (volatilidad cero)" if sharpe is None else f"{sharpe:.2f}"
        lineas = [
            "# Informe de cartera",
            "",
            "## Resumen",
            "",
            "- **Moneda:** USD",
            f"- **Periodo:** {self.precio_activos.index[0].date()} a "
            f"{self.precio_activos.index[-1].date()}",
            f"- **Observaciones de precios:** {len(self.precio_activos)}",
            f"- **Activos:** {', '.join(map(str, self.precio_activos.columns))}",
            "",
            "## Métricas",
            "",
            f"- **Rentabilidad anualizada:** {self.rentabilidad_anualizada:.2%}",
            f"- **Volatilidad anualizada:** {self.volatilidad_anualizada:.2%}",
            f"- **Sharpe anualizado:** {sharpe_texto}",
            f"- **Drawdown máximo:** {drawdown_maximo:.2%}",
            "",
            "## Pesos actuales",
            "",
            "| Activo | Peso |",
            "| --- | ---: |",
        ]
        lineas.extend(f"| {activo} | {peso:.2%} |" for activo, peso in pesos_actuales.items())
        lineas.extend(["", "## Diagnosticos y advertencias", ""])
        if advertencias:
            lineas.extend(f"- {advertencia}" for advertencia in advertencias)
        else:
            lineas.append("Sin advertencias con los umbrales indicados.")
        return "\n".join(lineas)

    def simulacion_monte_carlo(self, n_simulaciones: int = 1000,
             horizonte: int = DIAS_COTIZACION_ANUAL,
             rentabilidad: float | int | Mapping[str, float | int] | None = None,
             volatilidad: float | int | Mapping[str, float | int] | None = None,
             valor_inicial: float | int | None = None,
             rebalanceo: bool = False,
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
        :param rebalanceo: `False` (por defecto) para comprar al inicio y no tocar la cartera y
            `True` para mantener los pesos constantes cada día (rebalanceo diario).
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
