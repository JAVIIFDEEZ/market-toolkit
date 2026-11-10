"""
market-toolkit: extracción, estandarización y análisis de datos bursátiles, y gestión y simulación
de carteras de inversión.

Las clases principales se pueden importar directamente desde el paquete:

    from market_toolkit import Portfolio, YahooFinanceProvider
"""

from importlib.metadata import PackageNotFoundError, version

from market_toolkit.exceptions import (
    DataNotFoundException,
    DataValidationError,
    InsufficientDataError,
    MarketToolkitError,
    ProviderError,
    RateLimitError,
)
from market_toolkit.models import (
    FinancialSeries,
    Fundamentales,
    MacroSeries,
    Portfolio,
    SerieTemporal,
    TipoActivo,
)
from market_toolkit.providers.providers import (
    AlphaVantageProvider,
    MacroProvider,
    PolygonProvider,
    Provider,
    YahooFinanceProvider,
)
from market_toolkit.simulation import MonteCarlo

try:
    __version__ = version("market-toolkit")  # La versión del pyproject.toml instalado
except PackageNotFoundError:  # Código usado sin instalar el paquete
    __version__ = "desconocida"

__all__ = [
    # Proveedores
    "Provider",
    "YahooFinanceProvider",
    "PolygonProvider",
    "AlphaVantageProvider",
    "MacroProvider",
    # Modelos
    "SerieTemporal",
    "FinancialSeries",
    "MacroSeries",
    "TipoActivo",
    "Fundamentales",
    "Portfolio",
    # Simulación
    "MonteCarlo",
    # Excepciones
    "MarketToolkitError",
    "DataNotFoundException",
    "ProviderError",
    "RateLimitError",
    "DataValidationError",
    "InsufficientDataError",
]
