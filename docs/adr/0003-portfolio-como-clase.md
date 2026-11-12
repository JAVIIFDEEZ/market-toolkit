# ADR 0003 — `Portfolio` como clase normal y no como dataclass

- **Estado:** aceptado
- **Ámbito:** `models/portfolio.py`

## Contexto

Las series de datos del paquete son dataclasses inmutables: `FinancialSeries`, `MacroSeries` y
`Fundamentales`. El enunciado habla también de "la DataClass de la cartera" (apartado 4.4), así
que había que decidir si `Portfolio` debía serlo.

Una dataclass encaja cuando el objeto es, sobre todo, la suma de los datos que recibe: sus campos
son los argumentos del constructor y Python genera `__init__`, `__repr__` y `__eq__` a partir de
ellos. Es el caso de las series: reciben una `pd.Series` y unos metadatos, y lo demás se deriva.

## Decisión

`Portfolio` es una **clase normal** con un constructor explícito.

## Justificación

- **Lo que recibe no es lo que guarda.** El constructor recibe `activos` (una lista de series),
  `pesos` y `alineacion_temporal`, pero guarda otra cosa: `precio_activos` (los precios alineados
  y en USD), `pesos` (ya ajustados a las fechas y con su deriva entre rebalanceos),
  `metadatos_activos`, `rendimiento` y los estadísticos de la cartera. En una dataclass casi todos
  serían campos `field(init=False)` y los argumentos reales no serían campos.
- **El constructor hace un proceso en varios pasos.** Alinea los calendarios, convierte monedas,
  valida los pesos, recorta las fechas de pesos y precios con avisos y calcula la deriva de los
  pesos. Algunos atributos se reasignan durante el proceso, por ejemplo `precio_activos` al
  recortarse. Un constructor explícito, comentado paso a paso, lo hace más legible que meterlo
  todo en `__post_init__`.
- **Lo que genera una dataclass no aporta aquí.** El `__eq__` automático compararía `DataFrame`
  con `==`, que no devuelve `True` o `False` sino otra tabla, y fallaría. Por eso las series
  usan `eq=False`. El `__repr__` automático imprimiría tablas enteras.
- **La cartera guarda estado interno.** Atributos como `_series`, `_sesiones_cambio`,
  `_ultimo_rebalanceo` o `_firma` no forman parte de su definición; los usan `report()`,
  `plots_report()` y `correlacion()`.

## Consecuencias

- `Portfolio` mantiene el papel que pide el enunciado: agrega varios activos con sus
  ponderaciones (4.3) e integra Monte Carlo como método directo, `simulacion_monte_carlo()` (4.4).
- Los datos que entran en la cartera sí son dataclasses validadas (`FinancialSeries` y `MacroSeries`), así que la
  cartera trabaja siempre sobre datos estandarizados.
- Si en el futuro la cartera solo guardara datos y delegara los cálculos en otros módulos
  (`analytics/`, `reporting/`), convertirla en dataclass sería sencillo y habría que revisar esta
  decisión.
