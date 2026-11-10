#!/usr/bin/env python3
"""CLK-ROOT-CROSS (DIE-HBM-97 11-10, COORD vecd-clkroot-gen): root repeater for a clock port boxed in by macros.

Class (hnx_vms_bank_q0_faces__vecd4ae v32e0 / v512b, GRT 11-09/11-10): the clock ports sit in the M5 gap between two
stacked SRAM macros.  --macro-gap-block cuts the std-cell rows in that gap, so CTS puts the root buffer of the port net
outside it, across a macro (clk: port y 155.5 -> clkbuf_0_clk at y 74, under macro u_a).  The port net is then the only
signal whose box crosses the macro; GRT routes it straight over the macro on M5 (123 one-net overflow markers, GRT-0116)
or, for a second port in the same gap, runs out of legal paths (clk_e, GRT-0183).  -repair_clock_nets repairs the root
wire's length, not its geometry, and clk_leaf_repeat never touches the root port net.

Rule, from geometry only (no module, die or net name): a clock port net with exactly one sink pin, the sink not a
macro, gets ONE repeater when (a) every Manhattan L route from the port to the sink crosses a macro box, or (b) the port
is enclosed by macros (it lies in the gap between two macro boxes that overlap it in x, or between two that overlap it
in y) and the sink is outside that gap.  The repeater goes on a legal free row site outside every macro box (+ halo),
in the row band nearest the port, at the gap exit (the macro-free channel) with the shortest port -> repeater -> sink
Manhattan length whose repeater -> sink L route clears every macro; several ports in one gap get distinct sites.
A port net that needs a repeater and has no such site is an error (fail closed), never a silent skip.

plan() is pure (tested in test_clk_root_cross.py); physical/common_flow/clk_root_cross.tcl dumps the design to JSON,
runs `clk_root_cross.py plan IN OUT` and applies the result at PRE_GLOBAL_ROUTE.  Units: microns.
"""
import json
import sys

EPS = 1e-6


def _inside(box, x, y):
    return box[0] + EPS < x < box[2] - EPS and box[1] + EPS < y < box[3] - EPS


def _seg_hits(box, x0, y0, x1, y1):
    """axis-parallel segment (x0,y0)-(x1,y1) passes through the open interior of box"""
    lx, hx = min(x0, x1), max(x0, x1)
    ly, hy = min(y0, y1), max(y0, y1)
    if abs(y0 - y1) < EPS:   # horizontal
        return box[1] + EPS < y0 < box[3] - EPS and lx < box[2] - EPS and hx > box[0] + EPS
    if abs(x0 - x1) < EPS:   # vertical
        return box[0] + EPS < x0 < box[2] - EPS and ly < box[3] - EPS and hy > box[1] + EPS
    raise ValueError("segment not axis-parallel")


def l_routes_clear(macros, x0, y0, x1, y1):
    """number of the two L routes (H-then-V, V-then-H) between the points that clear every macro interior"""
    hv = not any(_seg_hits(m, x0, y0, x1, y0) or _seg_hits(m, x1, y0, x1, y1) for m in macros)
    vh = not any(_seg_hits(m, x0, y0, x0, y1) or _seg_hits(m, x0, y1, x1, y1) for m in macros)
    return int(hv) + int(vh)


def enclosing_gap(macros, x, y):
    """(axis, lo, hi) when the point lies between two macro boxes that both overlap it in the other axis: 'y' = the
    point is in a horizontal gap (macro below and above, gap spans y lo..hi), 'x' = a vertical gap; else None"""
    below = [m for m in macros if m[0] - EPS <= x <= m[2] + EPS and m[3] <= y + EPS]
    above = [m for m in macros if m[0] - EPS <= x <= m[2] + EPS and m[1] >= y - EPS]
    if below and above:
        return ("y", max(m[3] for m in below), min(m[1] for m in above))
    left = [m for m in macros if m[1] - EPS <= y <= m[3] + EPS and m[2] <= x + EPS]
    right = [m for m in macros if m[1] - EPS <= y <= m[3] + EPS and m[0] >= x - EPS]
    if left and right:
        return ("x", max(m[2] for m in left), min(m[0] for m in right))
    return None


def needs_repeater(macros, port, sink):
    """reason string when the port net needs a root repeater, else None"""
    px, py = port
    sx, sy = sink
    if not l_routes_clear(macros, px, py, sx, sy):
        return "cross"
    g = enclosing_gap(macros, px, py)
    if g:
        axis, lo, hi = g
        v = sy if axis == "y" else sx
        if not lo - EPS <= v <= hi + EPS:
            return "enclosed"
    return None


