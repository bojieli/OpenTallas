"""Sink-anchored clock taps (COORD 10-23 R4, GEOM-REVIEW6 17:09, KV-P6).

A partition whose clock sinks are FIRM-planned (face registers at their pins, ft stations on their planned routes, the
per-tap reset synchronisers) may ADD clock taps at those sinks to its ceil(w/pitch) x ceil(h/pitch) grid (KV-P6
motivation: a coarse grid left 6/12 (400 um) and 11/20 (280 um) io_cor_v1 taps without a sink (dead spine drops, unloaded
per-tap reset synchronisers) while the loaded taps held 2.7k sinks / 349-ps trees.

    clock.tap_mode      "grid+sinks" / "sinks" (default "grid": schema.tap_grid's pitch grid).  CP1 r8 RULING (COORD
                        10-23 21:26): these taps are ADDED to the R4 grid (schema.tap_grid), never replace it -- as a
                        replacement the frame's interior logic (4.5-5.7k sinks) piled on one tap (spread 133 ps)
    clock.tap_radius_um max Manhattan distance tap -> planned sink (default 250: the 280-um grid's 205-222 ps trees)
    clock.tap_max_sinks max planned sinks per sink tap (clustering default 1500); clock_taps.tcl caps the real
                        netlist per tap (grid or added) at OT_TAP_MAX_SINKS = this value, else 3000

Method: the planned sinks (planned_sinks) are clustered by capacity- and radius-bounded Manhattan k-medians: k grows
from ceil(N / cap) until every cluster fits the radius and the cap; a tap sits at its cluster's coordinate-wise median
(the L1 centre), clamped TAP_MARGIN_UM inside the outline; empty clusters are dropped, so every tap carries planned
sinks.  Deterministic (farthest-point seeding from the sink nearest the outline centre).  Tap 0 = 'clk' is the tap
nearest the plan's clock.tap_um (the die spine's partition root), the rest 'clk_t<i>' in (y, x) order.

clock.tap_mode "density" (OWNER decision 5, 10-24, industry multi-source CTS; opt-in, density_taps): NO grid.  Taps are
placed by sink density over the full register inventory (clock.sink_bins_file from a placed netlist via
`taps.py bins`, and/or clock.sink_sites_um, else the planned face / ft sinks): <= tap_target_sinks (0.8 x
tap_max_sinks, default 1500) per tap within tap_radius_um (200), none on a hard core (keep-clear), refined on the kit's
own nearest-tap + cap split (assign = clock_taps.tcl).  gen_phys exports OT_TAP_REASSIGN_UM = radius and the GRT-RC tap
hook (tap_balance_grt.tcl, clock.tap_balance_rc grt_report | grt | placement).
"""
from collections import OrderedDict
import hashlib
import json
import math
import sys
from threading import RLock

TAP_MARGIN_UM = 17.28          # keep the interior tap pins off the face pin bands
FACE_INSET_UM = 2.0            # a face register sits just inside its pin
SEP_UM = 8.64                  # two taps closer than one lattice step merge (one spine drop)

# Retain the exact Plan with its result: id(P) alone can be reused after a
# transient compose Plan is collected, otherwise returning another plan's taps.
# The identity check also keeps cache hits correct for plan-like test objects.
_CACHE = {}

# Density results may be requested through many transient compose Plans. Retain
# immutable values by their resolved inputs, never the Plan or its mutable lists.
_DENSITY_CACHE = OrderedDict()
_DENSITY_CACHE_BYTES = 0
_DENSITY_CACHE_MAX_BYTES = 4 << 20
_DENSITY_CACHE_MAX_ENTRIES = 16
_DENSITY_CACHE_LOCK = RLock()


def _clear_density_cache():
    global _DENSITY_CACHE_BYTES
    with _DENSITY_CACHE_LOCK:
        _DENSITY_CACHE.clear()
        _DENSITY_CACHE_BYTES = 0


def _density_key(P, tn, control, pts, taken, boxes):
    import schema
    import gen_phys
    inputs = dict(type_name=tn, type=P.types[tn], control=control,
                  sinks=pts, reserved=taken, boxes=boxes,
                  layers=getattr(P, "layers", None), layer_budget=getattr(P, "layer_budget", None),
                  grid=getattr(P, "grid", None), core_margin=gen_phys.CORE_MARGIN_UM,
                  tap_clear=schema.TAP_CLEAR_UM, tap_step=schema.TAP_STEP_UM,
                  pg_bands=schema.PART_PG_BANDS, tap_margin=TAP_MARGIN_UM)
    try:
        # Resolved sites include external bin/per-bit files and type origins.
        # Only the digest is retained, even for hundreds of thousands of sites.
        text = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        return None  # unusual plan-like callers retain uncached planner behavior
    return hashlib.sha256(text.encode()).digest()


def _density_cached(key):
    with _DENSITY_CACHE_LOCK:
        value = _DENSITY_CACHE.get(key) if key is not None else None
        if value is None:
            return None
        _DENSITY_CACHE.move_to_end(key)
    return list(value[0])


def _density_remember(key, result):
    global _DENSITY_CACHE_BYTES
    if key is None:
        return
    value = tuple(tuple(row) for row in result)
    # Conservative deep size, including scalar values and container overhead.
    size = (256 + sys.getsizeof(key) + sys.getsizeof(value)
            + sum(sys.getsizeof(row) + sum(sys.getsizeof(v) for v in row) for row in value))
    if size > _DENSITY_CACHE_MAX_BYTES:
        return
    with _DENSITY_CACHE_LOCK:
        old = _DENSITY_CACHE.pop(key, None)
        if old is not None:
            _DENSITY_CACHE_BYTES -= old[1]
        while _DENSITY_CACHE and (len(_DENSITY_CACHE) >= _DENSITY_CACHE_MAX_ENTRIES
                                or _DENSITY_CACHE_BYTES + size > _DENSITY_CACHE_MAX_BYTES):
            _, (_, removed) = _DENSITY_CACHE.popitem(last=False)
            _DENSITY_CACHE_BYTES -= removed
        _DENSITY_CACHE[key] = (value, size)
        _DENSITY_CACHE_BYTES += size


def _zroute(a, b, fin, fout):
    """face_flops.tcl ff_zroute: the slot's planned route as a polyline."""
    (ax, ay), (bx, by) = a, b
    if abs(ax - bx) < 1 or abs(ay - by) < 1:
        return [a, b]
    if (fin in "EW") != (fout in "EW"):
        return [a, (bx, ay), b] if fin in "EW" else [a, (ax, by), b]
    if fin in "EW":
        xm = (ax + bx) / 2
        return [a, (xm, ay), (xm, by), b]
    ym = (ay + by) / 2
    return [a, (ax, ym), (bx, ym), b]


def _point_at(pts, t):
    for (px, py), (qx, qy) in zip(pts, pts[1:]):
        d = abs(px - qx) + abs(py - qy)
        if t <= d:
            f = 0.0 if d == 0 else t / d
            return (px + f * (qx - px), py + f * (qy - py))
        t -= d
    return pts[-1]


def _inset(x, y, face, w, h):
    return {"E": (x - FACE_INSET_UM, y), "W": (x + FACE_INSET_UM, y), "N": (x, y - FACE_INSET_UM),
            "S": (x, y + FACE_INSET_UM)}.get(face, (x, y))


def planned_sinks(P, tn, bit_sites=False):
    """[(x, y, kind)] type-frame sites of the type's FIRM-planned clock sinks: one face register per bus pin (in and
    out ports register at the face, R2), ft slot station 0 at each in pin and stations j = 1..k-1 at L*j/k along the
    slot route (or at regs_um), as face_flops.tcl places them.  ft out pins carry no sink (the neighbour's station 0)."""
    import gen_phys
    t = P.types[tn]
    from ft_full_stage import load, centre
    full = load(P, tn)
    w, h = t["outline_um"]
    slots = {s["name"]: s for s in t.get("ft_slots", [])}
    pins = gen_phys.type_pins(P, tn)
    at = {(p[0], p[1]): (p[3], p[4], p[5]) for p in pins}
    exact_faces = {e["conn"][4:]: e for e in t.get("internal_stations", [])
                   if e.get("conn", "").startswith("bus:") and e.get("face_bit_sites_um")}
    out = [centre(row) + (f"ft_s{stage}",) for rows in full.values() for (stage, bit), row in sorted(rows.items())]
    for name, bit, _ln, x, y, face in pins:
        base, sfx = (name[:-2], name[-2:]) if name[-2:] in ("_i", "_o") else (name, "")
        if base in slots and sfx:
            if sfx == "_o":
                continue
            s = slots[base]
            if base in full:
                continue
            out.append(_inset(x, y, face, w, h) + ("ft_s0",))
            k = int(s.get("stations", 1))
            o = at.get((base + "_o", bit))
            if k < 2 or o is None:
                continue
            regs = s.get("regs_um", [])
            if bit_sites and s.get("bit_sites_um"):
                # explicit per-bit station sites (lower-left corners; check.py / die_hop_scan.py cell-centre rule)
                cw, ch = s["bit_site_cell_um"]
                for j in range(1, k):
                    bx, by = s["bit_sites_um"][j - 1][bit]
                    out.append((bx + cw / 2, by + ch / 2, f"ft_s{j}"))
                continue
            pts = _zroute((x, y), (o[0], o[1]), s["in_face"], s["out_face"])
            L = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))
            for j in range(1, k):
                xy = tuple(regs[j]) if len(regs) >= k else _point_at(pts, L * j / k)
                out.append((xy[0], xy[1], f"ft_s{j}"))
        else:
            if name in exact_faces:
                e=exact_faces[name];cw,ch=e["bit_site_cell_um"];bx,by=e["face_bit_sites_um"][bit]
                out.append((bx+cw/2,by+ch/2,"face"))
            else:
                out.append(_inset(x, y, face, w, h) + ("face",))
    for bus,e in exact_faces.items():
        # Payload face bits were counted above. Exact-bank physical metadata
        # also carries the epoch FF, which is not a payload bus pin.
        n=max((bit for name,bit,*_ in pins if name==bus),default=-1)+1
        cw,ch=e["bit_site_cell_um"]
        for bx,by in e["face_bit_sites_um"][n:]:
            out.append((bx+cw/2,by+ch/2,"face_epoch"))
    out += per_bit_station_sites(t, pins)
    return out


