import hashlib
import warnings
from collections.abc import Mapping, Sequence
from itertools import combinations_with_replacement
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

import market_toolkit.models as models
import market_toolkit.models.informe as informe
import market_toolkit.simulation.montecarlo as montecarlo
from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.exceptions import DataValidationError, InsufficientDataError
from market_toolkit.models.series import FinancialSeries, MacroSeries, SerieTemporal
from market_toolkit.preprocessing import juntar_series


class Portfolio:
    """
    Clase que modela una cartera de inversión.
    """
    TOLERANCIA_PESOS = 1e-6  # Margen para considerar que los pesos de una fecha suman 1
    MACRO_ADMITIDOS = {
        "DGS10",  # Bono EE.UU. 10 años, % diario
        "DGS2",  # Bono EE.UU. 2 años, % diario
        "IRLTLT01ESM156N",  # Bono España 10 años, % mensual
        "IRLTLT01DEM156N"  # Bund 10 años, % mensual
    }

    precio_activos: pd.DataFrame
    rendimiento: pd.Series
    pesos: pd.DataFrame
    metadatos_activos: pd.DataFrame
    metadatos: dict
    rentabilidad_media: float
    desviacion_tipica: float
    rentabilidad_anualizada: float
    volatilidad_anualizada: float

    def __init__(self, activos: Sequence[SerieTemporal], pesos: pd.DataFrame, *,
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
        n_activos = len(activos)
        activos_macro = [activo for activo in activos if isinstance(activo, MacroSeries)
                               and activo.activo in self.MACRO_ADMITIDOS]
        activos_financiero = [activo for activo in activos if isinstance(activo, FinancialSeries)
                               and activo.tipo_activo != models.TipoActivo.INDICE]
        activos = activos_macro + activos_financiero
        if len(activos) != n_activos:
            raise DataValidationError(
                f"Se han introducido activos no válidos en la cartera. "
                f"Se permiten series financieras que no sean índices y "
                f"las siguientes series macro: {', '.join(self.MACRO_ADMITIDOS)}"
            )
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
        # Ajuste temporal entre los pesos y los activos
        inicio_activos = self.precio_activos.index[0]
        fin_activos = self.precio_activos.index[-1]
        fechas_activos = self.precio_activos.index[self.precio_activos.index >= pesos.index[0]]
        pesos = pesos.reindex(pesos.index.union(fechas_activos))
        if pesos.index[0] < inicio_activos:
            warnings.warn(
                "Hay pesos configurados para antes de la existencia de algunos activos. "
                "Se truncan para que el día de inicio coincida con el de los activos.",
                UserWarning,
                stacklevel=2,
            )
            pesos_iniciales = pesos.loc[pesos.index < inicio_activos].iloc[-1]
            pesos = pesos[inicio_activos:]
            if pesos.iloc[0].isnull().any():
                pesos.iloc[0] = pesos_iniciales
        elif pesos.index[0] > inicio_activos:
            warnings.warn(
                "Hay activos configurados para antes de la existencia de los pesos. "
                "Se truncan para que el día de inicio coincida con el de los pesos.",
                UserWarning,
                stacklevel=2,
            )
            self.precio_activos = self.precio_activos[pesos.index[0]:]
        if pesos.index[-1] > fin_activos:
            warnings.warn(
                "Hay pesos configurados para después de la existencia de los activos. "
                "Se truncan para que el día de fin coincida con el de los activos.",
                UserWarning,
                stacklevel=2,
            )
            pesos = pesos[:fin_activos]
        elif pesos.index[-1] < fin_activos:
            pesos = pesos.reindex(self.precio_activos.index).ffill()
        # Informacion de cada activo, sobre las fechas definitivas de la cartera
        self.metadatos_activos = self._calcular_metadatos_activos(activos)
        self.metadatos_activos.columns.name = None
        self.metadatos_activos.index.name = "Información"
        # Pesos de los activos. Cada fila introducida por el usuario representa un rebalanceo de
        # los pesos. Para el resto del tiempo, se simula la evolución de los pesos según las
        # rentabilidades de los activos asociados.
        self._ultimo_rebalanceo = pesos.last_valid_index()
        self.pesos = self._calcular_pesos_activos(
            pesos,
            self.precio_activos.pct_change(fill_method=None)
        )
        self._firma = hashlib.sha256(pesos.sort_index(axis=1).to_csv().encode()).hexdigest()
        # Metadatos de los activos
        self.metadatos = {activo.activo: activo.metadatos for activo in activos}
        # Calcular estadisticos
        self._calcular_estadisticos()
        self._borrar_correlacion_si_cambia()

    def _calcular_metadatos_activos(self, activos: Sequence[SerieTemporal]) -> pd.DataFrame:
        """
        Recalcula los metadatos de los activos que forman la cartera tras la alineacion temporal.
        :param activos: Lista de series temporales de la cartera.
        :return: DataFrame en el que cada columna es un activo y cada fila un metadato
        """
        info = pd.DataFrame(
            [activo.resumen() for activo in activos]
        ).set_index("activo").T
        rentabilidades = self.precio_activos.pct_change().dropna()
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
        self.rendimiento = self._rendimientos_cartera()
        if len(self.rendimiento) < 2:
            raise InsufficientDataError(
                "La cartera no tiene suficientes fechas con precios de sus activos para "
                "calcular sus estadísticos.")
        self.rentabilidad_media = float(self.rendimiento.mean())
        self.desviacion_tipica = float(self.rendimiento.std())
        self.rentabilidad_anualizada = (1 + self.rentabilidad_media) ** DIAS_COTIZACION_ANUAL - 1
        self.volatilidad_anualizada = self.desviacion_tipica * np.sqrt(DIAS_COTIZACION_ANUAL)

    def correlacion(self, t: float, guardar: bool = True) -> pd.DataFrame:
        """
        Calcula la correlación de los rendimientos diarios de los activos durante los últimos
        `t` años de la cartera, en USD y con las fechas de la cartera.
        :param t: Años hacia atrás desde la última fecha de la cartera (admite fracciones).
        :param guardar: `True` para guardar la matriz como imagen en
            `simulation/graficos/correlacion.png`.
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
        correlaciones = self._matriz_correlacion(desde, ultima_fecha)
        if guardar:
            inicio = max(desde, self.precio_activos.index[0])
            self._guardar_grafico_correlacion(correlaciones, inicio, ultima_fecha)
        return correlaciones

    def _matriz_correlacion(
            self,
            desde: pd.Timestamp,
            hasta: pd.Timestamp,
    ) -> pd.DataFrame:
        """Calcula correlaciones por parejas sin guardar archivos ni emitir advertencias.
        :param desde: Límite inferior exclusivo del periodo.
        :param hasta: Límite superior inclusivo del periodo.
        :return: Matriz de correlaciones.
        """
        nombres = list(self.precio_activos.columns)
        correlaciones = pd.DataFrame(np.eye(len(nombres)), index=nombres, columns=nombres)
        for activo_a, activo_b in combinations_with_replacement(nombres, 2):
            columnas = [activo_a] if activo_a == activo_b else [activo_a, activo_b]
            rendimientos = self.precio_activos[columnas].pct_change(fill_method=None).dropna()
            dentro_periodo = (rendimientos.index > desde) & (rendimientos.index <= hasta)
            rendimientos = rendimientos.loc[dentro_periodo]
            if len(rendimientos) < 2:
                raise InsufficientDataError(
                    f"No hay suficientes sesiones comunes de {activo_a} y {activo_b} entre {desde} "
                    f"y {hasta} para calcular la correlación.")
            if activo_a != activo_b:
                valor = rendimientos[activo_a].corr(rendimientos[activo_b])
                correlaciones.loc[activo_a, activo_b] = valor
                correlaciones.loc[activo_b, activo_a] = valor
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
                                     fin: pd.Timestamp) -> None:
        """
        Guarda la matriz de correlaciones en `simulation/graficos/correlacion.png`.
        :param correlaciones: Matriz de correlaciones.
        :param inicio: Primera fecha del periodo, para el título.
        :param fin: Última fecha del periodo, para el título.
        """
        figura = Figure(figsize=self._tamano_correlacion(len(correlaciones)),
                        facecolor=montecarlo.COLORES["superficie"])
        self._dibujar_correlacion(figura, correlaciones, inicio, fin, len(self.precio_activos))
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
                             fin: pd.Timestamp, n_sesiones: int) -> None:
        """
        Dibuja la matriz de correlaciones como una cuadrícula con escala de -1 a 1.
        :param figura: Figura vacía en la que dibujar.
        :param correlaciones: Matriz de correlaciones.
        :param inicio: Primera fecha del periodo, para el título.
        :param fin: Última fecha del periodo, para el título.
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
        eje.set_title(
            f"Correlación de rendimientos diarios\n{inicio.date()} a {fin.date()} · "
            f"cartera con {n_sesiones} sesiones en total",
            loc="left", color=montecarlo.COLORES["texto"], fontsize=12)

    def plots_report(self, mostrar: bool = True, carpeta: str | Path | None = None,
                     guardar: bool = True) -> dict[str, Figure]:
        """
        Genera el informe gráfico de la cartera en todo su periodo: evolución frente a sus
        activos, drawdown, evolución de los pesos, riesgo y rentabilidad, contribución de cada
        activo y correlaciones. Al guardarlos, cada PNG sustituye al del informe anterior; no
        afecta a `correlacion.png` ni a los gráficos de la simulación.
        :param mostrar: `True` para mostrar los gráficos por pantalla.
        :param carpeta: Carpeta de destino. Por defecto, `simulation/graficos/informe/`.
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
        correlaciones = self._matriz_correlacion(inicio, fin)
        self._dibujar_correlacion(
            figuras["correlacion"],
            correlaciones,
            inicio,
            fin,
            len(self.precio_activos)
        )
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

    def report(
            self,
            tasa_libre_riesgo: float = 0.0,
            max_volatilidad: float = 0.30,
            max_drawdown: float = 0.20,
            *,
            ruta: str | None = None,
            confianza_es: float = 0.95,
            max_concentracion: float = 0.50,
            max_correlacion: float = 0.80,
            min_historial: int = 252,
            min_activos_efectivos: float = 3.0,
            max_correlacion_diversificada: float = 0.30,
            min_sharpe: float = 1.0,
            min_cobertura: float = 0.90,
    ) -> str:
        """Devuelve un informe Markdown de rentabilidad, riesgo y diversificación.

        La atribución por activo usa contribuciones diarias ponderadas por los pesos vigentes
        al cierre anterior y las encadena para que sumen la rentabilidad total compuesta.
        El Expected Shortfall se estima históricamente sobre los rendimientos diarios.

        :param tasa_libre_riesgo: Tasa anual en tanto por uno para Sharpe y Sortino.
        :param max_volatilidad: Umbral anual de volatilidad para emitir una advertencia.
        :param max_drawdown: Umbral de drawdown para emitir una advertencia.
        :param ruta: Ruta opcional donde guardar el informe con codificación UTF-8.
        :param confianza_es: Nivel de confianza del Expected Shortfall histórico.
        :param max_concentracion: Peso máximo aceptado para un activo.
        :param max_correlacion: Correlación media máxima antes de emitir advertencia.
        :param min_historial: Número mínimo de rendimientos diarios esperados.
        :param min_activos_efectivos: Número efectivo mínimo para considerar diversificada.
        :param max_correlacion_diversificada: Correlación máxima para destacar diversificación.
        :param min_sharpe: Sharpe mínimo para destacar esta fortaleza.
        :param min_cobertura: Cobertura mínima de datos por activo durante el periodo.
        :return: Informe Markdown en español.
        """
        parametros_numericos = {
            "tasa_libre_riesgo": tasa_libre_riesgo,
            "max_volatilidad": max_volatilidad,
            "max_drawdown": max_drawdown,
            "confianza_es": confianza_es,
            "max_concentracion": max_concentracion,
            "max_correlacion": max_correlacion,
            "min_activos_efectivos": min_activos_efectivos,
            "max_correlacion_diversificada": max_correlacion_diversificada,
            "min_sharpe": min_sharpe,
            "min_cobertura": min_cobertura,
        }
        for clave, valor in parametros_numericos.items():
            if (isinstance(valor, bool)
                    or not isinstance(valor, (int, float, np.integer, np.floating))
                    or not np.isfinite(valor)):
                raise ValueError(f"`{clave}` debe ser un número finito.")
        if (isinstance(min_historial, bool)
                or not isinstance(min_historial, (int, np.integer))):
            raise ValueError("`min_historial` debe ser un entero positivo.")
        min_historial = int(min_historial)
        if min_historial < 1:
            raise ValueError("`min_historial` debe ser un entero positivo.")
        if not 0 < confianza_es < 1:
            raise ValueError("`confianza_es` debe estar entre 0 y 1, sin incluirlos.")
        if not 0 <= max_concentracion <= 1:
            raise ValueError("`max_concentracion` debe estar entre 0 y 1.")
        if not -1 <= max_correlacion <= 1 or not -1 <= max_correlacion_diversificada <= 1:
            raise ValueError("Los umbrales de correlación deben estar entre -1 y 1.")
        if min_activos_efectivos <= 0 or min_cobertura < 0 or min_cobertura > 1:
            raise ValueError("Los umbrales de diversificación y cobertura no son válidos.")
        if max_volatilidad < 0 or max_drawdown < 0:
            raise ValueError("Los umbrales de volatilidad y drawdown deben ser no negativos.")

        rendimientos_activos = self.precio_activos.pct_change(fill_method=None)
        # `self.pesos` ya son los pesos con los que empieza cada sesión: no se desplazan otra vez
        contribuciones_diarias = (rendimientos_activos * self.pesos).dropna()
        rendimientos = self.rendimiento

        factores_crecimiento = 1 + rendimientos
        crecimiento = factores_crecimiento.cumprod()
        valor_final = float(crecimiento.iloc[-1])
        rentabilidad_acumulada = valor_final - 1
        numero_sesiones = len(self.precio_activos)
        if valor_final > 0:
            cagr = valor_final ** (DIAS_COTIZACION_ANUAL / numero_sesiones) - 1
        else:
            cagr = None
        exceso_diario = rendimientos - tasa_libre_riesgo / DIAS_COTIZACION_ANUAL
        sharpe = float(
            exceso_diario.mean() / self.desviacion_tipica * np.sqrt(DIAS_COTIZACION_ANUAL)
        )
        desviacion_bajista = float(np.sqrt(np.square(exceso_diario.clip(upper=0)).mean()))
        sortino = (
            float(exceso_diario.mean() / desviacion_bajista * np.sqrt(DIAS_COTIZACION_ANUAL))
            if desviacion_bajista > 0 else None
        )
        drawdown_maximo = -(crecimiento / crecimiento.cummax() - 1).min()
        cuantil_rendimiento = rendimientos.quantile(1 - confianza_es)
        cola_perdedora = rendimientos[rendimientos <= cuantil_rendimiento]
        expected_shortfall = float(-cola_perdedora.mean())
        rendimientos_mensuales = (1 + rendimientos).groupby(
            rendimientos.index.to_period("M")
        ).prod() - 1

        pesos_actuales = self.pesos_actuales
        exposicion_total = float(pesos_actuales.sum())
        pesos_para_hhi = pesos_actuales / exposicion_total if exposicion_total else pesos_actuales
        hhi = float(np.square(pesos_para_hhi).sum()) if exposicion_total else None
        activos_efectivos = 1 / hhi if hhi and hhi > 0 else None
        inicio, fin = self.precio_activos.index[[0, -1]]
        correlaciones = self._matriz_correlacion(inicio, fin)
        indices_superiores = np.triu_indices_from(correlaciones.to_numpy(), k=1)
        valores_correlacion = correlaciones.to_numpy()[indices_superiores]
        valores_correlacion = valores_correlacion[np.isfinite(valores_correlacion)]
        correlacion_media = (
            float(valores_correlacion.mean()) if len(valores_correlacion) else None
        )
        pares_alta_correlacion = [
            (str(correlaciones.index[fila]), str(correlaciones.columns[columna]),
             float(correlaciones.iat[fila, columna]))
            for fila, columna in zip(*indices_superiores, strict=True)
            if np.isfinite(correlaciones.iat[fila, columna])
            and correlaciones.iat[fila, columna] > max_correlacion
        ]

        contribuciones_acumuladas = (contribuciones_diarias.mul(
            factores_crecimiento.iloc[::-1].cumprod().iloc[::-1].shift(-1, fill_value=1),
            axis=0,
        )).sum()
        tabla_activos = []
        for activo in self.precio_activos.columns:
            precios_activo = self.precio_activos[activo].dropna()
            retorno_activo = float(precios_activo.iloc[-1] / precios_activo.iloc[0] - 1)
            volatilidad_activo = self.metadatos_activos.loc["volatilidad_anualizada", activo]
            tabla_activos.append(
                (str(activo), float(pesos_actuales[activo]), retorno_activo,
                 volatilidad_activo, float(contribuciones_acumuladas[activo]))
            )

        coberturas = {}
        for activo in self.precio_activos.columns:
            serie = next(item for item in self._series if item.activo == activo)
            fechas_fuente = serie.serie_temporal.loc[inicio:fin].index
            coberturas[activo] = len(self.precio_activos.index.intersection(fechas_fuente)) / len(
                self.precio_activos
            )

        pesos_actuales = self.pesos_actuales  # Pesos al cierre de la última sesión
        advertencias = []
        fortalezas = []
        if  self.volatilidad_anualizada > max_volatilidad:
            advertencias.append(
                f"La volatilidad anualizada ({ self.volatilidad_anualizada:.2%}) supera "
                f"el umbral de {max_volatilidad:.2%}."
            )
        if drawdown_maximo > max_drawdown:
            advertencias.append(
                f"El drawdown máximo ({drawdown_maximo:.2%}) supera "
                f"el umbral de {max_drawdown:.2%}."
            )
        if pesos_actuales.max() > max_concentracion:
            activo_concentrado = pesos_actuales.idxmax()
            advertencias.append(
                f"Concentración elevada en **{activo_concentrado}**: exposición "
                f"actual de {pesos_actuales.max():.2%} (umbral: {max_concentracion:.2%})."
            )
        if valores_correlacion.size and correlacion_media > max_correlacion:
            advertencias.append(
                f"La correlación media entre activos ({correlacion_media:.2f}) supera "
                f"el umbral de {max_correlacion:.2f}."
            )
        for activo_a, activo_b, correlacion in pares_alta_correlacion:
            advertencias.append(
                f"Correlación elevada entre **{activo_a}** y **{activo_b}**: {correlacion:.2f}."
            )
        if numero_sesiones < min_historial:
            advertencias.append(
                f"Historial corto: {numero_sesiones} sesiones con rendimientos; "
                f"se requieren {min_historial} para alcanzar el umbral configurado."
            )
        for activo, cobertura in coberturas.items():
            if cobertura < min_cobertura:
                advertencias.append(
                    f"Cobertura temporal limitada para **{activo}**: {cobertura:.1%} "
                    f"(mínimo: {min_cobertura:.1%})."
                )

        if activos_efectivos is not None and activos_efectivos >= min_activos_efectivos:
            fortalezas.append(
                f"Diversificación por pesos: {activos_efectivos:.2f} activos efectivos."
            )
        if (correlacion_media is not None
                and correlacion_media <= max_correlacion_diversificada):
            fortalezas.append(
                f"Correlación media reducida entre activos ({correlacion_media:.2f})."
            )
        if drawdown_maximo <= max_drawdown:
            fortalezas.append(f"Drawdown histórico moderado ({drawdown_maximo:.2%}).")
        if sharpe is not None and sharpe >= min_sharpe:
            fortalezas.append(
                f"Sharpe elevado respecto al umbral ({sharpe:.2f} ≥ {min_sharpe:.2f})."
            )

        def porcentaje(valor: float | None) -> str:
            return "No disponible" if valor is None else f"{valor:.2%}"

        def ratio(valor: float | None) -> str:
            return "No disponible" if valor is None else f"{valor:.2f}"

        lineas = [
            "# Informe de cartera",
            "",
            "## Información general",
            "",
            f"- **Número de activos:** {len(self.precio_activos.columns)}",
            f"- **Periodo disponible:** {inicio.date()} a {fin.date()}",
            f"- **Observaciones:** {len(self.precio_activos)}",
            "- **Moneda de referencia:** USD",
            f"- **Último rebalanceo explícito:** {self._ultimo_rebalanceo.date()}"
        ]
        lineas.extend(
                f"  - {activo}: {peso:.2%}"
                for activo, peso in self.pesos.loc[self._ultimo_rebalanceo].items()
        )
        lineas.extend([
            f"- **Valor final de 100 iniciales:** {valor_final * 100:.2f}",
            "",
            "### Composición por activo",
            "",
            "| Activo | Peso actual | Rentabilidad histórica | "
            "Volatilidad anualizada | Contribución acumulada |",
            "| --- | ---: | ---: | ---: | ---: |",
        ])
        lineas.extend(
            f"| {activo} | {peso:.2%} | {retorno:.2%} | {volatilidad:.2%} | "
            f"{contribucion:.2%} |"
            for activo, peso, retorno, volatilidad, contribucion in tabla_activos
        )
        lineas.extend([
            "",
            "## Rentabilidad",
            "",
            f"- **Rentabilidad acumulada:** {rentabilidad_acumulada:.2%}",
            f"- **CAGR:** {porcentaje(cagr)}" + (
                " (no disponible porque el valor final no es positivo)" if cagr is None else ""
            ),
            f"- **Rentabilidad media diaria:** {rendimientos.mean():.3%}",
            f"- **Mejor día:** {rendimientos.idxmax().date()} ({rendimientos.max():.2%})",
            f"- **Peor día:** {rendimientos.idxmin().date()} ({rendimientos.min():.2%})",
            f"- **Mejor mes:** {rendimientos_mensuales.idxmax()} "
            f"({rendimientos_mensuales.max():.2%})",
            f"- **Peor mes:** {rendimientos_mensuales.idxmin()} "
            f"({rendimientos_mensuales.min():.2%})",
            "",
            "## Riesgo",
            "",
            f"- **Volatilidad anualizada:** {self.volatilidad_anualizada:.2%}",
            f"- **Drawdown máximo:** {drawdown_maximo:.2%}",
            f"- **Sharpe anualizado:** {ratio(sharpe)}",
            f"- **Sortino anualizado:** {ratio(sortino)}",
            f"- **Expected Shortfall ({confianza_es:.0%}, histórico diario):** "
            f"{expected_shortfall:.2%}",
            "",
            "## Diversificación y concentración",
            "",
            f"- **Índice HHI:** {ratio(hhi)}",
            f"- **Número efectivo de activos:** {ratio(activos_efectivos)}",
            f"- **Mayor exposición absoluta:** {pesos_actuales.max():.2%}",
            f"- **Correlación media:** {ratio(correlacion_media)}",
            "",
            "### Matriz de correlaciones diarias",
            "",
            "| Activo | " + " | ".join(map(str, correlaciones.columns)) + " |",
            "| --- | " + " | ".join("---:" for _ in correlaciones.columns) + " |",
        ])
        for activo, fila in correlaciones.iterrows():
            valores = ["No disponible" if pd.isna(valor) else f"{valor:.2f}"
                       for valor in fila]
            lineas.append(f"| {activo} | " + " | ".join(valores) + " |")
        lineas.extend(["", "## Diagnósticos y advertencias", ""])
        lineas.extend(
            [f"- {advertencia}" for advertencia in advertencias]
            if advertencias else ["Sin advertencias con los umbrales indicados."]
        )
        lineas.extend(["", "## Fortalezas", ""])
        lineas.extend(
            [f"- {fortaleza}" for fortaleza in fortalezas]
            if fortalezas else ["No se han detectado fortalezas según los umbrales configurados."]
        )
        informe = "\n".join(lineas)
        if ruta is not None:
            with open(ruta, "w", encoding="utf-8", newline="\n") as archivo:
                archivo.write(informe)
        return informe

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
            guardar los de esta en `simulation/graficos/` (trayectorias.png y distribucion.png).
        :return: El objeto MonteCarlo con los resultados de la simulación.
        """
        sim = montecarlo.MonteCarlo(
            self,
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
