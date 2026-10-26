#!/usr/bin/env python3
"""Die clock MESH (D-QC-CLKMESH, COORD 2026-10-25 23:53; owner clock rule 10-23: industry multi-source CTS =
H-tree -> mesh -> local stubs, judged by related-pair skew with CPPR).  Opt-in; die_clock.py defaults are unchanged.

    die_clock_mesh.py build  PLAN --out DIR [--nx 64 --ny 64 --m 2 --rep-um 450 --ndr 4w]
    die_clock_mesh.py combo  DIR --kit KIT              # one die global_route: kit signals M4-M7 + mesh clock M8-M9
    die_clock_mesh.py mesh   DIR --corner TT            # linear-RC transient of the mesh net, driven by the routed tree
    die_clock_mesh.py stubsta DIR --corner TT           # OpenSTA tcl: stub buffer -> tap on the routed RC
    die_clock_mesh.py report DIR --plan PLAN            # related-pair skew with CPPR, slew, cap, clock power
    die_clock_mesh.py render DIR --plan PLAN            # mesh, drivers, H-tree, stubs, taps, keep-outs PNG

Structure (all die cells BUFx24, all die clock wire on M8 horizontal / M9 vertical, NDR 4W = width 0.16 / space 0.08):
  * mesh: nx vertical M9 straps at x_i = (i + 1/2) W / nx and ny horizontal M8 straps at y_j = (j + 1/2) H / ny,
    each spanning the strap grid; one special net ck_mesh (real special wires, so the die GRT sees their tracks).
  * drivers: m BUFx24 in parallel at every strap intersection, at a reserved site; an intersection on a keep-out (hard
    core / ROM / PHY macro) moves ALONG one of its two straps to the nearest free point (<= MAX_MOVE_UM), so it still
    lands directly on the strap.  The sites are the plan item (die.clock.mesh.driver_sites).
  * H-tree: a complete binary H-tree over the nx x ny intersection index grid (nx, ny powers of two): every level
    halves the index range of the axis with more intersections, every node sits at the exact midpoint of its two
    children, so every leg of a level has one length and one layer.  Legs get n = ceil(L / rep_um) equal segments;
    a repeater on a keep-out slides along its own leg to the nearest free point (the leg stays straight); a node
    buffer on a keep-out moves upstream along its incoming leg and drives the branch point through that wire, which
    is common to both children.  No balance pads anywhere.
  * leaf: the last-level node drives its two intersections; each intersection's m drivers sit at its reserved site.
  * stubs: every partition tap gets one stub BUFx24 whose input sits on the nearest strap (perpendicular foot of the
    tap; slid along the strap off a keep-out) and drives the tap through a straight M8/M9 stub.
Timing: OpenSTA cannot time a multi-driver mesh, so the routed RC is used in three exact pieces: (1) the routed
tree root -> driver A pins (OpenSTA, routed GRT RC, native NDR R + profile C, terminal caps restored; arrival max/min
per driver), (2) a linear RC transient of the mesh net (strap RC from the real strap geometry, via stacks, driver
Thevenin from the BUFx24 liberty at that corner, stub buffer pin caps) giving every stub input's late / early 50 %
arrival and 10-90 slew, (3) OpenSTA on the routed stub nets with those arrivals and slews as input constraints.
CPPR credit for a tap pair = the early/late range at the H-tree node common to the two taps' nearest drivers.
"""
import argparse
import gzip
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
import die_clock as DC  # noqa: E402

BUF = DC.BUF
STEP_UM = 2.16
MAX_MOVE_UM = 250.0             # COORD 23:53: driver-site moves within 250 um
NDR = {"4w": dict(width=0.16, space=0.08, rf=0.25, cf=1.3), "8w": dict(width=0.32, space=0.08, rf=0.125, cf=1.6)}
VDD = {"TT": 0.70, "FF": 0.77}
SITE_X, ROW_Y = 0.054, 0.27
BUF_W = 1.35                    # BUFx24 width (um) for side-by-side parallel drivers (ASAP7 BUFx24 25 x 0.054)


def snap(x, q):
    return round(round(x / q) * q, 4)


def pow2(n):
    return n > 0 and (n & (n - 1)) == 0


# ------------------------------------------------------------------------------------------------------------ build
FOOT_M = 2.0     # keep-out test margin around a site point: two side-by-side BUFx24 (2.7 um) + one-site halo


def hitf(K, p):
    """keep-out test of the whole site footprint (corners + centre, each with a one-site halo), so a rect that only
    reaches the footprint from a neighbouring index bucket is still found."""
    return any(K.hit(p[0] + dx, p[1] + dy, m=0.6) for dx in (-FOOT_M + 0.6, 0.0, FOOT_M - 0.6) for dy in (-0.4, 0.4))


def free_along(K, p, axis, limit, step=STEP_UM):
    """nearest free point to p moving along axis (0 = x, 1 = y) by <= limit (either direction); None if none."""
    if not hitf(K, p):
        return p, 0.0
    k = 1
    while k * step <= limit:
        for s in (1, -1):
            q = (p[0] + s * k * step, p[1]) if axis == 0 else (p[0], p[1] + s * k * step)
            if not hitf(K, q):
                return q, k * step
        k += 1
    return None, None


def free_near(K, p, limit=1500.0, step=4.32):
    """nearest free point to p in any direction (Manhattan rings), <= limit; (None, None) if none."""
    if not hitf(K, p):
        return p, 0.0
    r = 1
    while r * step <= limit:
        best = None
        for dx in range(-r, r + 1):
            for dy in {r - abs(dx), -(r - abs(dx))}:
                q = (p[0] + dx * step, p[1] + dy * step)
                if not hitf(K, q):
                    best = q
                    break
            if best:
                return best, r * step
        r += 1
    return None, None


def leg_sites(K, a, b, seg, out, tag, step=STEP_UM, s_init=0.0):
    """repeater sites on the straight leg a -> b: greedy walk, each next site the FARTHEST free on-leg point within
    seg of the previous one (so no on-leg hop exceeds seg: equal-length hops wherever the leg is free); where a
    keep-out longer than seg covers the leg, the site is the nearest free point to the ideal one (a short off-leg
    jog, recorded).  Returns [(xy, displacement_um)]."""
    L = abs(b[0] - a[0]) + abs(b[1] - a[1])
    if L - s_init <= seg:
        return []
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    n = math.ceil((L - s_init) / seg - 1e-9)
    s_eq = (L - s_init) / n            # equal split target when the leg is free
    pts, s0 = [], s_init
    while L - s0 > seg:
        tgt = min(s0 + s_eq, L - 1e-6)
        best = None
        t = tgt
        while t > max(s0, 0.0) + step:
            q = (a[0] + ux * t, a[1] + uy * t)
            if not hitf(K, q):
                best = (q, tgt - t, t)
                break
            t -= step
        if best is None:
            ideal = (a[0] + ux * tgt, a[1] + uy * tgt)
            q, d = free_near(K, ideal)
            if q is None:
                q, d = ideal, -1.0
                out["unplaced"].append([tag, len(pts) + 1])
            else:
                out.setdefault("jogs", []).append([tag, len(pts) + 1, round(d, 2)])
            best = (q, d, tgt)
        pts.append((best[0], best[1]))
        s0 = best[2]
        rem = L - s0
        if rem > seg:
            s_eq = rem / math.ceil(rem / seg - 1e-9)
    return pts


