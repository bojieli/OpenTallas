#!/usr/bin/env python3
"""DIE-HBM-82-EP6 d44v part 48 (plan-owner approved DIE-HBM-82): ot_wbq_root payload banks -> one-mask-pin master.

Run from the repo root: python3 -I results/die_hbm_1106/wbq_n1m/mk_p48.py SRC_COMMIT
 - core_macros.json cores.ot_wbq_root: 8 x ot_sram_1r1w_128x256_m1_r2c2 (94.824 x 41.04 rects) -> ot_sram_1r1w_128x256_m1_r0c0_g256
   (91.8 x 27.576), same lower-left origins, same orient;
 - recipes_b2.json: ot_wbq_root gets define OT_WBQ_N1M + the new master (source_commit SRC_COMMIT); the old form is kept as
   ot_wbq_root__r2c2;
 - part48_event.json, README paragraph, SHA256SUMS rows.
"""
import hashlib, json, sys
from pathlib import Path
SRC = sys.argv[1]
D = Path("physical/die_plan/hbm/plan_of_record/d44v"); OLD, NEW, NW, NH = "ot_sram_1r1w_128x256_m1_r2c2", "ot_sram_1r1w_128x256_m1_r0c0_g256", 91.8, 27.576
cm = json.loads((D / "core_macros.json").read_text()); c = cm["cores"]["ot_wbq_root"]
assert len(c["macros"]) == 8 and all(m["master"] == OLD for m in c["macros"])
for m in c["macros"]:
    x, y = m["rect_um"][:2]; m["master"] = NEW; m["rect_um"] = [x, y, round(x + NW, 3), round(y + NH, 3)]
c["basis"] += "; d44v part 48 (DIE-HBM-82-EP6): payload master -> " + NEW + " (OT_WBQ_N1M), same origins"
(D / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
rp = Path("physical/die_plan/hbm_arch_cores/recipes_b2.json"); r = json.loads(rp.read_text())
old = dict(r["ot_wbq_root"]); r["ot_wbq_root__r2c2"] = dict(old, source=old["source"] + "; kept as the fallback r2c2 payload form by d44v part 48")
r["ot_wbq_root"] = dict(old, defines=["OT_WBQ_N1M"], macros=[NEW], source_commit=SRC,
    source=old["source"] + "; DIE-HBM-82-EP6 d44v part 48: OT_WBQ_N1M one-mask-pin payload (8 x " + NEW + ", 530 pins, was 819), lock-step bench results/die_hbm_1106/wbq_n1m (0 errors x 3 seeds, 4/4 mutants FAIL), PIN CYCLES 0")
rp.write_text(json.dumps(r, indent=2) + "\n")
ev = {"schema": "opentallas.hbm_plan_event.v1", "part": 48, "plan": "d44v", "lane": "DIE-HBM-82-EP6", "date": "2026-11-06",
      "approved": "plan-owner DIE-HBM-82 16:1x (wbq_root narrow-pin SRAM form, PART 41 pattern)",
      "what": "ot_wbq_root (16 inst, 432x129.6, q_hub_nw/ne u_wbk_Q__q{0,1}__r{0..3}): payload macros 8 x " + OLD + " (94.824x41.064, 819 signal pins) -> 8 x " + NEW + " (91.8x27.576, 530 signal pins), RTL define OT_WBQ_N1M (recipe ot_wbq_root)",
      "why": "both HG7 kits (vA PD 0.45, vB PD 0.38) GRT-0116 at M2 114% / total 92%, effective util 0.753; growth of the slot needs neighbour moves (q1 boxed by xload bfqg, aq_tree13, fused_lane_11); the r2c2 master carries a 256-bit mask tied to ones and repair ports tied 0",
      "unchanged": ["die_plan.json (slots, outlines, orient, pins table be03cffe8be6)", "core_conns", "clock_entries", "stations", "reset_contract", "PIN CYCLES 0 (lock-step bench, every output every edge)"],
      "core_macros": {"module": "ot_wbq_root", "old_masters": [OLD], "new_masters": [NEW], "old_macro_area_um2": round(8 * 94.824 * 41.064, 1), "new_macro_area_um2": round(8 * NW * NH, 1), "placement": "same lower-left origins, 2 rows x 4"},
      "rtl": {"files": ["rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv (ifdef only)"], "bench": "results/die_hbm_1106/wbq_n1m/BENCH.txt", "source_commit": SRC}}
(D / "part48_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"; t = rd.read_text()
para = "\nEvent part 48 (DIE-HBM-82-EP6 11-06, plan-owner approved DIE-HBM-82): ot_wbq_root (16 instances) payload banks 8 x " + OLD + " (819 pins) -> 8 x " + NEW + " (91.8 x 27.576, 530 pins: one mask pin, no repair), RTL define OT_WBQ_N1M; core_macros rects resized at the same origins; slots, pin tables and stations unchanged; PIN CYCLES 0; part48_event.json; bench results/die_hbm_1106/wbq_n1m.\n"
if "Event part 48" not in t: rd.write_text(t.rstrip("\n") + "\n" + para)
L = [l.split(None, 1) for l in (D / "SHA256SUMS").read_text().splitlines() if l.strip()]
cur = {n: hashlib.sha256((D / n).read_bytes()).hexdigest() for n in ("core_macros.json", "part48_event.json", "README.md")}
names = [n for _, n in L]
for i, (a, n) in enumerate(L):
    if n in cur: L[i] = [cur[n], n]
L += [[cur[n], n] for n in cur if n not in names]
(D / "SHA256SUMS").write_text("".join(f"{a}  {n}\n" for a, n in L)); print("PART 48 written", cur)
