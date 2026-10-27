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


def split_axis(ni, nj, level, axes=""):
    axis = (0 if axes[level] == "x" else 1) if level < len(axes) else (0 if ni >= nj and ni > 1 else 1)
    if (ni if axis == 0 else nj) <= 1:
        raise ValueError("clock-region split profile exceeds the intersection grid")
    return axis


def htree_tag(i, j, nx, ny, axes=""):
    """H-tree tag ('h' + one bit per level) of intersection (i, j): replay the build's index bisection."""
    i0, i1, j0, j1, tag = 0, nx, 0, ny, "h"
    while (i1 - i0) * (j1 - j0) > 1:
        ni, nj = i1 - i0, j1 - j0
        if split_axis(ni, nj, len(tag) - 1, axes) == 0:
            h = (i0 + i1) // 2
            c = int(i >= h)
            i0, i1 = (i0, h) if not c else (h, i1)
        else:
            h = (j0 + j1) // 2
            c = int(j >= h)
            j0, j1 = (j0, h) if not c else (h, j1)
        tag += str(c)
    return tag


def region_boxes(nx, ny, depth, W=None, H=None, axes="", x_edges=None, y_edges=None):
    """the 2^depth clock regions = the H-tree subtrees below level `depth`, in index space [i0, i1) x [j0, j1)
    (same bisection as the build), each with its geometric box (cut half-way between straps) when W, H are given."""
    regs = [("h", 0, nx, 0, ny)]
    for level in range(depth):
        nxt = []
        for tag, i0, i1, j0, j1 in regs:
            ni, nj = i1 - i0, j1 - j0
            if ni * nj <= 1:
                raise ValueError(f"--regions {depth} deeper than the {nx}x{ny} mesh")
            if split_axis(ni, nj, level, axes) == 0:
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
            r["box_um"] = [round(x_edges[i0] if x_edges is not None else i0 * px, 3),
                           round(y_edges[j0] if y_edges is not None else j0 * py, 3),
                           round(x_edges[i1] if x_edges is not None else i1 * px, 3),
                           round(y_edges[j1] if y_edges is not None else j1 * py, 3)]
        out.append(r)
    return out


def cohort_axis_grid(n, span, cuts, count):
    """Keep a power-of-two driver count per cohort while placing physical cuts on real dataflow seams."""
    edges = [0.] + list(map(float, cuts)) + [float(span)]
    if len(edges) != 2**count + 1 or any(b <= a for a, b in zip(edges, edges[1:])) or n % (len(edges)-1):
        raise ValueError("clock cohort cuts must be ordered internal seams matching the split-axis profile")
    each = n // (len(edges) - 1)
    grid = [a + (i + .5) * (b-a)/each for a, b in zip(edges, edges[1:]) for i in range(each)]
    cell_edges = [a + i * (b-a)/each for a, b in zip(edges, edges[1:]) for i in range(each)] + [float(span)]
    return grid, cell_edges


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


def split_long(cells, nets, K, taps_xy, hop_max, cell, out=None, yfirst=False, both_l=False):
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
            for orient in ("xy", "yx") if (both_l or yfirst) else ("xy",):
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


def uniform_region_boxes(xs, ys, W, H, spec):
    """--uniform-regions (CLOCK-KV-R2, opt-in): clock regions = strap boxes cut at the declared dataflow seams
    (x_cuts_um / y_cuts_um, partition edges) on the UNIFORM die lattice xs/ys.  The H-tree stays the plain index
    bisection of the whole nx x ny grid (equal-length by construction, independent of the cuts); a region is only a
    mesh (its own straps, special net ck_mesh_r<k>, landed seams to its neighbours).  The region's CPPR node is the
    lowest common H-tree node of ALL its intersections (htree_tag common prefix): the mesh shorts every driver of
    the region, so no lower node is common to its taps.  Intersection (i, j) belongs to the box holding (xs[i], ys[j])."""
    def intervals(cuts, span, vals, axis):
        e = [0.0] + [float(c) for c in cuts] + [float(span)]
        if any(b <= a for a, b in zip(e, e[1:])):
            raise ValueError(f"--uniform-regions: {axis}_cuts_um must be ordered internal seams")
        out = []
        for a, b in zip(e, e[1:]):
            idx = [k for k, v in enumerate(vals) if a <= v < b or (b == float(span) and v == b)]
            if not idx:
                raise ValueError(f"--uniform-regions: {axis} interval [{a}, {b}] holds no lattice line (pitch too coarse)")
            out.append((a, b, idx[0], idx[-1] + 1))
        return out
    nx, ny = len(xs), len(ys)
    R = []
    for ya, yb, j0, j1 in intervals(spec.get("y_cuts_um", []), H, ys, "y"):
        for xa, xb, i0, i1 in intervals(spec.get("x_cuts_um", []), W, xs, "x"):
            tags = [htree_tag(i, j, nx, ny) for i in range(i0, i1) for j in range(j0, j1)]
            lca = tags[0]
            for t in tags[1:]:
                k = 0
                while k < min(len(lca), len(t)) and lca[k] == t[k]:
                    k += 1
                lca = lca[:k]
            R.append(dict(k=len(R), tag=lca, i0=i0, i1=i1, j0=j0, j1=j1,
                          box_um=[round(xa, 3), round(ya, 3), round(xb, 3), round(yb, 3)]))
    if len(R) > 1 and any(g["i1"] - g["i0"] < 2 or g["j1"] - g["j0"] < 2 for g in R):
        raise ValueError("--uniform-regions: every region needs >= 2 x 2 intersections (a mesh)")
    return R


