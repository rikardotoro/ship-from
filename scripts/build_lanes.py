"""Compute sea distance and sailing days for every site x destination lane.

Uses the open `searoute` package (Apache-2.0) on the committed coordinates;
run with `uvx --with searoute python scripts/build_lanes.py`. Output is committed
so the tool itself needs no network and no routing dependency.
"""
from pathlib import Path

import pandas as pd
import searoute as sr

EX = Path(__file__).parent.parent / "src" / "ship_from" / "examples"


def main() -> None:
    sites = pd.read_csv(EX / "sites.csv")
    dests = pd.read_csv(EX / "destinations.csv")
    rows = []
    for s in sites.itertuples():
        for d in dests.itertuples():
            if abs(s.lat - d.lat) < 0.01 and abs(s.lon - d.lon) < 0.01:
                km, days = 0.0, 0.0
            else:
                r = sr.searoute([s.lon, s.lat], [d.lon, d.lat], units="km")
                km = r["properties"]["length"]
                days = r["properties"]["duration_hours"] / 24
            rows.append((s.site, d.destination, round(km), round(days, 1)))
    out = pd.DataFrame(rows, columns=["site", "destination", "km", "sea_days"])
    out.to_csv(EX / "lanes.csv", index=False)
    print(f"{len(out)} lanes; km {out.km.min()}–{out.km.max()}; days {out.sea_days.min()}–{out.sea_days.max()}")


if __name__ == "__main__":
    main()
