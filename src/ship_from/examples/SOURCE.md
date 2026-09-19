# Where the demo data comes from

**demand.csv** — DataCo Smart Supply Chain dataset (Kaggle, CC0 public domain).
The twenty largest destination countries by order-line quantity, January
2015 to December 2017 (January 2018 is a partial month and is dropped). The
source serves one world region at a time, rotating every few months, so a
raw calendar month contains a single region and no country mix. The demo
therefore has twelve months: each destination's tonnes are its three-year
share of the total times the mean volume of that calendar month across the
three years. One order-line unit is taken as **one tonne**; that scaling is
invented so totals land in a plausible range for a four-site network. The
country mix and the month-to-month totals are the dataset's own. Rebuild with
`scripts/make_demand.py <path to DataCoSupplyChainDataset.csv>`.

**sites.csv** — four fictional plants at real port coordinates (Rotterdam,
Savannah, Santos, Singapore). Capacities and handling costs are invented
and sized so total capacity sits about 11% above the peak demand month.

**destinations.csv** — each demand country mapped to one major container
port, coordinates rounded to two decimals.

**lanes.csv** — sea distance and sailing days for every site × destination
pair from the open `searoute` package (Apache-2.0), computed once by
`scripts/build_lanes.py` and committed. Sailing days assume the package's
default speed; port days are a separate parameter of the tool.

No real company, product or industry is represented.
