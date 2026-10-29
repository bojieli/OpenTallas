#!/usr/bin/env python3
"""DIE-HEAD-21 HK4: HEAD channel / feed-through resize (plan_hk3 -> plan_hk4).

COORD 10-28 23:20: hd_st_m failed GEOM (1442.88 x 1226.88 um slot, ~6k cells, fill 0.0005, clock reach 1322/957 um).
The HEAD feed-through types (hd_st_*, hd_turn_*, hd_spn*) were sized as plan slots, not from their contents.

Design (README "Choice"): (A) crop each type to the minimal rectangle that still holds every functional object of the
type (ft / bus windows, landing ring bands, landing-contract pins, collector points, count straps, the one-entry clock
tap and the die clock islands), plus a 34.56-um boundary margin, snapped OUTWARD to the 8.64-um die grid.  A face that
carries a window stays a face (its objects sit on it, so the clamp keeps it), so every abutting neighbour still meets
the same absolute pin windows; the die port windows are unchanged.  The freed part of the old slot becomes a die
channel (die.channels, no signal std cells, 12.1d); die clock-tree reserved sites that fall in it are listed per
instance in the report (top-owned infra-island sites, 12.2a).  (B) dissolving the types into die-level relay cells is
rejected: 12.1d (frozen, 12.14a) pushes ft stations down into partitions and forbids die-level signal std cells.

A type is cropped only if the new area is <= MAX_KEEP x the old area (default 0.9); hd_spn / hd_spn_end are never
cropped here: they carry the die clock trunk and abut both tile halves (narrowing them moves the tile array -> ASK).

Everything type-local is translated by (-x0, -y0) of the crop: outline, ft/bus windows (by face), clock tap, edge
clock taps, landing pins / bands / collector points, reserved sites (dropped outside), die islands (dropped outside),
reset local taps (dropped outside; the clock tap is added when none is left), count strap sites.  Instance origins move
by the crop per orientation (R0/MX/MY/R180), so every kept object keeps its absolute die position.  reset.in_sites are
re-anchored to the same corner/face inset in the new outline.

usage: head_channel_resize_delta.py PLAN_IN.json --out PLAN_OUT.json --report REPORT.json [--synth SYNTH.json]
       [--types t1,t2] [--margin 34.56] [--max-keep 0.9] [--png-dir DIR]
"""
import argparse
import copy
import gzip
import json
import math
import sys

GRID = 8.64
MARGIN = 17.28            # = taps.TAP_MARGIN_UM and the band inset from the face (bands start 17.28 in)
TAP_RADIUS = 250.0        # COORD HEAD-KITS-4: one core-clock tap per face bank, <= 250 um from its bank flops
TAP_TYPES_EXTRA = ["hd_ctl", "hd_host", "hd_mesh"]
TAG = "DIE-HEAD-21 HK4 resize"
DEFAULT_TYPES = ["hd_st_turn", "hd_st_str", "hd_st_n3", "hd_st_n4", "hd_st_m", "hd_st_k5", "hd_turn_a", "hd_turn_b",
                 "hd_spn", "hd_spn_end"]
NEVER = {"hd_spn": "carries the die clock trunk (spine root x 8760.96) and abuts both tile halves on W/E; narrowing it moves "
                   "the 264-tile array (ASK, default keep)",
         "hd_spn_end": "same as hd_spn (spine end; tile halves abut W/E)"}
RING_FF_UM2 = 1.4166 * 1.05          # DIE-HEAD-11 measured ring-flop footprint x 1.05 (hk3 README)
FACE_TOL = 3.0


def r3(v):
    return round(v + 0.0, 3)


