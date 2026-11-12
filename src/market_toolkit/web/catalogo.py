"""
Catálogo de activos de la interfaz web: tickers habituales agrupados, para elegirlos sin tener que
conocerlos de memoria. Cualquier otro ticker de Yahoo Finance se puede buscar o escribir a mano.
"""

# Grupo -> lista de (ticker, nombre)
ACTIVOS = {
    "Tecnológicas EE. UU.": [
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("GOOGL", "Alphabet (Google)"),
        ("AMZN", "Amazon"),
        ("NVDA", "NVIDIA"),
        ("META", "Meta Platforms"),
        ("TSLA", "Tesla"),
        ("NFLX", "Netflix"),
    ],
    "Finanzas, salud y consumo EE. UU.": [
        ("JPM", "JPMorgan Chase"),
        ("BAC", "Bank of America"),
        ("GS", "Goldman Sachs"),
        ("V", "Visa"),
        ("JNJ", "Johnson & Johnson"),
        ("PFE", "Pfizer"),
        ("KO", "Coca-Cola"),
        ("PG", "Procter & Gamble"),
        ("WMT", "Walmart"),
        ("MCD", "McDonald's"),
        ("XOM", "ExxonMobil"),
        ("DIS", "Walt Disney"),
    ],
    "IBEX 35 (en euros)": [
        ("SAN.MC", "Banco Santander"),
        ("BBVA.MC", "BBVA"),
        ("ITX.MC", "Inditex"),
        ("IBE.MC", "Iberdrola"),
        ("TEF.MC", "Telefónica"),
        ("REP.MC", "Repsol"),
        ("AENA.MC", "Aena"),
        ("FER.MC", "Ferrovial"),
    ],
    "Europa": [
        ("ASML.AS", "ASML (Países Bajos)"),
        ("MC.PA", "LVMH (Francia)"),
        ("SAP.DE", "SAP (Alemania)"),
        ("SIE.DE", "Siemens (Alemania)"),
        ("NESN.SW", "Nestlé (Suiza)"),
    ],
    "ETF": [
        ("SPY", "SPDR S&P 500"),
        ("QQQ", "Invesco Nasdaq 100"),
        ("VTI", "Vanguard Total Stock Market"),
        ("EEM", "iShares mercados emergentes"),
        ("TLT", "iShares bonos EE. UU. 20+ años"),
        ("GLD", "SPDR Gold Shares"),
    ],
    "Materias primas (Alpha Vantage)": [
        ("GOLD", "Oro"),
        ("SILVER", "Plata"),
        ("BRENT", "Petróleo Brent"),
    ],
}

# Índices que se pueden usar como referencia (no pueden formar parte de la cartera)
INDICES = [
    ("^GSPC", "S&P 500"),
    ("^NDX", "Nasdaq 100"),
    ("^DJI", "Dow Jones"),
    ("^IBEX", "IBEX 35"),
    ("^STOXX50E", "Euro Stoxx 50"),
    ("^GDAXI", "DAX"),
    ("^FTSE", "FTSE 100"),
    ("^N225", "Nikkei 225"),
]

# Series macro de FRED: alias de MacroProvider.SERIES -> descripción
SERIES_MACRO = {
    "us10y": "Bono EE. UU. a 10 años (%)",
    "us2y": "Bono EE. UU. a 2 años (%)",
    "us10y_2y": "Diferencial 10 años - 2 años EE. UU. (p. p.)",
    "fed_funds": "Tipo de la Fed (%)",
    "bce_depo": "Facilidad de depósito del BCE (%)",
    "es10y": "Bono España a 10 años (%)",
    "de10y": "Bund alemán a 10 años (%)",
    "cpi_eeuu": "IPC EE. UU. (índice)",
    "ipc_eurozona": "IPC armonizado eurozona (índice)",
    "paro_eeuu": "Tasa de paro EE. UU. (%)",
    "pib_eeuu": "PIB real EE. UU.",
    "pib_espana": "PIB real España",
    "eurusd": "Dólares por euro",
    "vix": "VIX: volatilidad esperada del S&P 500",
    "hy_spread": "Diferencial de la deuda high yield (%)",
    "wti": "Petróleo WTI ($/barril)",
    "breakeven10y": "Inflación esperada a 10 años EE. UU. (%)",
}


def tickers_del_grupo(grupo: str) -> list[str]:
    """Tickers de un grupo del catálogo (por ejemplo, "ETF")."""
    return [ticker for ticker, nombre in ACTIVOS.get(grupo, [])]


def todos_los_activos() -> list[dict]:
    """Lista plana del catálogo, con el grupo de cada activo."""
    lista = []
    for grupo, activos in ACTIVOS.items():
        for ticker, nombre in activos:
            lista.append({"ticker": ticker, "nombre": nombre, "grupo": grupo})
    for ticker, nombre in INDICES:
        lista.append({"ticker": ticker, "nombre": nombre, "grupo": "Índices"})
    return lista


def buscar_en_catalogo(texto: str, maximo: int = 10) -> list[dict]:
    """Activos del catálogo cuyo ticker o nombre contienen el texto (sin distinguir mayúsculas)."""
    texto = texto.strip().lower()
    encontrados = []
    for activo in todos_los_activos():
        if texto in activo["ticker"].lower() or texto in activo["nombre"].lower():
            encontrados.append(activo)
    return encontrados[:maximo]
