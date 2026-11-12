"""SEAM-HOP-1: render the worst N seam hops of a plan on the die plan render (render.py).

    python3 tools/die_plan/seam_hop_render.py PLAN[.gz] OUTDIR [--n 5] [--internal-first] [--pad 1500]

Writes OUTDIR/<die>_overview.png (whole die, the N hops numbered, each hop's lane drawn) and
OUTDIR/<die>_hop<k>_<lane>.png (zoom, +-pad um around the hop).  The hop is drawn magenta: last station of the source
side -> seam pin -> first station of the sink side (square = station / face register, X = seam pin)."""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import render  # noqa: E402
import schema as S  # noqa: E402
import seam_hop  # noqa: E402


def _overlay(rows, label):
    def draw(ax):
        for k, r in enumerate(rows, 1):
            xs = [r["src_xy"][0], r["pin_xy"][0], r["dst_xy"][0]]
            ys = [r["src_xy"][1], r["pin_xy"][1], r["dst_xy"][1]]
            ax.plot(xs, ys, color="magenta", lw=2.0, zorder=9)
            ax.plot(xs[::2], ys[::2], ls="", marker="s", ms=6, mfc="none", mec="magenta", zorder=10)
            ax.plot([xs[1]], [ys[1]], ls="", marker="x", ms=7, color="black", zorder=10)
            ax.annotate(f"{k}: {r['hop_um']:.0f} um", (xs[1], ys[1]), xytext=(6, 6), textcoords="offset points",
                        fontsize=7, color="magenta", weight="bold", zorder=11)
        ax.text(0.01, 0.01, label, transform=ax.transAxes, fontsize=7, zorder=12,
                bbox=dict(fc="white", ec="grey", alpha=0.85))
    return draw


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--pad", type=float, default=1500.0)
    ap.add_argument("--internal-first", action="store_true")
    a = ap.parse_args(argv)
    raw = json.loads(gzip.open(a.plan, "rt").read()) if str(a.plan).endswith(".gz") else S.load(a.plan)
    P = S.Plan(raw, Path(a.plan).resolve())
    geo_all = {lid: check.lane_geometry(P, lid) for lid in P.lanes}
    rows = sorted(seam_hop.seam_hops(P, geo_all, internal_first=a.internal_first), key=lambda r: -r["hop_um"])[:a.n]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mode = "first internal station counted (pessimistic)" if a.internal_first else "face-register model (default)"
    label = f"{P.name}: worst {len(rows)} seam hops, {mode}; limit {seam_hop.S.SIGNAL_REACH_UM:g} um"
    geo = {r["lane"]: geo_all[r["lane"]] for r in rows}
    render.render(P, geo, None, out / f"{P.name}_overview.png", title=label, extra=_overlay(rows, label))
    for k, r in enumerate(rows, 1):
        xs = [r["src_xy"][0], r["pin_xy"][0], r["dst_xy"][0]]
        ys = [r["src_xy"][1], r["pin_xy"][1], r["dst_xy"][1]]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half = max(a.pad, (max(xs) - min(xs)) / 2 + 300, (max(ys) - min(ys)) / 2 + 300)
        lab = f"hop {k}: lane {r['lane']}  {r['src']} -> {r['dst']}  {r['hop_um']:.0f} um (legs {r['src_leg_um']:.0f} + {r['dst_leg_um']:.0f})"
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", r["lane"])
        render.render(P, geo, None, out / f"{P.name}_hop{k}_{name}.png", title=lab, extra=_overlay([dict(r, hop_um=r["hop_um"])], lab),
                      view=((cx - half, cx + half), (cy - half, cy + half)))
    for r in rows:
        print(f"{r['hop_um']:8.1f} um  {r['lane']}  {r['src']} -> {r['dst']}  bus {r['bus']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