def stub_foot(K, xs, ys, x, y, limit):
    """stub input site for a tap at (x, y): over the two nearest M8 (horizontal) and two nearest M9 (vertical) straps,
    the perpendicular foot slid along the strap to the nearest free site; the one with the shortest stub wins.
    Returns (xy, slide_um, axis, i, j): axis 0 = foot on M8 strap j, 1 = on M9 strap i."""
    import bisect
    best = None
    ci = bisect.bisect_left(xs, x)
    cj = bisect.bisect_left(ys, y)
    for j in {max(cj - 1, 0), min(cj, len(ys) - 1)}:
        q, d = free_along(K, (min(max(x, xs[0]), xs[-1]), ys[j]), 0, limit)
        if q is not None:
            L = abs(q[0] - x) + abs(q[1] - y)
            if best is None or L < best[0]:
                best = (L, q, d, 0, int(min(range(len(xs)), key=lambda k: abs(xs[k] - q[0]))), j)
    for i in {max(ci - 1, 0), min(ci, len(xs) - 1)}:
        q, d = free_along(K, (xs[i], min(max(y, ys[0]), ys[-1])), 1, limit)
        if q is not None:
            L = abs(q[0] - x) + abs(q[1] - y)
            if best is None or L < best[0]:
                best = (L, q, d, 1, i, int(min(range(len(ys)), key=lambda k: abs(ys[k] - q[1]))))
    if best is None:
        return None, None, 0, 0, 0
    return best[1], best[2], best[3], best[4], best[5]


def split_long(cells, nets, K, taps_xy, hop_max, cell):
    """every driver -> load branch longer than hop_max (a slide / jog / node move made it long) gets equal-cut
    repeaters on its own L path (x first, then y), each at the nearest free site: no hop exceeds ~hop_max, so slew
    stays inside the limit.  Returns the number of repeaters added."""
    added = 0
    new_nets = []
    for n in nets:
        if n["drv"].startswith("port:"):
            continue
        a = cells[n["drv"]]
        pa = (a["x"], a["y"])
        loads = []
        for ld in n["loads"]:
            pb = taps_xy[ld[5:]] if ld.startswith("port:") else (cells[ld]["x"], cells[ld]["y"])
            L = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
            k = math.ceil(L / hop_max - 1e-9) - 1
            if k <= 0:
                loads.append(ld)
                continue
            corner = (pb[0], pa[1])
            chain = []
            for c in range(1, k + 1):
                t = c * L / (k + 1)
                dx = abs(corner[0] - pa[0])
                if t <= dx:
                    p = (pa[0] + math.copysign(t, corner[0] - pa[0]), pa[1])
                else:
                    p = (corner[0], pa[1] + math.copysign(t - dx, pb[1] - pa[1]))
                q, _ = free_near(K, p, limit=hop_max / 2)
                q = q or p
                nm = cell(f"ckm_x_{added}", q[0], q[1], "rep", level=n.get("level"), split=True)
                added += 1
                chain.append(nm)
            loads.append(chain[0])
            for u, w in zip(chain, chain[1:]):
                new_nets.append(dict(name=f"ckm_w_{u}", drv=u, loads=[w], level=n.get("level")))
            new_nets.append(dict(name=f"ckm_w_{chain[-1]}", drv=chain[-1], loads=[ld], level=n.get("level")))
        n["loads"] = loads
    nets += new_nets
    return added