def per_bit_station_sites(t, pins):
    """[(x, y, 'ist')] sites of the internal stations with bit_route "per_bit" (HEAD-SPINE2 10-25), exactly as
    kit_istations.is_bits places them: bit b of station k (k = 0 next to the face for an in bus, next to the leaf for an
    out bus) at L_b * (k + 1) / (n + 1) along its own L leaf_um <-> pin b, the segment at the pin perpendicular to the
    face.  Entries without bit_route are not FIRM per bit and stay out (other plans unchanged)."""
    buses = {b["name"]: b for b in t.get("buses", [])}
    at = {}
    for name, bit, _ln, x, y, face in pins:
        at.setdefault(name, {})[bit] = (x, y, face)
    out = []
    for e in t.get("internal_stations", []):
        if e.get("bit_sites_um"):
            cw,ch=e["bit_site_cell_um"]
            for bank in e["bit_sites_um"]:
                out.extend((bx+cw/2,by+ch/2,"ist") for bx,by in bank)
            continue
        if e.get("bit_route") != "per_bit" or not e.get("conn", "").startswith("bus:"):
            continue
        bus = e["conn"][4:]
        lx, ly = e["leaf_um"]
        n = len(e["regs_um"])
        d_in = buses[bus]["dir"] == "in"
        for bit, (px, py, face) in sorted(at.get(bus, {}).items()):
            cx, cy = (lx, py) if face in ("E", "W") else (px, ly)
            pts = [(px, py), (cx, cy), (lx, ly)] if d_in else [(lx, ly), (cx, cy), (px, py)]
            L = abs(px - cx) + abs(py - cy) + abs(cx - lx) + abs(cy - ly)
            for k in range(n):
                xy = _point_at(pts, L * (k + 1) / (n + 1))
                out.append((xy[0], xy[1], "ist"))
    return out


def _median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def _kmedians(pts, k, iters=25):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    seed = min(pts, key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p))
    cen = [seed]
    dmin = [abs(p[0] - seed[0]) + abs(p[1] - seed[1]) for p in pts]
    while len(cen) < k:
        i = max(range(len(pts)), key=lambda j: (dmin[j], -j))
        c = pts[i]
        cen.append(c)
        dmin = [min(d, abs(p[0] - c[0]) + abs(p[1] - c[1])) for d, p in zip(dmin, pts)]
    asg = None
    for _ in range(iters):
        new = [min(range(len(cen)), key=lambda c: (abs(p[0] - cen[c][0]) + abs(p[1] - cen[c][1]), c)) for p in pts]
        if new == asg:
            break
        asg = new
        groups = [[] for _ in cen]
        for p, a in zip(pts, asg):
            groups[a].append(p)
        cen = [(_median([p[0] for p in g]), _median([p[1] for p in g])) if g else c for g, c in zip(groups, cen)]
    groups = [[] for _ in cen]
    for p, a in zip(pts, asg):
        groups[a].append(p)
    return cen, groups


def _root():
    from pathlib import Path
    return Path(__file__).resolve().parents[2]


def sink_sites(P, tn, control=True):
    """[(x, y, weight)] type-frame clock sinks for clock.tap_mode "density": the FIRM planned sinks (planned_sinks,
    weight 1) plus the plan's internal sink inventory -- clock.sink_sites_um ([x, y] or [x, y, n] rows) -- or, with
    clock.sink_bins_file (the full register inventory of a placed netlist, which already holds the face / ft
    registers, so planned_sinks are then left out) plus any sink_sites_um.  The bins file is repo-relative JSON
    {"bin_um": b, "bins": [[x, y, n], ...]}, written by `taps.py bins <odb dump.json>`: the registers of a placed
    netlist binned to their bin centres."""
    ck = P.types[tn].get("clock", {})
    if ck.get("native_domains") is not None:
        import native_clock_domains as NCD
        domain_sites=NCD.core_planning_sites(P,tn)
        if domain_sites is not None:
            if control and ck.get("control_sinks"):
                domain_sites += [(x,y,1.0) for _,x,y in control_pin_sinks(P,tn)]
            return domain_sites
        if ck.get("sink_sites_um") or ck.get("sink_bins_file"):
            raise ValueError("native-domain spatial planning requires explicit per-root sink sites; aggregate bins are unqualified")
    rows = list(ck.get("sink_sites_um", []))
    if ck.get("sink_bins_file"):
        # a placed netlist's inventory already holds the face / ft registers: the planned ones are not added again
        import json
        rows += json.loads((_root() / ck["sink_bins_file"]).read_text())["bins"]
        out = []
    else:
        out = [(x, y, 1.0) for x, y, _ in planned_sinks(P, tn, bit_sites=ck.get("tap_model") != "frozen_anchor")]
    out += [(float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 else 1.0) for r in rows]
    if control and ck.get("control_sinks"):
        out += [(x, y, 1.0) for _, x, y in control_pin_sinks(P, tn)]
    return [p for p in out if p[2] > 0]


def control_pin_sinks(P, tn):
    """[(port, x, y)] the registered control pins of a wavefront soft type: the reset IN (arst_n -> u_rst_in), the
    START IN (start_i -> u_run_in) and every registered reset / START OUT (rst_o_<k>, start_o_<k>).  Each is captured
    or launched by one register AT its pin (rule LC1: a boundary pin register is captured within its declared
    interface latency), so with clock.control_sinks a density-tap plan covers it like a face register: a control
    pin far from every data sink gets its own light tap within tap_radius_um instead of the nearest data tap's long
    arm (QC coll_ftm 10-25: START at the E face 513 um from clk_t18, FF hold -167.66 ps on start_i -> u_run_in)."""
    import reset_tree as RT
    t = P.types[tn]
    if t.get("hard") or not RT.wavefront(P):
        return []
    out = [("arst_n",) + tuple(RT.in_pin(P, tn))]
    if RT.start_broadcast(P):
        out.append(("start_i",) + tuple(RT.start_in_pin(P, tn)))
    out += [tuple(q) for q in RT.out_pins(P, tn) + RT.start_out_pins(P, tn)]
    return [(n, float(x), float(y)) for n, x, y in out]


def _wmedian(pts, i):
    """weighted median of coordinate i (lower median on ties: deterministic)."""
    s = sorted(pts, key=lambda p: (p[i], p[1 - i]))
    tot, acc = sum(p[2] for p in s), 0.0
    for p in s:
        acc += p[2]
        if acc >= tot / 2:
            return p[i]
    return s[-1][i]


def _bisect(pts, target, radius, blocked=lambda x, y: False, min_sinks=1):
    """capacity- and radius-bounded weighted median bisection (a balanced kd split along the longer extent): every leaf
    holds <= target sinks within `radius` (Manhattan) of its weighted L1 centre.  Unlike k-medians with coincident
    seeds, a dense bank can never silently overflow a tap: it is split until it fits (a single site heavier than the
    target stays one leaf).  A leaf whose centre falls in a keep-clear (`blocked`: a hard core) is split further, so
    a group straddling a core becomes one tap on each side instead of one tap pushed to the core edge."""
    pending, leaves = [pts], []
    while pending:
        g = pending.pop()
        x, y = _wmedian(g, 0), _wmedian(g, 1)
        n = sum(p[2] for p in g)
        r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
        if len(g) == 1 or (n <= target and r <= radius and not blocked(x, y)):
            leaves.append((x, y, n, r, g))
            continue
        ax = max((0, 1), key=lambda i: (max(p[i] for p in g) - min(p[i] for p in g), -i))
        g = sorted(g, key=lambda p: (p[ax], p[1 - ax]))
        acc, k = 0.0, 1
        for k, p in enumerate(g[:-1], 1):
            acc += p[2]
            if acc >= n / 2:
                break
        pending += [g[k:], g[:k]]
    return _absorb(_merge(leaves, target, radius, blocked), target, min_sinks, radius)


