#!/usr/bin/env python3
"""s5_vm8x_kit.py -- QW-VM8SPLIT 10-20 (COORD 09:45): ref_tile specs of the SPLIT slice2 VM leaves
(rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv).  Each leaf = ONE CTS root (S-centre clock pin), every pin registered in RTL, rst_n
landed rl0 -> rl1, macros on the 43.2 x-lattice / 8.64 y-lattice, every macro channel >= 20 um, S std-cell band 86.4.
Zero signals cross between leaves; their crossings to slice2 neighbours land in the parent's mesochronous rings.

  vmr   qfd_dv_s5_vmr   (x3 in slice2)  2 x 1024x256 (VM banks 0/1) + write-merge copy   259.2 x 276.48  W reads, S writes
  crom  qfd_dv_s5_crom                  4 x 1024x256 (2x2)                              475.2 x 276.48  W reads, S tw
  su    qfd_dv_s5_su                    4 x 256x256 PROG col + 4 x 128x256 BTAB col     388.8 x 354.24  E reads, S tw
  fallback partition (instead of su):
  btab  qfd_dv_s5_btab                  4 x 128x256 (2x2)                               302.4 x 216.0   E reads, S tw
  prog  qfd_dv_s5_prog                  4 x 256x256 column                              259.2 x 354.24  E reads, S tw

    python3 tools/qwen_dv/s5_vm8x_kit.py [vmr crom su btab prog]  -> tools/ref_tile/specs_qw_vm8split/<name>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MV = "physical/asap7_memory_macros_v2"
BIG, BT, PG = "ot_sram_1r1w_1024x256_m2_r2c2", "ot_sram_1r1w_128x256_m1_r2c2", "ot_sram_1r1w_256x256_m2_r2c2"
SRC = ["rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv", f"{MV}/{BIG}/{BIG}_bb.v", f"{MV}/{BT}/{BT}_bb.v", f"{MV}/{PG}/{PG}_bb.v"]
WDIR = "results/arch/qw_vm8split_1020/bench"
VL = "export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH && "


def mac(view, inst, x, y):
    return {"view": f"{MV}/{view}", "count": 1, "inst": inst, "at": [round(x, 3), round(y, 3)], "at_exact": True,
            "orient": "R0"}


TW = ["tw_we", "tw_kind", "tw_addr", "tw_data"]
LEAF = {
    "vmr": dict(top="qfd_dv_s8x_vmr", w=259.2, h=276.48,
                macros=[mac(BIG, "*g_bank?0?*u_m", 43.2, 86.4), mac(BIG, "*g_bank?1?*u_m", 43.2, 181.44)],
                pins={"W": ["re", "addr", "q"],
                      "S": ["rst_n", "vm_we", "vm_waddr", "vm_wdata", "w16_we", "w16_addr", "w16_data", "w1_we",
                            "w1_addr", "w1_data", "fault", "ck"]},
                what="VM replica (2 x 1024x256 banks) + full vm7 write-merge copy; x3 in slice2 (a/b/c)",
                faces="W 456 pins / 267.8 um = 1.7/um, S 1,054 / 259.2 = 4.1/um"),
    "crom": dict(top="qfd_dv_s8x_crom", w=475.2, h=276.48,
                 macros=[mac(BIG, "*g_crom?0?*u_lo", 43.2, 86.4), mac(BIG, "*g_crom?0?*u_hi", 43.2, 181.44),
                         mac(BIG, "*g_crom?1?*u_lo", 259.2, 86.4), mac(BIG, "*g_crom?1?*u_hi", 259.2, 181.44)],
                 pins={"W": ["cr_re", "cr_addr", "cr_q"], "S": ["rst_n"] + TW + ["fault", "ck"]},
                 what="CROM 2 banks x {lo, hi} (2x2 of 1024x256) + table-write landing + table-write fault",
                 faces="W 712 / 276.5 = 2.6/um, S 1,054 / 475.2 = 2.2/um"),
    "su": dict(top="qfd_dv_s8x_su", w=388.8, h=354.24,
               macros=[mac(PG, f"*g_prog?{b}?*u_{s}", 43.2, 86.4 + 69.12 * (2 * b + i)) for b in (0, 1)
                       for i, s in enumerate(("lo", "hi"))] +
                      [mac(BT, f"*g_btb?{b}?*u_m", 259.2, 86.4 + 69.12 * b) for b in range(4)],
               pins={"E": ["bs_re", "bs_addr", "bs_q", "p_re", "p_idx", "p_q"], "S": ["rst_n"] + TW + ["fault", "ck"]},
               what="BTAB SU copy (4 x 128x256) + PROG 2 banks x {lo, hi} (4 x 256x256) = btab + prog",
               faces="E 748 / 354.2 = 2.1/um, S 1,039 / 388.8 = 2.7/um"),
    "btab": dict(top="qfd_dv_s8x_btab", w=302.4, h=216.0,
                 macros=[mac(BT, f"*g_btb?{b}?*u_m", 43.2 + 129.6 * (b % 2), 86.4 + 69.12 * (b // 2)) for b in range(4)],
                 pins={"E": ["bs_re", "bs_addr", "bs_q"], "S": ["rst_n"] + TW + ["fault", "ck"]},
                 what="fallback partition: BTAB SU copy (2x2 of 128x256)",
                 faces="E 281 / 216 = 1.3/um, S 1,037 / 302.4 = 3.4/um"),
    "prog": dict(top="qfd_dv_s8x_prog", w=259.2, h=354.24,
                 macros=[mac(PG, f"*g_prog?{b}?*u_{s}", 43.2, 86.4 + 69.12 * (2 * b + i)) for b in (0, 1)
                         for i, s in enumerate(("lo", "hi"))],
                 pins={"E": ["p_re", "p_idx", "p_q"], "S": ["tw_we", "tw_kind", "tw_addr", "tw_d0", "tw_d1", "ck"]},
                 what="fallback partition: PROG 2 banks x {lo, hi} (column of 4 x 256x256); no reset, no fault",
                 faces="E 467 / 354.2 = 1.3/um, S 926 / 259.2 = 3.6/um"),
}


def spec(leaf):
    L = LEAF[leaf]
    name = f"qfd_dv_s5_{leaf}"
    rst = leaf != "prog"
    mut = lambda m: {"name": f"vm8x_mut_{m}", "cmd": VL + f"bash rtl/test/qwen_dv/s5/vm8x/bench.sh {{RUN}}/m_{m} {m} 0",
                     "expect": "fail", "fail_regex": "VM8X_EQ FAIL", "fail_witness": f"{WDIR}/run_{m}_0.log",
                     "threads": 8, "peak_ram_gb": 16, "needs": ["verilator"]}
    chk = {
        "1_pins": "PASS: RTL registers every input and output at its pin (= vm8 pin registers); " +
                  ("rst_n lands rl0 -> rl1 and resets only the sticky fault" if rst else "no reset (datapath only)") +
                  "; no combinational pin arc",
        "2_reach": f"PASS (by floorplan): outline {L['w']} x {L['h']}, every pin <= {max(L['w'], L['h']):.0f} um from any "
                   "sink; gate wire_reach checks 405 um",
        "3_fanout": "pre-gate mapped census results/arch/qw_vm8split_1020/native/<top> (kept copies as vm8)",
        "4_depth": "PASS: = vm8 (census depth recorded); no logic before a macro pin except the 2-register collision compare",
        "5_storage": "PASS: all > 2 kb state in SRAM macros",
        "6_floorplan": f"PASS: x on 43.2, y on 8.64, macro channels >= 20 um, S band 86.4, aspect "
                       f"{max(L['w'], L['h']) / min(L['w'], L['h']):.2f}, faces {L['faces']}",
        "7_clock": "ONE CTS root (S-centre ck) over the whole leaf = one region; pin-flop spread <= 80 TT+FF judged in the "
                   "gate; every crossing to a slice2 neighbour lands in a parent mesochronous ring; io_hold_margin 0.03",
        "8_schedule": "static; 0 edges vs vm8 (reads 2 -> 4, VM write -> read 1 -> 3, tw +2, fault +1 = vm8b prices)",
    }
    return {
        "name": name, "top": L["top"], "kind": "tile", "sources": SRC, "params": {}, "clock_port": "ck",
        "reset_ports": ["rst_n"] if rst else [],
        "outline": {"w": L["w"], "h": L["h"]}, "macros": L["macros"], "pins": L["pins"],
        "layer_cap": "M5", "recipe": 2, "hold_budget": "die",
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 64, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
                  "macro_halo_um": 5.4},
        "pin_regs": {"enable": False, "reason": "the RTL registers every input and every output at its pin (vm8 pin "
                     "registers, priced); a flow pin register would add a second, unpriced edge"},
        "reset_landing": {"enable": False, "reason": ("the RTL lands rst_n in two registered stages (rl0 -> rl1) and rl1 "
                          "resets only the sticky fault register") if rst else "no reset port (datapath-only leaf)"},
        "safe_design_checklist": chk,
        "structural_change": f"QW-VM8SPLIT: vm8 split into single-root leaves (COORD 09:45); this leaf = {L['what']}",
        "children": [], "inter": [],
        "job": {
            "owner": "Claude:QW-VM8SPLIT", "branch": "claude/qw-vm8split-1020", "tag": "x" + leaf,
            "purpose": f"QW-VM8SPLIT slice2 VM leaf: {L['what']}",
            "extra_paths": ["rtl", "rtl/test/qwen_dv", "physical/asap7_memory_macros_v2", "results/arch/qw_vm8split_1020"],
            "benches": [
                {"name": "vm8x_eq", "cmd": VL + "bash rtl/test/qwen_dv/s5/vm8x/bench.sh {RUN}/eq 0 0",
                 "expect": "pass", "pass_regex": "VM8X_EQ PASS", "threads": 8, "peak_ram_gb": 16, "needs": ["verilator"]},
                {"name": "vm8x_eq_split1", "cmd": VL + "bash rtl/test/qwen_dv/s5/vm8x/bench.sh {RUN}/eq1 0 1",
                 "expect": "pass", "pass_regex": "VM8X_EQ PASS", "threads": 8, "peak_ram_gb": 16, "needs": ["verilator"]},
                mut("coll"), mut("wpri"), mut("bsel"),
            ],
            "views_to": f"physical/ref_tile/{name}/views",
            "record_to": f"results/rtl/ref_tile/{name}",
        },
    }


def main():
    out = ROOT / "tools/ref_tile/specs_qw_vm8split"
    out.mkdir(parents=True, exist_ok=True)
    for v in sys.argv[1:] or list(LEAF):
        s = spec(v)
        p = out / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", p)


if __name__ == "__main__":
    main()
