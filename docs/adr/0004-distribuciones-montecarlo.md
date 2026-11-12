# ADR 0004 — Distribuciones de los choques en Monte Carlo

- **Estado:** aceptado
- **Ámbito:** `simulation/montecarlo.py`, `analytics/distribuciones.py`

## Contexto

`MonteCarlo` simulaba los rendimientos diarios con una distribución normal. Los rendimientos
reales tienen **colas gruesas**: las caídas fuertes son bastante más frecuentes de lo que predice
una normal. Con una normal, el VaR y el CVaR, que miden justamente las pérdidas extremas, se
quedan cortos.

## Decisión

`MonteCarlo` admite tres distribuciones con el parámetro `distribucion`, y `"normal"` sigue siendo
la de por defecto:

| Distribución | Cómo se generan los choques diarios |
| --- | --- |
| `"normal"` | Normales correlacionadas con la descomposición de Cholesky (el modelo de siempre) |
| `"t"` | **t de Student multivariante**: los choques normales correlacionados se dividen por un mismo factor χ² por día, y se escalan para que la volatilidad siga siendo la supuesta |
| `"bootstrap"` | **Bootstrap histórico**: días reales del pasado elegidos al azar (todos los activos del mismo día, para conservar sus correlaciones), estandarizados y reescalados a la volatilidad supuesta |

Los grados de libertad de la t se estiman, si no se indican, a partir de la curtosis histórica por
el método de los momentos (ν = 6 / curtosis + 4). Así no hace falta `scipy`.

## Justificación

- **Las tres opciones mantienen los supuestos del usuario.** La rentabilidad y la volatilidad
  anuales se respetan con cualquier distribución; solo cambia la forma de las colas. Así se pueden
  comparar sin mezclar efectos.
- **La t y el bootstrap se complementan.** La t es un modelo paramétrico con un único parámetro
  interpretable (ν); el bootstrap no supone ninguna distribución, pero solo puede repetir días que
  ya han pasado.
- **La normal sigue siendo la de por defecto** y genera exactamente los mismos números aleatorios
  que antes, así que los resultados anteriores no cambian.
- `MonteCarlo.comparar_distribuciones()` y la sección de Monte Carlo de `report()` muestran el VaR y
  el CVaR de las tres a la vez, que es la forma de ver el riesgo de modelo.

## Consecuencias

- Las diferencias son grandes a horizontes cortos y en los percentiles extremos, y se reducen a
  horizontes largos: la suma de muchos días se parece cada vez más a una normal (teorema central
  del límite).
- Los choques siguen siendo independientes entre días: ninguna de las tres reproduce que la
  volatilidad se agrupe en el tiempo (rachas de días agitados). Para eso haría falta un modelo de
  volatilidad cambiante, como GARCH.
