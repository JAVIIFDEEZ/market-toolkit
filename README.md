# market-toolkit
El proyecto consistes en la implementación de una toolkit para la extracción, análisis bursátil y gestión de  carteras

<details>
<summary><h2>Descarga de Datos</h2></summary>

Todos los proveedores siguen la misma estructura: se crean con una lista de tickers (o series),
validan que existen y `download()` devuelve una **lista de series** ya limpias y validadas.

Las API keys se leen del fichero `.env` (si no están, se piden por pantalla):

```
POLYGON_API_KEY=tu_clave
FRED_API_KEY=tu_clave
```

<details>
<summary><h3>Acciones / Stocks</h3></summary>

Se descargan con `PolygonProvider` (Polygon.io, ahora Massive). El plan gratuito tiene dos
limitaciones que el proveedor gestiona solo:

- Solo cubre los **últimos 2 años**: si se pide una fecha anterior, se recorta y se avisa.
- Solo permite **5 llamadas por minuto**: espera `pausa` segundos (12 por defecto) entre
  llamadas, así que cada ticker tarda unos 12 s.

Solo admite acciones ordinarias (`CS`). ETFs, índices o tickers inexistentes se descartan con
un aviso.

#### Crear el proveedor

```python
from market_toolkit.providers.providers import PolygonProvider

polygon = PolygonProvider(["aapl", "MSFT", "SPY", "NOEXISTE"])
print(polygon)
```

```
UserWarning: Los tickers NOEXISTE, SPY no son equities o no existen en Polygon. Se eliminan de los datos de busqueda.
Polygon object tickers<AAPL, MSFT>
```

La API key también se puede pasar como argumento: `PolygonProvider(["AAPL"], api_key="...")`.

#### Descargar

`download()` devuelve una lista de `FinancialSeries` con los cierres ajustados de cada ticker.

```python
series = polygon.download()                                   # Últimos 2 años (por defecto)
series = polygon.download(periodo="6mo")                      # "3mo", "6mo", "1y" o "2y"
series = polygon.download(inicio="2025-01-01", fin="2025-06-30")

for s in polygon.download():
    print(s.activo, s.tipo, s.proveedor, s.inicio, s.fin, s.observaciones)
```

```
AAPL acción Polygon 2024-11-04 2026-11-02 500
MSFT acción Polygon 2024-11-04 2026-11-02 500
```

| Llamada | Resultado |
|---|---|
| `download()` | 2024-11-04 → 2026-11-02, 500 sesiones |
| `download(periodo="6mo")` | 2026-05-06 → 2026-11-02, 125 sesiones |
| `download(inicio="2025-01-01", fin="2025-06-30")` | 2025-01-02 → 2025-06-30, 122 sesiones |
| `download(inicio="2015-01-01")` | Se recorta a 2024-11-04 y avisa: `UserWarning: El plan de Polygon solo cubre desde 2024-11-04. Se recorta la fecha de inicio 2015-01-01.` |

#### Trabajar con una serie

Cada `FinancialSeries` calcula sus estadísticos al crearse. La moneda y la bolsa salen de los
detalles del ticker en Polygon: la bolsa es la principal de cotización (`NASDAQ`, `NYSE`...) y,
si Polygon no la indica, `Desconocido`. El precio es el consolidado de todos los mercados de
EE.UU.

```python
aapl = series[0]
aapl.resumen()
```

```
nombre                     Apple Inc.
activo                     AAPL
tipo                       acción
moneda                     USD
bolsa                      NASDAQ
proveedor                  Polygon
inicio                     2024-11-04
fin                        2026-11-02
observaciones              500
media_diaria               0.0010069361415077649
desviacion_tipica_diaria   0.018092462152309082
rentabilidad_anualizada    0.2886823205407585
volatilidad_anualizada     0.28720893275914944
```

```python
aapl.serie_temporal.tail(3)        # pd.Series con los precios
aapl.rendimientos().tail(3)        # Rendimientos simples
aapl.rendimientos("log").tail(3)   # Rendimientos logarítmicos
```

```
2026-10-30    344.63
2026-11-02    338.32
Name: AAPL, dtype: float64

2026-10-29    0.014775
2026-10-30   -0.012267
2026-11-02   -0.018309
Name: AAPL, dtype: float64

2026-10-29    0.014667
2026-10-30   -0.012343
2026-11-02   -0.018479
Name: AAPL, dtype: float64
```

Para tener todos los tickers en un `DataFrame`:

```python
import pandas as pd

df = pd.concat([s.serie_temporal for s in series], axis=1)
df.tail(3)
```

```
              AAPL    MSFT
2026-10-30  344.63  521.91
2026-11-02  338.32  507.12
```

</details>

<details>
<summary><h3>Índices / Market Index</h3></summary>

Pendiente de documentar. El plan gratuito de Polygon no incluye índices; se pueden descargar
con `YahooFinanceProvider`, que admite acciones e índices (por ejemplo `^GSPC` o `^IBEX`).

</details>

<details>
<summary><h3>Macro</h3></summary>

Se descargan con `MacroProvider`, que usa la API de FRED y, para datos históricos tal y como se
publicaron (sin revisiones posteriores), ALFRED.

Las series se indican con su ID de FRED (por ejemplo `DGS10`) o con un alias de
`MacroProvider.SERIES`:

