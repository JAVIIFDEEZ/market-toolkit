# Dependencias entre módulos

Cada flecha `A → B` significa «A importa B». Las líneas discontinuas indican que una capa usa la
base común (`config` y `exceptions`), que pueden usar todas.

## Estado actual

![Dependencias actuales entre módulos](diagramas/dependencias_actual.svg)

Código fuente: [`diagramas/dependencias_actual.mmd`](diagramas/dependencias_actual.mmd)

La regla principal se cumple: **ningún módulo de `models`, `simulation` ni `preprocessing`
importa `providers`**, así que los modelos no saben de dónde vienen los datos. La demo y el
cuaderno de la presentación usan el paquete igual que lo haría cualquier usuario.

Las flechas en rojo son los acoplamientos que quedan por resolver:

| Acoplamiento | Por qué conviene quitarlo |
| --- | --- |
| Ciclo `portfolio` → `informe` → `montecarlo` → `portfolio` | Los tres módulos se importan entre sí, y además entre dos paquetes (`models` y `simulation`). Funciona porque se importan como módulo y no por nombre, pero cualquier cambio en el orden de los imports puede romperlo y hace difícil probarlos por separado. `montecarlo` solo importa `portfolio` para comprobar el tipo del objeto que simula, e `informe` solo importa `montecarlo` para reutilizar sus colores y el estilo de los ejes |
| `cleaning` → `yfinance` | El preprocesado descarga tipos de cambio de Yahoo para pasar la cartera a USD. Crear una `Portfolio` con activos que no estén en USD llama a internet aunque los precios vengan de otra fuente |

## Arquitectura objetivo

Cómo quedaría el paquete al completar los módulos pendientes. En naranja, lo que falta.
`MonteCarlo` ya está en `simulation/`; `analytics/` ya tiene las métricas frente al índice de
referencia y la estimación de colas de la t de Student, y `reporting/` ya genera el
informe en HTML. Faltan `extractor.py`, el registro de proveedores y llevar a `analytics/` y
`reporting/` los cálculos y gráficos que aún están en `Portfolio`.

![Arquitectura objetivo](diagramas/dependencias_objetivo.svg)

Código fuente: [`diagramas/dependencias_objetivo.mmd`](diagramas/dependencias_objetivo.mmd)

- `Portfolio` solo **orquesta**: delega los cálculos en `analytics`, la simulación en `simulation`
  y los informes en `reporting`.
- `analytics` son funciones puras sobre pandas: no dependen de ningún otro módulo del paquete,
  así que se pueden probar con datos sintéticos y reutilizar en cualquier sitio.
- Los tipos de cambio pasan a ser un proveedor más, y el preprocesado solo limpia y alinea.
