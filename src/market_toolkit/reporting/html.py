"""
Conversión del informe de la cartera de Markdown a una página HTML autocontenida.

El informe se genera siempre en Markdown (apartado 4.5 del enunciado) y este módulo lo traduce a
HTML con estilo propio y, si se indican, los gráficos incrustados como imágenes. El fichero
resultante no necesita nada más: se abre en cualquier navegador y se puede enviar tal cual.

Solo traduce lo que usa el informe: títulos, listas (con un nivel de anidación), tablas, negritas
y código. Así no hace falta ninguna librería externa.
"""

import base64
import html
import io
import re
from collections.abc import Mapping

from matplotlib.figure import Figure

ESTILO = """
:root { --texto: #0b0b0b; --secundario: #52514e; --borde: #e1e0d9; --fondo: #fcfcfb;
        --acento: #2a78d6; --aviso: #fff4e5; --borde-aviso: #e8590c; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--fondo); color: var(--texto);
       font: 15px/1.55 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 1000px; margin: 0 auto; padding: 32px 24px 64px; }
h1 { font-size: 28px; margin: 0 0 4px; }
h2 { font-size: 20px; margin: 36px 0 12px; padding-bottom: 6px;
     border-bottom: 2px solid var(--borde); }
h3 { font-size: 16px; margin: 24px 0 8px; color: var(--secundario); }
ul { padding-left: 22px; margin: 8px 0; }
li { margin: 3px 0; }
strong { font-weight: 600; }
code { background: #f0efea; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
table { border-collapse: collapse; margin: 10px 0 18px; width: 100%; font-size: 14px; }
th, td { padding: 7px 10px; border-bottom: 1px solid var(--borde); text-align: left; }
th { background: #f3f2ed; font-weight: 600; }
td.numero, th.numero { text-align: right; font-variant-numeric: tabular-nums; }
tbody tr:hover { background: #f7f6f2; }
section.advertencias li { background: var(--aviso); border-left: 3px solid var(--borde-aviso);
                          list-style: none; margin: 6px 0 6px -22px; padding: 6px 10px; }
figure { margin: 18px 0 28px; }
figure img { max-width: 100%; height: auto; border: 1px solid var(--borde); border-radius: 6px; }
figcaption { color: var(--secundario); font-size: 13px; margin-top: 4px; }
footer { margin-top: 40px; color: var(--secundario); font-size: 13px; }
@media print { body { background: #fff; } main { max-width: none; padding: 0; } }
"""

# Título legible de cada gráfico de plots_report(), en el orden en que se muestran
TITULOS_GRAFICOS = {
    "evolucion": "Evolución de la cartera frente a sus activos",
    "drawdown": "Drawdown de la cartera",
    "pesos": "Evolución de los pesos",
    "riesgo_rentabilidad": "Riesgo y rentabilidad de cada activo",
    "contribucion": "Contribución de cada activo a la rentabilidad",
    "correlacion": "Correlación entre los activos",
}


def figura_a_base64(figura: Figure) -> str:
    """
    Convierte una figura de matplotlib en una imagen PNG codificada en base64, para incrustarla en
    el HTML sin ficheros aparte.
    :param figura: Figura de matplotlib.
    :return: Texto base64 de la imagen PNG.
    """
    memoria = io.BytesIO()
    figura.savefig(
        memoria, format="png", dpi=120, bbox_inches="tight", facecolor=figura.get_facecolor()
    )
    return base64.b64encode(memoria.getvalue()).decode("ascii")