def _absorb(leaves, target, min_sinks, radius):
    """Merge light clusters only while every sink stays within the tap radius.

    A remote control bank needs its own spine drop even when it has few sinks;
    attaching it to a data band creates a long clock arm and delays that band.
    """
    leaves = sorted(leaves, key=lambda a: (-a[2], round(a[1], 3), round(a[0], 3)))
    keep = [q for q in leaves if q[2] >= min_sinks]
    if not keep:
        return leaves
    for x, y, n, _, g in (q for q in leaves if q[2] < min_sinks):
        room = [k for k, q in enumerate(keep) if q[2] + n <= target
                and all(abs(p[0]-q[0])+abs(p[1]-q[1]) <= radius for p in g)]
        if not room:
            keep.append((x, y, n, max(abs(p[0]-x)+abs(p[1]-y) for p in g), g))
            continue
        k = min(room, key=lambda k: (abs(keep[k][0] - x) + abs(keep[k][1] - y), k))
        a = keep[k]
        keep[k] = (a[0], a[1], a[2] + n, max(a[3], max(abs(p[0] - a[0]) + abs(p[1] - a[1]) for p in g)), a[4] + g)
    return keep


_EXACT_SUM = float(1 << 53)    # integer-valued float weights sum exactly (in any order) below 2**53


def _median_index(pts):
    """((keys, prefix) for axis 0, (keys, prefix) for axis 1, total) of a leaf's sinks for the exact union weighted
    median (_union_wmedian), or None when that median could differ from _wmedian in any bit.  keys = the sinks'
    _wmedian sort keys (p[i], p[1-i]) in sorted order, prefix[k] = weight of the first k.  Qualifies only plain finite
    non-zero float coordinates (equal keys are then the same bits; a +-0.0 / int / NaN coordinate keeps _wmedian) and
    positive integer-valued float weights summing below 2**53 (every partial sum exact, so the order of the old
    sorted-order accumulation cannot change a sum or a comparison with tot / 2)."""
    tot = 0.0
    for p in pts:
        x, y, w = p[0], p[1], p[2]
        if type(x) is not float or type(y) is not float or type(w) is not float:
            return None
        if x == 0.0 or y == 0.0 or not (math.isfinite(x) and math.isfinite(y)) or not (w > 0 and w.is_integer()):
            return None
        tot += w
    if tot >= _EXACT_SUM:
        return None
    return _axis_index([(p[0], p[1], p[2]) for p in pts]) + _axis_index([(p[1], p[0], p[2]) for p in pts]) + (tot,)


def _axis_index(rows):
    rows.sort()
    pre, acc = [0.0], 0.0
    for row in rows:
        acc += row[2]
        pre.append(acc)
    return ((rows, [row[:2] for row in rows], pre),)


def _merge_index(A, B):
    """the _median_index of the union of two qualified leaves (both sorted runs: Timsort merges them in linear time)."""
    out = ()
    for (ra, _, _), (rb, _, _) in zip(A[:2], B[:2]):
        out += _axis_index(ra + rb)
    return out + (A[2] + B[2],)


def _union_wmedian(a, b, half):
    """_wmedian(ga + gb, i) from the axis-i indexes a, b of two qualified leaves: the smallest sort key K of the union
    with W(key <= K) >= tot / 2 (the first sorted sink whose running weight reaches tot / 2 carries exactly that key),
    by binary search on each side (the cumulative weight is monotone in the key).  Returns K[0] = p[i]."""
    from bisect import bisect_right
    best = None
    for (_, k1, p1), (_, k2, p2) in ((a, b), (b, a)):
        lo, hi = 0, len(k1)
        while lo < hi:
            mid = (lo + hi) // 2
            if p1[mid + 1] + p2[bisect_right(k2, k1[mid])] >= half:
                hi = mid
            else:
                lo = mid + 1
        if lo < len(k1) and (best is None or k1[lo] < best):
            best = k1[lo]
    return best[0]


_DIRS = ((1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0))   # index d and 3 - d are opposite directions
_GEO_ABS_UM = 1e5     # coordinate bound of the bounded radius search (any die frame is a few mm)
_GEO_TOL_UM = 1e-6    # >> the float error of an L1 distance below 4e5 um (< 1e-9 um), << any planned distance


def _geo_index(pts):
    """per direction s of _DIRS the leaf's sinks as [(-(s . p), p[0], p[1])] ascending (the farthest along s first),
    or None unless every coordinate is a finite float with |v| < _GEO_ABS_UM (then the bounded radius of
    _radius_within is exact)."""
    for p in pts:
        x, y = p[0], p[1]
        if type(x) is not float or type(y) is not float or not (abs(x) < _GEO_ABS_UM and abs(y) < _GEO_ABS_UM):
            return None
    return tuple(sorted((-(sx * p[0] + sy * p[1]), p[0], p[1]) for p in pts) for sx, sy in _DIRS)


def _merge_geo(A, B):
    return tuple(sorted(a + b) for a, b in zip(A, B))


def _spread_lb(A, B):
    """a lower bound of the L1 radius about ANY centre of the union of two _geo_index leaves: half its diagonal extent
    max_s (M_s + M_-s) / 2, M_s = max s . p (float, within _GEO_TOL_UM of exact)."""
    m = [-min(A[d][0][0], B[d][0][0]) for d in range(4)]
    return max(m[0] + m[3], m[1] + m[2]) / 2


def _radius_within(A, B, x, y, radius):
    """max(abs(p[0] - x) + abs(p[1] - y) for p in the union), exactly as that generator gives it, or None when it is
    > radius.  The L1 distance is max_s s . (p - c), so the exact radius is D = max_s (M_s - s . c); a sink whose s . p
    is below D + s . c - _GEO_TOL_UM in every direction is farther than float rounding from the maximum and cannot
    be (or tie) it, so the old formula on the remaining near-extreme sinks gives the same float maximum."""
    m = [-min(A[d][0][0], B[d][0][0]) for d in range(4)]
    sc = [sx * x + sy * y for sx, sy in _DIRS]
    D = max(m[d] - sc[d] for d in range(4))
    if D > radius + _GEO_TOL_UM:
        return None
    r = None
    for d in range(4):
        thr = -(D + sc[d] - _GEO_TOL_UM)
        for L in (A[d], B[d]):
            for v, px, py in L:
                if v > thr:
                    break
                q = abs(px - x) + abs(py - y)
                if r is None or q > r:
                    r = q
    if r is None:       # unreachable: the sink attaining D is always kept; stay exact regardless
        r = max(abs(px - x) + abs(py - y) for L in (A[0], B[0]) for _, px, py in L)
    return r


class _Keepout:
    """blocked(x, y) of density_taps: (x, y) strictly inside a hard-core keep-clear box (the same test as the lambda it
    replaces).  _merge reads `boxes` to skip pairs that this test rejects whatever their median (_sure_blocked)."""
    __slots__ = ("boxes",)

    def __init__(self, boxes):
        self.boxes = tuple(tuple(b) for b in boxes)

    def __call__(self, x, y):
        return any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in self.boxes)


_NO_BOXES = (frozenset(), frozenset())


def _box_key(boxes, pts):
    """(BX, BY): the keep-clear boxes whose open x (BX) / y (BY) interval holds EVERY sink's x / y of pts (finite float
    sinks only, else no box).  The key of a union is the intersection of its parts' keys."""
    if not boxes:
        return _NO_BOXES
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if any(type(v) is not float or not math.isfinite(v) for v in xs + ys):
        return _NO_BOXES
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    return (frozenset(k for k, (x0, _, x1, _) in enumerate(boxes) if x0 < lo_x and hi_x < x1),
            frozenset(k for k, (_, y0, _, y1) in enumerate(boxes) if y0 < lo_y and hi_y < y1))


def _sure_blocked(ka, kb):
    """True when _Keepout rejects the weighted median of the union of two leaves with box keys ka, kb, whatever it
    is.  The median is (x, y) with x, y the coordinates of union sinks (_wmedian / _union_wmedian return a sink's).
    If boxes b1 in BYa, b2 in BYb both lie in BXa & BXb, every union x is inside both x intervals, and y comes from
    a (inside b1's y interval) or from b (inside b2's): (x, y) is strictly inside b1 or b2.  Likewise with x, y swapped."""
    (xa, ya), (xb, yb) = ka, kb
    X, Y = xa & xb, ya & yb
    return bool((ya & X and yb & X) or (xa & Y and xb & Y))


def _median_box(np, own_ax, w):
    """per partner weight w: (x_lo, x_hi, y_lo, y_hi) holding the union weighted median of the owner (median index
    own_index, total W) and any partner of weight w.  The union key K* is the least key whose union weight reaches
    (W + w) / 2, so the owner's own weight up to K* is >= (W - w) / 2 and K* <= the owner's least key whose weight
    reaches (W + w) / 2 (if any): x* lies between those keys' x (keys sort on x first; likewise y)."""
    if own_ax is None:
        inf = np.full(len(w), np.inf)
        return -inf, inf, -inf, inf
    ax, W = own_ax
    out = []
    for v, pre, _ in ax:
        c = pre[1:]
        lo_t, hi_t = (W - w) / 2, (W + w) / 2
        lo = v[np.minimum(np.searchsorted(c, lo_t, side="left"), len(v) - 1)]
        hi = v[np.minimum(np.searchsorted(c, hi_t, side="left"), len(v) - 1)]
        out += [np.where(lo_t > 0, lo, -np.inf), np.where(hi_t <= W, hi, np.inf)]
    return tuple(out)