def build(P, nx=64, ny=64, m=2, rep_um=450.0, ndr="4w", max_move=MAX_MOVE_UM, hop_max=480.0, leg_mode="slide", sites="any"):
    assert pow2(nx) and pow2(ny), "nx, ny must be powers of two (complete H-tree)"
    W, H = float(P.W), float(P.H)
    ko = DC.keepouts(P)
    if sites == "channel":   # every die clock cell outside all partitions (channels only; no tile outline change)
        ko = list(ko) + [P.rect(n) for n in P.parts]
    K = DC.KeepIndex(ko, die=(W, H))
    xs = [(i + 0.5) * W / nx for i in range(nx)]
    ys = [(j + 0.5) * H / ny for j in range(ny)]
    cells, nets, ports = {}, [], [("input", "root")]
    out = dict(meta=dict(nx=nx, ny=ny, m=m, rep_um=rep_um, ndr=ndr, sites=sites, W=W, H=H, pitch_um=[W / nx, H / ny]),
               xs=xs, ys=ys, drivers={}, htree=[], stubs=[], unplaced=[])

    def cell(name, x, y, kind, **kw):
        cells[name] = dict(x=snap(x - BUF_W / 2, SITE_X), y=snap(y - ROW_Y / 2, ROW_Y), kind=kind, **kw)
        return name

    # --- driver sites: intersection, else slide along the M9 strap (y) or the M8 strap (x), whichever is nearer
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            best = None
            for axis in (0, 1):
                q, d = free_along(K, (x, y), axis, max_move)
                if q is not None and (best is None or d < best[1]):
                    best = (q, d, axis)
            if best is None:
                out["unplaced"].append([i, j])
                continue
            q, d, axis = best
            names = [cell(f"ckm_d_{i}_{j}_{k}", q[0] + (k - (m - 1) / 2) * BUF_W, q[1], "drv", i=i, j=j)
                     for k in range(m)]
            out["drivers"][f"{i}_{j}"] = dict(i=i, j=j, ideal=[x, y], site=[round(q[0], 3), round(q[1], 3)],
                                              move_um=round(d, 2), strap="M8" if axis == 0 else "M9", cells=names)
    # --- H-tree over index ranges
    nid = [0]

    def node_xy(i0, i1, j0, j1):
        return ((xs[i0] + xs[i1 - 1]) / 2, (ys[j0] + ys[j1 - 1]) / 2)

    def rec(i0, i1, j0, j1, level, drv_cell, path):
        """drv_cell drives the branch point of this region (already at node_xy)."""
        ni, nj = i1 - i0, j1 - j0
        if ni == 1 and nj == 1:
            raise AssertionError
        ax = 0 if ni >= nj and ni > 1 else 1
        if ax == 0:
            h = (i0 + i1) // 2
            kids = [(i0, h, j0, j1), (h, i1, j0, j1)]
        else:
            h = (j0 + j1) // 2
            kids = [(i0, i1, j0, h), (i0, i1, h, j1)]
        here = node_xy(i0, i1, j0, j1)
        loads = []
        for c, kr in enumerate(kids):
            kp = node_xy(*kr)
            L = abs(kp[0] - here[0]) + abs(kp[1] - here[1])
            n_seg = max(1, math.ceil(L / rep_um - 1e-9))
            tag = f"{path}{c}"
            leaf = (kr[1] - kr[0]) * (kr[3] - kr[2]) == 1
            if leaf:
                assert n_seg == 1, f"leaf leg {L:.0f} um > rep_um: use a finer mesh"
                d = out["drivers"].get(f"{kr[0]}_{kr[2]}")
                loads += d["cells"] if d else []
                out["htree"].append(dict(level=level + 1, tag=tag, a=list(here), b=list(kp), len_um=round(L, 2),
                                         n_seg=1, reps=[], leaf=True))
                continue
            # internal child: node buffer on the incoming leg, upstream of the branch point when on a keep-out
            q, d = free_along(K, kp, ax, L / n_seg)
            if q is None:
                q, d = free_near(K, kp)
            if q is None:
                q, d = kp, -1.0
                out["unplaced"].append([tag, "node"])
            nb = cell(f"ckm_n{level + 1}_{tag}", q[0], q[1], "node", level=level + 1)
            first = None
            prev = None
            reps = []
            pc = cells.get(drv_cell)
            off = abs(pc["x"] + BUF_W / 2 - here[0]) + abs(pc["y"] + ROW_Y / 2 - here[1]) if pc else 0.0
            same_leg = (q[1 - ax] == kp[1 - ax])
            if leg_mode == "greedy":
                pts = leg_sites(K, here, q if same_leg else kp, rep_um, out, tag, s_init=-off)
            else:   # equal cuts, each slid along the leg (<= one segment), else the nearest free site (a jog)
                pts = []
                for k in range(1, n_seg):
                    t = k / n_seg
                    p = (here[0] + (kp[0] - here[0]) * t, here[1] + (kp[1] - here[1]) * t)
                    rq, rd = free_along(K, p, ax, L / n_seg)
                    if rq is None:
                        rq, rd = free_near(K, p)
                        if rq is not None:
                            out.setdefault("jogs", []).append([tag, k, round(rd, 2)])
                    if rq is None:
                        rq, rd = p, -1.0
                        out["unplaced"].append([tag, k])
                    pts.append((rq, rd))
            if pts:
                for k, (rq, rd) in enumerate(pts, 1):
                    rn = cell(f"ckm_r{level + 1}_{tag}_{k}", rq[0], rq[1], "rep", level=level + 1)
                    reps.append(dict(cell=rn, slide_um=round(rd, 2)))
                    if prev is None:
                        first = rn
                    else:
                        nets.append(dict(name=f"ckm_w_{prev}", drv=prev, loads=[rn], level=level + 1))
                    prev = rn
                nets.append(dict(name=f"ckm_w_{prev}", drv=prev, loads=[nb], level=level + 1))
                loads.append(first)
            else:
                loads.append(nb)
            out["htree"].append(dict(level=level + 1, tag=tag, a=list(here), b=list(kp), len_um=round(L, 2),
                                     n_seg=n_seg, reps=reps, node=nb, node_move_um=round(d, 2), leaf=False))
            rec(*kr, level + 1, nb, tag)
        nets.append(dict(name=f"ckm_w_{drv_cell}" if not drv_cell.startswith("port:") else "root",
                         drv=drv_cell, loads=loads, level=level))

    c0 = node_xy(0, nx, 0, ny)
    sp = P.clock.get("spine", {}) or {}
    root = tuple(sp.get("die_root_um") or sp.get("root_um") or c0)
    q, d = free_along(K, c0, 0, 2 * rep_um)
    if q is None:
        q, d = free_near(K, c0, limit=max(W, H))
    if q is None:
        q = c0
        out["unplaced"].append(["root", "node"])
    n0 = cell("ckm_n0", q[0], q[1], "node", level=0)
    trunk = abs(root[0] - c0[0]) + abs(root[1] - c0[1])
    out["meta"]["root_um"] = list(root)
    out["meta"]["trunk_um"] = round(trunk, 2)
    nets.append(dict(name="root", drv="port:root", loads=[n0], level=-1))
    rec(0, nx, 0, ny, 0, n0, "h")
    # --- stubs: every partition tap
    taps = DC.plan_taps(P)
    tap_rows = []
    import numpy as np
    xa, ya = np.array(xs), np.array(ys)
    for part, port, x, y, early in taps:
        tp = f"t_{DC.sv(part)}__{port}"
        ports.append(("output", tp))
        fq, fd, axis, i, j = stub_foot(K, xs, ys, x, y, 4 * max_move)
        if fq is None:
            fq, fd = (x, y), -1.0
            out["unplaced"].append([tp, "stub"])
        sb = cell(f"ckm_s_{len(tap_rows)}", fq[0], fq[1], "stub")
        nets.append(dict(name=f"ckm_w_{sb}", drv=sb, loads=["port:" + tp], level=99))
        tap_rows.append(dict(part=part, tap=port, port=tp, xy=[x, y], early_ps=early, stub=sb, foot=[round(fq[0], 3),
                             round(fq[1], 3)], strap=("M8", j) if axis == 0 else ("M9", i), slide_um=round(fd, 2),
                             stub_um=round(abs(fq[0] - x) + abs(fq[1] - y), 2)))
    out["taps"] = tap_rows
    if hop_max:
        out["meta"]["split_reps"] = split_long(cells, nets, K, {t["port"]: tuple(t["xy"]) for t in tap_rows}, hop_max,
                                               cell)
    out["meta"].update(cells=len(cells), drivers=len(out["drivers"]), bufx24_drivers=sum(len(d["cells"]) for d in
                       out["drivers"].values()), nodes=sum(1 for c in cells.values() if c["kind"] == "node"),
                       reps=sum(1 for c in cells.values() if c["kind"] == "rep"), stubs=len(tap_rows),
                       taps_early_nonzero=sum(1 for t in tap_rows if t["early_ps"]), unplaced=len(out["unplaced"]),
                       driver_moves=sum(1 for d in out["drivers"].values() if d["move_um"] > 0),
                       driver_move_max_um=max([d["move_um"] for d in out["drivers"].values()] or [0]),
                       rep_slide_max_um=max([r["slide_um"] for h in out["htree"] for r in h["reps"]] or [0]),
                       node_move_max_um=max([h.get("node_move_um", 0) for h in out["htree"]] or [0]),
                       stub_max_um=max(t["stub_um"] for t in tap_rows),
                       htree_wire_mm=round(sum(h["len_um"] for h in out["htree"]) / 1e3 + trunk / 1e3, 2),
                       mesh_wire_mm=round((len(ys) * (xs[-1] - xs[0]) + len(xs) * (ys[-1] - ys[0])) / 1e3, 2),
                       stub_wire_mm=round(sum(t["stub_um"] for t in tap_rows) / 1e3, 2))
    return cells, nets, ports, out


def write_verilog(cells, nets, ports, path):
    """timing/GRT netlist: tree + drivers + stubs.  Driver outputs and stub inputs join the special net ck_mesh."""
    outs = [p for d, p in ports if d == "output"]
    L = ["// GENERATED by tools/die_plan/die_clock_mesh.py", "module die_ctree (root, " + ", ".join(outs) + ");",
         "  input root;"] + [f"  output {p};" for p in outs]
    drv_net, in_net = {}, {}
    for n in nets:
        drv_net[n["drv"]] = n["name"]
        for ld in n["loads"]:
            if not ld.startswith("port:"):
                in_net[ld] = n["name"]
    wires = sorted({n["name"] for n in nets} - set(outs) - {"root"}) + ["ck_mesh"]
    L += [f"  wire {w};" for w in wires]
    for c in sorted(cells):
        k = cells[c]["kind"]
        a = "ck_mesh" if k == "stub" else in_net.get(c)
        y = "ck_mesh" if k == "drv" else drv_net.get(c)
        if a is None or y is None:
            raise SystemExit(f"die_clock_mesh: unconnected cell {c} A={a} Y={y}")
        L.append(f"  {BUF} {c} (.A({a}), .Y({y}));")
    L.append("endmodule")
    txt = "\n".join(L) + "\n"
    # a net that drives a tap port IS that port (no assign statements in the GRT netlist)
    ren = {n["name"]: ld[5:] for n in nets for ld in n["loads"] if ld.startswith("port:")}
    txt = re.sub(r"\b(ckm_w_[A-Za-z0-9_]+)\b", lambda q: ren.get(q.group(1), q.group(1)), txt)
    txt = "\n".join(l for l in txt.split("\n") if not re.match(r"\s*wire t_", l)) + "\n"
    Path(path).write_text(txt)
    return ren


