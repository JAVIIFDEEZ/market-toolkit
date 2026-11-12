from matplotlib.figure import Figure

from market_toolkit.reporting import informe_html, markdown_a_html

INFORME = """# Informe de cartera

## Riesgo

- **Volatilidad anualizada:** 12.00%
- **Último rebalanceo:** 2024-01-02
  - AAA: 50.00%
  - BBB: 50.00%

### Composición

| Activo | Peso |
| --- | ---: |
| AAA | 50.00% |
| B<C | 50.00% |

## Diagnósticos y advertencias

- Concentración elevada en **AAA**.
"""


def test_traduce_titulos_listas_y_tablas():
    cuerpo = markdown_a_html(INFORME)
    assert "<h1>Informe de cartera</h1>" in cuerpo
    assert "<h2>Riesgo</h2>" in cuerpo
    assert "<h3>Composición</h3>" in cuerpo
    assert "<strong>Volatilidad anualizada:</strong> 12.00%" in cuerpo
    assert "<ul><li>AAA: 50.00%</li><li>BBB: 50.00%</li></ul>" in cuerpo  # Lista anidada
    assert '<th class="numero">Peso</th>' in cuerpo
    assert '<td class="numero">50.00%</td>' in cuerpo


def test_escapa_el_html_del_contenido():
    assert "<td>B&lt;C</td>" in markdown_a_html(INFORME)


def test_marca_la_seccion_de_advertencias():
    assert '<section class="advertencias"><h2>Diagnósticos y advertencias</h2>' in markdown_a_html(
        INFORME
    )


def test_pagina_completa_con_graficos():
    figura = Figure()
    figura.subplots().plot([1, 2, 3])
    pagina = informe_html(INFORME, {"evolucion": figura})
    assert pagina.startswith("<!DOCTYPE html>")
    assert '<html lang="es">' in pagina
    assert "<figcaption>Evolución de la cartera frente a sus activos</figcaption>" in pagina
    assert pagina.count('src="data:image/png;base64,') == 1
