#!/usr/bin/env python3
"""TYPE-SAFE-2-KV 11-08 (OWNER 11-08 (B) macro congestion budget; COORD 07:35 KV PV START-IN-MACRO -> TYPE-SAFE-2;
KV-TYPES-4 06:07 CLASS C4): one plan event, three steps, for every type named by --types (the PV family by default).

Why (kv3_pv_v1n, measured by KV-TYPES-3/Codex): the START relays of the landing contract were sited on straight
L paths that only avoided clock keepouts, so 190/731 sat inside kv3_pv_pair / pv_join macros, and the outer macro
columns leave a 4.704 um edge channel against the 10.8 um kit contract (kit_contract.MIN_CHANNEL_UM, measured from
CORE_AREA).  A sideways nudge gives 500-524 um hops.  Form (KV-TYPES-4 06:07): macro move first, then re-derive
START / raw sites on the MOVED macros with Codex's macro-aware corridor router (start_obstacle_path.py,
codex/kv-start-obstacles-0222@873374c71c), then the ring-band spread (ring_band_spread.py, a separate step).

  channel  macro x-columns (placement_obstacles boxes): an OUTER column closer than --min-channel-um (10.8) to the
           kit core edge (outline inset --core-margin-um, KV kits 4.32) moves inward by exactly the deficit; every
           facing channel to the next column must stay >= the minimum (fail closed otherwise).  Only hard_cores[*]
           .origin_um changes.  Plan items inside a moved macro footprint (+4.32 halo) are reported; taps, keepouts,
           landing bands and internal stations there FAIL the step (they would need their own re-derivation).
  start    clock.landing_writer_start / landing_reader_start (existing opt-in START transport, DIE-KV-58 GEOM-96
           form: origin at (cland_tstart_in.x, 12), writer branches for output rings farther than 380 um, reader
           branches for every input ring, data cycles 0, boot +W/+R) with every stage ON A MACRO-FREE CORRIDOR:
           path() around the macro boxes (macros closer than 15.12 um to the core edge are closed to the edge, so no
           relay row is squeezed into a 10.8 um channel), depth = ceil(corridor / 340) - 1 (max over the branches of
           a group, one depth per group), relay_sites(max hop 405) off the landing bands, raw reset = nearest
           equal-depth reset tap (reset_tree.consumer_taps).  An existing START config keeps its depth if deeper.
  raw      clock.landing_raw_branches from a strict bind of the start plan (bound <type>_part.sv relay comments):
           each consumer (origin + every FSTART pin) copies the ORIGINAL relay chain of cland_start_raw from the
           deepest ancestor whose corridor allows hops <= 405 (same clock / D chain / depth -> same release cycle,
           +flops only), sites on the corridor.
Every step asserts that only the declared keys of the named types change (everything else byte-equal), and the plan
passes schema validation with no new error.  Cycle effect: data 0; START boot +W/+R (count-aligned rings bind K+W /
K-R, count_align_bind); reset depth 0.

  edge     non-hard `contents` macro (sys_SD PHY form) moved toward --side until that channel is exactly the minimum,
           so the interface channel grows by the slack; the die PG domain of each instance moves with it (Codex
           sd_corridor 11-08 form, dry gen PASS); reports the OWNER (B) channel / face-window budget.
  selfband wide landing rings the ring_band_spread sizer kept ("no macro-free ... band"): their own band rect is a
           clock keepout, so the sizer never grows them in place; same sizer with that one keepout lifted, keepout
           follows the band (--bands type.bus,... --sidecar eW_sidecar.json).
  istations existing internal_stations chains with sites inside macros: same count, re-laid on a corridor (report the
           ones that need more stations: cycles are TYPE-SAFE-2's relay event).
usage (repo root): kv_start_corridor_event.py channel|start|raw|istations|edge|selfband PLAN_IN PLAN_OUT REPORT.json [--types a,b]
                   [--bind-rtl DIR (raw)] [--core-margin-um 4.32] [--min-channel-um 10.8]"""
import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STEP_UM = 340.0          # target hop of a START stage (r2r gate 405; margin for GPL of face flops / ring cells)
MAX_HOP_UM = 405.0
NEED_UM = 380.0          # writer branches only for output rings whose START corridor is longer than this
EDGE_Y = 12.0            # origin row (inside core rows, clear of the M7 strap/pin sites)
CLEAR_UM = 4.32          # corridor clearance around macros (= reset_tree.CLEAR_UM)
REL = re.compile(r"ot_dp_rrelay\s+(\w+)\s*\(\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\);\s*//[^\n]*?depth (\d+) "
                 r"@ \(([-\d.]+), ([-\d.]+)\)")


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def macro_boxes(t):
    from placement_obstacles import placement_boxes
    return {k: tuple(v) for k, v in placement_boxes(t, halo=0.0).items()}


