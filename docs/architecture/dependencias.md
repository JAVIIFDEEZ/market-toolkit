# Dependencias entre módulos

Cada flecha `A → B` significa «A importa B». Las líneas discontinuas son dependencias de la base
común (`config` y `exceptions`), que cualquier módulo puede usar.

## Estado actual

![Dependencias actuales entre módulos](diagramas/dependencias_actual.svg)

Código fuente: [`diagramas/dependencias_actual.mmd`](diagramas/dependencias_actual.mmd)

La regla principal se cumple: **`models` nunca importa `providers`**, así que los modelos no saben
de dónde vienen los datos. Las flechas en rojo son los acoplamientos que quedan por resolver:

| Acoplamiento | Por qué conviene quitarlo |
| --- | --- |
| `models/portfolio` ↔ `simulation/montecarlo` (y `informe` → `montecarlo`) | Los módulos se importan entre sí, ahora además entre dos paquetes distintos. Funciona porque se importan como módulo y no por nombre, pero cualquier cambio en el orden de los imports puede romperlo y hace difícil probarlos por separado. `informe` solo importa `montecarlo` para reutilizar sus colores y el estilo de los ejes |
| `cleaning` → `yfinance` | El preprocesado descarga tipos de cambio de Yahoo para pasar la cartera a USD. Crear una `Portfolio` con activos que no estén en USD llama a internet aunque los precios vengan de otra fuente |

## Arquitectura objetivo

Cómo quedaría el paquete al rellenar los módulos que hoy están vacíos (`extractor.py`,
`analytics/` y `reporting/`). En naranja, lo pendiente. `MonteCarlo` ya está en `simulation/`.

![Arquitectura objetivo](diagramas/dependencias_objetivo.svg)

Código fuente: [`diagramas/dependencias_objetivo.mmd`](diagramas/dependencias_objetivo.mmd)

- `Portfolio` solo **orquesta**: delega los cálculos en `analytics`, la simulación en `simulation`
  y los informes en `reporting`.
- `analytics` son funciones puras sobre pandas: no dependen de ningún otro módulo del paquete,
  así que se pueden probar con datos sintéticos y reutilizar en cualquier sitio.
- Los tipos de cambio pasan a ser un proveedor más, y el preprocesado solo limpia y alinea.