def cmd_build(a):
    P = S.Plan(S.load(a.plan))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cells, nets, ports, M = build(P, a.nx, a.ny, a.m, a.rep_um, a.ndr, a.max_move, a.hop_max, a.leg, a.sites)
    ren = write_verilog(cells, nets, ports, out / "ctree.v")
    for n in nets:
        n["name"] = ren.get(n["name"], n["name"])
    import hashlib
    M["meta"]["plan"] = str(a.plan)
    M["meta"]["plan_sha256"] = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    M["meta"]["build_s"] = round(time.time() - t0, 1)
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
    print(json.dumps(M["meta"], indent=1))
    return 0


def pad_delay(corner, libdir, slew=40.0):
    """BUFx24 stage delay driving the next abutted BUFx24 (smallest table load), ps."""
    f = Path(libdir) / f"asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz"
    txt = gzip.open(f, "rt").read()
    i = txt.index("cell (BUFx24_ASAP7_75t_R)")
    blk = txt[i:txt.index("cell (", i + 10)]
    m = re.search(r"cell_rise \(\w+\) \{\s*index_1 \(\"([^\"]+)\"\);\s*index_2 \(\"([^\"]+)\"\);\s*values \((.*?)\);",
                  blk, re.S)
    sl = [float(v) for v in m.group(1).split(",")]
    rows = [[float(v) for v in r.split(",")] for r in re.findall(r"\"([^\"]+)\"", m.group(3))]
    return interp(sl, [r[0] for r in rows], slew)


