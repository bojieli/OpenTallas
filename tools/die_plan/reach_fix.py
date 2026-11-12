#!/usr/bin/env python3
"""REACH-FIX-1 (OWNER 11-12 "the reach problem can be resolved via fixed scripts"): ONE deterministic, die-agnostic reach
stage for every die plan event.  It FIXES the plan, it does not only report, and it is idempotent (a fixed plan run
again changes nothing).

    reach_fix.py check PLAN [--repo SRC] [--types RE] [--json OUT] [--tsv OUT] [-j N]
    reach_fix.py fix   PLAN --out-plan NEW.json --event EVENT.json [--repo SRC] [--types RE] [--classes 1,2,3,4,5]

PLAN is any die plan (S81, s81_head, qwen_compute, qwen_kvsys, hbm).  --repo is the source tree the plan's repo-relative
side files (clock.sink_bins_file, pins files) resolve against (default: this checkout).  Only non-hard partition types
are evaluated (hard cores are built and signed on their own kit).

CLASSES (limits from the canonical rules; METHODOLOGY 12.1e / 12.8b, geom_rules for the AUTO-GEOM limits):
  1 clock_tap_radius   every die-clock sink within RADIUS_UM (200, 12.8b) of the tap it is assigned to under the kit's
                       own split rule (taps.assign = clock_taps.tcl: nearest grid tap, then capacity moves <= radius).
                       Sinks = plan_geom.type_sites (face / ft / internal inventory incl. sink_bins_file, reset relays,
                       landing groups, ring local-read flops) on the grid taps (clk, clk_t<i>) the kit exports.
  2 clock_tap_sinks    no tap above CAP_SINKS (800, see CAP_BASIS) under the same split.
  3 fwd_clock          every forwarded / incoming clock (clock.edge_clocks fclk_in_*, landing bands): farthest sink of
                       the port <= one repeater span (450 um, owner repeater rule) from its pin, else the port joins
                       clock.edge_split_ports: the kit's clock_edge_split.tcl builds a repeater chain every 200 um from
                       the pin to each sink group root (groups <= 1500 sinks / 300 um).  Class 2 also covers plain
                       PHY-edge clocks the kit leaves as one tree (S81 clk_pma_rx 22k): they join the same list.
  4 signal_hop         every ft slot hop (in face -> stations -> out face) and internal station hop (from -> regs -> to)
                       <= REACH_UM (405, 12.1e); fixed by +k registers on the hop (STREET-RULE-1 lever 1, owner
                       approved 11-12: street_rule.add_ft_regs / hub_repack.route_station).
  5 reset_reach        reset relay chain hops <= 405 and every raw reset reference (reset_start_raw_exports, landing
                       reader/writer START stages, landing_local_resets) names a relay of the re-solved reset tree at its
                       depth within 405 um; fixed by street_rule.reset_resel (STREET-RULE-1 d94ec4b983).

  6 landed_window      (die level, only with --landed-hops TSV) a landed crossing launch_part -> capture_part over the
                       landing window by over_ps gets k = ceil(over_ps / window) cycles on every lane of that part pair
                       (lanes[].fixed_cycles = latency cycles + k; owner-approved +1 register per over-reach hop).

INPUTS (REACH-FIX-2): cap per die (DIE_CAP: S81 800, QC / KV / HEAD / HBM 1200; --cap overrides); --sinks-dir D /
--sinks T=F placed sinks (tap_sinks_dump.tcl JSON) replace the plan sinks of those types (a dump outside the outline is
refused); --min-taps T=N die-owner tap counts; check --tap-table TSV = one row per tap (sinks, max tap-to-sink um).
Over-cap taps split by DENSITY-WEIGHTED k-medians (k = ceil(load / 0.875 cap)); reset re-selects keep ROLE + depth.

FIX ORDER (each a stage of the same pass, deterministic): 4 signal hops -> 1+2 taps (tap parameters + added taps at the
weighted median of every over-cap / over-radius cluster, legal by schema.tap_clear; the reset tree then re-solves from the
taps) -> 5 reset re-select -> 3 forwarded-clock repeater plan.  A type is APPLIED only if its export taps load
(schema.tap_grid) and no class got worse; else it keeps the base and the row says why.
"""
import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))

SCHEMA = "opentallas.reach_fix.v1"
RADIUS_UM = 200.0          # METHODOLOGY 12.8b entry-to-sink ~200 um (the kit tap_radius_um default for density taps)
CAP_SINKS = 800            # see CAP_BASIS
CAP_BASIS = ("tap cap 800: METHODOLOGY 3.3 gives ~1000-1500 sinks/tap; the QC s28 HOLD-TAP-SPLIT measured real "
             "netlists 883-1,200 per tap at the 1200 kit cap, and plan sinks are a LOWER bound of the netlist (internal "
             "registers count only with sink_bins_file); 800 plan sinks keeps the measured real load under the 1200 "
             "kit cap with the measured planner/netlist ratio (s28: planner 24,788 vs netlist 67,305 worst, 1.1-2.7x)")
REACH_UM = 405.0           # METHODOLOGY 12.1e registered hop
REPEATER_UM = 450.0        # METHODOLOGY 12.1e repeaters <= 450 um (owner repeater rule 10-23)
GRID = 4.32
CLASSES = ("1", "2", "3", "4", "5")
CLASS_NAME = {"1": "clock_tap_radius", "2": "clock_tap_sinks", "3": "fwd_clock", "4": "signal_hop", "5": "reset_reach",
              "6": "landed_window"}
# REACH-FIX-2 (COORD 11-12 05:19 rulings): sinks-per-tap cap per die.  S81 keeps 800 plan sinks (CAP_BASIS: plan sinks
# are a lower bound there); QC and KV 1200 (measured bins); HEAD / HBM 1200 = METHODOLOGY 3.3 (~1000-1500 per tap),
# 12 names no number.  --cap overrides.
DIE_CAP = {"s81": 800, "qwen_compute": 1200, "qwen_kvsys": 1200, "s81_head": 1200, "hbm": 1200}
SPLIT_FRAC = 0.875         # an over-cap tap splits into ceil(load / (0.875 cap)) k-medians groups (X-TIER-OTC 700/800)
LANDED_WINDOW_PS = 416.5   # S81 landing window (DIE-RECHECK-1 / DIE-S81-87 reach_hops tables)
MEASURED = {}              # type -> [(x, y, 1.0)] placed clock sinks (tap_sinks_dump.tcl), replaces the plan sinks
MIN_TAPS = {}              # type -> minimum tap count (die-owner input, e.g. KV hgi_v8 39)
TAP_TABLE = False          # check --tap-table: keep per-tap rows


def die_cap(name, cap=None):
    return int(cap) if cap else DIE_CAP.get(str(name), CAP_SINKS)


def load_measured(dirs=(), specs=(), outlines=None):
    """placed sinks: --sinks-dir D (D/<type>.json) and --sinks TYPE=FILE, JSON [[x, y], ...] (tap_sinks_dump.tcl).
    A file with a sink outside the type outline (form changed since that place) is refused: {type: reason}."""
    files = {}
    for d in dirs or ():
        for f in sorted(Path(d).glob("*.json")):
            files[f.stem] = f
    for s in specs or ():
        tn, f = s.split("=", 1)
        files[tn] = Path(f)
    out, bad = {}, {}
    for tn, f in sorted(files.items()):
        pts = [(float(p[0]), float(p[1]), 1.0) for p in json.loads(Path(f).read_text())]
        ol = (outlines or {}).get(tn)
        if ol is None and outlines is not None:
            continue
        if ol and any(not (-1.0 <= x <= ol[0] + 1.0 and -1.0 <= y <= ol[1] + 1.0) for x, y, _w in pts):
            bad[tn] = "sink outside outline %s: placed DB of another form" % (ol,)
            continue
        if pts:
            out[tn] = pts
    return out, bad


def _wkmedians(pts, k, iters=25):
    """weighted k-medians (L1) of [(x, y, w)]: farthest-first seeds from the weighted median, nearest assignment,
    weighted-median centres.  Deterministic.  Returns (centres, groups)."""
    import taps as TP
    pts = [p if p[2] > 0 else (p[0], p[1], 1.0) for p in pts]
    c0 = (TP._wmedian(pts, 0), TP._wmedian(pts, 1))
    cen = [c0]
    dmin = [_d(p, c0) for p in pts]
    while len(cen) < k:
        i = max(range(len(pts)), key=lambda j: (dmin[j] * pts[j][2], -j))
        if dmin[i] <= 0:
            break
        cen.append((pts[i][0], pts[i][1]))
        dmin = [min(d, _d(p, cen[-1])) for d, p in zip(dmin, pts)]
    asg = None
    for _ in range(iters):
        new = [min(range(len(cen)), key=lambda c: (_d(p, cen[c]), c)) for p in pts]
        if new == asg:
            break
        asg = new
        groups = [[p for p, a in zip(pts, asg) if a == c] for c in range(len(cen))]
        cen = [(TP._wmedian(g, 0), TP._wmedian(g, 1)) if g else c for g, c in zip(groups, cen)]
    groups = [[p for p, a in zip(pts, asg) if a == c] for c in range(len(cen))]
    return cen, groups


