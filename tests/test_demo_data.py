from pathlib import Path

import pandas as pd

EX = Path(__file__).parent.parent / "src" / "ship_from" / "examples"


def test_demand_has_12_months_and_20_destinations_every_month():
    d = pd.read_csv(EX / "demand.csv")
    assert d["month"].nunique() == 12
    assert (d.groupby("month")["destination"].nunique() == 20).all()
    assert (d["tonnes"] > 0).all()


def test_lanes_cover_every_site_destination_pair():
    sites = pd.read_csv(EX / "sites.csv")
    dests = pd.read_csv(EX / "destinations.csv")
    lanes = pd.read_csv(EX / "lanes.csv")
    assert len(lanes) == len(sites) * len(dests)
    assert set(lanes["site"]) == set(sites["site"])
    assert set(lanes["destination"]) == set(dests["destination"])
    assert (lanes["km"] >= 0).all() and (lanes["sea_days"] >= 0).all()


def test_capacity_exceeds_peak_month_but_not_by_much():
    peak = pd.read_csv(EX / "demand.csv").groupby("month")["tonnes"].sum().max()
    cap = pd.read_csv(EX / "sites.csv")["capacity_t"].sum()
    assert 1.05 < cap / peak < 1.25


def test_examples_stay_small():
    assert sum(p.stat().st_size for p in EX.iterdir()) < 100_000