def _free_x(row, busy, w, x_want):
    """legal site x in row nearest to x_want for a cell of width w, avoiding busy [x0,x1) spans; None if full"""
    x0, y0, x1, y1, site = row["box"][0], row["box"][1], row["box"][2], row["box"][3], row["site"]
    n = int(round((x1 - x0) / site))
    if n <= 0 or w > x1 - x0 + EPS:
        return None
    k0 = int(round((min(max(x_want, x0), x1 - w) - x0) / site))
    spans = [b for b in busy if b[1] > y0 + EPS and b[0] < y1 - EPS]
    for d in range(n + 1):
        for k in ((k0 - d, k0 + d) if d else (k0,)):
            x = x0 + k * site
            if x < x0 - EPS or x + w > x1 + EPS:
                continue
            if not any(b[3] > x + EPS and b[2] < x + w - EPS for b in spans):
                return x
    return None


def plan(d):
    """d: {macros: [[x0,y0,x1,y1]], halo, rows: [{box:[x0,y0,x1,y1], site}], busy: [[y0,y1,x0,x1]],
    cell_w, band_um, ports: [{net, port:[x,y], sinks:[{inst, xy:[x,y], macro: bool}]}]}
    -> {placements: [{net, reason, x, y}], skipped: [{net, why}], errors: [{net, why}]}"""
    macros = [tuple(m) for m in d["macros"]]
    halo = float(d.get("halo", 0.0))
    keep = [(m[0] - halo, m[1] - halo, m[2] + halo, m[3] + halo) for m in macros]
    w = float(d["cell_w"])
    band = float(d.get("band_um", 30.0))
    busy = [list(b) for b in d.get("busy", [])]
    rows = [r for r in d["rows"] if not any(r["box"][0] < k[2] - EPS and r["box"][2] > k[0] + EPS
                                            and r["box"][1] < k[3] - EPS and r["box"][3] > k[1] + EPS for k in keep)]
    out = {"placements": [], "skipped": [], "errors": []}
    for p in sorted(d["ports"], key=lambda q: q["net"]):
        net = p["net"]
        sinks = p.get("sinks", [])
        if len(sinks) != 1:
            out["skipped"].append({"net": net, "why": f"{len(sinks)} sinks"})
            continue
        s = sinks[0]
        if s.get("macro"):
            out["skipped"].append({"net": net, "why": "sink is a macro pin"})
            continue
        px, py = p["port"]
        sx, sy = s["xy"]
        why = needs_repeater(macros, (px, py), (sx, sy))
        if not why:
            out["skipped"].append({"net": net, "why": "route clear"})
            continue
        best = None
        for b in (band, 2 * band, 4 * band):
            for r in rows:
                ry = r["box"][1]
                if abs(ry - py) > b:
                    continue
                # nearest free site to the port's x, and to each side channel edge
                wants = [px] + [k[0] - w for k in keep] + [k[2] for k in keep]
                for xw in wants:
                    x = _free_x(r, busy, w, xw)
                    if x is None:
                        continue
                    cx, cy = x + w / 2, ry + (r["box"][3] - ry) / 2
                    if any(_inside(k, cx, cy) for k in keep):
                        continue
                    if not l_routes_clear(macros, cx, cy, sx, sy):
                        continue
                    if not l_routes_clear(macros, px, py, cx, cy):
                        continue
                    cost = abs(px - cx) + abs(py - cy) + abs(cx - sx) + abs(cy - sy)
                    if best is None or cost < best[0] - EPS:
                        best = (cost, x, ry, r["box"][3])
            if best:
                break
        if not best:
            out["errors"].append({"net": net, "why": f"{why}: no free legal site outside macros within {4 * band:g} um "
                                                     "of the port with a macro-free route to the sink"})
            continue
        _, x, y0, y1 = best
        busy.append([y0, y1, x, x + w])
        out["placements"].append({"net": net, "reason": why, "x": round(x, 4), "y": round(y0, 4),
                                  "len_um": round(best[0], 2)})
    return out


def main(argv):
    if len(argv) != 4 or argv[1] != "plan":
        print("usage: clk_root_cross.py plan IN.json OUT.json", file=sys.stderr)
        return 2
    res = plan(json.load(open(argv[2])))
    json.dump(res, open(argv[3], "w"), indent=1, sort_keys=True)
    for e in res["errors"]:
        print(f"OT_CLK_ROOT_CROSS ERROR {e['net']}: {e['why']}")
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