def load(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt") as f:
        return json.load(f)


def _pts(t, infra=True):
    """every functional point / rect corner of a type (type frame) that a crop must keep (infra=False: without the
    one-entry clock tap and the die clock islands -- COORD HEAD-KITS-4 strip ruling, the tap moves into the strip)."""
    c = t.get("clock", {})
    W, H = t["outline_um"]
    pts = []
    face = {"W": lambda a: (0.0, a), "E": lambda a: (W, a), "S": lambda a: (a, 0.0), "N": lambda a: (a, H)}
    for f in t.get("ft_slots", []):
        for fc, key in ((f["in_face"], "in_window_um"), (f["out_face"], "out_window_um")):
            pts += [face[fc](v) for v in f[key]]
    for b in t.get("buses", []):
        if "face" in b and "window_um" in b:
            pts += [face[b["face"]](v) for v in b["window_um"]]
    lc = c.get("landing_contract", {}) or {}
    pts += [tuple(q["xy_um"]) for q in lc.get("pins", [])]
    for b in (lc.get("bands") or {}).values():
        r = b["rect_um"]
        pts += [(r[0], r[1]), (r[2], r[3])]
    for k in ("collector_local_sources", "collector_children"):
        pts += [tuple(q["xy_um"]) for q in lc.get(k) or [] if "xy_um" in q]
    for s in t.get("count_straps", []):
        pts += [tuple(p) for p in s["sites_um"]]
    if c.get("tap_um") and infra:
        pts.append(tuple(c["tap_um"]))
    pts += [tuple(e["tap_um"]) for e in c.get("edge_clocks", [])]
    for r in c.get("die_islands_um", []) if infra else []:
        pts += [(r[0], r[1]), (r[2], r[3])]
    for r in c.get("reserved_sites_um", []):
        if r.get("kind") == "landing_ring_bank":
            pts += [(r["rect_um"][0], r["rect_um"][1]), (r["rect_um"][2], r["rect_um"][3])]
    return pts


def crop_rect(t, margin=MARGIN, infra=False):
    W, H = t["outline_um"]
    pts = _pts(t, infra)
    x0 = min(p[0] for p in pts) - margin
    y0 = min(p[1] for p in pts) - margin
    x1 = max(p[0] for p in pts) + margin
    y1 = max(p[1] for p in pts) + margin
    snap_lo = lambda v: max(0.0, math.floor(v / GRID + 1e-9) * GRID)
    x0, y0 = snap_lo(x0), snap_lo(y0)
    x1 = min(W, math.ceil(x1 / GRID - 1e-9) * GRID)
    y1 = min(H, math.ceil(y1 / GRID - 1e-9) * GRID)
    # a face whose clamp stopped within one grid step of the outline is the outline face (keeps W/H exact)
    if W - x1 < GRID:
        x1 = W
    if H - y1 < GRID:
        y1 = H
    return [r3(x0), r3(y0), r3(x1), r3(y1)]


def _in(p, R, tol=1e-6):
    return R[0] - tol <= p[0] <= R[2] + tol and R[1] - tol <= p[1] <= R[3] + tol


def _rin(r, R, tol=1e-6):
    return _in((r[0], r[1]), R, tol) and _in((r[2], r[3]), R, tol)


def _sp(p, dx, dy):
    return [r3(p[0] - dx), r3(p[1] - dy)] + list(p[2:])


def _sr(r, dx, dy):
    return [r3(r[0] - dx), r3(r[1] - dy), r3(r[2] - dx), r3(r[3] - dy)]


def shift_type(t, R):
    """translate a type into its crop R (type frame); returns (new type, dropped reserved sites, dropped islands,
    dropped reset taps)."""
    t = copy.deepcopy(t)
    dx, dy = R[0], R[1]
    W, H = R[2] - R[0], R[3] - R[1]
    t["outline_um"] = [r3(W), r3(H)]
    for f in t.get("ft_slots", []):
        for fc, key in ((f["in_face"], "in_window_um"), (f["out_face"], "out_window_um")):
            d = dy if fc in "WE" else dx
            f[key] = [r3(v - d) for v in f[key]]
    for b in t.get("buses", []):
        if "face" in b and "window_um" in b:
            d = dy if b["face"] in "WE" else dx
            b["window_um"] = [r3(v - d) for v in b["window_um"]]
    c = t.get("clock", {})
    if c.get("tap_um"):
        q = _sp(c["tap_um"], dx, dy)
        q[0] = r3(min(max(q[0], MARGIN), W - MARGIN))
        q[1] = r3(min(max(q[1], MARGIN), H - MARGIN))
        c["tap_um"] = q
    for e in c.get("edge_clocks", []):
        e["tap_um"] = _sp(e["tap_um"], dx, dy)
    lc = c.get("landing_contract") or {}
    for q in lc.get("pins", []):
        q["xy_um"] = _sp(q["xy_um"], dx, dy)
    seen = {}
    for b in (lc.get("bands") or {}).values():
        b["rect_um"] = _sr(b["rect_um"], dx, dy)
    for k in ("collector_local_sources", "collector_children"):
        for q in lc.get(k) or []:
            if "xy_um" in q:
                q["xy_um"] = _sp(q["xy_um"], dx, dy)
            if isinstance(q.get("band"), dict) and "rect_um" in q["band"]:
                q["band"]["rect_um"] = _sr(q["band"]["rect_um"], dx, dy)
    Rn = [0.0, 0.0, W, H]
    keep, drop_rs = [], []
    for r in c.get("reserved_sites_um", []):
        rr = dict(r, rect_um=_sr(r["rect_um"], dx, dy))
        (keep if _rin(rr["rect_um"], Rn) else drop_rs).append(rr if _rin(rr["rect_um"], Rn) else r)
    if "reserved_sites_um" in c:
        c["reserved_sites_um"] = keep
    isl_keep, drop_isl = [], []
    for r in c.get("die_islands_um", []):
        rr = _sr(r, dx, dy)
        (isl_keep if _rin(rr, Rn) else drop_isl).append(rr if _rin(rr, Rn) else r)
    if "die_islands_um" in c:
        c["die_islands_um"] = isl_keep
    for s in t.get("count_straps", []):
        s["sites_um"] = [_sp(p, dx, dy) for p in s["sites_um"]]
    rs = t.get("reset", {})
    drop_rt = []
    if rs.get("local_taps_um"):
        kept = []
        for p in rs["local_taps_um"]:
            q = _sp(p, dx, dy)
            legal = _in(q, [MARGIN, MARGIN, W-MARGIN, H-MARGIN])
            (kept if legal else drop_rt).append(q if legal else p)
        if not kept and c.get("tap_um"):
            kept = [list(c["tap_um"][:2])]
        rs["local_taps_um"] = kept
    if rs.get("leaf_um"):
        rs["leaf_um"] = _sp(rs["leaf_um"], dx, dy)
    t["note"] = (t.get("note", "") + f" | {TAG}: cropped from the plan slot to x {R[0]}-{R[2]} / y {R[1]}-{R[3]} "
                 "(old frame); freed slot = die channel").strip(" |")
    return t, drop_rs, drop_isl, drop_rt


def check_inside(t):
    """every functional object of a shifted type lies inside its outline (returns list of violations)."""
    W, H = t["outline_um"]
    R = [0.0, 0.0, W, H]
    return [p for p in _pts(t, True) if not _in(p, R, 1e-3)]


def set_bank_taps(t):
    """sink-anchored taps (taps.py tap_mode 'sinks'): k-medians of the planned face / ft-station sinks, every tap
    within TAP_RADIUS of its sinks; tap 0 'clk' = the one nearest clock.tap_um."""
    c = t["clock"]
    c["tap_mode"] = "density"
    # The CA readers are internal register banks, absent from planned face/FT
    # sinks. Include their complete rectangular extent in density planning.
    rows = []
    for b in (c.get("landing_contract", {}).get("bands") or {}).values():
        x0, y0, x1, y1 = b["rect_um"]
        n = b.get("clock_roles", {}).get("local_read_flops", b.get("ring_width", 1))
        rows.extend([[x, y, n / 4] for x, y in ((x0,y0),(x0,y1),(x1,y0),(x1,y1))])
    c["sink_sites_um"] = rows
    c["tap_radius_um"] = TAP_RADIUS


def new_origin(o, orient, W, H, R):
    ox, oy = o
    x0, y0, x1, y1 = R
    nx = ox + x0 if orient in ("R0", "MX") else ox + W - x1
    ny = oy + y0 if orient in ("R0", "MY") else oy + H - y1
    return [r3(nx), r3(ny)]


def to_die(o, orient, W, H, p):
    """type-frame point -> die (old outline W,H)."""
    x, y = p
    X = o[0] + (x if orient in ("R0", "MX") else W - x)
    Y = o[1] + (y if orient in ("R0", "MY") else H - y)
    return [r3(X), r3(Y)]


def die_rect(o, orient, W, H, r):
    a, b = to_die(o, orient, W, H, (r[0], r[1])), to_die(o, orient, W, H, (r[2], r[3]))
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]


