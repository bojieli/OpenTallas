#!/usr/bin/env python3
"""DIE-PROTO/QC hop audit (read-only): every unregistered signal leg vs the 405-um M4-M7 reach (decision 12).

(a) lane hops: tools/die_plan/check.py run() -> summary hops/stations (lane register-to-register hops, slot-level
    stations evenly along the crossing route).
(b) actual-bit ft legs: per ft slot, per bit: in-pin -> station 1..k-1 -> out-pin with each bit's own face pins
    (gen_phys.type_pins) and the plan's station sites (bit_sites_um, else regs_um, else evenly along the bit's own
    Z route) -- the method of codex/qc-bitstations-1025 bit_stations.geometry_failures, but counting every leg.
    Legs are multiplied by the instance count of the type.

    python3 qc_hop_audit.py REPO PLAN.json OUT.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

repo, plan, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
sys.path.insert(0, str(repo / "tools" / "die_plan"))
import check  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

LIM = 405.0
raw = json.loads(Path(plan).read_text())
P = S.Plan(raw)
ninst = defaultdict(int)
for p in P.parts.values():
    ninst[p["type"]] += 1

rows, hist = [], defaultdict(int)
tot_legs = tot_bad = tot_bad_inst = 0
for tn, ty in sorted(P.types.items()):
    if not ty.get("ft_slots"):
        continue
    pins = {(b, i): (x, y, face) for b, i, _, x, y, face in gen_phys.type_pins(P, tn)}
    boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
              c["origin_um"][1] + c["outline_um"][1]) for c in ty.get("hard_cores", []) or []]
    for slot in ty["ft_slots"]:
        name, k = slot["name"], int(slot.get("stations", 1))
        worst, bad, legs, inside, mode = 0.0, 0, 0, 0, "even"
        for bit in range(int(slot["width"]) + 1):
            a, b = pins.get((name + "_i", bit)), pins.get((name + "_o", bit))
            if a is None or b is None:
                continue
            path = check.zroute(a[:2], b[:2], a[2], b[2])
            length = check.plen(path)
            pts = [a[:2]]
            for j in range(1, k):
                if slot.get("bit_sites_um"):
                    q = slot["bit_sites_um"][j - 1][bit]
                    c = slot["bit_site_cell_um"]
                    pt, mode = (q[0] + c[0] / 2, q[1] + c[1] / 2), "bit_sites"
                elif slot.get("regs_um"):
                    pt, mode = tuple(slot["regs_um"][j]), "regs_um"
                else:
                    pt = check.point_at(path, length * j / k)
                inside += sum(x0 < pt[0] < x1 and y0 < pt[1] < y1 for x0, y0, x1, y1 in boxes)
                pts.append(pt)
            pts.append(b[:2])
            for p, q in zip(pts, pts[1:]):
                L = abs(p[0] - q[0]) + abs(p[1] - q[1])
                legs += 1
                worst = max(worst, L)
                if L > LIM + 1e-6:
                    bad += 1
                    hist[int(L // 50) * 50] += ninst[tn]
        tot_legs += legs * ninst[tn]
        tot_bad += bad
        tot_bad_inst += bad * ninst[tn]
        if bad or inside:
            rows.append(dict(type=tn, slot=name, width=slot["width"], stations=k, site_mode=mode, worst_leg_um=round(worst, 1),
                             legs_over_405=bad, instances=ninst[tn], legs_over_405_x_inst=bad * ninst[tn],
                             stations_inside_core=inside))
rows.sort(key=lambda r: -r["worst_leg_um"])

R, summ = check.run(raw, plan_dir=str(Path(plan).parent))
errs = [dict(i) for i in R.items if i.get("check") in ("hops", "stations")]
res = dict(plan=plan, limit_um=LIM,
           bit_legs=dict(total_legs_x_inst=tot_legs, over_405_type_level=tot_bad, over_405_x_inst=tot_bad_inst,
                         slots_failing=len(rows), hist_over_405_x_inst=dict(sorted(hist.items())), worst=rows[:60]),
           lane_hops=dict(top10=summ.get("worst_hops"),
                          errors=len(errs), first_errors=errs[:20]))
Path(out).write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(dict(bit=res["bit_legs"] | {"worst": rows[:8]}, lane=res["lane_hops"] | {"first_errors": errs[:5]}),
                 indent=1))
