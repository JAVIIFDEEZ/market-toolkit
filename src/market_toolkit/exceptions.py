class MarketToolkitError(Exception):
    """Excepción base de la que heredan todas las excepciones del paquete."""


class DataNotFoundException(MarketToolkitError):
    """No se ha encontrado información para los activos solicitados."""


class ProviderError(MarketToolkitError):
    """Error devuelto por un proveedor de datos o en la comunicación con él."""


class RateLimitError(ProviderError):
    """Se ha superado el límite de peticiones permitido por el proveedor."""


class DataValidationError(MarketToolkitError):
    """Los datos no cumplen las condiciones necesarias para construir el objeto."""


class InsufficientDataError(DataValidationError):
    """La serie no tiene suficientes observaciones para calcular sus estadísticos."""
