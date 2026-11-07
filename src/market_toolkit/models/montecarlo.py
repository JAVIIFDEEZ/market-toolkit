from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from market_toolkit.config import DIAS_COTIZACION_ANUAL
from market_toolkit.exceptions import InsufficientDataError
from market_toolkit.models.series import FinancialSeries

if TYPE_CHECKING:
    # Solo para las anotaciones: Portfolio usa MonteCarlo y un import real sería circular
    from market_toolkit.models.portfolio import Portfolio

Supuesto = float | Mapping[str, float] | None

# Carpeta donde se guardan los gráficos de la última simulación
CARPETA_GRAFICOS = Path(__file__).parent / "graficos"

# Colores de los gráficos: aqua de claro a oscuro para las bandas de percentiles, negro
# semitransparente para las trayectorias de muestra, media en negro discontinuo y mediana en azul,
# aqua/naranja para ganancia/pérdida en la distribución y rojos solo para los umbrales del VaR
COLORES = {
    "superficie": "#fcfcfb",
    "texto": "#0b0b0b",
    "texto_secundario": "#52514e",
    "texto_tenue": "#898781",
    "rejilla": "#e1e0d9",
    "eje": "#c3c2b7",
    "trayectorias": "#0b0b0b",
    "banda_exterior": "#c4e9db",
    "banda_interior": "#8cd6bb",
    "media": "#0b0b0b",
    "mediana": "#2a78d6",
    "ganancia": "#1baf7a",
    "perdida": "#eb6834",
    "var_95": "#d03b3b",
    "var_99": "#8b1d1d",
}
GROSOR_REFERENCIAS = 2.5  # Grosor de las líneas de valores fijos (media, mediana, VaR...)