def columns(boxes):
    """x-overlap clusters (kit_contract._clusters on x) -> list of [names]"""
    order = sorted(boxes, key=lambda k: boxes[k][0])
    cols = []
    for k in order:
        if cols and boxes[k][0] < max(boxes[j][2] for j in cols[-1]) - 1e-6:
            cols[-1].append(k)
        else:
            cols.append([k])
    return cols


def facing_gap(boxes, ca, cb, min_um):
    g = None
    for a in ca:
        for b in cb:
            A, B = boxes[a], boxes[b]
            if min(A[3], B[3]) - max(A[1], B[1]) > -min_um + 1e-6:
                d = B[0] - A[2]
                g = d if g is None else min(g, d)
    return g


def _hc_index(t):
    return {hc["inst"]: hc for hc in t.get("hard_cores", [])}


def channel_type(t, margin, min_um):
    """per macro: a box whose own edge channel to the core edge is below min moves inward by exactly the deficit (the
    outer pair columns; an interior join macro of the same x-cluster stays).  Its core clock taps (clock.taps kind
    'core' named '<inst>.<pin>') move with it.  A landing band or internal-station site that was legal before and now
    meets the moved footprint (+4.32 halo) translates by the same dx (it was adjacent to that macro); anything that
    still collides, or a clock keepout / soft tap / START site inside a moved footprint, FAILS."""
    boxes = macro_boxes(t)
    hcs = _hc_index(t)
    if not boxes:
        return dict(applies=False)
    W, H = t["outline_um"]
    core = (margin, margin, W - margin, H - margin)
    shifts = {}
    for k, b in boxes.items():
        if b[0] - core[0] < min_um - 1e-6:
            shifts[k] = round(min_um - (b[0] - core[0]), 3)
        elif core[2] - b[2] < min_um - 1e-6:
            shifts[k] = -round(min_um - (core[2] - b[2]), 3)
    moved = {k: (b[0] + shifts.get(k, 0.0), b[1], b[2] + shifts.get(k, 0.0), b[3]) for k, b in boxes.items()}
    cols = columns(moved)
    err = [f"moved box {k} is not a plan hard_core" for k in shifts if k not in hcs]
    for i in range(len(cols) - 1):
        g = facing_gap(moved, cols[i], cols[i + 1], min_um)
        if g is not None and g < min_um - 1e-6:
            err.append(f"columns {i}/{i + 1}: facing channel {g:.3f} um < {min_um} after the move")
    for a in moved:                                    # no moved box may meet another macro (+halo both sides)
        for b in moved:
            if a < b and (a in shifts or b in shifts):
                A, B = moved[a], moved[b]
                if A[0] < B[2] + 2 * CLEAR_UM and B[0] < A[2] + 2 * CLEAR_UM and A[1] < B[3] and B[1] < A[3]:
                    err.append(f"{a} / {b} closer than {2 * CLEAR_UM} um after the move")
    if err:
        raise SystemExit("kv_start_corridor_event channel: " + "; ".join(err[:6]))
    for k, dx in shifts.items():
        hcs[k]["origin_um"] = [round(hcs[k]["origin_um"][0] + dx, 3), hcs[k]["origin_um"][1]]

    def grown(bx):
        return {k: (b[0] - CLEAR_UM, b[1] - CLEAR_UM, b[2] + CLEAR_UM, b[3] + CLEAR_UM) for k, b in bx.items()}
    g_old, g_new = grown(boxes), grown(moved)

    def hit_pt(p, G, only=None):
        return [k for k, (a, b, c, d) in G.items() if (only is None or k in only) and a < p[0] < c and b < p[1] < d]

    def hit_rect(r, G, only=None):
        return [k for k, (a, b, c, d) in G.items() if (only is None or k in only)
                and r[0] < c and a < r[2] and r[1] < d and b < r[3]]
    ck = t.get("clock", {})
    rep = dict(taps_moved=[], bands_moved=[], istation_sites_moved=0, fatal=[], preexisting=[])
    for tp in ck.get("taps", []) or []:
        inst = str(tp.get("name", "")).split(".", 1)[0]
        if tp.get("kind") == "core" and inst in shifts and tp.get("xy"):
            tp["xy"] = [round(tp["xy"][0] + shifts[inst], 3), tp["xy"][1]]
            rep["taps_moved"].append(tp["name"])
        elif tp.get("xy") and hit_pt(tp["xy"], g_new, shifts):
            rep["fatal"].append(f"tap {tp.get('name')}")
    for r in ck.get("keepouts_um", []):
        if hit_rect(r, g_new, shifts) and not hit_rect(r, g_old):
            rep["fatal"].append(f"keepout {r}")

    def carry(kind, name, get, put, is_rect):
        h = (hit_rect if is_rect else hit_pt)(get(), g_new, shifts)
        if not h:
            return
        if (hit_rect if is_rect else hit_pt)(get(), g_old):
            rep["preexisting"].append(f"{kind} {name}")
            return
        dxs = {shifts[k] for k in h}
        if len(dxs) != 1:
            rep["fatal"].append(f"{kind} {name}: meets macros with different shifts")
            return
        dx = dxs.pop()
        v = get()
        put([round(v[0] + dx, 3), v[1], round(v[2] + dx, 3), v[3]] if is_rect else [round(v[0] + dx, 3), v[1]])
        if (hit_rect if is_rect else hit_pt)(get(), g_new):
            rep["fatal"].append(f"{kind} {name}: still collides after the carry")
        return True
    for n, band in (ck.get("landing_contract", {}).get("bands", {}) or {}).items():
        def put(v, band=band):
            band["rect_um"] = v
        if carry("band", n, lambda band=band: band["rect_um"], put, True):
            rep["bands_moved"].append(n)
    for e in t.get("internal_stations", []):
        for j in range(len(e.get("regs_um", []))):
            def put(v, e=e, j=j):
                e["regs_um"][j] = v
            if carry("istation", f"{e.get('conn')}[{j}]", lambda e=e, j=j: e["regs_um"][j], put, False):
                rep["istation_sites_moved"] += 1
    for key in ("landing_writer_start", "landing_reader_start"):
        for b, br in ((ck.get(key) or {}).get("branches", {}) or {}).items():
            if any(hit_pt(st["xy_um"], g_new, shifts) for st in br["stages"]):
                rep["fatal"].append(f"{key}:{b} (re-derive with the start step)")
    if rep["fatal"]:
        raise SystemExit(f"kv_start_corridor_event channel: placed plan items inside a moved macro: {rep['fatal'][:6]}")
    edge = dict(W=round(min(b[0] for b in moved.values()) - core[0], 3),
                E=round(core[2] - max(b[2] for b in moved.values()), 3))
    return dict(applies=True, columns=len(cols), shifts=shifts, edge_channels_um=edge, **rep)