def cmd_balance(a):
    """measured skew balancing of the H-tree (standard CTS delay balancing, done once on routed RC): from the combo
    run's driver-A arrivals (tree_<corner>.txt), every branching net gives each load the delay pad that lifts its
    subtree's latest driver arrival to the latest sibling's (pads = abutted BUFx24 chains placed just upstream of the
    load cell, so the leg wire is unchanged).  Writes a new build dir (ctree.v, place/nets/mesh.json)."""
    src, out = Path(a.dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    P = S.Plan(S.load(a.plan))
    M = json.loads((src / "mesh.json").read_text())
    ko = list(DC.keepouts(P)) + ([P.rect(n) for n in P.parts] if M["meta"].get("sites") == "channel" else [])
    K = DC.KeepIndex(ko, die=(float(P.W), float(P.H)))
    cells = json.loads((src / "place.json").read_text())
    data = json.loads((src / "nets.json").read_text())
    nets, ports = data["nets"], [tuple(p) for p in data["ports"]]
    D, _ = read_tree(Path(a.tree) if a.tree else src / f"tree_{a.corner}.txt")
    dl = pad_delay(a.corner, a.libdir)
    by_drv = {n["drv"]: n for n in nets}
    memo = {}

    def sub(c):   # latest driver-A arrival in the subtree of cell c (drivers themselves: their A arrival)
        if c in memo:
            return memo[c]
        if c in D:
            v = D[c][0]
        elif c.startswith("port:") or cells[c]["kind"] == "stub" or c not in by_drv:
            v = None
        else:
            vs = [sub(x) for x in by_drv[c]["loads"]]
            vs = [x for x in vs if x is not None]
            v = max(vs) if vs else None
        memo[c] = v
        return v
    sys.setrecursionlimit(100000)
    for n in nets:
        sub(n["drv"]) if not n["drv"].startswith("port:") else [sub(x) for x in n["loads"]]
    added, total_pad, hist = 0, 0.0, defaultdict(int)
    new_nets = []
    for n in nets:
        ld = [x for x in n["loads"] if not x.startswith("port:") and cells[x]["kind"] in ("node", "rep", "pad")]
        if len(ld) < 2:
            continue
        vmax = max(sub(x) for x in ld if sub(x) is not None)
        loads = []
        for x in n["loads"]:
            v = sub(x) if x in ld else None
            k = int(round((vmax - v) / dl)) if v is not None else 0
            if k <= 0:
                loads.append(x)
                continue
            hist[min(k, 50) // 5 * 5] += 1
            total_pad += k * dl
            cx, cy = cells[x]["x"], cells[x]["y"]
            chain = []
            for i in range(k):
                col, row = i % 16, i // 16
                for sgn in (-1, 1):
                    q = (cx + BUF_W / 2 + sgn * (col + 1) * (BUF_W + SITE_X * 2), cy + ROW_Y / 2 + 2 * ROW_Y * (row + 1))
                    if not hitf(K, q):
                        break
                else:
                    q, _ = free_near(K, q)
                nm = f"ckm_p{a.tag}_{added}"
                added += 1
                cells[nm] = dict(x=snap(q[0] - BUF_W / 2, SITE_X), y=snap(q[1] - ROW_Y / 2, ROW_Y), kind="pad",
                                 level=cells[x].get("level"))
                chain.append(nm)
            loads.append(chain[0])
            for u, w in zip(chain, chain[1:]):
                new_nets.append(dict(name=f"ckm_w_{u}", drv=u, loads=[w], level=cells[x].get("level")))
            new_nets.append(dict(name=f"ckm_w_{chain[-1]}", drv=chain[-1], loads=[x], level=cells[x].get("level")))
        n["loads"] = loads
    nets += new_nets
    ren = write_verilog(cells, nets, ports, out / "ctree.v")
    for n in nets:
        n["name"] = ren.get(n["name"], n["name"])
    M["meta"]["cells"] = len(cells)
    M["meta"]["balance"] = dict(src=str(src), corner=a.corner, pad_ps=round(dl, 2), pads=added,
                                total_pad_ns=round(total_pad / 1e3, 2), hist=dict(sorted(hist.items())))
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
    print(json.dumps(M["meta"]["balance"]))
    return 0


# ------------------------------------------------------------------------------------------------------------ combo
def cmd_combo(a):
    """combo.v + combo.tcl: kit signals (abstracts, M4-M7) + the mesh clock (M8-M9) in ONE global_route, then the
    native-NDR RC export of every clock net and the tree arrival at every driver A pin."""
    d, kit = Path(a.dir), Path(a.kit)
    M = json.loads((d / "mesh.json").read_text())
    cells = json.loads((d / "place.json").read_text())
    data = json.loads((d / "nets.json").read_text())
    rv = (kit / "grt/route.v").read_text()
    cv = (d / "ctree.v").read_text()
    mh = re.match(r"\s*module\s+(\w+)\s*\(([^)]*)\);", rv)
    rports = [p.strip() for p in mh.group(2).split(",") if p.strip()]
    rbody = rv[mh.end():rv.rindex("endmodule")]
    mc = re.search(r"module\s+die_ctree\s*\(([^)]*)\);", cv, re.S)
    cports = [p.strip() for p in mc.group(1).split(",") if p.strip()]
    assert not set(rports) & set(cports)
    cbody = cv[mc.end():cv.rindex("endmodule")]
    v = f"module die_combo ({', '.join(rports + cports)});\n" + rbody + cbody + "endmodule\n"
    (d / "combo.v").write_text(v)
    t = (kit / "grt/grt.tcl").read_text()
    pre = t.split("source /work/grt/obs.tcl")[0]
    pre = pre.replace("read_verilog /work/grt/route.v",
                      "foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\n"
                      "read_verilog /out/combo.v")
    pre = pre.replace(re.search(r"link_design \S+", pre).group(0), "link_design die_combo")
    nd = NDR[M["meta"]["ndr"]]
    W, H = M["meta"]["W"], M["meta"]["H"]
    xs, ys = M["xs"], M["ys"]
    L = ["source /work/grt/obs.tcl"]
    root = M["meta"]["root_um"]
    L.append(f"place_pin -pin_name root -layer M9 -location {{{root[0]:.3f} {root[1]:.3f}}} -pin_size {{0.04 0.32}}")
    for t_ in M["taps"]:
        L.append(f"place_pin -pin_name {t_['port']} -layer M9 -location {{{t_['xy'][0]:.3f} {t_['xy'][1]:.3f}}} "
                 f"-pin_size {{0.04 0.32}}")
    for c, v_ in sorted(cells.items()):
        L.append(f"place_inst -name {c} -location {{{v_['x']} {v_['y']}}} -orient R0 -status FIRM")
    hw = nd["width"] / 2
    L += ["set blk [ord::get_db_block]", "set tech [ord::get_db_tech]",
          "set mn [$blk findNet ck_mesh]", "$mn setSpecial", "$mn setSigType CLOCK", "$mn setWildConnected",
          "foreach it [$mn getITerms] { $it setSpecial }",
          "set sw [odb::dbSWire_create $mn ROUTED]", "set l8 [$tech findLayer M8]", "set l9 [$tech findLayer M9]",
          "set dbu [$tech getDbUnitsPerMicron]", "proc um {v} { global dbu; return [expr {round($v*$dbu)}] }"]
    # the strap footprint (+ NDR spacing) is also a routing obstruction: GRT does not derate special wires
    hs = hw + nd["space"]
    for y in ys:
        L.append(f"odb::dbObstruction_create $blk $l8 [um {xs[0] - hs:.4f}] [um {y - hs:.4f}] [um {xs[-1] + hs:.4f}] "
                 f"[um {y + hs:.4f}]")
    for x in xs:
        L.append(f"odb::dbObstruction_create $blk $l9 [um {x - hs:.4f}] [um {ys[0] - hs:.4f}] [um {x + hs:.4f}] "
                 f"[um {ys[-1] + hs:.4f}]")
    for y in ys:
        L.append(f"odb::dbSBox_create $sw $l8 [um {xs[0] - hw:.4f}] [um {y - hw:.4f}] [um {xs[-1] + hw:.4f}] "
                 f"[um {y + hw:.4f}] STRIPE")
    for x in xs:
        L.append(f"odb::dbSBox_create $sw $l9 [um {x - hw:.4f}] [um {ys[0] - hw:.4f}] [um {x + hw:.4f}] "
                 f"[um {ys[-1] + hw:.4f}] STRIPE")
    clock_nets = [n["name"] for n in data["nets"]]
    L += ["puts \"OT_MESH straps [llength [$sw getWires]]\"",
          "create_clock -name dck -period 833.000 [get_ports root]",
          "set_routing_layers -signal M4-M7 -clock M8-M9"]
    L += [f"set_global_routing_layer_adjustment M{k} 0.75" for k in (4, 5, 6, 7)]
    L += ["set_global_routing_layer_adjustment M8 0.4", "set_global_routing_layer_adjustment M9 0.4",
          f"create_ndr -name ot_mesh_ndr -width {{M8 {nd['width']} M9 {nd['width']}}} "
          f"-spacing {{M8 {nd['space']} M9 {nd['space']}}}",
          "set ndr [$blk findNonDefaultRule ot_mesh_ndr]", "set nn 0"]
    (d / "clock_nets.txt").write_text("\n".join(clock_nets) + "\n")
    L += ["set fh [open /clock/clock_nets.txt r]",
          "foreach nm [split [string trim [read $fh]] \"\\n\"] { set n [$blk findNet $nm]; if {$n == \"NULL\"} "
          "{ error \"missing clock net $nm\" }; $n setNonDefaultRule $ndr; $n setSigType CLOCK; incr nn }",
          "close $fh", "puts \"OT_NDR nets=$nn\"",
          "global_route -congestion_iterations 5 -allow_congestion -verbose -congestion_report_file "
          "/out/congestion_$::env(CORNER).rpt",
          "write_guides /out/route_$::env(CORNER).guide",
          "source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl",
          f"set_layer_rc -layer M8 -resistance 8.44765e-3 -capacitance [expr {{.103962*{nd['cf']}}}]",
          f"set_layer_rc -layer M9 -resistance 8.89556e-3 -capacitance [expr {{.0928446*{nd['cf']}}}]",
          "delete_clock [get_clocks dck]",
          "estimate_parasitics -global_routing -spef_file /out/native_$::env(CORNER).spef",
          "foreach c [get_cells ckm_d_*] { set_disable_timing $c }",
          "create_clock -name vclk -period 833.000",
          "set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]",
          "set_input_delay 0 -clock vclk [get_ports root]",
          "set_load 3.0 [get_ports t_*]",
          "set fh [open /out/tree_$::env(CORNER).txt w]",
          "foreach c [get_cells ckm_d_*] { set p [get_pins [get_full_name $c]/A]; puts $fh \"D [get_full_name $c] "
          "[get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]\" }",
          "foreach c [get_cells {ckm_n* ckm_r*}] { set p [get_pins [get_full_name $c]/Y]; puts $fh \"N "
          "[get_full_name $c] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] "
          "[get_property $p slew_max_rise]\" }",
          "close $fh",
          "report_check_types -max_slew -max_capacitance -violators",
          "write_db /out/combo_$::env(CORNER).odb", "puts OT_DONE"]
    (d / "combo.tcl").write_text(pre + "\n".join(L) + "\n")
    (d / "run_combo.sh").write_text(f"""#!/bin/bash
# GENERATED by die_clock_mesh.py combo: one die global_route (kit signals M4-M7 + mesh clock M8-M9) per corner
D=$(cd $(dirname $0) && pwd); K={kit.resolve()}
for c in ${{CORNERS:-TT FF}}; do
 docker run --rm --name ckmesh-$(basename $D)-$c-$$ --cpus=16 --memory=${{MEM:-48}}g --memory-swap=${{MEM:-48}}g -e CORNER=$c \\
   -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $(readlink -f $K/abstracts):/work/abstracts:ro -v $D:/out -v $D:/clock:ro openroad/orfs:latest \\
   bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /out/combo.tcl > /out/combo_$c.log 2>&1; echo EXIT \\$? >> /out/combo_$c.log; chown -R $(id -u):$(id -g) /out" &
done; wait
""")
    print("combo written", d / "combo.tcl", "clock nets", len(clock_nets))
    return 0


# ------------------------------------------------------------------------------------------------------------- mesh
def lib_buf(corner, libdir):
    """BUFx24 A->Y rise: (delay intercept table by input slew, Thevenin R kohm from the delay slope, A pin cap)."""
    f = Path(libdir) / f"asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz"
    txt = gzip.open(f, "rt").read()
    i = txt.index("cell (BUFx24_ASAP7_75t_R)")
    blk = txt[i:txt.index("cell (", i + 10)]
    m = re.search(r"cell_rise \(\w+\) \{\s*index_1 \(\"([^\"]+)\"\);\s*index_2 \(\"([^\"]+)\"\);\s*values \((.*?)\);",
                  blk, re.S)
    sl = [float(v) for v in m.group(1).split(",")]
    ld = [float(v) for v in m.group(2).split(",")]
    rows = [[float(v) for v in r.split(",")] for r in re.findall(r"\"([^\"]+)\"", m.group(3))]
    cap = float(re.search(r"rise_capacitance : ([\d.]+)", blk).group(1))
    # fit delay = d0(slew) + R * C over the 92..737 fF loads (the mesh node loads sit there)
    slope = sum((r[5] - r[2]) / (ld[5] - ld[2]) for r in rows) / len(rows)   # ps/fF = 0.69 R_th (lumped load)
    d0 = [r[2] - slope * ld[2] for r in rows]
    return sl, d0, slope / 0.69, cap


def interp(xv, yv, x):
    if x <= xv[0]:
        return yv[0]
    for k in range(1, len(xv)):
        if x <= xv[k]:
            t = (x - xv[k - 1]) / (xv[k] - xv[k - 1])
            return yv[k - 1] + t * (yv[k] - yv[k - 1])
    return yv[-1]


def read_tree(path):
    D, N = {}, {}
    for line in open(path):
        f = line.split()
        if len(f) < 5:
            continue
        rec = (float(f[2]), float(f[3]), float(f[4]))
        (D if f[0] == "D" else N)[f[1]] = rec
    return D, N


def cmd_mesh(a):
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    d = Path(a.dir)
    M = json.loads((d / "mesh.json").read_text())
    nd = NDR[M["meta"]["ndr"]]
    RC = {L: (r * nd["rf"], c * nd["cf"]) for L, (r, c) in DC.LAYER_RC.items()}
    xs, ys = M["xs"], M["ys"]
    sl, d0, Rd, cin = lib_buf(a.corner, a.libdir)
    D, _ = read_tree(d / f"tree_{a.corner}.txt")
    seg = a.seg
    # node keys: points on straps; every strap = sorted breakpoints (intersections, driver sites, stub feet)
    hpts, vpts = defaultdict(set), defaultdict(set)
    for j in range(len(ys)):
        hpts[j] |= {round(x, 3) for x in xs}
    for i in range(len(xs)):
        vpts[i] |= {round(y, 3) for y in ys}
    xi = {round(x, 3): i for i, x in enumerate(xs)}
    yj = {round(y, 3): j for j, y in enumerate(ys)}
    drv_at = []
    for k, dv in M["drivers"].items():
        X, Y = round(dv["site"][0], 3), round(dv["site"][1], 3)
        if dv["strap"] == "M8":
            hpts[dv["j"]].add(X)
            key = ("H", dv["j"], X)
        else:
            vpts[dv["i"]].add(Y)
            key = ("V", dv["i"], Y)
        drv_at.append((key, dv))
    stub_at = []
    for t in M["taps"]:
        L_, idx = t["strap"]
        X, Y = round(t["foot"][0], 3), round(t["foot"][1], 3)
        if L_ == "M8":
            hpts[idx].add(X)
            key = ("H", idx, X)
        else:
            vpts[idx].add(Y)
            key = ("V", idx, Y)
        stub_at.append((key, t))
    nodes, caps, edges = {}, [], []

    def canon(key):
        if key[0] == "H" and key[2] in xi:
            return ("X", xi[key[2]], key[1])
        if key[0] == "V" and key[2] in yj:
            return ("X", key[1], yj[key[2]])
        return key

    def node(key):
        key = canon(key)
        if key not in nodes:
            nodes[key] = len(nodes)
            caps.append(0.0)
        return nodes[key]

    def wire(k0, k1, length, L_):
        r, c = RC[L_]
        n = max(1, int(math.ceil(length / seg)))
        prev = node(k0)
        for s in range(1, n + 1):
            cur = node(k1) if s == n else node((k0, k1, s))
            edges.append((prev, cur, r * length / n))
            caps[prev] += c * length / n / 2
            caps[cur] += c * length / n / 2
            prev = cur
    for j, pts in hpts.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire(("H", j, u), ("H", j, w), w - u, "M8")
    for i, pts in vpts.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire(("V", i, u), ("V", i, w), w - u, "M9")
    via = DC.VIA_KOHM["M9"]   # M1 pin -> M8/M9 strap via stack
    # drivers: each site = m parallel BUFx24 behind one via stack; Thevenin ramp source per corner
    drv = []
    for key, dv in drv_at:
        k = node(key)
        kk = len(caps)
        caps.append(0.0)
        edges.append((kk, k, via))
        late = [D[c][0] for c in dv["cells"] if c in D]
        early = [D[c][1] for c in dv["cells"] if c in D]
        slw = [D[c][2] for c in dv["cells"] if c in D]
        if not late:
            raise SystemExit(f"no tree arrival for driver {dv['cells']}")
        m = len(dv["cells"])
        off_l = max(late) + interp(sl, d0, max(slw))
        off_e = min(early) + interp(sl, d0, min(slw))
        drv.append((kk, Rd / m, off_l, off_e, dv))
    stubn = []
    for key, t in stub_at:
        k = node(key)
        kk = len(caps)
        caps.append(cin)
        edges.append((k, kk, via))
        stubn.append((kk, t))
    N = len(caps)
    C = np.array(caps) * 1e-15
    rows, cols, vals = [], [], []
    for i0, i1, r in edges:
        g = 1.0 / (r * 1e3)
        rows += [i0, i1, i0, i1]
        cols += [i0, i1, i1, i0]
        vals += [g, g, -g, -g]
    for kk, R, _, _, _ in drv:
        rows.append(kk)
        cols.append(kk)
        vals.append(1.0 / (R * 1e3))
    G = sp.csc_matrix((vals, (rows, cols)), shape=(N, N))
    dt = a.dt * 1e-12
    A = (G + sp.diags(C / dt)).tocsc()
    lu = sla.splu(A)
    dk = np.array([k for k, *_ in drv])
    gd = np.array([1.0 / (R * 1e3) for _, R, *_ in drv])
    tn = np.array([k for k, _ in stubn])
    res = {}
    tr = a.ramp * 1e-12
    for mode, col in (("late", 2), ("early", 3)):
        off = np.array([x[col] for x in drv]) * 1e-12
        t0 = off.min() - 5e-12
        v = np.zeros(N)
        c10, c50, c90 = (np.full(len(tn), np.nan) for _ in range(3))
        steps = int((off.max() - t0 + a.t_end * 1e-12) / dt)
        for s in range(steps):
            tt = t0 + (s + 1) * dt
            vin = np.clip((tt - off) / tr + 0.5, 0, 1)    # ramp centred on the driver's 50 % output time at zero load
            b = C / dt * v
            np.add.at(b, dk, gd * vin)
            vn = lu.solve(b)
            v0, v1 = v[tn], vn[tn]
            for arr_, th in ((c10, 0.1), (c50, 0.5), (c90, 0.9)):
                hit = np.isnan(arr_) & (v1 >= th) & (v0 < th)
                arr_[hit] = (tt - dt + dt * (th - v0[hit]) / (v1[hit] - v0[hit])) * 1e12
            v = vn
            if not np.isnan(c90).any():
                break
        if np.isnan(c90).any():
            raise SystemExit(f"mesh transient: {int(np.isnan(c90).sum())} stub nodes unresolved")
        res[mode] = (c50, (c90 - c10) / 0.8)   # 10-90 scaled to the liberty 0-100 slew convention
    out = dict(corner=a.corner, R_drv_kohm=round(Rd, 4), cin_ff=cin, nodes=N, mesh_cap_pF=round(float(C.sum()) * 1e12, 2),
               stubs={})
    for idx, (kk, t) in enumerate(stubn):
        out["stubs"][t["stub"]] = dict(port=t["port"], late=round(float(res["late"][0][idx]), 3),
                                       early=round(float(res["early"][0][idx]), 3),
                                       slew_late=round(float(res["late"][1][idx]), 3),
                                       slew_early=round(float(res["early"][1][idx]), 3))
    lat = [s["late"] for s in out["stubs"].values()]
    out["stub_in_late_ps"] = [round(min(lat), 2), round(max(lat), 2)]
    out["stub_in_slew_max_ps"] = round(max(max(s["slew_late"], s["slew_early"]) for s in out["stubs"].values()), 2)
    (d / f"mesh_{a.corner}.json").write_text(json.dumps(out) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "stubs"}))
    return 0