def _single_wmedian(np, v, pre, codes, cq, qv, w, W):
    """_union_wmedian of an indexed leaf (axis keys coded as `codes`, their coordinate `v`, prefix weights `pre`,
    total W) with each single sink q (key code cq, coordinate qv, weight w), vectorized: the owner's first key t whose
    union weight reaches half = (W + w) / 2 (q counts from the first owner key >= q's key) against q's own key, the
    smaller key wins.  Codes are exact ranks of the (p[i], p[1-i]) keys, so they order exactly as the key tuples."""
    n = len(v)
    half = (W + w) / 2
    pos = np.searchsorted(codes, cq, side="left")
    posr = np.searchsorted(codes, cq, side="right")
    c1 = pre[1:]
    i1 = np.searchsorted(c1, half, side="left")
    i2 = np.searchsorted(c1, half - w, side="left")
    tk = np.where(i1 < pos, i1, np.maximum(pos, i2))
    kval = tk < n
    tkc = np.minimum(tk, n - 1)
    useq = (pre[posr] + w >= half) & (~kval | (cq <= codes[tkc]))
    if not np.all(useq | kval):
        raise AssertionError("taps._single_wmedian: no median (weights not exact)")
    return np.where(useq, qv, v[tkc])


def _pair_keys(own, cand, target, radius, sb_row, np_arrays=None, leaf=None, own_ax=None):
    """(keys, js) (ascending without numpy; unsorted numpy arrays with it) for the pairs (own, j), j in cand, that can pass the merge offer: weight and centre tests
    exactly as offer computes them, minus pairs blocked whatever their median (_sure_blocked, sb_row[group]) and pairs
    whose union cannot fit the radius about any centre (_spread_lb).  key < the pair's exact r (a lower bound
    minus _GEO_TOL_UM; -inf without a geometry index): the cursor of `own` reaches the heap before the pair could."""
    if np_arrays is not None:
        np, X, Y, Wt, M, G, Q = np_arrays
        j = cand[~sb_row[G[cand]]] if sb_row.any() else cand
        j = j[~((Wt[own] + Wt[j] > target) | (np.abs(X[own] - X[j]) + np.abs(Y[own] - Y[j]) > 2 * radius))]
        if not len(j):
            return np.zeros(0), j
        with np.errstate(invalid="ignore"):
            mu = np.maximum(M[own], M[j])
            lb = np.maximum(mu[:, 0] + mu[:, 3], mu[:, 1] + mu[:, 2]) / 2
            # the union median lies in _median_box: r >= max_s (M_s - max of s . c over that box)
            # (both leaves qualified for _median_index: the old float sums are then exact)
            x_lo, x_hi, y_lo, y_hi = _median_box(np, own_ax() if own_ax else None, Wt[j])
            box = lb
            for d, (sx, sy) in enumerate(_DIRS):
                box = np.maximum(box, mu[:, d] - ((x_hi if sx > 0 else -x_lo) + (y_hi if sy > 0 else -y_lo)))
            lb = np.where(Q[j], box, lb)
            fin = np.isfinite(lb)
            keep = ~(fin & (lb > radius + _GEO_TOL_UM))
        j, lb, fin = j[keep], lb[keep], fin[keep]
        return np.where(fin, lb - _GEO_TOL_UM, -np.inf), j          # unsorted: the caller sorts
    a = leaf(own)
    out = []
    for j in cand:
        b = leaf(j)
        if a[2] + b[2] > target or abs(a[0] - b[0]) + abs(a[1] - b[1]) > 2 * radius or sb_row(j):
            continue
        ga, gb = a[5], b[5]
        if ga is not None and gb is not None:
            lb = _spread_lb(ga, gb)
            if lb > radius + _GEO_TOL_UM:
                continue
            out.append((lb - _GEO_TOL_UM, j))
        else:
            out.append((-math.inf, j))
    out.sort(key=lambda q: q[0])
    return [q[0] for q in out], [q[1] for q in out]


def _merge(leaves, target, radius, blocked=lambda x, y: False):
    """bisection cuts along the median, so a sparse channel or an L-shaped region ends up in many small leaves (dead-ish
    taps of a few hundred sinks next to each other).  Greedily merge the pair of leaves whose union still fits the
    target and radius with the smallest merged radius, until no pair fits.  Deterministic."""
    # Surviving leaves keep their relative order and each new merge is appended.
    # Monotonic IDs therefore preserve the original (radius, list-i, list-j)
    # tie break while unchanged pairs retain their previously computed cost.
    # DIE-QC-97 TAPS-MERGE 11-11: the same merges in the same order as the all-pairs heap form (offer every pair, then
    # every new leaf against every live leaf), by construction:
    #  - pairs are offered lazily.  Each leaf keeps its candidate pairs (initial leaf i: j > i; merged leaf k: every
    #    live j < k) sorted by a key below the pair's exact cost r (_pair_keys); only its cursor sits in the heap as
    #    (key, -1, leaf).  A popped cursor offers its pair exactly as before and re-enters with the next key.  A
    #    pair whose exact entry (r, i, j, x, y) would pop before another's is therefore always offered first: its
    #    cursor key is < r.  Exact entries are unique in (i, j), so pop order depends on the entries only, and a
    #    cursor of a merged-away leaf (all its pairs stale) is dropped.
    #  - pairs failing the weight / centre test, pairs blocked whatever their median (density_taps' _Keepout,
    #    _sure_blocked) and pairs no centre fits (_spread_lb) are never offered: the old offer dropped them too.
    #  - the merged weighted median comes from per-leaf sorted indexes (_union_wmedian), bit-identical to
    #    _wmedian(a[4] + b[4], i) for qualified leaves (_median_index); any other leaf keeps _wmedian.
    #  - r is the same float max over the same sinks (order-free without NaN), from the near-extreme sinks only
    #    (_radius_within); other leaves keep the full max.
    #  - a qualified leaf's offers with single-sink partners are computed at once (batch, _single_wmedian: the
    #    same median, r = max(leaf part, partner distance), blocked) and kept sorted; only the least is in the heap,
    #    the next one enters when it pops stale (advance).  Its merge retires the rest with the leaf.
    import heapq
    live = dict(enumerate(leaves))
    pending = []
    boxes = blocked.boxes if type(blocked) is _Keepout else ()
    n_ids = 2 * len(leaves) + 1
    inside, index, geo, gid, keys = {}, {}, {}, {}, []

    def group(k, key=None):
        key = _box_key(boxes, live[k][4]) if key is None else key
        inside[k] = key
        if key not in gid:
            gid[key] = len(keys)
            keys.append(key)
        return gid[key]

    try:
        import numpy as np
        if not all(type(v) in (float, int) for q in leaves for v in q[:3]):
            raise ImportError
    except ImportError:
        np = None
    if np is not None:
        # exact ranks of every sink coordinate: (p[i], p[1-i]) sort keys coded as integers (_single_wmedian)
        vals = sorted({v for q in leaves for p in q[4] for v in p[:2] if type(v) is float and math.isfinite(v)})
        rank = {v: k for k, v in enumerate(vals)}
        U = len(vals) + 1
        SX, SY = np.zeros(n_ids), np.zeros(n_ids)
        CX, CY = np.zeros(n_ids, dtype=np.int64), np.zeros(n_ids, dtype=np.int64)
        S1 = np.zeros(n_ids, dtype=bool)
        X, Y, Wt = np.zeros(n_ids), np.zeros(n_ids), np.zeros(n_ids)
        M = np.full((n_ids, 4), np.nan)
        G = np.zeros(n_ids, dtype=np.int64)
        alive = np.zeros(n_ids, dtype=bool)
        Q = np.zeros(n_ids, dtype=bool)
        arrays = (np, X, Y, Wt, M, G, Q)
        rows = {}

    def enter(k, key=None, ga=None):
        """index leaf k (live[k] set): box group, geometry index, numpy row."""
        g = group(k, key)
        geo[k] = _geo_index(live[k][4]) if ga is None else ga
        if np is not None:
            q = live[k]
            X[k], Y[k], Wt[k], G[k], alive[k], Q[k] = q[0], q[1], q[2], g, True, idx(k) is not None
            if geo[k] is not None:
                M[k] = [-geo[k][d][0][0] for d in range(4)]
                if Q[k] and len(q[4]) == 1:     # a qualified single sink: exact batch offers (batch)
                    px, py = q[4][0][0], q[4][0][1]
                    SX[k], SY[k], S1[k] = px, py, True
                    CX[k], CY[k] = rank[px] * U + rank[py], rank[py] * U + rank[px]

    def sb_row(k):
        g = gid[inside[k]]
        if np is None:
            return lambda j: _sure_blocked(keys[g], inside[j])
        row = rows.get(g)
        if row is None or len(row) < len(keys):
            row = rows[g] = np.array([_sure_blocked(keys[g], h) for h in keys], dtype=bool)
        return row

    cursor, batches, coded = {}, {}, {}

    def code(k):
        """k's median index as arrays: per axis (coordinate, prefix weights, exact key codes), total weight."""
        if k not in coded:
            ix = index[k]
            coded[k] = ([(np.array([q[0] for q in rows]), np.array(pre),
                          np.array([rank[q[0]] * U + rank[q[1]] for q in rows], dtype=np.int64))
                         for rows, _, pre in ix[:2]], ix[2])
        return coded[k]

    def candidates(k, ids):
        ks, js = _pair_keys(k, ids, target, radius, sb_row(k), arrays if np is not None else None,
                            None if np is not None else (lambda j: live[j][:5] + (geo[j],)),
                            (lambda: code(k)) if np is not None and Q[k] else None)
        if np is not None:
            if Q[k] and geo[k] is not None:
                one = S1[js]
                batch(k, js[one])
                ks, js = ks[~one], js[~one]
            o = np.argsort(ks, kind="stable")
            ks, js = ks[o].tolist(), js[o].tolist()
        if js:
            cursor[k] = [ks, js, 0]
            heapq.heappush(pending, (ks[0], -1, k))

    def batch(k, js):
        """the exact offers of k with single-sink partners js at once (offer's median / r / blocked, vectorized):
        sorted (r, i, j, x, y) entries of which only the least sits in the heap (the rest cannot pop before it)."""
        if not len(js):
            return
        ax, W = code(k)
        qx, qy, w = SX[js], SY[js], Wt[js]
        x = _single_wmedian(np, ax[0][0], ax[0][1], ax[0][2], CX[js], qx, w, W)
        y = _single_wmedian(np, ax[1][0], ax[1][1], ax[1][2], CY[js], qy, w, W)
        d = np.abs(qx - x) + np.abs(qy - y)
        xy = np.empty(len(x), dtype=np.complex128)        # exact (x, y) pairs, ordered by x then y
        xy.real, xy.imag = x, y
        cen, inv = np.unique(xy, return_inverse=True)
        inv = inv.reshape(-1)
        cen = list(zip(cen.real.tolist(), cen.imag.tolist()))
        rk = np.array([_radius_within(geo[k], geo[k], cx_, cy_, math.inf) for cx_, cy_ in cen])
        r = np.maximum(rk[inv], d)
        ok = r <= radius
        if not ok.any():
            return
        used = np.unique(inv[ok])
        blk = np.zeros(len(cen), dtype=bool)
        blk[used] = [bool(blocked(*cen[u])) for u in used.tolist()]
        ok &= ~blk[inv]
        if not ok.any():
            return
        jj, r, x, y = js[ok], r[ok], x[ok], y[ok]
        i_, j_ = np.minimum(jj, k), np.maximum(jj, k)
        o = np.lexsort((j_, i_, r))
        batches[k] = [(r[o], i_[o], j_[o], x[o], y[o]), 0]
        heapq.heappush(pending, head(k))

    def head(o):
        (r, i_, j_, x, y), p = batches[o]
        return (float(r[p]), int(i_[p]), int(j_[p]), float(x[p]), float(y[p]))

    def advance(i, j):
        """a stale exact entry (i, j) that heads a live leaf's batch: put that batch's next entry in the heap."""
        for o in (i, j):
            b = batches.get(o)
            if b is not None and o in live and head(o)[1:3] == (i, j):
                b[1] += 1
                if b[1] < len(b[0][0]):
                    heapq.heappush(pending, head(o))
                else:
                    del batches[o]

    def idx(k):
        if k not in index:
            index[k] = _median_index(live[k][4])
        return index[k]

    def offer(i, j):
        a, b = live[i], live[j]
        if a[2] + b[2] > target or abs(a[0] - b[0]) + abs(a[1] - b[1]) > 2 * radius:
            return
        ga, gb = geo[i], geo[j]
        if ga is not None and gb is not None and _spread_lb(ga, gb) > radius + _GEO_TOL_UM:
            return          # every centre is farther than radius from some sink: the old r <= radius test fails
        ia, ib = idx(i), idx(j)
        if ia is not None and ib is not None:
            half = (ia[2] + ib[2]) / 2
            x, y = _union_wmedian(ia[0], ib[0], half), _union_wmedian(ia[1], ib[1], half)
        else:
            g = a[4] + b[4]
            x, y = _wmedian(g, 0), _wmedian(g, 1)
        if ga is not None and gb is not None and math.isfinite(x) and math.isfinite(y):
            r = _radius_within(ga, gb, x, y, radius)
            if r is None:
                return
        else:
            r = max(abs(p[0] - x) + abs(p[1] - y) for p in a[4] + b[4])
        if r <= radius and not blocked(x, y):
            heapq.heappush(pending, (r, i, j, x, y))

    L = len(leaves)
    for k in live:
        enter(k)
    for i in range(L):
        candidates(i, np.arange(i + 1, L) if np is not None else range(i + 1, L))
    next_id = L
    while pending:
        e = heapq.heappop(pending)
        if e[1] == -1:                      # a leaf's cursor: offer its next pair
            k = e[2]
            if k not in live:
                continue
            c = cursor[k]
            ks, js, n = c
            j = js[n]
            c[2] = n + 1
            if n + 1 < len(js):
                heapq.heappush(pending, (ks[n + 1], -1, k))
            if j in live:
                offer(min(k, j), max(k, j))
            continue
        r, i, j, x, y = e
        if i not in live or j not in live:
            advance(i, j)
            continue
        ia, ib = index.pop(i, None), index.pop(j, None)
        ga, gb = geo.pop(i), geo.pop(j)
        key = (inside[i][0] & inside[j][0], inside[i][1] & inside[j][1])     # = _box_key of the union
        for q in (i, j):
            inside.pop(q)
            cursor.pop(q, None)
            batches.pop(q, None)
            coded.pop(q, None)
            if np is not None:
                alive[q] = False
        a, b = live.pop(i), live.pop(j)
        k = next_id
        next_id += 1
        live[k] = (x, y, a[2] + b[2], r, a[4] + b[4])
        if ia is not None and ib is not None:
            index[k] = _merge_index(ia, ib)
        enter(k, key, _merge_geo(ga, gb) if ga is not None and gb is not None else None)
        if np is not None:
            candidates(k, np.flatnonzero(alive[:k]))
        else:
            candidates(k, [o for o in live if o != k])
    return list(live.values())


