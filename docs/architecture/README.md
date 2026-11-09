# Arquitectura

Diagramas de la arquitectura de `market-toolkit` (apartado 4.6 del enunciado). Cada diagrama
está escrito en [Mermaid](https://mermaid.js.org/) y exportado a SVG:

- `diagramas/*.mmd`: el **código fuente** de cada diagrama. Es lo que se edita y se versiona.
- `diagramas/*.svg`: la **imagen** generada a partir de ese código. Es la que se muestra en la
  documentación, así que los diagramas se ven en GitHub, en VS Code y en cualquier visor de
  Markdown sin instalar nada.

| Diagrama | Qué muestra |
| --- | --- |
| [Clases](clases.md) | Jerarquía de clases: proveedores, series, cartera, simulación y excepciones |
| [Dependencias](dependencias.md) | Qué módulo importa a cuál, hoy y en la arquitectura objetivo |
| [Flujo](flujo.md) | El recorrido de los datos: ingesta → modelos → cartera → simulación → resultados |

Las decisiones de diseño se justifican en los [ADR](../adr/) (*Architecture Decision Records*).

## Editar y regenerar los diagramas

1. Edita el fichero `.mmd` del diagrama. Para ver los cambios mientras editas, pega el código en
   [mermaid.live](https://mermaid.live) o usa la extensión de VS Code *Mermaid Chart*.
2. Regenera la imagen SVG desde la raíz del repositorio (necesita [Node.js](https://nodejs.org/)):

   ```bash
   npx -p @mermaid-js/mermaid-cli@11.4.2 mmdc -c docs/architecture/diagramas/mermaid.json -b white -i docs/architecture/diagramas/flujo.mmd -o docs/architecture/diagramas/flujo.svg
   ```

   Cambia `flujo` por el nombre del diagrama editado. `mermaid.json` hace que el texto se
   guarde como texto SVG normal, para que la imagen se vea igual en cualquier visor.
3. Sube juntos el `.mmd` y el `.svg`, para que la imagen y su código no se desincronicen.
