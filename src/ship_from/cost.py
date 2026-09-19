"""Price every lane per tonne: handling + freight + the cash tied up at sea."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ship_from.data import Network


@dataclass(frozen=True)
class CostParams:
    value: float = 20_000.0        # $ per tonne of goods
    capital_rate: float = 0.12     # annual cost of capital
    freight_per_t_km: float = 0.012
    port_days: float = 4.0         # days in port at both ends, in total

    def validate(self) -> "CostParams":
        if self.value < 0:
            raise ValueError("a negative unit value means customers pay you to take the goods; "
                             "ship-from does not plan that business")
        for name in ("capital_rate", "freight_per_t_km", "port_days"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")
        return self

    def cash_per_day(self) -> float:
        return self.value * self.capital_rate / 365.0


def lane_costs(net: Network, params: CostParams = CostParams()) -> pd.DataFrame:
    """$ per tonne for each site (rows) x destination (columns)."""
    handling = net.sites["handling_per_t"].to_numpy()[:, None]
    freight = params.freight_per_t_km * net.lanes
    transit = (net.sea_days + params.port_days).where(net.lanes > 0, 0.0)
    cash = params.cash_per_day() * transit
    return freight + cash + handling


def lane_breakdown(net: Network, params: CostParams = CostParams()) -> dict[str, pd.DataFrame]:
    transit = (net.sea_days + params.port_days).where(net.lanes > 0, 0.0)
    return {
        "handling": pd.DataFrame(net.sites["handling_per_t"].to_numpy()[:, None].repeat(net.lanes.shape[1], 1),
                                 index=net.lanes.index, columns=net.lanes.columns),
        "freight": params.freight_per_t_km * net.lanes,
        "cash_at_sea": params.cash_per_day() * transit,
    }
