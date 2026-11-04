#!/usr/bin/env python3
"""S81 rom_q g_mac RE-FORM (DIE-S81-56 11-04): spec + LEF pin contract of hard core ot_v41_rom_mac (one half of rom_q, two ROMs).
Outline 233.28 x 198.72 in the rom_q frame 510.84 x 221.4: u_m[0] R0 at x 4.32, u_m[1] MY at x 273.24, y 10.8, parent logic in the
35.64 um centre strip and the two 6.5-7.6 um channels.  All 668 pins on the E face (the centre strip side after MY), M4 tracks."""
import json
from pathlib import Path
SPECS = Path("physical/die_plan/s81/cores/legacy/specs")
W, H = 233.28, 198.72
G = [("i2x_q0", 256, "INPUT"), ("i2x_e0", 10, "INPUT"), ("i1_v", 1, "INPUT"), ("i1_bk", 1, "INPUT"), ("i1_bf", 1, "INPUT"), ("i1_t", 17, "INPUT"),
     ("issue", 1, "INPUT"), ("a_ctr", 13, "INPUT"), ("rst_n_pin", 1, "INPUT"), ("clk", 1, "INPUT"), ("cg_en", 1, "INPUT"), ("wen_t", 1, "INPUT"),
     ("pq_tree", 4, "OUTPUT"), ("pq_pos", 3, "OUTPUT"), ("pq_idle", 1, "INPUT"), ("pq_row", 16, "INPUT"), ("pq_idx", 5, "INPUT"), ("pq_n", 5, "INPUT"),
     ("qy_bkf", 1, "OUTPUT"), ("pv", 1, "OUTPUT"), ("pval", 32, "OUTPUT"), ("prow", 16, "OUTPUT"), ("pseg", 5, "OUTPUT"), ("pnseg", 5, "OUTPUT"),
     ("perr", 1, "OUTPUT"), ("ppos", 3, "OUTPUT"), ("i2x_e1", 10, "INPUT"), ("i2x_q1", 256, "INPUT")]
pins = [(n if w == 1 else f"{n}[{i}]", d) for n, w, d in G for i in range(w)]
assert len(pins) == 668, len(pins)
PITCH, OFF = 0.048, 0.012
step = 5                            # 0.24 um: 668 pins span 160 um, centred on the face
k0 = round((H / 2 - (len(pins) - 1) * step * PITCH / 2 - OFF) / PITCH)
rows = []
for i, (n, d) in enumerate(pins):
    y = round(OFF + (k0 + i * step) * PITCH, 3)
    rows.append((n, d, y))
L = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", "MACRO ot_v41_rom_mac", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;", "  FOREIGN ot_v41_rom_mac 0 0 ;",
     f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y R90 ;"]
for n, d, y in rows:
    use = "CLOCK" if n == "clk" else "SIGNAL"
    L += [f"  PIN {n}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT", "      LAYER M4 ;",
          f"        RECT {W-0.084:.3f} {y-0.012:.3f} {W:.3f} {y+0.012:.3f} ;", "    END", f"  END {n}"]
L += ["END ot_v41_rom_mac", "END LIBRARY", ""]
v = SPECS / "ot_v41_rom_mac/views/ot_v41_rom_mac"; v.mkdir(parents=True, exist_ok=True)
(v / "ot_v41_rom_mac.lef").write_text("\n".join(L))
par = json.load(open(SPECS / "ot_v41_rom_elem_q_qxpq_w10/spec.json"))
drop = {"physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v", "rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv", "rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv", "rtl/v41rom/ot_v41_elem_pq_tags.sv", "rtl/v41rom/ot_v41_rom_elem_w10.sv"}
ms = dict(par)
ms.update(top="ot_v41_rom_mac", sources=["rtl/v41rom/ot_v41_rom_mac.sv"] + [s for s in par["sources"] if s not in drop], params={}, defines=[],
          clock_port="clk", reset_ports=["rst_n_pin"],
          macros=[dict(par["macros"][0], count=2, at=[21.6, 32.592], orient="R180")], route={"pd": 0.45}, children=[],
          notes="DIE-S81-56 11-04 RE-FORM (COORD order): one rom_q g_mac half as hard core, 0 cycles, LEC MACHARD 1 vs 0.  Outline 233.28x198.72; ROMs at (21.6, 32.592) R180 and (21.6, 104.208) MY, the same y phase as the flat rom_q.",
          provenance="rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv g_mac")
(SPECS / "ot_v41_rom_mac/spec.json").write_text(json.dumps(ms, indent=1) + "\n")
pp = dict(par)
pp.update(sources=par["sources"] + ["rtl/v41rom/ot_v41_rom_mac.sv"], params=dict(par["params"], MACHARD=1, OLAT=0, IFN=1), macros=[],
          children=[dict(view=str(v), inst="u_e.g_mh.g_m[0].u_m", at=[4.32, 10.8], orient="R0"),
                    dict(view=str(v), inst="u_e.g_mh.g_m[1].u_m", at=[273.24, 10.8], orient="MY")],
          notes="DIE-S81-56 11-04 RE-FORM: rom_q with hard children ot_v41_rom_mac (MACHARD 1), plan outline and pins unchanged.")
d = SPECS / "ot_v41_rom_elem_q_qxpq_w10_mh"; d.mkdir(exist_ok=True)
(d / "spec.json").write_text(json.dumps(pp, indent=1) + "\n")
rec = {"ot_v41_rom_elem_q_qxpq_w10_gb": {"ref_tile": str(d), "suffix": "mh1",
                                         "why": "S81 rom_q g_mac RE-FORM parent (DIE-S81-56 11-04): children must be SIGNED first"},
       "ot_v41_rom_mac": {"child_of": "ot_v41_rom_elem_q_qxpq_w10_gb", "ref_tile": str(SPECS / "ot_v41_rom_mac"), "lef_contract": str(v / "ot_v41_rom_mac.lef"),
                          "rtl_dirs": True, "util": 0.45, "suffix": "f1",
                          "macro_sites": {"ot_rom_4096x274_m8": [[21.6, 32.592, "R180"], [21.6, 104.208, "MY"]]},
                          "why": "S81 rom_q g_mac RE-FORM child (DIE-S81-56 11-04, COORD): 2 ROMs, about 96k cells, registered faces except issue/a_ctr to ROM"}}
Path("physical/die_plan/s81/cores/legacy/recipes_rommac_1104.json").write_text(json.dumps(rec, indent=1) + "\n")
print(len(rows), rows[0][2], rows[-1][2])
