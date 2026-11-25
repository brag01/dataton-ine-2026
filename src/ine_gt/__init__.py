"""Herramientas para consultar datos abiertos del INE Guatemala."""
from .client import INEClient
from .exceptions import INEAPIError, INEError

__version__ = "2.0.0"
__all__ = ["INEClient", "INEAPIError", "INEError"]

from .series import buscar_serie, buscar_municipio, cargar_serie, mostrar_fuente
__all__ += ["buscar_serie", "buscar_municipio", "cargar_serie", "mostrar_fuente"]
