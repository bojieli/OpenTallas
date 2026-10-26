#!/usr/bin/env python3
"""Die clock MESH (D-QC-CLKMESH, COORD 2026-10-25 23:53; owner clock rule 10-23: industry multi-source CTS =
H-tree -> mesh -> local stubs, judged by related-pair skew with CPPR).  Opt-in; die_clock.py defaults are unchanged.

    die_clock_mesh.py build  PLAN --out DIR [--nx 64 --ny 64 --m 2 --rep-um 450 --ndr 4w] [--regions D]
                             [--delta-id D-<DIE>-CLKMESH]
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
Early/late (CLOCK-MESH-2, 10-26): with no derate the whole late-early range comes from the liberty pin
rise/fall_capacitance_range (OpenSTA, like sign-off STA, uses the min pin cap for min and the max for max arrivals);
every arrival is rise->rise (all die clock cells are non-inverting BUFx24), so pairs always compare like edges.

Clock regions (--regions D, opt-in; default 0 = one die mesh, unchanged): the 2^D subtrees below H-tree level D are
separate clock regions.  Each region has its OWN mesh (straps end at the region's outer intersections, special net
ck_mesh_r<k>), its drivers stay on its own straps, and every partition is assigned whole to the region holding its
centre (its taps' stubs land on that region's straps only), so no partition straddles a region seam.  Related pairs
are judged only inside a region (gate 80 ps).  An abutted port whose src and dst partitions sit in different regions
is a LANDED crossing (forwarded-clock landing, owner landed-regions standard 10-18 / neighbour-relative clocking 10-16;
COORD 2026-10-26 01:22): listed per port with its added cycles (--landing-cycles) in landed_crossings.json for TOK
pricing; its region-to-region clock offset is reported against the landing window (--landing-budget-ps).
"""
import argparse
import bisect
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
import die_clock_128 as C128  # noqa: E402

BUF = DC.BUF
STEP_UM = 2.16
MAX_MOVE_UM = 250.0             # COORD 23:53: driver-site moves within 250 um
NDR = {"4w": dict(width=0.16, space=0.08, rf=0.25, cf=1.3), "8w": dict(width=0.32, space=0.08, rf=0.125, cf=1.6)}
VDD = {"TT": 0.70, "FF": 0.77}
SITE_X, ROW_Y = 0.054, 0.27
# Actual current ORFS asap7sc7p5t_28_R_1x_220121a.lef SIZE, not the obsolete 25-site estimate.
# Parallel drivers use the full physical width; every buffer has the same 0.27-um row height.
BUF_WIDTHS = {f"BUFx{k}_ASAP7_75t_R": w for k, w in
              {"2": .270, "3": .324, "4": .378, "4f": .432, "5": .432, "6f": .540,
               "8": .648, "10": .756, "12": .864, "12f": .972, "16f": 1.188, "24": 1.620}.items()}
BUF_W = BUF_WIDTHS[BUF]


def snap(x, q):
    return round(round(x / q) * q, 4)


def pow2(n):
    return n > 0 and (n & (n - 1)) == 0


def htree_tag(i, j, nx, ny):
    """H-tree tag ('h' + one bit per level) of intersection (i, j): replay the build's index bisection."""
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


def region_boxes(nx, ny, depth, W=None, H=None):
    """the 2^depth clock regions = the H-tree subtrees below level `depth`, in index space [i0, i1) x [j0, j1)
    (same bisection as the build), each with its geometric box (cut half-way between straps) when W, H are given."""
    regs = [("h", 0, nx, 0, ny)]
    for _ in range(depth):
        nxt = []
        for tag, i0, i1, j0, j1 in regs:
            ni, nj = i1 - i0, j1 - j0
            if ni * nj <= 1:
                raise ValueError(f"--regions {depth} deeper than the {nx}x{ny} mesh")
            if ni >= nj and ni > 1:
                h = (i0 + i1) // 2
                nxt += [(tag + "0", i0, h, j0, j1), (tag + "1", h, i1, j0, j1)]
            else:
                h = (j0 + j1) // 2
                nxt += [(tag + "0", i0, i1, j0, h), (tag + "1", i0, i1, h, j1)]
        regs = nxt
    out = []
    for k, (tag, i0, i1, j0, j1) in enumerate(regs):
        r = dict(k=k, tag=tag, i0=i0, i1=i1, j0=j0, j1=j1)
        if W is not None:
            px, py = W / nx, H / ny
            r["box_um"] = [round(i0 * px, 3), round(j0 * py, 3), round(i1 * px, 3), round(j1 * py, 3)]
        out.append(r)
    return out


def strap_bounds(g, xs, ys, axis):
    """Metal ends may extend beyond the last crossing to legal driver islands, but never meet a neighbour mesh."""
    if g.get("strap_box_um") is not None:
        b = g["strap_box_um"]
        return b[axis], b[axis + 2]
    return (xs[g["i0"]], xs[g["i1"] - 1]) if axis == 0 else (ys[g["j0"]], ys[g["j1"] - 1])


def strap_span(M, g, xs, ys, axis, idx):
    """extent of ONE strap (axis 0 = M8 row j=idx, 1 = M9 column i=idx) of region g: the region extent, clipped at
    declared macro holes when the build recorded per-strap spans (--clock-floorplan); None = strap removed."""
    sp = (M or {}).get("strap_spans")
    if sp is None:
        return strap_bounds(g, xs, ys, axis)
    v = sp.get(f"{'H' if axis == 0 else 'V'}:{idx}:{g.get('k')}")
    return tuple(v) if v else None


def clip_span(lo, hi, c, axis, holes, margin):
    """clip strap [lo, hi] (at perpendicular coordinate c) at every hole rect it crosses; a hole must touch one end
    of the strap (it may not split it in two: one strap = one metal segment).  None when nothing remains."""
    for h in holes:
        r = h["rect_um"]
        plo, phi = (r[1], r[3]) if axis == 0 else (r[0], r[2])
        if not plo - margin <= c <= phi + margin:
            continue
        a, b = ((r[0], r[2]) if axis == 0 else (r[1], r[3]))
        a, b = a - margin, b + margin
        if b <= lo or a >= hi:
            continue
        if a <= lo:
            lo = b
        elif b >= hi:
            hi = a
        else:
            raise ValueError(f"clock-floorplan hole {h['name']} splits a strap in two at {c}: declare regions so a hole "
                             f"touches a region strap end")
        if hi - lo < 1.0:
            return None
    return (round(lo, 4), round(hi, 4))


def floorplan_regions(fp, W, H, ny):
    """explicit clock regions on declared partition edges (x_cuts_um), each a complete power-of-two mesh of
    region_nx columns x ny rows; returns (xs, R).  Tags h0..h<n-1>: the die root drives one tree per region."""
    cuts = [0.0] + [float(c) for c in fp.get("x_cuts_um", [])] + [float(W)]
    nxs = [int(n) for n in fp["region_nx"]]
    if len(nxs) != len(cuts) - 1 or any(b <= a for a, b in zip(cuts, cuts[1:])) or not all(pow2(n) for n in nxs):
        raise ValueError("clock-floorplan: region_nx must give one power-of-two column count per x_cuts_um interval")
    if len(nxs) > 10:
        raise ValueError("clock-floorplan: at most 10 regions (one-digit region tags)")
    xs, R, i0 = [], [], 0
    for k, ((a, b), n) in enumerate(zip(zip(cuts, cuts[1:]), nxs)):
        xs += [a + (i + 0.5) * (b - a) / n for i in range(n)]
        R.append(dict(k=k, tag=f"h{k}", i0=i0, i1=i0 + n, j0=0, j1=ny, box_um=[round(a, 3), 0.0, round(b, 3), round(H, 3)]))
        i0 += n
    return xs, R


def floorplan_tag(i, j, R, ny):
    """H-tree tag of intersection (i, j) under explicit floorplan regions: region tag + its own bisection bits."""
    g = next(g for g in R if g["i0"] <= i < g["i1"])
    return g["tag"] + htree_tag(i - g["i0"], j - g["j0"], g["i1"] - g["i0"], g["j1"] - g["j0"])[1:]


def floorplan_holes(P, fp):
    """declared macro holes (straps stop at the macro edge, no drivers / tree cells inside, no taps allowed) and the
    driverless hard-core rects (cores at or below M7 under the M8/M9 mesh: straps pass over, a driver whose
    intersection has no legal site within max-move is dropped; the core's own tree is its declared tap latency)."""
    holes = []
    for name in fp.get("macro_holes", []):
        if isinstance(name, dict):
            holes.append(dict(name=name["name"], rect_um=list(map(float, name["rect_um"]))))
        else:
            holes.append(dict(name=name, rect_um=list(map(float, P.rect(name)))))
    cores = []
    if fp.get("hard_core_drivers") == "drop":
        for n, p in P.parts.items():
            for hc in P.types[p["type"]].get("hard_cores", []) or []:
                om = hc.get("obs_max")
                if om is None or int(str(om).lstrip("Mm")) > 7:
                    continue      # unknown / above M7: never assume the mesh may pass over it
                (x0, y0), (w, h) = hc["origin_um"], hc["outline_um"]
                a, b = P.to_die(n, (x0, y0)), P.to_die(n, (x0 + w, y0 + h))
                cores.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), f"{n}/{hc['inst']}"))
    return holes, cores


def floorplan_islands(P, fp):
    """in-core INFRA ISLAND via windows (HBM-CORE-LAT core_infra_islands.json, METHODOLOGY 12.2a/12.7): die-frame
    rects (x0, y0, x1, y1, '<part>/<inst>') of every window of every hard-core instance whose master has an ISLAND."""
    path = fp.get("island_windows")
    if not path:
        return []
    isl = json.loads(Path(path).read_text())["islands"]
    out = []
    for n, p in P.parts.items():
        for hc in P.types[p["type"]].get("hard_cores", []) or []:
            g = isl.get(hc.get("module"))
            if not g or g.get("action") != "ISLAND":
                continue
            x0, y0 = hc["origin_um"]
            for w in g["windows_um"]:
                a, b = P.to_die(n, (x0 + w[0], y0 + w[1])), P.to_die(n, (x0 + w[2], y0 + w[3]))
                out.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), f"{n}/{hc['inst']}"))
    return out