# ---------------------------------------------------------------------------------------------------------- stubsta
def cmd_stubsta(a):
    """stub netlist: every stub buffer (A = port sm_<k>) and the split repeaters below it down to the tap port, with
    the mesh arrival/slew at each stub input as input constraints; routed RC of exactly those nets (stub_nets.txt)
    from the combo run's native SPEF (terminal caps restored with restore_clock_spef_caps.py first)."""
    d = Path(a.dir)
    Mz = json.loads((d / f"mesh_{a.corner}.json").read_text())
    M = json.loads((d / "mesh.json").read_text())
    data = json.loads((d / "nets.json").read_text())
    by_drv = {n["drv"]: n for n in data["nets"]}
    cells, nets = [], []
    for t in M["taps"]:
        todo = [t["stub"]]
        while todo:
            c = todo.pop()
            n = by_drv[c]
            cells.append((c, f"sm_{c[6:]}" if c == t["stub"] else None, n["name"]))
            nets.append(n["name"])
            todo += [ld for ld in n["loads"] if not ld.startswith("port:")]
    in_net = {}
    for n in data["nets"]:
        for ld in n["loads"]:
            in_net[ld] = n["name"]
    ins = [f"sm_{t['stub'][6:]}" for t in M["taps"]]
    outs = [t["port"] for t in M["taps"]]
    L = ["module die_stubs (" + ", ".join(ins + outs) + ");"] + [f"  input {p};" for p in ins] + \
        [f"  output {p};" for p in outs] + [f"  wire {w};" for w in sorted(set(nets) - set(outs))]
    cell_info = json.loads((d / "place.json").read_text())
    for c, port, y in cells:
        lib = cell_info[c].get("lib", BUF)
        L.append(f"  {lib} {c} (.A({port or in_net[c]}), .Y({y}));")
    L.append("endmodule")
    (d / "stubs.v").write_text("\n".join(L) + "\n")
    (d / "stub_nets.txt").write_text("\n".join(sorted(set(nets))) + "\n")
    T = [f"read_liberty {a.libdir}/asap7sc7p5t_INVBUF_RVT_{a.corner}_nldm_220122.lib.gz",
         "read_verilog /out/stubs.v", "link_design die_stubs", f"read_spef /out/stubs_{a.corner}.spef",
         "create_clock -name vclk -period 833.000"]
    for t in M["taps"]:
        s_ = Mz["stubs"][t["stub"]]
        p = f"sm_{t['stub'][6:]}"
        T.append(f"set_input_delay -max {s_['late']} -clock vclk [get_ports {p}]")
        T.append(f"set_input_delay -min {s_['early']} -clock vclk [get_ports {p}]")
        T.append(f"set_input_transition -max {s_['slew_late']} [get_ports {p}]")
        T.append(f"set_input_transition -min {s_['slew_early']} [get_ports {p}]")
    T += ["set_load 3.0 [get_ports t_*]", "set_output_delay 0 -clock vclk [get_ports t_*]",
          f"set fh [open /out/taps_{a.corner}.txt w]",
          "foreach p [get_ports t_*] {puts $fh \"T [get_full_name $p] [expr {833.000-[get_property $p slack_max_rise]}] "
          "[get_property $p slack_min_rise] [get_property $p slew_max_rise]\"}", "close $fh",
          "report_check_types -max_slew -max_capacitance -violators", "puts OT_DONE"]
    (d / f"stubs_{a.corner}.tcl").write_text("\n".join(T) + "\n")
    print("stub sta tcl", d / f"stubs_{a.corner}.tcl", "cells", len(cells), "nets", len(set(nets)))
    return 0


