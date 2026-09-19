import numpy as np
import pandas as pd
import pytest

from ship_from.cost import CostParams, lane_costs
from ship_from.data import EXAMPLES, load_network
from ship_from.errors import InfeasiblePlanError
from ship_from.plan import nearest_rule, solve

MONTH = "2017-07"


@pytest.fixture(scope="module")
def net():
    return load_network(EXAMPLES)


@pytest.fixture(scope="module")
def costs(net):
    return lane_costs(net, CostParams())


def test_plan_meets_every_demand_and_respects_capacity(net, costs):
    demand = net.demand_for(MONTH)
    plan = solve(net.sites["capacity_t"], demand, costs)
    assert np.allclose(plan.allocation.sum(axis=0), demand)
    assert (plan.allocation.sum(axis=1) <= net.sites["capacity_t"] + 1e-6).all()
    assert np.isclose(plan.cost, (plan.allocation * costs).to_numpy().sum())


def test_unlimited_capacity_means_cheapest_lane_per_destination(net, costs):
    demand = net.demand_for(MONTH)
    huge = net.sites["capacity_t"] * 0 + 1e9
    plan = solve(huge, demand, costs)
    for d in demand.index:
        if demand[d] > 0:
            assert plan.allocation[d].idxmax() == costs[d].idxmin()
    assert np.isclose(plan.cost, (costs.min(axis=0) * demand).sum())


def test_plan_never_costs_more_than_the_nearest_rule(net, costs):
    for month in net.months:
        demand = net.demand_for(month)
        lp = solve(net.sites["capacity_t"], demand, costs)
        rule = nearest_rule(net.sites["capacity_t"], demand, costs, net.lanes)
        assert lp.cost <= rule.cost + 1e-6
        assert np.allclose(rule.allocation.sum(axis=0), demand)


def test_demo_month_has_a_real_gap(net, costs):
    demand = net.demand_for(MONTH)
    lp = solve(net.sites["capacity_t"], demand, costs)
    rule = nearest_rule(net.sites["capacity_t"], demand, costs, net.lanes)
    assert lp.cost < rule.cost  # the demo month has a real gap


def test_shadow_price_equals_finite_difference(net, costs):
    demand = net.demand_for(MONTH)
    cap = net.sites["capacity_t"].astype(float)
    base = solve(cap, demand, costs)
    for site in cap.index:
        bumped = cap.copy(); bumped[site] += 1.0
        gain = base.cost - solve(bumped, demand, costs).cost
        assert np.isclose(gain, base.shadow_price[site], atol=1e-6)
        assert base.shadow_price[site] >= 0


def test_marginal_cost_equals_one_more_tonne_of_demand(net, costs):
    demand = net.demand_for(MONTH).astype(float)
    cap = net.sites["capacity_t"]
    base = solve(cap, demand, costs)
    d = "Germany"
    more = demand.copy(); more[d] += 1.0
    assert np.isclose(solve(cap, more, costs).cost - base.cost, base.marginal_cost[d], atol=1e-6)


def test_infeasible_month_names_the_shortfall(net, costs):
    demand = net.demand_for(MONTH) * 2
    with pytest.raises(InfeasiblePlanError, match=r"short by [\d,]+ t"):
        solve(net.sites["capacity_t"], demand, costs)


def test_joke_refusal_negative_value(net):
    with pytest.raises(ValueError, match="pay you"):
        CostParams(value=-5).validate()
