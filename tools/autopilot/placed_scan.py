#!/usr/bin/env python3
"""PLACED-SCAN-1115: early-fail diagnostic on a placed geom.tsv (geom_dump.tcl format).

Finds buses that cross a type in ONE cycle with no station on the matched group: zero-logic links
(flop / hard macro / top pin -> buffers or inverters only -> flop / macro / top pin), grouped by
(source group -> end group) and measured as Manhattan distance on the placed dump.  Such a group
shows up otherwise only after a long place / route / CTS fails (QC su_c, fw / st_b; KV pv, hg / hgi).

Reach thresholds (FABLE-CLOSURE-STRATEGY lever 4, FABLE-PD-QC-SUC-0800 s1):
  PLAN_REACH_UM  405  the plan signal reach (die_plan schema SIGNAL_REACH_UM, ruling 9.3): a hop longer than this
                      needs a station by the plan rule                                    -> class REACH
  CYCLE_REACH_UM 580  what one 833 ps cycle carries at ~1.24 ps/um (measured slw_su_c worst path)
                      -> class NEED-STATION (the group will not time as one cycle)
When the kit's die plan is found (--plan, or <kit>/../../plandir/die_plan.json) each flagged group is matched to the
type's internal_stations rows: ROW=n/hop means a station row exists on that bus but the placed hop is still over reach
(station sited wrong or row too sparse); ROW=none means the plan has no station on the matched group.

Advisory only: exit 0 unless --strict.  Prints one line `AP_PLACED_SCAN ...` that names the worst groups and
writes OUT/placed_scan.tsv + OUT/placed_scan.json.

  placed_scan.py GEOM.TSV [--kit KITDIR] [--plan die_plan.json] [--type NAME] [--out DIR]
                 [--limit 405] [--cycle 580] [--top 25] [--min-bits 1] [--strict]
"""
import argparse
import collections
import json
import os
import re
import sys

PLAN_REACH_UM = 405.0
CYCLE_REACH_UM = 580.0
PS_PER_UM = 1.24
STRAP_RE = re.compile(r"strap", re.I)


def load(path):
    C, P, drv = {}, {}, {}
    with open(path, errors="replace") as fh:
        for ln in fh:
            t = ln.rstrip("\n").split("\t")
            k = t[0]
            if k == "C":
                C[t[1]] = (t[2], float(t[4]), float(t[5]), float(t[6]), float(t[7]), t[8])
            elif k == "P":
                P[t[1]] = (t[2], t[3], float(t[6]), float(t[7]))
            elif k == "N" and t[1] == "SIGNAL":
                d = t[2]
                for s in t[3:]:
                    if not s.endswith("c"):
                        drv.setdefault(s, []).append(d)
    return C, P, drv


def grp(n):
    n = n.replace("\\", "")
    n = re.sub(r"\$_.*$", "", n)
    n = re.sub(r"\[\d+\]", "", n)
    n = re.sub(r"/q$", "", n)
    return re.sub(r"_q$", "", n)


def scan(C, P, drv, limit, cycle):
    def pos(k, other=None):
        if k[0] == "p":
            p = P[k[1:]]
            return (p[2], p[3])
        c = C[k[1:]]
        if c[0] == "M" and other:
            return (min(max(other[0], c[1]), c[3]), min(max(other[1], c[2]), c[4]))
        return ((c[1] + c[3]) / 2, (c[2] + c[4]) / 2)

    def name(k):
        return "PIN:" + re.sub(r"\[\d+\]", "", P[k[1:]][0]) if k[0] == "p" else grp(C[k[1:]][5])

    def kind(k):
        return "P" if k[0] == "p" else C[k[1:]][0] if k[1:] in C else "?"

    st = collections.defaultdict(lambda: {"bits": 0, "reach": 0, "cycle": 0, "max": 0.0, "sum": 0.0, "bufs": 0,
                                  "sx": 0.0, "sy": 0.0, "ex": 0.0, "ey": 0.0})
    ends = [("i" + i) for i, c in C.items() if c[0] in "SM"] + [("p" + k) for k, p in P.items() if p[1] == "OUTPUT"]
    for e in ends:
        for d in drv.get(e, []):
            nb, cur, ok = 0, d, True
            while True:
                k = kind(cur)
                if k != "B":
                    break
                nb += 1
                ds = drv.get(cur, [])
                if len(ds) != 1 or nb > 200:
                    ok = False
                    break
                cur = ds[0]
            if not ok or k not in ("S", "M", "P"):
                continue
            if e[0] == "i" and C[e[1:]][0] == "M":
                ps = pos(cur)
                pe = pos(e, ps)
            else:
                pe = pos(e)
                ps = pos(cur, pe)
            dist = abs(ps[0] - pe[0]) + abs(ps[1] - pe[1])
            a, b = name(cur), name(e)
            if STRAP_RE.search(a) or STRAP_RE.search(b):
                continue
            s = st[(a, b)]
            s["bits"] += 1
            s["sum"] += dist
            s["reach"] += dist > limit
            if dist > limit:                      # mean launch / capture point of the long bits (station rows)
                s["sx"] += ps[0]; s["sy"] += ps[1]; s["ex"] += pe[0]; s["ey"] += pe[1]
            s["cycle"] += dist > cycle
            s["max"] = max(s["max"], dist)
            s["bufs"] = max(s["bufs"], nb)
    return st


