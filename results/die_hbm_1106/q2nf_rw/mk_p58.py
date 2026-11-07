#!/usr/bin/env python3
"""HBM d44v part 58 (DIE-HBM-83-Q2R 11-06): ot_q2nf_rest core_macros -> right-width masters at the rects of a kit layout.
Slot, outline, pins table, conns, clock entry, stations, reset contract unchanged; PIN CYCLES 0.
    mk_p58.py PLAN_DIR KIT_MACRO_PLACEMENT_TCL   (the tcl of the build that won; writes core_macros.json + part58_event.json)"""
import json, re, sys
from pathlib import Path
d, tcl = Path(sys.argv[1]), Path(sys.argv[2]).read_text()
SZ = {"ot_sram_1r1w_64x141_m1_r0c0_g141": (56.184, 20.808), "ot_sram_1r1w_256x256_m2_r0c0_g256": (169.368, 28.392), "ot_sram_1rw_256x64_m4_r2c2": (66.312, 17.832)}
rows = re.findall(r"\{(\S+)\}\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)\s*$", tcl, re.M); assert len(rows) == 19
cm = json.loads((d / "core_macros.json").read_text()); M = "ot_q2nf_rest"; e = cm["cores"][M]; old = e["macros"]
names = {q["name"] for q in old}
new = []
for n, m, x, y, o in rows:
    n = n.replace("\\", ""); x, y = float(x), float(y); w, h = SZ[m]; assert n in names, n
    new.append(dict(name=n, master=m, orient=o, rect_um=[x, y, round(x + w, 3), round(y + h, 3)]))
assert {q["name"] for q in new} == names
W, H = e["outline_um"]
for q in new:
    r = q["rect_um"]; assert 4.32 <= r[0] and 4.32 <= r[1] and r[2] <= W - 4.32 and r[3] <= H - 4.32, q
for i, a in enumerate(new):
    for b in new[i + 1:]:
        ra, rb = a["rect_um"], b["rect_um"]
        assert ra[2] + 8.64 <= rb[0] or rb[2] + 8.64 <= ra[0] or ra[3] + 8.64 <= rb[1] or rb[3] + 8.64 <= ra[1], (a, b)
area = lambda L: round(sum((q["rect_um"][2] - q["rect_um"][0]) * (q["rect_um"][3] - q["rect_um"][1]) for q in L), 1)
e["macros"] = new; e["basis"] = "d44v part 58 (DIE-HBM-83-Q2R): OT_Q2NF_RW right-width masters"
(d / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
ev = dict(schema="opentallas.hbm_plan_event.v1", part=58, plan="d44v", lane="DIE-HBM-83-Q2R", date="2026-11-06",
          what="ot_q2nf_rest: 8 x ot_sram_1r1w_64x512_m1_r2c2 -> ot_sram_1r1w_64x141_m1_r0c0_g141, 6 x ot_sram_1r1w_256x256_m2_r2c2 -> ot_sram_1r1w_256x256_m2_r0c0_g256, RTL define OT_Q2NF_RW",
          why="GRT probe on the old vA 4_cts.odb: overflow 469,484, over the macro walls; 9,341 of 18,761 macro pins tied, 3,259 outputs unread",
          unchanged=["die_plan.json (slot, outline, pins table)", "core_conns", "clock_entries", "stations", "reset_contract", "PIN CYCLES 0"],
          core_macros=dict(module=M, old_macro_area_um2=area(old), new_macro_area_um2=area(new)),
          rtl=dict(files=["rtl/hbm_accel/cores_split/reform_1105b/ot_q2nf_rest.sv (ifdef only)"], patch="results/die_hbm_1106/q2nf_rw/patch_rw.py", bench="results/die_hbm_1106/q2nf_rw/bench_rw.sh"),
          recipes=dict(ot_q2nf_rest="OT_Q2NF_RW form", ot_q2nf_rest__r2c2="old form (fallback)"))
(d / "part58_event.json").write_text(json.dumps(ev, indent=1) + "\n"); print("part58", ev["core_macros"])
