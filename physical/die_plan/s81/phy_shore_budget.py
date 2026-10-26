#!/usr/bin/env python3
"""PATH-S81/PHY (2026-10-26): shoreline budget of the S81 SerDes windows vs the published N7 6-lane 112G macro
(phy_assumptions.json, OWNER 10-26 published-figure assumptions).  Read-only; answers D-S81-PHY step 1: can every
SerDes partition get a one-row macro (>= SER.MACRO6_SHORE x SER.DEPTH_N7) on the die edge by re-laying the SerDes
partitions only, with the other die-edge partitions (HBM PHY, iqf, eng, gunit, bk_sel, stations) left in place?

Per die edge (partitions whose rect touches the edge band), the edge is cut into SEGMENTS by the non-SerDes partitions;
free cells and SerDes partitions inside a segment can be re-laid freely (the most optimistic case: any order, any
width, no feed-through strip).  A segment holding n SerDes needs n x (shore + 2 x PHY guard).  A second, still
optimistic bound adds the junction strip: the partition that hands the chained coll lanes to the slice column needs a
core strip beside its macro (the lanes of its neighbours turn into the column there), >= JUNCTION_STRIP_UM per segment.
Depth: a SerDes partition whose macro must be >= SER.DEPTH_N7 deep in a 1226.88-um row keeps <= 1226.88 - depth for
the core strip under it, i.e. it can carry at most MAX_FT_LINKS other links' feed-through slots (2 x ~115 um each).

usage: phy_shore_budget.py [PLAN.json] [ASSUMPTIONS.json] [--out OUT.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD_UM = 63.64            # pg_domains.PHY_GUARD_UM (VDDPHY domain guard inside the SerDes partition)
EDGE_UM = 105.0
SLOT_PAIR_UM = 2 * 115.0    # one link's coll pair (512 + 514 b) at the plan's face pin density (6 pins/um, 2 layers)
JUNCTION_STRIP_UM = 900.0   # measured: the 8 coll windows of lk_WN3 -> s_0N_x06 span 8767-9665 um


def main(argv):
    out = None
    if "--out" in argv:
        k = argv.index("--out"); out = argv[k + 1]; del argv[k:k + 2]
    plan = json.load(open(argv[1] if len(argv) > 1 else os.path.join(HERE, "die_plan.json")))
    asm = json.load(open(argv[2] if len(argv) > 2 else os.path.join(HERE, "phy_assumptions.json")))
    ent = {e["id"]: e for e in asm["entries"]}
    sh, dp = ent["SER.MACRO6_SHORE"], ent["SER.DEPTH_N7"]
    W, H = plan["die"]["outline_um"]
    T = plan["partition_types"]
    ser = {io["part"] for io in plan["die"]["io"] if io.get("iface") == "serdes"}
    rects = {}
    for q in plan["partitions"]:
        w, h = T[q["type"]]["outline_um"]
        x, y = q["origin_um"]
        rects[q["name"]] = (x, y, x + w, y + h)
    row_h = min(r[3] - r[1] for n, r in rects.items() if n in ser)
    res = dict(die_outline_um=[W, H], shore_low_um=sh["low"], shore_central_um=sh["value"], depth_low_um=dp["low"],
               guard_um=GUARD_UM, edges={}, notes=[])
    tot_avail = tot_need_low = tot_need_c = 0.0
    lo_e, hi_e = EDGE_UM, None
    counted = set()
    for edge in "SNWE":
        if edge in "SN":
            on = [(n, r) for n, r in rects.items() if (r[1] <= EDGE_UM if edge == "S" else H - r[3] <= EDGE_UM)]
            key = lambda t: t[1][0]; span = (EDGE_UM - 1.32, W - EDGE_UM + 1.32); a0, a1 = 0, 2
        else:
            on = [(n, r) for n, r in rects.items() if (r[0] <= EDGE_UM if edge == "W" else W - r[2] <= EDGE_UM)]
            key = lambda t: t[1][1]; span = (EDGE_UM - 1.32, H - EDGE_UM + 1.32); a0, a1 = 1, 3
        on.sort(key=key)
        segs, cur, pos = [], dict(lo=span[0], ser=[], blocked=None), span[0]
        fixed = []
        for n, r in on:
            if n in ser:
                if n not in counted:          # a corner SerDes counts on its S / N edge only (its macro row)
                    cur["ser"].append(n); counted.add(n)
            else:
                fixed.append(dict(part=n, type=next(q["type"] for q in plan["partitions"] if q["name"] == n),
                                  span_um=[round(r[a0], 2), round(r[a1], 2)]))
                cur["hi"] = r[a0]; segs.append(cur); cur = dict(lo=r[a1], ser=[])
        cur["hi"] = span[1]; segs.append(cur)
        rows = []
        for s in segs:
            n = len(s["ser"]); L = s["hi"] - s["lo"]
            if n == 0:
                continue
            need_lo = n * (sh["low"] + 2 * GUARD_UM); need_c = n * (sh["value"] + 2 * GUARD_UM)
            rows.append(dict(segment_um=[round(s["lo"], 2), round(s["hi"], 2)], length_um=round(L, 1), serdes=s["ser"],
                             per_link_um=round(L / n, 1), need_low_um=round(need_lo, 1), need_central_um=round(need_c, 1),
                             need_low_with_junction_um=round(need_lo + JUNCTION_STRIP_UM, 1),
                             fits_low=L >= need_lo, fits_low_with_junction=L >= need_lo + JUNCTION_STRIP_UM,
                             fits_central=L >= need_c, max_links_low=int(L // (sh["low"] + 2 * GUARD_UM)),
                             max_links_low_with_junction=int(max(0.0, L - JUNCTION_STRIP_UM) // (sh["low"] + 2 * GUARD_UM))))
            tot_avail += L; tot_need_low += need_lo; tot_need_c += need_c
        res["edges"][edge] = dict(fixed_non_serdes=fixed, segments=rows,
                                  serdes=sum(len(r["serdes"]) for r in rows))
    strip = row_h - dp["low"]
    res["depth"] = dict(row_um=row_h, max_core_strip_um=round(strip, 1),
                        max_ft_links_under_macro=int(strip // SLOT_PAIR_UM),
                        note="a SerDes partition carrying k other links' coll pairs under its macro needs ~k x 230 um "
                             "of core strip; lk_WN0 (t3, k=2) has 516 um -> 711-um macro, lk_WS0 (t15, k=2+) 482 um")
    res["total"] = dict(serdes=len(ser), segment_length_um=round(tot_avail, 1), need_low_um=round(tot_need_low, 1),
                        need_central_um=round(tot_need_c, 1), fits_low=tot_avail >= tot_need_low,
                        max_links_low=sum(r["max_links_low"] for e in res["edges"].values() for r in e["segments"]),
                        max_links_low_with_junction=sum(r["max_links_low_with_junction"] for e in res["edges"].values()
                                                        for r in e["segments"]))
    s = json.dumps(res, indent=1)
    if out:
        open(out, "w").write(s + "\n")
    print(s)


if __name__ == "__main__":
    main(sys.argv)