def plan_rows(plan, tname):
    """-> [(bus, n_stations, max_declared_hop_um)] from partition_types[tname].internal_stations"""
    try:
        t = json.load(open(plan))["partition_types"][tname]
    except Exception:
        return None
    rows = []
    for s in t.get("internal_stations") or []:
        pts = [s.get("from_um")] + list(s.get("regs_um") or []) + [s.get("to_um")]
        pts = [p for p in pts if p]
        hop = max((abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])), default=0.0)
        rows.append((str(s.get("conn", "")).split(":", 1)[-1], len(s.get("regs_um") or []), hop))
    return rows


def row_for(rows, a, b):
    if rows is None:
        return "NA"
    for bus, n, hop in rows:
        if len(bus) >= 6 and any(bus in x or x.replace("PIN:", "") == bus for x in (a, b)):
            return f"{n}/{hop:.0f}um"
    return "none"


def derive_rows(out, limit):
    """Station form for the NEED-STATION groups, instead of a wider band / bigger window: per matched group the number of
    stations n = ceil(mean_long_hop / limit) - 1 and their sites on the Manhattan leg launch -> capture (x first, as the
    plan rows `regs_um`).  Rows follow the plan internal_stations layout (conn, from_um, to_um, regs_um)."""
    import math
    rows = []
    for r in out:
        if r["cls"] != "NEED-STATION" or not r.get("_n"):
            continue
        n = r["_n"]
        sx, sy, ex, ey = (x / n for x in (r["_sx"], r["_sy"], r["_ex"], r["_ey"]))
        leg = abs(ex - sx) + abs(ey - sy)
        k = max(1, math.ceil(leg / limit) - 1)
        regs = []
        for i in range(1, k + 1):
            d = leg * i / (k + 1)
            dx = abs(ex - sx)
            if d <= dx:
                regs.append([round(sx + math.copysign(d, ex - sx), 2), round(sy, 2)])
            else:
                regs.append([round(ex, 2), round(sy + math.copysign(d - dx, ey - sy), 2)])
        rows.append({"conn": "group:" + r["src"] + "->" + r["end"], "from_um": [round(sx, 2), round(sy, 2)],
                     "to_um": [round(ex, 2), round(ey, 2)], "regs_um": regs, "bits": r["over_reach"],
                     "leg_um": round(leg), "max_um": r["max_um"], "stations": k, "hop_um": round(leg / (k + 1)),
                     "plan_row": r["row"]})
    return rows


def find_plan(kit, plan):
    if plan:
        return plan
    if not kit:
        return None
    for rel in ("plandir/die_plan.json", "../../plandir/die_plan.json", "die_plan.json"):
        p = os.path.join(kit, rel)
        if os.path.isfile(p):
            return p
    return None