def uniform_region_gate(P, R, taps, reach_um=750.0):
    """--uniform-regions plan gate: every partition lies wholly in one region box and each of its taps reaches a
    strap of its OWN region within the clock reach (stub foot distance); a cut that strands a partition (the
    u32x64r3 plan error: t_sys_c clk_t11 1431 um) is a structural FAIL, never a slide into a foreign region."""
    strad, far = [], []
    for n in P.parts:
        r = P.rect(n)
        if not any(g["box_um"][0] - 1e-3 <= r[0] and r[2] <= g["box_um"][2] + 1e-3 and
                   g["box_um"][1] - 1e-3 <= r[1] and r[3] <= g["box_um"][3] + 1e-3 for g in R):
            strad.append(n)
    for t in taps:
        if t["stub_um"] < 0 or t["stub_um"] + BUF_W + ROW_Y > reach_um:
            far.append([t["port"], t.get("region"), t["stub_um"]])
    return dict(verdict="PASS" if not strad and not far else "FAIL", reach_um=reach_um, straddling_parts=strad,
                stubs_beyond_reach=far, max_stub_um=round(max((t["stub_um"] for t in taps), default=0.0), 2),
                regions=[dict(k=g["k"], tag=g["tag"], box_um=g["box_um"], i=[g["i0"], g["i1"]], j=[g["j0"], g["j1"]])
                         for g in R])


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
          region_spec=None, trunk_repeaters=False, driver_pair_span_um=0.0, split_yfirst=False, floorplan=None,
          rule128=None, plan_sites=None, uniform_regions=None, lattice=None):
    """opt-in PATH-KV 10-26 site fixes (defaults keep the prior QC/S81 builds unchanged): trunk_repeaters = equal-cut
    BUFx24 repeaters on a root->ckm_n0 trunk > 750 um; driver_pair_span_um > 0 = a leaf driver pair whose nearest sites
    span more than this takes the shortest-span candidate combination; split_yfirst = split_long also tries the y-first L.
    floorplan (--clock-floorplan, CLOCK-2) / rule128 (--rule-12-8, CLOCK-128 METHODOLOGY 12.8): opt-in.
    plan_sites (--plan-sites, CLOCK-128-R2, 12.8 only): ot_clock_sites/1 reserved lattice island sites (12.2a1 pushdown
    cells from the master-plan slices).  Every mesh driver, tree node, leg / trunk repeater and the tree root then sits
    on its plan site; the only allowed move is the PG-track snap (C128.SITE_SNAP_UM); anything farther is a plan
    error (no slide, no free-site search).  Under 12.8 dead branches are pruned by construction and every unplaced /
    off-site cell or loadless net is a plan error: the build raises C128.PlanError unless rule128["allow_plan_errors"]
    (diagnostic only; the report then never qualifies)."""
    # lattice (--lattice-spec, CLOCK-KV-R3, opt-in, METHODOLOGY 12.8e/12.8e1 continuous mesh): explicit strap rows
    # ys_um (commensurate pitch, any count) of ONE continuous die mesh; mesh drivers (global-tree leaves) only on the
    # declared driver_rows (a power-of-two count); tree = index bisection over the driver rows in the declared split
    # order `axes` (y-first keeps the upper levels on the single-instance centre column), equal by construction when
    # the driver rows are mirror-symmetric.  Rows not in driver_rows are driverless mesh straps (fed by the mesh).
    jm = None
    if lattice is not None:
        if regions or region_spec is not None or floorplan is not None or uniform_regions is not None:
            raise ValueError("--lattice-spec is one continuous mesh: no --regions/--region-spec/--clock-floorplan/"
                             "--uniform-regions")
        jm = [int(k) for k in lattice["driver_rows"]]
        if not pow2(len(jm)) or jm != sorted(set(jm)) or jm[-1] >= len(lattice["ys_um"]):
            raise ValueError("--lattice-spec driver_rows: sorted unique strap-row indices, power-of-two count")
        ny = len(lattice["ys_um"])
    assert pow2(nx) and (jm is not None or pow2(ny)), "nx, ny must be powers of two (complete H-tree)"
    SI, perr = None, []
    if plan_sites is not None:
        if rule128 is None:
            raise ValueError("--plan-sites needs the METHODOLOGY 12.8 build")
        if leg_mode != "slide":
            raise ValueError("--plan-sites places leg repeaters at plan sites: use --leg slide")
        SI = C128.SiteIndex(plan_sites["sites"], plan_sites.get("snap_um", C128.SITE_SNAP_UM))
    pg_mm = SI.snap if SI is not None else max_move

    def on_site(p, name, role):
        """plan site of the lattice point p (SI mode): (xy, move_um, site) or (p, -1, None) + a plan error."""
        st, d, err = SI.take(p, name)
        if st is None:
            perr.append(dict(err, name=name, role=role))
            return tuple(p), -1.0, None
        return tuple(st["xy_um"]), d, st
    W, H = float(P.W), float(P.H)
    ko = DC.keepouts(P)
    if sites == "channel":   # every die clock cell outside all partitions (channels only; no tile outline change)
        ko = list(ko) + [P.rect(n) for n in P.parts]
    K = DC.KeepIndex(ko, die=(W, H))
    xs = [(i + 0.5) * W / nx for i in range(nx)]
    ys = [(j + 0.5) * H / ny for j in range(ny)]
    axes, x_edges, y_edges = "", None, None
    if jm is not None:
        ys = [float(v) for v in lattice["ys_um"]]
        axes = str(lattice.get("axes", "")).lower()
    drv_rows = set(jm) if jm is not None else set(range(ny))
    nty = len(jm) if jm is not None else ny          # tree index rows
    jt = jm if jm is not None else list(range(ny))   # tree row index -> strap row index
    if region_spec is not None:
        axes = region_spec["split_axes"].lower()
        if not axes or set(axes) - {"x", "y"} or regions not in (0, len(axes)):
            raise ValueError("region-spec split_axes must match --regions and contain only x/y")
        regions = len(axes)
        xs, x_edges = cohort_axis_grid(nx, W, region_spec.get("x_cuts_um", []), axes.count("x"))
        ys, y_edges = cohort_axis_grid(ny, H, region_spec.get("y_cuts_um", []), axes.count("y"))
    if uniform_regions is not None and (regions or region_spec is not None or floorplan is not None):
        raise ValueError("--uniform-regions declares its own regions on the uniform lattice; do not combine with "
                         "--regions/--region-spec/--clock-floorplan")
    fp = floorplan
    if fp is not None:
        if regions or region_spec is not None:
            raise ValueError("--clock-floorplan declares its own regions; do not combine with --regions/--region-spec")
        xs, R_fp = floorplan_regions(fp, W, H, ny)
        nx = len(xs)
        holes, cores = floorplan_holes(P, fp)
        islands = floorplan_islands(P, fp)
    axis_snap = None
    # CLOCK-128 shield lane: a shielded strap's footprint is clock metal + both VSS shields (C128.shield_geom), so the
    # PG-free track test clears the shields, not only the clock metal, from every parallel PG stripe
    # When the die PG grid on a layer is too dense for drawn stripes (KV M9: 0.48 um every 0.864 um), the strap sits
    # in a PG gap and the two neighbouring PG stripes are its shields (C128.FLANK, checked for every strap below).
    shielded = rule128 is not None or bool((fp or {}).get("shield_net"))
    shield_foot = C128.shield_geom(NDR[ndr])[2] if shielded else NDR[ndr]["width"] / 2
    strap_mode = {}
    if pg_shapes is not None:
        if track_profile is None:
            raise ValueError("PG-aware mesh requires the actual die-kit routing tracks")
        old_xs, old_ys = xs, ys

        def axis(v, layer, ax, span):
            if shielded:
                try:
                    r_ = pg_free_axis(v, pg_shapes, layer, ax, span, track_profile[layer], shield_foot, NDR[ndr]["space"],
                                      pg_mm)
                    strap_mode[layer] = C128.DRAWN
                    return r_
                except ValueError:
                    strap_mode[layer] = C128.FLANK
            return pg_free_axis(v, pg_shapes, layer, ax, span, track_profile[layer], NDR[ndr]["width"] / 2,
                                NDR[ndr]["space"], pg_mm)
        try:
            xs = axis(xs, "M9", 0, W)
            ys = axis(ys, "M8", 1, H)
        except ValueError as e:
            if SI is None:
                raise
            raise C128.PlanError([dict(kind="pg_snap", name="mesh axis", detail=str(e))])
        axis_snap = dict(M9=round(max(abs(x-y) for x, y in zip(xs, old_xs)), 6),
                         M8=round(max(abs(x-y) for x, y in zip(ys, old_ys)), 6))
    cells, nets, ports = {}, [], [("input", "root")]
    out = dict(meta=dict(nx=nx, ny=ny, m=m, rep_um=rep_um, ndr=ndr, sites=sites, W=W, H=H, pitch_um=[W / nx, H / ny]),
               xs=xs, ys=ys, drivers={}, htree=[], stubs=[], unplaced=[])
    if axis_snap is not None:
        out["meta"].update(pg_aware=True, pg_tracks=track_profile, pg_axis_snap_max_um=axis_snap)
    if strap_mode:
        out["meta"]["strap_shield"] = strap_mode
    import gen_phys as GP
    out["meta"]["tap_layer"] = P.layer_budget["partition_signal_max"]
    out["meta"]["tap_pin_size_um"] = [GP.LAYER_W.get(out["meta"]["tap_layer"], .04), 4 * GP.PIN_LEN_UM]
    if region_spec is not None:
        out["meta"].update(region_spec=region_spec, region_axes=axes)
    if jm is not None:
        out["meta"].update(lattice_spec=dict(lattice, ys_um=None, rows=len(ys)), tree_axes=axes,
                           driverless_rows=[j for j in range(len(ys)) if j not in drv_rows])
    if delta_id:
        out["meta"]["delta_id"] = delta_id
    if fp is not None:
        R, regions = R_fp, 1
        out["meta"].update(clock_floorplan=fp, macro_holes=holes, driverless_hard_cores=len(cores))
    elif uniform_regions is not None:
        R = uniform_region_boxes(xs, ys, W, H, uniform_regions)
        regions = len(R)
        out["meta"].update(uniform_regions=uniform_regions)
    else:
        R = region_boxes(nx, ny, regions, W, H, axes, x_edges, y_edges)
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
    # PATH-KV 10-26: candidates on both straps first; a leaf pair (i, 2k)/(i, 2k+1) whose nearest sites land on
    # opposite sides of a PHY/hard macro (pair span > 700 um, i.e. past the 750-um clock reach) takes the candidate combination with the shortest pair
    # span instead, so the leaf node can reach both drivers around the macro.
    if SI is None:
        cand = {}
        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                if j not in drv_rows:
                    continue
                g = R[reg_ij[(i, j)]]
                cs = []
                if fp is not None:
                    mh = next((h["name"] for h in holes if in_rect(h["rect_um"], x, y)), None)
                    if mh is not None:
                        out["hole_drivers"].append([i, j, "macro_hole", mh])
                        cand[(i, j)] = None
                        continue
                for axis in (0, 1):
                    bnd = strap_bounds(g, xs, ys, axis) if fp is None else span(axis, j if axis == 0 else i, g)
                    if bnd is None:
                        continue
                    q, d = free_along(K, (x, y), axis, max_move, bounds=bnd if regions else None)
                    if q is not None:
                        cs.append((q, d, axis))
                cand[(i, j)] = sorted(cs, key=lambda c: c[1])
        pick = {k: (v[0] if v else None) for k, v in cand.items()}
        pair_fix = []
        for (i, j), v in cand.items():
            if j % 2 or not v or not cand.get((i, j + 1)):
                continue
            a, b = pick[(i, j)], pick[(i, j + 1)]
            pspan = lambda p, q: abs(p[0][0] - q[0][0]) + abs(p[0][1] - q[0][1])
            if driver_pair_span_um > 0 and pspan(a, b) > driver_pair_span_um:
                combo = min(((p, q) for p in v for q in cand[(i, j + 1)]), key=lambda pq: (pspan(*pq), pq[0][1] + pq[1][1]))
                pick[(i, j)], pick[(i, j + 1)] = combo
                pair_fix.append([i, j, round(pspan(a, b), 1), round(pspan(*combo), 1)])
        out["meta"]["driver_pair_fixes"] = pair_fix
        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                if j not in drv_rows:
                    continue
                g = R[reg_ij[(i, j)]]
                rk = dict(region=g["k"]) if regions else {}
                if cand[(i, j)] is None:      # --clock-floorplan macro hole: driverless, recorded in pass 1
                    continue
                best = pick[(i, j)]
                if best is not None and hitf(K, best[0]):   # an earlier driver reserved this site: fall back to a fresh search
                    best = None
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
    else:   # CLOCK-128-R2: every mesh driver on its reserved plan site (pushdown island), move <= PG snap only
        out["meta"]["driver_pair_fixes"] = []
        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                if j not in drv_rows:
                    continue
                g = R[reg_ij[(i, j)]]
                rk = dict(region=g["k"]) if regions else {}
                if fp is not None:
                    mh = next((h["name"] for h in holes if in_rect(h["rect_um"], x, y)), None)
                    if mh is not None:
                        out["hole_drivers"].append([i, j, "macro_hole", mh])
                        continue
                (cx, cy), d, st = on_site((x, y), f"ckm_d_{i}_{j}", "mesh_driver")
                if st is None:
                    continue
                names = [cell(f"ckm_d_{i}_{j}_{k}", cx + (k - (m - 1) / 2) * BUF_W, cy, "drv", i=i, j=j, **rk)
                         for k in range(m)]
                out["drivers"][f"{i}_{j}"] = dict(i=i, j=j, ideal=[x, y], site=[round(cx, 4), round(y, 4)],
                                                  cell_site=[round(cx, 4), round(cy, 4)], move_um=round(d, 4),
                                                  jog_um=round(abs(cy - y), 4), strap="M8", plan_site=st["name"],
                                                  pushdown={k: st.get(k) for k in ("inst", "island", "role")},
                                                  cells=names, **rk)
    # --- H-tree over index ranges
    nid = [0]

    def node_xy(i0, i1, j0, j1):
        if region_spec is not None:
            # Mean children give equal sibling leg lengths even for unequal physical cohort widths.
            return (sum(xs[i0:i1])/(i1-i0), sum(ys[j0:j1])/(j1-j0))
        return ((xs[i0] + xs[i1 - 1]) / 2, (ys[jt[j0]] + ys[jt[j1 - 1]]) / 2)

    def live(i0, i1, j0, j1):
        return any(f"{i}_{jt[j]}" in out["drivers"] for i in range(i0, i1) for j in range(j0, j1))

    def rec(i0, i1, j0, j1, level, drv_cell, path, kids=None, here=None):
        """drv_cell drives the branch point of this region (already at node_xy).  kids/here (--clock-floorplan
        root only): the region boxes driven from the die root point."""
        ni, nj = i1 - i0, j1 - j0
        if ni == 1 and nj == 1:
            raise AssertionError
        ax = split_axis(ni, nj, level, axes)
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
            if (fp is not None or rule128 is not None) and not live(*kr):
                # dead branch (every driver below sits in a declared hole, or is a plan error): pruned by
                # construction, so no loadless tree net exists (CLOCK-128-R2)
                out.setdefault("pruned_branches", []).append(f"{path}{c}")
                continue
            kp = node_xy(*kr)
            L = abs(kp[0] - here[0]) + abs(kp[1] - here[1])
            n_seg = max(1, math.ceil(L / rep_um - 1e-9))
            tag = f"{path}{c}"
            leaf = (kr[1] - kr[0]) * (kr[3] - kr[2]) == 1
            if leaf:
                assert n_seg == 1, f"leaf leg {L:.0f} um > rep_um: use a finer mesh"
                d = out["drivers"].get(f"{kr[0]}_{jt[kr[2]]}")
                loads += d["cells"] if d else []
                out["htree"].append(dict(level=level + 1, tag=tag, a=list(here), b=list(kp), len_um=round(L, 2),
                                         n_seg=1, reps=[], leaf=True))
                continue
            # internal child: node buffer on the incoming leg, upstream of the branch point when on a keep-out
            node_site = None
            if SI is not None:
                q, d, node_site = on_site(kp, f"ckm_n{level + 1}_{tag}", "tree_node")
            else:
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
                    if SI is not None:
                        rq, rd, _ = on_site(p, f"ckm_r{level + 1}_{tag}_{k}", "leg_rep")
                        pts.append((rq, rd))
                        continue
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
                                     n_seg=n_seg, reps=reps, node=nb, node_move_um=round(d, 2), leaf=False,
                                     **(dict(plan_site=node_site["name"]) if node_site else {})))
            rec(*kr, level + 1, nb, tag)
        nets.append(dict(name=f"ckm_w_{drv_cell}" if not drv_cell.startswith("port:") else "root",
                         drv=drv_cell, loads=loads, level=level))

    c0 = node_xy(0, nx, 0, nty)
    sp = P.clock.get("spine", {}) or {}
    root = tuple(sp.get("die_root_um") or sp.get("root_um") or c0)
    if pg_shapes is not None:
        planned_root = root
        # The actual die input is on M9; placing it on the old grid centre can short a newly sized PG rail.
        root = (pg_free_axis([root[0]], pg_shapes, "M9", 0, W, track_profile["M9"],
                             shield_foot if strap_mode.get("M9", C128.DRAWN) == C128.DRAWN else NDR[ndr]["width"] / 2,
                             NDR[ndr]["space"], max_move)[0], root[1])
        out["meta"].update(root_plan_um=list(planned_root), root_pg_shift_um=round(abs(root[0]-planned_root[0]), 6))
    if fp is not None:
        c0 = root      # the die root drives one tree per explicit region: no trunk
    if SI is not None:
        q, d, _ = on_site(c0, "ckm_n0", "tree_root")
    else:
        q, d = free_along(K, c0, 0, 2 * rep_um)
        if q is None:
            q, d = free_near(K, c0, limit=max(W, H))
        if q is None:
            q = c0
            out["unplaced"].append(["root", "node"])
    n0 = cell("ckm_n0", q[0], q[1], "node", level=0)
    trunk = abs(root[0] - q[0]) + abs(root[1] - q[1])
    # Trunk repeaters (PATH-KV 10-26): a cohort tree centre that is not the die input point gets equal-cut BUFx24
    # repeaters on the L path root -> ckm_n0 (x first, then y), each at the nearest free site.  The trunk is
    # upstream of ckm_n0, so it is common to every pair (no skew effect); it only keeps every hop <= rep_um.
    trunk_reps = []
    n_tr = max(1, math.ceil(trunk / rep_um - 1e-9))
    if trunk_repeaters and trunk + BUF_W + ROW_Y > 750.0:
        ax_len = abs(q[0] - root[0])
        for k in range(1, n_tr):
            s_ = trunk * k / n_tr
            if s_ <= ax_len:
                p = (root[0] + math.copysign(s_, q[0] - root[0]), root[1])
            else:
                p = (q[0], root[1] + math.copysign(s_ - ax_len, q[1] - root[1]))
            if SI is not None:
                rq, rd, _ = on_site(p, f"ckm_t_{k}", "trunk_rep")
            else:
                rq, rd = free_near(K, p, limit=rep_um / 2)
            if rq is None:
                out["unplaced"].append(["root", f"trunk repeater {k} has no free site", round(s_, 1)])
                rq = p
            trunk_reps.append(cell(f"ckm_t_{k}", rq[0], rq[1], "rep", level=0))
    if region_spec is not None and (trunk / n_tr if trunk_repeaters else trunk) + BUF_W + ROW_Y > 750.0:
        out["unplaced"].append(["root", "STRUCTURAL root-to-tree span exceeds 750 um", round(trunk, 3)])
    out["meta"]["root_um"] = list(root)
    if fp is not None:
        out["meta"].update(nx=nx, pitch_um=[max((g["box_um"][2] - g["box_um"][0]) / (g["i1"] - g["i0"]) for g in R),
                                            H / ny], hole_drivers=len(out["hole_drivers"]))
    out["meta"]["trunk_um"] = round(trunk, 2)
    # DECLARED meta-only change (PATH-KV 10-26, COORD-REVIEW-20): trunk_um is now measured from the die root to the
    # PLACED ckm_n0 site (q), not to the grid centre c0 as before; the old figure is kept as trunk_um_c0. No geometry,
    # net or timing change in a default build (ckm_n0 was always placed at q).
    out["meta"]["trunk_um_basis"] = "root->placed ckm_n0 site"
    out["meta"]["trunk_um_c0"] = round(abs(root[0] - c0[0]) + abs(root[1] - c0[1]), 2)
    out["meta"]["trunk_reps"] = len(trunk_reps)
    chain = trunk_reps + [n0]
    nets.append(dict(name="root", drv="port:root", loads=[chain[0]], level=-1))
    for a_, b_ in zip(chain, chain[1:]):
        nets.append(dict(name=f"ckm_w_{a_}", drv=a_, loads=[b_], level=-1))
    if fp is not None:
        rec(0, nx, 0, ny, 0, n0, "h", kids=[(g["i0"], g["i1"], g["j0"], g["j1"]) for g in R], here=c0)
    else:
        rec(0, nx, 0, nty, 0, n0, "h")
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
        tap_rows.append(dict(part=part, tap=port, port=tp, xy=[x, y], layer=out["meta"]["tap_layer"], early_ps=early,
                             early_corner_ps=early_c.get((part, port)), stub=sb, **rk, foot=[round(fq[0], 3),
                             round(fq[1], 3)], strap=("M8", j) if axis == 0 else ("M9", i), slide_um=round(fd, 2),
                             stub_um=round(abs(fq[0] - x) + abs(fq[1] - y), 2)))
    out["taps"] = tap_rows
    if uniform_regions is not None:
        ug = uniform_region_gate(P, R, tap_rows)
        out["meta"]["uniform_regions_gate"] = ug
        if ug["verdict"] != "PASS":
            out["unplaced"] += [[n, "STRUCTURAL partition straddles a uniform-regions cut"] for n in ug["straddling_parts"]]
            out["unplaced"] += [[p, "STRUCTURAL tap beyond clock reach of its own region strap", d]
                                for p, _, d in ug["stubs_beyond_reach"]]
    if hop_max:
        out["meta"]["split_reps"] = split_long(cells, nets, K, {t["port"]: tuple(t["xy"]) for t in tap_rows}, hop_max,
                                               cell, out, yfirst=split_yfirst, both_l=fp is not None)
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
    if fp is None and out.get("pruned_branches"):
        out["meta"]["pruned_branches"] = len(out["pruned_branches"])
    if SI is not None:
        out["meta"]["plan_sites"] = dict(snap_um=SI.snap, sites=len(SI.sites), used=len(SI.used),
                                         source=plan_sites.get("source"), sha256=plan_sites.get("sha256"))
    if rule128 is not None:   # CLOCK-128-R2: fail closed -- unplaced / off-site cells and loadless nets are plan errors
        def uname(u):
            if len(u) == 2 and all(isinstance(v, int) for v in u):
                return f"ckm_d_{u[0]}_{u[1]}", "mesh_driver"
            return ":".join(str(v) for v in u[:2]), "tree"
        rows = [dict(kind="unplaced", name=uname(u)[0], role=uname(u)[1], detail=u) for u in out["unplaced"]] + perr
        rows += [dict(kind="empty_tree_net", name=n["name"], detail="tree net without loads") for n in nets
                 if not n["loads"]]
        if rows:
            out["plan_errors"] = rows
            out["meta"]["plan_errors"] = len(rows)
            out["unplaced"] += [[r["name"], r["kind"]] for r in perr]
            out["meta"]["unplaced"] = len(out["unplaced"])
            if not rule128.get("allow_plan_errors") or any(r["kind"] == "empty_tree_net" for r in rows):
                raise C128.PlanError(rows)
    if rule128 is not None:
        sh = (fp or {}).get("shield_net") or "VSS"
        # CLOCK-128 shield lane: legal by construction -- the die PG grid (the build's --pg-json rects, else the plan
        # die.pg grid) and the mesh straps / jogs with their shields are reserved first, then every fixed tree trunk /
        # drop takes the nearest PG-aware track whose metal + shields clear all other nets by the NDR space
        if pg_shapes is not None:
            pgr = pg_shapes
        else:
            import die_infra as DI
            pgr = DI.pg_rects(P, C128.pg_grid(P)) if getattr(P, "die", None) is not None else []
        router = C128.TrackRouter(NDR[ndr], sh, track_profile or DEFAULT_TRACKS, TRACK_MOVE_UM)
        router.reserve(C128.pg_shapes(pgr))
        msegs = mesh_segments(out, jogs=False)
        bad = C128.flank_census(pgr, msegs, NDR[ndr])
        if bad:
            raise C128.PlanError([dict(kind="strap_unshielded", name=r_[5], detail=f"{r_[6]} {r_[0]} {r_[1:5]}: in a "
                                       "PG gap but not flanked by PG on both sides over its span") for r_ in bad])
        router.reserve(C128.clock_shapes(msegs, NDR[ndr], sh))
        jerr = []
        for dk, dv in sorted(out["drivers"].items()):     # island jogs: PG-aware track at the island cell row/column
            if not dv.get("jog_um"):
                continue
            (fx, fy), (cx, cy) = dv["site"], dv["cell_site"]
            lay, ideal, a0_, a1_ = (("M8", cy, fx, cx) if dv["strap"] == "M9" else ("M9", cx, fy, cy))
            c_, m_, e_ = router.place(lay, ideal, a0_, a1_, mesh_net(dv.get("region")))
            if c_ is None:
                jerr.append(dict(kind="no_clock_track", name=str(dk), detail=f"island jog {lay} {ideal:.3f}"))
                continue
            dv.update(jog_c=c_, jog_mode=m_, jog_ext=e_)
        if jerr:
            raise C128.PlanError(jerr)
        wires = C128.fixed_wires(out, cells, nets, BUF_W, ROW_Y, router=router)
        out["fixed_wires"] = wires
        free = C128.fixed_wires(out, cells, nets, BUF_W, ROW_Y)
        dl = [abs(a_["wire_um"] - b_["wire_um"]) for a_, b_ in zip(wires, free)]
        out["meta"]["tree_tracks"] = dict(
            method="C128.TrackRouter: nearest PG-aware track, clock metal + VSS shields clear of PG/clock/shields by "
                   "the NDR space", tracks=track_profile or DEFAULT_TRACKS, max_move_um=TRACK_MOVE_UM,
            segments=len(router.moves), moved=sum(1 for v in router.moves if v > 1e-6), modes=dict(router.modes),
            strap_shield=strap_mode or None,
            move_max_um=round(max(router.moves or [0.0]), 4),
            net_wire_delta_max_um=round(max(dl or [0.0]), 4), pg_rects=len(pgr),
            pg_source="--pg-json" if pg_shapes is not None else "plan die.pg.grid")
        straps = (sum(1 for v in out["strap_spans"].values() if v) if fp is not None else
                  sum((g["i1"] - g["i0"]) + (g["j1"] - g["j0"]) for g in R))
        out["meta"]["clock_shield"] = C128.shield_record(wires, sh, straps,
                                                         sum(1 for d in out["drivers"].values() if d.get("jog_um")))
        out["meta"]["rule_12_8"] = dict(methodology="v4.1 12.8 + 12.4b", shield_net=sh, sizing="plan model (d1)",
                                        early_offset_taps=len(out["rule_12_8"]["early_offset_taps"]),
                                        tap_slew_max_ps=rule128.get("tap_slew_max_ps", C128.TAP_SLEW_MAX_PS))
    return cells, nets, ports, out


