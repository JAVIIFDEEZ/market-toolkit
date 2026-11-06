import warnings
from collections.abc import Sequence
from typing import Literal

import pandas as pd

from market_toolkit.models import FinancialSeries
from market_toolkit.preprocessing import juntar_series


class Portfolio:
    """
    Clase que modela una cartera de inversión.
    """
    activos: pd.DataFrame
    pesos: pd.DataFrame
    info: pd.DataFrame
    metadatos: dict

    def __init__(self, activos: Sequence[FinancialSeries], pesos: pd.DataFrame, *,
                 alineacion_temporal: Literal["relleno", "eliminacion"] | None = None):
        """
        Inicializa un objeto de Portfolio.
        :param activos: Lista con las series temporales que forman la cartera.
        :param pesos: DataFrame con los pesos de cada uno de los activos de la cartera.
            Debe tener un índice temporal y cada fila se corresponde con los pesos del día
            correspondiente. Si el índice no es diario, cada fila indica los pesos en la ventana
            temporal que empieza en esa fecha y termina en la fecha de la próxima fila.
        :param alineacion_temporal: Establece cómo tratar los valores nulos causados por la
            alineación temporal de los activos. `None` si no se desea hacer nada, `"relleno"` para
            reemplazarlos por los valores anteriores y `"eliminacion"` para eliminar esas fechas del
            dataframe.
        """
        # Juntar activos
        self.activos = juntar_series(activos, alineacion_temporal=alineacion_temporal)
        # Juntar la informacion
        self.info = pd.DataFrame(
            [activo.resumen() for activo in activos]
        ).set_index("activo").T
        self.info.columns.name = None
        self.info.index.name = "Información"
        # Validar pesos
        if len(pesos.columns) != len(activos):
            raise ValueError("La cantidad de pesos debe coincidir con en número de activos.")
        pesos = pesos.dropna()  # Nos quedamos SOLO cuando todos los pesos son validos.
        if pesos.empty:
            raise ValueError("No se han proporcionado pesos válidos.")
        # Pesos de los activos
        self.pesos = pesos.asfreq("D").ffill()
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
        # Metadatos de los activos
        self.metadatos = {activo.activo: activo.metadatos for activo in activos}