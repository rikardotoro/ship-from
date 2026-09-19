"""What-ifs: re-solve the same month with something changed."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ship_from.data import Network
from ship_from.plan import Plan, nearest_rule, solve


@dataclass(frozen=True)
class Outage:
    site: str
    plan: Plan
    base: Plan

    @property
    def extra_cost(self) -> float:
        return self.plan.cost - self.base.cost


@dataclass(frozen=True)
class ExtraCapacity:
    site: str
    tonnes: float
    plan: Plan
    base: Plan

    @property
    def gain(self) -> float:
        return self.base.cost - self.plan.cost

    @property
    def shadow_estimate(self) -> float:
        return float(self.base.shadow_price[self.site] * self.tonnes)


def _capacity(net: Network, site: str) -> pd.Series:
    cap = net.sites["capacity_t"].astype(float).copy()
    if site not in cap.index:
        raise KeyError(f"unknown site {site!r}; sites are {', '.join(cap.index)}")
    return cap


def outage(net: Network, demand: pd.Series, costs: pd.DataFrame, site: str) -> Outage:
    cap = _capacity(net, site)
    base = solve(cap, demand, costs)
    cap[site] = 0.0
    return Outage(site, solve(cap, demand, costs), base)


def extra_capacity(net: Network, demand: pd.Series, costs: pd.DataFrame, site: str,
                   tonnes: float) -> ExtraCapacity:
    cap = _capacity(net, site)
    base = solve(cap, demand, costs)
    cap[site] += tonnes
    return ExtraCapacity(site, tonnes, solve(cap, demand, costs), base)


def month_by_month(net: Network, costs: pd.DataFrame) -> pd.DataFrame:
    """Plan cost, nearest-rule cost and the gap for every month in the file."""
    cap = net.sites["capacity_t"]
    rows = []
    for month in net.months:
        demand = net.demand_for(month)
        lp = solve(cap, demand, costs)
        rule = nearest_rule(cap, demand, costs, net.lanes)
        rows.append({"month": month, "tonnes": float(demand.sum()),
                     "utilisation": float(demand.sum() / cap.sum()),
                     "plan_cost": lp.cost, "rule_cost": rule.cost,
                     "gap_pct": (rule.cost - lp.cost) / rule.cost if rule.cost else 0.0,
                     "binding_sites": int((lp.shadow_price > 1e-9).sum())})
    return pd.DataFrame(rows).set_index("month")
