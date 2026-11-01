# ADR 0002 — Validación estricta de los inputs de los modelos

- **Estado:** aceptado
- **Ámbito:** `models/series.py`, `preprocessing/validation.py`

## Contexto

Los modelos (`FinancialSeries`, `MacroSeries` y, más adelante, `Portfolio`) son la base de todos
los cálculos del paquete: estadísticos, métricas de riesgo, Monte Carlo y reportes. Las fuentes
de datos (Yahoo Finance, Alpha Vantage, FRED…) devuelven formatos distintos y con defectos
habituales: fechas duplicadas o desordenadas, huecos por festivos, valores nulos, precios a cero
o negativos e históricos muy cortos.

Había dos alternativas:

1. **Inputs abiertos:** aceptar cualquier objeto con una serie temporal (un `DataFrame`, un
   `dict`, una lista de tuplas…) y que cada método se adapte y limpie lo que reciba.
2. **Inputs restringidos:** aceptar solo un `pd.Series` con `DatetimeIndex` que cumpla unas
   condiciones mínimas, y rechazar el resto con una excepción propia.

## Decisión

Se restringen los inputs a series validadas (opción 2):

- `FinancialSeries` y `MacroSeries` reciben un `pd.Series` y lo validan en `__post_init__`
  mediante las funciones de `preprocessing/validation.py`.
- Una serie de precios debe tener un `DatetimeIndex` ordenado y sin duplicados, valores
  numéricos sin NaN ni infinitos, precios estrictamente positivos y al menos
  `MIN_OBSERVACIONES` datos.
- Si no se cumple, se lanza `DataValidationError` o, si faltan observaciones,
  `InsufficientDataError` (subclase de la anterior).
- La validación **no corrige** nada. La limpieza (`limpiar_datos`) es responsabilidad previa de
  los proveedores, que son los que conocen el formato de cada fuente.

## Justificación

- **Garantías para todo el análisis.** Si existe un objeto `FinancialSeries`, sus datos son
  válidos. Los módulos de análisis, simulación y reporte no tienen que repetir comprobaciones
  ni defenderse de casos raros.
- **Estadísticos fiables desde la creación.** Los estadísticos se calculan automáticamente al
  instanciar la serie. Con un precio a cero los rendimientos serían infinitos; con NaN o fechas
  desordenadas, la media y la volatilidad serían incorrectas sin dar ningún error.
- **Errores pronto y claros.** Un dato erróneo se detecta en el punto de entrada, con un mensaje
  que dice qué falla, en lugar de propagarse y aparecer como un resultado absurdo en el report.
- **Desacoplamiento entre ingesta y análisis.** Los modelos no saben de dónde vienen los datos.
  Cada proveedor transforma su formato al estándar (`pd.Series` limpio) y el resto del paquete
  solo trabaja con ese estándar. Añadir una fuente nueva no obliga a tocar los modelos.
- **Responsabilidad única.** Limpiar (decidir cómo rellenar huecos o qué fechas eliminar) es una
  decisión que depende de la fuente y del uso; validar es una comprobación objetiva. Mezclar
  ambas en la dataclass ocultaría decisiones que el usuario debe conocer.

## Consecuencias

- Quien construya una serie a mano debe limpiarla antes (por ejemplo, con `limpiar_datos`) o
  recibirá una excepción.
- Una serie con menos de `MIN_OBSERVACIONES` datos no puede crearse, aunque sea correcta. Es
  intencionado: con tan pocos datos los estadísticos anualizados no son representativos.
- `MacroSeries` usa una validación más flexible: admite valores negativos o cero (los tipos de
  interés pueden serlo) y menos observaciones, porque muchas series macroeconómicas son
  mensuales o anuales.