def freed_rects(old, new):
    """old minus new (both die rects, new inside old): up to 4 rects (S, N full width; W, E between)."""
    X0, Y0, X1, Y1 = old
    x0, y0, x1, y1 = new
    out = []
    if y0 > Y0 + 1e-6:
        out.append([X0, Y0, X1, y0])
    if y1 < Y1 - 1e-6:
        out.append([X0, y1, X1, Y1])
    if x0 > X0 + 1e-6:
        out.append([X0, y0, x0, y1])
    if x1 < X1 - 1e-6:
        out.append([x1, y0, X1, y1])
    return [[r3(v) for v in r] for r in out]


def reanchor_in_site(s, W, H, R):
    """keep the same inset to the nearest old corner/face in the new outline."""
    x, y = s[:2]
    nW, nH = R[2] - R[0], R[3] - R[1]
    nx = x if x <= W / 2 else nW - (W - x)
    ny = y if y <= H / 2 else nH - (H - y)
    if R[0] <= x <= R[2] and R[1] <= y <= R[3] and (min(x - R[0], R[2] - x) < 20 or min(y - R[1], R[3] - y) < 20):
        nx, ny = x - R[0], y - R[1]      # already on a kept face: plain shift
    return [r3(min(max(nx, 0.0), nW)), r3(min(max(ny, 0.0), nH))]