# ------------------------------------------------------------------------------------------------------- loading
def set_repo(repo):
    """repo-relative plan side files (clock.sink_bins_file, ...) resolve against `repo` (the die's source tree)."""
    import taps as TP
    if repo:
        r = Path(repo).resolve()
        TP._root = lambda: r


def load_raw(path):
    p = Path(path)
    data = p.read_bytes()
    if p.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data), hashlib.sha256(data).hexdigest()


def plan_obj(raw, path):
    import schema as S
    return S.Plan(raw, Path(path).resolve())


def soft_types(P, rx=None):
    used = {p["type"] for p in P.parts.values()} if hasattr(P, "parts") else set(P.types)
    return [tn for tn in sorted(used) if not P.types[tn].get("hard") and (not rx or re.search(rx, tn))]


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _rect_far(p, r):
    """max Manhattan distance from p to the corners of rect r (the farthest flop of a filled band)."""
    x0, y0, x1, y1 = r
    return max(abs(p[0] - x) + abs(p[1] - y) for x in (x0, x1) for y in (y0, y1))


# ------------------------------------------------------------------------------------------------------- measure
def tap_metrics(P, tn, G=None, cap=CAP_SINKS, radius=RADIUS_UM):
    """classes 1 + 2 on the kit split: (row dict, assignment detail)."""
    import plan_geom as PG
    import geom_rules as GR
    import taps as TP
    G = G or PG.type_sites(P, tn)
    grid = [(n, x, y) for n, x, y in G["entries"] if GR.GRID_TAP_RE.match(n)]
    # sinks REACH-FIX added to a density planner's inventory (clock.reach_fix_sinks) are already in G as the kit flops
    # they stand for: drop their 'plan' copies once
    dup = defaultdict(int)
    for r in (P.types[tn].get("clock") or {}).get("reach_fix_sinks") or []:
        dup[(round(float(r[0]), 3), round(float(r[1]), 3))] += 1
    rows = []
    for x, y, w, k in G["sinks"]:
        key = (round(float(x), 3), round(float(y), 3))
        if k == "plan" and dup.get(key):
            dup[key] -= 1
            continue
        rows.append((x, y, w, k))
    if tn in MEASURED:                     # placed sinks (tap_sinks_dump.tcl): the real kit registers, not the plan
        rows = [(x, y, w, "measured") for x, y, w in MEASURED[tn]]
    G = dict(G, sinks=rows)
    sinks = [(float(x), float(y), float(w)) for x, y, w, _k in G["sinks"]]
    out = dict(taps=len(grid), sinks=round(sum(s[2] for s in sinks), 1),
               sink_source="measured" if tn in MEASURED else "plan",
               lower_bound=tn not in MEASURED and not (P.types[tn].get("clock") or {}).get("sink_bins_file"))
    # tap sites: on a hard core / macro (GEOM-VIS-1 clock-tap-on-macro) and stacked taps (tap-pileup, < taps.SEP_UM)
    try:
        from placement_obstacles import placement_boxes
        boxes = list(placement_boxes(P.types[tn], halo=0.0).values())
    except Exception:  # noqa: BLE001
        boxes = []
    out["tap_on_macro"] = sorted(n for n, x, y in grid
                                 if any(a + 1e-6 < x < c - 1e-6 and b + 1e-6 < y < d - 1e-6 for a, b, c, d in boxes))
    pile = 0
    for i in range(len(grid)):
        for j in range(i + 1, len(grid)):
            if _d(grid[i][1:], grid[j][1:]) < TP.SEP_UM - 1e-6:
                pile += 1
    out["tap_pileup"] = pile
    if not grid or not sinks:
        out.update(c1=len(out["tap_on_macro"]), c1_max_um=0.0, c2=pile, c2_max=0.0)
        return out, None
    load, far, own = TP.assign(grid, sinks, cap, radius)
    dist = [_d(s, (grid[j][1], grid[j][2])) for s, j in zip(sinks, own)]
    over_r = [i for i, d in enumerate(dist) if d > radius + 1e-6]
    kinds = defaultdict(int)
    for i in over_r:
        kinds[re.split(r"[:(]", G["sinks"][i][3])[0]] += 1
    out.update(c1=len(over_r) + len(out["tap_on_macro"]), c1_weight=round(sum(sinks[i][2] for i in over_r), 1), c1_kinds=dict(kinds),
               c1_max_um=round(max(dist), 1),
               c1_worst=(grid[own[max(range(len(dist)), key=dist.__getitem__)]][0]),
               c2=sum(1 for v in load if v > cap + 1e-6) + pile, c2_max=round(max(load), 1),
               c2_worst=grid[max(range(len(load)), key=load.__getitem__)][0],
               load_min=round(min(load), 1))
    if MIN_TAPS.get(tn) and len(grid) < MIN_TAPS[tn]:
        out["taps_short"] = MIN_TAPS[tn] - len(grid)
        out["c2"] += 1
    if TAP_TABLE:
        far = defaultdict(float)
        for d, j in zip(dist, own):
            far[j] = max(far[j], d)
        out["tap_rows"] = [[n, round(x, 3), round(y, 3), round(load[j], 1), round(far[j], 1)]
                           for j, (n, x, y) in enumerate(grid)]
    return out, dict(grid=grid, sinks=sinks, own=own, load=load, dist=dist,
                     kinds=[re.split(r"[:(]", k)[0] for _x, _y, _w, k in G["sinks"]])


def fwd_ports(P, tn, G=None):
    """[(port, (x, y) driver, [sink rects])] of the forwarded / incoming clocks of type tn."""
    """Mapping (clock_landings.py RTL): u_cland_<b>.fclk = fclk_in_<b> (landing_contract.ring_input_ports) and
    u_cland_monitor_<i>.fclk = fclk_in_cland_dn_<i> (clock_landing_plan monitor rings).  Driver = the port pin
    (landing_contract.pins[].xy_um, = edge_clocks[].tap_um); sinks = the band's flop rects
    (landing_place._band_groups: rect_um / rects_um / ff / freg / native role banks)."""
    import landing_place as LP
    t = P.types[tn]
    ck = t.get("clock") or {}
    lc = ck.get("landing_contract") or {}
    bands = lc.get("bands") or {}
    pins = {p.get("name"): p for p in lc.get("pins") or []}
    ports = []
    for e in ck.get("edge_clocks") or []:
        n = str(e.get("port", ""))
        if not n.startswith("fclk_in_"):
            continue
        p = pins.get(n) or {}
        ports.append((n, tuple(map(float, p.get("xy_um") or e["tap_um"]))))
    out = []
    for port, xy in ports:
        x = port[len("fclk_in_"):]
        m = re.fullmatch(r"cland_dn_(\d+)", x)
        bname = x if x in bands else ("monitor_" + m.group(1) if m and ("monitor_" + m.group(1)) in bands else None)
        b = bands.get(bname) if bname else None
        rects = []
        if b and not b.get("hard_core") and b.get("placement") != "FAIL":
            try:
                rects = [list(map(float, r)) for _p, r, _tag in LP._band_groups(tn, bname, b, t)]
            except Exception:  # noqa: BLE001  (a band LP cannot place: its rect_um still bounds the flops)
                rr = b.get("rects_um") or ([b["rect_um"]] if b.get("rect_um") else [])
                rects = [list(map(float, r)) for r in rr]
        out.append((port, xy, rects))
    return out


def fwd_metrics(P, tn, G=None, span=REPEATER_UM):
    """class 3: per fclk_in_* port, farthest band flop from the port pin.  OK when <= span, or when the port is in
    clock.edge_split_ports: the kit's clock_edge_split.tcl then builds a repeater chain every OT_EDGE_SPLIT_SEG_UM
    (200 um <= 450) from the pin to each group root (groups <= 1500 sinks, <= 300 um span)."""
    ck = P.types[tn].get("clock") or {}
    split = set(ck.get("edge_split_ports") or [])
    rows = []
    for port, xy, rects in fwd_ports(P, tn, G):
        if not rects:
            continue
        far = max(_rect_far(xy, r) for r in rects)
        rows.append(dict(port=port, far_um=round(far, 1), split=port in split,
                         ok=bool(far <= span + 1e-6 or port in split)))
    return rows


