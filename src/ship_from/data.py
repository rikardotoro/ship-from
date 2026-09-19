"""Load the four network files with column aliases and row-numbered errors."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ship_from.errors import InvalidDataError, MissingColumnError

EXAMPLES = Path(__file__).parent / "examples"

ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "sites.csv": {
        "site": ("site", "plant", "origin", "warehouse", "source", "name"),
        "lat": ("lat", "latitude"),
        "lon": ("lon", "lng", "longitude"),
        "capacity_t": ("capacity_t", "capacity", "capacity_tonnes", "supply"),
        "handling_per_t": ("handling_per_t", "handling", "handling_cost", "port_cost"),
    },
    "destinations.csv": {
        "destination": ("destination", "country", "market", "customer", "name"),
        "lat": ("lat", "latitude"),
        "lon": ("lon", "lng", "longitude"),
    },
    "demand.csv": {
        "month": ("month", "period", "date"),
        "destination": ("destination", "country", "market", "customer"),
        "tonnes": ("tonnes", "qty", "quantity", "demand", "volume", "t"),
    },
    "lanes.csv": {
        "site": ("site", "plant", "origin", "warehouse", "source"),
        "destination": ("destination", "country", "market", "customer"),
        "km": ("km", "distance_km", "distance", "nm"),
        "sea_days": ("sea_days", "days", "transit_days", "sailing_days"),
    },
}


@dataclass(frozen=True)
class Network:
    sites: pd.DataFrame        # index site: lat, lon, capacity_t, handling_per_t
    destinations: pd.DataFrame # index destination: lat, lon
    demand: pd.DataFrame       # index month (str "YYYY-MM"), columns destinations, tonnes
    lanes: pd.DataFrame        # km matrix, index sites, columns destinations
    sea_days: pd.DataFrame     # sailing days matrix, same shape

    def demand_for(self, month: str) -> pd.Series:
        if month not in self.demand.index:
            raise InvalidDataError(f"no demand for month {month}; months run {self.demand.index[0]} to {self.demand.index[-1]}")
        return self.demand.loc[month]

    @property
    def months(self) -> list[str]:
        return list(self.demand.index)


def _read(folder: Path, name: str) -> pd.DataFrame:
    path = folder / name
    if not path.exists():
        raise MissingColumnError(f"{name} not found in {folder}")
    df = pd.read_csv(path)
    lower = {c.lower().strip(): c for c in df.columns}
    out = {}
    for canonical, options in ALIASES[name].items():
        found = next((lower[o] for o in options if o in lower), None)
        if found is None:
            raise MissingColumnError(f"{name}: no column for '{canonical}' (accepted: {', '.join(options)})")
        out[canonical] = df[found]
    return pd.DataFrame(out)


def _check_nonnegative(df: pd.DataFrame, col: str, name: str) -> None:
    bad = df.index[pd.to_numeric(df[col], errors="coerce").isna() | (pd.to_numeric(df[col], errors="coerce") < 0)]
    if len(bad):
        i = int(bad[0])
        raise InvalidDataError(f"{name} row {i + 2}: {col} = {df[col].iloc[i]!r} must be a number >= 0")


def load_network(folder: Path | str = EXAMPLES) -> Network:
    folder = Path(folder)
    sites = _read(folder, "sites.csv")
    dests = _read(folder, "destinations.csv")
    demand = _read(folder, "demand.csv")
    lanes = _read(folder, "lanes.csv")
    for col in ("capacity_t", "handling_per_t"):
        _check_nonnegative(sites, col, "sites.csv")
    _check_nonnegative(demand, "tonnes", "demand.csv")
    for col in ("km", "sea_days"):
        _check_nonnegative(lanes, col, "lanes.csv")
    for col in ("capacity_t", "handling_per_t"):
        sites[col] = pd.to_numeric(sites[col])
    demand["tonnes"] = pd.to_numeric(demand["tonnes"])
    lanes["km"] = pd.to_numeric(lanes["km"]); lanes["sea_days"] = pd.to_numeric(lanes["sea_days"])
    demand["month"] = pd.to_datetime(demand["month"]).dt.to_period("M").astype(str)
    if sites["site"].duplicated().any():
        raise InvalidDataError("sites.csv: duplicate site names")
    sites = sites.set_index("site")
    dests = dests.drop_duplicates("destination").set_index("destination")
    unknown = set(demand["destination"]) - set(dests.index)
    if unknown:
        raise InvalidDataError(f"demand.csv names destinations missing from destinations.csv: {sorted(unknown)}")
    dmat = (demand.groupby(["month", "destination"])["tonnes"].sum().unstack("destination")
                  .reindex(columns=dests.index).fillna(0.0).sort_index())
    km = lanes.pivot_table(index="site", columns="destination", values="km", aggfunc="first")
    days = lanes.pivot_table(index="site", columns="destination", values="sea_days", aggfunc="first")
    km = km.reindex(index=sites.index, columns=dests.index)
    days = days.reindex(index=sites.index, columns=dests.index)
    if km.isna().any().any():
        s, d = next((s, d) for s in km.index for d in km.columns if pd.isna(km.loc[s, d]))
        raise InvalidDataError(f"lanes.csv: no lane for {s} -> {d}; every site x destination pair needs one")
    return Network(sites, dests, dmat, km, days)