def corridor_obstacles(t, margin, min_um):
    """macro boxes; a macro closer than min + clearance to the core edge is extended to the outline (no relay row in
    a min-width edge channel: Codex's revised candidate)"""
    W, H = t["outline_um"]
    lim = min_um + CLEAR_UM
    out = []
    for a, b, c, d in macro_boxes(t).values():
        out.append([0.0 if a - margin < lim else a, 0.0 if b - margin < lim else b,
                    W if (W - margin) - c < lim else c, H if (H - margin) - d < lim else d])
    return out


def _route(o, tgt, obs, W, H):
    from start_obstacle_path import path
    return path(tuple(o), tuple(tgt), obs, clearance_um=CLEAR_UM, bounds=(0.0, 0.0, W, H))


def sited(o, tgt, r, depth, obs, occupied, W, H):
    """relay sites on corridor r; if a band run leaves no legal site, re-route with those bands as obstacles too
    (bands carry wires but no relay cells).  -> (sites | None, route used)"""
    from start_obstacle_path import relay_sites
    try:
        return relay_sites(r, depth, max_hop_um=MAX_HOP_UM, site_boxes=occupied, clearance_um=CLEAR_UM), r
    except ValueError:
        pass
    try:
        r2 = _route(o, tgt, obs + [list(x) for x in occupied], W, H)
        return relay_sites(r2, depth, max_hop_um=MAX_HOP_UM, site_boxes=occupied, clearance_um=CLEAR_UM), r2
    except ValueError:
        return None, r


def _free_point(p, obs):
    """nearest point outside every clearance-grown obstacle (a core-pin end of a station chain sits on its macro)"""
    x, y = p
    for _ in range(8):
        hit = next((g for g in ((a - CLEAR_UM, b - CLEAR_UM, c + CLEAR_UM, d + CLEAR_UM) for a, b, c, d in obs)
                    if g[0] < x < g[2] and g[1] < y < g[3]), None)
        if hit is None:
            return (round(x, 3), round(y, 3))
        x, y = min(((hit[0], y), (hit[2], y), (x, hit[1]), (x, hit[3])), key=lambda q: abs(q[0] - x) + abs(q[1] - y))
    return (round(x, 3), round(y, 3))


