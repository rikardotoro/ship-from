"""Build examples/demand.csv from the DataCo Smart Supply Chain dataset (CC0).

One order-line unit is taken as one tonne (a disclosed scaling, see SOURCE.md).
Top destination countries by volume, monthly totals, full months only.
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
    df["month"] = pd.to_datetime(df["order date (DateOrders)"]).dt.to_period("M").astype(str)
    out = (df.groupby(["month", "destination"])["Order Item Quantity"].sum()
             .rename("tonnes").reset_index())
    out = out[out["month"] < "2018-01"]  # January 2018 is a partial month in the source
    out.sort_values(["month", "destination"]).to_csv(OUT, index=False)
    print(f"{OUT}: {out['month'].nunique()} months, {out['destination'].nunique()} destinations")


if __name__ == "__main__":
    main()