def explicit_tap_sites(P, tn):
    """Fixed explicit endpoints for acyclic reset/START placement, geometry checked.

    This first phase never enumerates sinks or invokes the wavefront solver.
    Budget consumers must use explicit_taps, which adds all control-pin sinks.

    Materializing a density-derived table breaks control-relay/tap coordinate
    feedback. No endpoint is moved, added, dropped or silently re-legalized.
    The normal density CTS/load/balance recipe still applies to these ports.
    """
    import schema
    ck=P.types[tn].get("clock",{})
    if ck.get("child_root_taps") is not None:
        return child_root_tap_sites(P, tn)
    table=[p for p in ck.get("taps",[]) if p.get("kind")!="core"]
    if not table:
        raise ValueError(f"{tn}: explicit tap table is empty")
    names=[p["name"] for p in table]
    expected=["clk"]+[f"clk_t{i}" for i in range(1,len(table))]
    if names!=expected:
        raise ValueError(f"{tn}: explicit local tap names/order must be {expected}")
    out=[];taken=[(x,y) for _,x,y,_ in schema.core_taps(P,tn)]
    for p in table:
        x,y=map(float,p["xy"])
        # Frozen density coordinates are rounded to 4 decimals. Check the
        # same halo/spacing geometry directly; binary 8.64-8.64 subtraction
        # must not trigger a fresh legalizer move (t43 gap 8.639999999999986).
        eps=1e-8
        clear=schema.TAP_CLEAR_UM
        typ=P.types[tn];w,h=typ["outline_um"]
        from placement_obstacles import placement_boxes
        boxes=list(placement_boxes(typ,halo=clear).values())
        boxes += [(a-clear,b-clear,c+clear,d+clear) for a,b,c,d in ck.get("keepouts_um",[])]
        legal=(clear-eps<=x<=w-clear+eps and clear-eps<=y<=h-clear+eps
               and not any(abs(x-a)<clear-eps and abs(y-b)<clear-eps for a,b in taken)
               and not any(a+eps<x<c-eps and b+eps<y<d-eps for a,b,c,d in boxes))
        if not legal:
            raise ValueError("{}: explicit tap {} violates outline/halo/tap spacing".format(tn,p["name"]))
        out.append((p["name"],x,y));taken.append((x,y))
    return out


CHILD_ROOT_SEP_UM = 1e-3   # two child-root landings may not share one point


def _child_boxes(t):
    """{hard core inst: placed box (type frame, origin + track_offset, R0/MX/MY/R180 keep the outline)}"""
    out = {}
    for hc in t.get("hard_cores") or []:
        (x, y), (w, h) = hc["origin_um"], hc["outline_um"]
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        out[hc["inst"]] = (x + dx, y + dy, x + dx + w, y + dy + h)
    return out


