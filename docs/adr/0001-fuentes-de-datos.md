# ADR 0001 — Fuentes de datos y su estandarización

- **Estado:** aceptado
- **Ámbito:** `providers/providers.py`, `config.py`

## Contexto

El enunciado (apartado 4.2) pide descargar precios de acciones e índices, añadir al menos un tipo
de dato adicional y garantizar que, con independencia de la API utilizada, el programa devuelva
objetos idénticos y compatibles entre sí. Cada API tiene su propio formato, sus límites de uso y,
en algunos casos, necesita una clave personal.

## Decisión

Se usan cuatro fuentes, cada una detrás de un proveedor que hereda de la clase abstracta
`Provider` y cuyo `download()` devuelve siempre una lista de series del paquete:

| Proveedor | Fuente | Datos | Clave | Devuelve |
| --- | --- | --- | --- | --- |
| `YahooFinanceProvider` | Yahoo Finance (`yfinance`) | Acciones, índices y ETF | No | `FinancialSeries` |
| `PolygonProvider` | Polygon / Massive (`massive`) | Acciones ordinarias | `POLYGON_API_KEY` | `FinancialSeries` |
| `AlphaVantageProvider` | Alpha Vantage (REST con `requests`) | Oro, plata y petróleo Brent | `ALPHAVANTAGE_API_KEY` | `FinancialSeries` |
| `MacroProvider` | FRED / ALFRED (`fredapi`) | Series macroeconómicas (tipos, IPC, PIB…) | `FRED_API_KEY` | `MacroSeries` |

**Yahoo Finance es la fuente principal** porque no necesita clave: el proyecto funciona nada más
clonarlo (apartado 4.1), y la demo y los ejemplos se basan en ella. Las demás fuentes son
complementarias y solo se usan si hay clave en el `.env`.

Todas las fuentes se **estandarizan de la misma forma** antes de salir del proveedor:

- Precios de cierre **ajustados** (`auto_adjust=True` en Yahoo, `adjusted=True` en Polygon).
- Índice de fechas **sin zona horaria ni hora**, para poder alinear activos de mercados distintos.
- Limpieza con `limpiar_serie()` y validación estricta al crear la serie
  (ver [ADR 0002](0002-validacion-de-inputs.md)).
- Metadatos comunes: tipo de activo (`TipoActivo`: acción, índice, ETF o materia prima),
  moneda, bolsa, proveedor y nombre. La cartera usa el tipo para rechazar los índices,
  que no se pueden comprar: en su lugar se usa un ETF que los replique.

Un test (`test_todas_las_fuentes_de_precios_devuelven_el_mismo_tipo_de_objeto`) comprueba este
contrato con respuestas simuladas de las tres fuentes de precios.

## Limitaciones conocidas

| Fuente | Limitación | Cómo se gestiona |
| --- | --- | --- |
| Yahoo Finance | API no oficial: puede cambiar o limitar el acceso sin aviso | La demo pasa a datos sintéticos si la descarga falla |
| Polygon | El plan gratuito solo cubre **2 años** y permite **5 llamadas por minuto** | Las fechas anteriores se recortan con un aviso, y hay una pausa de 12 s entre llamadas (`pausa`) |
| Alpha Vantage | Solo materias primas, y el plan gratuito limita las peticiones | Pausa entre descargas y `ProviderError` con el mensaje de la API cuando la rechaza |
| FRED | Necesita clave; las series se revisan con el tiempo | La opción `vintage` (ALFRED) descarga los datos tal y como se publicaron |

## Consecuencias

- Añadir una fuente nueva es crear una subclase de `Provider`. Los modelos, la cartera, la
  simulación y los informes no cambian, porque solo trabajan con `FinancialSeries`.
- Las claves se leen del `.env`, que no se sube al repositorio. `.env.example` sirve de plantilla.
- Los tests no usan red ni claves: sustituyen cada API por respuestas simuladas.