class MonteCarlo:
    """
    Simulación de Monte Carlo de la evolución del valor de un activo (`FinancialSeries`) o de
    una cartera (`Portfolio`). La simulación se lanza automáticamente al crear el objeto.

    Cada activo sigue un movimiento browniano geométrico: su rendimiento logarítmico diario es
    normal, con la volatilidad indicada y una deriva que hace que la rentabilidad esperada sea la
    indicada. En una cartera los activos se simulan a la vez, con las correlaciones históricas de
    sus rendimientos, y se combinan con los pesos actuales de la cartera.
    """

    trayectorias: pd.DataFrame
    rentabilidades: pd.Series
    volatilidades: pd.Series
    pesos: pd.Series | None

    def __init__(
        self,
        objetivo: FinancialSeries | Portfolio,
        *,
        n_simulaciones: int = 1000,
        horizonte: int = DIAS_COTIZACION_ANUAL,
        rentabilidad: Supuesto = None,
        volatilidad: Supuesto = None,
        valor_inicial: float | None = None,
        rebalanceo: bool = True,
        semilla: int | None = None,
        guardar_graficos: bool = True,
    ) -> None:
        """
        Inicializa y ejecuta la simulación.
        :param objetivo: El activo o la cartera a simular.
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
        """
        # Una cartera se reconoce por sus precios alineados y sus pesos (sin importar Portfolio)
        es_cartera = (isinstance(getattr(objetivo, "activos", None), pd.DataFrame)
                      and isinstance(getattr(objetivo, "pesos", None), pd.DataFrame))
        if not (isinstance(objetivo, FinancialSeries) or es_cartera):
            raise TypeError(
                f"Solo se puede simular una FinancialSeries o un Portfolio, no "
                f"{type(objetivo).__name__}.")
        if not isinstance(n_simulaciones, int) or n_simulaciones < 1:
            raise ValueError("El número de simulaciones debe ser un entero mayor que 0.")
        if not isinstance(horizonte, int) or horizonte < 1:
            raise ValueError("El horizonte debe ser un número entero de sesiones mayor que 0.")
        self.objetivo = objetivo
        self.n_simulaciones = n_simulaciones
        self.horizonte = horizonte
        self.rebalanceo = rebalanceo
        self.semilla = semilla

        if isinstance(objetivo, FinancialSeries):
            precios = objetivo.serie_temporal.to_frame()
            # Supuestos por defecto: los estadísticos que la serie calcula al crearse
            historicas = pd.Series({objetivo.activo: objetivo.rentabilidad_anualizada})
            vol_historicas = pd.Series({objetivo.activo: objetivo.volatilidad_anualizada})
            self.pesos = None
            por_defecto = float(objetivo.serie_temporal.iloc[-1])
        else:
            precios = objetivo.activos.dropna()  # Solo las fechas en las que cotizan todos
            historicas, vol_historicas = self._estadisticos_historicos(precios)
            # Pesos actuales de la cartera (última fila), emparejados por nombre con los precios
            self.pesos = objetivo.pesos.iloc[-1].reindex(precios.columns).astype(float)
            if self.pesos.isna().any():
                faltan = ", ".join(self.pesos.index[self.pesos.isna()])
                raise ValueError(f"La cartera no tiene pesos actuales para: {faltan}.")
            por_defecto = 100.0
        self.rentabilidades = self._aplicar_supuesto(historicas, rentabilidad, "rentabilidad")
        self.volatilidades = self._aplicar_supuesto(vol_historicas, volatilidad, "volatilidad")
        if (self.rentabilidades <= -1).any():
            raise ValueError("La rentabilidad anual debe ser mayor que -1 (-100 %).")
        if (self.volatilidades < 0).any():
            raise ValueError("La volatilidad no puede ser negativa.")
        self.valor_inicial = por_defecto if valor_inicial is None else float(valor_inicial)
        if self.valor_inicial <= 0:
            raise ValueError("El valor inicial debe ser mayor que 0.")
        self.correlaciones = precios.pct_change(fill_method=None).dropna().corr()
        self.fecha_inicio = precios.index[-1]
        self.trayectorias = self._simular()
        if guardar_graficos:
            self.guardar_graficos()

    @staticmethod
    def _estadisticos_historicos(precios: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """
        Calcula la rentabilidad y la volatilidad anualizadas de cada activo de una cartera con
        las mismas fórmulas que `FinancialSeries`, sobre las fechas comunes de la cartera.
        :param precios: Precios alineados de los activos.
        :return: Tupla (rentabilidades anuales, volatilidades anuales) por activo.
        """
        rendimientos = precios.pct_change(fill_method=None).dropna()
        if len(rendimientos) < 2:
            raise InsufficientDataError(
                "La cartera no tiene suficientes fechas en común para estimar los supuestos.")
        rentabilidades = (1 + rendimientos.mean()) ** DIAS_COTIZACION_ANUAL - 1
        volatilidades = rendimientos.std() * np.sqrt(DIAS_COTIZACION_ANUAL)
        return rentabilidades, volatilidades

    @staticmethod
    def _aplicar_supuesto(historico: pd.Series, supuesto: Supuesto, nombre: str) -> pd.Series:
        """
        Combina los valores históricos de cada activo con el supuesto indicado por el usuario.
        :param historico: Valor histórico de cada activo.
        :param supuesto: `None`, un número para todos los activos o un diccionario por activo.
        :param nombre: Nombre del supuesto, para los mensajes de error.
        :return: Serie con el valor que se usará para cada activo.
        """
        if supuesto is None:
            return historico.astype(float)
        if isinstance(supuesto, Mapping):
            desconocidos = sorted(set(supuesto) - set(historico.index))
            if desconocidos:
                raise ValueError(
                    f"La {nombre} indica activos que no están en la simulación: "
                    f"{', '.join(desconocidos)}.")
            valores = historico.astype(float).copy()
            valores.update(pd.Series(supuesto, dtype=float))
            return valores
        return pd.Series(float(supuesto), index=historico.index)

    def _factor_covarianzas(self, volatilidades_diarias: np.ndarray) -> np.ndarray:
        """
        Obtiene la matriz L tal que L·Lᵀ es la matriz de covarianzas diaria, para generar
        rendimientos correlacionados a partir de normales independientes.
        :param volatilidades_diarias: Volatilidad diaria de cada activo.
        :return: Matriz L (n_activos x n_activos).
        """
        correlaciones = self.correlaciones.fillna(0).to_numpy(copy=True)
        np.fill_diagonal(correlaciones, 1.0)
        covarianzas = np.outer(volatilidades_diarias, volatilidades_diarias) * correlaciones
        try:
            return np.linalg.cholesky(covarianzas)
        except np.linalg.LinAlgError:
            # Activos perfectamente correlacionados o sin volatilidad: la matriz no es definida
            # positiva y se usa la descomposición en autovalores (descartando los negativos)
            autovalores, autovectores = np.linalg.eigh(covarianzas)
            return autovectores * np.sqrt(np.clip(autovalores, 0, None))

    def _simular(self) -> pd.DataFrame:
        """
        Genera las trayectorias del valor del activo o de la cartera.
        :return: DataFrame con una columna por simulación y una fila por sesión (la primera
            fila es el valor inicial).
        """
        rng = np.random.default_rng(self.semilla)
        n_activos = len(self.rentabilidades)
        # Supuestos diarios: rentabilidad compuesta y volatilidad por la regla de la raíz
        media_diaria = (1 + self.rentabilidades.to_numpy()) ** (1 / DIAS_COTIZACION_ANUAL) - 1
        vol_diaria = self.volatilidades.to_numpy() / np.sqrt(DIAS_COTIZACION_ANUAL)
        # Deriva logarítmica para que el rendimiento diario esperado sea `media_diaria`
        deriva = np.log1p(media_diaria) - vol_diaria ** 2 / 2
        aleatorios = rng.standard_normal((self.horizonte, self.n_simulaciones, n_activos))
        choques = aleatorios @ self._factor_covarianzas(vol_diaria).T
        crecimiento = np.exp(deriva + choques)  # Valor de 1 € de cada activo tras cada sesión

        if self.pesos is None:
            factores = np.cumprod(crecimiento[:, :, 0], axis=0)
        elif self.rebalanceo:
            # Pesos constantes cada día: el crecimiento de la cartera es la media ponderada
            factores = np.cumprod(crecimiento @ self.pesos.to_numpy(), axis=0)
        else:
            # Compra inicial sin tocar: cada activo evoluciona por su cuenta
            factores = np.cumprod(crecimiento, axis=0) @ self.pesos.to_numpy()

        valores = self.valor_inicial * np.vstack([np.ones(self.n_simulaciones), factores])
        fechas = pd.bdate_range(self.fecha_inicio, periods=self.horizonte + 1, name="fecha")
        return pd.DataFrame(valores, index=fechas,
                            columns=pd.RangeIndex(self.n_simulaciones, name="simulacion"))

    @property
    def valores_finales(self) -> pd.Series:
        """Valor de cada simulación al final del horizonte."""
        return self.trayectorias.iloc[-1].rename("valor_final")

    @property
    def rentabilidades_finales(self) -> pd.Series:
        """Rentabilidad acumulada de cada simulación al final del horizonte (tanto por uno)."""
        return (self.valores_finales / self.valor_inicial - 1).rename("rentabilidad_final")

    def percentiles(self, niveles: Sequence[float] = (5, 25, 50, 75, 95)) -> pd.DataFrame:
        """
        Calcula los percentiles del valor en cada sesión del horizonte (para dibujar abanicos).
        :param niveles: Percentiles a calcular, entre 0 y 100.
        :return: DataFrame con una fila por sesión y una columna por percentil.
        """
        resultado = self.trayectorias.quantile(np.asarray(niveles) / 100, axis=1).T
        resultado.columns = [f"p{nivel:g}" for nivel in niveles]
        return resultado

    def var(self, confianza: float = 0.95) -> float:
        """
        Value at Risk: pérdida que no se supera con la confianza indicada al final del horizonte.
        :param confianza: Nivel de confianza (0.95 = 95 %).
        :return: Pérdida en tanto por uno sobre el valor inicial (positiva si es pérdida).
        """
        return float(-self.rentabilidades_finales.quantile(1 - confianza))

    def cvar(self, confianza: float = 0.95) -> float:
        """
        Conditional VaR (Expected Shortfall): pérdida media en el peor `1 - confianza` de los
        escenarios.
        :param confianza: Nivel de confianza (0.95 = 95 %).
        :return: Pérdida media en tanto por uno sobre el valor inicial (positiva si es pérdida).
        """
        rentabilidades = self.rentabilidades_finales
        peores = rentabilidades[rentabilidades <= rentabilidades.quantile(1 - confianza)]
        return float(-peores.mean())

    def resumen(self) -> dict:
        """
        Devuelve los parámetros de la simulación y los estadísticos del valor final.
        :return: Diccionario con los supuestos y los resultados.
        """
        finales = self.valores_finales
        return {
            "objetivo": self._nombre_objetivo,
            "n_simulaciones": self.n_simulaciones,
            "horizonte_sesiones": self.horizonte,
            "rentabilidad_anual_supuesta": self.rentabilidades.to_dict(),
            "volatilidad_anual_supuesta": self.volatilidades.to_dict(),
            "pesos": None if self.pesos is None else self.pesos.to_dict(),
            "valor_inicial": self.valor_inicial,
            "valor_final_medio": float(finales.mean()),
            "valor_final_mediano": float(finales.median()),
            "valor_final_p5": float(finales.quantile(0.05)),
            "valor_final_p95": float(finales.quantile(0.95)),
            "rentabilidad_media": float(self.rentabilidades_finales.mean()),
            "probabilidad_perdida": float((finales < self.valor_inicial).mean()),
            "var_95": self.var(0.95),
            "cvar_95": self.cvar(0.95),
        }

    @property
    def _nombre_objetivo(self) -> str:
        """Nombre del activo o de la cartera simulada, para el resumen y el gráfico."""
        if self.pesos is None:
            return self.objetivo.activo
        return f"Cartera ({', '.join(self.pesos.index)})"

    @property
    def _unidad(self) -> str:
        """
        Unidad del valor simulado: la moneda del activo, la moneda común de los activos de la
        cartera o, si no se conoce o la cartera mezcla monedas, "puntos".
        """
        if self.pesos is None:
            return self.objetivo.moneda or "puntos"
        info = getattr(self.objetivo, "info", None)
        if not isinstance(info, pd.DataFrame) or "moneda" not in info.index:
            return "puntos"
        monedas = {moneda for moneda in info.loc["moneda"] if isinstance(moneda, str) and moneda}
        return monedas.pop() if len(monedas) == 1 else "puntos"

    @property
    def _etiqueta_valor(self) -> str:
        """Etiqueta del eje del valor, con sus unidades."""
        return f"Valor ({self._unidad})"

    @staticmethod
    def _preparar_eje(eje) -> None:
        """Aplica el estilo común: fondo, rejilla horizontal fina y ejes discretos."""
        eje.set_facecolor(COLORES["superficie"])
        eje.grid(axis="y", color=COLORES["rejilla"], linewidth=0.8)
        eje.set_axisbelow(True)
        for lado in ("top", "right"):
            eje.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            eje.spines[lado].set_color(COLORES["eje"])
        eje.tick_params(colors=COLORES["texto_tenue"], labelsize=9)

    def _dibujar_trayectorias(self, figura: Figure, n_trayectorias: int) -> Figure:
        """
        Dibuja una muestra de trayectorias con las bandas de percentiles 5-95 y 25-75, la media
        y la mediana de cada sesión.
        :param figura: Figura vacía en la que dibujar.
        :param n_trayectorias: Número de trayectorias individuales a dibujar de fondo.
        :return: La figura dibujada.
        """
        eje = figura.subplots()
        self._preparar_eje(eje)
        percentiles = self.percentiles((5, 25, 50, 75, 95))
        media = self.trayectorias.mean(axis=1)
        fechas = self.trayectorias.index
        muestra = self.trayectorias.iloc[:, :min(n_trayectorias, self.n_simulaciones)]
        eje.plot(fechas, muestra.to_numpy(), color=COLORES["trayectorias"], linewidth=0.6,
                 alpha=0.12, zorder=1)
        eje.fill_between(fechas, percentiles["p5"], percentiles["p95"],
                         color=COLORES["banda_exterior"], alpha=0.85, linewidth=0, zorder=2,
                         label="Percentiles 5-95")
        eje.fill_between(fechas, percentiles["p25"], percentiles["p75"],
                         color=COLORES["banda_interior"], alpha=0.85, linewidth=0, zorder=3,
                         label="Percentiles 25-75")
        eje.plot(fechas, percentiles["p50"], color=COLORES["mediana"], linewidth=2, zorder=4,
                 label="Mediana")
        eje.plot(fechas, media, color=COLORES["media"], linewidth=2, linestyle="--", zorder=5,
                 label="Media")
        eje.axhline(self.valor_inicial, color=COLORES["texto_secundario"], linewidth=1,
                    zorder=5, label="Valor inicial")
        eje.plot([], [], color=COLORES["trayectorias"], alpha=0.35, linewidth=1,
                 label=f"Trayectorias (muestra de {muestra.shape[1]})")
        # Etiquetas directas solo al final de la media, la mediana y los extremos de la banda.
        # Se separan verticalmente si están demasiado cerca y llevan fondo para que ninguna
        # línea las atraviese
        etiquetas = sorted(
            (float(serie.iloc[-1]), nombre)
            for nombre, serie in (("p95", percentiles["p95"]), ("Media", media),
                                  ("Mediana", percentiles["p50"]), ("p5", percentiles["p5"])))
        y_min, y_max = eje.get_ylim()
        separacion = 0.045 * (y_max - y_min)
        posicion_anterior = -np.inf
        for valor, nombre in etiquetas:
            posicion = max(valor, posicion_anterior + separacion)
            eje.annotate(f"{nombre} {valor:,.2f}", (fechas[-1], posicion), xytext=(-4, 0),
                         textcoords="offset points", ha="right", va="center", fontsize=9,
                         color=COLORES["texto_secundario"], zorder=6,
                         bbox={"boxstyle": "round,pad=0.2", "facecolor": COLORES["superficie"],
                               "edgecolor": "none", "alpha": 0.85})
            posicion_anterior = posicion
        eje.set_xlim(fechas[0], fechas[-1])
        eje.xaxis.set_major_formatter(mdates.ConciseDateFormatter(eje.xaxis.get_major_locator()))
        eje.set_ylabel(self._etiqueta_valor, color=COLORES["texto_secundario"])
        eje.set_title(
            f"Trayectorias simuladas · {self._nombre_objetivo} · "
            f"{self.n_simulaciones:,} simulaciones, {self.horizonte} sesiones",
            loc="left", color=COLORES["texto"], fontsize=12)
        eje.legend(loc="upper left", frameon=False, fontsize=9,
                   labelcolor=COLORES["texto_secundario"])
        return figura

    def _dibujar_distribucion(self, figura: Figure) -> Figure:
        """
        Dibuja el histograma del valor final, separando los escenarios con pérdida y con
        ganancia, con el valor inicial, la media, la mediana y los umbrales del VaR al 95 % y
        al 99 %.
        :param figura: Figura vacía en la que dibujar.
        :return: La figura dibujada.
        """
        eje = figura.subplots()
        self._preparar_eje(eje)
        finales = self.valores_finales
        media = float(finales.mean())
        mediana = float(finales.median())
        # Valor final por debajo del cual queda el 5 % / 1 % de los escenarios
        umbral_var_95 = self.valor_inicial * (1 - self.var(0.95))
        umbral_var_99 = self.valor_inicial * (1 - self.var(0.99))
        # 50 intervalos con el valor inicial como borde, para que ninguna barra mezcle
        # escenarios con pérdida y con ganancia
        ancho = (finales.max() - finales.min()) / 50 or 1.0
        desde = np.floor((finales.min() - self.valor_inicial) / ancho)
        hasta = np.ceil((finales.max() - self.valor_inicial) / ancho)
        intervalos = self.valor_inicial + ancho * np.arange(desde, hasta + 1)
        eje.hist(finales[finales < self.valor_inicial], bins=intervalos,
                 color=COLORES["perdida"], edgecolor=COLORES["superficie"], linewidth=0.6,
                 label="Pérdida")
        eje.hist(finales[finales >= self.valor_inicial], bins=intervalos,
                 color=COLORES["ganancia"], edgecolor=COLORES["superficie"], linewidth=0.6,
                 label="Ganancia")
        referencias = (
            (self.valor_inicial, COLORES["texto_secundario"], "-", "Valor inicial"),
            (media, COLORES["media"], "--", "Media"),
            (mediana, COLORES["mediana"], "-", "Mediana"),
            (umbral_var_95, COLORES["var_95"], "-", "VaR 95 %"),
            (umbral_var_99, COLORES["var_99"], "-", "VaR 99 %"),
        )
        for valor, color, estilo, nombre in referencias:
            eje.axvline(valor, color=color, linestyle=estilo, linewidth=GROSOR_REFERENCIAS,
                        label=f"{nombre} {valor:,.2f}")
        eje.set_xlabel(f"{self._etiqueta_valor} al final del horizonte",
                       color=COLORES["texto_secundario"])
        eje.set_ylabel("Nº de simulaciones", color=COLORES["texto_secundario"])
        eje.set_title(
            f"Distribución del valor final · {self._nombre_objetivo} · "
            f"{self.horizonte} sesiones", loc="left", color=COLORES["texto"], fontsize=12)
        # Leyenda y estadísticos a la derecha, sobre la cola de la distribución, para no tapar
        # las líneas de los valores de referencia
        eje.legend(loc="upper right", frameon=False, fontsize=9,
                   labelcolor=COLORES["texto_secundario"])
        eje.text(
            0.98, 0.50,
            f"Prob. de pérdida: {(finales < self.valor_inicial).mean():.1%}\n"
            f"VaR 95 %: {self.var(0.95):.1%}   CVaR 95 %: {self.cvar(0.95):.1%}\n"
            f"VaR 99 %: {self.var(0.99):.1%}   CVaR 99 %: {self.cvar(0.99):.1%}\n"
            f"Rent. media: {self.rentabilidades_finales.mean():.1%}",
            transform=eje.transAxes, ha="right", va="top", fontsize=9,
            color=COLORES["texto_secundario"], linespacing=1.5,
        )
        return figura

    def guardar_graficos(self, n_trayectorias: int = 50,
                         carpeta: str | Path = CARPETA_GRAFICOS) -> list[Path]:
        """
        Borra los gráficos (PNG) de la simulación anterior y guarda los de esta:
        `trayectorias.png` y `distribucion.png`. Se llama automáticamente al crear el objeto.
        :param n_trayectorias: Número de trayectorias individuales a dibujar de fondo.
        :param carpeta: Carpeta de destino. Por defecto, `models/graficos/`.
        :return: Las rutas de los ficheros guardados.
        """
        carpeta = Path(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        for anterior in carpeta.glob("*.png"):
            anterior.unlink()
        # Figuras fuera de pyplot: se guardan sin abrirse ni mostrarse en un notebook
        figuras = {
            "trayectorias.png": self._dibujar_trayectorias(Figure(figsize=(11, 6)),
                                                           n_trayectorias),
            "distribucion.png": self._dibujar_distribucion(Figure(figsize=(10, 5.5))),
        }
        rutas = []
        for nombre, figura in figuras.items():
            ruta = carpeta / nombre
            figura.savefig(ruta, dpi=150, bbox_inches="tight", facecolor=COLORES["superficie"])
            rutas.append(ruta)
        return rutas

    def graficar(self, n_trayectorias: int = 50) -> tuple[Figure, Figure]:
        """
        Muestra por pantalla el resultado de la simulación en dos gráficos separados: las
        trayectorias (con bandas de percentiles y mediana) y la distribución del valor final.
        :param n_trayectorias: Número de trayectorias individuales a dibujar de fondo.
        :return: Las dos figuras de matplotlib (trayectorias, distribución).
        """
        trayectorias = self._dibujar_trayectorias(
            plt.figure(figsize=(11, 6), facecolor=COLORES["superficie"]), n_trayectorias)
        distribucion = self._dibujar_distribucion(
            plt.figure(figsize=(10, 5.5), facecolor=COLORES["superficie"]))
        plt.show()
        return trayectorias, distribucion

    def __repr__(self) -> str:
        objetivo = "FinancialSeries" if self.pesos is None else "Portfolio"
        return (f"MonteCarlo<{objetivo}, {self.n_simulaciones} simulaciones, "
                f"{self.horizonte} sesiones>")
