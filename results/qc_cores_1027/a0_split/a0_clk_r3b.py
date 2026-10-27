#!/usr/bin/env python3
"""QC-CORES-2 A0-CLK-R3b (COORD 05:5x / GEOM-21): drop form per island, per-instance identity incl. MX rows, the 16 strap-less
instances, PG stripe check.  Input: R3 plan (islands, core frame), die plan + r2 mesh plan (R22 d43 PROVISIONAL / R23 d51).
Die PG (plan die.pg.grid): M8/M9 0.48 um at 8.64 pitch, VDD offset 4.32; VSS lanes at 8.64k (qc_clk_mesh3 R15 comment); R22
mesh straps are all on 8.64k lanes (CHECKED below) = a clock strap takes a VSS lane, shielded by the VDD stripes at +-4.32.
R3b rule: each island's die drop = the crossing of a die M9 strap x = x0+U and M8 strap y = y0+V (MX: y0+H-V), U, V = the
8.64 multiples INSIDE the island's 8.64 footprint; a straight stacked via M9->M8->M7->M6->M5 at that crossing is the island
feed port (M5).  No die stub (length 0); inside the island the driver input wire is core M5/M4 <= |dU|+|dV|.
usage: a0_clk_r3b.py R3PLAN FLOORPLAN PLAN_D43 R2_D43 PLAN_D51 R2_D51 OUTDIR"""
import bisect, json, os, sys
R3P, FP, PD, RD, P51, R51, OUT = sys.argv[1:8]
G, ISL, HALO, CW, CH = 8.64, 4.32, 5.4, 457.92, 1157.76
os.makedirs(OUT, exist_ok=True)
r3 = json.load(open(R3P))
fp = json.load(open(FP))
ism = lambda v: abs(v / G - round(v / G)) < 1e-6


def kids(core):
    return [(c["at"][0], c["at"][1], c["at"][0] + c["size_um"][0], c["at"][1] + c["size_um"][1], c["view"]) for c in fp[core]["hard_children"]]


def legal(core, x, y):
    if x - ISL < 0 or y - ISL < 0 or x + ISL > CW or y + ISL > CH:
        return False
    return not any(x - ISL < k[2] + HALO and x + ISL > k[0] - HALO and y - ISL < k[3] + HALO and y + ISL > k[1] - HALO for k in kids(core))


