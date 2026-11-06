#!/usr/bin/env python3
"""HBM d44v part 41 (HBM-FORM-SPLIT-13-OPSB 11-06): ot_hgi_sfu_opsb_output banks -> 16 x ot_sram_1r1w_2048x32_m8_r0c0_g32.
Plan change = core_macros.json KNOWN rects of ot_hgi_sfu_opsb_output only (4 x 4, macro_placement_n32.json, the kit's
snapped origins); slot, outline, orient, pins table (ev74_tall 3379bbf2f6a7), clock entry, taps, conns, stations and
reset contract are unchanged.  Writes part41_event.json.     mk_p41.py PLAN_DIR"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); H = Path(__file__).resolve().parent
mp = json.loads((H / "macro_placement_n32_kit.json").read_text())["macro_placement"]
lef = (H.parents[2] / "physical/asap7_memory_macros_v2/ot_sram_1r1w_2048x32_m8_r0c0_g32/ot_sram_1r1w_2048x32_m8_r0c0_g32.lef").read_text()
import re
W, Hh = map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", lef).groups())
cm = json.loads((d / "core_macros.json").read_text()); M = "ot_hgi_sfu_opsb_output"; e = cm["cores"][M]
old = [(q["master"], q["rect_um"]) for q in e["macros"]]
e["macros"] = [dict(name=f"u_fcore.u_g.g_bank[{m['k']}].u_b.g_m11n.u_m", master=m["macro"], orient=m.get("orient", "R0"),
                    rect_um=[m["origin_um"][0], m["origin_um"][1], round(m["origin_um"][0] + W, 3), round(m["origin_um"][1] + Hh, 3)])
               for m in sorted(mp, key=lambda m: m["k"])]
e["basis"] = "d44v part 41 (HBM-FORM-SPLIT-13-OPSB): OT_OPSB_N32 4x4 narrow-macro banks, kit-snapped origins"
ox, oy, x1, y1 = 4.32, 4.32, e["outline_um"][0] - 4.32, e["outline_um"][1] - 4.32
for q in e["macros"]:
    r = q["rect_um"]; assert ox <= r[0] and oy <= r[1] and r[2] <= x1 and r[3] <= y1, q
for i, a in enumerate(e["macros"]):
    for b in e["macros"][i + 1:]:
        ra, rb = a["rect_um"], b["rect_um"]
        assert ra[2] + 8.64 <= rb[0] or rb[2] + 8.64 <= ra[0] or ra[3] + 8.64 <= rb[1] or rb[3] + 8.64 <= ra[1], (a, b)
(d / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
area = lambda L: round(sum((r[2] - r[0]) * (r[3] - r[1]) for _, r in L), 1)
ev = dict(schema="opentallas.hbm_plan_event.v1", part=41, plan="d44v", lane="HBM-FORM-SPLIT-13-OPSB", date="2026-11-06",
          what="ot_hgi_sfu_opsb_output (q_b113 / q_b113__physical_v1 u_sfucore_Q_opstore_b__o, MX, slot 760.32x280.8 at "
               "(656.64, 388.8)): bank macros 16 x ot_sram_1r1w_256x256_m2_r2c2 (823 pins) -> 16 x "
               "ot_sram_1r1w_2048x32_m8_r0c0_g32 (90 signal pins), RTL define OT_OPSB_N32 (recipe ot_hgi_sfu_opsb_output)",
          why="the 256-bit-row bank macros GRT-overflow on every placement in the slot (B11 4 columns 143,100; vA 3 "
              "columns 506); the ruled 2 x 8-bank split in the same slot repeats the B11 4-column geometry (estimate "
              "est_split.txt, ASK 13:29 default)",
          unchanged=["die_plan.json (slot, outline, orient, pins table 3379bbf2f6a7)", "core_conns", "clock_entries",
                     "stations", "reset_contract", "PIN CYCLES 0 (same latency, lock-step bench every output every cycle)"],
          core_macros=dict(module=M, old_masters=sorted({m for m, _ in old}), new_masters=sorted({q["master"] for q in e["macros"]}),
                           old_macro_area_um2=area(old), new_macro_area_um2=area([(q["master"], q["rect_um"]) for q in e["macros"]]),
                           placement="results/die_hbm_1106/opsb_n32/macro_placement_n32_kit.json (kit-snapped; input macro_placement_n32.json)"),
          rtl=dict(files=["rtl/hbm_accel/cores_split/reform_1105s/opstore/ot_hgi_su_lbank_n32.sv",
                          "rtl/hbm_accel/cores_split/reform_1105s/opstore/ot_hgi_su_lgroup2_lf.sv (ifdef only)"],
                   bench="results/die_hbm_1106/opsb_n32/BENCH.txt", macro_gen="results/die_hbm_1106/opsb_n32/macro_gen.py"),
          recipes=dict(ot_hgi_sfu_opsb_output="OT_OPSB_N32 form", ot_hgi_sfu_opsb_output__row256="old form (fallback)"))
(d / "part41_event.json").write_text(json.dumps(ev, indent=1) + "\n"); print("part41", ev["core_macros"])
