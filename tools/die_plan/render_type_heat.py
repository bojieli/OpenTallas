#!/usr/bin/env python3
"""render_type_heat.py -- per-type plan render with the die-GRT congestion heatmap (FP-CONVERGE-HEAD 11-25).

    python3 render_type_heat.py PLAN.json OUT_DIR [--types a,b]

One PNG per partition type: outline, hard cores, clock taps (labelled with their planned sink count when the plan carries one),
internal_stations / ft_slots legs (red when a hop is over the 405 um reach), and the ADV-ROUTE-DEMAND estimated routing utilisation as
a heat layer (peak printed).  Plan only, matplotlib Agg, seconds per type; report only.  summary.json lists peak util, legs > 405, taps."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_route_demand as RD  # noqa: E402

REACH = 405.0


def leg_pts(t):
    out = []
    for key in ("internal_stations", "ft_slots"):
        for e in t.get(key) or []:
            if isinstance(e, dict):
                pts = [tuple(p) for p in (e.get("regs_um") or []) if isinstance(p, (list, tuple)) and len(p) == 2]
                if len(pts) >= 2:
                    out.append(pts)
    return out


def tap_sinks(t):
    ck = t.get("clock") or {}
    out = []
    for tp in ck.get("taps") or []:
        if isinstance(tp, dict) and tp.get("xy"):
            out.append((tp["xy"][0], tp["xy"][1], tp.get("sinks") or tp.get("sink_count") or tp.get("n_sinks")))
    if not out and ck.get("tap_um"):
        out.append((ck["tap_um"][0], ck["tap_um"][1], None))
    return out


def render_type(tn, t, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    gr = RD.grid(t)
    W, H, g, nx, ny = gr["W"], gr["H"], gr["G"], gr["nx"], gr["ny"]
    sc = 9.0 / max(W, H)
    fig, ax = plt.subplots(figsize=(max(5.0, W * sc) + 1.5, max(4.0, H * sc) + 0.8), dpi=110)
    peak = 0.0
    try:
        import numpy as np
        u = np.array(gr["util"]).T
        peak = float(u.max()) if u.size else 0.0
        im = ax.imshow(u, origin="lower", extent=[0, nx * g, 0, ny * g], cmap="YlOrRd", vmin=0, vmax=max(1.0, peak), alpha=0.75, aspect="equal")
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01, label="est. routing util")
    except ImportError:
        pass
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1.2))
    for c in gr["cores"]:
        ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#5b7fa6", ec="#1f3b5c", lw=0.4, alpha=0.65))
    nlong = 0
    for pts in leg_pts(t):
        for a, b in zip(pts, pts[1:]):
            d = abs(a[0] - b[0]) + abs(a[1] - b[1])
            bad = d > REACH
            nlong += bad
            ax.plot([a[0], b[0]], [a[1], b[1]], color="red" if bad else "#555", lw=0.9 if bad else 0.3, alpha=0.9 if bad else 0.5)
    taps = tap_sinks(t)
    for x, y, n in taps:
        ax.plot(x, y, "k^", ms=3)
        if n:
            ax.annotate(str(n), (x, y), fontsize=5, color="k")
    ax.set_xlim(-5, W + 5)
    ax.set_ylim(-5, H + 5)
    # a peak of 0.00 means the demand model saw no loaded lane, not that the type is clean (FP-CONVERGE-HEAD 11-25: 20 of 27 HEAD types)
    nlegs = len(leg_pts(t))
    modelled = peak > 0.0 and nlegs > 0
    if modelled:
        ax.set_title(f"{tn}  {W:g}x{H:g} um  cores {len(gr['cores'])}  taps {len(taps)}  legs>405: {nlong}  route util peak {peak:.2f}", fontsize=8)
    else:
        ax.set_title(f"{tn}  {W:g}x{H:g} um  cores {len(gr['cores'])}  taps {len(taps)}  legs {nlegs}  NOT MODELLED (no lane load; NOT a pass)", fontsize=8, color="red")
        ax.text(0.5, 0.5, "NOT MODELLED", transform=ax.transAxes, ha="center", va="center", fontsize=18, color="red", alpha=0.35)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    return {"type": tn, "modelled": modelled, "peak_util": round(peak, 2) if modelled else None, "legs_over_405": int(nlong) if nlegs else None,
            "legs": nlegs, "taps": len(taps), "cores": len(gr["cores"])}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--types")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    Path(a.out).mkdir(parents=True, exist_ok=True)
    want = set(a.types.split(",")) if a.types else None
    rows = []
    for tn, t in sorted(raw["partition_types"].items()):
        if (want and tn not in want) or not isinstance(t, dict) or not t.get("outline_um"):
            continue
        try:
            rows.append(render_type(tn, t, str(Path(a.out) / f"{tn}.png")))
        except Exception as e:  # noqa: BLE001
            rows.append({"type": tn, "error": f"{type(e).__name__}: {str(e)[:100]}"})
    (Path(a.out) / "summary.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