# ----------------------------------------------------------------------------------------------------------- report
def lca(a, b):
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return a[:k]


def cmd_report(a):
    P = S.Plan(S.load(a.plan))
    d = Path(a.dir)
    M = json.loads((d / "mesh.json").read_text())
    xs, ys = M["xs"], M["ys"]
    nx, ny = len(xs), len(ys)

    def path_of(i, j):
        """H-tree tag of intersection (i, j): replay the index bisection."""
        i0, i1, j0, j1, tag = 0, nx, 0, ny, "h"
        while (i1 - i0) * (j1 - j0) > 1:
            ni, nj = i1 - i0, j1 - j0
            if ni >= nj and ni > 1:
                h = (i0 + i1) // 2
                c = int(i >= h)
                i0, i1 = (i0, h) if not c else (h, i1)
            else:
                h = (j0 + j1) // 2
                c = int(j >= h)
                j0, j1 = (j0, h) if not c else (h, j1)
            tag += str(c)
        return tag
    import numpy as np
    xa, ya = np.array(xs), np.array(ys)
    rep = dict(meta=M["meta"], corners={})
    tb = defaultdict(list)
    for t in M["taps"]:
        tb[t["part"]].append(dict(port=t["port"], part=t["part"], xy=t["xy"]))
    seam = DC.seam_pairs(P, tb)
    intra = DC.intra_pairs(tb, float(P.budgets.get("tap_pitch_um", 400.0)))
    tagof = {}
    for t in M["taps"]:
        fx, fy = t["foot"]
        tagof[t["port"]] = path_of(int(np.argmin(abs(xa - fx))), int(np.argmin(abs(ya - fy))))
    for corner in [c for c in a.corner if (d / f"taps_{c}.txt").exists()]:
        _, N = read_tree(d / f"tree_{corner}.txt")
        rng = {"h": 0.0}
        for name, (late, early, _) in N.items():
            m_ = re.match(r"ckm_n\d+_(h[01]*)$", name)
            if m_:
                rng[m_.group(1)] = late - early
        if "ckm_n0" in N:
            rng["h"] = N["ckm_n0"][0] - N["ckm_n0"][1]
        arr = {}
        for line in open(d / f"taps_{corner}.txt"):
            f = line.split()
            arr[f[1]] = (float(f[2]), float(f[3]), float(f[4]))   # T port late early slew
        late = {p: v[0] for p, v in arr.items()}
        early = {p: v[1] for p, v in arr.items()}
        core_offsets = DC.plan_tap_early(P)
        for tap in M["taps"]:
            offset = core_offsets.get((tap["part"], tap["tap"]), {}).get(corner, tap.get("early_ps", 0.0))
            late[tap["port"]] += offset
            early[tap["port"]] += offset
        slew = {p: v[2] for p, v in arr.items()}

        def dmg(pa, pb):
            c = lca(tagof[pa], tagof[pb])
            while c not in rng and len(c) > 1:
                c = c[:-1]
            return DC.pair_clock_damage(late[pa], early[pa], late[pb], early[pb], rng.get(c, 0.0))["max_damage_ps"]
        sk = [dmg(x[0], x[1]) for x in seam]
        ik = [dmg(x[0], x[1]) for x in intra]
        worst = sorted(((dmg(x[0], x[1]), x[0], x[1]) for x in list(seam) + [(i[0], i[1]) for i in intra]),
                       reverse=True)[:10]
        Mz = json.loads((d / f"mesh_{corner}.json").read_text())
        _, Nn = read_tree(d / f"tree_{corner}.txt")
        rep["corners"][corner] = dict(
            insertion_ps=[round(min(late.values()), 2), round(max(late.values()), 2)],
            tap_skew_ps=round(max(late.values()) - min(late.values()), 2),
            seam_pairs=len(sk), seam_max_ps=round(max(sk), 2), seam_p99_ps=round(DC.pctl(sk, .99), 2),
            intra_pairs=len(ik), intra_max_ps=round(max(ik), 2), pairs_over_80=sum(1 for v in sk + ik if v > 80),
            related_pair_max_ps=round(max(sk + ik), 2), gate_ps=DC.GATE_PS,
            verdict="PASS" if max(sk + ik) <= DC.GATE_PS else "FAIL",
            tap_slew_max_ps=round(max(slew.values()), 2), mesh_stub_in_slew_max_ps=Mz["stub_in_slew_max_ps"],
            tree_slew_max_ps=round(max(v[2] for v in Nn.values()), 2), mesh_cap_pF=Mz["mesh_cap_pF"],
            worst=[[round(w, 2), x, y] for w, x, y in worst])
    # clock power: C V^2 f over every die clock wire + pin (mesh from the transient, tree/stub wire from length)
    nd = NDR[M["meta"]["ndr"]]
    cw = (DC.LAYER_RC["M8"][1] + DC.LAYER_RC["M9"][1]) / 2 * nd["cf"]
    ncell = M["meta"]["cells"]
    for corner, r in rep["corners"].items():
        c_tot = r["mesh_cap_pF"] + (M["meta"]["htree_wire_mm"] + M["meta"]["stub_wire_mm"]) * 1e3 * cw / 1e3 \
            + ncell * DC.BUF_CIN_FF / 1e3 + len(M["taps"]) * DC.TAP_LOAD_FF / 1e3
        r["clock_switched_cap_pF"] = round(c_tot, 1)
        r["clock_wire_power_W"] = round(c_tot * 1e-12 * VDD[corner] ** 2 / (DC.PERIOD_PS * 1e-12), 3)
    (d / "clock_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({c: {k: v for k, v in r.items() if k != "worst"} for c, r in rep["corners"].items()}, indent=1))
    return 0


# ----------------------------------------------------------------------------------------------------------- render
def cmd_render(a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    P = S.Plan(S.load(a.plan))
    d = Path(a.dir)
    M = json.loads((d / "mesh.json").read_text())
    W, H = M["meta"]["W"], M["meta"]["H"]
    fig, ax = plt.subplots(figsize=(W / 1600, H / 1600), dpi=a.dpi)
    for n in P.parts:
        r = P.rect(n)
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, lw=0.2, ec="0.6"))
    for r in DC.keepouts(P):
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="0.85", ec="none"))
    xs, ys = M["xs"], M["ys"]
    for y in ys:
        ax.plot([xs[0], xs[-1]], [y, y], color="tab:blue", lw=0.25)
    for x in xs:
        ax.plot([x, x], [ys[0], ys[-1]], color="tab:blue", lw=0.25)
    for h in M["htree"]:
        lw = max(0.3, 2.4 - 0.18 * h["level"])
        ax.plot([h["a"][0], h["b"][0]], [h["a"][1], h["b"][1]], color="tab:red", lw=lw)
    dv = list(M["drivers"].values())
    mv = [v for v in dv if v["move_um"] > 0]
    st = [v for v in dv if v["move_um"] == 0]
    ax.scatter([v["site"][0] for v in st], [v["site"][1] for v in st], s=1.2, c="k", marker="s", lw=0)
    ax.scatter([v["site"][0] for v in mv], [v["site"][1] for v in mv], s=2.0, c="tab:orange", marker="s", lw=0)
    for t in M["taps"]:
        ax.plot([t["foot"][0], t["xy"][0]], [t["foot"][1], t["xy"][1]], color="tab:green", lw=0.3)
    ax.scatter([t["xy"][0] for t in M["taps"]], [t["xy"][1] for t in M["taps"]], s=0.6, c="tab:green", lw=0)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    m_ = M["meta"]
    ax.set_title(f"{Path(m_.get('plan', 'die')).parent.name} die clock mesh {m_['nx']}x{m_['ny']} ({m_['pitch_um'][0]:.0f}x{m_['pitch_um'][1]:.0f} um, "
                 f"{m_['ndr']}), {m_['drivers']} driver sites x{m_['m']} (orange = moved, max "
                 f"{m_['driver_move_max_um']:.0f} um), H-tree red, {m_['stubs']} stubs green", fontsize=7)
    out = a.out or str(d / "mesh.png")
    fig.savefig(out, bbox_inches="tight")
    print(out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("plan")
    b.add_argument("--out", required=True)
    b.add_argument("--nx", type=int, default=64)
    b.add_argument("--ny", type=int, default=64)
    b.add_argument("--m", type=int, default=2)
    b.add_argument("--rep-um", type=float, default=450.0)
    b.add_argument("--ndr", choices=sorted(NDR), default="4w")
    b.add_argument("--max-move", type=float, default=MAX_MOVE_UM)
    b.add_argument("--leg", choices=["slide", "greedy"], default="slide",
                   help="repeater sites: equal cuts slid along the leg (balanced stage count) or greedy walk")
    b.add_argument("--sites", choices=["any", "channel"], default="any",
                   help="channel: die clock cells only outside partitions (reported as unplaced where impossible)")
    b.add_argument("--hop-max", type=float, default=480.0, help="split any driver->load branch longer than this")
    bl = sub.add_parser("balance")
    bl.add_argument("dir")
    bl.add_argument("--out", required=True)
    bl.add_argument("--plan", required=True)
    bl.add_argument("--corner", default="TT")
    bl.add_argument("--tree", help="measured tree_<corner>.txt of the same tree (default: DIR's)")
    bl.add_argument("--tag", default="", help="pad name tag (one per balancing pass)")
    bl.add_argument("--libdir", default=str(Path("~/.cache/opentallas/asap7_nldm").expanduser()))
    c = sub.add_parser("combo")
    c.add_argument("dir")
    c.add_argument("--kit", required=True)
    m = sub.add_parser("mesh")
    m.add_argument("dir")
    m.add_argument("--corner", default="TT")
    m.add_argument("--libdir", default=str(Path("~/.cache/opentallas/asap7_nldm").expanduser()))
    m.add_argument("--seg", type=float, default=100.0)
    m.add_argument("--dt", type=float, default=0.5)
    m.add_argument("--ramp", type=float, default=20.0)
    m.add_argument("--t-end", dest="t_end", type=float, default=600.0)
    s = sub.add_parser("stubsta")
    s.add_argument("dir")
    s.add_argument("--corner", default="TT")
    s.add_argument("--libdir", default="/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM")
    r = sub.add_parser("report")
    r.add_argument("dir")
    r.add_argument("--plan", required=True)
    r.add_argument("--corner", action="append")
    g = sub.add_parser("render")
    g.add_argument("dir")
    g.add_argument("--plan", required=True)
    g.add_argument("--out")
    g.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args(argv)
    if a.cmd == "report" and not a.corner:
        a.corner = ["TT", "FF"]
    return dict(build=cmd_build, balance=cmd_balance, combo=cmd_combo, mesh=cmd_mesh, stubsta=cmd_stubsta, report=cmd_report,
                render=cmd_render)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
