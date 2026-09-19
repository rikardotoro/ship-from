import numpy as np
import pytest

from ship_from.cost import CostParams, lane_costs
from ship_from.data import EXAMPLES, load_network
from ship_from.errors import InfeasiblePlanError
from ship_from.plan import solve
from ship_from.scenarios import extra_capacity, month_by_month, outage


@pytest.fixture(scope="module")
def net():
    return load_network(EXAMPLES)


@pytest.fixture(scope="module")
def costs(net):
    return lane_costs(net, CostParams())


def test_month_by_month_gap_is_zero_when_capacity_is_slack(net, costs):
    table = month_by_month(net, costs)
    assert list(table.index) == net.months
    slack = table[table["utilisation"] < 0.6]
    assert (slack["gap_pct"].abs() < 1e-6).all()
    assert table["gap_pct"].max() > 0.10


def test_extra_capacity_gain_never_exceeds_shadow_price_times_tonnes(net, costs):
    demand = net.demand_for("2017-07")
    base = solve(net.sites["capacity_t"], demand, costs)
    for site in net.sites.index:
        r = extra_capacity(net, demand, costs, site, 500)
        assert r.gain <= base.shadow_price[site] * 500 + 1e-6
        assert r.gain >= 0
    assert extra_capacity(net, demand, costs, "Savannah", 1).gain == pytest.approx(base.shadow_price["Savannah"], abs=1e-6)


def test_outage_in_a_slack_month_reallocates_and_costs_more(net, costs):
    r = outage(net, net.demand_for("2017-03"), costs, "Santos")
    assert r.plan.allocation.loc["Santos"].sum() == 0
    assert r.extra_cost > 0


def test_outage_in_the_peak_month_names_the_shortfall(net, costs):
    with pytest.raises(InfeasiblePlanError, match="short by"):
        outage(net, net.demand_for("2017-07"), costs, "Singapore")


def test_unknown_site_is_refused(net, costs):
    with pytest.raises(KeyError, match="Atlantis"):
        outage(net, net.demand_for("2017-03"), costs, "Atlantis")