def _en_linea(texto: str) -> str:
    """Escapa el texto y traduce las negritas (`**texto**`) y el código (`` `texto` ``)."""
    texto = html.escape(texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", texto)


def _es_numero(celda: str) -> bool:
    """`True` si la celda contiene un número (con %, signo o separadores), para alinearla."""
    return re.fullmatch(r"[-+]?[\d.,]+\s*%?", celda.strip()) is not None


def _tabla(filas: list[str]) -> str:
    """Traduce las líneas de una tabla Markdown (cabecera, separador y filas) a HTML."""
    celdas = [[celda.strip() for celda in fila.strip().strip("|").split("|")] for fila in filas]
    cabecera, cuerpo = celdas[0], celdas[2:]
    # La alineación a la derecha se marca en el separador (`---:`) o se deduce de los números
    derecha = (
        [separador.endswith(":") for separador in celdas[1]]
        if len(celdas) > 1
        else [False] * len(cabecera)
    )
    partes = ["<table>", "<thead><tr>"]
    for i, titulo in enumerate(cabecera):
        clase = ' class="numero"' if derecha[i] else ""
        partes.append(f"<th{clase}>{_en_linea(titulo)}</th>")
    partes.append("</tr></thead>")
    partes.append("<tbody>")
    for fila in cuerpo:
        partes.append("<tr>")
        for i, celda in enumerate(fila):
            numero = (i < len(derecha) and derecha[i]) or _es_numero(celda)
            clase = ' class="numero"' if numero else ""
            partes.append(f"<td{clase}>{_en_linea(celda)}</td>")
        partes.append("</tr>")
    partes.append("</tbody></table>")
    return "".join(partes)


def markdown_a_html(texto: str) -> str:
    """
    Traduce el Markdown del informe al cuerpo de una página HTML.
    :param texto: Informe en Markdown.
    :return: Fragmento HTML con las secciones del informe.
    """
    lineas = texto.splitlines()
    partes: list[str] = []
    seccion_abierta = False
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if linea.startswith("# "):
            partes.append(f"<h1>{_en_linea(linea[2:])}</h1>")
        elif linea.startswith("## "):
            if seccion_abierta:
                partes.append("</section>")
            titulo = linea[3:]
            clase = ' class="advertencias"' if "advertencias" in titulo.lower() else ""
            partes.append(f"<section{clase}><h2>{_en_linea(titulo)}</h2>")
            seccion_abierta = True
        elif linea.startswith("### "):
            partes.append(f"<h3>{_en_linea(linea[4:])}</h3>")
        elif linea.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                filas.append(lineas[i])
                i += 1
            partes.append(_tabla(filas))
            continue
        elif linea.startswith("- "):
            partes.append("<ul>")
            while i < len(lineas) and (lineas[i].startswith("- ") or lineas[i].startswith("  - ")):
                elemento = _en_linea(lineas[i][2:])
                i += 1
                # Subelementos (dos espacios delante): una lista dentro del elemento
                subelementos = []
                while i < len(lineas) and lineas[i].startswith("  - "):
                    subelementos.append(f"<li>{_en_linea(lineas[i][4:])}</li>")
                    i += 1
                if subelementos:
                    elemento += "<ul>" + "".join(subelementos) + "</ul>"
                partes.append(f"<li>{elemento}</li>")
            partes.append("</ul>")
            continue
        elif linea.strip():
            partes.append(f"<p>{_en_linea(linea)}</p>")
        i += 1
    if seccion_abierta:
        partes.append("</section>")
    return "\n".join(partes)


def informe_html(
    texto_markdown: str,
    figuras: Mapping[str, Figure] | None = None,
    titulo: str = "Informe de cartera",
) -> str:
    """
    Genera una página HTML completa y autocontenida con el informe y, opcionalmente, sus gráficos.
    :param texto_markdown: Informe en Markdown.
    :param figuras: Figuras a incrustar al final, por ejemplo las de `plots_report()`.
    :param titulo: Título de la pestaña del navegador.
    :return: Documento HTML.
    """
    cuerpo = markdown_a_html(texto_markdown)
    graficos = ""
    if figuras:
        bloques = []
        for nombre, figura in figuras.items():
            leyenda = html.escape(
                TITULOS_GRAFICOS.get(nombre, nombre.replace("_", " ").capitalize())
            )
            bloques.append(
                f'<figure><img alt="{leyenda}" '
                f'src="data:image/png;base64,{figura_a_base64(figura)}">'
                f"<figcaption>{leyenda}</figcaption></figure>"
            )
        graficos = "<section><h2>Gráficos</h2>" + "".join(bloques) + "</section>"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(titulo)}</title>\n<style>{ESTILO}</style>\n</head>\n<body>\n<main>\n"
        f"{cuerpo}\n{graficos}\n"
        "<footer>Generado con market-toolkit.</footer>\n"
        "</main>\n</body>\n</html>\n"
    )
