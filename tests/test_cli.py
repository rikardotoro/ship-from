import json
import re

from typer.testing import CliRunner

from ship_from.cli import app

runner = CliRunner()


def test_demo_runs_and_states_the_gap():
    r = runner.invoke(app, ["--demo"])
    assert r.exit_code == 0, r.output
    assert "2017-07" in r.output and "linear program" in r.output
    assert re.search(r"1\d\.\d% less", r.output)


def test_json_has_the_card_numbers():
    r = runner.invoke(app, ["--demo", "--json"])
    d = json.loads(r.output)
    assert 0.10 < d["gap_pct"] < 0.20
    assert d["shadow_price"]["Savannah"] > 0 and d["shadow_price"]["Singapore"] == 0
    assert len(d["months"]) == 12 and d["extra_capacity"]["site"] == "Savannah"


def test_outage_in_peak_month_is_reported_not_crashed():
    r = runner.invoke(app, ["--demo", "--outage", "Singapore"])
    assert r.exit_code == 0 and "short by" in r.output


def test_outage_in_slack_month_gives_a_cost():
    r = runner.invoke(app, ["--demo", "--month", "2017-03", "--outage", "Santos"])
    assert r.exit_code == 0 and "still feasible" in r.output


def test_negative_value_is_refused_with_the_joke():
    r = runner.invoke(app, ["--demo", "--value", "-1"])
    assert r.exit_code == 1 and "pay you" in " ".join(r.output.split())


def test_missing_data_folder_is_refused():
    r = runner.invoke(app, ["--data", "/nonexistent", "--month", "2017-01"])
    assert r.exit_code == 1 and "sites.csv" in r.output
