import market_toolkit


def test_api_publica_completa():
    for nombre in market_toolkit.__all__:
        assert hasattr(market_toolkit, nombre), nombre


def test_version_del_paquete():
    assert market_toolkit.__version__ != "desconocida"
    assert market_toolkit.__version__.count(".") == 2  # MAYOR.MENOR.PARCHE