| Alias | ID de FRED | Serie |
|---|---|---|
| `us10y` / `us2y` | `DGS10` / `DGS2` | Bono EE.UU. 10 / 2 años (%) |
| `us10y_2y` | `T10Y2Y` | Spread 10Y-2Y EE.UU. |
| `ipc_eurozona` | `CP0000EZ19M086NEST` | IPC armonizado de la Eurozona |
| `pib_espana` | `CLVMNACSCAB1GQES` | PIB real de España (trimestral) |
| `pib_eeuu` | `GDPC1` | PIB real de EE.UU. (trimestral) |
| `es10y` / `de10y` | `IRLTLT01ESM156N` / `IRLTLT01DEM156N` | Bono España / Alemania 10 años |
| `bce_depo` / `fed_funds` | `ECBDFR` / `DFF` | Tipo de depósito del BCE / Fed Funds |
| `cpi_eeuu` / `paro_eeuu` | `CPIAUCSL` / `UNRATE` | IPC / paro de EE.UU. |
| `eurusd`, `vix`, `wti`, `hy_spread`, `breakeven10y` | ... | Ver `MacroProvider.SERIES` |

#### Crear el proveedor

```python
from market_toolkit.providers.providers import MacroProvider

macro = MacroProvider(["us10y", "us10y_2y", "pib_espana", "ipc_eurozona", "NOEXISTE"])
print(macro)
```

```
UserWarning: Las series NOEXISTE no existen en FRED. Se eliminan de los datos de busqueda.
MacroProvider object series<CLVMNACSCAB1GQES, T10Y2Y, CP0000EZ19M086NEST, DGS10>
```

#### Descargar

`download()` devuelve una lista de `MacroSeries`. Sin parámetros descarga todo el histórico.

```python
series = macro.download()                                     # Todo el histórico
series = macro.download(periodo="5y")                         # "max" o "<n>mo" / "<n>y"
series = macro.download(inicio="2024-01-01")

for s in macro.download(inicio="2024-01-01"):
    print(s.serie_temporal.name, s.nombre, s.unidad, s.observaciones)
```

```
CLVMNACSCAB1GQES   Real Gross Domestic Product for Spain                   Mil. of Chn. 2010 Euros  10
T10Y2Y             10-Year Treasury Constant Maturity Minus 2-Year ...     %                        709
CP0000EZ19M086NEST Harmonized Index of Consumer Prices: Total for Euro...  Index 2025=100           33
DGS10              Market Yield on U.S. Treasury Securities at 10-Year...  %                        708
```

Los valores negativos se conservan (tipos de interés, spreads...), a diferencia de las series
de precios.

#### Trabajar con una serie

```python
dgs10 = next(s for s in series if s.serie_temporal.name == "DGS10")
dgs10.resumen()
```

```
nombre             Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis
unidad             %
proveedor          FRED
inicio             2024-01-02
fin                2026-10-30
observaciones      708
media              4.332951977401129
desviacion_tipica  0.287962972944004
ultimo_valor       4.94
```

```python
dgs10.metadatos
dgs10.serie_temporal.tail(3)
```

```
{'nombre': 'Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis',
 'frecuencia': 'Daily', 'ajuste_estacional': 'NSA', 'ultima_actualizacion': '2026-11-02 15:16:54-06', 'vintage': None}

2026-10-28    5.05
2026-10-29    4.98
2026-10-30    4.94
Name: DGS10, dtype: float64
```

#### Cambiar la frecuencia

FRED puede agregar la serie a una frecuencia menor con `frecuencia` (`"d"`, `"w"`, `"bw"`,
`"m"`, `"q"`, `"sa"`, `"a"`) y `agregacion` (`"avg"` media, `"sum"` suma o `"eop"` último dato
del periodo). Es útil para juntar series de distinta frecuencia en un `DataFrame`:

```python
import pandas as pd

mensual = MacroProvider(["us10y", "us2y"]).download(periodo="6mo", frecuencia="m", agregacion="eop")
pd.concat([s.serie_temporal for s in mensual], axis=1)
```

```
            DGS2  DGS10
2026-05-01  3.98   4.45
2026-06-01  4.14   4.44
2026-07-01  4.28   4.75
2026-08-01  4.34   4.75
2026-09-01  4.88   5.29
2026-10-01  4.56   4.94
```

FRED fecha cada mes en su día 1, aunque con `"eop"` el valor sea el del último día del mes.

#### Datos históricos sin revisiones (ALFRED)

Con la opción `vintage` se obtienen los datos tal y como se conocían en una fecha
(`vintage="2020-01-01"`) o su primera publicación (`vintage="first"`). Estas series tienen
`proveedor="ALFRED"`.

```python
pib = MacroProvider(["pib_eeuu"])
antes = pib.download(inicio="2019-01-01", fin="2019-12-31", vintage="2020-01-01")[0]
hoy = pib.download(inicio="2019-01-01", fin="2019-12-31")[0]

pd.concat([antes.serie_temporal.rename("vintage_2020"), hoy.serie_temporal.rename("actual")], axis=1)
```

```
            vintage_2020     actual
2019-01-01     18927.281  20431.641
2019-04-01     19021.860  20602.275
2019-07-01     19121.112  20843.322
2019-10-01           NaN  20985.448
```

El 1-1-2020 aún no se había publicado el PIB del 4T de 2019, y los valores actuales son
distintos por las revisiones y el cambio de año base.

</details>

</details>
