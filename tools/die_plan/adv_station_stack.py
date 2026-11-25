"""adv_station_stack.py -- PRECHECK ADV-STATION-STACK (COORD 11-25, KV-OWN-PV V1NSITE class; report only).

Two or more DIFFERENT buses whose station registers sit on the same plan point stack their FIRM banks into one
landing window: kv3_pv_v1n (A5t6 a498941539fd) gave the three parallel 269-bit vport buses i_vport_{E,W}_N_vo /
_vo_d1 / _vo_d2 identical regs_um, so 191 points held 3 banks each; at two of them a reset tap and a reader START
landed in the same window -> OT_CLAND "no legal site" at place.  Fix row ROWS_KV-OWN-PV-R2-V1NSITE (887341f510ca):
the first bus keeps the point, the others move +-12 um across their leg.

Per partition type: every station point (internal_stations[].regs_um keyed by conn, ft_slots[].regs_um keyed by slot
name; points within 0.1 um are one point, as in the row) shared by >= 2 distinct buses is a STACK; stacks with an
ft slot are counted apart (the V1NSITE row counts internal_stations only: kv3_pv_v1n 191 before, 0 after, plus 6 ft4/ft5).  Reported: stacked
points, max buses per point, bits per point (sum of the stacked buses' widths: buses[].width / ft_slots[].width), and
how many stacks have a reset tap / reset relay (TAP) or a landing reader/writer START stage or START local reset (START)
within NEAR_UM (10 um, Manhattan) -- the sites adv_site_collide.type_items lists.
Fix: move the extra buses' registers >= one bank (12 um) off the shared point (V1NSITE rule).
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_site_collide as _SC  # noqa: E402

CHECK = "ADV-STATION-STACK"
NEAR_UM = 10.0
PT_UM = 0.1
MAX_LINES = 25
TAP_KINDS = ("reset_tap", "reset_relay")
START_KINDS = ("start", "local_reset_start")


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _key(p):
    return (round(float(p[0]) / PT_UM), round(float(p[1]) / PT_UM))


def stacks(t):
    """{point key: {bus: (x, y)}} of the station points shared by >= 2 distinct buses of one type"""
    own = collections.defaultdict(dict)
    for st in t.get("internal_stations") or []:
        if not isinstance(st, dict):
            continue
        b = str(st.get("conn"))
        for p in st.get("regs_um") or []:
            q = _SC._xy(p)
            if q:
                own[_key(q)].setdefault(b, q)
    for sl in t.get("ft_slots") or []:
        if not isinstance(sl, dict):
            continue
        b = f"ft:{sl.get('name')}"
        for p in sl.get("regs_um") or []:
            q = _SC._xy(p)
            if q:
                own[_key(q)].setdefault(b, q)
    return {k: v for k, v in own.items() if len(v) > 1}


def widths(t):
    w = {}
    for b in t.get("buses") or []:
        if isinstance(b, dict) and b.get("name") is not None:
            w[f"bus:{b['name']}"] = b.get("width")
    for sl in t.get("ft_slots") or []:
        if isinstance(sl, dict):
            w[f"ft:{sl.get('name')}"] = sl.get("width")
    return w


def judge_type(t):
    """-> dict(points, max_buses, max_bits, bits, tap, start, sample) for one partition type"""
    S = stacks(t)
    r = dict(points=len(S), ft=sum(1 for v in S.values() if any(b.startswith("ft:") for b in v)), max_buses=0, max_bits=0, bits=0, tap=0, start=0, sample=None)
    if not S:
        return r
    W = widths(t)
    items = _SC.type_items(t)
    taps = [(x, y) for k, _, x, y in items if k in TAP_KINDS]
    starts = [(x, y) for k, _, x, y in items if k in START_KINDS]

    def near(q, pts):
        return any(abs(q[0] - a) + abs(q[1] - b) <= NEAR_UM for a, b in pts)

    worst = None
    for k, buses in sorted(S.items()):
        q = next(iter(buses.values()))
        bits = sum(int(W.get(b) or 0) for b in buses)
        r["bits"] += bits
        r["max_buses"] = max(r["max_buses"], len(buses))
        r["max_bits"] = max(r["max_bits"], bits)
        nt, ns = near(q, taps), near(q, starts)
        r["tap"] += nt
        r["start"] += ns
        rank = (nt + ns, len(buses), bits)
        if worst is None or rank > worst[0]:
            worst = (rank, q, sorted(buses), bits, nt, ns)
    _, q, bl, bits, nt, ns = worst
    r["sample"] = (f"({q[0]:.1f}, {q[1]:.1f}) {len(bl)} buses {bits} bits ({', '.join(b.replace('bus:', '') for b in bl[:4])}"
                   f"{' ...' if len(bl) > 4 else ''}){' + TAP' if nt else ''}{' + START' if ns else ''} within {NEAR_UM:g} um")
    return r


def _findings(raw, plan_path, tree=None, **kw):
    out, nt, nbad = [], 0, 0
    tot = dict(points=0, ft=0, bits=0, tap=0, start=0)
    mx = dict(max_buses=0, max_bits=0)
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict) or t.get("hard"):
            continue
        nt += 1
        r = judge_type(t)
        if not r["points"]:
            continue
        nbad += 1
        for k in tot:
            tot[k] += r[k]
        for k in mx:
            mx[k] = max(mx[k], r[k])
        out.append(((r["tap"] + r["start"], r["points"]), _w(
            f"{tn}: {r['points']} station point(s) shared by >= 2 buses ({r['points'] - r['ft']} internal_stations, {r['ft']} with ft_slots; max {r['max_buses']} buses / {r['max_bits']} bits per point, "
            f"{r['bits']} stacked bits), {r['tap']} with a reset tap and {r['start']} with a START within {NEAR_UM:g} um; worst {r['sample']}; "
            f"stacked FIRM banks share one landing window (kv3_pv_v1n: OT_CLAND no legal site): move the extra buses >= 12 um off "
            f"the point (ROWS_KV-OWN-PV-R2-V1NSITE rule)")))
    out.sort(key=lambda x: (-x[0][0], -x[0][1]))
    lines = [m for _, m in out[:MAX_LINES]]
    lines.append(_w("summary", f"{nbad} of {nt} soft types have stacked station points: {tot['points']} points ({tot['points'] - tot['ft']} internal_stations, "
                               f"{tot['ft']} with ft_slots), {tot['bits']} stacked bits "
                               f"(max {mx['max_buses']} buses / {mx['max_bits']} bits per point), {tot['tap']} with a reset tap and "
                               f"{tot['start']} with a START within {NEAR_UM:g} um"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import time
    t0 = time.time()
    raw_ = json.load(open(sys.argv[1]))
    ls = findings(raw_, sys.argv[1])
    print(f"tag={sys.argv[2] if len(sys.argv) > 2 else ''} {time.time() - t0:.1f}s")
    for ln in ls:
        print(ln)
