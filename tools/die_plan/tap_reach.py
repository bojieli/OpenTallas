#!/usr/bin/env python3
"""tap_reach.py -- PRE class TAPREACH (class C-TAP-REACH, QC-INT-R2-TOOLS 11-26, COORD FABLE-FLOW-0847 item 2).

Class: a plan seats FIRM flops (relay sites, station registers, collector / landing relays, reset-tree relays, clock sink seats) farther
from every clock tap of its type than clock.tap_radius_um.  The kit's tap assignment (taps.assign) reaches a sink only within the radius, so
such a seat times against a tap 200+ um away or forces an extra tap late.  QC cA4 coll_ft d229e02da578: the east relay column x=655
(collector_tree relays y 8 / 231 / 454 / 676) had 40 clock flops over 220 um from the nearest tap and 5 over 300; S81 t23 c985 8 of 24
taps over a 300 um span, HEAD hd_spn 26 of 42.

Rule (static, plan only, seconds): for every non-hard type with a tap set, every FIRM seat lies within clock.tap_radius_um (default 200,
Manhattan like taps.assign) of SOME tap of the type.  Taps = schema.tap_grid (every tap mode: density grid + added taps, explicit,
grid+explicit); core taps (clk_c*) serve core clock pins and are not flop taps.  When the grid cannot be solved (tap_offset_cover.type_ports
returns a reason) an explicit-mode type falls back to clock.taps, any other mode is listed UNCHECKED.

Seats (category): relay site (type relay_sites values), station reg (internal_stations / ft_slots regs_um), clock sink site (clock.sink_sites_um,
reach_fix_sinks), collector relay (landing_contract.collector_tree.relays, collector_children, collector_local_sources xy_um), landing reset
(clock.landing_local_resets xy_um), reset anchor relay (clock.reset_tree_anchor.relays).

    python3 -I tools/die_plan/tap_reach.py census PLAN [--types REGEX] [--tsv OUT] [--list N]
PRE: WARN TAPREACH <type> lines (FAIL when $OT_PRE_TAPREACH_BLOCK=1) + LIST TAPREACH die summary.  --skip TAPREACH.
Fix (tap generator, not here): a sink tap per relay column / seat cluster beyond the radius; CLASS-OWNERS-B owns the generator side.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I drops the script dir
EPS = 1e-6
DEFAULT_RADIUS_UM = 200.0
FAR_FACTOR = 1.5          # second census bucket: over 1.5 x radius (300 um at the default)
LEVEL_ENV = "OT_PRE_TAPREACH_BLOCK"


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _xy(v):
    return isinstance(v, (list, tuple)) and len(v) >= 2 and _num(v[0]) and _num(v[1])


def _pts(o):
    """every [x, y(, w)] leaf of a nested list"""
    if isinstance(o, (list, tuple)):
        if 2 <= len(o) <= 3 and all(_num(v) for v in o):
            yield float(o[0]), float(o[1])
        else:
            for v in o:
                yield from _pts(v)


def seats(t):
    """[(category, name, x, y)] every FIRM flop seat of the type the plan pins"""
    out = []
    ck = t.get("clock") or {}
    for k, v in (t.get("relay_sites") or {}).items():
        if _xy(v):
            out.append(("relay site", k, float(v[0]), float(v[1])))
    for i, s in enumerate(t.get("internal_stations") or []):
        if isinstance(s, dict):
            for j, (x, y) in enumerate(_pts(s.get("regs_um"))):
                out.append(("station reg", f"{s.get('conn', i)}[{j}]", x, y))
    for s in t.get("ft_slots") or []:
        if isinstance(s, dict):
            for j, (x, y) in enumerate(_pts(s.get("regs_um"))):
                out.append(("station reg", f"ft {s.get('name')}[{j}]", x, y))
    for k in ("sink_sites_um", "reach_fix_sinks"):
        for j, (x, y) in enumerate(_pts(ck.get(k))):
            out.append(("clock sink site", f"{k}[{j}]", x, y))
    lc = ck.get("landing_contract") or {}
    for r in (lc.get("collector_tree") or {}).get("relays") or []:
        if isinstance(r, dict) and _xy(r.get("xy")):
            out.append(("collector relay", str(r.get("name")), float(r["xy"][0]), float(r["xy"][1])))
    for k in ("collector_children", "collector_local_sources"):
        for j, r in enumerate(lc.get(k) or []):
            if isinstance(r, dict) and _xy(r.get("xy_um")):
                out.append(("collector relay", str(r.get("name") or r.get("node") or f"{k}[{j}]"), float(r["xy_um"][0]), float(r["xy_um"][1])))
    for j, r in enumerate(ck.get("landing_local_resets") or []):
        if isinstance(r, dict) and _xy(r.get("xy_um")):
            out.append(("landing reset", str(r.get("name") or j), float(r["xy_um"][0]), float(r["xy_um"][1])))
    rel = (ck.get("reset_tree_anchor") or {}).get("relays")
    if isinstance(rel, dict):
        for k, r in rel.items():
            if isinstance(r, dict) and _xy(r.get("xy")):
                out.append(("reset anchor relay", str(k), float(r["xy"][0]), float(r["xy"][1])))
    return out


def raw_explicit_taps(t):
    """[(name, x, y)] the plan's own tap rows of an explicit-mode type (clock.taps minus core taps)"""
    ck = t.get("clock") or {}
    return [(str(p.get("name")), float(p["xy"][0]), float(p["xy"][1])) for p in ck.get("taps") or []
            if isinstance(p, dict) and p.get("kind") != "core" and _xy(p.get("xy"))]


