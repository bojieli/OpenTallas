#!/usr/bin/env python3
"""R-REACH (RULEBOOK 11-13, lane RULES-REACH-1; OWNER 11-12 "the reach problem can be resolved via fixed scripts"):
fanout and reach locality of every die plan, checked at G0 and fixed by ONE deterministic script.

    reach_rules.py check  PLAN [--repo SRC] [--types RE] [--json OUT] [--tsv OUT]      exit 1 = R-REACH errors
    reach_rules.py fix    PLAN --out-plan NEW.json --report REP.json [--repo SRC] [--types RE] [--rules 1,4]
    reach_rules.py census PLAN [PLAN ...] [--repo SRC]                                  affected types per die

THE RULES (numbers; the why and the evidence are in ~/coord/lanes/RULEBOOK-1113.md section R-REACH):
  R-REACH-1 start_fan   One register (or one kept copy) drives <= FANOUT_MAX (48) loads, all within REACH_UM (405 um,
                        METHODOLOGY 12.1e) of it.  A control source with wider loads is carried by registered relays
                        at <= REACH_UM hops (planned at STEP_UM 340) and copied once per region (a hub with its loads
                        within HUB_UM 300 um).  Checked on the count-aligned START fan, the largest such net of every
                        die: origin (clock.landing_reader_start.origin_rect_um / landing_origin_rect_um, else the
                        cland_tstart_in pin) -> every input ring band, and origin -> every FSTART output pin.
                        FIX: clock.landing_reader_start with share_trunk (one relay trunk per region hub, one last
                        stage per ring; depth uniform per type, K - depth at the bind, data cycles 0) and
                        clock.landing_writer_start for far FSTART pins, sites on macro-free corridors
                        (start_obstacle_path), raw reset = nearest equal-depth reset tap.
  R-REACH-2 macro_barrier  A macro with a side >= BARRIER_UM (405) splits a type: logic on both sides needs a
                        registered stage on the way round it.  A type with such a macro and face buses that name no
                        consumer (no buses[].leaf, no internal_stations bus:<name> chain) must declare reach_homes
                        [{name, rect_um, buses}] (where the soft logic of those buses is placed); every bus window ->
                        home corridor (around the macros) longer than REACH_UM needs an internal_stations chain with
                        hops <= REACH_UM.  FIX (opt-in --rules 2, with reach_homes declared): the chain, k =
                        ceil(L / 340) - 1 stations, +k cycles on that bus (pre-approved).
  R-REACH-3 bus_window  A bus window sits on the face nearest its consumer: window -> consumer (hard core box / pins,
                        or its reach_home) <= WINDOW_UM (200 um, target; warning + MOVE-WINDOW list) and never more
                        than REACH_UM without internal stations (R3-INTERNAL already errors on that).  Face-net
                        buffers ~ bits x distance / 150 um (HBM q_su: 83k buffers on 8.3k face nets), so the report
                        prices every type in bit-mm.
  R-REACH-4 fwd_source  A forwarded clock output (landing_contract pin, kind clock, dir out) takes the NEAREST grid
                        tap of the type's current tap grid: hop tap -> pin <= REACH_UM; never the root 'clk' when a
                        nearer tap exists, never a tap that no longer exists.  FIX: re-point source_clock_port to
                        the nearest tap (0 cycles, same clock family).

G0: check.py calls check_plan(); a finding is an ERROR (check "r_reach") unless budgets.r_reach is "warn"; rule 3 is
always a warning.  The fix is idempotent: a fixed plan run again changes nothing.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SCHEMA = "opentallas.reach_rules.v1"
REACH_UM = 405.0        # METHODOLOGY 12.1e registered hop, every layer
STEP_UM = 340.0         # planned hop of a relay trunk (kv_start_corridor_event.STEP_UM): margin for legal sites / GPL
HUB_UM = 300.0          # a region: loads within this Manhattan distance of their hub copy
FANOUT_MAX = 48         # loads per register copy (CLAND-RELAY-3: 65 loads = 331-336 ps routed slew, 33-48 clean)
BARRIER_UM = 405.0      # a macro side this long is a barrier (no single registered hop crosses it)
WINDOW_UM = 200.0       # target face window -> consumer distance (tap radius / half a hop)
BUF_UM = 150.0          # repeater spacing used to price face-net buffers (HBM q_su: ~10 buffers per ~1.5 mm net)
EDGE_IN_UM = 12.0       # origin home: this far inside the face of the START pin (KV corridor form EDGE_Y)
PAD_PITCH_UM = 5.4      # dwell stages of a short trunk sit side by side at the origin home
RULES = ("1", "2", "3", "4")
RULE_NAME = {"1": "start_fan", "2": "macro_barrier", "3": "bus_window", "4": "fwd_source"}
EPS = 1e-6


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def box_dist(p, r):
    return max(r[0] - p[0], p[0] - r[2], 0.0) + max(r[1] - p[1], p[1] - r[3], 0.0)


def _centre(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def used_types(F, rx=None):
    parts = F["partitions"]
    used = {q["type"] for q in (parts.values() if isinstance(parts, dict) else parts)}
    pat = re.compile(rx) if rx else None
    return sorted(tn for tn in used if tn in F["partition_types"] and not F["partition_types"][tn].get("hard")
                  and (pat is None or pat.search(tn)))


def macro_boxes(t):
    from placement_obstacles import placement_boxes
    return {k: tuple(v) for k, v in placement_boxes(t, halo=0.0).items()}


# ---------------------------------------------------------------------------------------------- rule 1: START fan
def start_info(t):
    """START fan geometry of a type dict, None when the type has no START-tree child origin (no cland_tstart_in pin:
    a root origin, a non-strap landing form, or no landing at all)."""
    ck = t.get("clock") or {}
    lc = ck.get("landing_contract") or {}
    pins = {p["name"]: p["xy_um"] for p in lc.get("pins", [])}
    if "cland_tstart_in" not in pins:
        return None
    bands = lc.get("bands") or {}
    ins = sorted(b for b in bands if "cland_fstart_in_" + b in pins and bands[b].get("rect_um"))
    outs = sorted(n[len("cland_fstart_out_"):] for n in pins if n.startswith("cland_fstart_out_"))
    rs, ws = ck.get("landing_reader_start") or {}, ck.get("landing_writer_start") or {}
    rect = rs.get("origin_rect_um") or ws.get("origin_rect_um") or ck.get("landing_origin_rect_um")
    W, H = t["outline_um"]
    sp = pins["cland_tstart_in"]
    if rect:
        o = _centre(rect)
    else:
        d = {"W": sp[0], "E": W - sp[0], "S": sp[1], "N": H - sp[1]}
        f = min(d, key=d.get)
        o = {"W": (EDGE_IN_UM, sp[1]), "E": (W - EDGE_IN_UM, sp[1]), "S": (sp[0], EDGE_IN_UM),
             "N": (sp[0], H - EDGE_IN_UM)}[f]
    return dict(pins=pins, bands=bands, ins=ins, outs=outs, origin=(round(o[0], 3), round(o[1], 3)),
                pinned=bool(rect), reader=rs, writer=ws)


def _chain_hops(o, stages, end_rect=None, end_pt=None):
    pts = [tuple(o)] + [tuple(s["xy_um"]) for s in stages]
    hops = [man(a, b) for a, b in zip(pts, pts[1:])]
    hops.append(box_dist(pts[-1], end_rect) if end_rect is not None else man(pts[-1], end_pt))
    return hops


def start_findings(t, tn, reach=REACH_UM, fanout=FANOUT_MAX):
    """-> (row, [finding]) of rule 1 for one type; row = the numbers the census prints"""
    si = start_info(t)
    if si is None or not (si["ins"] or si["outs"]):
        return None, []
    import clock_landings as CL
    o, out = si["origin"], []
    rs, ws = si["reader"], si["writer"]
    rbr, wbr = (rs.get("branches") or {}), (ws.get("branches") or {})
    worst_r, far_r, direct, firsts = 0.0, [], 0, set()
    owners = CL.reader_start_owners(rs) if rs else {}
    for b in si["ins"]:
        st = (rbr.get(b) or {}).get("stages") if isinstance(rbr.get(b), dict) else None
        if st:
            hops = _chain_hops(o, st, end_rect=si["bands"][b]["rect_um"])
            firsts.add((owners.get(b) or [b])[0])
        else:
            hops = [box_dist(o, si["bands"][b]["rect_um"])]
            direct += 1
        h = max(hops)
        worst_r = max(worst_r, h)
        if h > reach + EPS:
            far_r.append((b, h, bool(st)))
    worst_w, far_w, wfirsts, wdirect = 0.0, [], set(), 0
    wowners = CL.reader_start_owners(ws) if ws else {}
    for b in si["outs"]:
        st = (wbr.get(b) or {}).get("stages") if isinstance(wbr.get(b), dict) else None
        if st:
            wfirsts.add((wowners.get(b) or [b])[0])
        else:
            wdirect += 1
        hops = _chain_hops(o, st or [], end_pt=si["pins"]["cland_fstart_out_" + b])
        h = max(hops)
        worst_w = max(worst_w, h)
        if h > reach + EPS:
            far_w.append((b, h, bool(st)))
    # loads of the origin's start: one per trunk head (shared) / first stage, plus every ring that takes it straight
    loads = len(firsts) + direct
    row = dict(type=tn, rings=len(si["ins"]), fstart_out=len(si["outs"]), origin=list(o), origin_pinned=si["pinned"],
               reader_depth=int(rs.get("depth", 0) or 0), writer_depth=int(ws.get("depth", 0) or 0),
               share_trunk=bool(rs.get("share_trunk")), reader_worst_hop_um=round(worst_r, 1),
               writer_worst_hop_um=round(worst_w, 1), reader_over=len(far_r), writer_over=len(far_w),
               origin_loads=loads, origin_d_loads=len(wfirsts) + wdirect)
    if far_r:
        b, h, has = max(far_r, key=lambda v: v[1])
        out.append(dict(rule="1", kind="start_reach", type=tn, value=round(h, 1), limit=reach, n=len(far_r),
                        msg=f"START fan: {len(far_r)}/{len(si['ins'])} input rings are more than {reach:g} um from "
                            f"the START origin{'' if si['pinned'] else ' (origin home not pinned: measured from its pin)'}"
                            f" with {'a reader START hop over the reach' if has else 'no reader START relay'}; worst "
                            f"{b} {h:.0f} um (fix: reach_rules.py fix --rules 1 -> clock.landing_reader_start "
                            f"share_trunk)"))
    if far_w:
        b, h, has = max(far_w, key=lambda v: v[1])
        out.append(dict(rule="1", kind="start_writer_reach", type=tn, value=round(h, 1), limit=reach, n=len(far_w),
                        msg=f"START fan: {len(far_w)}/{len(si['outs'])} FSTART output pins are more than {reach:g} um "
                            f"from the START origin with {'a writer START hop over the reach' if has else 'no writer START relay'}"
                            f"; worst {b} {h:.0f} um (fix: reach_rules.py fix --rules 1 -> clock.landing_writer_start)"))
    if loads > fanout:
        out.append(dict(rule="1", kind="start_fanout", type=tn, value=loads, limit=fanout, n=1,
                        msg=f"START fan: the origin start drives {loads} loads ({len(firsts)} first relays + {direct} "
                            f"rings direct) > {fanout} per copy (fix: share_trunk region hubs)"))
    if len(wfirsts) + wdirect > fanout:
        out.append(dict(rule="1", kind="start_fanout", type=tn, value=len(wfirsts) + wdirect, limit=fanout, n=1,
                        msg=f"START fan: the origin start_d drives {len(wfirsts) + wdirect} loads ({len(wfirsts)} "
                            f"first writer relays + {wdirect} FSTART face flops direct) > {fanout} per copy "
                            f"(fix: writer share_trunk region hubs)"))
    if rs.get("share_trunk"):
        kids = defaultdict(set)
        for b in si["ins"]:
            ow = owners.get(b) or []
            for i in range(1, len(ow)):
                kids[(ow[i - 1], i - 1)].add((ow[i], i))
        big = [(k, len(v)) for k, v in kids.items() if len(v) > fanout]
        if big:
            k, n = max(big, key=lambda v: v[1])
            out.append(dict(rule="1", kind="start_fanout", type=tn, value=n, limit=fanout, n=len(big),
                            msg=f"START fan: trunk relay {k[0]} stage {k[1]} drives {n} next relays > {fanout}"))
    return row, out


def _home(t, si, obs):
    from kv_start_corridor_event import _free_point
    return _free_point(si["origin"], obs)


def _hubs(o, targets, hub_um=HUB_UM, cap=FANOUT_MAX):
    """deterministic regions: targets {name: (x, y)} binned on a hub_um lattice anchored at the origin; a bin's hub is
    the centre of its members' bounding box (every member within hub_um of it); bins over cap split along their
    longer side.  -> [(hub_xy, [names])]"""
    bins = defaultdict(list)
    for n in sorted(targets):
        x, y = targets[n]
        bins[(math.floor((x - o[0]) / hub_um), math.floor((y - o[1]) / hub_um))].append(n)
    out = []
    todo = [bins[k] for k in sorted(bins)]
    while todo:
        m = todo.pop(0)
        xs, ys = [targets[n][0] for n in m], [targets[n][1] for n in m]
        if len(m) > cap:
            ax = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
            m = sorted(m, key=lambda n: (targets[n][ax], n))
            todo[:0] = [m[:len(m) // 2], m[len(m) // 2:]]
            continue
        out.append(((round((min(xs) + max(xs)) / 2, 3), round((min(ys) + max(ys)) / 2, 3)), m))
    return out


def _trunk(o, h, obs, bands, W, H, reach=REACH_UM):
    """relay trunk origin -> hub: (route, [sites on the way]) with hops <= reach, sites off the landing bands; if a band
    run along the direct corridor leaves no legal site, the corridor goes round the bands (they carry wires, no relays)"""
    import kv_start_corridor_event as KS
    from start_obstacle_path import length, relay_sites
    err = None
    for extra in (False, True):
        try:
            r = KS._route(tuple(o), tuple(h), obs + ([list(x) for x in bands] if extra else []), W, H)
            n = max(0, math.ceil(length(r) / STEP_UM) - 1)
            way = relay_sites(r, n, max_hop_um=reach, site_boxes=bands, clearance_um=KS.CLEAR_UM) if n else []
            return r, [list(q) for q in way]
        except ValueError as ex:
            err = ex
    raise ValueError(f"no legal relay trunk {tuple(o)} -> {tuple(h)}: {err}")


def fix_start(P, t, tn, margin=4.32, min_um=10.8, reach=REACH_UM):
    """R-REACH-1 fix on type dict t (in place).  -> report dict.  Raises ValueError when no legal corridor / site
    exists (the caller reports the type as NOT FIXED; nothing is half-written)."""
    import reset_tree as RT
    import kv_start_corridor_event as KS
    from start_obstacle_path import length, relay_sites
    si = start_info(t)
    row0, f0 = start_findings(t, tn, reach)
    rep = dict(type=tn, before=row0, changed=[])
    if not f0:
        return rep
    W, H = t["outline_um"]
    ck = t["clock"]
    obs = KS.corridor_obstacles(t, margin, min_um)
    bands = [b["rect_um"] for b in si["bands"].values() if b.get("rect_um")]
    o = _home(t, si, obs)
    taps = RT.consumer_taps(P, tn)
    raw_prefix = "rst_n_t" if (t.get("reset") or {}).get("start_role") == "bootstrap" else "rr_t"

    def raw_of(xy):
        return f"{raw_prefix}{min(range(len(taps)), key=lambda j: (man(xy, taps[j][1:]), j))}"

    def route(a, b):
        return KS._route(tuple(a), tuple(b), obs, W, H)

    def free(p):
        return KS._free_point(p, obs + [list(x) for x in bands])
    kinds = {f["kind"] for f in f0}
    new = {}
    if kinds & {"start_writer_reach", "start_fanout"}:
        kinds.add("start_writer_reach") if (row0["writer_over"] or row0["origin_d_loads"] > FANOUT_MAX) else None
    if (row0["reader_over"] or row0["origin_loads"] > FANOUT_MAX) and si["ins"]:
        tg = {b: free(_centre(si["bands"][b]["rect_um"])) for b in si["ins"]}
        hubs = [(free(h), m) for h, m in _hubs(o, tg)]
        tr = [_trunk(o, h, obs, bands, W, H, reach) for h, _m in hubs]
        routes = [x[0] for x in tr]
        # trunk relays of a hub: the hub relay itself + ceil(L / STEP) - 1 on the way; one more stage per ring
        need = [len(x[1]) + 1 for x in tr]
        depth = max(need) + 1
        pads = [free((o[0] + (i + 1) * PAD_PITCH_UM, o[1])) for i in range(depth - 1 - min(need))]
        branches, hub_rep = {}, []
        for (h, members), (r, way), n in zip(hubs, tr, need):
            k = depth - 1 - n                      # dwell stages at the origin home (shared by every such trunk)
            trunk = [list(p) for p in pads[:k]] + [list(p) for p in way] + [list(h)]
            hub_rep.append(dict(hub=list(h), rings=len(members), trunk_stages=len(trunk), dwell=k,
                                corridor_um=round(length(r), 1)))
            for b in members:
                last = tg[b]
                if man(h, last) > reach:
                    raise ValueError(f"{tn}.{b}: ring {man(h, last):.0f} um from its hub")
                st = trunk + [list(last)]
                pts = [list(o)] + st
                if max(man(a, c) for a, c in zip(pts, pts[1:])) > reach + EPS:
                    raise ValueError(f"{tn}.{b}: no relay sites within {reach:g} um on the START corridor")
                branches[b] = dict(stages=[dict(xy_um=[round(xy[0], 3), round(xy[1], 3)], raw_reset=raw_of(xy))
                                           for xy in st])
        cfg = dict(depth=depth, share_trunk=True, branches=branches)
        if not ck.get("landing_origin_rect_um") and not (ck.get("landing_writer_start") or {}).get("origin_rect_um"):
            cfg["origin_rect_um"] = [round(max(0.0, o[0] - 8.64), 3), round(max(0.0, o[1] - 6.48), 3),
                                     round(min(W, o[0] + 8.64), 3), round(min(H, o[1] + 6.48), 3)]
        new["landing_reader_start"] = cfg
        rep["reader"] = dict(depth=depth, hubs=hub_rep, rings=len(branches),
                             old_depth=int(si["reader"].get("depth", 0) or 0))
        rep["changed"].append("landing_reader_start")
    if "start_writer_reach" in kinds and si["outs"]:
        old = si["writer"]
        if old.get("reuse_relay_origin"):
            raise ValueError(f"{tn}: writer START reuse_relay_origin form: re-site by hand (HEAD relay origin)")
        tg = {}
        for b in si["outs"]:
            q = free(_inside(si["pins"]["cland_fstart_out_" + b], W, H, 4.32))
            if man(o, q) > KS.NEED_UM or b in (old.get("branches") or {}):
                tg[b] = q
        hubs = [(free(h), m) for h, m in _hubs(o, tg)]
        tr = [_trunk(o, h, obs, bands, W, H, reach) for h, _m in hubs]
        need = [len(x[1]) + 1 for x in tr]
        depth = max(max(need) + 1, int(old.get("depth", 0) or 0))
        pads = [free((o[0] - (i + 1) * PAD_PITCH_UM, o[1])) for i in range(depth - 1 - min(need))]
        branches = {}
        for (h, members), (r, way), n in zip(hubs, tr, need):
            k = depth - 1 - n
            trunk = [list(p) for p in pads[:k]] + [list(p) for p in way] + [list(h)]
            for b in members:
                # the last relay sits between its hub and the FSTART pin (the face flop itself is at the pin)
                last = free(((h[0] + tg[b][0]) / 2.0, (h[1] + tg[b][1]) / 2.0))
                pts = [list(o)] + trunk + [list(last), list(tg[b])]
                if max(man(a, c) for a, c in zip(pts, pts[1:])) > reach + EPS:
                    raise ValueError(f"{tn}.{b}: no writer relay sites within {reach:g} um")
                branches[b] = dict(stages=[dict(xy_um=[round(xy[0], 3), round(xy[1], 3)], raw_reset=raw_of(xy))
                                           for xy in trunk + [list(last)]])
        if branches:
            keep = {k: v for k, v in old.items() if k not in ("depth", "branches")}
            new["landing_writer_start"] = dict(keep, depth=depth, share_trunk=True, branches=branches)
            rep["writer"] = dict(depth=depth, branches=len(branches), hubs=len(hubs),
                                 old_depth=int(old.get("depth", 0) or 0))
            rep["changed"].append("landing_writer_start")
    trial = copy.deepcopy(t)
    trial["clock"].update(copy.deepcopy(new))
    row1, f1 = start_findings(trial, tn, reach)
    if f1:
        raise ValueError(f"{tn}: fix leaves {[f['kind'] for f in f1]} ({f1[0]['msg'][:120]})")
    ck.update(new)
    rep["after"] = row1
    return rep


# ------------------------------------------------------------------------------ rules 2 + 3: barriers and windows
def _bus_points(P, tn):
    import check as CK
    try:
        return CK._bus_targets(P, tn)
    except Exception:
        return {}


def _side(P):
    """core_conns sidecar of the plan ({type: {core: {port: ["bus:<bus>", ...]}}}, check.load_core_conns), cached"""
    if getattr(P, "_r_reach_side", None) is None:
        import check as CK
        try:
            P._r_reach_side = CK.load_core_conns(str(Path(P.path).parent) if P.path else None)
        except Exception:
            P._r_reach_side = {}
    return P._r_reach_side


def _consumers(P, t, tn):
    """{bus: {core inst}} consumers / producers the plan names: buses[].leaf (hard core or its children) and the
    core_conns sidecar "bus:<name>" targets"""
    cores = [hc["inst"] for hc in t.get("hard_cores", []) or []]
    out = defaultdict(set)
    for b in t.get("buses", []) or []:
        li = (b.get("leaf") or "").split(".")[0]
        for c in cores:
            if li and (c == li or c.startswith(li + "_") or c.startswith(li + ".")):
                out[b["name"]].add(c)
    for ci, ports in (_side(P).get(tn) or {}).items():
        for tgs in ports.values():
            for tg in tgs:
                if tg.startswith("bus:") and ci in cores:
                    out[tg[4:]].add(ci)
    return out


def _station_buses(t):
    out = set()
    for e in t.get("internal_stations", []) or []:
        c = str(e.get("conn") or "")
        if c.startswith("bus:"):
            out.add(c[4:])
    return out


def _inside(pt, W, H, d=EDGE_IN_UM):
    return (min(max(pt[0], d), W - d), min(max(pt[1], d), H - d))


def barrier_findings(P, t, tn, reach=REACH_UM, barrier=BARRIER_UM):
    """rule 2 -> (row, findings)"""
    boxes = macro_boxes(t)
    big = {k: b for k, b in boxes.items() if max(b[2] - b[0], b[3] - b[1]) >= barrier - EPS}
    if not big:
        return None, []
    W, H = t["outline_um"]
    homes = t.get("reach_homes") or []
    stn = _station_buses(t)
    pts = _bus_points(P, tn)
    buses = [b for b in t.get("buses", []) if b.get("kind", "data") != "clock" and b["name"] in pts]
    cons = _consumers(P, t, tn)
    loose = [b["name"] for b in buses if not b.get("leaf") and b["name"] not in stn and b["name"] not in cons
             and not any(b["name"] in (h.get("buses") or []) or "*" in (h.get("buses") or []) for h in homes)]
    out = []
    worst = max(big, key=lambda k: max(big[k][2] - big[k][0], big[k][3] - big[k][1]))
    wdim = max(big[worst][2] - big[worst][0], big[worst][3] - big[worst][1])
    # a barrier only matters when buses sit on both sides of it: face points more than the reach apart round it
    sides = set()
    for n in loose:
        p = pts[n][1]
        b = big[worst]
        sides.add(("W" if p[0] < b[0] else "E" if p[0] > b[2] else "M", "S" if p[1] < b[1] else "N" if p[1] > b[3]
                   else "M"))
    row = dict(type=tn, barrier=worst, barrier_um=round(wdim, 1), barriers=len(big), buses=len(buses),
               unanchored=len(loose), homes=len(homes), sides=len(sides), over=0)
    if loose and len(sides) > 1:
        out.append(dict(rule="2", kind="barrier_unanchored", type=tn, value=len(loose), limit=0, n=len(loose),
                        msg=f"macro barrier: {worst} is {wdim:.0f} um long (>= {barrier:g}) and {len(loose)} face "
                            f"buses on {len(sides)} sides of it name no consumer (no leaf, no internal_stations, no "
                            f"reach_homes), e.g. {loose[0]}: declare reach_homes [{{name, rect_um, buses}}] or move "
                            f"the windows to the consumer's side"))
    if homes:
        import kv_start_corridor_event as KS
        from start_obstacle_path import length
        obs = KS.corridor_obstacles(t, 4.32, 10.8)
        for h in homes:
            r = h["rect_um"]
            for b in buses:
                n = b["name"]
                if n in stn or not (n in (h.get("buses") or []) or "*" in (h.get("buses") or [])):
                    continue
                a = KS._free_point(_inside(pts[n][1], W, H), obs)
                q = KS._free_point((min(max(a[0], r[0]), r[2]), min(max(a[1], r[1]), r[3])), obs)
                try:
                    L = length(KS._route(a, q, obs, W, H))
                except ValueError:
                    L = float("inf")
                if L > reach + EPS:
                    row["over"] += 1
                    out.append(dict(rule="2", kind="barrier_hop", type=tn, value=round(L, 1) if L < 1e9 else -1,
                                    limit=reach, n=1, bus=n, home=h.get("name"),
                                    msg=f"macro barrier: bus {n} window -> home {h.get('name')} is "
                                        f"{L:.0f} um round the macros (> {reach:g}) with no internal_stations "
                                        f"bus:{n} chain (fix: reach_rules.py fix --rules 2, +"
                                        f"{max(1, math.ceil(L / STEP_UM) - 1) if L < 1e9 else '?'} cycles)"))
    return row, out


def fix_barrier(P, t, tn, reach=REACH_UM):
    """rule 2 fix (opt-in): an internal_stations chain bus:<name> for every barrier_hop finding, sites on the
    macro-free corridor, k = ceil(L / STEP) - 1 stations.  The lane cycles (+k) follow by reach_fix.sync_fixed_cycles /
    the die latency step, as for every station add (STREET-RULE-1 lever 1)."""
    import kv_start_corridor_event as KS
    from start_obstacle_path import length, relay_sites
    _row, fs = barrier_findings(P, t, tn, reach)
    W, H = t["outline_um"]
    obs = KS.corridor_obstacles(t, 4.32, 10.8)
    pts = _bus_points(P, tn)
    homes = {h.get("name"): h for h in t.get("reach_homes") or []}
    width = {b["name"]: b for b in t.get("buses", [])}
    rep = dict(type=tn, added=[])
    for f in fs:
        if f["kind"] != "barrier_hop" or f["value"] < 0:
            continue
        n, r = f["bus"], homes[f["home"]]["rect_um"]
        a = KS._free_point(_inside(pts[n][1], W, H), obs)
        q = KS._free_point((min(max(a[0], r[0]), r[2]), min(max(a[1], r[1]), r[3])), obs)
        rt = KS._route(a, q, obs, W, H)
        k = max(1, math.ceil(length(rt) / STEP_UM) - 1)
        regs = relay_sites(rt, k, max_hop_um=reach, clearance_um=KS.CLEAR_UM)
        face = pts[n][0]
        isin = width[n].get("dir") == "in"
        t.setdefault("internal_stations", []).append(dict(
            conn=f"bus:{n}", from_um=[round(v, 3) for v in (a if isin else q)],
            to_um=[round(v, 3) for v in (q if isin else a)], regs_um=regs if isin else regs[::-1],
            bits=int(width[n].get("width", 1)),
            **({"launch": f"face:{face}"} if isin else {"capture": f"face:{face}"}),
            note=f"R-REACH-2 (RULEBOOK 11-13): {length(rt):.0f} um round the macro barrier to reach_home "
                 f"{f['home']}: {k} FIRM station(s), +{k} cycle(s)"))
        rep["added"].append(dict(bus=n, stations=k, corridor_um=round(length(rt), 1)))
    return rep


def window_rows(P, t, tn, target=WINDOW_UM):
    """rule 3 (report + warning): every face bus with a known consumer box (buses[].leaf hard core, or its
    reach_home): window -> consumer distance, bit-mm and the buffers that wire costs"""
    pts = _bus_points(P, tn)
    boxes = {}
    for hc in t.get("hard_cores", []) or []:
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
        boxes[hc["inst"]] = (x0, y0, x0 + hc["outline_um"][0], y0 + hc["outline_um"][1])
    homes = t.get("reach_homes") or []
    cons = _consumers(P, t, tn)
    rows = []
    for b in t.get("buses", []) or []:
        n = b["name"]
        if n not in pts or b.get("kind", "data") == "clock":
            continue
        cand = [boxes[c] for c in cons.get(n, ()) if c in boxes]
        cand += [tuple(h["rect_um"]) for h in homes if n in (h.get("buses") or []) or "*" in (h.get("buses") or [])]
        if not cand:
            continue
        d = min(box_dist(pts[n][1], r) for r in cand)
        rows.append(dict(bus=n, bits=int(b.get("width", 1)), dist_um=round(d, 1)))
    if not rows:
        return None, []
    bits = sum(r["bits"] for r in rows)
    mm = sum(r["bits"] * r["dist_um"] for r in rows) / 1000.0
    far = [r for r in rows if r["dist_um"] > target]
    row = dict(type=tn, buses=len(rows), bits=bits, bit_mm=round(mm, 1), mean_um=round(1000.0 * mm / max(bits, 1), 1),
               est_buffers=int(sum(r["bits"] * r["dist_um"] for r in rows) / BUF_UM), far=len(far),
               far_bits=sum(r["bits"] for r in far))
    out = []
    if far:
        w = max(far, key=lambda r: r["bits"] * r["dist_um"])
        out.append(dict(rule="3", kind="window_far", type=tn, value=row["far_bits"], limit=0, n=len(far), warn=True,
                        msg=f"bus window: {len(far)} face buses ({row['far_bits']} bits) sit more than {target:g} um "
                            f"from their consumer; {row['bit_mm']:.0f} bit-mm ~ {row['est_buffers']} face-net buffers; "
                            f"worst {w['bus']} {w['bits']} b x {w['dist_um']:.0f} um (MOVE-WINDOW at the next plan event)"))
    return row, out


# ------------------------------------------------------------------------------------ rule 4: forwarded clock source
def _grid(P, tn):
    import schema
    c = P.__dict__.setdefault("_r_reach_grid", {})
    if tn not in c:
        c[tn] = {n: (x, y) for n, x, y in schema.tap_grid(P, tn)}
    return c[tn]


def fwd_findings(P, t, tn, reach=REACH_UM):
    import schema
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    pins = [q for q in lc.get("pins", []) if q.get("kind") == "clock" and q.get("dir") == "out"]
    if not pins:
        return None, []
    try:
        g = _grid(P, tn)
    except Exception as ex:      # no tap grid: the clock checks own that
        return dict(type=tn, fwd_out=len(pins), over=0, dangling=0, root=0, note=str(ex)[:80]), []
    taps = [n for n in g if n != "clk"] or list(g)
    over, dang, root, worst, unfix = [], [], [], 0.0, []
    for q in pins:
        s, xy = q.get("source_clock_port"), q["xy_um"]
        if s is None:
            continue
        near = min(taps, key=lambda n: (man(g[n], xy), n))
        h1 = man(g[near], xy)
        if s not in g:
            dang.append((q["name"], s, near, h1))
        else:
            h0 = man(g[s], xy)
            worst = max(worst, h0)
            if h0 > reach + EPS:
                (root if s == "clk" else over).append((q["name"], s, near, h1, h0))
            else:
                continue
        if h1 > reach + EPS:
            unfix.append((q["name"], near, h1))
    row = dict(type=tn, fwd_out=len(pins), over=len(over), dangling=len(dang), root=len(root),
               worst_hop_um=round(worst, 1), no_tap_in_reach=len(unfix))
    out = []
    n = len(over) + len(dang) + len(root)
    if n:
        ex = (over or root or dang)[0]
        out.append(dict(rule="4", kind="fwd_source", type=tn, value=round(worst, 1), limit=reach, n=n,
                        msg=f"forwarded clock source: {len(over)} outputs take a tap more than {reach:g} um from "
                            f"their pin, {len(root)} the far root, {len(dang)} a tap that no longer exists; e.g. "
                            f"{ex[0]} <- {ex[1]} (nearest tap {ex[2]} at {ex[3]:.0f} um; fix: reach_rules.py fix "
                            f"--rules 4)"))
    if unfix:
        out.append(dict(rule="4", kind="fwd_no_tap", type=tn, value=round(max(u[2] for u in unfix), 1), limit=reach,
                        n=len(unfix), msg=f"forwarded clock source: {len(unfix)} outputs have NO tap within "
                                          f"{reach:g} um of the pin, e.g. {unfix[0][0]} (nearest {unfix[0][1]} "
                                          f"{unfix[0][2]:.0f} um): add a tap or move the pin"))
    return row, out


def fix_fwd(P, t, tn, reach=REACH_UM):
    import schema
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    rep = dict(type=tn, repoints=[])
    if not any(q.get("kind") == "clock" and q.get("dir") == "out" for q in lc.get("pins", [])):
        return rep
    g = _grid(P, tn)
    taps = [n for n in g if n != "clk"] or list(g)
    for q in lc.get("pins", []):
        if not (q.get("kind") == "clock" and q.get("dir") == "out") or q.get("source_clock_port") is None:
            continue
        s, xy = q["source_clock_port"], q["xy_um"]
        if s in g and man(g[s], xy) <= reach + EPS:
            continue
        near = min(taps, key=lambda n: (man(g[n], xy), n))
        if man(g[near], xy) > reach + EPS or near == s:
            continue
        q["source_clock_port"] = near
        if q.get("source_clock_tap") in (s, "clk"):
            q["source_clock_tap"] = near
        if s == "clk":
            lc["forwarded_clock_only_inputs"] = True      # FWDCLK-1 form (export_source_tap.py), as fwd_src_fix
        rep["repoints"].append(dict(pin=q["name"], old=s, new=near, hop_before_um=round(man(g[s], xy), 1) if s in g
                                    else None, hop_after_um=round(man(g[near], xy), 1)))
    return rep


# ------------------------------------------------------------------------------------------------------- plan level
def type_findings(P, tn, rules=RULES):
    t = P.types[tn]
    rows, out = {}, []
    for r, fn in (("1", lambda: start_findings(t, tn)), ("2", lambda: barrier_findings(P, t, tn)),
                  ("3", lambda: window_rows(P, t, tn)), ("4", lambda: fwd_findings(P, t, tn))):
        if r not in rules:
            continue
        try:
            row, fs = fn()
        except Exception as ex:          # loud: a type the rule cannot read is a finding (warning), never a silent pass
            row, fs = None, [dict(rule=r, kind="unreadable", type=tn, value=0, limit=0, n=1, warn=True,
                                  msg=f"R-REACH-{r} could not evaluate the type: {type(ex).__name__}: {str(ex)[:160]}")]
        if row is not None:
            rows[r] = row
        out += fs
    return rows, out


def plan_findings(P, rx=None, rules=RULES):
    rows, out = {}, []
    for tn in used_types(P.raw, rx):
        r, fs = type_findings(P, tn, rules)
        rows[tn] = r
        out += fs
    return rows, out


def check_plan(P, R, max_msgs=40):
    """G0 entry (check.py run): ERROR per finding under check "r_reach" (budgets.r_reach "warn" -> warnings; "off"
    skips); rule 3 is always a warning.  -> summary dict"""
    mode = P.budgets.get("r_reach", "error")
    if mode == "off":
        return dict(mode="off")
    rows, fs = plan_findings(P)
    n = defaultdict(int)
    for f in fs:
        k = f"R-REACH-{f['rule']} {f['kind']}"
        n[k] += 1
        if f.get("warn") or mode == "warn":
            if n[k] <= max_msgs:
                R.warn("r_reach", f"[{k}] type {f['type']}: {f['msg']}", type=f["type"], rule=f["rule"])
        else:
            R.err("r_reach", f"[{k}] type {f['type']}: {f['msg']}", type=f["type"], rule=f["rule"], kind=f["kind"])
    return dict(mode=mode, findings=dict(n), types=len({f["type"] for f in fs if not f.get("warn")}))


def census(P, rules=RULES):
    rows, fs = plan_findings(P, rules=rules)
    per = defaultdict(set)
    for f in fs:
        per[f"{f['rule']}:{f['kind']}"].add(f["type"])
    return dict(die=P.name, soft_types=len(rows),
                affected={k: len(v) for k, v in sorted(per.items())},
                types={k: sorted(v) for k, v in sorted(per.items())},
                face_bit_mm=round(sum(r["3"]["bit_mm"] for r in rows.values() if "3" in r), 1),
                est_face_buffers=sum(r["3"]["est_buffers"] for r in rows.values() if "3" in r))


def _load(path, repo=None):
    import schema
    if repo:
        import os
        os.chdir(repo)
    raw = json.loads(Path(path).read_text())
    return raw, schema.Plan(raw, path)


def cmd_check(a):
    raw, P = _load(a.plan, a.repo)
    rows, fs = plan_findings(P, a.types, tuple(a.rules.split(",")))
    errs = [f for f in fs if not f.get("warn")]
    if a.json:
        Path(a.json).write_text(json.dumps(dict(schema=SCHEMA, plan=a.plan, rows=rows, findings=fs), indent=1))
    if a.tsv:
        with open(a.tsv, "w") as o:
            o.write("rule\tkind\ttype\tvalue\tlimit\tn\tmsg\n")
            for f in fs:
                o.write("\t".join(str(f[k]) for k in ("rule", "kind", "type", "value", "limit", "n", "msg")) + "\n")
    per = defaultdict(set)
    for f in fs:
        per[f"R-REACH-{f['rule']} {f['kind']}"].add(f["type"])
    print(f"R-REACH {P.name}: {len(rows)} soft types, {len(errs)} errors, {len(fs) - len(errs)} warnings")
    for k in sorted(per):
        print(f"  {k}: {len(per[k])} types")
    return 1 if errs else 0


def cmd_fix(a):
    raw, P = _load(a.plan, a.repo)
    rules = tuple(a.rules.split(","))
    rep = dict(schema=SCHEMA, plan=a.plan, in_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
               rules=list(rules), types={}, not_fixed=[])
    for tn in used_types(raw, a.types):
        t = raw["partition_types"][tn]
        tr = {}
        for r, fn in (("4", lambda: fix_fwd(P, t, tn)), ("1", lambda: fix_start(P, t, tn)),
                      ("2", lambda: fix_barrier(P, t, tn))):
            if r not in rules:
                continue
            keep = copy.deepcopy(t)
            try:
                x = fn()
            except Exception as ex:
                t.clear()
                t.update(keep)
                rep["not_fixed"].append(dict(type=tn, rule=r, error=f"{type(ex).__name__}: {str(ex)[:200]}"))
                continue
            if x.get("changed") or x.get("repoints") or x.get("added"):
                tr[RULE_NAME[r]] = x
        if tr:
            rep["types"][tn] = tr
    import schema
    errs = schema.validate(raw)
    if errs:
        print(f"reach_rules fix: the fixed plan fails schema validation: {errs[:3]}", file=sys.stderr)
        return 3
    txt = json.dumps(raw, indent=1) + "\n"
    Path(a.out_plan).write_text(txt)
    rep["out_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"reach_rules fix {P.name}: {len(rep['types'])} types changed, {len(rep['not_fixed'])} NOT FIXED -> {a.out_plan}")
    for x in rep["not_fixed"][:10]:
        print(f"  NOT FIXED {x['type']} rule {x['rule']}: {x['error']}")
    return 2 if rep["not_fixed"] else 0


def cmd_census(a):
    out = []
    for p in a.plans:
        _raw, P = _load(p, a.repo)
        c = census(P)
        out.append(c)
        print(f"{c['die']}: {c['soft_types']} soft types; " + ", ".join(f"{k} {v}" for k, v in c["affected"].items())
              + f"; face nets {c['face_bit_mm']} bit-mm ~ {c['est_face_buffers']} buffers")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("plan")
    c.add_argument("--json")
    c.add_argument("--tsv")
    f = sub.add_parser("fix")
    f.add_argument("plan")
    f.add_argument("--out-plan", required=True)
    f.add_argument("--report", required=True)
    for s in (c, f):
        s.add_argument("--repo")
        s.add_argument("--types")
    c.add_argument("--rules", default="1,2,3,4")
    f.add_argument("--rules", default="1,4")
    n = sub.add_parser("census")
    n.add_argument("plans", nargs="+")
    n.add_argument("--repo")
    n.add_argument("--json")
    a = ap.parse_args(argv)
    for k in ("plan", "json", "tsv", "out_plan", "report"):        # --repo changes the working directory
        if getattr(a, k, None):
            setattr(a, k, str(Path(getattr(a, k)).resolve()))
    if getattr(a, "plans", None):
        a.plans = [str(Path(x).resolve()) for x in a.plans]
    return dict(check=cmd_check, fix=cmd_fix, census=cmd_census)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