def mesh_segments(M, jogs=True):
    """[(layer, x0, y0, x1, y1, net, kind)] centre lines of the mesh straps and island jogs exactly as cmd_combo draws
    them (strap spans clipped at macro holes with --clock-floorplan)."""
    xs, ys = M["xs"], M["ys"]
    regs = M["meta"].get("regions") or [dict(k=None, i0=0, i1=len(xs), j0=0, j1=len(ys))]
    md = {L: (M["meta"].get("strap_shield") or {}).get(L, C128.DRAWN) for L in ("M8", "M9")}
    out = []
    for g in regs:
        rx, ry = xs[g["i0"]:g["i1"]], ys[g["j0"]:g["j1"]]
        net = mesh_net(g["k"])
        if "strap_spans" in M:
            hsp = [(y, strap_span(M, g, xs, ys, 0, j)) for j, y in zip(range(g["j0"], g["j1"]), ry)]
            vsp = [(x, strap_span(M, g, xs, ys, 1, i)) for i, x in zip(range(g["i0"], g["i1"]), rx)]
            hsp, vsp = [v for v in hsp if v[1]], [v for v in vsp if v[1]]
        else:
            xlo, xhi = strap_bounds(g, xs, ys, 0)
            ylo, yhi = strap_bounds(g, xs, ys, 1)
            hsp, vsp = [(y, (xlo, xhi)) for y in ry], [(x, (ylo, yhi)) for x in rx]
        out += [("M8", lo, y, hi, y, net, "strap", md["M8"]) for y, (lo, hi) in hsp]
        out += [("M9", x, lo, x, hi, net, "strap", md["M9"]) for x, (lo, hi) in vsp]
        for dv in (M.get("drivers", {}).values() if jogs else ()):
            if not dv.get("jog_um") or dv.get("region") != g["k"]:
                continue
            out.append(jog_segment(dv, net, md))
    return out


