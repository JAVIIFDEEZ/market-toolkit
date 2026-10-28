"""Configuración global del paquete: constantes y variables de entorno (fichero `.env`)."""

import os

from dotenv import load_dotenv

load_dotenv()

DIAS_COTIZACION_ANUAL: int = 252
"""Número de sesiones bursátiles en un año, usado para anualizar estadísticos diarios."""

MIN_OBSERVACIONES: int = 30
"""Número mínimo de observaciones que debe tener una serie para considerarse válida."""

ALPHAVANTAGE_API_KEY: str | None = os.getenv("ALPHAVANTAGE_API_KEY") or None
"""Clave de la API de Alpha Vantage. `None` si no está configurada."""
