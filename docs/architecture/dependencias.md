# Dependencias entre módulos

Cada flecha `A → B` significa «A importa B». Las líneas discontinuas son dependencias de la base
común (`config` y `exceptions`), que cualquier módulo puede usar.

## Estado actual

```mermaid
flowchart TB
    subgraph externas["Librerías y APIs externas"]
        yf[("yfinance")]
        massive[("massive<br/>(Polygon)")]
        fredapi[("fredapi<br/>(FRED / ALFRED)")]
        req[("requests<br/>(Alpha Vantage)")]
        mpl[("matplotlib")]
    end

    subgraph ingesta["Ingesta"]
        providers["providers/providers.py<br/>Provider · Yahoo · Polygon<br/>AlphaVantage · Macro"]
    end

    subgraph modelos["Modelos"]
        series["models/series.py<br/>SerieTemporal · FinancialSeries<br/>MacroSeries · TipoActivo"]
        fundamentals["models/fundamentals.py<br/>Fundamentales"]
        portfolio["models/portfolio.py<br/>Portfolio"]
        montecarlo["models/montecarlo.py<br/>MonteCarlo"]
        informe["models/informe.py<br/>gráficos de plots_report()"]
    end

    subgraph prep["Preprocesado"]
        cleaning["preprocessing/cleaning.py<br/>limpiar_serie · limpiar_dataframe<br/>juntar_series"]
        validation["preprocessing/validation.py<br/>validar_serie_precios · validar_serie_macro"]
    end

    subgraph base["Base común"]
        config["config.py<br/>constantes y API keys (.env)"]
        exceptions["exceptions.py<br/>MarketToolkitError y derivadas"]
    end

    providers --> series
    providers --> cleaning
    providers --> yf
    providers --> massive
    providers --> fredapi
    providers --> req
    series --> validation
    portfolio --> cleaning
    portfolio --> informe
    portfolio --> montecarlo
    montecarlo --> portfolio
    informe --> montecarlo
    montecarlo --> series
    montecarlo --> mpl
    portfolio --> mpl
    informe --> mpl
    cleaning -- "tipos de cambio a USD" --> yf

    providers -.-> config
    providers -.-> exceptions
    series -.-> config
    portfolio -.-> config
    portfolio -.-> exceptions
    montecarlo -.-> config
    validation -.-> config
    validation -.-> exceptions

    series -. "nunca" .-x providers

    linkStyle 9,10,16 stroke:#d03b3b,stroke-width:2px
```

La regla principal se cumple: **`models` nunca importa `providers`**, así que los modelos no saben
de dónde vienen los datos. Las flechas en rojo son los acoplamientos que quedan por resolver:

| Acoplamiento | Por qué conviene quitarlo |
| --- | --- |
| `portfolio` ↔ `montecarlo` (y `informe` → `montecarlo`) | Los módulos se importan entre sí. Funciona porque se importan como módulo y no por nombre, pero cualquier cambio en el orden de los imports puede romperlo y hace difícil probarlos por separado |
| `cleaning` → `yfinance` | El preprocesado descarga tipos de cambio de Yahoo para pasar la cartera a USD. Crear una `Portfolio` con activos que no estén en USD llama a internet aunque los precios vengan de otra fuente |

## Arquitectura objetivo

Cómo quedaría el paquete al rellenar los módulos que hoy están vacíos (`extractor.py`,
`analytics/`, `simulation/` y `reporting/`). En naranja, lo pendiente.

```mermaid
flowchart TB
    subgraph ingesta["Ingesta"]
        extractor["extractor.py<br/>DataExtractor"]
        registry["providers/registry.py<br/>nombre → proveedor"]
        providers["providers/<br/>Yahoo · Polygon · AlphaVantage · Macro<br/>+ tipos de cambio"]
    end

    subgraph modelos["Modelos"]
        series["models/series.py<br/>FinancialSeries · MacroSeries"]
        fundamentals["models/fundamentals.py<br/>Fundamentales"]
        portfolio["models/portfolio.py<br/>Portfolio (solo orquesta)"]
    end

    subgraph prep["Preprocesado"]
        cleaning["preprocessing/cleaning.py<br/>limpieza y alineación"]
        validation["preprocessing/validation.py"]
    end

    subgraph analisis["Análisis"]
        returns["analytics/returns.py<br/>rendimientos"]
        risk["analytics/risk.py<br/>Sharpe · drawdown · VaR · beta"]
    end

    subgraph sim["Simulación"]
        montecarlo["simulation/monte_carlo.py<br/>MonteCarlo"]
    end

    subgraph salida["Reportes"]
        markdown["reporting/markdown.py<br/>report()"]
        plots["reporting/plots.py<br/>plots_report()"]
    end

    subgraph base["Base común"]
        config["config.py"]
        exceptions["exceptions.py"]
    end

    extractor --> registry --> providers
    providers --> series
    providers --> cleaning
    series --> validation
    portfolio --> series
    portfolio --> cleaning
    portfolio --> risk
    portfolio --> montecarlo
    portfolio --> markdown
    portfolio --> plots
    risk --> returns
    montecarlo --> risk
    markdown --> risk
    plots --> risk

    providers -.-> config
    providers -.-> exceptions
    validation -.-> exceptions
    risk -.-> config

    series -. "nunca" .-x providers
    analisis -. "nunca" .-x ingesta

    classDef pendiente fill:#fff4e5,stroke:#e8590c,stroke-width:2px,stroke-dasharray: 5 3
    class extractor,registry,returns,risk,montecarlo,markdown,plots pendiente
```

- `Portfolio` solo **orquesta**: delega los cálculos en `analytics`, la simulación en `simulation`
  y los informes en `reporting`.
- `analytics` son funciones puras sobre pandas: no dependen de ningún otro módulo del paquete,
  así que se pueden probar con datos sintéticos y reutilizar en cualquier sitio.
- Los tipos de cambio pasan a ser un proveedor más, y el preprocesado solo limpia y alinea.