def child_root_tap_sites(P, tn):
    """clock.child_root_taps (DIE-S81-85 11-09): a soft parent with NO flip-flop of its own (every register of the
    type sits in its hard children, clock.child_root_taps.parent_ffs == 0) has no parent clock buffer to site.  Each
    explicit type tap (names clk, clk_t1 .. in order, as explicit mode) LANDS ON child clock root pins: tap.lands_on =
    [{pin: "<child inst>.<root port>", xy: type-frame pin centre}, ...]; the die clock (M9/M8) drops onto the first
    landing (tap xy = lands_on[0].xy) and reaches any further landing of the same root by a parent wire within
    clock.tap_radius_um.  Legal: inside the outline; each landing inside its own child's placed box (the halo rule does
    not apply to the landed child: the landing IS its pin); outside every other hard core / keepout box (+ TAP_CLEAR);
    landings never coincide.  Spacing is measured between landing pins, not as an empty parent site.  check.py
    (check_taps_cores) proves each landing xy = the child's pin table (origin + track_offset + pin).  No parent sink is
    assigned: a parent with registers cannot use this class (and every ft slot with stations declares stations_in)."""
    import schema
    t = P.types[tn]
    ck = t.get("clock", {})
    cr = ck.get("child_root_taps") or {}
    if cr.get("parent_ffs") != 0:
        raise ValueError(f"{tn}: clock.child_root_taps needs parent_ffs 0 (a parent register needs a parent tap)")
    if ck.get("tap_mode") != "explicit":
        raise ValueError(f"{tn}: clock.child_root_taps needs tap_mode explicit")
    boxes = _child_boxes(t)
    if not boxes:
        raise ValueError(f"{tn}: clock.child_root_taps needs hard_cores (the children that hold every register)")
    for s in t.get("ft_slots") or []:
        if int(s.get("stations", 1)) > 0 and not s.get("stations_in"):
            raise ValueError(f"{tn}: clock.child_root_taps: ft slot {s['name']} has stations but no stations_in child")
    table = [p for p in ck.get("taps", []) if p.get("kind") != "core"]
    if not table:
        raise ValueError(f"{tn}: explicit tap table is empty")
    names = [p["name"] for p in table]
    expected = ["clk"] + [f"clk_t{i}" for i in range(1, len(table))]
    if names != expected:
        raise ValueError(f"{tn}: explicit local tap names/order must be {expected}")
    eps, clear = 1e-8, schema.TAP_CLEAR_UM
    w, h = t["outline_um"]
    from placement_obstacles import placement_boxes
    others = placement_boxes(t, halo=clear)
    keep = [(a - clear, b - clear, c + clear, d + clear) for a, b, c, d in ck.get("keepouts_um", [])]
    seen, out = [], []
    for p in table:
        lands = p.get("lands_on") or []
        if not lands:
            raise ValueError(f"{tn}: child-root tap {p['name']} has no lands_on")
        x, y = map(float, p["xy"])
        if abs(x - lands[0]["xy"][0]) > 1e-4 or abs(y - lands[0]["xy"][1]) > 1e-4:
            raise ValueError(f"{tn}: child-root tap {p['name']} xy {p['xy']} != its first landing {lands[0]['xy']}")
        for ld in lands:
            inst, _, pin = ld["pin"].rpartition(".")
            if inst not in boxes or not pin:
                raise ValueError(f"{tn}: child-root tap {p['name']} lands on {ld['pin']}: not a hard core pin of the type")
            lx, ly = map(float, ld["xy"])
            a, b, c, d = boxes[inst]
            if not (a - eps <= lx <= c + eps and b - eps <= ly <= d + eps):
                raise ValueError(f"{tn}: child-root tap {p['name']} landing {ld['pin']} outside its child box")
            if not (-eps <= lx <= w + eps and -eps <= ly <= h + eps):
                raise ValueError(f"{tn}: child-root tap {p['name']} landing {ld['pin']} outside the outline")
            hit = [n for n, (a_, b_, c_, d_) in others.items()
                   if n != inst and a_ + eps < lx < c_ - eps and b_ + eps < ly < d_ - eps]
            if hit or any(a_ + eps < lx < c_ - eps and b_ + eps < ly < d_ - eps for a_, b_, c_, d_ in keep):
                raise ValueError(f"{tn}: child-root tap {p['name']} landing {ld['pin']} inside {hit or 'a keepout'}")
            if any(abs(lx - u) < CHILD_ROOT_SEP_UM and abs(ly - v) < CHILD_ROOT_SEP_UM for u, v in seen):
                raise ValueError(f"{tn}: child-root tap {p['name']} landing {ld['pin']} coincides with another landing")
            seen.append((lx, ly))
        out.append((p["name"], x, y))
    return out


def explicit_taps(P, tn):
    """Validate every actual data/control sink against the frozen explicit endpoints.

    Reset/START placement reads geometry-only explicit_tap_sites while solving
    control locations. Once those are known, full budget validation remains
    mandatory here; no zero-load/placeholder budget result is cached.
    """
    out = explicit_tap_sites(P, tn)
    ck = P.types[tn].get("clock", {})
    if ck.get("child_root_taps") is not None:
        # child-root class: the load of a tap is its landed child root pins (the child's own signed tree below them);
        # the parent has no register to assign.  Radius = farthest landing from the die drop.
        radius = float(ck.get("tap_radius_um", 200.))
        res = []
        for (name, x, y), p in zip(out, [q for q in ck["taps"] if q.get("kind") != "core"]):
            far = max(abs(float(ld["xy"][0]) - x) + abs(float(ld["xy"][1]) - y) for ld in p["lands_on"])
            if far > radius + 1e-6:
                raise ValueError(f"{tn}: child-root tap {name} reaches a landing {far:g} um > radius {radius}")
            res.append((name, x, y, len(p["lands_on"]), far))
        return res
    sinks=sink_sites(P,tn)
    cap=int(ck.get("tap_max_sinks",1500));radius=float(ck.get("tap_radius_um",200.))
    if cap<=0 or radius<=0:
        raise ValueError(f"{tn}: explicit tap radius/capacity must be positive")
    load,far,_=assign(out,sinks,cap,radius,max_distance_um=radius)
    for i,(n,r) in enumerate(zip(load,far)):
        if n>cap or r>radius+1e-6 or n==0:
            raise ValueError(f"{tn}: explicit tap {out[i][0]} load={n:g}/{cap}, radius={r:g}/{radius}, empty={n==0}")
    return [(name,x,y,n,r) for (name,x,y),n,r in zip(out,load,far)]


def grid_explicit_sites(P, tn):
    """clock.tap_mode "grid+explicit" (DIE-S81-39 10-31, COORD 23:5x plan_geom fold-in): the R4 grid EXACTLY as grid
    mode gives it (schema._grid_taps: same names, xy, order; a grid tap may carry no PLANNED sink, as in grid mode,
    because the plan sink inventory is a lower bound of the netlist) plus clock.added_taps [{name, xy}]: light taps
    where planned sinks are beyond the radius or a grid tap is over the cap.  Geometry only (reset/START siting reads
    this, like explicit_tap_sites); every added tap is checked like an explicit endpoint (outline, halo, spacing)."""
    import schema
    ck = P.types[tn].get("clock", {})
    grid = schema._grid_taps(P, tn)
    table = ck.get("added_taps", []) or []
    names = [p["name"] for p in table]
    expected = [f"clk_t{len(grid) + i}" for i in range(len(table))]
    if names != expected:
        raise ValueError(f"{tn}: grid+explicit added tap names/order must be {expected}")
    eps = 1e-8
    clear = schema.TAP_CLEAR_UM
    typ = P.types[tn]
    w, h = typ["outline_um"]
    from placement_obstacles import placement_boxes
    boxes = list(placement_boxes(typ, halo=clear).values())
    taken = [(x, y) for _, x, y in grid]
    out = list(grid)
    for p in table:
        x, y = map(float, p["xy"])
        legal = (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
                 and not any(abs(x - a) < clear - eps and abs(y - b) < clear - eps for a, b in taken)
                 and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes))
        if not legal:
            raise ValueError(f"{tn}: added tap {p['name']} violates outline/halo/tap spacing")
        out.append((p["name"], x, y))
        taken.append((x, y))
    return out


ADDED_TAP_RADIUS_SLACK = 1.10


def grid_explicit_taps(P, tn):
    """Validate grid+explicit on the kit split (assign: nearest + cap): every ADDED tap non-empty, <= tap_max_sinks
    and every sink it takes within tap_radius_um.  The R4 grid taps keep exactly the grid-mode rules (COORD 00:2x)."""
    import schema
    out = grid_explicit_sites(P, tn)
    n_grid = len(schema._grid_taps(P, tn))
    ck = P.types[tn].get("clock", {})
    sinks = sink_sites(P, tn)
    if not P.types[tn].get("hard"):
        # the reset relay registers (reset_tree.for_type relays, sited from the geometry-only tap read) are clocked
        # flops of this type too: an added tap that only clocks a relay chain far from the data sinks is not empty
        import reset_tree as RT
        sinks = sinks + [(float(r["xy"][0]), float(r["xy"][1]), 1.0) for r in RT.for_type(P, tn).get("relays", [])]
    cap = int(ck.get("tap_max_sinks", 1500))
    radius = float(ck.get("tap_radius_um", 200.))
    if cap <= 0 or radius <= 0:
        raise ValueError(f"{tn}: grid+explicit tap radius/capacity must be positive")
    load, far, _ = assign(out, sinks, cap, radius, max_distance_um=radius)
    # KW-FIX-28 11-07 (OWNER 11-03 targets, not gates): the radius is a target; a small overrun reports and goes on to CTS and
    # sign-off (leaf t24, t58, t68 at 1.04-1.08 x 200 um stopped at kit_rtl and failed the whole strict bind).  A far tap
    # still stops here: that is a wrong site, not a near miss.
    for i, (n, r) in enumerate(zip(load, far)):
        if i >= n_grid and (n > cap or r > radius * ADDED_TAP_RADIUS_SLACK + 1e-6 or n == 0):      # grid taps keep the grid-mode rules
            raise ValueError(f"{tn}: grid+explicit tap {out[i][0]} load={n:g}/{cap}, radius={r:g}/{radius}, "
                             f"empty={n == 0}")
        if i >= n_grid and r > radius + 1e-6:
            print(f"TAP-RADIUS-TARGET {tn}: grid+explicit tap {out[i][0]} radius={r:g}/{radius} (advisory)", file=sys.stderr)
    return [(name, x, y, n, r) for (name, x, y), n, r in zip(out, load, far)]


