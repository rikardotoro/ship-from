import importlib


def test_package_imports():
    assert importlib.import_module("ship_from")


def test_errors_hierarchy():
    from ship_from.errors import InfeasiblePlanError, ShipFromError
    assert issubclass(InfeasiblePlanError, ShipFromError)