def edge_unsplit(P, tn):
    """class 2 (edge clocks, GEOM-VIS-1 overloaded single taps: S81 clk_pma_rx 22k, QC clk_d2d 22k): plain PHY-edge
    clock ports (period x1, not forwarded, no source latency) that the kit leaves as ONE tree because neither the die
    (gen_phys.EDGE_SPLIT_DIES) nor the type (clock.edge_split_ports) opts them into clock_edge_split.tcl."""
    import gen_phys as GP
    ck = P.types[tn].get("clock") or {}
    try:
        on = set(GP.edge_split_ports(P, tn))
    except Exception:  # noqa: BLE001
        return []
    return sorted(e["port"] for e in ck.get("edge_clocks") or []
                  if int(e.get("period_mult", 1)) == 1 and not str(e["port"]).startswith("fclk_in")
                  and "source_latency_ps" not in e and e.get("cdc") is None and e["port"] not in on)


def slot_ends(P, tn):
    """{slot name: (in pin xy, out pin xy)}: mean of the slot's bit pins (gen_phys.type_pins), the real chain ends."""
    import gen_phys
    acc = defaultdict(lambda: [0.0, 0.0, 0])
    try:
        pins = gen_phys.type_pins(P, tn)
    except Exception:  # noqa: BLE001
        return {}
    for name, _bit, _ln, x, y, _f in pins:
        if name[-2:] in ("_i", "_o"):
            a = acc[name]
            a[0] += x
            a[1] += y
            a[2] += 1
    out = {}
    for f in P.types[tn].get("ft_slots") or []:
        i, o = acc.get(f["name"] + "_i"), acc.get(f["name"] + "_o")
        if i and o and i[2] and o[2]:
            out[f["name"]] = ((i[0] / i[2], i[1] / i[2]), (o[0] / o[2], o[1] / o[2]))
    return out


def ft_slot_hops(t, f, ends=None):
    """register hops of ft slot f as the kit places it (taps.planned_sinks / face_flops.tcl): with regs_um for every
    station the chain in face -> regs -> out face (street_rule.ft_hops); else station 0 at the in pin and stations
    j = 1..k-1 at L*j/k on the slot's z-route, so every hop (incl. last station -> the neighbour's station 0 at the
    out pin) is L/k.  Window mid-points stand for the bit pins."""
    import street_rule as SR
    import route_supply as RS
    import taps as TP
    k = max(1, int(f.get("stations", 1) or 1))
    regs = [r for r in f.get("regs_um") or [] if isinstance(r, (list, tuple))]
    W, H = t["outline_um"]
    a = RS.face_point(W, H, f.get("in_face", "W"), f.get("in_window_um"))
    b = RS.face_point(W, H, f.get("out_face", "E"), f.get("out_window_um"))
    if ends and f.get("name") in ends:
        a, b = ends[f["name"]]
    if regs and len(regs) >= k:
        ch_ = [tuple(a)] + [tuple(r[:2]) for r in regs] + [tuple(b)]
        return [_d(p, q) for p, q in zip(ch_, ch_[1:])], "regs"
    bs = f.get("bit_sites_um")
    if k >= 2 and isinstance(bs, list) and len(bs) >= k - 1 and all(bs[j] for j in range(k - 1)):
        cw, ch = (f.get("bit_site_cell_um") or [0.0, 0.0])[:2]
        cen = [(sum(p[0] for p in bs[j]) / len(bs[j]) + cw / 2, sum(p[1] for p in bs[j]) / len(bs[j]) + ch / 2)
               for j in range(k - 1)]
        ch_ = [tuple(a)] + cen + [tuple(b)]
        return [_d(p, q) for p, q in zip(ch_, ch_[1:])], "bit_sites"
    pts = TP._zroute(tuple(a), tuple(b), f.get("in_face", "W"), f.get("out_face", "E"))
    L = sum(_d(p, q) for p, q in zip(pts, pts[1:]))
    return [L / k] * k, "even"


def hop_rows(t, reach=REACH_UM, ends=None):
    """class 4: [(um, label)] signal register hops of type t."""
    out = []
    for f in t.get("ft_slots") or []:
        hops, _form = ft_slot_hops(t, f, ends)
        for j, h in enumerate(hops):
            out.append((h, "ft %s h%d" % (f.get("name"), j)))
    for i, s in enumerate(t.get("internal_stations") or []):
        regs = [tuple(r[:2]) for r in s.get("regs_um") or [] if isinstance(r, (list, tuple))]
        if not s.get("from_um") or not s.get("to_um"):
            continue
        ch = [tuple(s["from_um"][:2])] + regs + [tuple(s["to_um"][:2])]
        for j, (a, b) in enumerate(zip(ch, ch[1:])):
            out.append((_d(a, b), "station %d %s h%d" % (i, s.get("conn", ""), j)))
    return out


def reset_metrics(P, tn, G=None, reach=REACH_UM):
    """class 5: reset relay chain hops and raw reset references on the re-solved reset tree."""
    import reset_tree as RT
    import plan_geom as PG
    t = P.types[tn]
    ck = t.get("clock") or {}
    out = dict(hops_over=0, hop_max_um=0.0, raw_bad=0, raw_detail=[])
    try:
        T = RT.for_type(P, tn)
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
        return out
    xy = {"rst_root_n": tuple(T["root"])}
    for r in T.get("relays", []):
        xy[r["q"]] = tuple(r["xy"])
    hops = [_d(xy[r["d"]], r["xy"]) for r in T.get("relays", []) if r["d"] in xy]
    out["hop_max_um"] = round(max(hops), 1) if hops else 0.0
    out["hops_over"] = sum(1 for h in hops if h > reach + 1e-6)
    allr = []
    if T.get("start"):
        try:
            allr += RT.start_relays(T)       # START broadcast: raw / run / gated copies (the nets the RTL has)
        except Exception:  # noqa: BLE001
            pass
    allr += list(T.get("relays", []))
    T = dict(T, _all=allr)
    names = defaultdict(list)
    for r in allr:
        names[r["name"]].append(r)
    refs = []
    for e in t.get("reset_start_raw_exports") or []:
        cand = names.get(e.get("instance")) or []
        r = next((c for c in cand if c.get("q") == e.get("net")), cand[0] if cand else None)
        refs.append(("export " + str(e.get("port")), r, e.get("xy_um"), e.get("net")))
    for key in ("landing_reader_start", "landing_writer_start"):
        for bus, br in ((ck.get(key) or {}).get("branches") or {}).items():
            for i, st in enumerate(br.get("stages", [])):
                q = st.get("raw_reset")
                if q:
                    refs.append(("%s.%s.%d" % (key, bus, i), _by_q(T, q), st.get("xy_um"), q))
    for i, lr in enumerate(ck.get("landing_local_resets") or []):
        q = lr.get("raw")
        if q:
            refs.append(("landing_local_resets.%d" % i, _by_q(T, q), lr.get("xy_um"), q))
    for tag, r, pt, net in refs:
        if r is None:
            out["raw_bad"] += 1
            out["raw_detail"].append("%s: %s not a relay of the re-solved tree" % (tag, net))
        elif pt and _d(r["xy"], pt) > reach + 1e-6:
            out["raw_bad"] += 1
            out["raw_detail"].append("%s: %s %.0f um from its stage" % (tag, net, _d(r["xy"], pt)))
        elif r.get("q") and net and net != r.get("q") and tag.startswith("export"):
            out["raw_bad"] += 1
            out["raw_detail"].append("%s: net %s != relay q %s" % (tag, net, r.get("q")))
    out["raw_refs"] = len(refs)
    return out


def _by_q(T, q):
    for r in T.get("_all") or T.get("relays", []):
        if r.get("q") == q:
            return r
    return None


