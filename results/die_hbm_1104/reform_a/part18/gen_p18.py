#!/usr/bin/env python3
"""HBM-REFORM-A2 d44v part 18 inputs: lane_exp canon -> lane_exp_x + sfu_s, lane_exp0_id -> lane_full_x + sfu_s.
    gen_p18.py REPO KIT_CANON_RTL KIT_ID_RTL OUT     writes glue + conn + split_p18.json into OUT
Tile 319.68 + 120.96 = 440.64 x 207.36, abutted; the S-chain seam is 36 in, 65 out, each with its face flops."""
import json, subprocess, sys
from pathlib import Path
repo, kc, ki, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
RX = repo / "rtl/hbm_accel/cores_split/reform_1104a/lane_x"; R = repo / "results/die_hbm_1103/reform/split_p6"; SFU = "ot_hbm_su_pg_sfu_s_core"
ROWS = dict(canon=("ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691", kc, "ot_hbm_su_pg_lane_exp_core", "ot_hbm_su_pg_lane_exp_x_core", 120923),
            id=("ot_hbm_su_static_pgslice_lg__lane_exp0_id", ki, "ot_hbm_su_pg_lane_full_core", "ot_hbm_su_pg_lane_full_x_core", 144022))
M, MW, MH = "ot_sram_1r1w_128x256_m1_r2c2", 94.824, 41.064
X = (34.56, 190.08); Y = (20.52, 83.16, 145.8)    # 2 x 3 grid in the 319.68 x 207.36 tile. Macro pins are W/E on M4: mid channel 60.7 holds 6 macro edges, end bands 30.2 and 30.4 hold 3 (A3, class of the lane1p GRT-0116: a 10.8 channel for 6 edges starves). Row channels 21.576
macs = [dict(name=f"u_core.u_bank.u_data.g_read[{i}].u_m", master=M, orient="R0", rect_um=[x, y, round(x + MW, 3), round(y + MH, 3)]) for i, (y, x) in enumerate((y, x) for y in Y for x in X)]
PRE = "u_fcore.u_core."; LW, SW, H = 319.68, 120.96, 207.36
spec = []
for k, (core, kit, base, x, cells) in ROWS.items():
    comp, sv = base + "__splitx", RX / f"{base}__splitx.sv"
    g = out / f"{core}__p18glue.sv"
    subprocess.run([sys.executable, "-I", str(R / "split_glue.py"), str(kit / f"{core}__wrap.sv"), base, comp, str(sv), str(g)], check=True)
    nj = out / f"{k}.netlist.json"
    subprocess.run(["bash", str(R / "netlist2.sh"), str(nj), core, str(g), str(sv), str(RX / f"{x}.sv"), str(RX / f"{SFU}.sv")], check=True)
    subprocess.run([sys.executable, "-I", str(R / "split_conn.py"), str(nj), core, str(out / f"{k}.conn.json")], check=True)
    nj.unlink()
    spec.append(dict(core=core, sha="p18", part="p18", glue=g.name, conn=f"{k}.conn.json", subs=[dict(module=x, cells=cells), dict(module=SFU, cells=93105)],
                     added_cycles="SFU_EXP, SFU_SIGM, SFU_SILU +4 edges, S-chain fault +4; every other op and pin 0",
                     layout={PRE + "u_l": dict(xy=[0.0, 0.0], wh=[LW, H]), PRE + "u_s": dict(xy=[LW, 0.0], wh=[SW, H])},
                     clock_entry={x: [159.84, 73.44], SFU: [60.48, 103.68]}, macros={x: macs},
                     macro_basis="HBM-REFORM-A3 d44v part 18: 2 x 3 grid, W/E bands 30.2, 60.7, 30.4, row channels 21.576; clock entry in the first row channel"))
(out / "split_p18.json").write_text(json.dumps(spec, indent=1) + "\n")
print("wrote", out)
