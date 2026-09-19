import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ship_from.cost import CostParams
from ship_from.data import EXAMPLES, load_network
from ship_from.errors import ShipFromError
from ship_from.report import DEMO_MONTH, EXTRA_TONNES, analyse, render, to_dict

app = typer.Typer(add_completion=False,
                  help="A monthly shipping plan as a linear program: cheaper than the nearest-site rule, "
                       "and it tells you what a tonne of capacity is worth.")
console = Console(soft_wrap=True, width=110)


@app.command()
def main(
    data: Annotated[Path | None, typer.Option(help="Folder with sites.csv, destinations.csv, demand.csv, lanes.csv.")] = None,
    demo: Annotated[bool, typer.Option(help="Use the bundled four-site network.")] = False,
    month: Annotated[str | None, typer.Option(help="Month to plan, YYYY-MM (default: the peak month in the demo).")] = None,
    value: Annotated[float, typer.Option(help="Goods value, $ per tonne.")] = 20_000.0,
    capital_rate: Annotated[float, typer.Option(help="Annual cost of capital, e.g. 0.12.")] = 0.12,
    freight: Annotated[float, typer.Option(help="Freight, $ per tonne-km.")] = 0.012,
    port_days: Annotated[float, typer.Option(help="Days in port, both ends together.")] = 4.0,
    extra: Annotated[str | None, typer.Option(help="What-if: SITE=TONNES extra capacity (default: 500 t at the highest shadow price).")] = None,
    outage: Annotated[str | None, typer.Option(help="What-if: this site ships nothing this month.")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    if demo:
        data = data or EXAMPLES
        month = month or DEMO_MONTH
    if data is None:
        raise typer.BadParameter("provide --data FOLDER or --demo")
    if month is None:
        raise typer.BadParameter("provide --month YYYY-MM")
    extra_site, extra_t = None, EXTRA_TONNES
    if extra:
        extra_site, _, t = extra.partition("=")
        extra_t = float(t) if t else EXTRA_TONNES
    try:
        net = load_network(data)
        params = CostParams(value=value, capital_rate=capital_rate, freight_per_t_km=freight, port_days=port_days)
        result = analyse(net, month, params, extra_site=extra_site, extra_tonnes=extra_t, outage_site=outage)
    except (ShipFromError, ValueError, KeyError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error
    if as_json:
        print(json.dumps(to_dict(result), indent=2))
    else:
        render(result, console)


if __name__ == "__main__":
    app()