def reach_decision(summ, goal=None, environ=None):
    """FP-CONVERGE-S81 PLACED-REACH (FABLE-RC-S81, report-only): -> (stop, line).  The line is always printed; the stop is
    enforced only for a route-goal kit with OT_PLACED_REACH_STOP=1 and bits that need more than one cycle (bits_over_cycle > 0)."""
    env = os.environ if environ is None else environ
    goal = goal or env.get("OT_KIT_GOAL") or ""
    boc, bor = int(summ.get("bits_over_cycle") or 0), int(summ.get("bits_over_reach") or 0)
    bad = boc > 0
    stop = bool(bad and goal == "route" and env.get("OT_PLACED_REACH_STOP") == "1")
    line = (f"PLACED-REACH {'STOP' if stop else ('WARN' if bad else 'ok')} goal={goal or '-'} bits_over_cycle={boc} "
            f"bits_over_reach={bor} groups_need_station={summ.get('groups_need_station')}"
            + ("" if stop or not bad else " (report-only: OT_PLACED_REACH_STOP=1 stops a route-goal kit)"))
    return stop, line


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--goal", default="", help="kit goal (route/place); default $OT_KIT_GOAL")
    ap.add_argument("geom")
    ap.add_argument("--kit")
    ap.add_argument("--plan")
    ap.add_argument("--type")
    ap.add_argument("--out")
    ap.add_argument("--limit", type=float, default=PLAN_REACH_UM)
    ap.add_argument("--cycle", type=float, default=CYCLE_REACH_UM)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--min-bits", type=int, default=1)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)

    C, P, drv = load(a.geom)
    st = scan(C, P, drv, a.limit, a.cycle)
    tname = a.type or (os.path.basename(os.path.abspath(a.kit)) if a.kit else None)
    plan = find_plan(a.kit, a.plan)
    rows = plan_rows(plan, tname) if plan and tname else None
    out = []
    for (s, e), v in st.items():
        if v["reach"] < a.min_bits:
            continue
        cls = "NEED-STATION" if v["cycle"] else "REACH"
        out.append({"src": s, "end": e, "cls": cls, "bits": v["bits"], "over_reach": v["reach"], "over_cycle": v["cycle"],
                    "max_um": round(v["max"]), "mean_um": round(v["sum"] / v["bits"]), "max_bufs": v["bufs"],
                    "est_ps": round(v["max"] * PS_PER_UM), "row": row_for(rows, s, e),
                    "_n": v["reach"], "_sx": v["sx"], "_sy": v["sy"], "_ex": v["ex"], "_ey": v["ey"]})
    out.sort(key=lambda r: (r["cls"] != "NEED-STATION", -r["over_cycle"], -r["over_reach"], -r["max_um"]))
    need = [r for r in out if r["cls"] == "NEED-STATION"]
    summ = {"geom": a.geom, "type": tname, "limit_um": a.limit, "cycle_um": a.cycle, "plan": plan,
            "groups_over_reach": len(out), "groups_need_station": len(need),
            "bits_over_reach": sum(r["over_reach"] for r in out), "bits_over_cycle": sum(r["over_cycle"] for r in out),
            "groups": out}
    srows = derive_rows(out, a.limit)
    for r in out:
        for k in ("_n", "_sx", "_sy", "_ex", "_ey"):
            r.pop(k, None)
    summ["station_rows"] = len(srows)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "placed_scan_rows.json"), "w") as fh:
            json.dump({"type": tname, "limit_um": a.limit, "rows": srows}, fh, indent=1)
        with open(os.path.join(a.out, "placed_scan.json"), "w") as fh:
            json.dump(summ, fh, indent=1)
        with open(os.path.join(a.out, "placed_scan.tsv"), "w") as fh:
            fh.write("class\tsrc_group\tend_group\tbits\tover_reach\tover_cycle\tmax_um\tmean_um\test_ps\tmax_bufs\tplan_row\n")
            for r in out:
                fh.write("\t".join(str(r[k]) for k in ("cls", "src", "end", "bits", "over_reach", "over_cycle", "max_um",
                                                        "mean_um", "est_ps", "max_bufs", "row")) + "\n")
    top = "; ".join(f"{r['src']}->{r['end']} {r['over_cycle'] or r['over_reach']}b max {r['max_um']}um row={r['row']}"
                    for r in out[:3])
    verdict = "NEED-STATION" if need else ("REACH" if out else "OK")
    print(f"AP_PLACED_SCAN {verdict} type={tname} groups_need_station={len(need)} groups_over_{a.limit:.0f}um={len(out)} "
          f"bits_over_{a.cycle:.0f}um={summ['bits_over_cycle']} bits_over_{a.limit:.0f}um={summ['bits_over_reach']} "
          f"(advisory, early-fail diagnostic){' :: ' + top if top else ''}")
    for r in out[:a.top]:
        print(f"  {r['cls']:12s} {r['src']} -> {r['end']}\tbits {r['bits']} over{a.limit:.0f} {r['over_reach']} "
              f"over{a.cycle:.0f} {r['over_cycle']} max {r['max_um']}um mean {r['mean_um']}um ~{r['est_ps']}ps bufs {r['max_bufs']} "
              f"plan_row {r['row']}")
    stop, line = reach_decision(summ, a.goal)
    print(line)
    if stop:
        return 3
    return 1 if (a.strict and need) else 0


if __name__ == "__main__":
    sys.exit(main())