def nearest(points, taps):
    """-> ([manhattan distance to the nearest tap], [tap index]) per point; numpy when present, exact python otherwise"""
    if not points or not taps:
        return [], []
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None:
        P = np.asarray([(p[0], p[1]) for p in points], dtype=float)
        T = np.asarray([(p[1], p[2]) for p in taps], dtype=float)
        dist = np.empty(len(P))
        idx = np.empty(len(P), dtype=int)
        step = max(1, 4_000_000 // max(1, len(T)))
        for a in range(0, len(P), step):
            d = np.abs(P[a:a + step, None, 0] - T[None, :, 0]) + np.abs(P[a:a + step, None, 1] - T[None, :, 1])
            idx[a:a + step] = d.argmin(axis=1)
            dist[a:a + step] = d[np.arange(len(d)), idx[a:a + step]]
        return dist.tolist(), idx.tolist()
    dist, idx = [], []
    for x, y in points:
        j = min(range(len(taps)), key=lambda k: (abs(x - taps[k][1]) + abs(y - taps[k][2]), k))
        dist.append(abs(x - taps[j][1]) + abs(y - taps[j][2]))
        idx.append(j)
    return dist, idx


def seat_owner(cat, name):
    """tap_group owner key of a plan seat: landing reset 'k7' -> u_cland_lrst_k7, relay site 'u_rrl_15/q' -> u_rrl_15"""
    return "u_cland_lrst_" + str(name) if cat == "landing reset" else str(name).split("/")[0]


def type_reach(t, taps, radius=None):
    """-> dict(radius, taps, seats, over, far, worst, by_cat {cat: (n, over, worst)}, offenders [(d, cat, name, x, y, tap)] worst first) or None (no taps / no seats)"""
    ss = seats(t)
    if not ss or not taps:
        return None
    r = float(radius if radius is not None else (t.get("clock") or {}).get("tap_radius_um") or DEFAULT_RADIUS_UM)
    dist, idx = nearest([(s[2], s[3]) for s in ss], taps)
    # P-FALSE-GREEN (HEAD-PART-R3 11-27): a seat whose owner is pinned by clock.tap_group.fixed_taps times on THAT tap, not the nearest one
    fx = ((t.get("clock") or {}).get("tap_group") or {}).get("fixed_taps") or {}
    pos = {tp[0]: j for j, tp in enumerate(taps)}
    for i, s in enumerate(ss):
        a = fx.get(seat_owner(s[0], s[1]))
        if a in pos:
            j = pos[a]
            idx[i] = j
            dist[i] = abs(s[2] - taps[j][1]) + abs(s[3] - taps[j][2])
    bad, by = [], {}
    for s, d, j in zip(ss, dist, idx):
        n, o, w = by.get(s[0], (0, 0, 0.0))
        by[s[0]] = (n + 1, o + (d > r + EPS), max(w, d))
        if d > r + EPS:
            bad.append((round(d, 1), s[0], s[1], s[2], s[3], taps[j][0]))
    bad.sort(key=lambda b: -b[0])
    return dict(radius=r, taps=len(taps), seats=len(ss), over=len(bad), far=sum(1 for b in bad if b[0] > FAR_FACTOR * r + EPS),
                worst=bad[0][0] if bad else round(max(dist), 1), by_cat=by, offenders=bad)


def census(raw, tap_sites, types=None):
    """{type: result | dict(unchecked=why)}; tap_sites {type: (sites [(name,x,y)], core, why|None)} from tap_offset_cover.type_ports"""
    res = {}
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if types is not None and tn not in types or not isinstance(t, dict):
            continue
        sites, _core, why = tap_sites.get(tn, ({}, set(), "no tap sites computed"))
        if isinstance(sites, dict):
            sites = [(n, x, y) for n, (x, y) in sites.items()]
        taps = [s for s in sites if not str(s[0]).startswith("clk_c")]
        if why:
            if (t.get("clock") or {}).get("tap_mode") == "explicit" and raw_explicit_taps(t):
                taps, why = raw_explicit_taps(t), None
            else:
                if seats(t):
                    res[tn] = dict(unchecked=why)
                continue
        r = type_reach(t, taps)
        if r:
            res[tn] = r
    return res


def die_name(raw):
    d = raw.get("die")
    return d.get("name") if isinstance(d, dict) else d


def level():
    return "FAIL" if os.environ.get(LEVEL_ENV) == "1" else "WARN"


def findings(raw, res, max_list=3):
    """PRE lines for a census result"""
    lv = level()
    out = []
    flagged = seats_n = over_n = far_n = unchk = 0
    worst = (0.0, "")
    for tn, r in sorted(res.items()):
        if "unchecked" in r:
            unchk += 1
            out.append(f"WARN TAPREACH-UNCHECKED {tn}: tap set not solvable ({r['unchecked'][:120]}); its seats were not judged")
            continue
        seats_n += r["seats"]
        if r["worst"] > worst[0] and r["over"]:
            worst = (r["worst"], tn)
        if not r["over"]:
            continue
        flagged += 1
        over_n += r["over"]
        far_n += r["far"]
        cats = ", ".join(f"{c} {o}/{n}" for c, (n, o, w) in sorted(r["by_cat"].items()) if o)
        sam = "; ".join(f"{b[1]} {b[2]} ({b[3]:g},{b[4]:g}) {b[0]:g} um from {b[5]}" for b in r["offenders"][:max_list])
        out.append(f"{lv} TAPREACH {tn}: {r['over']} of {r['seats']} FIRM seat(s) beyond tap_radius {r['radius']:g} um of every one of "
                   f"{r['taps']} tap(s), {r['far']} beyond {FAR_FACTOR * r['radius']:g} um, worst {r['worst']:g} um [{cats}]: {sam} "
                   f"(fix: a sink tap per seat column in the tap generator, or re-seat; C-TAP-REACH)")
    out.append(f"LIST TAPREACH die {die_name(raw)} types judged {sum(1 for r in res.values() if 'unchecked' not in r)} unchecked {unchk} "
               f"flagged {flagged} seats {seats_n} over {over_n} over-1.5x {far_n} worst {worst[0]:g} um ({worst[1] or '-'})"
               + ("" if lv == "FAIL" else f" (report only; ${LEVEL_ENV}=1 makes them FAIL)"))
    return out


def solve_tap_sites(raw, plan_path, tns=None, mapper=None):
    """{type: (sites, core, why)} via tap_offset_cover.type_ports (the census / TAPOFF solver)"""
    import tap_offset_cover as TC
    P = TC.S.Plan(raw, Path(plan_path))
    names = sorted(tns if tns is not None else (raw.get("partition_types") or {}))
    fn = lambda tn: TC.type_ports(P, raw, tn)
    if mapper:
        return mapper(fn, names)
    return {tn: fn(tn) for tn in names}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    c.add_argument("plan")
    c.add_argument("--types")
    c.add_argument("--tsv")
    c.add_argument("--list", type=int, default=10, help="offender lines to print per flagged type")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    names = [tn for tn in raw.get("partition_types") or {} if not a.types or re.search(a.types, tn)]
    tapsites = solve_tap_sites(raw, a.plan, names)
    res = census(raw, tapsites, set(names))
    for line in findings(raw, res):
        print(line)
    if a.list:
        for tn, r in sorted(res.items()):
            for b in r.get("offenders", [])[:a.list]:
                print(f"  {tn}\t{b[1]}\t{b[2]}\t({b[3]:g},{b[4]:g})\t{b[0]:g}\t{b[5]}")
    if a.tsv:
        with open(a.tsv, "w") as f:
            f.write("type\tseats\ttaps\tradius\tover\tover_1p5x\tworst_um\n")
            for tn, r in sorted(res.items()):
                if "unchecked" not in r:
                    f.write(f"{tn}\t{r['seats']}\t{r['taps']}\t{r['radius']:g}\t{r['over']}\t{r['far']}\t{r['worst']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