def istations_type(t, margin, min_um):
    """existing internal_stations chains with a site inside a macro (+halo): same count, sites re-laid on a
    macro-free corridor from_um -> to_um (ends pulled to the nearest free point).  Exact-bank / bit_route entries and
    chains whose corridor needs more stations than they have are reported (cycles are TYPE-SAFE-2's relay event)."""
    from start_obstacle_path import length
    W, H = t["outline_um"]
    obs = corridor_obstacles(t, margin, min_um)
    grown = [(a - CLEAR_UM, b - CLEAR_UM, c + CLEAR_UM, d + CLEAR_UM) for a, b, c, d in macro_boxes(t).values()]
    bands = [b["rect_um"] for b in t.get("clock", {}).get("landing_contract", {}).get("bands", {}).values()]
    rep = dict(resited=[], reported=[])
    for e in t.get("internal_stations", []):
        regs = e.get("regs_um", [])
        bad = [j for j, p in enumerate(regs) if any(a < p[0] < c and b < p[1] < d for a, b, c, d in grown)]
        if not bad:
            continue
        tag = f"{e.get('conn')} ({len(bad)}/{len(regs)} sites in macros)"
        if any(k in e for k in ("bit_sites_um", "face_bit_sites_um", "bit_route")) or not (e.get("from_um") and e.get("to_um")):
            rep["reported"].append(tag + ": exact-bank / bit_route or no ends")
            continue
        a, b = _free_point(e["from_um"], obs), _free_point(e["to_um"], obs)
        try:
            r = _route(a, b, obs, W, H)
        except ValueError as x:
            rep["reported"].append(f"{tag}: {x}")
            continue
        st, r = sited(a, b, r, len(regs), obs, bands, W, H)
        if st is None:
            need = max(0, math.ceil(length(r) / MAX_HOP_UM) - 1)
            rep["reported"].append(f"{tag}: corridor {length(r):.0f} um needs {need} stations, has {len(regs)}")
            continue
        e["regs_um"] = st
        e["note"] = (e.get("note", "") + f" | TYPE-SAFE-2-KV 11-08: {len(bad)} site(s) were inside macros; "
                     f"{len(st)} sites re-laid on a macro-free corridor ({length(r):.0f} um), count unchanged").lstrip(" |")
        rep["resited"].append(tag)
    return rep


def start_type(P, tn, t, margin, min_um):
    import reset_tree as RT
    from start_obstacle_path import length, relay_sites
    W, H = t["outline_um"]
    ck = t["clock"]
    lc = ck["landing_contract"]
    pins = {p["name"]: p["xy_um"] for p in lc["pins"]}
    sp = pins["cland_tstart_in"]
    o = (sp[0], EDGE_Y)
    obs = corridor_obstacles(t, margin, min_um)
    bands = [b["rect_um"] for b in lc["bands"].values()]
    taps = RT.consumer_taps(P, tn)
    # a MISSION-role type gates rst_n_t<i> with run; START relays need the raw wavefront copy rr_t<i> (same depth)
    raw_prefix = "rst_n_t" if (t.get("reset") or {}).get("start_role") == "bootstrap" else "rr_t"

    def raw_of(xy):
        i = min(range(len(taps)), key=lambda j: man(xy, taps[j][1:]))
        return f"{raw_prefix}{i}"
    outs = sorted(n[len("cland_fstart_out_"):] for n in pins if n.startswith("cland_fstart_out_"))
    ins = sorted(n[len("cland_fstart_in_"):] for n in pins if n.startswith("cland_fstart_in_"))
    fails, rep = [], dict(origin_site=list(o), writer={}, reader={})
    groups = {}
    for key, names, tgt_of in (("landing_writer_start", outs, lambda b: pins["cland_fstart_out_" + b]),
                               ("landing_reader_start", ins, lambda b: (
                                   (lc["bands"][b]["rect_um"][0] + lc["bands"][b]["rect_um"][2]) / 2,
                                   (lc["bands"][b]["rect_um"][1] + lc["bands"][b]["rect_um"][3]) / 2))):
        routes = {}
        for b in names:
            try:
                r = _route(o, tgt_of(b), obs, W, H)
            except ValueError as e:
                fails.append(dict(group=key, bus=b, error=str(e)))
                continue
            if key == "landing_writer_start" and length(r) <= NEED_UM:
                continue
            routes[b] = r
        old = (ck.get(key) or {}).get("depth", 0)
        depth = max([max(0, math.ceil(length(r) / STEP_UM) - 1) for r in routes.values()] + [old])
        groups[key] = (routes, depth, tgt_of)
    if fails:
        raise SystemExit(f"kv_start_corridor_event start {tn}: no legal corridor: {fails[:3]}")
    for key, (routes, depth, tgt_of) in groups.items():
        if not routes or depth == 0:
            if key == "landing_reader_start":
                raise SystemExit(f"kv_start_corridor_event start {tn}: reader START needs depth >= 1")
            continue
        branches = {}
        sub = rep["writer" if key == "landing_writer_start" else "reader"]
        for b, r in sorted(routes.items()):
            tgt = r[-1]
            occupied = [x for x in bands if not (x[0] <= tgt[0] <= x[2] and x[1] <= tgt[1] <= x[3])]
            st, r = sited(o, tgt, r, depth, obs, occupied, W, H)
            if st is None:
                fails.append(dict(group=key, bus=b, depth=depth, corridor_um=round(length(r), 1)))
                continue
            branches[b] = dict(stages=[dict(xy_um=xy, raw_reset=raw_of(xy)) for xy in st])
            pts = [list(o)] + st + [list(tgt)]
            sub[b] = dict(corridor_um=round(length(r), 1), max_hop_um=round(max(man(a, c) for a, c in zip(pts, pts[1:])), 1))
        if fails:
            raise SystemExit(f"kv_start_corridor_event start {tn}: no legal relay sites: {fails[:4]}")
        cfg = dict(depth=depth, branches=branches)
        if key == "landing_reader_start":
            cfg["origin_rect_um"] = [round(o[0] - 8.64, 3), 6.48, round(o[0] + 8.64, 3), 19.44]
        ck[key] = cfg
        rep[key] = dict(depth=depth, branches=len(branches))
    return rep


