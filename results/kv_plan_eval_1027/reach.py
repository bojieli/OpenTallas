#!/usr/bin/env python3
"""KV-PLAN-EVAL (c): for every FT slot whose station count the event raises, is the +1 needed for 405-um reach?
Lower bound path = Manhattan in-pin -> out-pin centroid; event path = in-pin -> stations -> out-pin centroid."""
import json, math, sys, collections
from pathlib import Path
sys.path[:0] = [sys.argv[1] + "/tools/die_plan", sys.argv[1] + "/tools"]
import schema as S, gen_phys
qp, ep, out = sys.argv[2], sys.argv[3], sys.argv[4]
Q = S.Plan(S.load(qp), Path(qp)); E = S.Plan(S.load(ep), Path(ep))
REACH = 405.0
def pins(P, tn):
    d = collections.defaultdict(list)
    for bus, bit, ln, x, y, f in gen_phys.type_pins(P, tn):
        d[bus].append((x, y))
    return d
rows = []
for tn, te in E.types.items():
    tq = Q.types[tn]
    sq = {s["name"]: s for s in tq.get("ft_slots", []) or []}
    ch = [s for s in te.get("ft_slots", []) or [] if s["name"] in sq and s["stations"] != sq[s["name"]]["stations"]]
    if not ch: continue
    pe = pins(E, tn)
    for s in ch:
        n = s["name"]; pi, po = pe.get(n + "_i"), pe.get(n + "_o")
        if not pi or not po: rows.append(dict(type=tn, slot=n, err="nopins")); continue
        ci = (sum(x for x, _ in pi) / len(pi), sum(y for _, y in pi) / len(pi))
        co = (sum(x for x, _ in po) / len(po), sum(y for _, y in po) / len(po))
        # worst bit: pair bits by index
        lb = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(sorted(pi), sorted(po)))
        lbc = abs(ci[0] - co[0]) + abs(ci[1] - co[1])
        regs = s.get("regs_um") or []
        pts = [ci] + [tuple(r) for r in regs[1:]] + [co] if regs else []
        hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
        need = max(0, math.ceil(lbc / REACH) - 1)
        rows.append(dict(type=tn, slot=n, width=int(s["width"]), st_q2=sq[n]["stations"], st_ev=s["stations"],
                         manh_centroid=round(lbc, 1), manh_worstbit=round(lb, 1), ev_path=round(sum(hops), 1),
                         ev_maxhop=round(max(hops), 1) if hops else None, min_stations_reach=need,
                         plus1_needed_by_lower_bound=need > sq[n]["stations"],
                         detour=round(sum(hops) / lbc, 2) if lbc and hops else None))
ok = [r for r in rows if "err" not in r]
c = collections.Counter(r["plus1_needed_by_lower_bound"] for r in ok)
summ = dict(changed_slots=len(rows), errors=len(rows) - len(ok), plus1_needed_by_straight_manhattan=c[True],
            plus1_detour_only=c[False],
            bits_needed=sum(r["width"] for r in ok if r["plus1_needed_by_lower_bound"]),
            bits_detour_only=sum(r["width"] for r in ok if not r["plus1_needed_by_lower_bound"]),
            by_type={t: collections.Counter(str(r["plus1_needed_by_lower_bound"]) for r in ok if r["type"] == t) for t in sorted({r["type"] for r in ok})})
json.dump(dict(summary=summ, rows=rows), open(out, "w"), indent=1)
print(json.dumps(summ, indent=1))
