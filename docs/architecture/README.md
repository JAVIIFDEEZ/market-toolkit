# Arquitectura

Diagramas de la arquitectura de `market-toolkit` (apartado 4.6 del enunciado). Están escritos en
[Mermaid](https://mermaid.js.org/), así que GitHub los dibuja directamente y se versionan como el
resto del código: cuando cambia la arquitectura, se edita el texto y el cambio queda en el
historial.

| Diagrama | Qué muestra |
| --- | --- |
| [Clases](clases.md) | Jerarquía de clases: proveedores, series, cartera, simulación y excepciones |
| [Dependencias](dependencias.md) | Qué módulo importa a cuál, hoy y en la arquitectura objetivo |
| [Flujo](flujo.md) | El recorrido de los datos: ingesta → modelos → cartera → simulación → resultados |

Las decisiones de diseño se justifican en los [ADR](../adr/) (*Architecture Decision Records*).

## Editar o exportar los diagramas

- **En VS Code:** con la extensión *Markdown Preview Mermaid Support* se ven en la vista previa
  del Markdown (`Ctrl+Shift+V`).
- **En el navegador:** pegando el bloque `mermaid` en [mermaid.live](https://mermaid.live), que
  además permite exportarlo a SVG o PNG (por ejemplo, para la presentación).
