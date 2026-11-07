#!/usr/bin/env python3
"""HBM-FORM-SPLIT-14-OPSB: GPL guide boxes (gen_core_kit_hbm.py --reg-guide-boxes) for ot_hgi_sfu_opsb_output in the
ot_hgi_su_lgroup2_wp form, derived from the part 41 kit macro placement (16 x ot_sram_1r1w_2048x32_m8_r0c0_g32, 4 x 4,
bank b = column b // 4, row b % 4).
  bk<b>  : bank b's input regs + read reg (u_g.g_bank[b].*) around its macro: macro bbox + GROW um in x and at the outer
           rows, half the 19.4 um row gap between rows (disjoint by construction).
  col<c> : column c's kept copy (u_g.g_col[c].*) in the channel east of the column (between the column's bank boxes
           and the next column's), centre rows.
  fc / fq: control copy (u_g.g_fc.*) and the sr_d-face read-word copy (u_g.g_fq.*) in the west channel by the
           sr_* / flt / sr_d pins (W face, y 1..198).
usage: guide_boxes.py MACRO_PLACEMENT_KIT_JSON OUT_JSON"""
import json, sys
W_, H_ = 92.664, 43.752                     # ot_sram_1r1w_2048x32_m8_r0c0_g32 LEF size
CORE = (4.32, 4.32, 756.0, 276.48)
GROW, P = 12.0, "u_fcore.u_g."
mp = {m["k"]: m for m in json.load(open(sys.argv[1]))["macro_placement"]}
assert sorted(mp) == list(range(16)) and all(m["orient"] == "R0" for m in mp.values())
rect = {k: (m["origin_um"][0], m["origin_um"][1], m["origin_um"][0] + W_, m["origin_um"][1] + H_) for k, m in mp.items()}
for k in range(16):   # bank b sits in column b // 4, row b % 4 (columns left to right, rows bottom to top)
    c, r = k // 4, k % 4
    assert abs(rect[k][0] - rect[4 * c][0]) < 1e-6 and abs(rect[k][1] - rect[r][1]) < 1e-6
    if c: assert rect[k][0] > rect[4 * (c - 1)][2]
    if r: assert rect[k][1] > rect[k - 1][3]
boxes = []
for k in range(16):
    c, r = k // 4, k % 4
    x0, y0, x1, y1 = rect[k]
    lo = GROW if r == 0 else (y0 - rect[k - 1][3]) / 2 - 0.05
    hi = GROW if r == 3 else (rect[k + 1][1] - y1) / 2 - 0.05
    boxes.append(dict(name=f"bk{k}", prefixes=[f"{P}g_bank[{k}]."],
                      box_um=[max(CORE[0], x0 - GROW), max(CORE[1], y0 - lo), min(CORE[2], x1 + GROW), min(CORE[3], y1 + hi)]))
ymid0, ymid1 = rect[1][1] - 26.0, rect[2][3] + 26.0          # centre rows band
for c in range(4):
    xa = rect[4 * c][2] + GROW + 4.0
    xb = (rect[4 * (c + 1)][0] - GROW - 4.0) if c < 3 else CORE[2] - 6.0
    boxes.append(dict(name=f"col{c}", prefixes=[f"{P}g_col[{c}]."], box_um=[xa, ymid0, xb, ymid1]))
xw1 = rect[0][0] - GROW - 4.0
boxes.append(dict(name="fc", prefixes=[f"{P}g_fc."], box_um=[CORE[0] + 2.0, CORE[1] + 1.0, xw1, 60.0]))
boxes.append(dict(name="fq", prefixes=[f"{P}g_fq."], box_um=[CORE[0] + 2.0, 61.0, xw1, 205.0]))
for b in boxes: b["box_um"] = [round(v, 3) for v in b["box_um"]]
json.dump(dict(schema="hbm-form-split-14-opsb.reg_guide_boxes.v1", source="results/die_hbm_1106/opsb_wp/guide_boxes.py",
               boxes=boxes), open(sys.argv[2], "w"), indent=1)
for b in boxes: print(b["name"], b["box_um"])
