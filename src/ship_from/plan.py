"""The transportation linear program and the rule it is measured against."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from ship_from.errors import InfeasiblePlanError


@dataclass(frozen=True)
class Plan:
    allocation: pd.DataFrame     # tonnes, sites x destinations
    cost: float                  # $ for the month
    shadow_price: pd.Series      # $ per extra tonne of capacity at each site (0 when slack)
    marginal_cost: pd.Series     # $ delivered cost of one more tonne at each destination
    method: str

    @property
    def tonnes(self) -> float:
        return float(self.allocation.to_numpy().sum())

    @property
    def cost_per_tonne(self) -> float:
        return self.cost / self.tonnes if self.tonnes else 0.0

    def utilisation(self, capacity: pd.Series) -> pd.Series:
        return self.allocation.sum(axis=1) / capacity


def solve(capacity: pd.Series, demand: pd.Series, costs: pd.DataFrame) -> Plan:
    """min sum c_ij x_ij  s.t.  sum_j x_ij <= cap_i,  sum_i x_ij = dem_j,  x >= 0."""
    sites, dests = list(costs.index), list(costs.columns)
    cap = capacity.reindex(sites).to_numpy(float)
    dem = demand.reindex(dests).fillna(0.0).to_numpy(float)
    if dem.sum() > cap.sum() + 1e-9:
        raise InfeasiblePlanError(
            f"demand {dem.sum():,.0f} t exceeds capacity {cap.sum():,.0f} t: "
            f"short by {dem.sum() - cap.sum():,.0f} t this month")
    m, n = len(sites), len(dests)
    c = costs.to_numpy(float).ravel()
    a_ub = np.zeros((m, m * n)); a_eq = np.zeros((n, m * n))
    for i in range(m):
        a_ub[i, i * n:(i + 1) * n] = 1.0
    for j in range(n):
        a_eq[j, j::n] = 1.0
    res = linprog(c, A_ub=a_ub, b_ub=cap, A_eq=a_eq, b_eq=dem, bounds=(0, None), method="highs")
    if not res.success:
        raise InfeasiblePlanError(f"solver failed: {res.message}")
    x = pd.DataFrame(res.x.reshape(m, n), index=sites, columns=dests).clip(lower=0.0)
    shadow = pd.Series(-res.ineqlin.marginals, index=sites).clip(lower=0.0)
    marginal = pd.Series(res.eqlin.marginals, index=dests)
    return Plan(x, float(res.fun), shadow, marginal, "linear program")


def nearest_rule(capacity: pd.Series, demand: pd.Series, costs: pd.DataFrame,
                 km: pd.DataFrame) -> Plan:
    """Serve each destination from the nearest site with capacity left; overflow to the
    next nearest. Destinations are taken largest first, as a planner would."""
    sites, dests = list(costs.index), list(costs.columns)
    left = capacity.reindex(sites).astype(float).copy()
    x = pd.DataFrame(0.0, index=sites, columns=dests)
    dem = demand.reindex(dests).fillna(0.0).astype(float)
    if dem.sum() > left.sum() + 1e-9:
        raise InfeasiblePlanError(
            f"demand {dem.sum():,.0f} t exceeds capacity {left.sum():,.0f} t: "
            f"short by {dem.sum() - left.sum():,.0f} t this month")
    for d in dem.sort_values(ascending=False).index:
        need = dem[d]
        for s in km[d].sort_values().index:
            if need <= 0:
                break
            take = min(need, left[s])
            x.loc[s, d] += take; left[s] -= take; need -= take
    cost = float((x * costs).to_numpy().sum())
    zeros = pd.Series(0.0, index=sites)
    return Plan(x, cost, zeros, pd.Series(np.nan, index=dests), "nearest site")