def snap_island(core, x, y):
    """centre kept if a lattice point lies strictly inside the footprint; a tie (point on the edge) moves the centre by
    2.16 toward that point (re-checked for legality)."""
    out = []
    for v in (x, y):
        lo, hi = v - ISL, v + ISL
        cand = [k * G for k in range(int(lo // G), int(hi // G) + 2) if lo - 1e-6 <= k * G <= hi + 1e-6]
        c = min(cand, key=lambda q: (abs(q - v), q))
        out.append(c)
    cx, cy = x, y
    if abs(out[0] - x) > ISL - 1e-6:
        cx = x + (out[0] - x) / 2
    if abs(out[1] - y) > ISL - 1e-6:
        cy = y + (out[1] - y) / 2
    assert legal(core, cx, cy), (core, x, y, cx, cy)
    return (round(cx, 3), round(cy, 3)), (round(out[0], 3), round(out[1], 3))


tab = {}
for core in ("nk", "nl"):
    for n, v in r3["cores"][core]["islands"].items():
        c, U = snap_island(core, *v["xy"])
        t = tab.setdefault(n, dict(r3_centre=v["xy"], where=v["where"]))
        t.setdefault("by_core", {})[core] = dict(centre=list(c), drop=list(U))
for n, t in tab.items():
    a = t["by_core"]["nk"]; b = t["by_core"]["nl"]
    assert a == b, n
    t["centre"], t["drop_core_frame"] = a["centre"], a["drop"]
    t["d_um"] = [round(t["drop_core_frame"][0] - t["centre"][0], 3), round(t["drop_core_frame"][1] - t["centre"][1], 3)]
    t["island_wire_um"] = round(abs(t["d_um"][0]) + abs(t["d_um"][1]), 3)
    t["moved_from_r3_um"] = round(abs(t["centre"][0] - t["r3_centre"][0]) + abs(t["centre"][1] - t["r3_centre"][1]), 3)
    t["drop_form"] = "die M9 strap x=x0+U (VSS lane) x die M8 strap y=y0+V | y0+H-V (VSS lane) -> stacked via M9-M8-M7-M6-M5 at the crossing = island feed port M5; die stub 0"
    del t["by_core"]
XL = sorted({t["drop_core_frame"][0] for t in tab.values()}); YL = sorted({t["drop_core_frame"][1] for t in tab.values()})
assert all(ism(u) for u in XL) and all(ism(v) for v in YL) and ism(CH)


def instances(P):
    p = json.load(open(P)); pt = p["partition_types"]; out = []
    for part in p["partitions"]:
        t = pt[part["type"]]; PW, PH = t["outline_um"]; ox, oy = part["origin_um"]; o = part.get("orient", "R0")
        for c in t.get("contents", []):
            if c["module"].endswith("romleaf_rpf"):
                cx, cy = c["origin_um"]
                out.append(dict(n=part["name"] + "/" + c["inst"], m=c["module"], x0=round(ox + cx, 3),
                                y0=round(oy + (cy if o == "R0" else PH - cy - CH), 3), mx=o == "MX"))
    return out, p["die"]["pg"]


def near(v, a):
    i = bisect.bisect_left(a, v)
    return min(abs(v - a[j]) for j in (i - 1, i) if 0 <= j < len(a))


rep = dict(schema="qc_cores_1027.a0_clk_r3b.v1", rule=__doc__, islands=tab, type_lattice=dict(m9_u=XL, m8_v=YL), lattices={})
for tag, P, R in (("R22_d43_PROVISIONAL", PD, RD), ("R23_d51_candidate", P51, R51)):
    inst, pg = instances(P)
    r = json.load(open(R)); xs, ys = sorted(r["xs"]), sorted(r["ys"])
    reqx = sorted({round(i["x0"] + u, 3) for i in inst for u in XL})
    reqy = sorted({round(i["y0"] + (CH - v if i["mx"] else v), 3) for i in inst for v in YL})
    sx, sy = set(reqx), set(reqy)
    per, bad, onvss = [], [], True
    for i in inst:
        pts = [(round(i["x0"] + t["drop_core_frame"][0], 3), round(i["y0"] + (CH - t["drop_core_frame"][1] if i["mx"] else t["drop_core_frame"][1]), 3)) for t in tab.values()]
        n_cross = sum(1 for X, Y in pts if X in sx and Y in sy)
        onvss &= all(ism(X) and ism(Y) for X, Y in pts)
        n_r22 = sum(1 for X, Y in pts if near(X, xs) < 1e-3 and near(Y, ys) < 1e-3)
        per.append(dict(n=i["n"], m=i["m"], x0=i["x0"], y0=i["y0"], mx=i["mx"], r3b_crossings=n_cross, r22_crossings_at_islands=n_r22,
                        r22_m9_over_core=sum(1 for X in xs if i["x0"] <= X <= i["x0"] + CW)))
        if n_cross != len(tab):
            bad.append(i["n"])
    strapless = [q for q in per if q["r22_m9_over_core"] == 0]
    # alternative: keep the R22 lattice and ADD the drop straps (full-span straps; length = mesh span)
    yspan, xspan = ys[-1] - ys[0], xs[-1] - xs[0]
    add_m9 = [x for x in reqx if near(x, xs) > 1e-3]; add_m8 = [y for y in reqy if near(y, ys) > 1e-3]
    out_span = dict(m9_west_of_span=[x for x in reqx if x < xs[0]], m8_outside_span=[y for y in reqy if y < ys[0] or y > ys[-1]])
    sl_x = sorted({round(q["x0"] + u, 3) for q in strapless for u in XL})
    rep["lattices"][tag] = dict(
        plan_sha256=r.get("plan_sha256"), pg_grid=pg, r22_xs_on_8p64=all(ism(x) for x in xs),
        r22_ys_on_8p64=all(ism(round(y, 3)) for y in ys), r22_ys_off_lane=[round(y, 3) for y in ys if not ism(round(y, 3))],
        n_instances=len(inst), every_instance_22_crossings_under_r3b=not bad, instances_short=bad,
        all_drops_on_vss_lanes_both_orients=onvss, crossings_hist_r3b=sorted({q["r3b_crossings"] for q in per}),
        r22_crossings_at_r3b_islands_max=max(q["r22_crossings_at_islands"] for q in per),
        strapless_under_r22=[{k: q[k] for k in ("n", "m", "x0", "y0", "mx", "r3b_crossings")} for q in strapless],
        plan_delta_rephase=dict(m9=len(reqx), m8=len(reqy), r22_m9=len(xs), r22_m8=len(ys),
                                note="replace the R22 straps over the A0 field by the A0-commensurate drop straps; the die owner keeps/adds "
                                     "density straps in the inter-row bands and outside A0 (its call)"),
        alt_keep_r22_add_straps=dict(add_m9=len(add_m9), add_m8=len(add_m8), add_m9_mm=round(len(add_m9) * yspan / 1000, 1),
                                     add_m8_mm=round(len(add_m8) * xspan / 1000, 1),
                                     r22_mesh_mm=round((len(xs) * yspan + len(ys) * xspan) / 1000, 1), outside_span=out_span,
                                     strapless_only_m9=sl_x,
                                     note="full-span straps (UNCHECKED cost proxy = wire length; cap/power scale with it); the 16 strap-less "
                                          "cores alone need the 4 W-column M9 straps listed, but the other 752 still have 0 islands on R22 crossings"),
        per_instance=per)
json.dump(rep, open(os.path.join(OUT, "a0_clk_r3b.json"), "w"), indent=1)
print("islands", len(tab), "XL", XL, "YL", YL)
print("max island wire", max(t["island_wire_um"] for t in tab.values()), "max centre move", max(t["moved_from_r3_um"] for t in tab.values()))
for tag, L in rep["lattices"].items():
    print(tag, {k: L[k] for k in ("n_instances", "every_instance_22_crossings_under_r3b", "all_drops_on_vss_lanes_both_orients",
                                  "crossings_hist_r3b", "r22_crossings_at_r3b_islands_max", "r22_xs_on_8p64", "r22_ys_on_8p64", "r22_ys_off_lane")})
    print("  strapless", len(L["strapless_under_r22"]), "rephase", L["plan_delta_rephase"]["m9"], L["plan_delta_rephase"]["m8"],
          "alt", {k: v for k, v in L["alt_keep_r22_add_straps"].items() if k not in ("note", "outside_span")}, "outside", {k: len(v) for k, v in L["alt_keep_r22_add_straps"]["outside_span"].items()})