def island_site(wins, core, x, y, max_move, jog_max, spans):
    """nearest island window of `core` for the intersection (x, y): the driver pair sits at the window centre and
    joins the strap through a perpendicular jog (M8 jog to an M9 strap, M9 jog to an M8 strap).  spans(axis) gives
    the strap extent.  Returns (cell_xy, foot_xy, axis, slide_um, jog_um) or None."""
    best = None
    for w in wins:
        if w[4] != core:
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        for axis in (0, 1):     # 0: on the M8 strap (y fixed): slide x, jog in y; 1: on the M9 strap: slide y, jog x
            sp = spans(axis)
            if sp is None:
                continue
            slide, jog = (abs(cx - x), abs(cy - y)) if axis == 0 else (abs(cy - y), abs(cx - x))
            foot = (cx, y) if axis == 0 else (x, cy)
            if not sp[0] <= foot[axis] <= sp[1] or slide > max_move or jog > jog_max:
                continue
            if best is None or slide + jog < best[3] + best[4]:
                best = ((cx, cy), foot, axis, slide, jog)
    return best


def in_rect(r, x, y, m=0.0):
    return r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m


def cell_width(c):
    lib = c.get("lib", BUF)
    if lib not in BUF_WIDTHS:
        raise ValueError(f"clock cell geometry is unknown for {lib}")
    return BUF_WIDTHS[lib]


