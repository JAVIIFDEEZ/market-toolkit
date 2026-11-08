# Flujo de datos

Recorrido de los datos desde que se piden a una API hasta los resultados.

```mermaid
flowchart LR
    usuario(["Usuario:<br/>tickers + fechas"])

    subgraph fuentes["Fuentes externas"]
        yahoo[("Yahoo Finance")]
        polygon[("Polygon / Massive")]
        av[("Alpha Vantage")]
        fred[("FRED / ALFRED")]
    end

    subgraph ingesta["1 · Ingesta (providers)"]
        validar_tk["_validar_input()<br/>¿existe el ticker?"]
        download["download()<br/>cierres ajustados<br/>índice sin zona horaria"]
        limpiar["limpiar_serie()<br/>orden · duplicados · inf<br/>negativos · NaN"]
    end

    subgraph modelos["2 · Modelos"]
        validacion{"validation<br/>¿serie válida?"}
        fs["FinancialSeries<br/>estadísticos automáticos"]
        ms["MacroSeries<br/>nivel: media y desviación"]
        error["DataValidationError /<br/>InsufficientDataError"]
    end

    pesos(["Usuario:<br/>DataFrame de pesos"])

    subgraph cartera["3 · Cartera (Portfolio)"]
        juntar["juntar_series()<br/>alineación temporal<br/>+ conversión a USD"]
        validar_p["validar pesos<br/>suman 1 · uno por activo"]
        deriva["_calcular_pesos_activos()<br/>deriva entre rebalanceos"]
        stats["_rendimientos_cartera()<br/>rentabilidad y volatilidad"]
    end

    subgraph simulacion["4 · Simulación"]
        mc["MonteCarlo<br/>GBM + Cholesky"]
        res["percentiles · VaR · CVaR<br/>probabilidad de pérdida"]
    end

    subgraph salida["5 · Resultados"]
        resumen["resumen()"]
        md["report()<br/>Markdown con métricas<br/>y advertencias"]
        plots["plots_report()<br/>6 gráficos"]
        graficos["graficar() /<br/>guardar_graficos()"]
    end

    usuario --> validar_tk
    yahoo --> download
    polygon --> download
    av --> download
    fred --> download
    validar_tk --> download --> limpiar --> validacion
    validacion -- "sí, precios" --> fs
    validacion -- "sí, macro" --> ms
    validacion -- "no" --> error
    fs --> juntar
    pesos --> validar_p
    juntar --> validar_p --> deriva --> stats
    stats --> resumen
    stats --> md
    stats --> plots
    ms -. "tipo libre de riesgo" .-> md
    stats --> mc
    fs -- "un activo" --> mc
    mc --> res --> graficos
```

1. **Ingesta.** Cada proveedor comprueba los tickers, descarga los precios de cierre ajustados,
   quita la zona horaria del índice y los limpia con `limpiar_serie()`.
2. **Modelos.** La validación es estricta (ver
   [ADR 0002](../adr/0002-validacion-de-inputs.md)): si la serie no es válida se lanza una
   excepción; si lo es, la serie calcula sus estadísticos al crearse.
3. **Cartera.** `Portfolio` junta las series, alinea los calendarios, pasa los precios a USD,
   valida los pesos y calcula cómo derivan entre rebalanceos.
4. **Simulación.** `MonteCarlo` simula un activo o la cartera con un movimiento browniano
   geométrico, con las correlaciones históricas entre activos (descomposición de Cholesky).
5. **Resultados.** Resumen, informe en Markdown con advertencias de riesgo y gráficos.