def jog_segment(dv, net, md):
    """the island-driver jog (perpendicular from the strap to the island cell) as a mesh_segments row; on the build's
    PG-aware track (jog_c / jog_mode / jog_ext) when the 12.8 build routed it"""
    (fx, fy), (cx, cy) = dv["site"], dv["cell_site"]
    if dv["strap"] == "M9":
        c = dv.get("jog_c", cy)
        return ("M8", min(fx, cx), c, max(fx, cx), c, net, "jog", dv.get("jog_mode", md["M8"]), dv.get("jog_ext"))
    c = dv.get("jog_c", cx)
    return ("M9", c, min(fy, cy), c, max(fy, cy), net, "jog", dv.get("jog_mode", md["M9"]), dv.get("jog_ext"))


DEFAULT_TRACKS = {"M8": dict(pitch_um=0.08, offset_um=0.04), "M9": dict(pitch_um=0.08, offset_um=0.04)}
TRACK_MOVE_UM = 8.64     # max PG-aware snap of one fixed tree segment (one M8 PG pitch); farther = plan error


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
    if getattr(a, "rule_12_8", False):
        if "layer_budget" not in P.die:
            raise SystemExit(f"die_clock_mesh: {a.plan}: METHODOLOGY 12.8 requires an explicit die.layer_budget; "
                             "schema defaults do not declare the die routing contract")
        lib = Path(a.libdir) / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz"
        if not lib.is_file():
            raise SystemExit(f"die_clock_mesh: missing ASAP7 TT liberty {lib}; supply --libdir")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    pg, pg_shapes, tracks = None, None, None
    plan_grid = bool(a.track_file) and not a.pg_json and getattr(a, "rule_12_8", False) and bool(C128.pg_grid(P))
    if bool(a.pg_json) != bool(a.track_file) and not plan_grid:
        raise SystemExit("PG-aware mesh needs both --pg-json and --track-file from the actual die kit")
    if a.pg_json or plan_grid:
        # CLOCK-128 shield lane: a 12.8 build with --track-file but no --pg-json is PG-aware on the plan die.pg grid
        # (the grid the combo ties land on when the build had no --pg-json)
        import die_infra as DI
        pg = json.loads(Path(a.pg_json).read_text()) if a.pg_json else None
        # main pg_grid (HBM-PG 10-26: core grid + die.pg.domains with holes, die phase) for both --pg-json and the
        # CLOCK-128 shield plan-grid build (pg_grid(P, None) = plan die.pg.grid + domains)
        pg_shapes = DI.pg_rects(P, DI.pg_grid(P, a.pg_json))      # + die.pg.domains (HBM-PG 10-26)
        tracks = mesh_tracks(a.track_file, P)
    region_spec = json.loads(Path(a.region_spec).read_text()) if a.region_spec else None
    fp = json.loads(Path(a.clock_floorplan).read_text()) if a.clock_floorplan else None
    plan_sites = None
    if getattr(a, "plan_sites", None):
        import hashlib
        try:
            plan_sites = C128.load_plan_sites(a.plan_sites, hashlib.sha256(Path(a.plan).read_bytes()).hexdigest())
        except ValueError as e:
            raise SystemExit(f"die_clock_mesh: --plan-sites: {e}")
        plan_sites["source"] = str(a.plan_sites)
        plan_sites["sha256"] = hashlib.sha256(Path(a.plan_sites).read_bytes()).hexdigest()
    try:
        cells, nets, ports, M = build(P, a.nx, a.ny, a.m, a.rep_um, a.ndr, a.max_move, a.hop_max, a.leg, a.sites,
                                  a.regions, a.delta_id, a.region_edge_straps, a.reserve_cell_sites, pg_shapes, tracks, region_spec,
                                  trunk_repeaters=a.trunk_repeaters, driver_pair_span_um=a.driver_pair_span,
                                  split_yfirst=a.split_yfirst, floorplan=fp,
                                  rule128=(dict(libdir=a.libdir, tap_slew_max_ps=a.tap_slew_max_ps,
                                                allow_plan_errors=getattr(a, "allow_plan_errors", False))
                                           if getattr(a, "rule_12_8", False) else None), plan_sites=plan_sites,
                                  lattice=(json.loads(Path(a.lattice_spec).read_text())
                                           if getattr(a, "lattice_spec", None) else None),
                                  uniform_regions=(json.loads(Path(a.uniform_regions).read_text())
                                                   if getattr(a, "uniform_regions", None) else None))
    except C128.PlanError as e:
        (out / "plan_errors.json").write_text(json.dumps(dict(plan=str(a.plan), error=str(e), rows=e.rows), indent=1)
                                              + "\n")
        print(f"die_clock_mesh build: PLAN ERROR {e} -> {out / 'plan_errors.json'}", file=sys.stderr)
        for r in e.rows[:20]:
            print("  " + json.dumps(r), file=sys.stderr)
        return 2
    ren = write_verilog(cells, nets, ports, out / "ctree.v")
    for n in nets:
        n["name"] = ren.get(n["name"], n["name"])
    for w in M.get("fixed_wires", []):
        w["name"] = ren.get(w["name"], w["name"])
    import hashlib
    M["meta"]["plan"] = str(a.plan)
    M["meta"]["plan_sha256"] = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    if pg is not None:
        M["meta"].update(pg_source=str(a.pg_json), pg_sha256=hashlib.sha256(Path(a.pg_json).read_bytes()).hexdigest(),
                         pg_feasible=pg.get("feasible"))
    if "tree_tracks" in M["meta"]:
        M["meta"]["tree_tracks"]["pg_source"] = str(a.pg_json) if a.pg_json else "plan die.pg.grid"
    M["meta"]["build_s"] = round(time.time() - t0, 1)
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
    print(json.dumps(M["meta"], indent=1))
    return 0


