"""Interfaz web local del toolkit: una página para hacer en el navegador lo que hace la demo."""

from .aplicacion import Aplicacion
from .servidor import crear_servidor, servir

__all__ = ["Aplicacion", "crear_servidor", "servir"]