def type_row(P, tn, cap=CAP_SINKS, radius=RADIUS_UM, reach=REACH_UM, span=REPEATER_UM):
    """all five classes for one type: {type, mode, c1..c5 counts, detail}."""
    import plan_geom as PG
    t = P.types[tn]
    ck = t.get("clock") or {}
    row = dict(type=tn, tap_mode=ck.get("tap_mode", "grid"), outline=t.get("outline_um"))
    try:
        G = PG.type_sites(P, tn)
    except Exception as e:  # noqa: BLE001  (schema.tap_grid raised: the export taps do not load)
        row.update(error="tap export: %s: %s" % (type(e).__name__, str(e)[:200]), c1=1, c2=0, c3=0, c4=0, c5=0)
        G = None
    if G is not None:
        tm, _ = tap_metrics(P, tn, G, cap, radius)
        row.update(tm)
        eu = edge_unsplit(P, tn)
        row["edge_unsplit"] = eu
        row["c2_tap"] = row.get("c2") or 0
        row["c2"] = row["c2_tap"] + len(eu)
        fw = fwd_metrics(P, tn, G, span)
        row["fwd"] = fw
        row["c3"] = sum(1 for r in fw if not r["ok"])
        row["c3_max_um"] = max([r["far_um"] for r in fw], default=0.0)
    hops = hop_rows(t, reach, slot_ends(P, tn))
    bad = [h for h in hops if h[0] > reach + 0.01]
    row.update(c4=len(bad), c4_max_um=round(max([h[0] for h in hops], default=0.0), 1),
               c4_worst=max(bad)[1] if bad else None)
    rs = reset_metrics(P, tn, G, reach)
    row["reset"] = rs
    row["c5"] = rs["hops_over"] + rs["raw_bad"] + (1 if rs.get("error") else 0)
    row["viol"] = sum(int(bool(row.get("c" + c))) for c in CLASSES)
    return row


# ------------------------------------------------------------------------------------------------------- fix
def _set_le(ck, key, v, f, rec):
    old = ck.get(key)
    if old is None or f(old) > v:
        ck[key] = f(v)
        rec["changes"].append([key, old, f(v)])


def _export_ok(Q, path, tn):
    import schema as S
    PQ = plan_obj(Q, path)
    _reset_caches(PQ)
    try:
        S.tap_grid(PQ, tn)
        return None
    except Exception as e:  # noqa: BLE001
        return "%s: %s" % (type(e).__name__, str(e)[:200])


