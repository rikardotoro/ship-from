"""Assemble one month's analysis and render it (rich or JSON)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from rich.console import Console
from rich.table import Table

from ship_from.cost import CostParams, lane_breakdown, lane_costs
from ship_from.data import EXAMPLES, Network
from ship_from.errors import InfeasiblePlanError
from ship_from.plan import Plan, nearest_rule, solve
from ship_from.scenarios import ExtraCapacity, Outage, extra_capacity, month_by_month, outage

DEMO_MONTH = "2017-07"
EXTRA_TONNES = 500.0


@dataclass(frozen=True)
class Result:
    month: str
    params: CostParams
    net: Network
    demand: pd.Series
    costs: pd.DataFrame
    plan: Plan
    rule: Plan
    breakdown: dict[str, float]          # $ by component under the plan
    months: pd.DataFrame                 # month_by_month table
    extra: ExtraCapacity | None
    outage: Outage | None
    outage_error: str | None = None
    moved: pd.DataFrame = field(default_factory=pd.DataFrame)  # lanes where plan != rule

    @property
    def gap(self) -> float:
        return self.rule.cost - self.plan.cost

    @property
    def gap_pct(self) -> float:
        return self.gap / self.rule.cost if self.rule.cost else 0.0

    @property
    def utilisation(self) -> float:
        return float(self.demand.sum() / self.net.sites["capacity_t"].sum())


def analyse(net: Network, month: str = DEMO_MONTH, params: CostParams = CostParams(),
            extra_site: str | None = None, extra_tonnes: float = EXTRA_TONNES,
            outage_site: str | None = None) -> Result:
    params.validate()
    demand = net.demand_for(month)
    costs = lane_costs(net, params)
    cap = net.sites["capacity_t"]
    plan = solve(cap, demand, costs)
    rule = nearest_rule(cap, demand, costs, net.lanes)
    parts = lane_breakdown(net, params)
    breakdown = {k: float((plan.allocation * v).to_numpy().sum()) for k, v in parts.items()}
    months = month_by_month(net, costs)
    site = extra_site or plan.shadow_price.idxmax()
    extra = extra_capacity(net, demand, costs, site, extra_tonnes)
    out, err = None, None
    if outage_site:
        try:
            out = outage(net, demand, costs, outage_site)
        except InfeasiblePlanError as e:
            err = str(e)
    diff = plan.allocation.round(0) - rule.allocation.round(0)
    moved = diff.loc[:, (diff.abs() > 0.5).any()]
    return Result(month, params, net, demand, costs, plan, rule, breakdown, months, extra, out, err, moved)


def to_dict(r: Result) -> dict:
    cap = r.net.sites["capacity_t"]
    return {
        "month": r.month,
        "params": vars(r.params),
        "tonnes": float(r.demand.sum()),
        "capacity": float(cap.sum()),
        "utilisation": r.utilisation,
        "plan_cost": r.plan.cost,
        "rule_cost": r.rule.cost,
        "gap": r.gap,
        "gap_pct": r.gap_pct,
        "plan_cost_per_t": r.plan.cost_per_tonne,
        "breakdown": r.breakdown,
        "cash_at_sea_share": r.breakdown["cash_at_sea"] / r.plan.cost if r.plan.cost else 0.0,
        "shadow_price": {k: float(v) for k, v in r.plan.shadow_price.items()},
        "site_utilisation": {k: float(v) for k, v in r.plan.utilisation(cap).items()},
        "marginal_cost": {k: float(v) for k, v in r.plan.marginal_cost.items()},
        "allocation": {s: {d: float(v) for d, v in row.items() if v > 0.5} for s, row in r.plan.allocation.iterrows()},
        "rule_allocation": {s: {d: float(v) for d, v in row.items() if v > 0.5} for s, row in r.rule.allocation.iterrows()},
        "moved": {s: {d: float(v) for d, v in row.items() if abs(v) > 0.5} for s, row in r.moved.iterrows()},
        "months": r.months.reset_index().to_dict(orient="records"),
        "extra_capacity": None if r.extra is None else {
            "site": r.extra.site, "tonnes": r.extra.tonnes, "gain": r.extra.gain,
            "shadow_estimate": r.extra.shadow_estimate},
        "outage": None if r.outage is None else {
            "site": r.outage.site, "extra_cost": r.outage.extra_cost,
            "extra_cost_pct": r.outage.extra_cost / r.outage.base.cost},
        "outage_error": r.outage_error,
    }


def _money(x: float) -> str:
    return f"${x:,.0f}"


def render(r: Result, console: Console) -> None:
    cap = r.net.sites["capacity_t"]
    console.print(f"[bold]{r.month}[/bold]: {r.demand.sum():,.0f} t to {int((r.demand > 0).sum())} destinations "
                  f"from {len(cap)} sites, {r.utilisation:.0%} of capacity")
    console.print(f"  nearest-site rule  {_money(r.rule.cost)}")
    console.print(f"  linear program     {_money(r.plan.cost)}   "
                  f"[bold]{r.gap_pct:.1%} less[/bold] ({_money(r.gap)}) than the rule")
    share = r.breakdown["cash_at_sea"] / r.plan.cost if r.plan.cost else 0
    console.print(f"  landed cost {r.plan.cost_per_tonne:,.0f} $/t: handling {r.breakdown['handling'] / r.plan.cost:.0%}, "
                  f"freight {r.breakdown['freight'] / r.plan.cost:.0%}, cash at sea {share:.0%} "
                  f"(goods at ${r.params.value:,.0f}/t, {r.params.capital_rate:.0%} a year)")
    if not r.moved.empty:
        console.print("\n[bold]What the plan moves[/bold] (tonnes, plan minus rule)")
        t = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
        t.add_column("site")
        for d in r.moved.columns:
            t.add_column(d, justify="right")
        for s, row in r.moved.iterrows():
            t.add_row(s, *[f"{v:+,.0f}" if abs(v) > 0.5 else "" for v in row])
        console.print(t)
    console.print("\n[bold]Sites[/bold]")
    t = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    for col, just in (("site", "left"), ("capacity", "right"), ("used", "right"), ("shadow price $/t", "right")):
        t.add_column(col, justify=just)
    util = r.plan.utilisation(cap)
    for s in cap.index:
        sp = r.plan.shadow_price[s]
        t.add_row(s, f"{cap[s]:,.0f}", f"{util[s]:.0%}", f"{sp:,.0f}" if sp > 0.5 else "0 (slack)")
    console.print(t)
    if r.extra is not None:
        e = r.extra
        console.print(f"  +{e.tonnes:,.0f} t at {e.site}: saves {_money(e.gain)} this month "
                      f"(shadow price said up to {_money(e.shadow_estimate)})")
    if r.outage is not None:
        o = r.outage
        console.print(f"  {o.site} down: plan still feasible, costs {_money(o.extra_cost)} more "
                      f"({o.extra_cost / o.base.cost:+.1%})")
    if r.outage_error:
        console.print(f"  outage: [red]{r.outage_error}[/red]")
    console.print("\n[bold]Every month[/bold]  (utilisation → gap between rule and plan)")
    for m, row in r.months.iterrows():
        bar = "█" * int(round(row["gap_pct"] * 100)) if row["gap_pct"] > 0.0005 else ""
        console.print(f"  {m}  {row['utilisation']:>4.0%}  {max(row['gap_pct'], 0.0):>6.1%} {bar}")
    console.print("\nSource: demand from DataCo (CC0), lanes from searoute; sites and costs are stated parameters.")
