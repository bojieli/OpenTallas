#!/usr/bin/env python3
"""KV-D24-HUBC 11-18: re-site die clock tree sites (clock.reserved_sites_um kind die_clock_tree) that a planned hard core
covers.  A die clock cell cannot sit inside a hard core, and the reserved rect is an M1-M7 obstruction + placement
blockage in the type build (gen_phys.reserved_sites_tcl), so a rect under a core (+ halo) is a dead site.  KV hub_C split:
pvfin_hi (207.36 x 194.4 at 1503.36, 907.2) covers the die clock tree rect [1620.0, 972.0, 1622.16, 973.35]; no
collision-free pvfin pair exists in hub_C, and the e9 tree source (kv-clk-r2 runs/e9) that cut the rects is deleted.

Rule (fixed, die-agnostic): each rect that overlaps a hard core body moves by the SMALLEST axis-aligned translation (W/E/S/N, same size) that
clears every hard core + HALO, every other reserved rect (any kind), every planned register point
(clksite_points.points, + CLEAR_UM) and stays inside the outline; y snaps outward to the 0.27-um row, x to the 0.054-um
site.  No move over --max-move-um (exit 1).  The ledger gives the old / new rect, the move and the die-frame centre per
partition instance (R0 only, else origin + orient) for the die clock rebuild, which must place the node at the new site.

  clksite_resite.py PLAN -o OUT.json --ledger L.json [--types T,..] [--halo-um 2.16] [--max-move-um 80]
"""
import argparse, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_points as CP

ROW_UM, SITE_UM = 0.27, 0.054


def _ov(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _grow(r, g):
    return (r[0] - g, r[1] - g, r[2] + g, r[3] + g)


def _snap_out(v, step, up):
    q = v / step
    return round((math.ceil(q - 1e-9) if up else math.floor(q + 1e-9)) * step, 6)


def _legal(r, t, cores, others, pts):
    w, h = t["outline_um"]
    if r[0] < 0 or r[1] < 0 or r[2] > w or r[3] > h:
        return False
    if any(_ov(r, c) for c in cores) or any(_ov(r, o) for o in others):
        return False
    g = _grow(r, CP.CLEAR_UM)
    return not any(g[0] < p[0] < g[2] and g[1] < p[1] < g[3] for p in pts)


def _candidates(r, core, halo, max_move):
    """(move_um, dir, rect) for the 4 directions: first position clear of this core + halo, snapped outward"""
    c = _grow(core, halo); w, h = r[2] - r[0], r[3] - r[1]
    out = []
    y1 = _snap_out(c[1], ROW_UM, False); out.append(("S", (r[0], y1 - h, r[2], y1)))
    y0 = _snap_out(c[3], ROW_UM, True); out.append(("N", (r[0], y0, r[2], y0 + h)))
    x1 = _snap_out(c[0], SITE_UM, False); out.append(("W", (x1 - w, r[1], x1, r[3])))
    x0 = _snap_out(c[2], SITE_UM, True); out.append(("E", (x0, r[1], x0 + w, r[3])))
    return [(round(abs(n[0] - r[0]) + abs(n[1] - r[1]), 4), d, n) for d, n in out]


def _step(d, n):
    dx, dy = {"S": (0, -ROW_UM), "N": (0, ROW_UM), "W": (-SITE_UM, 0), "E": (SITE_UM, 0)}[d]
    return (n[0] + dx, n[1] + dy, n[2] + dx, n[3] + dy)


def resite_type(tn, t, halo, max_move, parts):
    rs = (t.get("clock") or {}).get("reserved_sites_um", []) or []
    cores = CP._cores(t); gcores = [_grow(c, halo) for c in cores]
    pts = [(c[i] if not isinstance(i, str) else c[i]) for _, c, i, _ in CP.points(t)]
    pts = [p for p in pts if isinstance(p, (list, tuple)) and len(p) == 2]
    led = []
    for k, e in enumerate(rs):
        if e.get("kind") != "die_clock_tree":
            continue
        r = tuple(e["rect_um"])
        hit = [c for c in cores if _ov(r, c)]        # covered = overlaps the core body (near-core rects cut by
        # clksite_reserve under its own edge-gap rule stay where they are)
        if not hit:
            continue
        others = [tuple(o["rect_um"]) for j, o in enumerate(rs) if j != k]
        best = None
        for _, d, n in sorted(_candidates(r, max(hit, key=lambda c: (c[2] - c[0]) * (c[3] - c[1])), halo, max_move)):
            while True:
                mv = abs(n[0] - r[0]) + abs(n[1] - r[1])
                if mv > max_move + 1e-9:
                    break
                if _legal(n, t, gcores, others, pts):
                    if best is None or mv < best[0] - 1e-9:
                        best = (mv, d, n)
                    break
                n = _step(d, n)
        row = dict(type=tn, index=k, old=list(r), cores=[list(c) for c in hit])
        if best is None:
            row.update(new=None, why=f"no legal site within {max_move} um")
        else:
            mv, d, n = best
            n = [round(v, 6) for v in n]
            e["rect_um"] = n
            row.update(new=n, dir=d, move_um=round(mv, 4),
                       die_centre_um={p: ([round(o[0] + (n[0] + n[2]) / 2, 4), round(o[1] + (n[1] + n[3]) / 2, 4)]
                                          if orient == "R0" else dict(origin_um=o, orient=orient))
                                      for p, o, orient in parts})
        led.append(row)
    return led


def run(plan, types=None, halo=CP.CORE_HALO_UM, max_move=80.0):
    pr = plan.get("partitions") or {}
    pr = pr.items() if isinstance(pr, dict) else [(v.get("name"), v) for v in pr]
    led = []
    for tn, t in sorted(plan["partition_types"].items()):
        if types and tn not in types:
            continue
        parts = [(n, v.get("origin_um"), str(v.get("orient", "R0"))) for n, v in pr if v.get("type") == tn]
        led += resite_type(tn, t, halo, max_move, parts)
    return led


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("-o", required=True); ap.add_argument("--ledger", required=True)
    ap.add_argument("--types"); ap.add_argument("--halo-um", type=float, default=CP.CORE_HALO_UM)
    ap.add_argument("--max-move-um", type=float, default=80.0); ap.add_argument("--lane", default="")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    led = run(plan, set(a.types.split(",")) if a.types else None, a.halo_um, a.max_move_um)
    stuck = [x for x in led if x["new"] is None]
    json.dump(plan, open(a.o, "w"), indent=1)
    json.dump(dict(lane=a.lane, halo_um=a.halo_um, max_move_um=a.max_move_um, moved=len(led) - len(stuck),
                   not_moved=len(stuck), rows=led), open(a.ledger, "w"), indent=1)
    print(json.dumps(dict(moved=len(led) - len(stuck), not_moved=len(stuck),
                          max_move_um=max((x["move_um"] for x in led if x["new"]), default=0.0))))
    return 1 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