def fix_taps(P, Q, tn, cap=CAP_SINKS, radius=RADIUS_UM, max_rounds=10, log=print):
    """classes 1+2 on plan dict Q (P = Plan view of Q, for its path).  Returns record.  Deterministic.

    Sinks are the AUTO-GEOM plan sinks (plan_geom.type_sites): the tap planners' own inventory (taps.sink_sites) plus
    the landing groups, ring local-read flops and reset relays the kit also places.  The two failure classes seen:
      (a) the planner's inventory misses kit flops (landing rings / relays far from every tap: S81 kv_leaf radius,
          QC coll_n clk_t2 690 um) -> density: the uncovered sinks join clock.sink_sites_um (recorded in
          clock.reach_fix_sinks so the check does not count them twice) and the export re-derives the taps;
          explicit / grid+explicit: a tap is added at the weighted L1 median of the uncovered sinks;
      (b) one tap takes the load of a whole dense region (S81 clk_t28 2221-2482 vs t11/t15/t17 < 10) -> density:
          tap_max_sinks <- cap (tap_target_sinks <= 0.8 cap); explicit / grid+explicit: the surplus half of an
          over-cap cluster gets an added tap at its weighted median (legal site: schema.tap_clear strict, off hard
          cores, keepouts and the other taps); the kit split (taps.assign) then re-homes sinks within the radius.
    grid / sinks modes become grid+explicit (the R4 grid is kept, the new taps are clock.added_taps).
    The type's own tap_radius_um / tap_max_sinks are lowered to the target only when the export then still loads."""
    import schema as S
    import taps as TP
    import gen_phys
    t = Q["partition_types"][tn]
    ck = t.setdefault("clock", {})
    mode = ck.get("tap_mode", "grid")
    rec = dict(mode=mode, changes=[])
    if ck.get("native_domains") is not None or ck.get("child_root_taps") is not None:
        rec["skip"] = "native clock domains / child-root taps: taps owned by native_clock_domains / the child roots"
        return rec
    if mode == "density":
        _set_le(ck, "tap_max_sinks", cap, int, rec)
        if ck.get("tap_target_sinks") is not None:
            _set_le(ck, "tap_target_sinks", int(0.8 * cap), int, rec)
        r_old = ck.get("tap_radius_um")
        _set_le(ck, "tap_radius_um", radius, float, rec)
        for rnd in range(8):
            PQ = plan_obj(Q, P.path)
            _reset_caches(PQ)
            try:
                row, A = tap_metrics(PQ, tn, None, cap, radius)
            except Exception as e:  # noqa: BLE001
                # a sink with no legal tap site within the lowered radius (macro / keepout field): the kit radius
                # goes back to the type's own value (the check still reports those sinks against 200 um)
                if "has no legal clock tap within" in str(e) and ck.get("tap_radius_um") != r_old:
                    if r_old is None:
                        ck.pop("tap_radius_um", None)
                    else:
                        ck["tap_radius_um"] = r_old
                    rec["changes"].append(["tap_radius_um", radius, r_old, "no legal site within the target"])
                    continue
                rec["error"] = "density round %d: %s: %s" % (rnd, type(e).__name__, str(e)[:200])
                return rec
            if A is None or (row["c1"] == 0 and row["c2"] == 0):
                break
            if row["c2"]:
                # the kit split still overloads a tap: density_taps targets tap_target_sinks per leaf; step it down
                # (deterministic 10 % steps, floor 0.5 cap) so the leaves split finer
                tgt = int(ck.get("tap_target_sinks") or int(0.8 * float(ck.get("tap_max_sinks", cap))))
                nt = max(int(0.5 * cap), int(tgt * 0.9))
                if row.get("taps_short"):        # die-owner minimum tap count: target = sinks / min taps
                    nt = min(nt, max(1, int(row["sinks"] / MIN_TAPS[tn])))
                if nt < tgt:
                    rec["changes"].append(["tap_target_sinks", tgt, nt])
                    ck["tap_target_sinks"] = nt
            far = [s for s, d, k in zip(A["sinks"], A["dist"], A["kinds"]) if d > radius + 1e-6 and k != "plan"]
            if not far:
                if row["c2"]:
                    continue
                break
            add = [[round(x, 4), round(y, 4), max(1.0, round(w, 3))] for x, y, w in far]
            ck.setdefault("sink_sites_um", []).extend(add)
            ck.setdefault("reach_fix_sinks", []).extend(add)
            rec["changes"].append(["sink_sites_um+", rnd, len(add)])
        return rec
    if mode in ("grid", "grid+sinks", "sinks"):
        ck["tap_mode"] = "grid+explicit"
        ck.setdefault("added_taps", [])
        rec["changes"].append(["tap_mode", mode, "grid+explicit"])
        mode = "grid+explicit"
    if mode not in ("grid+explicit", "explicit"):
        rec["skip"] = "tap_mode %s not handled" % mode
        return rec
    # while taps are added the planner's own validation (cap / radius) must not stop the measurement: open both,
    # then set the target (or restore the type's own value) once the table is final
    own_lim = {k: ck.get(k) for k in ("tap_radius_um", "tap_max_sinks")}
    ck["tap_radius_um"], ck["tap_max_sinks"] = 1e6, 10 ** 9
    mine = set()
    try:
        rec["legal_moves"] = _legalize_tap_table(plan_obj(Q, P.path), tn, ck, mode)
    except Exception as e:  # noqa: BLE001
        rec["legal_moves_error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    for rnd in range(max_rounds):
        PQ = plan_obj(Q, P.path)
        _reset_caches(PQ)
        try:
            row, A = tap_metrics(PQ, tn, None, cap, radius)
        except Exception as e:  # noqa: BLE001
            rec["error"] = "round %d: %s: %s" % (rnd, type(e).__name__, str(e)[:200])
            break
        if A is None or (row["c1"] == 0 and row["c2"] == 0):
            break
        grid, sinks, own, load, dist = A["grid"], A["sinks"], A["own"], A["load"], A["dist"]
        all_xy = [(x, y) for _, x, y in grid]
        core = [(x, y) for _, x, y, _ in S.core_taps(PQ, tn)]
        try:
            axes = gen_phys.clock_legal_axes(PQ, tn)
        except Exception:  # noqa: BLE001
            axes = None
        snap = lambda x, y: gen_phys._snap_tap(PQ, x, y, pg_legal=True)  # noqa: E731
        new = []
        tgt = SPLIT_FRAC * cap
        if row.get("taps_short"):
            tgt = min(tgt, max(1.0, sum(s[2] for s in sinks) / MIN_TAPS[tn]))
        bad = sorted({j for j, v in enumerate(load) if v > cap + 1e-6} |
                     ({j for j, v in enumerate(load) if v > tgt + 1e-6} if row.get("taps_short") else set()) |
                     {own[i] for i, d in enumerate(dist) if d > radius + 1e-6},
                     key=lambda j: (-load[j], j))
        for j in bad:
            cl = [(s, d) for s, o, d in zip(sinks, own, dist) if o == j]
            far = [s for s, d in cl if d > radius + 1e-6]
            if far:
                # radius-bounded groups (greedy k-centre, farthest first): one tap per group, so a spread of
                # uncovered sinks gets as many taps as its geometry needs, never one tap at their median
                rem = sorted(far, key=lambda p: (-_d(p, (grid[j][1], grid[j][2])), p[0], p[1]))
                while rem:
                    seed = rem[0]
                    grp = [p for p in rem if _d(p, seed) <= radius] or [seed]
                    gp = [p if p[2] > 0 else (p[0], p[1], 1.0) for p in grp]
                    cx, cy = TP._wmedian(gp, 0), TP._wmedian(gp, 1)
                    took = [p for p in rem if _d(p, (cx, cy)) <= 0.95 * radius] or [seed]
                    rem = [p for p in rem if p not in took]
                    try:
                        q = S.tap_clear(t, cx, cy, core + all_xy + new, strict=True, pin_snap=snap, legal_axes=axes)
                    except Exception:  # noqa: BLE001
                        continue
                    q = (round(q[0], 4), round(q[1], 4))
                    if q not in all_xy and q not in new:
                        new.append(q)
                continue
            # density-weighted re-site (REACH-FIX-2, X-TIER-OTC tap_split fold-in): the over-cap tap's own sinks split
            # into k = ceil(load / target) weighted k-medians groups; the group nearest the tap keeps it, every other
            # group gets a tap at its weighted median (legal site: schema.tap_clear strict)
            pts = [s for s, _d_ in cl]
            k = max(2, int(math.ceil(load[j] / tgt - 1e-9)))
            cen, groups = _wkmedians(pts, k)
            keep = min(range(len(cen)), key=lambda c: (_d(cen[c], (grid[j][1], grid[j][2])), c))
            for c, (x, y) in enumerate(cen):
                if c == keep or not groups[c]:
                    continue
                try:
                    q = S.tap_clear(t, x, y, core + all_xy + new, strict=True, pin_snap=snap, legal_axes=axes)
                except Exception:  # noqa: BLE001
                    continue
                q = (round(q[0], 4), round(q[1], 4))
                if q in all_xy or q in new:
                    continue
                new.append(q)
        if not new:
            rec["unfixed"] = dict(c1=row["c1"], c2=row["c2"], reason="no legal tap site reduces the debt")
            break
        # the kit flops the planner does not list (landing rings, relays) join its inventory, so the planner's own
        # validation (taps.explicit_taps / grid_explicit_taps: no empty tap, radius) sees what the new tap is for
        farx = [s for s, d, k in zip(sinks, dist, A["kinds"]) if d > radius + 1e-6 and k != "plan"]
        if farx:
            add = [[round(x, 4), round(y, 4), max(1.0, round(w, 3))] for x, y, w in farx]
            ck.setdefault("sink_sites_um", []).extend(add)
            ck.setdefault("reach_fix_sinks", []).extend(add)
            rec["changes"].append(["sink_sites_um+", rnd, len(add)])
        if mode == "explicit":
            tbl = ck.setdefault("taps", [])
            nloc = sum(1 for p in tbl if p.get("kind") != "core")
            for q in new:
                tbl.append(dict(name="clk_t%d" % nloc, xy=list(q)))
                nloc += 1
        else:
            tbl = ck.setdefault("added_taps", [])
            n0 = len(S._grid_taps(PQ, tn))
            for q in new:
                tbl.append(dict(name="clk_t%d" % (n0 + len(tbl)), xy=list(q)))
        mine.update((float(q[0]), float(q[1])) for q in new)   # schema: tap rows carry name/xy only; track ours here
        rec["changes"].append(["added_taps", rnd, [list(q) for q in new]])
        # the export validator (taps.explicit_tap_sites / grid_explicit_taps) checks outline / halo-grown boxes /
        # keepouts / spacing to the taps before it in table order: move our new taps the same way (a pin snap can
        # push a tap_clear site back into a halo); a tap with no legal site is dropped below
        try:
            mv = _legalize_tap_table(plan_obj(Q, P.path), tn, ck, mode)
        except Exception:  # noqa: BLE001
            mv = []
        for _n, old, nw in mv:
            if (float(old[0]), float(old[1])) in mine:
                mine.add((float(nw[0]), float(nw[1])))
        if mv:
            rec["changes"].append(["legal_moves", rnd, mv])
        for _k in range(len(new) + len(mv)):
            err = _export_ok(Q, P.path, tn)
            m = (re.search(r"tap (clk_t\d+) load=0/.*empty=True", err or "")
                 or re.search(r"tap (clk_t\d+) violates outline/halo/tap spacing", err or ""))
            if not m:
                break
            drop = m.group(1)
            if mode == "explicit":
                rows_ = ck["taps"]
            else:
                rows_ = ck["added_taps"]
            idx = next((i for i, r in enumerate(rows_) if r.get("name") == drop
                        and (float(r["xy"][0]), float(r["xy"][1])) in mine), None)
            if idx is None:
                break
            rows_.pop(idx)
            n = 0
            for r in rows_:                      # keep the canonical contiguous names
                if mode == "explicit" and r.get("kind") == "core":
                    continue
                if mode == "explicit":
                    r["name"] = "clk" if n == 0 else "clk_t%d" % n
                n += 1
            if mode != "explicit":
                n0 = len(S._grid_taps(plan_obj(Q, P.path), tn))
                for i, r in enumerate(rows_):
                    r["name"] = "clk_t%d" % (n0 + i)
            rec["changes"].append(["dropped_empty_tap", rnd, drop])
    # the type's own kit radius / cap follow the target when the export still loads with them
    for key in own_lim:
        if own_lim[key] is None:
            ck.pop(key, None)
        else:
            ck[key] = own_lim[key]
    for key, v, f in (("tap_radius_um", radius, float), ("tap_max_sinks", cap, int)):
        old = ck.get(key)
        if old is not None and f(old) <= v:
            continue
        ck[key] = f(v)
        err = _export_ok(Q, P.path, tn)
        if err:
            if old is None:
                ck.pop(key)
            else:
                ck[key] = old
            rec.setdefault("kept", []).append([key, old, err[:160]])
        else:
            rec["changes"].append([key, old, f(v)])
    # the sinks this tool added to the inventory can push one tap past the type's OWN cap / radius (a value above the
    # 800 / 200 targets): raise that limit to the measured value so the export loads; the check still reports the tap
    # against the targets (no hidden debt), and the kit split keeps its own cap
    for _k in range(64):
        err = _export_ok(Q, P.path, tn) or ""
        m = re.search(r"tap clk_t?\d* ?load=([0-9.]+)/([0-9.]+), radius=([0-9.]+)/([0-9.]+)", err)
        if not m:
            break
        ld, lc, rd, rc = map(float, m.groups())
        if ld > lc:
            ck["tap_max_sinks"] = int(math.ceil(ld))
            rec.setdefault("raised", []).append(["tap_max_sinks", lc, ck["tap_max_sinks"]])
        elif rd > rc:
            ck["tap_radius_um"] = round(math.ceil(rd * 10) / 10.0, 1)
            rec.setdefault("raised", []).append(["tap_radius_um", rc, ck["tap_radius_um"]])
        else:
            break
    return rec


def _legalize_tap_table(PQ, tn, ck, mode):
    """street_rule._tap_legalize_table on the stored taps: every tap on a hard core / keepout / outline margin or
    closer than TAP_CLEAR to another tap moves to the nearest legal site (taps on macros, stacked taps)."""
    import schema as S
    import street_rule as SR
    if mode == "explicit":
        tbl = [p for p in ck.get("taps") or [] if p.get("kind") != "core"]
        clear = S.TAP_CLEAR_UM
        ko = [(a - clear, b - clear, c + clear, d + clear) for a, b, c, d in ck.get("keepouts_um", [])]
        return SR._tap_legalize_table(PQ, tn, tbl, [(x, y) for _, x, y, _ in S.core_taps(PQ, tn)], ko)
    tbl = ck.get("added_taps") or []
    if not tbl:
        return []
    return SR._tap_legalize_table(PQ, tn, tbl, [(x, y) for _, x, y in S._grid_taps(PQ, tn)])


def _reset_caches(PQ):
    import taps as TP
    TP._CACHE.clear()
    TP._clear_density_cache()
    try:
        import added_tap_recentre as ATR
        ATR.S_reset_cache(PQ)
    except Exception:  # noqa: BLE001
        pass


class _Ras:
    """street_rule.add_ft_regs / add_station_regs input: the raster of the type's hard cores."""

    def __init__(self, t):
        import street_rule as SR
        import hub_repack as HR
        W, H = t["outline_um"]
        self.R = HR.Raster(W, H, [tuple(r) for r in SR._core_rects(t)])


def fix_hops(t, reach=REACH_UM, add_max=4, ends=None):
    """class 4: +k registers on every ft / station hop > reach (owner-approved lever 1, cycles reported)."""
    import street_rule as SR
    import hub_repack as HR
    ras = _Ras(t)
    rec = dict(ft=[], stations=[], ft_even=[], unfixed=[])
    reg_form = False
    for f in t.get("ft_slots") or []:
        hops, form = ft_slot_hops(t, f, ends)
        if max(hops) <= reach + 0.01:
            continue
        if form == "even":
            # kit places stations 1..k-1 at L*j/k on the route: k' = ceil(L / reach) stations bring every hop <= reach
            k0 = max(1, int(f.get("stations", 1) or 1))
            L = sum(hops)
            k1 = int(math.ceil(L / reach - 1e-9))
            if k1 - k0 > add_max:
                rec["unfixed"].append(dict(slot=f.get("name"), len_um=round(L, 1), need=k1 - k0))
                continue
            f["stations"] = k1
            rec["ft_even"].append(dict(name=f.get("name"), len_um=round(L, 1), stations_before=k0, stations_after=k1,
                                       added=k1 - k0))
        elif form == "regs":
            reg_form = True
        else:
            rec["unfixed"].append(dict(slot=f.get("name"), form=form, max_hop_um=round(max(hops), 1),
                                       reason="per-bit station sites without regs_um: re-site with ft_reach_fix"))
    if reg_form:
        # regs_um slots: base hops = 0 so every hop > reach is split (street_rule only splits hops a move stretched)
        t0 = copy.deepcopy(t)
        for f in t0.get("ft_slots") or []:
            f["regs_um"] = []
        idx = {k: ends[f.get("name")] for k, f in enumerate(t.get("ft_slots") or []) if ends and f.get("name") in ends}
        rec["ft"] = SR.add_ft_regs(None, t0, t, reach, add_max, raster=ras.R, use_base=False, ends=idx)
    for si, s in enumerate(t.get("internal_stations") or []):
        if not s.get("from_um") or not s.get("to_um"):
            continue
        regs = [tuple(r[:2]) for r in s.get("regs_um") or []]
        ch = [tuple(s["from_um"][:2])] + regs + [tuple(s["to_um"][:2])]
        if max(_d(a, b) for a, b in zip(ch, ch[1:])) <= reach + 0.01:
            continue
        rec["stations"] += SR.add_station_regs(None, t, [si], reach, add_max, raster=ras.R)
    rec["cycles_added"] = sum(r.get("added", 0) for r in rec["ft"] + rec["ft_even"]) + sum(
        r["regs_after"] - r["regs_before"] for r in rec["stations"])
    return rec


def fix_fwd(P, Q, tn, span=REPEATER_UM):
    """class 3: every fclk_in_* port whose farthest band flop is > span joins clock.edge_split_ports (kit repeater
    chain every 200 um + per-group roots, clock_edge_split.tcl).  Returns the ports added."""
    ck = Q["partition_types"][tn].setdefault("clock", {})
    lst = ck.setdefault("edge_split_ports", [])
    out = []
    for r in fwd_metrics(P, tn, None, span):
        if not r["ok"] and r["port"] not in lst:
            lst.append(r["port"])
            out.append(dict(port=r["port"], far_um=r["far_um"]))
    if not lst:
        ck.pop("edge_split_ports")
    return out


def fix_edge(P, Q, tn):
    """class 2 edge clocks: the unsplit plain edge ports join clock.edge_split_ports (the kit splits a port only when
    it has more than one group, so a small domain is left alone)."""
    ports = edge_unsplit(P, tn)
    if ports:
        lst = Q["partition_types"][tn].setdefault("clock", {}).setdefault("edge_split_ports", [])
        lst += [p for p in ports if p not in lst]
    return ports


def fix_reset_local_taps(Q, tn, plan_path):
    """a reset.local_taps_um terminal that now coincides with a clock tap is served by that tap's own leaf relay
    (reset_tree.consumer_taps refuses the duplicate): drop it.  Returns the dropped points."""
    import schema as S
    t = Q["partition_types"][tn]
    lt = (t.get("reset") or {}).get("local_taps_um")
    if not lt:
        return []
    PQ = plan_obj(Q, plan_path)
    _reset_caches(PQ)
    try:
        taps = [(x, y) for _n, x, y in S.tap_grid(PQ, tn)]
    except Exception:  # noqa: BLE001
        return []
    keep, drop = [], []
    for xy in lt:
        x, y = map(float, xy)
        (drop if any(abs(x - a) < 1e-6 and abs(y - b) < 1e-6 for a, b in taps) else keep).append(xy)
    if drop:
        t["reset"]["local_taps_um"] = keep
    return drop


def fix_raw_tap_refs(P, Q, tn, plan_path, reach=REACH_UM):
    """raw START references to a tap's raw copy (rr_t<k>) after the taps changed: street_rule.reset_resel re-selects
    only rst_rl_* / rst_n_t* nets.  A landing reader/writer START stage or local reset whose rr_t<k> no longer exists
    or lies > reach from it takes rr_t<j> of the nearest consumer tap leaf rst_n_t<j> of the SAME depth (same release
    cycle).  Returns [[tag, old, new]]."""
    import reset_tree as RT
    t = Q["partition_types"][tn]
    ck = t.get("clock") or {}
    PQ = plan_obj(Q, plan_path)
    _reset_caches(PQ)
    try:
        TA, TB = RT.for_type(P, tn), RT.for_type(PQ, tn)
    except Exception:  # noqa: BLE001
        return []
    leaf = re.compile(r"rst_n_t(\d+)$")
    # ROLE (COORD 11-12, HEAD-94 hd_st_n3_transit.u2_i picked the gated rst_n_t1 for a raw rst_rl_*): a re-select keeps
    # role AND depth (street_rule._q_roles: gated rst_n_t<i>, raw rst_rl_*, raw copy rr_t<i> of a gated leaf); no
    # same-role relay -> the reference is left as is and reported
    import street_rule as SR
    try:
        rolb = {q: r.get("role") for q, r in SR._q_roles(TB).items()}
    except Exception:  # noqa: BLE001
        rolb = {}
    role = lambda q: rolb.get(q, "raw" if not TB.get("start") else None)  # noqa: E731
    da = {"rr_t" + leaf.match(r["q"]).group(1): r for r in TA.get("relays", []) if leaf.match(r["q"])}
    cand = [r for r in TB.get("relays", []) if leaf.match(r["q"])
            and (not TB.get("start") or role(r["q"]) == "gated")]      # rr_t<j> exists only for a gated leaf
    newq = {"rr_t" + leaf.match(r["q"]).group(1): r for r in cand}
    refs = []
    for key in ("landing_reader_start", "landing_writer_start"):
        for bus, br in ((ck.get(key) or {}).get("branches") or {}).items():
            for i, st in enumerate(br.get("stages", [])):
                refs.append(("%s.%s.%d" % (key, bus, i), st, "raw_reset"))
    for i, lr in enumerate(ck.get("landing_local_resets") or []):
        refs.append(("landing_local_resets.%d" % i, lr, "raw"))
    out = []
    for tag, obj, fld in refs:
        q = obj.get(fld)
        pt = obj.get("xy_um")
        if isinstance(q, str) and not q.startswith("rr_t") and pt is not None:
            # a relay net (rst_rl_* / rst_n_t*) still > reach after street_rule.reset_resel: nearest same-depth relay
            o = next((r for r in TB.get("relays", []) if r["q"] == q), None)
            if o is None or _d(o["xy"], pt) <= reach:
                continue
            c = [r for r in TB.get("relays", []) if r.get("depth") == o.get("depth") and role(r["q"]) == role(q)]
            if not c:
                out.append([tag, q, None, "no same-role relay at depth %s" % o.get("depth")])
                continue
            n = min(c, key=lambda r: (_d(r["xy"], pt), r["q"]))
            if n["q"] != q and _d(n["xy"], pt) < _d(o["xy"], pt):
                obj[fld] = n["q"]
                out.append([tag, q, n["q"]])
            continue
        if not (isinstance(q, str) and q.startswith("rr_t")):
            continue
        cur = newq.get(q)
        old = da.get(q)
        if pt is None or old is None:
            continue
        if cur is not None and cur.get("depth") == old.get("depth") and _d(cur["xy"], pt) <= reach:
            continue
        c = [r for r in cand if r.get("depth") == old.get("depth")]
        if not c:
            continue
        n = min(c, key=lambda r: (_d(r["xy"], pt), r["q"]))
        nq = "rr_t" + leaf.match(n["q"]).group(1)
        if nq != q:
            obj[fld] = nq
            out.append([tag, q, nq])
    return out


def fix_type(P, Q, tn, classes, base_row, cap, radius, reach, span, plan_path):
    """apply the stages to type tn of plan dict Q in place (Q holds a deep copy of the base type).  Returns record."""
    rec = dict(type=tn)
    t = Q["partition_types"][tn]
    if "4" in classes and base_row.get("c4"):
        rec["hops"] = fix_hops(t, reach, ends=slot_ends(P, tn))
    if ("1" in classes or "2" in classes) and (base_row.get("c1") or base_row.get("c2_tap", base_row.get("c2"))):
        rec["taps"] = fix_taps(P, Q, tn, cap, radius)
        if base_row.get("edge_unsplit"):
            rec["edge_split"] = fix_edge(P, Q, tn)
        rl = fix_reset_local_taps(Q, tn, plan_path)
        if rl:
            rec["reset_local_taps"] = rl
    if "5" in classes:
        import street_rule as SR
        rs = SR.reset_resel(P.raw, Q, [tn], plan_path)
        if rs.get(tn) and (rs[tn].get("exports") or rs[tn].get("raw") or rs[tn].get("error")):
            rec["reset_resel"] = rs[tn]
        rr = fix_raw_tap_refs(P, Q, tn, plan_path)
        if rr:
            rec["raw_tap_resel"] = rr
    if "3" in classes and base_row.get("c3"):
        rec["fwd"] = fix_fwd(plan_obj(Q, plan_path), Q, tn, span)
    return rec


def landed_rows(raw, tsv, window=LANDED_WINDOW_PS):
    """class 6 landed_window (die level, S81 ready12b): a landed crossing launch_part -> capture_part whose clock damage
    exceeds the landing window by over_ps (reach_hops TSV of DIE-RECHECK-1 / DIE-S81-87 / the die STA residue after the
    balanced die clock) takes k = ceil(over_ps / window) more cycles on every plan lane carrying that part pair
    (owner-approved +1 register per over-reach hop).  Lever: lanes[].fixed_cycles = latency.lanes[id].cycles + k (the
    composer pads the lane with k registers).  Returns one row per lane."""
    import csv
    with open(tsv) as fh:
        hops = list(csv.DictReader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"))
    ports = {p["id"]: p for p in raw.get("ports") or []}
    by = defaultdict(set)
    for ln in raw.get("lanes") or []:
        for pid in ln.get("ports") or []:
            p = ports.get(pid)
            if p:
                by[((p.get("src") or {}).get("part"), (p.get("dst") or {}).get("part"))].add(ln["id"])
    need = {}
    for h in hops:
        over = float(h.get("over_ps") or 0.0)
        if over <= 0:
            continue
        k = int(math.ceil(over / window - 1e-9))
        for lid in by.get((h.get("launch_part"), h.get("capture_part"))) or [None]:
            key = lid or "%s->%s" % (h.get("launch_part"), h.get("capture_part"))
            o = need.setdefault(key, dict(lane=lid, k=0, over_ps=0.0, hops=[]))
            o["k"] = max(o["k"], k)
            o["over_ps"] = max(o["over_ps"], over)
            o["hops"].append(h.get("lane_tag") or key)
    lat = (raw.get("latency") or {}).get("lanes") or {}
    lanes = {ln["id"]: ln for ln in raw.get("lanes") or []}
    out = []
    for key in sorted(need):
        o = need[key]
        lid = o["lane"]
        if lid is None:
            out.append(dict(o, ok=False, reason="no plan lane carries this part pair"))
            continue
        cyc = (lat.get(lid) or {}).get("cycles")
        fx = lanes[lid].get("fixed_cycles")
        if cyc is None:
            out.append(dict(o, fixed_before=fx, ok=False, reason="no latency.lanes cycles"))
            continue
        tgt = int(cyc) + o["k"]
        out.append(dict(o, cycles_before=int(cyc), fixed_before=fx, target=tgt, ok=fx is not None and int(fx) >= tgt))
    return out


def fix_landed(Q, rows):
    """apply class 6 to plan dict Q: lanes[].fixed_cycles = target.  Idempotent (target is computed from
    latency.lanes, which the fix does not touch).  Returns {lane: [before, after]}."""
    lanes = {ln["id"]: ln for ln in Q.get("lanes") or []}
    done = {}
    for r in rows:
        if r.get("ok") or r.get("target") is None or r.get("lane") not in lanes:
            continue
        ln = lanes[r["lane"]]
        done[r["lane"]] = [ln.get("fixed_cycles"), r["target"]]
        ln["fixed_cycles"] = r["target"]
    return done


# ------------------------------------------------------------------------------------------------------- driver
_JOB = {}


def _row_job(tn):
    P = _JOB["P"]
    a = _JOB["a"]
    _reset_caches(P)
    try:
        return type_row(P, tn, a.cap, a.radius, a.reach, a.span)
    except Exception as e:  # noqa: BLE001
        return dict(type=tn, error="%s: %s" % (type(e).__name__, str(e)[:200]), viol=-1)


def _fix_job(tn):
    P, raw, a, base = _JOB["P"], _JOB["raw"], _JOB["a"], _JOB["base"]
    import io
    import contextlib
    Q = dict(raw)
    Q["partition_types"] = dict(raw["partition_types"])
    Q["partition_types"][tn] = copy.deepcopy(raw["partition_types"][tn])
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rec = fix_type(P, Q, tn, set(a.classes.split(",")), base[tn], a.cap, a.radius, a.reach, a.span, P.path)
            PQ = plan_obj(Q, P.path)
            _reset_caches(PQ)
            after = type_row(PQ, tn, a.cap, a.radius, a.reach, a.span)
    except Exception as e:  # noqa: BLE001
        return tn, dict(type=tn, error="%s: %s" % (type(e).__name__, str(e)[:300])), None, None
    return tn, rec, after, Q["partition_types"][tn]


def _pool(fn, items, jobs):
    if jobs <= 1 or len(items) <= 1:
        return [fn(x) for x in items]
    import multiprocessing as mp
    with mp.get_context("fork").Pool(jobs) as pool:
        return pool.map(fn, items, chunksize=1)


def summarize(rows):
    s = dict(types=len(rows), types_viol=sum(1 for r in rows if any(r.get("c" + c) for c in CLASSES)))
    for c in CLASSES:
        s["c" + c + "_types"] = sum(1 for r in rows if r.get("c" + c))
    s["errors"] = sum(1 for r in rows if r.get("error"))
    return s


def tsv_line(r, tag=""):
    return "\t".join(str(x) for x in (
        tag, r["type"], r.get("tap_mode", ""), r.get("taps", ""),
        "%s/%s" % (r.get("c1", ""), r.get("c1_max_um", "")), "%s/%s" % (r.get("c2", ""), r.get("c2_max", "")),
        "%s/%s" % (r.get("c3", ""), r.get("c3_max_um", "")), "%s/%s" % (r.get("c4", ""), r.get("c4_max_um", "")),
        "%s/%s/%s" % (r.get("c5", ""), (r.get("reset") or {}).get("hop_max_um", ""), (r.get("reset") or {}).get("raw_bad", "")),
        (r.get("error") or "")[:120]))


TSV_HEAD = "tag\ttype\ttap_mode\ttaps\tc1 n/max_um\tc2 n/max_sinks\tc3 n/max_um\tc4 n/max_um\tc5 n/hop_max/raw_bad\terror"


def _setup(a, P):
    """per-die cap, measured sinks, minimum tap counts, tap table flag (globals; the fork pool inherits them)."""
    global TAP_TABLE
    a.cap = die_cap(P.name, a.cap)
    MIN_TAPS.clear()
    MEASURED.clear()
    for s in a.min_taps or []:
        tn, n = s.split("=", 1)
        MIN_TAPS[tn] = int(n)
    outl = {tn: P.types[tn].get("outline_um") for tn in P.types}
    m, bad = load_measured(a.sinks_dir, a.sinks, outl)
    MEASURED.update(m)
    TAP_TABLE = bool(getattr(a, "tap_table", None))
    return dict(cap=a.cap, cap_source="--cap" if a.cap_given else "DIE_CAP[%s]" % P.name,
                measured=sorted(m), measured_refused=bad, min_taps=dict(MIN_TAPS),
                landed_hops=getattr(a, "landed_hops", None), landed_window_ps=a.landed_window)


def _landed_summary(lr):
    return dict(c6_lanes=sum(1 for r in lr if not r.get("ok")),
                c6_unmapped=sum(1 for r in lr if r.get("lane") is None or r.get("target") is None),
                c6_cycles=sum(r["k"] for r in lr if not r.get("ok") and r.get("target") is not None))


def write_tap_table(path, rows, cap, radius):
    head = "type\ttap\tx_um\ty_um\tsinks\tmax_tap_to_sink_um\tover_cap\tover_radius\tsink_source"
    out = [head]
    for r in rows:
        for n, x, y, ld, far in r.get("tap_rows") or []:
            out.append("\t".join(str(v) for v in (r["type"], n, x, y, ld, far, int(ld > cap + 1e-6),
                                                   int(far > radius + 1e-6), r.get("sink_source", ""))))
    Path(path).write_text("\n".join(out) + "\n")


def cmd_check(a):
    set_repo(a.repo)
    raw, sha = load_raw(a.plan)
    P = plan_obj(raw, a.plan)
    inputs = _setup(a, P)
    names = soft_types(P, a.types)
    _JOB.update(P=P, a=a)
    rows = _pool(_row_job, names, a.jobs)
    rec = dict(schema=SCHEMA, mode="check", plan=str(a.plan), plan_sha256=sha, die=P.name, inputs=inputs,
               limits=dict(radius_um=a.radius, cap_sinks=a.cap, cap_basis=CAP_BASIS, reach_um=a.reach,
                           repeater_um=a.span), summary=summarize(rows), rows=rows)
    if a.landed_hops:
        rec["landed"] = landed_rows(raw, a.landed_hops, a.landed_window)
        rec["summary"].update(_landed_summary(rec["landed"]))
    if a.tap_table:
        write_tap_table(a.tap_table, rows, a.cap, a.radius)
        for r in rows:
            r.pop("tap_rows", None)
    if a.json:
        Path(a.json).write_text(json.dumps(rec, indent=1, default=str) + "\n")
    lines = [TSV_HEAD] + [tsv_line(r, "base") for r in rows]
    if a.tsv:
        Path(a.tsv).write_text("\n".join(lines) + "\n")
    print(json.dumps(dict(die=P.name, plan_sha256=sha[:12], **rec["summary"])))
    return 0


def cmd_fix(a):
    set_repo(a.repo)
    raw, sha = load_raw(a.plan)
    P = plan_obj(raw, a.plan)
    inputs = _setup(a, P)
    names = soft_types(P, a.types)
    _JOB.update(P=P, a=a, raw=raw)
    base_rows = _pool(_row_job, names, a.jobs)
    base = {r["type"]: r for r in base_rows}
    todo = [r["type"] for r in base_rows if r.get("viol")]
    _JOB["base"] = base
    res = _pool(_fix_job, todo, a.jobs)
    lr = landed_rows(raw, a.landed_hops, a.landed_window) if a.landed_hops and "6" in a.classes.split(",") else []
    Q = copy.deepcopy(raw) if (res or any(not r.get("ok") and r.get("target") is not None for r in lr)) else raw
    landed_done = fix_landed(Q, lr) if lr else {}
    rows = []
    for tn, rec, after, tnew in res:
        b = base[tn]
        worse = []
        if after is not None:
            for c in CLASSES:
                if (after.get("c" + c) or 0) > (b.get("c" + c) or 0):
                    worse.append("c" + c)
            if after.get("error") and not b.get("error"):
                worse.append("error")
        ok = after is not None and not worse and tnew is not None and tnew != raw["partition_types"][tn]
        if ok:
            Q["partition_types"][tn] = tnew
        rows.append(dict(type=tn, applied=ok, worse=worse, fix=rec, before={k: b.get(k) for k in (
            "c1", "c2", "c3", "c4", "c5", "c1_max_um", "c2_max", "c3_max_um", "c4_max_um")},
            after=None if after is None else {k: after.get(k) for k in (
                "c1", "c2", "c3", "c4", "c5", "c1_max_um", "c2_max", "c3_max_um", "c4_max_um", "error")},
            reset_after=None if after is None else ((after.get("reset") or {}).get("raw_detail") or [])
            + ([after["reset"]["error"]] if (after.get("reset") or {}).get("error") else []),
            reset_hop_after=None if after is None else (after.get("reset") or {}).get("hop_max_um")))
    after_rows = []
    for r in base_rows:
        x = next((y for y in rows if y["type"] == r["type"]), None)
        if x and x["applied"]:
            after_rows.append(dict(r, **{k: v for k, v in (x["after"] or {}).items()}))
        else:
            after_rows.append(r)
    out_txt = json.dumps(Q, indent=1, sort_keys=False) + "\n"
    new_sha = hashlib.sha256(out_txt.encode()).hexdigest() if Q is not raw else sha
    if a.out_plan:
        Path(a.out_plan).write_text(out_txt)
    ev = dict(schema=SCHEMA, mode="fix", base_plan=str(a.plan), base_sha256=sha, out_plan=a.out_plan,
              out_sha256=new_sha, die=P.name, classes=a.classes, inputs=inputs,
              limits=dict(radius_um=a.radius, cap_sinks=a.cap, cap_basis=CAP_BASIS, reach_um=a.reach, repeater_um=a.span),
              summary_before=summarize(base_rows), summary_after=summarize(after_rows),
              landed=dict(rows=lr, applied=landed_done, before=_landed_summary(lr),
                          after=_landed_summary([dict(r, ok=r.get("ok") or r.get("lane") in landed_done) for r in lr]))
              if lr else None,
              applied=sum(1 for r in rows if r["applied"]), rows=rows,
              cycles_added={r["type"]: r["fix"].get("hops", {}).get("cycles_added") for r in rows
                            if r["applied"] and (r["fix"].get("hops") or {}).get("cycles_added")})
    if a.event:
        Path(a.event).write_text(json.dumps(ev, indent=1, default=str) + "\n")
    if a.tsv:
        Path(a.tsv).write_text("\n".join([TSV_HEAD] + [tsv_line(r, "before") for r in base_rows]
                                         + [tsv_line(r, "after") for r in after_rows]) + "\n")
    print(json.dumps(dict(die=P.name, base=sha[:12], out=new_sha[:12], applied=ev["applied"], cap=a.cap,
                          measured=len(MEASURED), before=ev["summary_before"], after=ev["summary_after"],
                          landed_lanes=len(landed_done))))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "fix"):
        p = sub.add_parser(name)
        p.add_argument("plan")
        p.add_argument("--repo", default=None)
        p.add_argument("--types", default=None, help="regex of type names")
        p.add_argument("--json")
        p.add_argument("--tsv")
        p.add_argument("-j", "--jobs", type=int, default=1)
        p.add_argument("--cap", type=int, default=None, help="sinks per tap (default per die: %s)" % DIE_CAP)
        p.add_argument("--radius", type=float, default=RADIUS_UM)
        p.add_argument("--reach", type=float, default=REACH_UM)
        p.add_argument("--span", type=float, default=REPEATER_UM)
        p.add_argument("--sinks-dir", action="append", default=[], help="dir of <type>.json placed sinks")
        p.add_argument("--sinks", action="append", default=[], help="TYPE=placed sinks JSON [[x, y], ...]")
        p.add_argument("--min-taps", action="append", default=[], help="TYPE=N minimum tap count")
        p.add_argument("--landed-hops", default=None, help="reach_hops TSV (class 6, landed window)")
        p.add_argument("--landed-window", type=float, default=LANDED_WINDOW_PS)
        if name == "check":
            p.add_argument("--tap-table", default=None, help="TSV: one row per tap (sinks, max tap-to-sink um)")
        if name == "fix":
            p.add_argument("--out-plan")
            p.add_argument("--event")
            p.add_argument("--classes", default="1,2,3,4,5,6")
    a = ap.parse_args(argv)
    a.cap_given = a.cap is not None
    if a.cmd == "fix":
        a.tap_table = None
    return cmd_check(a) if a.cmd == "check" else cmd_fix(a)


if __name__ == "__main__":
    sys.exit(main())
