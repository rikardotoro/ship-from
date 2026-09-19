import numpy as np

from ship_from.cost import CostParams, lane_costs
from ship_from.data import EXAMPLES, load_network


def test_zero_value_leaves_freight_and_handling_only():
    net = load_network(EXAMPLES)
    c = lane_costs(net, CostParams(value=0, capital_rate=0.12, freight_per_t_km=0.012, port_days=4))
    expected = 22 + 0.012 * net.lanes.loc["Rotterdam", "France"]
    assert np.isclose(c.loc["Rotterdam", "France"], expected)


def test_cash_at_sea_is_value_times_rate_times_days():
    net = load_network(EXAMPLES)
    p = CostParams(value=20000, capital_rate=0.12, freight_per_t_km=0.0, port_days=0)
    c = lane_costs(net, p)
    days = net.sea_days.loc["Singapore", "Japan"]
    assert np.isclose(c.loc["Singapore", "Japan"], 20 + 20000 * 0.12 * days / 365)


def test_cost_is_monotone_in_distance_for_one_site():
    net = load_network(EXAMPLES)
    c = lane_costs(net, CostParams())
    row = c.loc["Rotterdam"]
    km = net.lanes.loc["Rotterdam"]
    order = km.sort_values().index
    assert (np.diff(row[order].to_numpy()) >= 0).all()