def raw_type(P, tn, t, rtl_dir, margin, min_um):
    from start_obstacle_path import length, relay_sites
    W, H = t["outline_um"]
    ck = t["clock"]
    lc = ck["landing_contract"]
    pins = {p["name"]: p["xy_um"] for p in lc["pins"]}
    f = Path(rtl_dir) / f"{tn}_part.sv"
    if not f.exists():
        f = Path(rtl_dir) / f"{tn}.sv"     # bind writes split variants (kv3_pv_v2n) without the _part suffix
    text = f.read_text()
    m = re.search(r"assign cland_start_raw = (\w+);", text)
    if not m:
        raise SystemExit(f"kv_start_corridor_event raw {tn}: no cland_start_raw in {f}")
    raw = m.group(1)
    by_q = {q: dict(d=d, depth=int(dep), xy=(float(x), float(y))) for _, d, q, dep, x, y in REL.findall(text)}
    chain = [raw]
    while chain[-1] in by_q and by_q[chain[-1]]["d"] in by_q:
        chain.append(by_q[chain[-1]]["d"])
    chain = chain[::-1]
    obs = corridor_obstacles(t, margin, min_um)
    bands = [b["rect_um"] for b in lc["bands"].values()]
    cons = {"origin": (pins["cland_tstart_in"][0], EDGE_Y)}
    for n, xy in sorted(pins.items()):
        if n.startswith("cland_fstart_out_"):
            cons["fstart:" + n[len("cland_fstart_out_"):]] = tuple(xy)
    branches, rep, fails = [], {}, []
    for role, xy in cons.items():
        occupied = [x for x in bands if not (x[0] <= xy[0] <= x[2] and x[1] <= xy[1] <= x[3])]
        done = None
        for k in range(len(chain) - 2, -1, -1):          # deepest base first = fewest copies
            base, n = chain[k], len(chain) - 1 - k
            try:
                r = _route(by_q[base]["xy"], xy, obs, W, H)
            except ValueError:
                continue
            st, r = sited(by_q[base]["xy"], xy, r, n, obs, occupied, W, H)
            if st is None:
                continue
            done = (k, base, n, r, st)
            break
        if done is None:
            fails.append(role)
            continue
        k, base, n, r, st = done
        name = "o" if role == "origin" else "fs_" + role.split(":", 1)[1]
        branches.append(dict(name=name, base=base, stages=[dict(original=chain[k + 1 + i], xy_um=st[i]) for i in range(n)],
                             consumers=[role]))
        pts = [list(by_q[base]["xy"])] + st + [list(xy)]
        rep[role] = dict(base=base, copies=n, corridor_um=round(length(r), 1),
                         max_hop_um=round(max(man(a, c) for a, c in zip(pts, pts[1:])), 1))
    if fails:
        raise SystemExit(f"kv_start_corridor_event raw {tn}: no corridor with hops <= {MAX_HOP_UM}: {fails[:4]}")
    ck["landing_raw_branches"] = branches
    return dict(raw=raw, chain_depth=len(chain), branches=len(branches),
                copies=sum(len(b["stages"]) for b in branches), consumers=rep)