def reserve_cell(K, name, c, width=None):
    """Occupancy is a physical keepout, including clock cells already placed during this build."""
    width = cell_width(c) if width is None else width
    r = (c["x"], c["y"], c["x"] + width, c["y"] + ROW_Y, "clock:" + name)
    for i in range(int(r[0] // K.b), int(r[2] // K.b) + 1):
        for j in range(int(r[1] // K.b), int(r[3] // K.b) + 1):
            K.g[(i, j)].append(r)
    return r


def release_cell_reservation(K, r):
    for i in range(int(r[0] // K.b), int(r[2] // K.b) + 1):
        for j in range(int(r[1] // K.b), int(r[3] // K.b) + 1):
            K.g[(i, j)].remove(r)


def placement_overlaps(cells):
    """Actual cell-body overlaps; abutting rectangles are legal.  Report independently of legalization settings."""
    buckets, out = defaultdict(list), []
    for n, c in cells.items():
        x, y = c["x"], c["y"]
        width = cell_width(c)
        keys = [(i, j) for i in range(int(x // 4), int((x + width) // 4) + 1)
                for j in range(int(y // 1), int((y + ROW_Y) // 1) + 1)]
        seen = set()
        for key in keys:
            for old in buckets[key]:
                if old in seen:
                    continue
                seen.add(old)
                v = cells[old]
                if min(x + width, v["x"] + cell_width(v)) - max(x, v["x"]) > 1e-5 and \
                   min(y + ROW_Y, v["y"] + ROW_Y) - max(y, v["y"]) > 1e-5:
                    out.append([old, n])
            buckets[key].append(n)
    return out


def hard_keepout_violations(P, cells, islands=None):
    """Check actual cell bodies, including split repeaters, against every hard/PHY clock keepout.  islands (12.2a /
    12.7, --clock-floorplan island_windows): a clock DRIVER body wholly inside a declared in-core island window of
    that very core is legal (the core is built with the island)."""
    K = DC.KeepIndex(DC.keepouts(P), die=(P.W, P.H))
    bad = []
    for name, c in cells.items():
        x0, y0 = c["x"], c["y"]
        x1, y1 = x0 + cell_width(c), y0 + ROW_Y
        if x0 < 0 or y0 < 0 or x1 > P.W or y1 > P.H:
            bad.append(dict(cell=name, keepout="outside die", rect_um=[x0, y0, x1, y1]))
        seen = set()
        for i in range(int(x0 // K.b), int(x1 // K.b) + 1):
            for j in range(int(y0 // K.b), int(y1 // K.b) + 1):
                for r in K.g.get((i, j), []):
                    if tuple(r) in seen:
                        continue
                    seen.add(tuple(r))
                    if x0 < r[2] and x1 > r[0] and y0 < r[3] and y1 > r[1]:
                        if islands and c.get("kind") == "drv" and any(
                                w[4] == r[4] and w[0] <= x0 and x1 <= w[2] and w[1] <= y0 and y1 <= w[3] for w in islands):
                            continue
                        bad.append(dict(cell=name, keepout=r[4], rect_um=[x0, y0, x1, y1], keepout_um=list(r[:4])))
    return bad


def mesh_tracks(path, P):
    """Read the actual die kit's make_tracks commands, rather than guessing a platform offset."""
    out = {}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if len(f) < 2 or f[0] != "make_tracks" or f[1] not in ("M8", "M9"):
            continue
        options = dict(zip(f[2::2], f[3::2]))
        axis = "y" if P.layers[f[1]]["dir"] == "H" else "x"
        value = dict(pitch_um=float(options[f"-{axis}_pitch"]), offset_um=float(options[f"-{axis}_offset"]))
        if value["pitch_um"] <= 0 or (f[1] in out and out[f[1]] != value):
            raise ValueError(f"ambiguous routing tracks for {f[1]}")
        out[f[1]] = value
    if set(out) != {"M8", "M9"}:
        raise ValueError("PG-aware mesh requires actual M8 and M9 make_tracks commands")
    return out


def pg_free_axis(ideal, shapes, layer, axis, span, profile, half_width, spacing, max_move):
    """Project the mesh onto real routing tracks outside exact PG rectangles plus the clock NDR footprint.

    Shapes are die_infra.pg_rects tuples (net, layer, x0, y0, x1, y1). A full mesh strap must avoid every
    parallel PG shape on its span; an impossible PHY band fails here instead of silently shorting its supply.
    """
    clearance = half_width + spacing + .001   # one actual 1x-LEF DBU beyond the NDR boundary
    intervals = sorted((r[2 + axis] - clearance, r[4 + axis] + clearance) for r in shapes if r[1] == layer)
    merged = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    starts = [r[0] for r in merged]
    pitch, offset = profile["pitch_um"], profile["offset_um"]
    out = []
    for target in ideal:
        k0 = round((target - offset) / pitch)
        best = None
        for d in range(math.ceil(max_move / pitch) + 2):
            ks = [k0] if d == 0 else sorted((k0 - d, k0 + d), key=lambda k: abs(offset + k * pitch - target))
            for k in ks:
                q = round(offset + k * pitch, 6)
                if abs(q - target) > max_move or q < half_width + spacing or q > span - half_width - spacing:
                    continue
                if out and q <= out[-1]:
                    continue
                ix = bisect.bisect_right(starts, q) - 1
                if ix < 0 or q >= merged[ix][1]:
                    best = q
                    break
            if best is not None:
                break
        if best is None:
            raise ValueError(f"no PG-free {layer} routing track within {max_move} um of mesh strap {target:.3f}; "
                             "the clock/PHY supply geometry needs a structural revision")
        out.append(best)
    return out


# ------------------------------------------------------------------------------------------------------------ build
FOOT_M = 2.0     # keep-out test margin around a site point: two side-by-side BUFx24 (2.7 um) + one-site halo


def hitf(K, p):
    """keep-out test of the whole site footprint (corners + centre, each with a one-site halo), so a rect that only
    reaches the footprint from a neighbouring index bucket is still found."""
    return any(K.hit(p[0] + dx, p[1] + dy, m=0.6) for dx in (-FOOT_M + 0.6, 0.0, FOOT_M - 0.6) for dy in (-0.4, 0.4))


def free_along(K, p, axis, limit, step=STEP_UM, bounds=None):
    """nearest free point to p moving along axis (0 = x, 1 = y) by <= limit (either direction); None if none.
    bounds = (lo, hi): the moved coordinate must stay inside (a region's strap extent)."""
    if not hitf(K, p):
        return p, 0.0
    k = 1
    while k * step <= limit:
        for s in (1, -1):
            q = (p[0] + s * k * step, p[1]) if axis == 0 else (p[0], p[1] + s * k * step)
            if bounds is not None and not (bounds[0] - 1e-6 <= q[axis] <= bounds[1] + 1e-6):
                continue
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


def stub_foot(K, xs, ys, x, y, limit, box=None, extent=None, span=None):
    """stub input site for a tap at (x, y): over the two nearest M8 (horizontal) and two nearest M9 (vertical) straps,
    the perpendicular foot slid along the strap to the nearest free site; the one with the shortest stub wins.
    box = (i0, i1, j0, j1): only that clock region's straps, foot inside the region's strap extent.
    Returns (xy, slide_um, axis, i, j): axis 0 = foot on M8 strap j, 1 = on M9 strap i."""
    import bisect
    i0, i1, j0, j1 = box or (0, len(xs), 0, len(ys))
    xs_, ys_ = xs[i0:i1], ys[j0:j1]
    bx, by = ((xs_[0], xs_[-1]), (ys_[0], ys_[-1])) if box else (None, None)
    if extent is not None:
        bx, by = (extent[0], extent[2]), (extent[1], extent[3])
    best = None
    ci = i0 + bisect.bisect_left(xs_, x)
    cj = j0 + bisect.bisect_left(ys_, y)
    for j in {max(cj - 1, j0), min(cj, j1 - 1)}:
        if span is not None:
            bx = span(0, j)
            if bx is None:
                continue
        q, d = free_along(K, (min(max(x, bx[0] if bx else xs_[0]), bx[1] if bx else xs_[-1]), ys[j]), 0, limit, bounds=bx)
        if q is not None:
            L = abs(q[0] - x) + abs(q[1] - y)
            if best is None or L < best[0]:
                best = (L, q, d, 0, int(min(range(len(xs)), key=lambda k: abs(xs[k] - q[0]))), j)
    for i in {max(ci - 1, i0), min(ci, i1 - 1)}:
        if span is not None:
            by = span(1, i)
            if by is None:
                continue
        q, d = free_along(K, (xs[i], min(max(y, by[0] if by else ys_[0]), by[1] if by else ys_[-1])), 1, limit, bounds=by)
        if q is not None:
            L = abs(q[0] - x) + abs(q[1] - y)
            if best is None or L < best[0]:
                best = (L, q, d, 1, i, int(min(range(len(ys)), key=lambda k: abs(ys[k] - q[1]))))
    if best is None:
        return None, None, 0, 0, 0
    return best[1], best[2], best[3], best[4], best[5]


def detour_sites(K, pa, pb, hop, grid=10.8, margin=900.0):
    """shortest 4-connected path pa -> pb over legal clock-cell sites (grid points free of every keep-out) inside the
    pa/pb box grown by margin; returns repeater sites, one wherever the walked path would exceed hop, or None."""
    from collections import deque
    x0, y0 = min(pa[0], pb[0]) - margin, min(pa[1], pb[1]) - margin
    nx_ = int((abs(pa[0] - pb[0]) + 2 * margin) / grid) + 2
    ny_ = int((abs(pa[1] - pb[1]) + 2 * margin) / grid) + 2

    def ij(p):
        return (min(max(int(round((p[0] - x0) / grid)), 0), nx_ - 1), min(max(int(round((p[1] - y0) / grid)), 0), ny_ - 1))
    s_, t_ = ij(pa), ij(pb)
    free = {}

    def ok(c):
        if c in (s_, t_):
            return True
        if c not in free:
            free[c] = not hitf(K, (x0 + c[0] * grid, y0 + c[1] * grid))
        return free[c]
    prev = {s_: None}
    dq = deque([s_])
    while dq:
        c = dq.popleft()
        if c == t_:
            break
        for dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n_ = (c[0] + dc[0], c[1] + dc[1])
            if 0 <= n_[0] < nx_ and 0 <= n_[1] < ny_ and n_ not in prev and ok(n_):
                prev[n_] = c
                dq.append(n_)
    if t_ not in prev:
        return None
    path = []
    c = t_
    while c is not None:
        path.append(c)
        c = prev[c]
    path.reverse()
    sites, run = [], 0.0
    pts = [(x0 + c[0] * grid, y0 + c[1] * grid) for c in path]
    pts[0], pts[-1] = tuple(pa), tuple(pb)
    for a_, b_ in zip(pts, pts[1:]):
        run += abs(b_[0] - a_[0]) + abs(b_[1] - a_[1])
        if run > hop - 2 * grid and b_ != pts[-1]:
            sites.append(b_)
            run = 0.0
    return sites or None


def split_long(cells, nets, K, taps_xy, hop_max, cell, out=None, both_l=False):
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
            for orient in ("xy", "yx") if both_l else ("xy",):
                # both_l (--clock-floorplan): when the x-first L crosses a hard wall, try the y-first L (e.g. up a
                # core channel, then along the core row gap) before declaring the tail unsplittable
                planned, reservations = [], []
                for c in range(1, k + 1):
                    t = c * L / (k + 1)
                    if orient == "xy":
                        corner = (pb[0], pa[1])
                        dx = abs(corner[0] - pa[0])
                        if t <= dx:
                            p = (pa[0] + math.copysign(t, corner[0] - pa[0]), pa[1])
                        else:
                            p = (corner[0], pa[1] + math.copysign(t - dx, pb[1] - pa[1]))
                    else:
                        dy = abs(pb[1] - pa[1])
                        if t <= dy:
                            p = (pa[0], pa[1] + math.copysign(t, pb[1] - pa[1]))
                        else:
                            p = (pa[0] + math.copysign(t - dy, pb[0] - pa[0]), pb[1])
                    q, _ = free_near(K, p, limit=hop_max / 2)
                    if q is None:
                        break
                    probe = dict(x=snap(q[0] - BUF_W / 2, SITE_X), y=snap(q[1] - ROW_Y / 2, ROW_Y))
                    reservations.append(reserve_cell(K, f"split_probe_{c}", probe))
                    planned.append(q)
                for r in reservations:
                    release_cell_reservation(K, r)
                if len(planned) == k:
                    break
            if both_l and len(planned) != k and k == 1 and L <= 2 * (750.0 - BUF_W - ROW_Y):
                # one repeater anywhere on either L whose two hops both stay inside the 750-um reach (the
                # equal-split site sits in a macro): scan the path, keep the most balanced legal site
                best_q = None
                for orient in ("xy", "yx"):
                    n_ = int(L // 10.8)
                    for s_ in range(1, n_):
                        t = s_ * 10.8
                        if orient == "xy":
                            dx = abs(pb[0] - pa[0])
                            p = ((pa[0] + math.copysign(t, pb[0] - pa[0]), pa[1]) if t <= dx else
                                 (pb[0], pa[1] + math.copysign(t - dx, pb[1] - pa[1])))
                        else:
                            dy = abs(pb[1] - pa[1])
                            p = ((pa[0], pa[1] + math.copysign(t, pb[1] - pa[1])) if t <= dy else
                                 (pa[0] + math.copysign(t - dy, pb[0] - pa[0]), pb[1]))
                        if hitf(K, p):
                            p, _ = free_near(K, p, limit=hop_max / 2)   # off-path site: still both hops <= reach
                            if p is None:
                                continue
                        h1 = abs(p[0] - pa[0]) + abs(p[1] - pa[1]) + BUF_W + ROW_Y
                        h2 = abs(pb[0] - p[0]) + abs(pb[1] - p[1]) + BUF_W + ROW_Y
                        if max(h1, h2) <= 750.0 and (best_q is None or max(h1, h2) < best_q[0]):
                            best_q = (max(h1, h2), p)
                if best_q is not None:
                    planned = [best_q[1]]
            if both_l and len(planned) != k:
                # no repeater set on either L: route around the macro on legal sites (maze detour), one repeater per
                # <= hop_max of detour path, so every hop is a real legal site inside the reach
                det = detour_sites(K, pa, pb, hop_max)
                if det:
                    planned, k = det, len(det)
                    if out is not None:
                        out.setdefault("detours", []).append(dict(driver=n["drv"], load=ld, direct_um=round(L, 2),
                                                                  reps=len(det)))
            if len(planned) != k:
                # A clock tail can traverse a PHY with its driver outside it. Never manufacture an illegal cell.
                # Keep the direct tail only within the binding 750-um reach; actual routed slew still decides.
                bound = L + BUF_W + ROW_Y
                if out is not None:
                    out.setdefault("unsplit_clock_branches", []).append(dict(driver=n["drv"], load=ld,
                        span_bound_um=round(bound, 3), reason="no legal repeater outside hard/PHY keepouts"))
                    if bound > 750.0:
                        out["unplaced"].append([n["drv"], ld, "STRUCTURAL clock span exceeds 750 um", round(bound, 3)])
                loads.append(ld)
                continue
            chain = []
            for q in planned:
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


def part_regions(P, R):
    """every partition -> the clock region whose geometric box holds its centre (whole partition, never split)."""
    out = {}
    for n in P.parts:
        r = P.rect(n)
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        out[n] = next(g["k"] for g in R if g["box_um"][0] <= cx <= g["box_um"][2] and g["box_um"][1] <= cy <= g["box_um"][3])
    return out


def build(P, nx=64, ny=64, m=2, rep_um=450.0, ndr="4w", max_move=MAX_MOVE_UM, hop_max=480.0, leg_mode="slide", sites="any",
          regions=0, delta_id=None, region_edge_straps=False, reserve_sites=False, pg_shapes=None, track_profile=None,
          floorplan=None, rule128=None):
    assert pow2(nx) and pow2(ny), "nx, ny must be powers of two (complete H-tree)"
    W, H = float(P.W), float(P.H)
    ko = DC.keepouts(P)
    if sites == "channel":   # every die clock cell outside all partitions (channels only; no tile outline change)
        ko = list(ko) + [P.rect(n) for n in P.parts]
    K = DC.KeepIndex(ko, die=(W, H))
    xs = [(i + 0.5) * W / nx for i in range(nx)]
    ys = [(j + 0.5) * H / ny for j in range(ny)]
    fp = floorplan
    if fp is not None:
        if regions:
            raise ValueError("--clock-floorplan declares its own regions; do not combine with --regions")
        xs, R_fp = floorplan_regions(fp, W, H, ny)
        nx = len(xs)
        holes, cores = floorplan_holes(P, fp)
        islands = floorplan_islands(P, fp)
    axis_snap = None
    if pg_shapes is not None:
        if track_profile is None:
            raise ValueError("PG-aware mesh requires the actual die-kit routing tracks")
        old_xs, old_ys = xs, ys
        xs = pg_free_axis(xs, pg_shapes, "M9", 0, W, track_profile["M9"], NDR[ndr]["width"] / 2, NDR[ndr]["space"], max_move)
        ys = pg_free_axis(ys, pg_shapes, "M8", 1, H, track_profile["M8"], NDR[ndr]["width"] / 2, NDR[ndr]["space"], max_move)
        axis_snap = dict(M9=round(max(abs(x-y) for x, y in zip(xs, old_xs)), 6),
                         M8=round(max(abs(x-y) for x, y in zip(ys, old_ys)), 6))
    cells, nets, ports = {}, [], [("input", "root")]
    out = dict(meta=dict(nx=nx, ny=ny, m=m, rep_um=rep_um, ndr=ndr, sites=sites, W=W, H=H, pitch_um=[W / nx, H / ny]),
               xs=xs, ys=ys, drivers={}, htree=[], stubs=[], unplaced=[])
    if axis_snap is not None:
        out["meta"].update(pg_aware=True, pg_tracks=track_profile, pg_axis_snap_max_um=axis_snap)
    if delta_id:
        out["meta"]["delta_id"] = delta_id
    if fp is not None:
        R, regions = R_fp, 1
        out["meta"].update(clock_floorplan=fp, macro_holes=holes, driverless_hard_cores=len(cores))
    else:
        R = region_boxes(nx, ny, regions, W, H)
    if region_edge_straps:
        if not regions:
            raise ValueError("--region-edge-straps requires --regions")
        # Leave a real NDR gap at every region boundary: both metal and its spacing footprint stay in the region.
        margin = NDR[ndr]["width"] / 2 + NDR[ndr]["space"] + SITE_X
        for g in R:
            b = g["box_um"]
            g["strap_box_um"] = [round(b[0] + margin, 4), round(b[1] + margin, 4),
                                  round(b[2] - margin, 4), round(b[3] - margin, 4)]
        out["meta"]["region_edge_straps"] = True
    reg_ij = {}
    for g in R:
        for i in range(g["i0"], g["i1"]):
            for j in range(g["j0"], g["j1"]):
                reg_ij[(i, j)] = g["k"]
    if regions:
        out["meta"].update(regions_depth=regions, regions=R)
        out["part_region"] = part_regions(P, R)
    span = None
    if fp is not None:
        hm = NDR[ndr]["width"] / 2 + NDR[ndr]["space"]
        spans = {}
        for g in R:
            for j in range(g["j0"], g["j1"]):
                spans[f"H:{j}:{g['k']}"] = clip_span(*strap_bounds(g, xs, ys, 0), ys[j], 0, holes, hm)
            for i in range(g["i0"], g["i1"]):
                spans[f"V:{i}:{g['k']}"] = clip_span(*strap_bounds(g, xs, ys, 1), xs[i], 1, holes, hm)
        out["strap_spans"] = spans
        out["hole_drivers"] = []

        def span(axis, idx, g=None):
            return strap_span(out, g, xs, ys, axis, idx)

    def cell(name, x, y, kind, **kw):
        cells[name] = dict(x=snap(x - BUF_W / 2, SITE_X), y=snap(y - ROW_Y / 2, ROW_Y), kind=kind, **kw)
        if reserve_sites:
            reserve_cell(K, name, cells[name])
        return name

    # --- driver sites: intersection, else slide along the M9 strap (y) or the M8 strap (x), whichever is nearer
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            best = None
            g = R[reg_ij[(i, j)]]
            rk = dict(region=g["k"]) if regions else {}
            if fp is not None:
                mh = next((h["name"] for h in holes if in_rect(h["rect_um"], x, y)), None)
                if mh is not None:
                    out["hole_drivers"].append([i, j, "macro_hole", mh])
                    continue
            for axis in (0, 1):
                bnd = strap_bounds(g, xs, ys, axis) if fp is None else span(axis, j if axis == 0 else i, g)
                if bnd is None:
                    continue
                q, d = free_along(K, (x, y), axis, max_move, bounds=bnd if regions else None)
                if q is not None and (best is None or d < best[1]):
                    best = (q, d, axis)
            if best is None and fp is not None and islands:
                core = next((c[4] for c in cores if in_rect(c, x, y)), None)
                isl = island_site(islands, core, x, y, max_move, float(fp.get("island_jog_max_um", 60.0)),
                                  lambda ax_: span(ax_, j if ax_ == 0 else i, g)) if core else None
                if isl is not None:
                    (cx, cy), foot, axis, sl, jg = isl
                    names = [cell(f"ckm_d_{i}_{j}_{k}", cx + (k - (m - 1) / 2) * BUF_W, cy, "drv", i=i, j=j, **rk)
                             for k in range(m)]
                    out["drivers"][f"{i}_{j}"] = dict(i=i, j=j, ideal=[x, y], site=[round(foot[0], 3), round(foot[1], 3)],
                                                      cell_site=[round(cx, 3), round(cy, 3)], island=core,
                                                      move_um=round(sl, 2), jog_um=round(jg, 2),
                                                      strap="M8" if axis == 0 else "M9", cells=names, **rk)
                    continue
            if best is None:
                hc = next((c[4] for c in cores if in_rect(c, x, y)), None) if fp is not None else None
                if hc is None and fp is not None and fp.get("io_macro_drivers") == "drop":
                    hc = next((r[4] for r in ko if str(r[4]).startswith("io/") and in_rect(r, x, y)), None)
                if hc is not None:
                    out["hole_drivers"].append([i, j, "io_macro" if hc.startswith("io/") else "hard_core", hc])
                    continue
                out["unplaced"].append([i, j])
                continue
            q, d, axis = best
            names = [cell(f"ckm_d_{i}_{j}_{k}", q[0] + (k - (m - 1) / 2) * BUF_W, q[1], "drv", i=i, j=j, **rk)
                     for k in range(m)]
            out["drivers"][f"{i}_{j}"] = dict(i=i, j=j, ideal=[x, y], site=[round(q[0], 3), round(q[1], 3)],
                                              move_um=round(d, 2), strap="M8" if axis == 0 else "M9", cells=names, **rk)
    # --- H-tree over index ranges
    nid = [0]

    def node_xy(i0, i1, j0, j1):
        return ((xs[i0] + xs[i1 - 1]) / 2, (ys[j0] + ys[j1 - 1]) / 2)

    def live(i0, i1, j0, j1):
        return any(f"{i}_{j}" in out["drivers"] for i in range(i0, i1) for j in range(j0, j1))

    def rec(i0, i1, j0, j1, level, drv_cell, path, kids=None, here=None):
        """drv_cell drives the branch point of this region (already at node_xy).  kids/here (--clock-floorplan
        root only): the region boxes driven from the die root point."""
        ni, nj = i1 - i0, j1 - j0
        if ni == 1 and nj == 1:
            raise AssertionError
        ax = 0 if ni >= nj and ni > 1 else 1
        if kids is not None:
            ax = 0
        elif ax == 0:
            h = (i0 + i1) // 2
            kids = [(i0, h, j0, j1), (h, i1, j0, j1)]
        else:
            h = (j0 + j1) // 2
            kids = [(i0, i1, j0, h), (i0, i1, h, j1)]
        here = here or node_xy(i0, i1, j0, j1)
        loads = []
        for c, kr in enumerate(kids):
            if fp is not None and not live(*kr):    # dead branch: every driver below sits in a hole
                out.setdefault("pruned_branches", []).append(f"{path}{c}")
                continue
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
    if fp is not None:
        c0 = root      # the die root drives one tree per explicit region: no trunk
    q, d = free_along(K, c0, 0, 2 * rep_um)
    if q is None:
        q, d = free_near(K, c0, limit=max(W, H))
    if q is None:
        q = c0
        out["unplaced"].append(["root", "node"])
    n0 = cell("ckm_n0", q[0], q[1], "node", level=0)
    trunk = abs(root[0] - c0[0]) + abs(root[1] - c0[1])
    out["meta"]["root_um"] = list(root)
    if fp is not None:
        out["meta"].update(nx=nx, pitch_um=[max((g["box_um"][2] - g["box_um"][0]) / (g["i1"] - g["i0"]) for g in R),
                                            H / ny], hole_drivers=len(out["hole_drivers"]))
    out["meta"]["trunk_um"] = round(trunk, 2)
    nets.append(dict(name="root", drv="port:root", loads=[n0], level=-1))
    if fp is not None:
        rec(0, nx, 0, ny, 0, n0, "h", kids=[(g["i0"], g["i1"], g["j0"], g["j1"]) for g in R], here=c0)
    else:
        rec(0, nx, 0, ny, 0, n0, "h")
    # --- stubs: every partition tap
    taps = DC.plan_taps(P)
    early_c = DC.plan_tap_early(P)
    tap_rows = []
    import numpy as np
    xa, ya = np.array(xs), np.array(ys)
    for part, port, x, y, early in taps:
        tp = f"t_{DC.sv(part)}__{port}"
        ports.append(("output", tp))
        g = R[out["part_region"][part]] if regions else R[0]
        rk = dict(region=g["k"]) if regions else {}
        fq, fd, axis, i, j = stub_foot(K, xs, ys, x, y, 4 * max_move,
                                       box=(g["i0"], g["i1"], g["j0"], g["j1"]) if regions else None,
                                       extent=g.get("strap_box_um"),
                                       span=(lambda ax_, k_, g=g: span(ax_, k_, g)) if fp is not None else None)
        if fp is not None and any(in_rect(h["rect_um"], x, y) and h["name"] != part for h in holes):
            out["unplaced"].append([tp, "tap inside a declared macro hole"])
        if fq is None:
            fq, fd = (x, y), -1.0
            out["unplaced"].append([tp, "stub"])
        sb = cell(f"ckm_s_{len(tap_rows)}", fq[0], fq[1], "stub", **rk)
        nets.append(dict(name=f"ckm_w_{sb}", drv=sb, loads=["port:" + tp], level=99))
        tap_rows.append(dict(part=part, tap=port, port=tp, xy=[x, y], early_ps=early,
                             early_corner_ps=early_c.get((part, port)), stub=sb, **rk, foot=[round(fq[0], 3),
                             round(fq[1], 3)], strap=("M8", j) if axis == 0 else ("M9", i), slide_um=round(fd, 2),
                             stub_um=round(abs(fq[0] - x) + abs(fq[1] - y), 2)))
    out["taps"] = tap_rows
    if hop_max:
        out["meta"]["split_reps"] = split_long(cells, nets, K, {t["port"]: tuple(t["xy"]) for t in tap_rows}, hop_max,
                                               cell, out, both_l=fp is not None)
    if rule128 is not None:   # METHODOLOGY 12.8: plan-model stub sizing (d1), early-tap FAIL list, fixed shielded tree
        libs = C128.lib_cells("TT", rule128["libdir"])
        sizing = C128.size_stubs(cells, nets, tap_rows, libs, NDR[ndr], DC.LAYER_RC, DC.TAP_LOAD_FF, BUF, BUF_W, ROW_Y,
                                 slew_max=rule128.get("tap_slew_max_ps", C128.TAP_SLEW_MAX_PS))
        erows = C128.early_offset_taps(P, tap_rows, early_c)
        out["rule_12_8"] = dict(early_offset_taps=erows, early_offset_cores=C128.summarize_early(erows),
                                stub_sizing=sizing)
    overlaps = placement_overlaps(cells)
    out["clock_cell_overlaps"] = overlaps
    out["clock_hard_keepout_violations"] = hard_keepout_violations(P, cells, islands if fp is not None else None)
    if fp is not None and islands:
        out["island_windows"] = [list(w) for w in islands]
        out["meta"]["island_drivers"] = sum(1 for d in out["drivers"].values() if d.get("island"))
    if reserve_sites:
        out["meta"]["reserve_cell_sites"] = True
    out["meta"].update(cells=len(cells), drivers=len(out["drivers"]), bufx24_drivers=sum(len(d["cells"]) for d in
                       out["drivers"].values()), nodes=sum(1 for c in cells.values() if c["kind"] == "node"),
                       reps=sum(1 for c in cells.values() if c["kind"] == "rep"), stubs=len(tap_rows),
                       taps_early_nonzero=sum(1 for t in tap_rows if t["early_ps"]), unplaced=len(out["unplaced"]),
                       clock_cell_overlap_pairs=len(overlaps),
                       clock_hard_keepout_violations=len(out["clock_hard_keepout_violations"]),
                       driver_moves=sum(1 for d in out["drivers"].values() if d["move_um"] > 0),
                       driver_move_max_um=max([d["move_um"] for d in out["drivers"].values()] or [0]),
                       rep_slide_max_um=max([r["slide_um"] for h in out["htree"] for r in h["reps"]] or [0]),
                       node_move_max_um=max([h.get("node_move_um", 0) for h in out["htree"]] or [0]),
                       stub_max_um=max(t["stub_um"] for t in tap_rows),
                       htree_wire_mm=round(sum(h["len_um"] for h in out["htree"]) / 1e3 + trunk / 1e3, 2),
                       mesh_wire_mm=round(sum((g["j1"] - g["j0"]) * (strap_bounds(g, xs, ys, 0)[1] - strap_bounds(g, xs, ys, 0)[0]) +
                                              (g["i1"] - g["i0"]) * (strap_bounds(g, xs, ys, 1)[1] - strap_bounds(g, xs, ys, 1)[0]) for g in R) / 1e3, 2)
                       if fp is None else round(sum(s_[1] - s_[0] for s_ in out["strap_spans"].values() if s_) / 1e3, 2),
                       stub_wire_mm=round(sum(t["stub_um"] for t in tap_rows) / 1e3, 2))
    if fp is not None:
        sh = fp.get("shield_net")
        tree_mm = 0.0
        txy = {t["port"]: t["xy"] for t in tap_rows}
        for n in nets:
            if n["drv"].startswith("port:"):
                continue
            a = cells[n["drv"]]
            for ld in n["loads"]:
                b = (txy[ld[5:]] if ld.startswith("port:") else
                     (cells[ld]["x"], cells[ld]["y"]))
                tree_mm += (abs(a["x"] - b[0]) + abs(a["y"] - b[1])) / 1e3
        out["meta"]["clock_shield"] = dict(
            net=sh, straps_shielded=sum(1 for v in out["strap_spans"].values() if v) if sh else 0,
            jogs_shielded=sum(1 for d in out["drivers"].values() if d.get("jog_um")) if sh else 0,
            grt_routed_tree_nets=sum(1 for n in nets if not n["drv"].startswith("port:")), grt_routed_tree_mm=round(tree_mm, 1),
            complete=False, open="12.7a/b: H-tree legs, split tails and stubs are still GRT-routed signal-style nets with "
                                 "no PG shield; shielding is complete only for mesh straps + island jogs")
        out["meta"]["pruned_branches"] = len(out.get("pruned_branches", []))
        out["meta"]["strap_spans_removed"] = sum(1 for v in out["strap_spans"].values() if not v)
    if rule128 is not None:
        sh = (fp or {}).get("shield_net") or "VSS"
        wires = C128.fixed_wires(out, cells, nets, BUF_W, ROW_Y)
        straps = (sum(1 for v in out["strap_spans"].values() if v) if fp is not None else
                  sum((g["i1"] - g["i0"]) + (g["j1"] - g["j0"]) for g in R))
        out["meta"]["clock_shield"] = C128.shield_record(wires, sh, straps,
                                                         sum(1 for d in out["drivers"].values() if d.get("jog_um")))
        out["meta"]["rule_12_8"] = dict(methodology="v4.1 12.8 + 12.4b", shield_net=sh, sizing="plan model (d1)",
                                        early_offset_taps=len(out["rule_12_8"]["early_offset_taps"]),
                                        tap_slew_max_ps=rule128.get("tap_slew_max_ps", C128.TAP_SLEW_MAX_PS))
    return cells, nets, ports, out


def mesh_net(region):
    return "ck_mesh" if region is None else f"ck_mesh_r{region}"


def write_verilog(cells, nets, ports, path):
    """timing/GRT netlist: tree + drivers + stubs.  Driver outputs and stub inputs join the special net ck_mesh (one
    net ck_mesh_r<k> per clock region with --regions)."""
    outs = [p for d, p in ports if d == "output"]
    L = ["// GENERATED by tools/die_plan/die_clock_mesh.py", "module die_ctree (root, " + ", ".join(outs) + ");",
         "  input root;"] + [f"  output {p};" for p in outs]
    drv_net, in_net = {}, {}
    for n in nets:
        drv_net[n["drv"]] = n["name"]
        for ld in n["loads"]:
            if not ld.startswith("port:"):
                in_net[ld] = n["name"]
    mnet = {c: mesh_net(v.get("region")) for c, v in cells.items() if v["kind"] in ("drv", "stub")}
    wires = sorted({n["name"] for n in nets} - set(outs) - {"root"}) + sorted(set(mnet.values()))
    L += [f"  wire {w};" for w in wires]
    for c in sorted(cells):
        k = cells[c]["kind"]
        a = mnet[c] if k == "stub" else in_net.get(c)
        y = mnet[c] if k == "drv" else drv_net.get(c)
        if a is None or y is None:
            raise SystemExit(f"die_clock_mesh: unconnected cell {c} A={a} Y={y}")
        L.append(f"  {cells[c].get('lib', BUF)} {c} (.A({a}), .Y({y}));")
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
    pg, pg_shapes, tracks = None, None, None
    if bool(a.pg_json) != bool(a.track_file):
        raise SystemExit("PG-aware mesh needs both --pg-json and --track-file from the actual die kit")
    if a.pg_json:
        import die_infra as DI
        pg = json.loads(Path(a.pg_json).read_text())
        pg_shapes = DI.pg_rects(P, pg["grid"])
        tracks = mesh_tracks(a.track_file, P)
    fp = json.loads(Path(a.clock_floorplan).read_text()) if a.clock_floorplan else None
    cells, nets, ports, M = build(P, a.nx, a.ny, a.m, a.rep_um, a.ndr, a.max_move, a.hop_max, a.leg, a.sites,
                                  a.regions, a.delta_id, a.region_edge_straps, a.reserve_cell_sites, pg_shapes, tracks,
                                  floorplan=fp, rule128=(dict(libdir=a.libdir, tap_slew_max_ps=a.tap_slew_max_ps)
                                                         if getattr(a, "rule_12_8", False) else None))
    ren = write_verilog(cells, nets, ports, out / "ctree.v")
    for n in nets:
        n["name"] = ren.get(n["name"], n["name"])
    import hashlib
    M["meta"]["plan"] = str(a.plan)
    M["meta"]["plan_sha256"] = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    if pg is not None:
        M["meta"].update(pg_source=str(a.pg_json), pg_sha256=hashlib.sha256(Path(a.pg_json).read_bytes()).hexdigest(),
                         pg_feasible=pg.get("feasible"))
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
    if C128.enabled(M):
        return balance_audit_128(a, src, out, M)
    ko = list(DC.keepouts(P)) + ([P.rect(n) for n in P.parts] if M["meta"].get("sites") == "channel" else [])
    K = DC.KeepIndex(ko, die=(float(P.W), float(P.H)))
    cells = json.loads((src / "place.json").read_text())
    reserve_sites = M["meta"].get("reserve_cell_sites", False)
    if reserve_sites:
        for name, c in cells.items():
            reserve_cell(K, name, c)
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
        # drivers too: a leaf node whose two intersections differ (one leg split by a repeater after a driver-site
        # move) is balanced at the driver pins (CLOCK-MESH-2 10-26: unbalanced leaf siblings left ~90 ps neighbour
        # driver steps on QC)
        ld = [x for x in n["loads"] if not x.startswith("port:") and cells[x]["kind"] in ("node", "rep", "pad", "drv")]
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
                if q is None:
                    raise SystemExit("die_clock_mesh balance: no legal site for clock pad")
                nm = f"ckm_p{a.tag}_{added}"
                added += 1
                cells[nm] = dict(x=snap(q[0] - BUF_W / 2, SITE_X), y=snap(q[1] - ROW_Y / 2, ROW_Y), kind="pad",
                                 level=cells[x].get("level"))
                if reserve_sites:
                    reserve_cell(K, nm, cells[nm])
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
    M["clock_cell_overlaps"] = placement_overlaps(cells)
    M["meta"]["clock_cell_overlap_pairs"] = len(M["clock_cell_overlaps"])
    M["meta"]["balance"] = dict(src=str(src), corner=a.corner, pad_ps=round(dl, 2), pads=added,
                                total_pad_ns=round(total_pad / 1e3, 2), hist=dict(sorted(hist.items())))
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
    print(json.dumps(M["meta"]["balance"]))
    return 0


def balance_audit_128(a, src, out, M):
    """12.8d: no measured pads.  Copies the build unchanged and writes the plan-model structural audit."""
    if a.tree:
        raise SystemExit("die_clock_mesh balance: 12.8 build -- measured balancing (--tree) is banned (12.8d)")
    cells = json.loads((src / "place.json").read_text())
    data = json.loads((src / "nets.json").read_text())
    libs = C128.lib_cells(a.corner, a.libdir)
    au = C128.structural_audit(M, cells, data["nets"], libs, NDR[M["meta"]["ndr"]], DC.LAYER_RC, BUF, BUF_W, ROW_Y)
    M["meta"]["balance"] = dict(src=str(src), corner=a.corner, pads=0, mode="12.8 structural audit (no pads)")
    if src.resolve() != out.resolve():
        (out / "ctree.v").write_text((src / "ctree.v").read_text())
        (out / "place.json").write_text(json.dumps(cells) + "\n")
        (out / "nets.json").write_text(json.dumps(data) + "\n")
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "balance_audit.json").write_text(json.dumps(au, indent=1) + "\n")
    print(json.dumps(au))
    return 0


# ------------------------------------------------------------------------------------------------------------ combo
def cmd_combo(a):
    """combo.v + combo.tcl: kit signals (abstracts, M4-M7) + the mesh clock (M8-M9) in ONE global_route, then the
    native-NDR RC export of every clock net and the tree arrival at every driver A pin."""
    d, kit = Path(a.dir), Path(a.kit)
    M = json.loads((d / "mesh.json").read_text())
    cells = json.loads((d / "place.json").read_text())
    if M.get("unplaced") or M["meta"].get("unplaced", 0):
        raise SystemExit("die_clock_mesh combo: unresolved/STRUCTURAL clock sites; revise before routing")
    overlaps = placement_overlaps(cells)
    if overlaps:
        raise SystemExit(f"die_clock_mesh combo: {len(overlaps)} physical clock-cell overlaps; "
                         f"rebuild with --reserve-cell-sites and actual LEF widths before routing: {overlaps[:3]}")
    if cells:
        plan_file = getattr(a, "plan", None) or M["meta"].get("plan")
        if not plan_file or not Path(plan_file).is_file():
            raise SystemExit("die_clock_mesh combo: needs --plan (or the original pinned plan) for actual hard-keepout census")
        bad = hard_keepout_violations(S.Plan(S.load(plan_file)), cells, [tuple(w) for w in M.get("island_windows", [])])
        if bad:
            raise SystemExit(f"die_clock_mesh combo: {len(bad)} clock-cell bodies overlap hard/PHY keepouts: {bad[:3]}")
    if M["meta"].get("pg_aware"):
        import types
        # Only directions are needed to parse the actual kit, so no guessed layer pitch or phase enters here.
        actual = mesh_tracks(kit / "grt/tracks.tcl", types.SimpleNamespace(layers={"M8": {"dir": "H"}, "M9": {"dir": "V"}}))
        if actual != M["meta"]["pg_tracks"]:
            raise SystemExit("PG-aware mesh routing tracks do not match the actual die kit")
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
    L += ["set blk [ord::get_db_block]", "set tech [ord::get_db_tech]", "set l8 [$tech findLayer M8]",
          "set l9 [$tech findLayer M9]", "set dbu [$tech getDbUnitsPerMicron]",
          "proc um {v} { global dbu; return [expr {round($v*$dbu)}] }"]
    # the strap footprint (+ NDR spacing) is also a routing obstruction: GRT does not derate special wires
    hs = hw + nd["space"]
    regs = M["meta"].get("regions") or [dict(k=None, i0=0, i1=len(xs), j0=0, j1=len(ys))]
    for g in regs:      # one special net per clock region (the whole strap grid without --regions)
        rx, ry = xs[g["i0"]:g["i1"]], ys[g["j0"]:g["j1"]]
        xlo, xhi = strap_bounds(g, xs, ys, 0)
        ylo, yhi = strap_bounds(g, xs, ys, 1)
        L += [f"set mn [$blk findNet {mesh_net(g['k'])}]", "$mn setSpecial", "$mn setSigType CLOCK",
              "$mn setWildConnected", "foreach it [$mn getITerms] { $it setSpecial }", "set sw [odb::dbSWire_create $mn ROUTED]"]
        if "strap_spans" in M:    # --clock-floorplan: per-strap extents clipped at macro holes
            hsp = [(y, strap_span(M, g, xs, ys, 0, j)) for j, y in zip(range(g["j0"], g["j1"]), ry)]
            vsp = [(x, strap_span(M, g, xs, ys, 1, i)) for i, x in zip(range(g["i0"], g["i1"]), rx)]
            hsp, vsp = [v for v in hsp if v[1]], [v for v in vsp if v[1]]
        else:
            hsp, vsp = [(y, (xlo, xhi)) for y in ry], [(x, (ylo, yhi)) for x in rx]
        shield = (M["meta"].get("clock_floorplan") or {}).get("shield_net") or \
            (M["meta"]["rule_12_8"]["shield_net"] if C128.enabled(M) else None)
        ob = hw + 2 * nd["space"] + nd["width"] if shield else hs    # shields: no signal within the shield spacing
        for y, (xlo, xhi) in hsp:
            L.append(f"odb::dbObstruction_create $blk $l8 [um {xlo - ob:.4f}] [um {y - ob:.4f}] [um {xhi + ob:.4f}] "
                     f"[um {y + ob:.4f}]")
        for x, (ylo, yhi) in vsp:
            L.append(f"odb::dbObstruction_create $blk $l9 [um {x - ob:.4f}] [um {ylo - ob:.4f}] [um {x + ob:.4f}] "
                     f"[um {yhi + ob:.4f}]")
        for y, (xlo, xhi) in hsp:
            L.append(f"odb::dbSBox_create $sw $l8 [um {xlo - hw:.4f}] [um {y - hw:.4f}] [um {xhi + hw:.4f}] "
                     f"[um {y + hw:.4f}] STRIPE")
        for x, (ylo, yhi) in vsp:
            L.append(f"odb::dbSBox_create $sw $l9 [um {x - hw:.4f}] [um {ylo - hw:.4f}] [um {x + hw:.4f}] "
                     f"[um {yhi + hw:.4f}] STRIPE")
        # island drivers (12.2a): perpendicular jog from the window to the strap, on this region's mesh net
        jogs = [dv for dv in M.get("drivers", {}).values() if dv.get("jog_um") and dv.get("region") == g["k"]]
        jo = hw + 2 * nd["space"] + nd["width"] if shield else hs
        for dv in jogs:
            (fx, fy), (cx, cy) = dv["site"], dv["cell_site"]
            lay, a0, b0, a1, b1 = (("$l8", min(fx, cx), cy, max(fx, cx), cy) if dv["strap"] == "M9" else
                                   ("$l9", cx, min(fy, cy), cx, max(fy, cy)))
            L.append(f"odb::dbObstruction_create $blk {lay} [um {a0 - jo:.4f}] [um {b0 - jo:.4f}] [um {a1 + jo:.4f}] "
                     f"[um {b1 + jo:.4f}]")
            if dv["strap"] == "M9":   # M8 jog in x at the window row
                L.append(f"odb::dbSBox_create $sw $l8 [um {min(fx, cx) - hw:.4f}] [um {cy - hw:.4f}] "
                         f"[um {max(fx, cx) + hw:.4f}] [um {cy + hw:.4f}] STRIPE")
            else:
                L.append(f"odb::dbSBox_create $sw $l9 [um {cx - hw:.4f}] [um {min(fy, cy) - hw:.4f}] "
                         f"[um {cx + hw:.4f}] [um {max(fy, cy) + hw:.4f}] STRIPE")
        if shield:   # 12.7a: a PG stripe on both sides of every clock strap and jog, one NDR space away
            off = hw + nd["space"] + nd["width"] / 2
            L += [f"set pn [$blk findNet {shield}]",
                  f"if {{$pn eq \"NULL\"}} {{ set pn [odb::dbNet_create $blk {shield}] }}",
                  "$pn setSpecial", "$pn setSigType GROUND", "set psw [odb::dbSWire_create $pn ROUTED]"]
            segs = [("M8", xlo, y, xhi, y) for y, (xlo, xhi) in hsp] + [("M9", x, ylo, x, yhi) for x, (ylo, yhi) in vsp]
            for dv in jogs:
                (fx, fy), (cx, cy) = dv["site"], dv["cell_site"]
                segs.append(("M8", min(fx, cx), cy, max(fx, cx), cy) if dv["strap"] == "M9" else
                            ("M9", cx, min(fy, cy), cx, max(fy, cy)))
            sw2 = nd["width"] / 2
            for lay, a0, b0, a1, b1 in segs:
                for sgn in (-1, 1):
                    if lay == "M8":
                        yy = b0 + sgn * off
                        L.append(f"odb::dbSBox_create $psw $l8 [um {a0 - hw:.4f}] [um {yy - sw2:.4f}] [um {a1 + hw:.4f}] "
                                 f"[um {yy + sw2:.4f}] STRIPE")
                    else:
                        xx = a0 + sgn * off
                        L.append(f"odb::dbSBox_create $psw $l9 [um {xx - sw2:.4f}] [um {b0 - hw:.4f}] [um {xx + sw2:.4f}] "
                                 f"[um {b1 + hw:.4f}] STRIPE")
    clock_nets = [n["name"] for n in data["nets"]]
    if C128.enabled(M):   # 12.7a/12.8: every tree net is a fixed, shielded pre-route; its RC is that geometry
        wires = C128.fixed_wires(M, cells, data["nets"], BUF_W, ROW_Y)
        L += C128.combo_tcl(wires, nd, M["meta"]["rule_12_8"]["shield_net"])
        sp = C128.spef(wires, cells, BUF, nd, DC.LAYER_RC, DC.VIA_KOHM)
        for c_ in ("TT", "FF"):
            (d / f"native_{c_}.spef").write_text(sp)
    L += [f"puts \"OT_MESH regions {len(regs)} straps {sum((g['i1'] - g['i0']) + (g['j1'] - g['j0']) for g in regs)}\"",
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
          "global_route -congestion_iterations 50 -allow_congestion -verbose -congestion_report_file "
          "/out/congestion_$::env(CORNER).rpt",
          "write_guides /out/route_$::env(CORNER).guide",
          "source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl",
          f"set_layer_rc -layer M8 -resistance 8.44765e-3 -capacitance [expr {{.103962*{nd['cf']}}}]",
          f"set_layer_rc -layer M9 -resistance 8.89556e-3 -capacitance [expr {{.0928446*{nd['cf']}}}]",
          "delete_clock [get_clocks dck]",
          ("read_spef /out/native_$::env(CORNER).spef" if C128.enabled(M) else
           "estimate_parasitics -global_routing -spef_file /out/native_$::env(CORNER).spef"),
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
pids=()
for c in ${{CORNERS:-TT FF}}; do
 docker run --rm --name ckmesh-$(basename $D)-$c-$$ --cpus=16 --memory=${{MEM:-48}}g --memory-swap=${{MEM:-48}}g -e CORNER=$c \\
   -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $(readlink -f $K/abstracts):/work/abstracts:ro -v $D:/out -v $D:/clock:ro openroad/orfs:latest \\
   bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 && openroad -no_init -threads 16 -exit /out/combo.tcl > /out/combo_$c.log 2>&1; rc=\\$?; echo EXIT \\$rc >> /out/combo_$c.log; chown -R $(id -u):$(id -g) /out; exit \\$rc" &
 pids+=($!)
done
rc=0
for p in "${{pids[@]}}"; do
 if wait "$p"; then :; else child_rc=$?; [ "$rc" -ne 0 ] || rc=$child_rc; fi
done
exit "$rc"
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
    # strap (j or i, region k) -> breakpoints; one region (k None) spanning the grid without --regions
    hpts, vpts = defaultdict(set), defaultdict(set)
    regs = M["meta"].get("regions") or [dict(k=None, i0=0, i1=len(xs), j0=0, j1=len(ys))]
    for g in regs:
        for j in range(g["j0"], g["j1"]):
            sj = strap_span(M, g, xs, ys, 0, j)
            if sj is None:
                continue
            hpts[(j, g["k"])] |= {round(x, 3) for x in xs[g["i0"]:g["i1"]] if sj[0] - 1e-3 <= x <= sj[1] + 1e-3}
            hpts[(j, g["k"])] |= {round(x, 3) for x in sj}
        for i in range(g["i0"], g["i1"]):
            si = strap_span(M, g, xs, ys, 1, i)
            if si is None:
                continue
            vpts[(i, g["k"])] |= {round(y, 3) for y in ys[g["j0"]:g["j1"]] if si[0] - 1e-3 <= y <= si[1] + 1e-3}
            vpts[(i, g["k"])] |= {round(y, 3) for y in si}
    ext = {g["k"]: g for g in regs}

    def on_strap(k, axis, v, idx=None):   # the point lies on its region's strap segment (checked with --regions)
        if k is None:
            return
        g = ext[k]
        lo, hi = strap_bounds(g, xs, ys, axis) if idx is None or "strap_spans" not in M else \
            (strap_span(M, g, xs, ys, axis, idx) or (math.inf, -math.inf))
        if not lo - 1e-3 <= v <= hi + 1e-3:
            raise SystemExit(f"die_clock_mesh mesh: point {v} off region {k} strap extent [{lo}, {hi}]")
    xi = {round(x, 3): i for i, x in enumerate(xs)}
    yj = {round(y, 3): j for j, y in enumerate(ys)}
    drv_at = []
    for k, dv in M["drivers"].items():
        X, Y = round(dv["site"][0], 3), round(dv["site"][1], 3)
        rk = dv.get("region")
        if dv["strap"] == "M8":
            on_strap(rk, 0, X, dv["j"])
            hpts[(dv["j"], rk)].add(X)
            key = ("H", dv["j"], X)
        else:
            on_strap(rk, 1, Y, dv["i"])
            vpts[(dv["i"], rk)].add(Y)
            key = ("V", dv["i"], Y)
        drv_at.append((key, dv))
    stub_at = []
    for t in M["taps"]:
        L_, idx = t["strap"]
        X, Y = round(t["foot"][0], 3), round(t["foot"][1], 3)
        rk = t.get("region")
        if L_ == "M8":
            on_strap(rk, 0, X, idx)
            hpts[(idx, rk)].add(X)
            key = ("H", idx, X)
        else:
            on_strap(rk, 1, Y, idx)
            vpts[(idx, rk)].add(Y)
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
    for (j, _), pts in hpts.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire(("H", j, u), ("H", j, w), w - u, "M8")
    for (i, _), pts in vpts.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire(("V", i, u), ("V", i, w), w - u, "M9")
    via = DC.VIA_KOHM["M9"]   # M1 pin -> M8/M9 strap via stack
    # drivers: each site = m parallel BUFx24 behind one via stack; Thevenin ramp source per corner
    drv = []
    for key, dv in drv_at:
        k = node(key)
        kk = len(caps)
        jg = dv.get("jog_um", 0.0)     # island driver: perpendicular jog from the window to the strap foot
        jl = RC["M8" if dv["strap"] == "M9" else "M9"]
        caps.append(jl[1] * jg)
        edges.append((kk, k, via + jl[0] * jg))
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
    scap = {}
    if C128.enabled(M):   # 12.8 d1 plan-sized stub buffers: each stub input pin cap from its own liberty cell
        libs = C128.lib_cells(a.corner, a.libdir, sorted({t.get("stub_lib") or BUF for t in M["taps"]}))
        scap = {t["stub"]: libs[t.get("stub_lib") or BUF]["cap"] for t in M["taps"]}
    for key, t in stub_at:
        k = node(key)
        kk = len(caps)
        caps.append(scap.get(t["stub"], cin))
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
    placed = json.loads((d / "place.json").read_text())
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
    for c, port, y in cells:
        L.append(f"  {placed[c].get('lib', BUF)} {c} (.A({port or in_net[c]}), .Y({y}));")
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
def write_landed(P, raw, M, d, cycles):
    """landed_crossings.json: every abutted plan port whose src and dst partitions sit in different clock regions =
    one LANDED (forwarded-clock) crossing at the sink, + `cycles` fixed cycles each (for TOK pricing)."""
    pr = M["part_region"]
    tag = {g["k"]: g["tag"] for g in M["meta"]["regions"]}
    lane_of = {pid: ln["id"] for ln in raw.get("lanes", []) for pid in ln.get("ports", [])}
    rows, pairs = [], defaultdict(lambda: dict(ports=0, bits=0))
    for pid, p in sorted(P.ports.items()):
        a, b = p["src"]["part"], p["dst"]["part"]
        if a not in pr or b not in pr or pr[a] == pr[b]:
            continue
        rows.append(dict(port=pid, lane=lane_of.get(pid), src=a, dst=b, src_region=tag[pr[a]], dst_region=tag[pr[b]],
                         width=p.get("width"), kind=p.get("kind"), added_cycles=cycles))
        k = f"{tag[pr[a]]}->{tag[pr[b]]}"
        pairs[k]["ports"] += 1
        pairs[k]["bits"] += int(p.get("width") or 0)
    out = dict(delta_id=M["meta"].get("delta_id"), regions_depth=M["meta"]["regions_depth"],
               regions=[dict(k=g["k"], tag=g["tag"], box_um=g["box_um"],
                             parts=sum(1 for v in pr.values() if v == g["k"])) for g in M["meta"]["regions"]],
               added_cycles_per_crossing=cycles, crossings=len(rows), bits=sum(int(r["width"] or 0) for r in rows),
               lanes=len({r["lane"] for r in rows}), by_region_pair=dict(sorted(pairs.items())), ports=rows)
    (d / "landed_crossings.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("ports",)}, indent=1))
    return out


def lca(a, b):
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return a[:k]


def sink_arrivals(M, arr, corner, early_by_plan):
    """Compare equivalent sink clocks: core pins must arrive earlier by their core insertion offset.

    Add that offset back to both measured pin arrivals for pair checks.  The raw pin arrivals remain INFO.
    Plan lookup also repairs measurements made before mesh.json carried per-corner offsets.
    """
    offsets = {t["port"]: float(early_by_plan.get((t["part"], t["tap"]), {}).get(
        corner, (t.get("early_corner_ps") or {}).get(corner, t.get("early_ps", 0.0)))) for t in M["taps"]}
    return ({p: v[0] + offsets[p] for p, v in arr.items()},
            {p: v[1] + offsets[p] for p, v in arr.items()}, offsets)


def regional_qualification(M, corners, crossings):
    """A regional clock diagnostic is not evidence of implemented forwarded-clock landings."""
    reasons = []
    if M.get("unplaced") or M["meta"].get("unplaced", 0):
        reasons.append("clock cells have no legal site")
    if M["meta"].get("clock_cell_overlap_pairs", 0):
        reasons.append("clock cell bodies overlap")
    if M["meta"].get("clock_hard_keepout_violations", 0):
        reasons.append("clock cell bodies overlap hard/PHY keepouts")
    if M["meta"].get("pg_aware") and M["meta"].get("pg_feasible") is not True:
        reasons.append("PG grid is not IR-qualified")
    if set(corners) != {"TT", "FF"}:
        reasons.append("both TT and FF clock measurements are required")
    if any(c["verdict"] != "PASS" or c.get("landed_verdict") == "FAIL" for c in corners.values()):
        reasons.append("clock skew or landing window fails")
    if crossings:
        reasons.append("forwarded-clock landing implementation and token cycle pricing remain required")
    return dict(scope="regional clock diagnostic; not a die freeze gate", release_verdict="BLOCKED" if reasons else
                "CLOCK-PASS", blockers=reasons, proposed_landed_crossings=crossings)


def cmd_report(a):
    P = S.Plan(S.load(a.plan))
    d = Path(a.dir)
    M = json.loads((d / "mesh.json").read_text())
    xs, ys = M["xs"], M["ys"]
    nx, ny = len(xs), len(ys)

    def path_of(i, j):
        if M["meta"].get("clock_floorplan"):
            return floorplan_tag(i, j, M["meta"]["regions"], ny)
        return htree_tag(i, j, nx, ny)
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
    regd = M["meta"].get("regions_depth", 0)
    reg = {t["port"]: t.get("region") for t in M["taps"]}
    if regd:   # the region also follows from the tag (H-tree prefix): a stub on a foreign strap is a build bug
        tags = {g["tag"]: g["k"] for g in M["meta"]["regions"]}
        sbox = {g["k"]: g.get("strap_box_um") for g in M["meta"]["regions"]}
        foot = {t["port"]: t["foot"] for t in M["taps"]}

        def on_own_edge(p):   # --region-edge-straps: a foot ON its own region edge strap is nearest a foreign index
            b = sbox.get(reg[p])
            return bool(b) and b[0] - 1e-3 <= foot[p][0] <= b[2] + 1e-3 and b[1] - 1e-3 <= foot[p][1] <= b[3] + 1e-3
        bad = [p for p, tg in tagof.items() if tags.get(tg[:1 + regd]) != reg[p] and not on_own_edge(p)]
        if bad:
            raise SystemExit(f"die_clock_mesh report: {len(bad)} taps fed from another region's strap, e.g. {bad[:3]}")
    landed = [x for x in seam if reg[x[0]] != reg[x[1]]]
    seam_in = [x for x in seam if reg[x[0]] == reg[x[1]]]
    intra_x = [x for x in intra if reg[x[0]] != reg[x[1]]]
    crossing_table = write_landed(P, S.load(a.plan), M, d, a.landing_cycles) if regd else None
    if intra_x:
        raise SystemExit(f"die_clock_mesh report: {len(intra_x)} intra-partition pairs straddle a region seam")
    for corner in [c for c in a.corner if (d / f"taps_{c}.txt").exists()]:
        _, N = read_tree(d / f"tree_{corner}.txt")
        rng = {"h": 0.0}
        for name, (late, early, _) in N.items():
            m_ = re.match(r"ckm_n\d+_(h[0-9]?[01]*)$", name)
            if m_:
                rng[m_.group(1)] = late - early
        if "ckm_n0" in N:
            rng["h"] = N["ckm_n0"][0] - N["ckm_n0"][1]
        arr = {}
        for line in open(d / f"taps_{corner}.txt"):
            f = line.split()
            arr[f[1]] = (float(f[2]), float(f[3]), float(f[4]))   # T port late early slew
        raw_late = {p: v[0] for p, v in arr.items()}
        if C128.enabled(M):   # 12.8d: raw arrivals, no early-offset add-back; offset taps FAIL in the gate below
            late, early, core_offsets = ({p: v[0] for p, v in arr.items()}, {p: v[1] for p, v in arr.items()},
                                         {t["port"]: 0.0 for t in M["taps"]})
        else:
            late, early, core_offsets = sink_arrivals(M, arr, corner, DC.plan_tap_early(P))
        slew = {p: v[2] for p, v in arr.items()}

        def dmg(pa, pb):
            # A region mesh mixes every driver in its subtree. A nearby driver is not a common clock path:
            # only the region root is shared by ALL contributors (D-INFRA-FIRST regional-clock contract).
            c = M["meta"]["regions"][reg[pa]]["tag"] if regd else "h"
            while c not in rng and len(c) > 1:
                c = c[:-1]
            return DC.pair_clock_damage(late[pa], early[pa], late[pb], early[pb], rng.get(c, 0.0))["max_damage_ps"]
        sk = [dmg(x[0], x[1]) for x in seam_in]
        ik = [dmg(x[0], x[1]) for x in intra]
        worst = sorted(((dmg(x[0], x[1]), x[0], x[1]) for x in list(seam_in) + [(i[0], i[1]) for i in intra]),
                       reverse=True)[:10]
        # landed seams: the region-to-region clock offset at the landing (no CPPR above the root; nominal pair offset
        # and early/late damage both reported) against the landing window
        lk = [(DC.pair_clock_damage(late[x[0]], early[x[0]], late[x[1]], early[x[1]], rng.get("h", 0.0))["max_damage_ps"],
               abs(late[x[0]] - late[x[1]]), x) for x in landed]
        Mz = json.loads((d / f"mesh_{corner}.json").read_text())
        _, Nn = read_tree(d / f"tree_{corner}.txt")
        rep["corners"][corner] = dict(
            insertion_ps=[round(min(raw_late.values()), 2), round(max(raw_late.values()), 2)],
            tap_skew_ps=round(max(raw_late.values()) - min(raw_late.values()), 2),
            compensated_sink_insertion_ps=[round(min(late.values()), 2), round(max(late.values()), 2)],
            core_offset_taps=sum(v != 0.0 for v in core_offsets.values()),
            seam_pairs=len(sk), seam_max_ps=round(max(sk), 2), seam_p99_ps=round(DC.pctl(sk, .99), 2),
            intra_pairs=len(ik), intra_max_ps=round(max(ik), 2), pairs_over_80=sum(1 for v in sk + ik if v > 80),
            related_pair_max_ps=round(max(sk + ik), 2), gate_ps=DC.GATE_PS,
            **(dict(regions=len(M["meta"]["regions"]), landed_seam_pairs=len(lk),
                    landed_damage_max_ps=round(max([v[0] for v in lk] or [0]), 2),
                    landed_nominal_offset_max_ps=round(max([v[1] for v in lk] or [0]), 2),
                    landing_budget_ps=a.landing_budget_ps,
                    landed_verdict="PASS" if max([v[0] for v in lk] or [0]) <= a.landing_budget_ps else "FAIL",
                    landed_worst=[[round(v[0], 2), v[2][0], v[2][1], v[2][2]] for v in sorted(lk, key=lambda z: -z[0])[:10]])
               if regd else {}),
            verdict="PASS" if max(sk + ik) <= DC.GATE_PS else "FAIL",
            tap_slew_max_ps=round(max(slew.values()), 2), mesh_stub_in_slew_max_ps=Mz["stub_in_slew_max_ps"],
            tree_slew_max_ps=round(max(v[2] for v in Nn.values()), 2), mesh_cap_pF=Mz["mesh_cap_pF"],
            worst=[[round(w, 2), x, y] for w, x, y in worst])
        if C128.enabled(M):
            Dt, _ = read_tree(d / f"tree_{corner}.txt")
            g12 = C128.gate(M, P, [(x[0], x[1]) for x in seam_in] + [(i[0], i[1]) for i in intra], late, early, rng, regd, Mz["stubs"], Dt,
                            M.get("rule_12_8", {}).get("early_offset_taps", []))
            r_ = rep["corners"][corner]
            r_.update(related_pair_max_ps=g12["related_pair_max_ps"], pairs_over_80=g12["pairs_over_80"],
                      verdict=g12["verdict"], rule_12_8=g12)
            r_.pop("compensated_sink_insertion_ps", None)
    # clock power: C V^2 f over every die clock wire + pin (mesh from the transient, tree/stub wire from length)
    nd = NDR[M["meta"]["ndr"]]
    cw = (DC.LAYER_RC["M8"][1] + DC.LAYER_RC["M9"][1]) / 2 * nd["cf"]
    ncell = M["meta"]["cells"]
    for corner, r in rep["corners"].items():
        c_tot = r["mesh_cap_pF"] + (M["meta"]["htree_wire_mm"] + M["meta"]["stub_wire_mm"]) * 1e3 * cw / 1e3 \
            + ncell * DC.BUF_CIN_FF / 1e3 + len(M["taps"]) * DC.TAP_LOAD_FF / 1e3
        r["clock_switched_cap_pF"] = round(c_tot, 1)
        r["clock_wire_power_W"] = round(c_tot * 1e-12 * VDD[corner] ** 2 / (DC.PERIOD_PS * 1e-12), 3)
    if regd or M["meta"].get("pg_aware"):
        rep["qualification"] = regional_qualification(M, rep["corners"], crossing_table["crossings"] if crossing_table else 0)
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
    for g in M["meta"].get("regions") or [dict(i0=0, i1=len(xs), j0=0, j1=len(ys))]:
        rx, ry = xs[g["i0"]:g["i1"]], ys[g["j0"]:g["j1"]]
        for j, y in zip(range(g["j0"], g["j1"]), ry):
            sj = strap_span(M, g, xs, ys, 0, j)
            if sj:
                ax.plot(sj, [y, y], color="tab:blue", lw=0.25)
        for i, x in zip(range(g["i0"], g["i1"]), rx):
            si = strap_span(M, g, xs, ys, 1, i)
            if si:
                ax.plot([x, x], si, color="tab:blue", lw=0.25)
        if "box_um" in g:
            b = g["box_um"]
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, lw=1.2, ec="tab:purple", ls="--"))
            ax.text(b[0] + 150, b[3] - 600, g["tag"], fontsize=6, color="tab:purple")
    for h in M["meta"].get("macro_holes", []):
        r = h["rect_um"]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, lw=1.0, ec="tab:brown", hatch="//"))
    hd = M.get("hole_drivers", [])
    if hd:
        ax.scatter([xs[v[0]] for v in hd], [ys[v[1]] for v in hd], s=2.0, c="tab:brown", marker="x", lw=0.4)
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
    b.add_argument("--regions", type=int, default=0,
                   help="D > 0: 2^D clock regions (H-tree subtrees below level D), one mesh each, LANDED seams")
    b.add_argument("--region-edge-straps", action="store_true",
                   help="extend regional metal to its geometric box with an NDR gap, opening legal edge driver islands")
    b.add_argument("--reserve-cell-sites", action="store_true",
                   help="reserve every clock cell body while searching later sites; prevent overlapping clock cells")
    b.add_argument("--pg-json", help="actual IR-sized PG file; consumes die_infra.pg_rects geometry (trial-only if infeasible)")
    b.add_argument("--track-file", help="actual die kit grt/tracks.tcl, required with --pg-json")
    b.add_argument("--delta-id", help="plan delta tag recorded in mesh.json meta (e.g. D-QC-CLKMESH)")
    b.add_argument("--rule-12-8", action="store_true",
                   help="METHODOLOGY v4.1 12.8: plan-model stub sizing (d1), early-offset taps FAIL, no measured "
                        "balance, fixed VSS-shielded tree pre-routes, CPPR at the last common tree node")
    b.add_argument("--libdir", default=str(Path("~/.cache/opentallas/asap7_nldm").expanduser()),
                   help="liberty dir for the 12.8 plan sizing model")
    b.add_argument("--tap-slew-max-ps", type=float, default=C128.TAP_SLEW_MAX_PS)
    b.add_argument("--clock-floorplan", help="opt-in JSON: x_cuts_um (region seams on partition edges) + region_nx "
                   "(power-of-two columns per region), macro_holes (part names / {name, rect_um}: straps stop at the "
                   "macro edge, no cells inside, dead branches pruned), hard_core_drivers='drop' (cores <= M7 under the "
                   "mesh: an intersection with no legal site is driverless; the core tree is its declared tap latency), "
                   "io_macro_drivers='drop' (same for die PHY io macros; straps crossing them are reported)")
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
    c.add_argument("--plan", help="pinned physical plan for the all-clock-cell hard-keepout census")
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
    r.add_argument("--landing-cycles", type=int, default=2,
                   help="fixed cycles a LANDED crossing adds (forwarded-clock land + local-clock read), --regions only")
    r.add_argument("--landing-budget-ps", type=float, default=DC.PERIOD_PS / 2,
                   help="landing window for the region-to-region clock offset at a landed seam, --regions only")
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
