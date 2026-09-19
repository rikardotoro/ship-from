# Where the demo data comes from

**demand.csv** — DataCo Smart Supply Chain dataset (Kaggle, CC0 public domain).
Order-line quantities summed by destination country and calendar month,
January 2015 to December 2017 (January 2018 is a partial month in the source
and is dropped). The twenty largest destination countries are kept. One
order-line unit is taken as **one tonne**; that scaling is invented so the
totals land in a plausible monthly range for a four-site network. The
seasonality and the country mix are the dataset's own. Rebuild with
`scripts/make_demand.py <path to DataCoSupplyChainDataset.csv>`.

**sites.csv** — four fictional plants at real port coordinates (Rotterdam,
Savannah, Santos, Singapore). Capacities and handling costs are invented
and sized so total capacity sits about 13% above the peak demand month.

**destinations.csv** — each demand country mapped to one major container
port, coordinates rounded to two decimals.

**lanes.csv** — sea distance and sailing days for every site × destination
pair from the open `searoute` package (Apache-2.0), computed once by
`scripts/build_lanes.py` and committed. Sailing days assume the package's
default speed; port days are a separate parameter of the tool.

No real company, product or industry is represented.