LAYER_PITCH_UM = {"M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}   # core_pin_sites_gate.MIN_PITCH
TRACK_USE_MAX = 0.70                                                        # OWNER (B): pin-track use per face


def _xf(part, W, rect):
    """type rect -> die rect for an R0 / MY partition (KV sys types)"""
    ox, oy = part["origin_um"]
    a, b, c, d = rect
    if part.get("orient", "R0") == "R0":
        return [ox + a, oy + b, ox + c, oy + d]
    if part["orient"] == "MY":
        return [ox + W - c, oy + b, ox + W - a, oy + d]
    raise SystemExit(f"kv_start_corridor_event edge: orient {part['orient']} not handled")


def edge_type(raw, tn, t, margin, min_um, side="W"):
    """non-hard `contents` macros (sys_SD form: one PHY macro filling the type): move the macro toward `side` until
    that edge channel is exactly --min-channel-um, so the opposite (interface) channel grows by the slack.  The die
    PG domain of every instance's macro (die.pg.domains rect + bumps rect == the old macro box in die coordinates)
    moves with it.  Fails closed when a plan site (relay_sites, landing bands, landing pins) would fall inside the
    moved macro + 4.32 halo.  Also reports the OWNER (B) budget of the interface channel."""
    W, H = t["outline_um"]
    rep = dict(moved=[], pg_domains=[], budget={})
    parts = [p for p in raw["partitions"] if p["type"] == tn]
    lc = t.get("clock", {}).get("landing_contract", {})
    sites = [("relay_sites:" + k, v) for k, v in (t.get("relay_sites") or {}).items()]
    sites += [("pin:" + p["name"], p["xy_um"]) for p in lc.get("pins", [])]
    for c in t.get("contents", []):
        if not (c.get("origin_um") and c.get("outline_um")):
            continue
        (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
        wgap, egap = x0 - margin, (W - margin) - (x0 + w)
        dx = (min_um - wgap) if side == "W" else (egap - min_um)
        dx = round(dx, 3) if (wgap if side == "W" else egap) > min_um + 1e-6 else 0.0
        if dx == 0.0:
            rep["moved"].append(dict(inst=c["inst"], dx_um=0.0, w_gap_um=round(wgap, 3), e_gap_um=round(egap, 3)))
            continue
        old = [x0, y0, x0 + w, y0 + h]
        new = [x0 + dx, y0, x0 + dx + w, y0 + h]
        g = [new[0] - CLEAR_UM, new[1] - CLEAR_UM, new[2] + CLEAR_UM, new[3] + CLEAR_UM]
        go = [old[0] - CLEAR_UM, old[1] - CLEAR_UM, old[2] + CLEAR_UM, old[3] + CLEAR_UM]
        inside = lambda r, q: r[0] < q[0] < r[2] and r[1] < q[1] < r[3]
        hit = [n for n, q in sites if inside(g, q) and not inside(go, q)]
        for bn, b in lc.get("bands", {}).items():
            r = b["rect_um"]
            if r[0] < g[2] and r[2] > g[0] and r[1] < g[3] and r[3] > g[1] and \
                    not (r[0] < go[2] and r[2] > go[0] and r[1] < go[3] and r[3] > go[1]):
                hit.append("band:" + bn)
        if hit:
            raise SystemExit(f"kv_start_corridor_event edge {tn}: moved {c['inst']} covers {hit[:5]}")
        c["origin_um"] = [round(x0 + dx, 3), y0]
        rep["moved"].append(dict(inst=c["inst"], dx_um=dx, w_gap_um=round(wgap + dx, 3), e_gap_um=round(egap - dx, 3),
                                 from_um=[x0, y0], to_um=c["origin_um"]))
        for p in parts:
            od, nd = _xf(p, W, old), _xf(p, W, new)
            hits = [d for d in raw["die"]["pg"]["domains"]
                    if all(abs(u - v) < 1e-3 for u, v in zip(d.get("rect_um", []), od))]
            if len(hits) != 1:
                raise SystemExit(f"kv_start_corridor_event edge {tn}: {p['name']} PG domain of {c['inst']} "
                                 f"not unique ({len(hits)} at {od})")
            d = hits[0]
            ddx = round(nd[0] - od[0], 3)
            d["rect_um"] = [round(v, 3) for v in nd]
            if isinstance(d.get("bumps"), dict) and d["bumps"].get("rect_um"):
                r = d["bumps"]["rect_um"]
                d["bumps"]["rect_um"] = [round(r[0] + ddx, 3), r[1], round(r[2] + ddx, 3), r[3]]
            rep["pg_domains"].append(dict(partition=p["name"], domain=d["name"], dx_um=ddx, rect_um=d["rect_um"]))
        # OWNER (B) budget on the interface channel (E for side W): face windows + vertical channel capacity
        ch = (W - margin) - (x0 + dx + w) - CLEAR_UM if side == "W" else (x0 + dx - margin) - CLEAR_UM
        bud = dict(channel_um=round(ch, 3), vertical_tracks_per_um_at_70pct=round(TRACK_USE_MAX * (
            1 / LAYER_PITCH_UM["M5"] + 1 / LAYER_PITCH_UM["M7"]), 2))
        bud["vertical_capacity_nets"] = int(ch * bud["vertical_tracks_per_um_at_70pct"])
        wins = []
        names = {p["name"] for p in parts}
        for q in raw["ports"]:
            end = "dst" if q["dst"]["part"] in names else "src" if q["src"]["part"] in names else None
            if end is None or not q.get("window_um") or q["width"] < 64:
                continue
            span = q["window_um"][1] - q["window_um"][0]
            tracks = sum(span / LAYER_PITCH_UM[L] for L in q.get("layers", []) if L in LAYER_PITCH_UM)
            wins.append(dict(port=q["id"], bus=q[end]["bus"], width=q["width"], span_um=round(span, 3),
                             layers=q.get("layers"), track_use=round(q["width"] / tracks, 3) if tracks else None))
        bud["face_windows"] = wins
        for bn, b in lc.get("bands", {}).items():
            r = b["rect_um"]
            if b.get("ring_width", 0) >= 192:
                bud.setdefault("rings", []).append(dict(band=bn, ring_width=b["ring_width"], rect_um=r))
        rep["budget"][c["inst"]] = bud
    return rep


def selfband_type(raw, tn, t, buses, side_path, spread=7.0, min_ring=192):
    """wide landing rings the ring_band_spread sizer could not re-site ("no macro-free clock landing storage band"):
    their OWN band rect is also a clock keepout (clock.keepouts_um == band rect), and reset_tree.blockages grows it,
    so the sizer can never grow the band in place.  Same sizer (clock_landing_plan._storage_band, BAND_RESERVE
    ring_ff, --spread stepped down to 1.0, every corner within 405 um of the pin, off macros / stations / resets /
    islands / other bands), with only the band's own keepout lifted; the keepout then follows the band."""
    import clock_landing_plan as C
    import schema as S
    side = json.load(open(side_path))
    geoms = side["collector"]["types"]
    lc = t["clock"]["landing_contract"]
    bands = lc["bands"]
    P = S.Plan(copy.deepcopy(raw))
    phy = C.phy_supply_rects(P, tn)
    resets = C._reset_sites_for_type(raw, tn, geoms[tn].get("tree"), lc.get("base_type"))
    rows = []
    for bus in buses:
        old = bands[bus]
        if int(old.get("ring_width", 0)) < min_ring:
            raise SystemExit(f"kv_start_corridor_event selfband {tn}.{bus}: ring {old.get('ring_width')} < {min_ring}")
        keep = t["clock"].get("keepouts_um", [])
        own = [i for i, r in enumerate(keep) if all(abs(u - v) < 1e-6 for u, v in zip(r, old["rect_um"]))]
        tt = copy.deepcopy(t)
        tt["clock"]["keepouts_um"] = [r for i, r in enumerate(keep) if i not in own]
        tt["_cland_geom"] = copy.deepcopy(geoms[tn]["bus_geometry"])
        used = [list(o["rect_um"]) for k, o in bands.items() if k != bus and o.get("rect_um")]
        saved = (C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING)
        try:
            C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING = "ring_ff", float(spread), old.get("ring_place", "ff") or "ff"
            try:
                nb = C._storage_band(tt, bus, int(old["width"]), used, phy=phy, resets=resets)
            except ValueError as e:
                rows.append(dict(bus=bus, kept=list(old["rect_um"]), own_keepouts=len(own), error=str(e)[:200]))
                continue
        finally:
            C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING = saved
        for k, v in old.items():
            if k not in nb and k not in ("spread", "band_spread_target", "max_pin_to_band_hop_um", "area_reserve_um2",
                                         "resized_from_um", "resize"):
                nb[k] = v
        nb["resized_from_um"] = list(old["rect_um"])
        nb["resize"] = (f"TYPE-SAFE-2-KV 11-08 LANDING-RING-DENSITY: ring_ff spread {spread:g}; own clock keepout lifted "
                        f"for the sizer and moved with the band")
        for i in own:
            keep[i] = list(nb["rect_um"])
        bands[bus] = nb
        (a, b, c, d), (e, f, g, h) = old["rect_um"], nb["rect_um"]
        rows.append(dict(bus=bus, old_um=list(old["rect_um"]), new_um=nb["rect_um"], old_area=round((c - a) * (d - b)),
                         new_area=round((g - e) * (h - f)), spread=nb.get("spread"), hop_um=nb.get("max_pin_to_band_hop_um"),
                         own_keepouts=len(own)))
    rr = [(k, v["rect_um"]) for k, v in bands.items() if v.get("rect_um")]
    for i, (x, ra) in enumerate(rr):
        for y, rb in rr[i + 1:]:
            if C._rect_overlap(ra, rb):
                raise SystemExit(f"kv_start_corridor_event selfband {tn}: bands {x} and {y} overlap")
    return dict(rows=rows)


ALLOWED = dict(channel={"hard_cores", "clock", "internal_stations"}, start={"clock"}, raw={"clock"},
               istations={"internal_stations"}, edge={"contents"}, selfband={"clock"})
CLOCK_KEYS = dict(start={"landing_writer_start", "landing_reader_start"}, raw={"landing_raw_branches"},
                  selfband={"landing_contract", "keepouts_um"})


def splice(text, raw, types):
    for tn in types:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        if not m:
            return None
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + json.dumps(raw["partition_types"][tn], indent=1).replace("\n", "\n  ") + text[j:]
    if json.loads(text)["die"] != raw["die"]:
        m = re.search(r'^ "die": ', text, re.M)
        if not m:
            return None
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + json.dumps(raw["die"], indent=1).replace("\n", "\n ") + text[j:]
    return text if json.loads(text) == raw else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("channel", "start", "raw", "istations", "edge", "selfband"))
    ap.add_argument("--bands", default="", help="selfband: type.bus,type.bus")
    ap.add_argument("--sidecar")
    ap.add_argument("--side", default="W", choices=("W", "E"))
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("report")
    ap.add_argument("--types", default="")
    ap.add_argument("--bind-rtl")
    ap.add_argument("--core-margin-um", type=float, default=4.32)
    ap.add_argument("--min-channel-um", type=float, default=10.8)
    a = ap.parse_args(argv)
    import schema as S
    text = Path(a.plan_in).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    types = [x for x in a.types.split(",") if x] or sorted(k for k in raw["partition_types"] if k.startswith("kv3_pv")
                                                         and not raw["partition_types"][k].get("hard"))
    P = S.Plan(copy.deepcopy(raw), Path(a.plan_in).resolve())
    rep = dict(tool="tools/die_plan/kv_start_corridor_event.py", step=a.step, plan_in=a.plan_in, types={})
    for tn in types:
        t = raw["partition_types"][tn]
        if a.step == "channel":
            rep["types"][tn] = channel_type(t, a.core_margin_um, a.min_channel_um)
        elif a.step == "selfband":
            rep["types"][tn] = selfband_type(raw, tn, t, [x.split(".", 1)[1] for x in a.bands.split(",") if
                                                          x.split(".", 1)[0] == tn], a.sidecar)
        elif a.step == "edge":
            rep["types"][tn] = edge_type(raw, tn, t, a.core_margin_um, a.min_channel_um, a.side)
        elif a.step == "istations":
            rep["types"][tn] = istations_type(t, a.core_margin_um, a.min_channel_um)
        elif a.step == "start":
            rep["types"][tn] = start_type(P, tn, t, a.core_margin_um, a.min_channel_um)
        else:
            if not a.bind_rtl:
                raise SystemExit("raw needs --bind-rtl")
            rep["types"][tn] = raw_type(P, tn, t, a.bind_rtl, a.core_margin_um, a.min_channel_um)
    # preservation
    for k in raw:
        if k == "die" and a.step == "edge":
            dv, do = copy.deepcopy(raw[k]), copy.deepcopy(orig[k])
            dv["pg"]["domains"] = do["pg"]["domains"] = None
            assert dv == do, k
            for x, y in zip(raw[k]["pg"]["domains"], orig[k]["pg"]["domains"]):
                assert {q: x[q] for q in x if q not in ("rect_um", "bumps")} == \
                    {q: y[q] for q in y if q not in ("rect_um", "bumps")}, x.get("name")
        elif k != "partition_types":
            assert raw[k] == orig[k], k
    for tn, v in raw["partition_types"].items():
        o = orig["partition_types"][tn]
        if tn not in types:
            assert v == o, tn
            continue
        for k in set(v) | set(o):
            if v.get(k) != o.get(k):
                assert k in ALLOWED[a.step], (tn, k)
        if a.step == "channel":
            for x, y in zip(v["hard_cores"], o["hard_cores"]):
                assert {k: x[k] for k in x if k != "origin_um"} == {k: y[k] for k in y if k != "origin_um"}, tn
                assert x["origin_um"][1] == y["origin_um"][1], tn
        if a.step == "edge":
            for x, y in zip(v["contents"], o["contents"]):
                assert {q: x[q] for q in x if q != "origin_um"} == {q: y[q] for q in y if q != "origin_um"}, tn
            continue
        if a.step == "istations":
            for x, y in zip(v.get("internal_stations", []), o.get("internal_stations", [])):
                assert len(x["regs_um"]) == len(y["regs_um"]), (tn, x.get("conn"))
                assert {k: x[k] for k in x if k not in ("regs_um", "note")} == \
                    {k: y[k] for k in y if k not in ("regs_um", "note")}, (tn, x.get("conn"))
            continue
        if a.step == "channel":
            for k in set(v["clock"]) | set(o["clock"]):
                if v["clock"].get(k) != o["clock"].get(k):
                    assert k in ("taps", "landing_contract"), (tn, k)
            lcv, lco = v["clock"].get("landing_contract", {}), o["clock"].get("landing_contract", {})
            for k in set(lcv) | set(lco):
                if lcv.get(k) != lco.get(k):
                    assert k == "bands", (tn, k)
        else:
            if a.step == "selfband":
                named = {x.split(".", 1)[1] for x in a.bands.split(",") if x.split(".", 1)[0] == tn}
                lcv, lco = v["clock"]["landing_contract"], o["clock"]["landing_contract"]
                assert {k: lcv[k] for k in lcv if k != "bands"} == {k: lco[k] for k in lco if k != "bands"}, tn
                assert {k: x for k, x in lcv["bands"].items() if k not in named} == \
                    {k: x for k, x in lco["bands"].items() if k not in named}, tn
                assert len(v["clock"].get("keepouts_um", [])) == len(o["clock"].get("keepouts_um", [])), tn
            for k in set(v["clock"]) | set(o["clock"]):
                if v["clock"].get(k) != o["clock"].get(k):
                    assert k in CLOCK_KEYS[a.step], (tn, k)
    base_errs = set(map(str, S.validate(copy.deepcopy(orig))))
    errs = [e for e in map(str, S.validate(copy.deepcopy(raw))) if e not in base_errs]
    if errs:
        raise SystemExit("kv_start_corridor_event: new schema errors: " + "; ".join(errs[:5]))
    out = splice(text, raw, types) or json.dumps(raw, indent=1) + "\n"
    Path(a.plan_out).write_text(out)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for tn, r in rep["types"].items():
        print(tn, json.dumps({k: v for k, v in r.items() if k not in ("writer", "reader", "consumers", "inside_moved")})[:300])


if __name__ == "__main__":
    main()
