"""Build examples/demand.csv from the DataCo Smart Supply Chain dataset (CC0).

One order-line unit is taken as one tonne (a disclosed scaling, see SOURCE.md).
The source serves one world region at a time (its months rotate through regions),
so a raw calendar month has no country mix. The demo therefore uses twelve
calendar months where each destination's share is its three-year share and the
monthly total is the mean of that calendar month over 2015-2017.
"""
import sys
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/DataCoSupplyChainDataset.csv")
OUT = Path(__file__).parent.parent / "src" / "ship_from" / "examples" / "demand.csv"
COUNTRY = {  # dataset names (Spanish) -> English
    "Estados Unidos": "United States", "México": "Mexico", "Francia": "France", "Alemania": "Germany",
    "Brasil": "Brazil", "Australia": "Australia", "Reino Unido": "United Kingdom", "China": "China",
    "Italia": "Italy", "India": "India", "Indonesia": "Indonesia", "España": "Spain",
    "Turquía": "Turkey", "Nigeria": "Nigeria", "Argentina": "Argentina", "Filipinas": "Philippines",
    "Países Bajos": "Netherlands", "Colombia": "Colombia", "Japón": "Japan", "Corea del Sur": "South Korea",
}


def main() -> None:
    cols = ["Order Country", "Order Item Quantity", "order date (DateOrders)"]
    df = pd.read_csv(RAW, encoding="latin1", usecols=cols)
    df = df[df["Order Country"].isin(COUNTRY)]
    df["destination"] = df["Order Country"].map(COUNTRY)
    df["date"] = pd.to_datetime(df["order date (DateOrders)"])
    df = df[df["date"] < "2018-01-01"]  # January 2018 is a partial month in the source
    share = df.groupby("destination")["Order Item Quantity"].sum()
    share = share / share.sum()
    by_month = df.groupby([df["date"].dt.year, df["date"].dt.month])["Order Item Quantity"].sum()
    total = by_month.groupby(level=1).mean()  # calendar-month mean over the three years
    rows = [(f"2017-{m:02d}", d, int(round(total[m] * share[d]))) for m in range(1, 13) for d in share.index]
    out = pd.DataFrame(rows, columns=["month", "destination", "tonnes"])
    out.sort_values(["month", "destination"]).to_csv(OUT, index=False)
    print(f"{OUT}: {out['month'].nunique()} months, {out['destination'].nunique()} destinations, "
          f"peak {out.groupby('month')['tonnes'].sum().max():,} t")


if __name__ == "__main__":
    main()
