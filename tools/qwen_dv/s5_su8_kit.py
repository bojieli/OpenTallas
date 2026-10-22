#!/usr/bin/env python3
"""s5_su8_kit.py -- QW-SU8 10-20: ref_tile specs of the slice2 SU control leaf qfd_dv_s5_su8_rst3
(rtl/qwen_dv/s5/qfd_dv_s5_su8_rst3.sv; Codex source e4f168a75 = SUVM7 control minus VM8 / BTAB payload).
No macros (VM8 group owns all SRAM), ONE CTS root (S-face ck), every pin registered in RTL, rst_n lands rs0 -> rs1 then
kept local reset leaves (raw reset contacts 2).  Pin-bound: 487 in (W) + 1058 out (pd1 768 N, gb/gv 247 E, misc 43 S).

  su8   qfd_dv_s5_su8   172.8 x 129.6   N 768/172.8 = 4.4/um  W 487/129.6 = 3.8/um  (main)
  su8b  qfd_dv_s5_su8b  216.0 x 108.0   N 768/216.0 = 3.6/um  W 487/108.0 = 4.5/um  (parallel fallback, flatter)

    python3 tools/qwen_dv/s5_su8_kit.py [su8 su8b]  -> tools/ref_tile/specs_qw_su8/<name>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ["rtl/qwen_dv/s5/qfd_dv_s5_su8.sv", "rtl/qwen_dv/s5/qfd_dv_s5_su8_rst3.sv"]
WDIR = "results/arch/qw_su8_1020/bench"
VL = "export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH && "
STD_AREA = 2895.37   # mapped ASAP7 RVT TT, results/arch/qw_su8_1020/native/mapped_stat.txt
PINS = {"W": ["start", "si", "l_retire", "l_last", "l_fault", "kv_we", "rd_v", "red_busy", "red_fault", "lvm_we"],
        "N": ["pd1"], "E": ["gb", "gv"],
        "S": ["rst_n", "lv1", "su_nr", "su_idle", "su_fault", "su_prog", "su_rows", "ck"]}
LEAF = {"su8": dict(w=172.8, h=129.6, what="main (172.8 x 129.6)"),
        "su8b": dict(w=216.0, h=108.0, what="parallel fallback, flatter (216 x 108): lower N/E density, S band longer")}
BENCH = "bash rtl/test/qwen_dv/s5/su8/bench.sh {RUN}/%s %d %d"


def spec(leaf):
    L = LEAF[leaf]
    w, h = L["w"], L["h"]
    name = f"qfd_dv_s5_{leaf}"
    faces = (f"N 768/{w} = {768 / w:.2f}/um, E 247/{h} = {247 / h:.2f}/um, W 487/{h} = {487 / h:.2f}/um, "
             f"S 45/{w} = {45 / w:.2f}/um")
    util = STD_AREA / (w * h)
    mut = lambda m, tag: {"name": f"su8_mut_{tag}", "cmd": VL + BENCH % (f"m{m}", m, 0), "expect": "fail",
                          "fail_regex": "SU8_EQ FAIL", "fail_witness": f"{WDIR}/run_{m}_0.log",
                          "threads": 8, "peak_ram_gb": 8, "needs": ["verilator"]}
    chk = {
        "1_pins": "PASS: RTL registers all 487 inputs and 1058 outputs at the pin (priced c_su 2 -> 6); rst_n lands "
                  "rs0 -> rs1 (2 raw reset contacts) then kept local leaves; resets only control/valid state (datapath "
                  "payload unreset, OWNER 09:05); no combinational pin arc (textbook in->reg/reg->out/in->out 0)",
        "2_reach": f"PASS (by floorplan): outline {w} x {h}, no wire can exceed {w + h:.0f} um; gate wire_reach checks 405",
        "3_fanout": "PASS: pre-gate mapped native census results/arch/qw_su8_1020/native: 0 drivers > 32, max 32, "
                    "20,460 roots, rst_n 2 loads (kept qfd_dv_su8_kff/kffr copies held: keep_hierarchy, census on flat map)",
        "4_depth": "PASS: mapped depth 470.1 ps / 15 lv (<= 600); stride multiples precomputed at accept, 24-bit "
                   "Kogge-Stone prefix add",
        "5_storage": "PASS: no dynamic table (VM/BTAB/PROG live in the VM8 group SRAMs); 4,655 FF all pipeline/control",
        "6_floorplan": f"PASS (pin-bound): no macros; aspect {max(w, h) / min(w, h):.2f}; full std-cell area; "
                       f"faces {faces}; util {util:.1%} (fill_reason pin_bound)",
        "7_clock": "ONE CTS root (S-face ck) = one region (the slice2 SU/VM8 group region, P2); pin-flop spread <= 80 "
                   "TT+FF judged in the gate; crossings to other regions land in parent rings; io_hold_margin 0.03",
        "8_schedule": "static: command/record visible c_su 2 -> 6 (+4 edges: start +1 pin +2 align, out pin +1), "
                      "reset release +1 boot edge; BTAB answer bypasses SU (parent relay, gb 500 -> 244); "
                      "NOTICE TOK.QW.SCHED (lanes/QW-TOKSCHED.md)",
    }
    return {
        "name": name, "top": "qfd_dv_s5_su8_rst3", "kind": "tile", "sources": SRC, "params": {}, "clock_port": "ck",
        "reset_ports": ["rst_n"], "outline": {"w": w, "h": h}, "macros": [], "pins": PINS,
        "layer_cap": "M5", "recipe": 2, "hold_budget": "die",
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 32, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03},
        "pin_regs": {"enable": False, "reason": "the RTL registers every input and every output at its pin (priced "
                     "c_su 2 -> 6); a flow pin register would add a second, unpriced edge"},
        "reset_landing": {"enable": False, "reason": "the RTL lands rst_n in two registered stages (rs0 -> rs1) and "
                          "fans out through kept local reset leaves (<= 32 loads each)"},
        "safe_design_checklist": chk,
        "fill_reason": {"pin_bound": f"pin-bound control leaf: 1,545 registered boundary bits ({faces}); the 768-bit "
                        f"lane address bus pd1 needs one >= 172.8 um face at <= ~4.5 pins/um; std-cell area "
                        f"{STD_AREA} um2 gives util {util:.1%}"},
        "structural_change": "QW-SU8: SU control split from SUVM7 into its own hard leaf (VM -> VM8 group; BTAB "
                             f"bypass), stride precompute, 2-stage reset landing; this kit = {L['what']}",
        "children": [], "inter": [],
        "job": {
            "owner": "Claude:QW-SU8", "branch": "claude/qw-su8-1020", "tag": "x" + leaf,
            "purpose": f"QW-SU8 slice2 SU control leaf ({L['what']})",
            "extra_paths": ["rtl/qwen_dv/s5", "rtl/test/qwen_dv/s5/su8", "results/arch/qw_su8_1020"],
            "benches": [
                {"name": "su8_eq", "cmd": VL + BENCH % ("eq", 0, 0), "expect": "pass", "pass_regex": "SU8_EQ PASS",
                 "threads": 8, "peak_ram_gb": 8, "needs": ["verilator"]},
                {"name": "su8_eq_xinit", "cmd": VL + BENCH % ("eqx", 0, 1), "expect": "pass",
                 "pass_regex": "SU8_EQ PASS", "threads": 8, "peak_ram_gb": 8, "needs": ["verilator"]},
                mut(1, "stride"), mut(2, "accept"),
            ],
            "views_to": f"physical/ref_tile/{name}/views",
            "record_to": f"results/rtl/ref_tile/{name}",
        },
    }


def main():
    out = ROOT / "tools/ref_tile/specs_qw_su8"
    out.mkdir(parents=True, exist_ok=True)
    for v in sys.argv[1:] or list(LEAF):
        s = spec(v)
        p = out / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", p)


if __name__ == "__main__":
    main()