def estimate(t, synth, Wo, Ho):
    """estimate row: cells, area, fill, bands, face pin need, clock reach (one entry, and 4-tap trunk)."""
    W, H = t["outline_um"]
    c = t["clock"]
    lc = c.get("landing_contract") or {}
    bands = lc.get("bands") or {}
    band_area = sum((b["rect_um"][2] - b["rect_um"][0]) * (b["rect_um"][3] - b["rect_um"][1]) for b in bands.values())
    ring_reserve = sum((5 * b.get("ring_width", 64) + 160) * RING_FF_UM2 for b in bands.values())
    face_need = {}
    for f in t.get("ft_slots", []):
        for fc, key in ((f["in_face"], "in_window_um"), (f["out_face"], "out_window_um")):
            face_need[fc] = face_need.get(fc, 0.0) + f[key][1] - f[key][0]
    for b in t.get("buses", []):
        if "face" in b:
            face_need[b["face"]] = face_need.get(b["face"], 0.0) + b["window_um"][1] - b["window_um"][0]
    # sinks: band rects + ft window ends on the faces (stations lie between the windows)
    pts = []
    for b in bands.values():
        r = b["rect_um"]
        pts += [(r[0], r[1]), (r[2], r[3]), (r[0], r[3]), (r[2], r[1])]
    face = {"W": lambda a: (0.0, a), "E": lambda a: (W, a), "S": lambda a: (a, 0.0), "N": lambda a: (a, H)}
    for f in t.get("ft_slots", []):
        for fc, key in ((f["in_face"], "in_window_um"), (f["out_face"], "out_window_um")):
            pts += [face[fc](v) for v in f[key]]
    tx, ty = c["tap_um"][:2]
    reach1 = max((abs(x - tx) + abs(y - ty) for x, y in pts), default=0.0)
    # sinks also along every ft path (stations sit on the in-window -> out-window L path)
    for f in t.get("ft_slots", []):
        (ax_, ay_), (bx_, by_) = [face[fc](sum(f[key]) / 2) for fc, key in
                                  ((f["in_face"], "in_window_um"), (f["out_face"], "out_window_um"))]
        L = abs(bx_ - ax_) + abs(by_ - ay_)
        for k in range(int(L // 20) + 1):
            d = 20.0 * k
            dxp = min(d, abs(bx_ - ax_))
            pts.append((ax_ + math.copysign(dxp, bx_ - ax_), ay_ + math.copysign(max(0.0, d - abs(bx_ - ax_)), by_ - ay_)))
    tx, ty = c["tap_um"][:2]
    reach1 = max((abs(x - tx) + abs(y - ty) for x, y in pts), default=0.0)
    # 12.8b internal tree estimate: leaf drivers on a 200-um grid, one per grid cell that holds sinks -> reach <= 200
    cells = {(int(x // 200.0), int(y // 200.0)) for x, y in pts}
    drv = [((i + 0.5) * 200.0, (j + 0.5) * 200.0) for i, j in cells]
    reachT = max((min(abs(x - a_) + abs(y - b_) for a_, b_ in drv) for x, y in pts), default=0.0)
    n = len(cells)
    return dict(outline_um=[W, H], area_um2=r3(W * H), band_area_um2=r3(band_area),
                ring_reserve_um2=r3(ring_reserve), face_window_um={k: r3(v) for k, v in sorted(face_need.items())},
                clock_reach_one_entry_um=r3(reach1), clock_trunk_drivers=n, clock_reach_trunk_um=r3(reachT))


def run(plan, types=None, margin=MARGIN, max_keep=0.9, synth=None):
    plan = copy.deepcopy(plan)
    pt = plan["partition_types"]
    types = types or [n for n in DEFAULT_TYPES if n in pt]
    rep = dict(schema="opentallas.head_channel_resize.v1", tag=TAG, margin_um=margin, grid_um=GRID, max_keep=max_keep,
               types={}, channels=[])
    in_sites = plan.get("reset", {}).get("in_sites", {})
    for tn in types:
        t = pt[tn]
        Wo, Ho = t["outline_um"]
        row = dict(old_outline_um=[Wo, Ho], instances=[q["name"] for q in plan["partitions"] if q["type"] == tn])
        syn = (synth or {}).get(tn)
        if syn:
            row["synth"] = syn
        est_old = estimate(t, None, Wo, Ho)
        row["old"] = est_old
        if syn:
            est_old["fill"] = r3(syn["area_um2"] / est_old["area_um2"])
        if tn in NEVER:
            row.update(action="keep", reason=NEVER[tn])
            rep["types"][tn] = row
            continue
        R = crop_rect(t, margin)
        nW, nH = R[2] - R[0], R[3] - R[1]
        if nW * nH > max_keep * Wo * Ho:
            row.update(action="keep", crop_um=R, reason=f"crop keeps {nW * nH / (Wo * Ho):.0%} of the slot (> {max_keep:.0%}): "
                       "the type's own windows span the slot")
            rep["types"][tn] = row
            continue
        nt, drop_rs, drop_isl, drop_rt = shift_type(t, R)
        bad = check_inside(nt)
        if bad:
            raise SystemExit(f"{tn}: {len(bad)} functional objects outside the crop, e.g. {bad[:3]}")
        pt[tn] = nt
        if tn in in_sites:
            in_sites[tn] = reanchor_in_site(in_sites[tn], Wo, Ho, R)
        row.update(action="crop", crop_um=R, new_outline_um=nt["outline_um"], new=estimate(nt, None, nW, nH),
                   dropped_reserved=[dict(kind=r["kind"], rect_um=r["rect_um"]) for r in drop_rs],
                   dropped_islands=drop_isl, dropped_reset_taps=drop_rt,
                   reset_in_site=in_sites.get(tn))
        if syn:
            row["new"]["fill"] = r3(syn["area_um2"] / row["new"]["area_um2"])
        moves = []
        for q in plan["partitions"]:
            if q["type"] != tn:
                continue
            o, orient = q["origin_um"], q.get("orient", "R0")
            old_die = [o[0], o[1], r3(o[0] + Wo), r3(o[1] + Ho)]
            no = new_origin(o, orient, Wo, Ho, R)
            new_die = [no[0], no[1], r3(no[0] + nW), r3(no[1] + nH)]
            assert all(abs(a - b) < 1e-3 for a, b in zip(new_die, die_rect(o, orient, Wo, Ho, R))), (tn, q["name"])
            q["origin_um"] = no
            dsites = [die_rect(o, orient, Wo, Ho, r["rect_um"]) for r in drop_rs if r["kind"] == "die_clock_tree"]
            disl = [die_rect(o, orient, Wo, Ho, r) for r in drop_isl]
            for fr in freed_rects(old_die, new_die):
                inside = lambda r: _rin(r, fr, 1e-3)
                ns, ni = sum(map(inside, dsites)), sum(map(inside, disl))
                ch = dict(name=f"hk4_free_{q['name']}_{len(moves)}", rect_um=fr,
                          reason=f"{TAG}: freed by the {q['name']} ({tn}) crop; die channel: no signal std cells (12.1d), "
                                 f"PG + filler/decap; top-owned die clock sites here (12.2a): {ns} tree sites, {ni} islands")
                plan["die"].setdefault("channels", []).append(ch)
                rep["channels"].append(dict(ch, part=q["name"], tree_sites_um=[r for r in dsites if inside(r)],
                                            islands_um=[r for r in disl if inside(r)]))
            moves.append(dict(part=q["name"], orient=orient, old_origin_um=o, new_origin_um=no, old_die_um=old_die,
                              new_die_um=new_die))
        row["moves"] = moves
        rep["types"][tn] = row
    for tn in [n for n in types if n in pt] + [n for n in TAP_TYPES_EXTRA if n in pt]:
        set_bank_taps(pt[tn])
        # Cropping changes which neighboring face can deliver reset. Let the
        # existing die wavefront planner choose a legal input from its standard
        # candidate faces rather than retaining a stale slot-corner override.
        in_sites.pop(tn, None)
    plan["note"] = (plan.get("note", "") + f" | {TAG}: ft channel types cropped to their windows (plan_hk4)").strip(" |")
    return plan, rep


def tap_report(plan, types, plan_path=None):
    """taps.py sink_taps per type: n taps, worst tap->sink radius, sinks."""
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "die_plan"))
    import schema as S
    import taps as TP
    P = S.Plan(plan, plan_path)
    out = {}
    for tn in types:
        if plan["partition_types"][tn]["clock"].get("tap_mode") not in ("sinks", "density"):
            continue
        tl = TP.sink_taps(P, tn)
        bands = plan["partition_types"][tn]["clock"].get("landing_contract", {}).get("bands", {})
        bank_radius = max((min(abs(x-a)+abs(y-b) for _,a,b,*_ in tl)
                           for q in bands.values() for x,y in ((q["rect_um"][0],q["rect_um"][1]),
                                                               (q["rect_um"][0],q["rect_um"][3]),
                                                               (q["rect_um"][2],q["rect_um"][1]),
                                                               (q["rect_um"][2],q["rect_um"][3]))), default=0)
        out[tn] = dict(bank_corner_radius_um=round(bank_radius,3), n=len(tl), worst_radius_um=max(t[4] for t in tl), sinks=sum(t[3] for t in tl),
                       taps=[dict(name=n, xy=[x, y], planned_sinks=k, radius_um=r) for n, x, y, k, r in tl])
    return out


def render_type(old_t, new_t, R, tn, png, row):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    Wo, Ho = old_t["outline_um"]
    fig, ax = plt.subplots(figsize=(12, 12 * Ho / Wo + 1.0) if Wo >= Ho else (6, 12))
    ax.add_patch(Rectangle((0, 0), Wo, Ho, fill=False, lw=1, ec="#999", ls="--"))
    ax.add_patch(Rectangle((R[0], R[1]), R[2] - R[0], R[3] - R[1], fc="#f4f4ec", ec="k", lw=1.8))
    t = new_t
    dx, dy = R[0], R[1]
    c = t["clock"]
    for r in c.get("reserved_sites_um", []):
        rr = r["rect_um"]
        col = "#e8a33d" if r["kind"] == "landing_ring_bank" else "#7b3fbf"
        ax.add_patch(Rectangle((rr[0] + dx, rr[1] + dy), rr[2] - rr[0], rr[3] - rr[1], fc=col, ec=col, alpha=.6))
    for r in row.get("dropped_reserved", []):
        rr = r["rect_um"]
        ax.add_patch(Rectangle((rr[0], rr[1]), rr[2] - rr[0], rr[3] - rr[1], fc="none", ec="#7b3fbf", lw=1.5, ls=":"))
    for r in c.get("die_islands_um", []):
        ax.add_patch(Rectangle((r[0] + dx, r[1] + dy), r[2] - r[0], r[3] - r[1], fc="#2a7de1", ec="#2a7de1", alpha=.6))
    W, H = t["outline_um"]
    face = {"W": lambda a, b: ([dx, dx], [a + dy, b + dy]), "E": lambda a, b: ([dx + W, dx + W], [a + dy, b + dy]),
            "S": lambda a, b: ([a + dx, b + dx], [dy, dy]), "N": lambda a, b: ([a + dx, b + dx], [dy + H, dy + H])}
    for f in t.get("ft_slots", []):
        for fc, key in ((f["in_face"], "in_window_um"), (f["out_face"], "out_window_um")):
            xy = face[fc](*f[key])
            ax.plot(*xy, lw=6, color="#1a9e5a", solid_capstyle="butt")
            ax.annotate(f"{f['name']}:{fc}", (sum(xy[0]) / 2, sum(xy[1]) / 2), fontsize=8, color="#1a9e5a")
    for b in t.get("buses", []):
        if "face" in b:
            xy = face[b["face"]](*b["window_um"])
            ax.plot(*xy, lw=6, color="#1a9e5a", solid_capstyle="butt")
    for q in (c.get("landing_contract") or {}).get("pins", []):
        ax.plot(q["xy_um"][0] + dx, q["xy_um"][1] + dy, ".", color="#c0392b", ms=4)
    for p in t.get("reset", {}).get("local_taps_um", []):
        ax.plot(p[0] + dx, p[1] + dy, "x", color="#333", ms=6)
    for s in t.get("count_straps", []):
        for p in s["sites_um"]:
            ax.plot(p[0] + dx, p[1] + dy, "+", color="#8a6d00", ms=4)
    ax.plot(c["tap_um"][0] + dx, c["tap_um"][1] + dy, "*", color="#2a7de1", ms=14)
    for tp in row.get("tap_list", []):
        ax.plot(tp["xy"][0] + dx, tp["xy"][1] + dy, "D", color="#0b5", ms=8, mfc="none", mew=2)
    e = row.get("new", {})
    ax.set_title(f"{tn}: slot {Wo} x {Ho} (dashed) -> {W} x {H} um (solid, crop x {R[0]}-{R[2]} y {R[1]}-{R[3]})\n"
                 f"fill {e.get('fill', '?')}  one-entry reach {e.get('clock_reach_one_entry_um')}  trunk reach "
                 f"{e.get('clock_reach_trunk_um')} um; taps (green diamonds) {row.get('taps', {}).get('n')} worst {row.get('taps', {}).get('worst_radius_um')} um; green windows, orange bands, purple die-clock sites (dotted = to "
                 "channel), blue islands, x reset taps, * clock tap", fontsize=9)
    ax.set_xlim(-20, Wo + 20)
    ax.set_ylim(-20, Ho + 20)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(png, dpi=90)
    plt.close(fig)


def render_die(plan_old, plan_new, rep, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(14, 14))
    W, H = plan_new["die"]["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k"))
    to = {q["name"]: q for q in plan_old["partitions"]}
    col = {"hd_tile": "#dddddd", "hd_serdes": "#b0c4de"}
    for q in plan_new["partitions"]:
        tn = q["type"]
        w, h = plan_new["partition_types"][tn]["outline_um"]
        crop = rep["types"].get(tn, {}).get("action") == "crop"
        if crop:
            o = to[q["name"]]
            ow, oh = plan_old["partition_types"][tn]["outline_um"]
            ax.add_patch(Rectangle(o["origin_um"], ow, oh, fill=False, ec="#999", ls="--", lw=0.8))
        ax.add_patch(Rectangle(q["origin_um"], w, h, fc="#e07b39" if crop else col.get(tn, "#9fd39f"), ec="#333",
                               lw=0.3, alpha=0.9))
        if tn != "hd_tile":
            ax.annotate(q["name"], (q["origin_um"][0] + w / 2, q["origin_um"][1] + h / 2), fontsize=6, ha="center")
    for ch in rep["channels"]:
        r = ch["rect_um"]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#fff3b0", ec="#c9a400", lw=0.5, hatch="//"))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.set_title("plan_hk4 die: cropped ft types (orange), old slots dashed, freed die channel (yellow hatched)")
    fig.tight_layout()
    fig.savefig(png, dpi=80)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--synth", help="JSON {type: {area_um2, cells, src}} (kit synth_stat)")
    ap.add_argument("--types")
    ap.add_argument("--margin", type=float, default=MARGIN)
    ap.add_argument("--max-keep", type=float, default=0.9)
    ap.add_argument("--png-dir")
    a = ap.parse_args(argv)
    old = load(a.plan)
    synth = load(a.synth) if a.synth else None
    plan, rep = run(old, a.types.split(",") if a.types else None, a.margin, a.max_keep, synth)
    json.dump(plan, open(a.out, "w"), indent=1)
    from pathlib import Path as _P
    rep["taps"] = tap_report(plan, list(plan["partition_types"]), _P(a.out).parent / "die_plan.json")
    for tn, row in rep["types"].items():
        if tn in rep["taps"]:
            row["taps"] = {k: v for k, v in rep["taps"][tn].items() if k != "taps"}
    json.dump(rep, open(a.report, "w"), indent=1)
    if a.png_dir:
        from pathlib import Path
        Path(a.png_dir).mkdir(parents=True, exist_ok=True)
        for tn, row in rep["types"].items():
            row["tap_list"] = rep["taps"].get(tn, {}).get("taps", [])
            if row["action"] == "crop":
                render_type(old["partition_types"][tn], plan["partition_types"][tn], row["crop_um"], tn,
                            f"{a.png_dir}/{tn}.png", row)
        render_die(old, plan, rep, f"{a.png_dir}/die_hk4.png")
        for row in rep["types"].values():
            row.pop("tap_list", None)
    for tn, row in rep["types"].items():
        n = row.get("new", row["old"])
        print(f"{tn}: {row['action']} {row['old_outline_um']} -> {n['outline_um']} fill {n.get('fill', '-')} "
              f"reach1 {n['clock_reach_one_entry_um']} taps {row.get('taps')}")
    for tn in TAP_TYPES_EXTRA:
        print(tn, rep["taps"].get(tn, {}).get("n"), rep["taps"].get(tn, {}).get("worst_radius_um"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
