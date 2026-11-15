#!/usr/bin/env python3
"""QC-HC-STRIP-1115: deepen the b_hw_i landing band of sle/slw hc1 + hc2 types under its S-face pin span so that
budgets.cland_strip_density_types (target 0.45 FIRM flops/um2) is not clamped by band depth ("band fits 1").
usage: gen_hc_strip.py BASE_PLAN OUT_ROWS OUT_PLAN [--dens 0.45]"""
import json, sys, math, copy
base, out_rows, out_plan = sys.argv[1:4]
DENS = 0.45
text = open(base).read(); plan = json.loads(text); pt = plan["partition_types"]
G = 2.16; rows = {}; rep = []
def ov(a, b, g=1.0):
    return min(a[2], b[2]) + g > max(a[0], b[0]) and min(a[3], b[3]) + g > max(a[1], b[1])
for tn, t in pt.items():
    if not tn.startswith(("sle_hc1", "slw_hc1", "sle_hc2", "slw_hc2")): continue
    lc = t["clock"]["landing_contract"]; bands = lc["bands"]; old = bands["b_hw_i"]
    win = next(b for b in t["buses"] if b["name"] == "b_hw_i")["window_um"]
    n = old["ring_width"] * 5.564  # ring flops incl. control at the measured 8902 for ring 1600
    n = 8902 * old["ring_width"] / 1600.0
    need_area = n / DENS
    others = [v["rect_um"] for k, v in bands.items() if k != "b_hw_i" and v.get("rect_um")]
    y0 = old["rect_um"][1]; W = t["outline_um"][0]
    xb = math.floor(min(win[1], W - 17.28) / G) * G
    xa0 = max(17.28, math.ceil(win[0] / G) * G); best = None
    while xb > xa0 + 250 and not best:
        xa = xa0
        while xa < xb - 150:
            d = math.ceil(need_area / (xb - xa) / G) * G
            box = [xa, y0, xb, y0 + d]
            if not any(ov(box, o, 1.5) for o in others) and y0 + d < 89.0:
                best = box; break
            xa += G
        xb -= G
    if not best: rep.append((tn, "NO FIT")); continue
    px = sum(win) / 2
    hop = max(abs(x - px) + abs(y) for x in (best[0], best[2]) for y in (best[1], best[3]))
    nb = copy.deepcopy(old)
    nb["rect_um"] = [round(v, 6) for v in best]
    nb["area_reserve_um2"] = round((best[2]-best[0])*(best[3]-best[1]), 3)
    nb["max_pin_to_band_hop_um"] = round(hop, 3)
    nb["resized_from_um"] = list(old["rect_um"])
    nb["resize"] = "QC-HC-STRIP-1115 F1: b_hw_i strip depth under its S-face pin span for cland_strip_density 0.45 (band fits 1 at 24 um)"
    assert hop <= 403
    bands["b_hw_i"] = nb
    rows[tn] = {"clock.landing_contract.bands.b_hw_i": nb}
    rep.append((tn, old["rect_um"], nb["rect_um"], round(hop, 1), round(nb["area_reserve_um2"])))
dens = dict(plan["budgets"].get("cland_strip_density_types") or {})
for b in ("sle_hc1", "slw_hc1", "sle_hc2", "slw_hc2"): dens[b] = DENS
plan["budgets"]["cland_strip_density_types"] = dens
json.dump({"lane": "QC-HC-STRIP-1115", "rows": rows,
           "die_rows": {"budgets.cland_strip_density_types": dens},
           "note": "rows = composed band edits (rows_apply refuses composed-only keys: apply with a plain deep-set, as gen_sc/gen_fe do)"},
          open(out_rows, "w"), indent=1)
open(out_plan, "w").write(json.dumps(plan, indent=1) + "\n")
for r in rep: print(r)
