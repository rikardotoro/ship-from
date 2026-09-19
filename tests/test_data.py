from pathlib import Path

import pytest

from ship_from.data import EXAMPLES, load_network
from ship_from.errors import InvalidDataError, MissingColumnError


def test_load_network_from_examples():
    net = load_network(EXAMPLES)
    assert list(net.sites.index) == ["Rotterdam", "Savannah", "Santos", "Singapore"]
    assert net.lanes.shape == (4, 20)  # km matrix: sites x destinations
    assert net.demand.shape[1] == 20
    assert net.demand_for("2016-07").sum() == 11652


def test_aliases_are_accepted(tmp_path: Path):
    _copy(tmp_path)
    (tmp_path / "sites.csv").write_text(
        "plant,latitude,longitude,capacity,handling\nRotterdam,51.95,4.14,4400,22\n")
    (tmp_path / "lanes.csv").write_text("site,destination,distance_km,days\nRotterdam,France,432,0.4\n")
    (tmp_path / "destinations.csv").write_text("destination,port,lat,lon\nFrance,Le Havre,49.48,0.11\n")
    (tmp_path / "demand.csv").write_text("month,country,qty\n2016-07,France,100\n")
    net = load_network(tmp_path)
    assert net.lanes.loc["Rotterdam", "France"] == 432
    assert net.demand_for("2016-07")["France"] == 100


def test_missing_column_names_the_file(tmp_path: Path):
    _copy(tmp_path)
    (tmp_path / "sites.csv").write_text("site,lat,lon\nRotterdam,51.95,4.14\n")
    with pytest.raises(MissingColumnError, match="sites.csv.*capacity"):
        load_network(tmp_path)


def test_negative_capacity_is_reported_with_row(tmp_path: Path):
    _copy(tmp_path)
    text = (tmp_path / "sites.csv").read_text().replace("Santos,-23.96,-46.30,2400,30", "Santos,-23.96,-46.30,-1,30")
    (tmp_path / "sites.csv").write_text(text)
    with pytest.raises(InvalidDataError, match="row 4"):
        load_network(tmp_path)


def test_missing_lane_is_refused(tmp_path: Path):
    _copy(tmp_path)
    lines = (tmp_path / "lanes.csv").read_text().splitlines()
    (tmp_path / "lanes.csv").write_text("\n".join(lines[:-1]) + "\n")
    with pytest.raises(InvalidDataError, match="lane"):
        load_network(tmp_path)


def _copy(tmp_path: Path) -> None:
    for name in ("sites.csv", "destinations.csv", "demand.csv", "lanes.csv"):
        (tmp_path / name).write_text((EXAMPLES / name).read_text())
