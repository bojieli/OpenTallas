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
import math

TAP_MARGIN_UM = 17.28          # keep the interior tap pins off the face pin bands
FACE_INSET_UM = 2.0            # a face register sits just inside its pin
SEP_UM = 8.64                  # two taps closer than one lattice step merge (one spine drop)

# Retain the exact Plan with its result: id(P) alone can be reused after a
# transient compose Plan is collected, otherwise returning another plan's taps.
# The identity check also keeps cache hits correct for plan-like test objects.
_CACHE = {}


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
    rows = list(ck.get("sink_sites_um", []))
    if ck.get("sink_bins_file"):
        # a placed netlist's inventory already holds the face / ft registers: the planned ones are not added again
        import json
        rows += json.loads((_root() / ck["sink_bins_file"]).read_text())["bins"]
        out = []
    else:
        out = [(x, y, 1.0) for x, y, _ in planned_sinks(P, tn)]
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


def _merge(leaves, target, radius, blocked=lambda x, y: False):
    """bisection cuts along the median, so a sparse channel or an L-shaped region ends up in many small leaves (dead-ish
    taps of a few hundred sinks next to each other).  Greedily merge the pair of leaves whose union still fits the
    target and radius with the smallest merged radius, until no pair fits.  Deterministic."""
    leaves = list(leaves)
    while True:
        best = None
        for i, a in enumerate(leaves):
            for j in range(i + 1, len(leaves)):
                b = leaves[j]
                if a[2] + b[2] > target or abs(a[0] - b[0]) + abs(a[1] - b[1]) > 2 * radius:
                    continue
                g = a[4] + b[4]
                x, y = _wmedian(g, 0), _wmedian(g, 1)
                r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
                if r <= radius and not blocked(x, y) and (best is None or (r, i, j) < best[:3]):
                    best = (r, i, j, (x, y, a[2] + b[2], r, g))
        if best is None:
            return leaves
        _, i, j, m = best
        leaves = [q for k, q in enumerate(leaves) if k not in (i, j)] + [m]


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
        boxes=list(schema.placed_macro_boxes(typ,halo=clear).values())
        boxes += [(a-clear,b-clear,c+clear,d+clear) for a,b,c,d in ck.get("keepouts_um",[])]
        legal=(clear-eps<=x<=w-clear+eps and clear-eps<=y<=h-clear+eps
               and not any(abs(x-a)<clear-eps and abs(y-b)<clear-eps for a,b in taken)
               and not any(a+eps<x<c-eps and b+eps<y<d-eps for a,b,c,d in boxes))
        if not legal:
            raise ValueError("{}: explicit tap {} violates outline/halo/tap spacing".format(tn,p["name"]))
        out.append((p["name"],x,y));taken.append((x,y))
    return out


def explicit_taps(P, tn):
    """Validate every actual data/control sink against the frozen explicit endpoints.

    Reset/START placement reads geometry-only explicit_tap_sites while solving
    control locations. Once those are known, full budget validation remains
    mandatory here; no zero-load/placeholder budget result is cached.
    """
    out = explicit_tap_sites(P, tn)
    ck = P.types[tn].get("clock", {})
    sinks=sink_sites(P,tn)
    cap=int(ck.get("tap_max_sinks",1500));radius=float(ck.get("tap_radius_um",200.))
    if cap<=0 or radius<=0:
        raise ValueError(f"{tn}: explicit tap radius/capacity must be positive")
    load,far,_=assign(out,sinks,cap,radius,max_distance_um=radius)
    for i,(n,r) in enumerate(zip(load,far)):
        if n>cap or r>radius+1e-6 or n==0:
            raise ValueError(f"{tn}: explicit tap {out[i][0]} load={n:g}/{cap}, radius={r:g}/{radius}, empty={n==0}")
    return [(name,x,y,n,r) for (name,x,y),n,r in zip(out,load,far)]


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
    key = ("density", id(P), tn, control)
    cached = _CACHE.get(key)
    if cached is not None and cached[0] is P:
        return cached[1]
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
    boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
              c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", []) or []]
    blocked = lambda x, y: any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in boxes)
    min_sinks = int(ck.get("tap_min_sinks", max(1, target // 20)))
    leaves = sorted(_bisect(pts, target, radius, blocked, min_sinks), key=lambda a: (round(a[1], 3), round(a[0], 3)))

    def place(cands):
        tk, xy = list(taken), []
        for x, y in cands:
            x = min(max(x, TAP_MARGIN_UM), w - TAP_MARGIN_UM)
            y = min(max(y, TAP_MARGIN_UM), h - TAP_MARGIN_UM)
            x, y = schema.tap_clear(t, x, y, tk, strict=True)
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
    _CACHE[key] = (P, res)
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
    boxes = list(schema.placed_macro_boxes(t).values()) + [tuple(b) for b in t.get("clock", {}).get("keepouts_um", [])]

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
    taps = sink_taps(P, tn)
    ck = P.types[tn].get("clock", {})
    dens = ck.get("tap_mode") == "density"
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
