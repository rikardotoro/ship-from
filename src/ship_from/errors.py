class ShipFromError(Exception):
    """Base class for all ship-from errors."""


class MissingColumnError(ShipFromError):
    """A required column could not be found or mapped."""


class InvalidDataError(ShipFromError):
    """A row or value failed validation."""


class InfeasiblePlanError(ShipFromError):
    """Demand exceeds what the sites can ship this month."""
