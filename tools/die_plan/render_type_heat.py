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


def _face_point(t, face, win):
    W, H = t["outline_um"]
    lo, hi = (win or [0.0, H if face in ("W", "E") else W])[:2]
    m = (lo + hi) / 2.0
    return {"W": (0.0, m), "E": (W, m), "S": (m, 0.0), "N": (m, H)}.get(face, (0.0, m))


def chain_legs(t):
    """DETAIL-1 (HEAD-SMALL-TAPS 11-25): [(name, [pts], [hop um])] for every ft slot / internal station, including slots that
    carry no regs_um (pass-through shims, st_*, turn_*): in-window mid -> `stations` evenly spaced points on the Manhattan
    route -> out-window mid, the way the kit places them (reach_fix.ft_slot_hops 'even')."""
    out = []
    for f in t.get("ft_slots") or []:
        if not isinstance(f, dict):
            continue
        a = _face_point(t, f.get("in_face", "W"), f.get("in_window_um"))
        b = _face_point(t, f.get("out_face", "E"), f.get("out_window_um"))
        k = max(1, int(f.get("stations", 1) or 1))
        regs = [tuple(r[:2]) for r in f.get("regs_um") or [] if isinstance(r, (list, tuple)) and len(r) >= 2]
        if len(regs) >= k:
            pts = [a] + regs + [b]
        else:
            # z-route: along the in axis to the mid, across, then along the out axis (L = Manhattan |dx|+|dy|)
            mid = ((a[0] + b[0]) / 2.0, a[1]) if f.get("in_face", "W") in ("W", "E") else (a[0], (a[1] + b[1]) / 2.0)
            corner = [a, mid, (mid[0], b[1]) if f.get("in_face", "W") in ("W", "E") else (b[0], mid[1]), b]
            seg = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(corner, corner[1:])]
            L = sum(seg)
            pts = [a]
            for j in range(1, k):
                want = L * j / k
                acc = 0.0
                for (p, q), sl in zip(zip(corner, corner[1:]), seg):
                    if acc + sl >= want - 1e-9 and sl > 0:
                        r = (want - acc) / sl
                        pts.append((p[0] + (q[0] - p[0]) * r, p[1] + (q[1] - p[1]) * r))
                        break
                    acc += sl
            pts.append(b)
        hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]
        out.append((str(f.get("name")), pts, hops))
    for s in t.get("internal_stations") or []:
        if isinstance(s, dict) and s.get("from_um") and s.get("to_um"):
            pts = [tuple(s["from_um"][:2])] + [tuple(r[:2]) for r in s.get("regs_um") or []] + [tuple(s["to_um"][:2])]
            out.append((str(s.get("conn", "st")), pts, [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]))
    return out


def pin_pts(t):
    """[(name, dir, x, y)] landing-contract pins of the type"""
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    return [(p.get("name"), p.get("dir"), p["xy_um"][0], p["xy_um"][1]) for p in lc.get("pins") or [] if isinstance(p, dict) and p.get("xy_um")]


def exported_taps(plan_path, tn, repo=None):
    """the kit's exported tap grid (schema.tap_grid) of type tn; [] when the plan side files do not resolve"""
    try:
        import reach_fix as RF
        RF.set_repo(repo)
        raw, _sha = RF.load_raw(plan_path)
        P = RF.plan_obj(raw, plan_path)
        import schema as S
        return [(n, x, y) for n, x, y in S.tap_grid(P, tn)]
    except Exception:  # noqa: BLE001
        return []


def render_type(tn, t, out_png, grid_taps=None, radius=200.0):
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
    # DETAIL-1: exported grid taps with their reach circle, pins, stations, labelled legs (red > 405, orange > 300)
    from matplotlib.patches import Circle
    for n, x, y in grid_taps or []:
        ax.plot(x, y, "m^", ms=4)
        ax.add_patch(Circle((x, y), radius, fill=False, ec="m", lw=0.4, ls="--", alpha=0.5))
    for pn, pd, x, y in pin_pts(t):
        ax.plot(x, y, "s", color="tab:blue" if pd == "in" else "tab:green", ms=2.5)
    dlegs = chain_legs(t)
    dmax = 0.0
    dover = 0
    for nm, pts, hops in dlegs:
        for (a, b), d in zip(zip(pts, pts[1:]), hops):
            dmax = max(dmax, d)
            col = "red" if d > REACH else ("darkorange" if d > 300.0 else "tab:purple")
            dover += d > REACH
            ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=0.8, alpha=0.8)
            ax.annotate("%d" % d, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), fontsize=4, color=col)
        for p in pts[1:-1]:
            ax.plot(p[0], p[1], "o", color="k", ms=2)
    ax.set_xlim(-5, W + 5)
    ax.set_ylim(-5, H + 5)
    # a peak of 0.00 means the demand model saw no loaded lane, not that the type is clean (FP-CONVERGE-HEAD 11-25: 20 of 27 HEAD types)
    nlegs = len(leg_pts(t))
    modelled = peak > 0.0 and nlegs > 0
    drawn = bool(dlegs or pin_pts(t) or grid_taps)
    if modelled:
        ax.set_title(f"{tn}  {W:g}x{H:g} um  cores {len(gr['cores'])}  taps {len(taps)}  legs>405: {nlong}  route util peak {peak:.2f}", fontsize=8)
    else:
        ax.set_title(f"{tn}  {W:g}x{H:g} um  cores {len(gr['cores'])}  taps {len(taps)}  legs {nlegs}  NOT MODELLED (no lane load; NOT a pass)", fontsize=8, color="red")
        ax.text(0.5, 0.5, "NOT MODELLED", transform=ax.transAxes, ha="center", va="center", fontsize=18, color="red", alpha=0.35)
    if drawn:
        ax.set_title(f"{tn}  {W:g}x{H:g} um  grid taps {len(grid_taps or [])} (r={radius:g})  pins {len(pin_pts(t))}  chains {len(dlegs)}  "
                     f"max hop {dmax:.0f} um  hops>405: {dover}  (heat {'%.2f' % peak if modelled else 'n/a'})", fontsize=7)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    return {"type": tn, "modelled": modelled, "peak_util": round(peak, 2) if modelled else None, "legs_over_405": int(nlong) if nlegs else None,
            "legs": nlegs, "taps": len(taps), "cores": len(gr["cores"]),
            "detail": drawn, "grid_taps": len(grid_taps or []), "pins": len(pin_pts(t)), "chains": len(dlegs),
            "max_hop_um": round(dmax, 1) if dlegs else None, "hops_over_405": int(dover) if dlegs else None}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--types")
    ap.add_argument("--repo", help="source tree the plan side files resolve against: draws the exported tap grid (DETAIL-1)")
    ap.add_argument("--radius", type=float, default=200.0)
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    Path(a.out).mkdir(parents=True, exist_ok=True)
    want = set(a.types.split(",")) if a.types else None
    rows = []
    for tn, t in sorted(raw["partition_types"].items()):
        if (want and tn not in want) or not isinstance(t, dict) or not t.get("outline_um"):
            continue
        try:
            gt = exported_taps(a.plan, tn, a.repo) if a.repo else None
            rows.append(render_type(tn, t, str(Path(a.out) / f"{tn}.png"), gt, a.radius))
        except Exception as e:  # noqa: BLE001
            rows.append({"type": tn, "error": f"{type(e).__name__}: {str(e)[:100]}"})
    (Path(a.out) / "summary.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
