#!/usr/bin/env python3
"""QC-SU-F4D GEOM detour check (RULING GEOM-REVIEW-10 meander 18:43): per tree edge, planned routed length (sum of the
shortest legal maze legs between placed cells) vs the Manhattan distance of its end nodes; an edge > 10 % over Manhattan
is listed with its legality reason (maze obstruction: macro + 4.32 halo, keep-outs, island squares).
usage: detour.py PLAN.json [OUT.json]"""
import json, sys
d = json.load(open(sys.argv[1])); E = d["gates"]["G4_strict"]["edges"]
tot_p = tot_m = 0.0; over = []; per = {}
for e in E:
    p = e["path_um"]; a, b = p[0], p[-1]
    man = abs(a[0] - b[0]) + abs(a[1] - b[1]); L = e["enforced_um"]
    tot_p += L; tot_m += man
    lv = per.setdefault(e["level"], [0, 0.0, 0.0, 0]); lv[0] += 1; lv[1] += L; lv[2] += man
    ex = L - man
    if man > 0 and ex > 0.10 * man and ex > 1.1:
        lv[3] += 1
        over.append(dict(edge=e["edge"], level=e["level"], len_um=L, manhattan_um=round(man, 2), over_pct=round(100 * ex / man, 1),
                         shortest_um=e["shortest_um"], legal_jog=abs(L - e["shortest_um"]) <= 1.1,
                         reason="maze shortest legal path (macro+halo / keep-out / island obstruction)" if abs(L - e["shortest_um"]) <= 1.1 else "NOT shortest: detour"))
r = dict(plan=sys.argv[1], edges=len(E), total_len_um=round(tot_p, 1), total_manhattan_um=round(tot_m, 1),
         detour_um=round(tot_p - tot_m, 1), detour_pct=round(100 * (tot_p - tot_m) / tot_m, 2),
         levels={k: dict(edges=v[0], len_um=round(v[1], 1), manhattan_um=round(v[2], 1), over10=v[3]) for k, v in per.items()},
         edges_over_10pct=len(over), edges_over_10pct_not_shortest=sum(1 for o in over if not o["legal_jog"]), over=over,
         pinwin_path_cells=d.get("pinwin_path_cells"), edges_with_pinwin_cells=d.get("edges_with_pinwin_cells"))
if len(sys.argv) > 2: json.dump(r, open(sys.argv[2], "w"), indent=1)
print(json.dumps({k: v for k, v in r.items() if k != "over"}))
for o in over: print(" ", o)