def pad_delay(corner, libdir, slew=40.0, cell="BUFx24_ASAP7_75t_R"):
    """pad-cell stage delay at the smallest table load (default BUFx24 driving the next abutted BUFx24), ps."""
    f = Path(libdir) / f"asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz"
    txt = gzip.open(f, "rt").read()
    i = txt.index(f"cell ({cell})")
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
    df = pad_delay(a.corner, a.libdir, cell=a.fine_lib) if a.fine_lib else None
    hist_f = defaultdict(int)
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
            kf = 0
            if v is not None and a.fine_lib:
                # PATH-KV 10-26 fine step: best (BUFx24 count, fine-pad count <= 3) for the measured lift
                k, kf = min(((i, j) for i in range(0, int((vmax - v) / dl) + 2) for j in range(4)),
                            key=lambda ij: (abs(vmax - v - ij[0] * dl - ij[1] * df), ij[1]))
            if k <= 0 and kf <= 0:
                loads.append(x)
                continue
            hist_f[kf] += 1
            hist[min(k, 50) // 5 * 5] += 1
            total_pad += k * dl + kf * (df or 0.0)
            cx, cy = cells[x]["x"], cells[x]["y"]
            chain = []
            for i in range(k + kf):
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
                if i >= k:
                    cells[nm]["lib"] = a.fine_lib
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
    for w in M.get("fixed_wires", []):
        w["name"] = ren.get(w["name"], w["name"])
    M["meta"]["cells"] = len(cells)
    M["clock_cell_overlaps"] = placement_overlaps(cells)
    M["meta"]["clock_cell_overlap_pairs"] = len(M["clock_cell_overlaps"])
    M["meta"]["balance"] = dict(src=str(src), corner=a.corner, pad_ps=round(dl, 2), pads=added,
                                total_pad_ns=round(total_pad / 1e3, 2), hist=dict(sorted(hist.items())),
                                fine_lib=a.fine_lib, fine_pad_ps=round(df, 2) if df else None,
                                fine_hist=dict(sorted(hist_f.items())))
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
    print(json.dumps(M["meta"]["balance"]))
    return 0


# ---------------------------------------------------------------------------------------------------------- stubtrim
def stubtrim_pairs(P, M):
    """conservative complete related-pair superset at tap level: every intra-partition tap pair plus every tap
    cross-product of plan-connected partitions in the SAME clock region (cross-region connected pairs are landed and
    gated by the landing window instead)."""
    import itertools
    reg = {t["port"]: t.get("region") for t in M["taps"]}
    tb = defaultdict(list)
    for t in M["taps"]:
        tb[t["part"]].append(t["port"])
    conn = {tuple(sorted((p["src"]["part"], p["dst"]["part"]))) for p in P.ports.values()
            if p["src"]["part"] in tb and p["dst"]["part"] in tb and p["src"]["part"] != p["dst"]["part"]}
    pairs = set()
    for ts in tb.values():
        pairs.update(itertools.combinations(sorted(ts), 2))
    for u, v in conn:
        if reg[tb[u][0]] == reg[tb[v][0]]:
            pairs.update((a, b) for a in tb[u] for b in tb[v])
    return sorted(pairs), reg


def region_credit(M, tree_path):
    """CPPR credit per region = late - early arrival at the region's own H-tree node (the mesh is NOT common)."""
    Dd, Nn = read_tree(tree_path)
    D = {**Dd, **Nn}
    out = {}
    for g in M["meta"]["regions"]:
        nm = [n for n in D if re.match(rf"ckm_n\d+_{g['tag']}$", n)]
        out[g["k"]] = (D[nm[0]][0] - D[nm[0]][1]) if nm else 0.0
    return out


def read_taps(path):
    arr = {}
    for line in open(path):
        f = line.split()
        if len(f) >= 4 and f[0] == "T":
            arr[f[1]] = (float(f[2]), float(f[3]))
    return arr


def pair_damage(arr, cred, reg, x, y, lift=None, ratio=1.0):
    """CPPR pair damage (both directions) with optional per-tap lifts (early side gets ratio * lift)."""
    lx = lift.get(x, 0.0) if lift else 0.0
    ly = lift.get(y, 0.0) if lift else 0.0
    La, Ea = arr[x][0] + lx, arr[x][1] + ratio * lx
    Lb, Eb = arr[y][0] + ly, arr[y][1] + ratio * ly
    c = min(cred[reg[x]], arr[x][0] - arr[x][1], arr[y][0] - arr[y][1])
    return max(La - Eb, Lb - Ea) - c


def cmd_stubtrim(a):
    """measured per-tap stub trim (standard mesh tap-delay tuning on routed RC): a joint TT+FF LP over the COMPLETE
    tap-level related-pair superset (stubtrim_pairs) picks a lift x_p >= 0 per tap minimising the worst CPPR pair
    damage (credit only at the region H-tree node; the trim's own range is uncredited: its early side gets
    --min-ratio of the lift).  Each lift is realised as abutted BUFx24 (+ <= 3 fine) pads inserted between the stub
    buffer and its tap wire (the stub buffer drives the first pad, the last pad drives the unchanged stub wire), so the
    mesh load and the stub route stay as they are.  Writes a new build dir like balance; re-measure with combo + post."""
    import numpy as np
    import scipy.sparse as sp
    from scipy.optimize import linprog
    src, out = Path(a.dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    P = S.Plan(S.load(a.plan))
    M = json.loads((src / "mesh.json").read_text())
    cells = json.loads((src / "place.json").read_text())
    data = json.loads((src / "nets.json").read_text())
    nets, ports = data["nets"], [tuple(p) for p in data["ports"]]
    pairs, reg = stubtrim_pairs(P, M)
    dl = {c: pad_delay(c, a.libdir) for c in ("TT", "FF")}
    df = {c: pad_delay(c, a.libdir, cell=a.fine_lib) for c in ("TT", "FF")} if a.fine_lib else None
    kff = dl["FF"] / dl["TT"]
    arr = {c: read_taps(src / f"taps_{c}.txt") for c in ("TT", "FF")}
    cred = {c: region_credit(M, src / f"tree_{c}.txt") for c in ("TT", "FF")}
    taps = sorted(arr["TT"])
    idx = {p: i for i, p in enumerate(taps)}
    n = len(taps)
    rows, cols, vals, rhs = [], [], [], []
    for c, kc in (("TT", 1.0), ("FF", kff)):
        A = arr[c]
        for x, y in pairs:
            for p, q in ((x, y), (y, x)):
                cc = min(cred[c][reg[p]], A[p][0] - A[p][1], A[q][0] - A[q][1])
                k = len(rhs)
                rows += [k, k, k]
                cols += [idx[p], idx[q], n]
                vals += [kc, -a.min_ratio * kc, -1.0]
                rhs.append(-(A[p][0] - A[q][1] - cc))
    Am = sp.csr_matrix((vals, (rows, cols)), shape=(len(rhs), n + 1))
    cost = np.full(n + 1, 1e-4)
    cost[n] = 1.0
    r = linprog(cost, A_ub=Am, b_ub=np.array(rhs), bounds=[(0, a.xmax)] * n + [(0, None)], method="highs")
    if not r.success:
        raise SystemExit(f"die_clock_mesh stubtrim: LP failed: {r.message}")
    real = {}
    for p in taps:
        x = float(r.x[idx[p]])
        best = (abs(x), 0, 0)
        for i in range(0, int(x / dl["TT"]) + 2):
            for j in (range(4) if df else [0]):
                best = min(best, (abs(x - i * dl["TT"] - j * (df["TT"] if df else 0.0)), i, j))
        real[p] = best[1:]
    lift = {c: {p: i * dl[c] + j * (df[c] if df else 0.0) for p, (i, j) in real.items()} for c in ("TT", "FF")}

    def worst(c, lf):
        return max((round(pair_damage(arr[c], cred[c], reg, x, y, lf, a.min_ratio), 2), x, y) for x, y in pairs)
    K = DC.KeepIndex(list(DC.keepouts(P)), die=(float(P.W), float(P.H)))
    for name, c in cells.items():
        reserve_cell(K, name, c)
    by_drv = {nn["drv"]: nn for nn in nets}
    added, new_nets = 0, []
    for t in M["taps"]:
        i, j = real[t["port"]]
        if i + j == 0:
            continue
        sb = t["stub"]
        nn = by_drv[sb]
        cx, cy = cells[sb]["x"], cells[sb]["y"]
        chain = []
        for m_ in range(i + j):
            col, row = m_ % 16, m_ // 16
            for sgn in (-1, 1):
                q = (cx + BUF_W / 2 + sgn * (col + 1) * (BUF_W + SITE_X * 2), cy + ROW_Y / 2 + 2 * ROW_Y * (row + 1))
                if not hitf(K, q):
                    break
            else:
                q, _ = free_near(K, q)
            if q is None:
                raise SystemExit("die_clock_mesh stubtrim: no legal site for trim pad")
            nm = f"ckm_p{a.tag}_{added}"
            added += 1
            cells[nm] = dict(x=snap(q[0] - BUF_W / 2, SITE_X), y=snap(q[1] - ROW_Y / 2, ROW_Y), kind="pad", level=99)
            if "region" in cells[sb]:
                cells[nm]["region"] = cells[sb]["region"]
            if m_ >= i:
                cells[nm]["lib"] = a.fine_lib
            reserve_cell(K, nm, cells[nm])
            chain.append(nm)
        loads = nn["loads"]
        nn["loads"] = [chain[0]]
        for u, w in zip(chain, chain[1:]):
            new_nets.append(dict(name=f"ckm_w_{u}", drv=u, loads=[w], level=99))
        # the LAST pad drives the unchanged tap wire: keep the stub net's name on it (stub_nets/SPEF naming)
        new_nets.append(dict(name=nn["name"], drv=chain[-1], loads=loads, level=99))
        nn["name"] = f"ckm_w_{sb}"
    nets += new_nets
    ren = write_verilog(cells, nets, ports, out / "ctree.v")
    for nn in nets:
        nn["name"] = ren.get(nn["name"], nn["name"])
    M["meta"]["cells"] = len(cells)
    M["clock_cell_overlaps"] = placement_overlaps(cells)
    M["meta"]["clock_cell_overlap_pairs"] = len(M["clock_cell_overlaps"])
    M["meta"]["stubtrim"] = dict(
        src=str(src), pairs=len(pairs), coverage="complete tap superset (intra-partition + connected same-region)",
        lp_bound_ps=round(float(r.x[n]), 2), untrimmed={c: worst(c, None) for c in ("TT", "FF")},
        predicted={c: worst(c, lift[c]) for c in ("TT", "FF")}, pads=added,
        trimmed_taps=sum(1 for v in real.values() if sum(v)), pad_ps={c: round(dl[c], 2) for c in dl},
        fine_lib=a.fine_lib, fine_ps={c: round(df[c], 2) for c in df} if df else None, xmax_ps=a.xmax,
        min_ratio=a.min_ratio)
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
    print(json.dumps(M["meta"]["stubtrim"]))
    return 0


def balance_audit_128(a, src, out, M):
    """12.8d: no measured pads.  Copies the build unchanged and writes the plan-model structural audit."""
    if a.tree:
        raise SystemExit("die_clock_mesh balance: 12.8 build -- measured balancing (--tree) is banned (12.8d)")
    cells = json.loads((src / "place.json").read_text())
    data = json.loads((src / "nets.json").read_text())
    libs = C128.lib_cells(a.corner, a.libdir)
    au = C128.structural_audit(M, cells, data["nets"], libs, NDR[M["meta"]["ndr"]], DC.LAYER_RC, BUF, BUF_W, ROW_Y)
    M["meta"]["balance_audit_12_8"] = dict(src=str(src), corner=a.corner, pads=0, mode="12.8 structural audit (no pads)")
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
    import gen_phys as GP
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
        # Match gen_phys.io_tcl: the die spine drops onto the real partition signal-max tap (currently M7).
        tap_layer = t_.get("layer", M["meta"].get("tap_layer", "M7"))
        pin_size = t_.get("pin_size_um", M["meta"].get("tap_pin_size_um", [GP.LAYER_W.get(tap_layer, .04), 4 * GP.PIN_LEN_UM]))
        L.append(f"place_pin -pin_name {t_['port']} -layer {tap_layer} -location {{{t_['xy'][0]:.3f} {t_['xy'][1]:.3f}}} "
                 f"-pin_size {{{pin_size[0]:g} {pin_size[1]:g}}}")
    for c, v_ in sorted(cells.items()):
        L.append(f"place_inst -name {c} -location {{{v_['x']} {v_['y']}}} -orient R0 -status FIRM")
    hw = nd["width"] / 2
    L += ["set blk [ord::get_db_block]", "set tech [ord::get_db_tech]", "set l8 [$tech findLayer M8]",
          "set l9 [$tech findLayer M9]", "set dbu [$tech getDbUnitsPerMicron]",
          "proc um {v} { global dbu; return [expr {round($v*$dbu)}] }"]
    # the strap footprint (+ NDR spacing) is also a routing obstruction: GRT does not derate special wires
    hs = hw + nd["space"]
    regs = M["meta"].get("regions") or [dict(k=None, i0=0, i1=len(xs), j0=0, j1=len(ys))]
    vias_meta, cross_meta = {}, {}
    shield_segs_all = []      # every shielded clock segment (straps, jogs, fixed tree wires): VSS ties below
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
        if getattr(a, "mesh_vias", False):   # the mesh is ONE connected net in the routed DB (qc-clock-r2 7ec62b303)
            L.append("set v89 [$tech findVia VIA89]")
            L.append("if {$v89 == \"NULL\"} { error \"tech via VIA89 missing\" }")
            xs_ = [(x, lo, hi) for x, (lo, hi) in vsp]
            nx_ = 0
            for y, (xlo, xhi) in hsp:          # a via only where both (possibly macro-clipped) straps exist
                for x, ylo, yhi in xs_:
                    if xlo - 1e-6 <= x <= xhi + 1e-6 and ylo - 1e-6 <= y <= yhi + 1e-6:
                        L.append(f"odb::dbSBox_create $sw $v89 [um {x:.4f}] [um {y:.4f}] STRIPE")
                        nx_ += 1
            L.append("set nv 0; foreach b [$sw getWires] { if {[$b isVia]} { incr nv } }")
            L.append(f"puts \"OT_MESH_VIAS {mesh_net(g['k'])} $nv\"")
            vias_meta[str(g["k"])] = nx_
        # island drivers (12.2a): perpendicular jog from the window to the strap, on this region's mesh net
        jogs = [dv for dv in M.get("drivers", {}).values() if dv.get("jog_um") and dv.get("region") == g["k"]]
        jo = hw + 2 * nd["space"] + nd["width"] if shield else hs
        md_ = {L_: (M["meta"].get("strap_shield") or {}).get(L_, C128.DRAWN) for L_ in ("M8", "M9")}
        jrows = [jog_segment(dv, mesh_net(g["k"]), md_) for dv in jogs]
        for r_ in jrows:
            lay_, a0, b0, a1, b1 = r_[:5]
            jx = max(jo, (r_[8] or 0) + hw)
            if lay_ == "M8":
                L.append(f"odb::dbObstruction_create $blk $l8 [um {a0 - jx:.4f}] [um {b0 - jo:.4f}] [um {a1 + jx:.4f}] "
                         f"[um {b1 + jo:.4f}]")
            else:
                L.append(f"odb::dbObstruction_create $blk $l9 [um {a0 - jo:.4f}] [um {b0 - jx:.4f}] [um {a1 + jo:.4f}] "
                         f"[um {b1 + jx:.4f}]")
            L.append(f"odb::dbSBox_create $sw $l{lay_[1]} [um {a0 - hw:.4f}] [um {b0 - hw:.4f}] [um {a1 + hw:.4f}] "
                     f"[um {b1 + hw:.4f}] STRIPE")
        if shield:   # 12.7a: a PG stripe on both sides of every clock strap and jog, one NDR space away
            _, off, ext = C128.shield_geom(nd)
            L += [f"set pn [$blk findNet {shield}]",
                  f"if {{$pn eq \"NULL\"}} {{ set pn [odb::dbNet_create $blk {shield}] }}",
                  "$pn setSpecial", "$pn setSigType GROUND", "set psw [odb::dbSWire_create $pn ROUTED]"]
            segs = [("M8", xlo, y, xhi, y) for y, (xlo, xhi) in hsp] + [("M9", x, ylo, x, yhi) for x, (ylo, yhi) in vsp]
            sw2 = nd["width"] / 2
            smode = M["meta"].get("strap_shield") or {}     # a 'pg' layer: the PG stripes are the shields, none drawn
            segs = [s_ + (None,) for s_ in segs if smode.get(s_[0], C128.DRAWN) == C128.DRAWN]
            segs += [tuple(r_[:5]) + (r_[8],) for r_ in jrows if r_[7] == C128.DRAWN]
            shield_segs_all += segs
            for lay, a0, b0, a1, b1, e_ in segs:
                ext = C128.shield_geom(nd)[2] if e_ is None else e_
                for sgn in (-1, 1):
                    if lay == "M8":
                        yy = b0 + sgn * off
                        L.append(f"odb::dbSBox_create $psw $l8 [um {a0 - ext:.4f}] [um {yy - sw2:.4f}] [um {a1 + ext:.4f}] "
                                 f"[um {yy + sw2:.4f}] STRIPE")
                    else:
                        xx = a0 + sgn * off
                        L.append(f"odb::dbSBox_create $psw $l9 [um {xx - sw2:.4f}] [um {b0 - ext:.4f}] [um {xx + sw2:.4f}] "
                                 f"[um {b1 + ext:.4f}] STRIPE")
    if getattr(a, "mesh_vias", False):
        M["meta"]["mesh_vias"] = vias_meta
        (d / "mesh.json").write_text(json.dumps(M) + "\n")
    clock_nets = [n["name"] for n in data["nets"]]
    if C128.enabled(M):   # 12.7a/12.8: every tree net is a fixed, shielded pre-route; its RC is that geometry
        # the build's PG-aware shielded tracks (CLOCK-128 shield lane) are the geometry; older builds recompute
        wires = M.get("fixed_wires") or C128.fixed_wires(M, cells, data["nets"], BUF_W, ROW_Y)
        L += C128.combo_tcl(wires, nd, M["meta"]["rule_12_8"]["shield_net"])
        sp = C128.spef(wires, cells, BUF, nd, DC.LAYER_RC, DC.VIA_KOHM)
        for c_ in ("TT", "FF"):
            (d / f"native_{c_}.spef").write_text(sp)
        shield_segs_all += [tuple(r_[:5]) + (r_[8],) for r_ in C128.tree_segs(wires) if r_[7] == C128.DRAWN]
    shield_net = (M["meta"].get("clock_floorplan") or {}).get("shield_net") or \
        (M["meta"]["rule_12_8"]["shield_net"] if C128.enabled(M) else None)
    if shield_net and shield_segs_all:
        # 12.7a / COORD 07:04: every shield stripe via-tied to the die VSS grid (plan die.pg.grid + PHY domain grids):
        # VIA89 at each shield x perpendicular VSS stripe and each M8 x M9 shield crossing; the VSS stripes the ties land
        # on are written as special wires of the shield net (the kit models the die grid only as obstructions).
        import die_infra as DI
        Pp = S.Plan(S.load(getattr(a, "plan", None) or M["meta"]["plan"]))
        # the build's actual IR-sized PG file (--pg-json, the same rects the mesh axes avoided) when it had one, else
        # the plan's die.pg grid (CLOCK-128-R2: the ties must land on the grid the die is really built with)
        pg_src = M["meta"].get("pg_source")
        grid_ = C128.pg_grid(Pp, pg_src)         # core grid (IR-sized pg.json or plan) + die.pg.domains, one model
        pgr = DI.pg_rects(Pp, grid_)
        stripes = C128.shield_stripes(shield_segs_all, nd)
        ties = C128.shield_ties(stripes, pgr, nd["width"], net=shield_net)
        # same-layer legality of everything drawn on M8/M9 (PG grid, straps, jogs, tree wires, shields): no two nets
        # closer than the NDR space; any short / spacing violation blocks freeze evidence
        msegs = mesh_segments(M) + (C128.tree_segs(wires) if C128.enabled(M) else [])
        census = C128.metal_census(C128.pg_shapes(pgr) + C128.clock_shapes(msegs, nd, shield_net), nd["space"])
        census["unflanked"] = C128.flank_census(pgr, msegs, nd)
        census["flank_mode_segments"] = sum(1 for r_ in msegs if len(r_) > 7 and r_[7] == C128.FLANK)
        L += [f"set tn [$blk findNet {shield_net}]",
              f"if {{$tn eq \"NULL\"}} {{ set tn [odb::dbNet_create $blk {shield_net}] }}",
              "$tn setSpecial", "$tn setSigType GROUND", "set tsw [odb::dbSWire_create $tn ROUTED]"]
        L += C128.grid_tcl(pgr, "$tsw", shield_net, used=ties["used_grid"])
        L += C128.tie_tcl(ties, "$tsw")
        cs = M["meta"].get("clock_shield") or {}
        cs.update(C128.tie_record(ties))
        cs.update(metal_shorts=census["shorts"], metal_spacing=census["spacing"],
                  pg_flanked_segments=census["flank_mode_segments"], unflanked_segments=len(census["unflanked"]),
                  shield_modes="drawn = 2 VSS stripes via-tied to the die VSS grid; pg = in a PG gap, the two "
                               "neighbouring die PG stripes (VDD/VSS) are the shields (12.7a 'PG stripes on both sides')",
                  metal_shorts_by_kind=census["shorts_by_kind"], metal_spacing_by_kind=census["spacing_by_kind"],
                  metal_shapes=census["shapes"])
        cs["vss_tied"] = bool(cs["vss_tied"] and not census["shorts"])
        cs["freeze_evidence_ok"] = bool(cs["vss_tied"] and cs.get("complete") and not census["spacing"]
                                        and not census["unflanked"])
        cs["tie_grid_stripes"] = len(ties["used_grid"])
        cs["tie_pg_source"] = pg_src or "plan die.pg.grid"
        M["meta"]["clock_shield"] = cs
        (d / "shield_ties.json").write_text(json.dumps(dict(
            record=C128.tie_record(ties), untied=[stripes[k] for k in ties["untied"][:200]],
            shorts=[[stripes[k], n_] for k, n_ in ties["shorts"][:200]],
            metal_census={k: v for k, v in census.items()})) + "\n")
        (d / "mesh.json").write_text(json.dumps(M) + "\n")
        print("shield ties", json.dumps(C128.tie_record(ties)), "metal shorts", census["shorts"], "spacing",
              census["spacing"], json.dumps(census["shorts_by_kind"]), json.dumps(census["spacing_by_kind"]))
    L += [f"puts \"OT_MESH regions {len(regs)} straps {sum((g['i1'] - g['i0']) + (g['j1'] - g['j0']) for g in regs)}\"",
          "create_clock -name dck -period 833.000 [get_ports root]",
          "set_routing_layers -signal M4-M9 -clock M8-M9"]
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


def mesh_connected(M, d=None):
    """{region k: bool}: True when region k's mesh is ONE connected net in the emitted geometry: the crossings carry
    emitted M8-M9 vias (meta.mesh_vias, written by combo --mesh-vias, >= every strap crossing) and, given the run dir,
    the routed-DB count (OT_MESH_VIAS in combo_<corner>.log, min over corners) agrees.  INFO input only (v4 12.4b)."""
    vias = M["meta"].get("mesh_vias") or {}
    db = {}
    for lg in sorted(Path(d).glob("combo_*.log")) if d else []:
        for m_ in re.finditer(r"^OT_MESH_VIAS (\S+) (\d+)", lg.read_text(errors="replace"), re.M):
            db[m_.group(1)] = min(db.get(m_.group(1), 1 << 60), int(m_.group(2)))
    out = {}
    for g in M["meta"].get("regions") or []:
        nh, nv = g["j1"] - g["j0"], g["i1"] - g["i0"]
        # macro-clipped straps (--clock-floorplan holes): the need is the emitted crossing count; else the full grid
        need = max(1, int(vias.get(str(g["k"]), 0))) if M["meta"].get("macro_holes") else nh * nv
        ok = nh > 0 and nv > 0 and int(vias.get(str(g["k"]), 0)) >= need
        if d is not None:
            ok = ok and db.get(mesh_net(g["k"]), 0) >= need
        out[g["k"]] = bool(ok)
    return out


def sink_arrivals(M, arr, corner, early_by_plan):
    """Compare equivalent sink clocks: core pins must arrive earlier by their core insertion offset.

    Add that offset back to both measured pin arrivals for pair checks.  The raw pin arrivals remain INFO.
    Plan lookup also repairs measurements made before mesh.json carried per-corner offsets.
    """
    offsets = {t["port"]: float(early_by_plan.get((t["part"], t["tap"]), {}).get(
        corner, (t.get("early_corner_ps") or {}).get(corner, t.get("early_ps", 0.0)))) for t in M["taps"]}
    return ({p: v[0] + offsets[p] for p, v in arr.items()},
            {p: v[1] + offsets[p] for p, v in arr.items()}, offsets)


INFO_128D = "INFO-12.8d (not qualifying)"


def banned_means_12_8d(M):
    """METHODOLOGY 12.8d: a build that used measured stub trims, balance pads, early-tap branches or core offsets is
    diagnostic evidence only; its report never carries PASS (12.8f re-measure on the 12.8 structure)."""
    meta = M.get("meta", {})
    why = []
    if meta.get("stubtrim"):
        why.append("stubtrim (per-tap trim chosen after a measurement)")
    if meta.get("balance"):
        why.append("balance pads (chosen after a measurement)")
    if any(float(t.get("early_ps") or 0.0) != 0.0 for t in M.get("taps", [])):
        why.append("early-tap branch / core offset")
    if meta.get("early_branches") or meta.get("core_offsets"):
        why.append("early-tap branch / core offset")
    if meta.get("plan_errors"):
        why.append("plan errors (diagnostic --allow-plan-errors build)")
    return sorted(set(why))


def apply_12_8d(rep, why):
    """Relabel every corner verdict of a banned-means build (never PASS) and return the qualification blocker."""
    if not why:
        return None
    for r in rep["corners"].values():
        r["verdict_measured"] = r["verdict"]
        r["verdict"] = INFO_128D
        if "landed_verdict" in r:
            r["landed_verdict_measured"] = r["landed_verdict"]
            r["landed_verdict"] = INFO_128D
    return "built with 12.8d banned means: " + "; ".join(why)


def regional_qualification(M, corners, crossings):
    """A regional clock diagnostic is not evidence of implemented forwarded-clock landings."""
    reasons = []
    reasons.append("related-pair coverage unproven: spatial tap pairs need an actual endpoint-to-tap ledger or conservative superset proof")
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
    return dict(scope="mesh clock diagnostic; not a complete die related-pair gate", release_verdict="BLOCKED" if reasons else
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
        return htree_tag(i, j, nx, ny, M["meta"].get("region_axes", ""))
    import numpy as np
    xa, ya = np.array(xs), np.array(ys)
    rep = dict(meta=M["meta"], corners={}, related_pair_coverage=dict(complete=False, kind="surrogate spatial tap pairs",
                    required="actual endpoint-to-tap pair ledger or qualified conservative all-tap superset"))
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
        if M["meta"].get("uniform_regions"):   # regions are strap boxes, not H-tree subtrees: check the index box
            gk = {g["k"]: g for g in M["meta"]["regions"]}
            near = {t["port"]: (int(np.argmin(abs(xa - t["foot"][0]))), int(np.argmin(abs(ya - t["foot"][1]))))
                    for t in M["taps"]}
            bad = [p for p, (i, j) in near.items()
                   if not (gk[reg[p]]["i0"] <= i < gk[reg[p]]["i1"] and gk[reg[p]]["j0"] <= j < gk[reg[p]]["j1"])]
        else:
            bad = [p for p, tg in tagof.items() if tags.get(tg[:1 + regd]) != reg[p] and not on_own_edge(p)]
        if bad:
            raise SystemExit(f"die_clock_mesh report: {len(bad)} taps fed from another region's strap, e.g. {bad[:3]}")
    landed = [x for x in seam if reg[x[0]] != reg[x[1]]]
    seam_in = [x for x in seam if reg[x[0]] == reg[x[1]]]
    intra_x = [x for x in intra if reg[x[0]] != reg[x[1]]]
    landing_cycles = M["meta"].get("region_spec", {}).get("landing_cycles", a.landing_cycles)
    crossing_table = write_landed(P, S.load(a.plan), M, d, landing_cycles) if regd else None
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
        # METHODOLOGY v4 12.4b (qc-clock-r2 aa83d0e48 + 71a183f91): the gate above credits CPPR at the last common
        # TREE node only; the mesh-node credit (smaller of the two stub-input ranges, same connected regional mesh) is INFO.
        srng = {s_["port"]: s_["late"] - s_["early"] for s_ in Mz["stubs"].values()}
        mesh_ok = mesh_connected(M, d) if regd else {}

        def dmg_mesh(pa, pb):
            c = M["meta"]["regions"][reg[pa]]["tag"] if regd else "h"
            while c not in rng and len(c) > 1:
                c = c[:-1]
            cr = rng.get(c, 0.0)
            if regd and reg[pa] == reg[pb] and pa in srng and pb in srng:
                cr = max(cr, min(srng[pa], srng[pb]))
            return DC.pair_clock_damage(late[pa], early[pa], late[pb], early[pb], cr)["max_damage_ps"]
        mk_ = [dmg_mesh(x[0], x[1]) for x in list(seam_in) + [(i[0], i[1]) for i in intra]]
        mesh_info = dict(cppr_rule="METHODOLOGY v4 12.4b: GATE = last common tree node (region root same-region, die root "
                                   "across); mesh-node credit = INFO only",
                         info_mesh_credit_related_pair_max_ps=round(max(mk_), 2),
                         info_mesh_credit_pairs_over_80=sum(1 for v in mk_ if v > 80),
                         mesh_connected={str(k_): v_ for k_, v_ in mesh_ok.items()})
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
            worst=[[round(w, 2), x, y] for w, x, y in worst], **mesh_info)
        if C128.enabled(M):
            Dt, _ = read_tree(d / f"tree_{corner}.txt")
            g12 = C128.gate(M, P, [(x[0], x[1]) for x in seam_in] + [(i[0], i[1]) for i in intra], late, early, rng, regd, Mz["stubs"], Dt,
                            M.get("rule_12_8", {}).get("early_offset_taps", []))
            r_ = rep["corners"][corner]
            # METHODOLOGY v4.3 12.4a (OWNER 06:33): the freeze gate is die STA (TT setup / FF hold >= 0, propagated routed
            # clock, CPPR to the last tree node); this skew number is a DIAGNOSTIC against the 80-ps design target.
            r_.update(related_pair_max_ps=g12["related_pair_max_ps"], pairs_over_80=g12["pairs_over_80"],
                      verdict="DIAGNOSTIC-" + g12["verdict"], skew_role="DIAGNOSTIC (target 80 ps); freeze gate = die STA "
                      "related-pair setup/hold on tap_arrivals_<corner>.json (12.4a v4.3)",
                      early_offset_verdict="FAIL" if g12["residual"]["core_latency"]["early_offset_taps"] else "PASS",
                      rule_12_8=g12)
            r_.pop("compensated_sink_insertion_ps", None)
            C128.write_tap_arrivals(d / f"tap_arrivals_{corner}.json", M, corner, arr, rng, regd)
    # clock power: C V^2 f over every die clock wire + pin (mesh from the transient, tree/stub wire from length)
    nd = NDR[M["meta"]["ndr"]]
    cw = (DC.LAYER_RC["M8"][1] + DC.LAYER_RC["M9"][1]) / 2 * nd["cf"]
    ncell = M["meta"]["cells"]
    for corner, r in rep["corners"].items():
        c_tot = r["mesh_cap_pF"] + (M["meta"]["htree_wire_mm"] + M["meta"]["stub_wire_mm"]) * 1e3 * cw / 1e3 \
            + ncell * DC.BUF_CIN_FF / 1e3 + len(M["taps"]) * DC.TAP_LOAD_FF / 1e3
        r["clock_switched_cap_pF"] = round(c_tot, 1)
        r["clock_wire_power_W"] = round(c_tot * 1e-12 * VDD[corner] ** 2 / (DC.PERIOD_PS * 1e-12), 3)
    why = banned_means_12_8d(M)
    if C128.enabled(M):   # a 12.8 build has no compensation: an early-offset tap is a structural FAIL (gate), not INFO
        why = [w for w in why if w != "early-tap branch / core offset"]
    for r in rep["corners"].values():
        if C128.enabled(M):
            continue
        if r.get("core_offset_taps") and "early-tap branch / core offset" not in why:
            why.append("early-tap branch / core offset")
    blocker = apply_12_8d(rep, why)
    rep["qualification"] = regional_qualification(M, rep["corners"], crossing_table["crossings"] if crossing_table else 0)
    if blocker:
        rep["qualification"]["blockers"].append(blocker)
        rep["qualification"]["release_verdict"] = "BLOCKED"
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
    b.add_argument("--region-spec", help="opt-in dataflow clock cohorts: split_axes plus actual x_cuts_um/y_cuts_um")
    b.add_argument("--trunk-repeaters", action="store_true",
                   help="opt-in: equal-cut BUFx24 repeaters on a root->tree-centre trunk > 750 um (PATH-KV 10-26)")
    b.add_argument("--driver-pair-span", type=float, default=0.0,
                   help="opt-in (>0, KV uses 700): leaf driver pair split by a macro beyond this span takes the shortest pair")
    b.add_argument("--split-yfirst", action="store_true", help="opt-in: split_long retries the y-first L (PHY corners)")
    b.add_argument("--delta-id", help="plan delta tag recorded in mesh.json meta (e.g. D-QC-CLKMESH)")
    b.add_argument("--rule-12-8", action="store_true", default=True,
                   help="(DEFAULT) METHODOLOGY v4.1 12.8: plan-model stub sizing (d1), early-offset taps FAIL, no measured "
                        "balance, fixed VSS-shielded tree pre-routes, CPPR at the last common tree node")
    b.add_argument("--legacy-pre-12-8", dest="rule_12_8", action="store_false",
                   help="DIAGNOSTIC ONLY: the pre-12.8 build (never freeze/sign-off evidence)")
    b.add_argument("--libdir", default=str(Path("~/.cache/opentallas/asap7_nldm").expanduser()),
                   help="liberty dir for the 12.8 plan sizing model")
    b.add_argument("--tap-slew-max-ps", type=float, default=C128.TAP_SLEW_MAX_PS)
    b.add_argument("--plan-sites", help="12.8: ot_clock_sites/1 reserved lattice island sites (clock_plan_sites.py from "
                                        "the master-plan slices); drivers/nodes/repeaters on plan sites, move <= PG snap")
    b.add_argument("--uniform-regions", help="opt-in JSON (CLOCK-KV-R2): x_cuts_um / y_cuts_um dataflow seams (partition "
                   "edges); regions = strap boxes on the UNIFORM nx x ny lattice, H-tree = whole-grid bisection "
                   "independent of the cuts, CPPR node per region = lowest common tree node of its intersections, "
                   "gate: every partition inside one box, every tap within 750 um of its own region strap")
    b.add_argument("--lattice-spec", help="opt-in JSON (CLOCK-KV-R3, 12.8e1 continuous mesh): ys_um (all strap rows, "
                   "any count), driver_rows (power-of-two list of strap-row indices carrying mesh drivers), axes "
                   "(tree split order, e.g. yyyyxxxxxyy); other rows are driverless straps of the same mesh")
    b.add_argument("--allow-plan-errors", action="store_true",
                   help="DIAGNOSTIC: write the build despite plan errors (never qualifies; combo refuses it)")
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
    bl.add_argument("--fine-lib", help="fine-step pad master (e.g. BUFx6f_ASAP7_75t_R): <=3 per load after BUFx24 pads")
    bl.add_argument("--libdir", default=str(Path("~/.cache/opentallas/asap7_nldm").expanduser()))
    st = sub.add_parser("stubtrim")
    st.add_argument("dir")
    st.add_argument("--out", required=True)
    st.add_argument("--plan", required=True)
    st.add_argument("--tag", default="t", help="pad name tag")
    st.add_argument("--xmax", type=float, default=120.0, help="max TT lift per tap, ps")
    st.add_argument("--min-ratio", type=float, default=0.97, help="early-side fraction of a lift (rest uncredited)")
    st.add_argument("--fine-lib", help="fine-step pad master (<= 3 per tap after BUFx24 pads)")
    st.add_argument("--libdir", default=str(Path("~/.cache/opentallas/asap7_nldm").expanduser()))
    c = sub.add_parser("combo")
    c.add_argument("dir")
    c.add_argument("--kit", required=True)
    c.add_argument("--plan", help="pinned physical plan for the all-clock-cell hard-keepout census")
    c.add_argument("--mesh-vias", action="store_true",
                   help="emit an M8-M9 VIA89 at every mesh strap crossing (mesh = one connected net in the DB); "
                        "mesh-node CPPR stays INFO only (METHODOLOGY v4 12.4b)")
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
    return dict(build=cmd_build, balance=cmd_balance, stubtrim=cmd_stubtrim, combo=cmd_combo, mesh=cmd_mesh, stubsta=cmd_stubsta, report=cmd_report,
                render=cmd_render)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
