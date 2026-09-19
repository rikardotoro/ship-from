"""Regenerate the README charts from the committed data so they can never drift.

Hand-rolled SVG, light and dark variants. Blue = the nearest-site rule (what
gets done), orange = the linear program (what it should be).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ship_from.cost import CostParams, lane_breakdown
from ship_from.data import EXAMPLES, load_network
from ship_from.report import DEMO_MONTH, analyse

ROOT = Path(__file__).parent.parent
OUT = ROOT / "docs" / "charts"
FONT = "system-ui, -apple-system, Segoe UI, sans-serif"
TOKENS = {
    "light": {"rule": "#2a78d6", "plan": "#eb6834", "ink": "#0b0b0b", "ink2": "#52514e",
              "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7", "neutral": "#b8b6ad",
              "band": "#fbe3d9", "rule_soft": "#cfe0f6"},
    "dark": {"rule": "#3987e5", "plan": "#d95926", "ink": "#ffffff", "ink2": "#c3c2b7",
             "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835", "neutral": "#4a4945",
             "band": "#3d2a22", "rule_soft": "#243a55"},
}


def _text(x, y, s, size, fill, anchor="start", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')


def _line(x1, y1, x2, y2, stroke, width=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>')


def _path(points, color, width=2.0, dash=None):
    d = " L ".join(f"{x:.1f} {y:.1f}" for x, y in points)
    dd = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="M {d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linejoin="round"{dd}/>')


def _rect(x, y, w, h, fill, opacity=1.0, rx=0):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" '
            f'opacity="{opacity}" rx="{rx}"/>')


def _circle(x, y, r, fill):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>'


def _svg(width, height, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">\n' + "\n".join(body) + "\n</svg>\n")


# ------------------------------------------------------------- chart 1: gap by month
def chart_months(r, mode):
    T = TOKENS[mode]
    W, H = 760, 420
    L, R, top, h = 56, 76, 84, 220
    months = r.months
    n = len(months)
    x = lambda i: L + (i + 0.5) * (W - L - R) / n
    bw = (W - L - R) / n * 0.6
    peak = months["gap_pct"].max()
    body = [_text(L, 24, "The nearest-site rule is free until capacity runs out", 15, T["ink"], weight="bold"),
            _text(L, 44, "Bars: how much more the nearest-site plan costs than the linear program, month by month.", 11, T["muted"]),
            _text(L, 60, "Line: that month's demand as a share of total capacity.", 11, T["muted"])]
    ymax = 0.15
    y = lambda v: top + h - min(v, ymax) / ymax * h
    for v in (0, 0.05, 0.10, 0.15):
        body.append(_line(L, y(v), W - R, y(v), T["grid"]))
        body.append(_text(L - 8, y(v) + 4, f"{v:.0%}", 10, T["muted"], anchor="end"))
    yu = lambda u: top + h - u * h  # utilisation 0..1 on the same height
    for i, (m, row) in enumerate(months.iterrows()):
        g = max(row["gap_pct"], 0)
        if g > 0.0005:
            body.append(_rect(x(i) - bw / 2, y(g), bw, y(0) - y(g), T["plan"]))
            if g >= 0.05:
                body.append(_text(x(i), y(g) + 16, f"{g:.1%}", 11, "#ffffff", anchor="middle", weight="bold"))
            else:
                body.append(_text(x(i), y(g) - 6, f"{g:.1%}", 11, T["plan"], anchor="middle", weight="bold"))
        else:
            body.append(_rect(x(i) - bw / 2, y(0) - 2, bw, 2, T["neutral"]))
        body.append(_text(x(i), top + h + 16, m[5:], 10, T["muted"], anchor="middle"))
    body.append(_path([(x(i), yu(u)) for i, u in enumerate(months["utilisation"])], T["rule"], 2.2))
    for i, u in enumerate(months["utilisation"]):
        body.append(_circle(x(i), yu(u), 3, T["rule"]))
    for u in (0.5, 1.0):
        body.append(_text(W - R + 6, yu(u) + 4, f"{u:.0%}", 10, T["rule"], anchor="start"))
    body.append(_text(W - R + 6, yu(0.75) + 4, "of capacity", 9, T["rule"], anchor="start"))
    i_peak = list(months.index).index(DEMO_MONTH)
    body.append(_text(x(i_peak) - bw / 2 - 8, y(peak) + 24, f"peak month: ${r.gap:,.0f} more", 11, T["ink2"], anchor="end"))
    body.append(_text(L, H - 32, "month of the demo year", 10, T["muted"]))
    lx, ly = L, H - 12
    body.append(_rect(lx, ly - 9, 12, 10, T["plan"]))
    body.append(_text(lx + 18, ly, "extra cost of the nearest-site rule", 11, T["ink2"]))
    body.append(_line(lx + 230, ly - 4, lx + 256, ly - 4, T["rule"], 2.2))
    body.append(_text(lx + 262, ly, "demand ÷ capacity", 11, T["ink2"]))
    return _svg(W, H, body)


# ------------------------------------------------------------- chart 2: what moves
def chart_moves(r, mode):
    T = TOKENS[mode]
    rows = []
    for d in r.moved.columns:
        rule_site = r.rule.allocation[d].idxmax()
        plan_site = r.plan.allocation[d].idxmax()
        gained = r.moved[d][r.moved[d] > 0.5]
        lost = r.moved[d][r.moved[d] < -0.5]
        if gained.empty or lost.empty:
            continue
        to, frm = gained.idxmax(), lost.idxmin()
        t = float(gained.max())
        rows.append((d, frm, to, t, float(r.costs.loc[frm, d]), float(r.costs.loc[to, d])))
    rows.sort(key=lambda z: -(z[4] - z[5]) * z[3])
    W = 760
    rowh = 34
    top = 92
    H = top + rowh * len(rows) + 70
    L, R = 150, 200
    xmax = max(max(a, b) for *_, a, b in rows) * 1.08
    x = lambda v: L + v / xmax * (W - L - R)
    body = [_text(24, 24, "Where the rule sends cargo the long way round", 15, T["ink"], weight="bold"),
            _text(24, 44, f"{r.month}: the lanes that differ between the two plans, landed cost in $ per tonne.", 11, T["muted"]),
            _text(24, 60, "Blue dot = the site the nearest rule ends up using; orange = the site the linear program picks.", 11, T["muted"])]
    for v in np.arange(0, xmax, 100):
        body.append(_line(x(v), top - 10, x(v), top + rowh * len(rows), T["grid"]))
        body.append(_text(x(v), top + rowh * len(rows) + 14, f"${v:.0f}", 10, T["muted"], anchor="middle"))
    for i, (d, frm, to, t, c_rule, c_plan) in enumerate(rows):
        yy = top + i * rowh + rowh / 2
        body.append(_text(L - 10, yy + 4, d, 12, T["ink"], anchor="end"))
        body.append(_line(x(min(c_rule, c_plan)), yy, x(max(c_rule, c_plan)), yy, T["axis"], 2))
        body.append(_circle(x(c_rule), yy, 6, T["rule"]))
        body.append(_circle(x(c_plan), yy, 6, T["plan"]))
        hi, lo = max(c_rule, c_plan), min(c_rule, c_plan)
        label_from = f"{frm} → {to}" if c_plan < c_rule else f"{frm} → {to}"
        body.append(_text(x(hi) + 10, yy + 4, f"{label_from}, {t:,.0f} t", 10, T["ink2"]))
    body.append(_text(24, H - 34, "The rule fills the nearest site with its biggest customer first; the small ones "
                      "left over sail from wherever still has room.", 11, T["ink2"]))
    body.append(_text(24, H - 16, "Some lanes get dearer on purpose: a tonne moved off a full site frees room for a "
                      "tonne that saves more.", 11, T["ink2"]))
    return _svg(W, H, body)


# ------------------------------------------------------------- chart 3: shadow prices
def chart_shadow(r, mode):
    T = TOKENS[mode]
    W, H = 760, 320
    L, R, top, h = 56, 24, 70, 150
    sites = list(r.net.sites.index)
    cap = r.net.sites["capacity_t"]
    util = r.plan.utilisation(cap)
    sp = r.plan.shadow_price
    n = len(sites)
    x = lambda i: L + (i + 0.5) * (W - L - R) / n
    bw = (W - L - R) / n * 0.28
    ymax = max(float(np.ceil(sp.max() * 1.25 / 20) * 20), 20)
    y = lambda v: top + h - v / ymax * h
    body = [_text(L, 24, "What one more tonne of capacity is worth, site by site", 15, T["ink"], weight="bold"),
            _text(L, 44, f"{r.month}: the shadow price from the linear program's dual, $ per tonne per month. "
                  "Grey bar: share of capacity used.", 11, T["muted"])]
    for v in np.arange(0, ymax + 1, 20):
        body.append(_line(L, y(v), W - R, y(v), T["grid"]))
        body.append(_text(L - 8, y(v) + 4, f"${v:.0f}", 10, T["muted"], anchor="end"))
    for i, s in enumerate(sites):
        body.append(_rect(x(i) - bw - 4, top + h - util[s] * h, bw, util[s] * h, T["neutral"]))
        body.append(_text(x(i) - bw / 2 - 4, top + h - util[s] * h - 5, f"{util[s]:.0%} used", 10, T["muted"], anchor="middle"))
        v = sp[s]
        if v > 0.5:
            body.append(_rect(x(i) + 4, y(v), bw, y(0) - y(v), T["plan"]))
            body.append(_text(x(i) + 4 + bw / 2, y(v) - 6, f"${v:.0f}/t", 11, T["plan"], anchor="middle", weight="bold"))
        else:
            body.append(_rect(x(i) + 4, y(0) - 2, bw, 2, T["plan"]))
            body.append(_text(x(i) + 4 + bw / 2, y(0) - 8, "$0: slack", 11, T["muted"], anchor="middle"))
        body.append(_text(x(i), top + h + 18, f"{s}  ({cap[s]:,.0f} t)", 11, T["ink"], anchor="middle"))
    e = r.extra
    body.append(_text(L, H - 30, f"Check: +{e.tonnes:,.0f} t at {e.site}, re-solved, saves ${e.gain:,.0f} this month; "
                      f"the shadow price predicted ${e.shadow_estimate:,.0f}.", 11, T["ink2"]))
    body.append(_text(L, H - 12, "Adding capacity at a slack site saves nothing, however cheap it is to ship from.", 11, T["ink2"]))
    return _svg(W, H, body)


# ------------------------------------------------------------- chart 4: cash at sea
def chart_cash(r, mode):
    T = TOKENS[mode]
    W, H = 760, 300
    L, R, top, h = 56, 24, 70, 150
    values = [2_000, 5_000, 10_000, 20_000, 50_000, 100_000]
    net = r.net
    stacks = []
    for v in values:
        p = CostParams(value=v, capital_rate=r.params.capital_rate, freight_per_t_km=r.params.freight_per_t_km,
                       port_days=r.params.port_days)
        parts = lane_breakdown(net, p)
        alloc = r.plan.allocation  # hold the plan fixed: same tonnes, same lanes
        t = alloc.to_numpy().sum()
        stacks.append({k: float((alloc * m).to_numpy().sum() / t) for k, m in parts.items()})
    n = len(values)
    x = lambda i: L + (i + 0.5) * (W - L - R) / n
    bw = (W - L - R) / n * 0.55
    ymax = float(np.ceil(max(sum(s.values()) for s in stacks) * 1.15 / 100) * 100)
    y = lambda v: top + h - v / ymax * h
    body = [_text(L, 24, "For dear goods, the days at sea cost more than the freight", 15, T["ink"], weight="bold"),
            _text(L, 44, f"Landed cost per tonne of the {r.month} plan as the goods' value changes, "
                  f"{r.params.capital_rate:.0%} cost of capital. Lanes and tonnes held fixed.", 11, T["muted"])]
    for v in np.arange(0, ymax + 1, 100):
        body.append(_line(L, y(v), W - R, y(v), T["grid"]))
        body.append(_text(L - 8, y(v) + 4, f"${v:.0f}", 10, T["muted"], anchor="end"))
    for i, (v, s) in enumerate(zip(values, stacks)):
        base = 0.0
        for key, col in (("handling", T["neutral"]), ("freight", T["rule"]), ("cash_at_sea", T["plan"])):
            body.append(_rect(x(i) - bw / 2, y(base + s[key]), bw, y(base) - y(base + s[key]), col))
            base += s[key]
        share = s["cash_at_sea"] / base
        body.append(_text(x(i), y(base) - 6, f"{share:.0%} at sea", 10, T["plan"], anchor="middle", weight="bold"))
        body.append(_text(x(i), top + h + 16, f"${v:,.0f}/t", 11, T["ink"], anchor="middle"))
    lx, ly = L, H - 12
    for key, col, label in (("handling", T["neutral"], "port handling"), ("freight", T["rule"], "freight"),
                            ("cash_at_sea", T["plan"], "cash tied up in transit")):
        body.append(_rect(lx, ly - 9, 12, 10, col))
        body.append(_text(lx + 18, ly, label, 11, T["ink2"]))
        lx += 130 if key != "freight" else 80
    return _svg(W, H, body)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    net = load_network(EXAMPLES)
    r = analyse(net, DEMO_MONTH)
    for mode in ("light", "dark"):
        (OUT / f"months-{mode}.svg").write_text(chart_months(r, mode))
        (OUT / f"moves-{mode}.svg").write_text(chart_moves(r, mode))
        (OUT / f"shadow-{mode}.svg").write_text(chart_shadow(r, mode))
        (OUT / f"cash-{mode}.svg").write_text(chart_cash(r, mode))
    print("charts written")


if __name__ == "__main__":
    main()
