"""Arranca la interfaz web: `python -m market_toolkit.web [--sin-red] [--puerto 8000]`."""

import argparse

import matplotlib

matplotlib.use("Agg")  # El servidor no abre ventanas: los gráficos se envían a la página

from market_toolkit.web.servidor import servir  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Interfaz web de market-toolkit")
    parser.add_argument("--puerto", type=int, default=8000, help="puerto local (por defecto, 8000)")
    parser.add_argument(
        "--sin-red", action="store_true", help="marca por defecto los datos sintéticos"
    )
    parser.add_argument("--no-abrir", action="store_true", help="no abre el navegador al arrancar")
    argumentos = parser.parse_args()
    servir(argumentos.puerto, sin_red=argumentos.sin_red, abrir_navegador=not argumentos.no_abrir)


if __name__ == "__main__":
    main()