def density_taps(P, tn, control=True):
    """OWNER decision 5 (10-24, industry multi-source CTS): partition clock taps placed by SINK DENSITY.

    The sinks (sink_sites: face / ft registers + the internal inventory) are split by weighted median bisection into
    leaves of <= clock.tap_target_sinks (default 0.8 x tap_max_sinks, so the kit's nearest-tap split of the real netlist
    stays under the hard cap clock_taps.tcl enforces) within clock.tap_radius_um (default 200) of their centre (a leaf
    centred on a hard core splits on; small neighbours merge; a stray leaf of < clock.tap_min_sinks, default target /
    20, joins its nearest tap).  Each
    leaf's tap sits at its weighted L1 centre, legalised by schema.tap_clear(strict): >= TAP_CLEAR_UM off every hard
    core (keep-clear: no tap buffer on a macro), inside the outline, off the taps already placed and off the early
    core tap pins.  No grid: an empty region gets no tap, a dense region gets as many as its load needs.  Tap 0 'clk'
    = the tap nearest clock.tap_um, the others 'clk_t<i>' in (y, x) order.  The leaves then seed a capacitated
    k-medians refinement on the kit's own split rule (assign: nearest tap + cap), so the planned load of every tap is
    what clock_taps.tcl will give it.  Deterministic.
    Returns [(port, x, y, planned_sinks (kit split at the hard cap), max sink distance um)]."""
    # control=False: the PLANNING taps (no control-pin sinks).  The reset wavefront solver sites arst_n / start_i /
    # rst_o from the tap set (reset_tree._est_depth / face_sites), so it must read these to stay acyclic; the final
    # taps (control=True, the default = schema.tap_grid) then add the control pins as sinks (clock.control_sinks).
    control = bool(control and P.types[tn].get("clock", {}).get("control_sinks"))
    import schema
    t = P.types[tn]
    ck = t.get("clock", {})
    cap = int(ck.get("tap_max_sinks", 1500))
    target = int(ck.get("tap_target_sinks", max(1, int(0.8 * cap))))
    radius = float(ck.get("tap_radius_um", 200.0))
    if cap <= 0 or target <= 0 or radius <= 0 or target > cap:
        raise ValueError(f"type {tn}: density taps need 0 < tap_target_sinks <= tap_max_sinks and tap_radius_um > 0")
    pts = sink_sites(P, tn, control)
    if not pts:
        raise ValueError(f"type {tn}: clock.tap_mode 'density' but no sinks (no pins / ft slots / sink inventory)")
    w, h = t["outline_um"]
    taken = [(x, y) for _, x, y, _ in schema.core_taps(P, tn)]
    if control:
        taken += [(x, y) for _, x, y in control_pin_sinks(P, tn)]
    # clock.tap_model "frozen_anchor" (opt-in per type, pin_frozen_tap_model.py): the model this plan was solved with,
    # before 0ddc1ccd8c8 (consumed PG-safe tracks) / e2a63cfee7d (reuse-leaf union) / 1d753c326cf (per-bit sinks).
    # Its relay graph, raw exports and landing raw_reset names depend on these taps; default = current model.
    frozen = ck.get("tap_model") == "frozen_anchor"
    if frozen:
        boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                  c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", []) or []]
    else:
        from placement_obstacles import placement_boxes
        boxes = list(placement_boxes(t).values())
    key = _density_key(P, tn, control, pts, taken, boxes)
    cached = _density_cached(key)
    if cached is not None:
        return cached
    blocked = _Keepout(boxes)
    min_sinks = int(ck.get("tap_min_sinks", max(1, target // 20)))
    leaves = sorted(_bisect(pts, target, radius, blocked, min_sinks), key=lambda a: (round(a[1], 3), round(a[0], 3)))

    import gen_phys
    legal_axes = None if frozen else gen_phys.clock_legal_axes(P, tn)
    pin_snap = None if frozen else (lambda x, y: gen_phys._snap_tap(P, x, y, pg_legal=not t.get('hard')))

    def place(cands):
        tk, xy = list(taken), []
        for x, y in cands:
            x = min(max(x, TAP_MARGIN_UM), w - TAP_MARGIN_UM)
            y = min(max(y, TAP_MARGIN_UM), h - TAP_MARGIN_UM)
            x, y = schema.tap_clear(t, x, y, tk, strict=True, pin_snap=pin_snap, legal_axes=legal_axes)
            tk.append((x, y))
            xy.append((round(x, 4), round(y, 4)))
        return xy
    # refine (capacitated k-medians seeded by the leaves): the kit splits the netlist by NEAREST tap + cap
    # (clock_taps.tcl, mirrored by assign()), so re-centre every tap on the sinks that split gives it, re-legalise,
    # Drop only empty taps. A light, isolated control cluster must keep its tap:
    # its radius cannot be traded for reaching a preferred minimum sink count.
    xy = place([(q[0], q[1]) for q in leaves])
    for _ in range(int(ck.get("tap_refine_iters", 6))):
        _, _, asg = assign([(None, x, y) for x, y in xy], pts, target, radius,
                           max_distance_um=radius)
        groups = [[] for _ in xy]
        for p, j in zip(pts, asg):
            groups[j].append(p)
        keep = [j for j, g in enumerate(groups) if g]
        nxt = place([(_wmedian(groups[j], 0), _wmedian(groups[j], 1)) if groups[j] else xy[j] for j in keep])
        if nxt == xy:
            break
        xy = nxt
    # Legalising a centre away from a face or a macro may uncover sinks that
    # fitted before it moved. Preserve the physical radius after legalisation,
    # rather than publishing the old pre-legalisation radius as a guarantee.
    while True:
        load, far, asg = assign([(None, x, y) for x, y in xy], pts, cap, radius,
                                max_distance_um=radius)
        uncovered = [(abs(p[0]-xy[j][0])+abs(p[1]-xy[j][1]), i)
                     for i, (p, j) in enumerate(zip(pts, asg))
                     if abs(p[0]-xy[j][0])+abs(p[1]-xy[j][1]) > radius+1e-6]
        if not uncovered:
            break
        _, i = max(uncovered)
        p = pts[i]
        nxt = place(xy + [(p[0], p[1])])[-1]
        if nxt in xy or abs(p[0]-nxt[0])+abs(p[1]-nxt[1]) > radius+1e-6:
            raise ValueError(f"type {tn}: sink {p[:2]} has no legal clock tap within {radius} um")
        xy.append(nxt)
    out = sorted(((x, y, int(round(n)), round(r, 1)) for (x, y), n, r in zip(xy, load, far) if n > 0),
                 key=lambda q: (q[1], q[0]))
    root = ck.get("tap_um", [w / 2, h / 2])
    i0 = min(range(len(out)), key=lambda i: (abs(out[i][0] - root[0]) + abs(out[i][1] - root[1]), i))
    out = [out[i0]] + [p for i, p in enumerate(out) if i != i0]
    res = [("clk" if i == 0 else f"clk_t{i}", x, y, n, r) for i, (x, y, n, r) in enumerate(out)]
    _density_remember(key, res)
    return res


def recentre_sinks(P, tn):
    """[(x, y, weight)] sinks for clock.tap_recentre: the FIRM planned sinks with explicit per-bit ft station sites
    (planned_sinks(bit_sites=True)) plus clock.sink_sites_um rows (e.g. macro clock pins)."""
    ck = P.types[tn].get("clock", {})
    out = [(x, y, 1.0) for x, y, _ in planned_sinks(P, tn, bit_sites=True)]
    out += [(float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 else 1.0) for r in ck.get("sink_sites_um", [])]
    return [p for p in out if p[2] > 0]


def recentre_displaced(P, tn, grid, moved, iters=12):
    """PATH-KV-SYSC2 10-25 (GEOM F2, clock.tap_recentre "sinks"): the R4 grid taps `moved` (indices into grid
    [(port, x, y)]) were pushed off a macro / clock keepout by schema.tap_clear.  Re-centre each on the weighted L1
    median of the sinks the kit's nearest-tap rule gives it (Lloyd iterations, all grid taps competing), legalised by
    tap_clear(strict) against the keepouts and the other taps.  Fixed grid taps never move.  `moved` = [(index, grid
    cell rect)].  A moved tap that wins no sink AND whose grid cell has no free std-cell area (the cell lies wholly
    under macros / clock keepouts, e.g. a PHY) is a dead spine drop + unloaded reset synchroniser: it is dropped and
    the taps are renumbered clk, clk_t1.. in grid order.  Deterministic."""
    key = ("recentre", id(P), tn)
    cached = _CACHE.get(key)
    if cached is not None and cached[0] is P:
        return cached[1]
    import schema
    t = P.types[tn]
    pts = recentre_sinks(P, tn)
    cells = dict(moved)
    moved = [k for k, _ in moved]
    xy = [(x, y) for _, x, y in grid]
    for _ in range(iters):
        grp = [[] for _ in xy]
        for p in pts:
            j = min(range(len(xy)), key=lambda i: (abs(p[0] - xy[i][0]) + abs(p[1] - xy[i][1]), i))
            grp[j].append(p)
        nxt = list(xy)
        for k in moved:
            if not grp[k]:
                continue
            others = [q for i, q in enumerate(nxt) if i != k]
            x, y = schema.tap_clear(t, _wmedian(grp[k], 0), _wmedian(grp[k], 1), others, strict=True)
            nxt[k] = (round(x, 4), round(y, 4))
        if nxt == xy:
            break
        xy = nxt
    grp = [0] * len(xy)
    for p in pts:
        grp[min(range(len(xy)), key=lambda i: (abs(p[0] - xy[i][0]) + abs(p[1] - xy[i][1]), i))] += 1
    w, h = t["outline_um"]
    from placement_obstacles import placement_boxes
    boxes = list(placement_boxes(t).values()) + [tuple(b) for b in t.get("clock", {}).get("keepouts_um", [])]

    def dead(k):
        x0, y0, x1, y1 = cells[k]
        step = schema.TAP_STEP_UM * 4
        for a in range(int((x1 - x0) / step) + 1):
            for b in range(int((y1 - y0) / step) + 1):
                px, py = x0 + a * step, y0 + b * step
                if not (schema.TAP_CLEAR_UM <= px <= w - schema.TAP_CLEAR_UM and
                        schema.TAP_CLEAR_UM <= py <= h - schema.TAP_CLEAR_UM):
                    continue          # the outline margin (face bands) is not std-cell area for a tap's sinks
                if not any(q0 < px < q1 and r0 < py < r1 for q0, r0, q1, r1 in boxes):
                    return False
        return True
    keep = [i for i in range(len(xy)) if not (i in moved and grp[i] == 0 and dead(i))]
    res = [("clk" if m == 0 else f"clk_t{m}",) + xy[i] for m, i in enumerate(keep)]
    _CACHE[key] = (P, res)
    return res


def tap_loads(taps_xy, sinks):
    """[(planned sink weight, max L1 distance um)] per tap under the kit's nearest-tap rule (no cap)."""
    load = [0.0] * len(taps_xy)
    far = [0.0] * len(taps_xy)
    for p in sinks:
        j = min(range(len(taps_xy)), key=lambda i: (abs(p[0] - taps_xy[i][0]) + abs(p[1] - taps_xy[i][1]), i))
        load[j] += p[2]
        far[j] = max(far[j], abs(p[0] - taps_xy[j][0]) + abs(p[1] - taps_xy[j][1]))
    return list(zip(load, far))


def assign(taps, sinks, cap, max_extra_um, max_distance_um=None):
    """Python mirror of clock_taps.tcl (the kit's sink -> tap split, for G0 / review): every sink (x, y, w) to its
    NEAREST tap (Manhattan, ties to the lower tap index), then capacity-constrained re-assignment: while a tap holds
    > cap, its sinks that cost the least extra distance move to the best other tap with room, at most max_extra_um
    further.  Returns (per-tap load, per-tap max distance, [tap index per sink]).  Deterministic."""
    xy = [(t[1], t[2]) for t in taps]
    d = lambda s, j: abs(s[0] - xy[j][0]) + abs(s[1] - xy[j][1])
    asg = [min(range(len(xy)), key=lambda j: (d(s, j), j)) for s in sinks]
    load = [0.0] * len(xy)
    for s, j in zip(sinks, asg):
        load[j] += s[2]
    stuck = set()
    for _ in range(8 * len(xy)):
        over = next((j for j in range(len(xy)) if j not in stuck and load[j] > cap), None)
        if over is None:
            break
        cand = []
        for i, s in enumerate(sinks):
            if asg[i] != over:
                continue
            best = min(((d(s, j) - d(s, over), j) for j in range(len(xy))
                        if j != over and load[j] < cap
                        and (max_distance_um is None or d(s, j) <= max_distance_um)),
                       default=None)
            if best and best[0] <= max_extra_um:
                cand.append((best[0], i, best[1]))
        if not cand:
            stuck.add(over)
            continue
        cand.sort()
        tgt = cand[0][2]
        for _, i, j in cand:
            if load[over] <= cap or load[tgt] >= cap:
                break
            if j != tgt:
                continue
            asg[i] = tgt
            load[over] -= sinks[i][2]
            load[tgt] += sinks[i][2]
    far = [0.0] * len(xy)
    for s, j in zip(sinks, asg):
        far[j] = max(far[j], d(s, j))
    return load, far, asg


def bins_from_dump(dump, bin_um=10.8, origin=(0.0, 0.0)):
    """{"bin_um", "bins": [[x, y, n]]} of the clocked registers (DFF* / ICG* / SDF* / DHL* / DLL* masters) of an odb
    geometry dump ({"cells": [[name, x0, y0, x1, y1, master], ...]}), binned at bin_um, sites at the bin centres."""
    import collections
    c = collections.Counter()
    for _, x0, y0, x1, y1, m in dump["cells"]:
        if not any(k in m for k in ("DFF", "ICG", "SDF", "DHL", "DLL")):
            continue
        cx, cy = (x0 + x1) / 2 - origin[0], (y0 + y1) / 2 - origin[1]
        c[(int(cx // bin_um), int(cy // bin_um))] += 1
    return dict(bin_um=bin_um, n=sum(c.values()),
                bins=[[round((i + 0.5) * bin_um, 3), round((j + 0.5) * bin_um, 3), n] for (i, j), n in sorted(c.items())])


def sink_taps(P, tn):
    """[(port, x, y, n_sinks, radius_um)] sink-anchored taps of type tn (cached per plan object and type)."""
    if P.types[tn].get("clock", {}).get("tap_mode") == "density":
        return density_taps(P, tn)
    key = (id(P), tn)
    cached = _CACHE.get(key)
    if cached is not None and cached[0] is P:
        return cached[1]
    t = P.types[tn]
    ck = t.get("clock", {})
    w, h = t["outline_um"]
    R = float(ck.get("tap_radius_um", 250.0))
    cap = int(ck.get("tap_max_sinks", 1500))
    pts = [(x, y) for x, y, _ in planned_sinks(P, tn)]
    if not pts:
        raise ValueError(f"type {tn}: clock.tap_mode 'sinks' but no planned sinks (no pins / ft slots)")
    k = max(1, math.ceil(len(pts) / cap))
    while True:
        cen, groups = _kmedians(pts, k)
        taps = []
        for (x, y), g in zip(cen, groups):
            if not g:
                continue
            x = min(max(x, TAP_MARGIN_UM), w - TAP_MARGIN_UM)
            y = min(max(y, TAP_MARGIN_UM), h - TAP_MARGIN_UM)
            r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
            taps.append([x, y, len(g), r])
        if all(tp[3] <= R and tp[2] <= cap for tp in taps) or k >= len(pts) or k >= 256:
            break
        k += 1
    # one spine drop per lattice step: merge near-coincident taps
    merged = []
    for tp in sorted(taps, key=lambda q: (round(q[1], 3), round(q[0], 3))):
        m = next((q for q in merged if abs(q[0] - tp[0]) + abs(q[1] - tp[1]) < SEP_UM), None)
        if m:
            m[2] += tp[2]
            m[3] = max(m[3], tp[3])
        else:
            merged.append(tp)
    root = ck.get("tap_um", [w / 2, h / 2])
    i0 = min(range(len(merged)), key=lambda i: (abs(merged[i][0] - root[0]) + abs(merged[i][1] - root[1]), i))
    order = [merged[i0]] + [q for i, q in enumerate(merged) if i != i0]
    out = [("clk" if i == 0 else f"clk_t{i}", round(q[0], 4), round(q[1], 4), q[2], round(q[3], 1))
           for i, q in enumerate(order)]
    _CACHE[key] = (P, out)
    return out


def report(P, tn):
    """kit / G0 summary of the sink-anchored taps."""
    ck = P.types[tn].get("clock", {})
    mode = ck.get("tap_mode")
    # The kit uses the plan's frozen endpoints. Reporting them must not launch
    # a second placement/discovery pass with a different tap count/geometry.
    taps = (explicit_taps(P, tn) if mode == "explicit" else
            grid_explicit_taps(P, tn) if mode == "grid+explicit" else sink_taps(P, tn))
    dens = mode == "density"
    return dict(mode=ck.get("tap_mode", "sinks"), radius_um=float(ck.get("tap_radius_um", 200.0 if dens else 250.0)),
                max_sinks=int(ck.get("tap_max_sinks", 1500)), n=len(taps), empty=sum(1 for t in taps if t[3] == 0),
                taps=[dict(name=n, xy=[x, y], planned_sinks=s, radius_um=r) for n, x, y, s, r in taps])


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="clock.sink_bins_file from a placed partition's odb geometry dump")
    ap.add_argument("cmd", choices=["bins"])
    ap.add_argument("dump", help="odb dump JSON (cells: [name, x0, y0, x1, y1, master]; outline: [x0, y0, x1, y1])")
    ap.add_argument("--bin-um", type=float, default=10.8)
    ap.add_argument("--src", default="", help="provenance note stored in the file")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    d = json.load(open(a.dump))
    b = bins_from_dump(d, a.bin_um, tuple(d.get("outline", [0, 0])[:2]))
    b["src"] = a.src
    open(a.out, "w").write(json.dumps(b, separators=(",", ":")) + "\n")
    print(f"{a.out}: {b['n']} registers in {len(b['bins'])} bins of {a.bin_um} um")
