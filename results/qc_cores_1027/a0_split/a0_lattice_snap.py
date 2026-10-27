#!/usr/bin/env python3
"""QC-CORES-2 A0-CLK-R3: snap check of the A0 type islands against a die strap lattice (published r2_plan xs/ys).
For every one of the 768 A0 instances (720 NK + 48 NL) in the die plan, map each type island (core frame, R0 in x, MX
partitions mirror y) to die coordinates and measure the distance to the nearest M9-x / M8-y strap and the nearest
crossing.  Also derive the A0-commensurate strap plan delta (die M9 at x0+XL, M8 at y0+YL / y0+H-YL).
usage: a0_lattice_snap.py PLAN R2PLAN R3PLANJSON R2PLANJSON OUT.json"""
import bisect, json, sys
from collections import Counter
P, R2, R3J, R2J, OUT = sys.argv[1:6]
p = json.load(open(P)); r = json.load(open(R2))
xs, ys = sorted(r["xs"]), sorted(r["ys"])
CW, CH = 457.92, 1157.76
pt = p["partition_types"]


def near(v, a):
    i = bisect.bisect_left(a, v)
    return min(abs(v - a[j]) for j in (i - 1, i) if 0 <= j < len(a))


inst = []
for part in p["partitions"]:
    t = pt[part["type"]]; PW, PH = t["outline_um"]; ox, oy = part["origin_um"]; o = part.get("orient", "R0")
    for c in t.get("contents", []):
        if c["module"].endswith("romleaf_rpf"):
            cx, cy = c["origin_um"]
            assert o in ("R0", "MX"), o
            inst.append((part["name"] + "/" + c["inst"], c["module"], ox + cx, oy + (cy if o == "R0" else PH - cy - CH), o == "MX"))


def snap(islands):
    rows, worst = [], (0, None)
    for n, m, x0, y0, fy in inst:
        for k, (u, v) in islands.items():
            X, Y = x0 + u, y0 + (CH - v if fy else v)
            dx, dy = near(X, xs), near(Y, ys)
            d = max(dx, dy) if False else (dx ** 2 + dy ** 2) ** 0.5
            rows.append((n, k, round(dx, 3), round(dy, 3), round(d, 3)))
            if d > worst[0]:
                worst = (d, (n, k, round(X, 3), round(Y, 3), round(dx, 3), round(dy, 3)))
    ds = sorted(x[4] for x in rows)
    coinc = sum(1 for x in rows if x[4] <= 0.5)
    inst_ok = Counter(x[0] for x in rows if x[4] > 0.5)
    return dict(sites=len(rows), coincide_le_0p5um=coinc, max_um=round(ds[-1], 3), median_um=ds[len(ds) // 2],
                p90_um=ds[int(0.9 * len(ds))], instances_all_coincide=len(inst) - len(inst_ok), worst=worst[1],
                max_dx_um=max(x[2] for x in rows), max_dy_um=max(x[3] for x in rows))


rep = dict(schema="qc_cores_1027.a0_lattice_snap.v1", plan=P, r2_plan=R2, plan_sha256=r.get("plan_sha256"),
           n_instances=len(inst), n_nk=sum(1 for i in inst if "nk_" in i[1]), n_nl=sum(1 for i in inst if "nl_" in i[1]),
           lattice=dict(m9_x=len(xs), m8_y=len(ys)))
r3 = json.load(open(R3J))["cores"]["nk"]["islands"]; r2i = json.load(open(R2J))["cores"]["nk"]["islands"]
rep["R2_islands_vs_lattice"] = snap({k: v["xy"] for k, v in r2i.items()})
rep["R3_islands_vs_lattice"] = snap({k: v["xy"] for k, v in r3.items()})
# per-type crossing census: which core-frame crossings each instance sees
cu = Counter(); cv = Counter(); cnt = Counter()
for n, m, x0, y0, fy in inst:
    us = tuple(round(X - x0, 3) for X in xs if x0 <= X <= x0 + CW)
    vs = tuple(sorted(round(CH - (Y - y0) if fy else Y - y0, 3) for Y in ys if y0 <= Y <= y0 + CH))
    cu[us] += 1; cv[vs] += 1; cnt[len(us) * len(vs)] += 1
rep["type_crossing_census"] = dict(distinct_m9_phase_sets=len(cu), m9_sets=[[list(k), n] for k, n in cu.most_common()],
                                   distinct_m8_phase_sets=len(cv), m8_sets=[[list(k), n] for k, n in cv.most_common()],
                                   crossings_per_core_hist=sorted(cnt.items()))
# plan delta: A0-commensurate drop straps
XL = sorted({v["xy"][0] for v in r3.values()}); YL = sorted({v["xy"][1] for v in r3.values()})
reqx = sorted({round(x0 + u, 3) for _, _, x0, _, _ in inst for u in XL})
reqy = sorted({round(y0 + (CH - v if fy else v), 3) for _, _, _, y0, fy in inst for v in YL})
gx = [round(b - a, 3) for a, b in zip(reqx, reqx[1:])]; gy = [round(b - a, 3) for a, b in zip(reqy, reqy[1:])]
rep["plan_delta_drop_straps"] = dict(type_lattice_core_frame=dict(m9_x=XL, m8_y=YL), m9_x_n=len(reqx), m8_y_n=len(reqy),
                                     m9_gap_um=[min(gx), max(gx)], m8_gap_um=[min(gy), max(gy)],
                                     m9_moved_vs_lattice=sum(1 for x in reqx if near(x, xs) > 0.5),
                                     m8_moved_vs_lattice=sum(1 for y in reqy if near(y, ys) > 0.5),
                                     max_shift_m9_um=round(max(near(x, xs) for x in reqx), 3),
                                     max_shift_m8_um=round(max(near(y, ys) for y in reqy), 3),
                                     m9_x=reqx, m8_y=reqy,
                                     note="die M9 straps at these x and M8 at these y make every A0 island a crossing; the die "
                                          "owner keeps/adds its own straps elsewhere (inter-row bands, non-A0 regions) for mesh density")
json.dump(rep, open(OUT, "w"), indent=1)
for k in ("R2_islands_vs_lattice", "R3_islands_vs_lattice"):
    print(k, {a: b for a, b in rep[k].items()})
print("census m9 sets", rep["type_crossing_census"]["distinct_m9_phase_sets"], "m8 sets", rep["type_crossing_census"]["distinct_m8_phase_sets"], "crossings/core", rep["type_crossing_census"]["crossings_per_core_hist"])
d = rep["plan_delta_drop_straps"]; print("delta", {k: d[k] for k in d if k not in ("m9_x", "m8_y")})
