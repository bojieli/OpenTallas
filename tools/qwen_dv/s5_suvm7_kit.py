#!/usr/bin/env python3
"""s5_suvm7_kit.py -- QW-SLICE7-LEAVES/SUVM 10-20: ref_tile specs of the SAFE successor qfd_dv_s5_suvm7 (same floorplans
as s5_suvm_kit.py, which made qfd_dv_s5_suvm: census FAIL 211 drivers > 32). Leaf qfd_dv_s5_suvm (SU issue control + VM with
18 SRAM macros: VM 3 replicas x 2 banks + CROM 2 x {lo, hi} = 10 x 1024x256, BTAB SU copy 4 x 128x256, PROG 4 x 256x256).

  a  qfd_dv_s5_suvm   (main)     2 abutted N-S macro columns (5 x 1024x256 + 2 PROG + 2 BTAB each), 43.2-um pin
                                 channels W | between | E, full-width std-cell band S (control, VM write merge, read
                                 capture / extraction), 483.84 x 691.2
  b  qfd_dv_s5_suvmb  (fallback) 3 abutted columns (5 big | 5 big | 4 PROG + 4 BTAB), wider / lower (691.2 x 561.6),
                                 deeper S band 151.2
Every macro column is an abutted stack (pitch = array height + 0.024, pins only on W / E faces), so the only
std-cell regions are the pin channels and the band: no slivers.

    python3 tools/qwen_dv/s5_suvm7_kit.py a|b   -> tools/ref_tile/specs_qw_slice6/<name>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MV = "physical/asap7_memory_macros_v2"
BIG, BT, PG = "ot_sram_1r1w_1024x256_m2_r2c2", "ot_sram_1r1w_128x256_m1_r2c2", "ot_sram_1r1w_256x256_m2_r2c2"
H = {BIG: 70.488, BT: 41.064, PG: 41.064}
P = 0.024                     # abutted stack pitch adder


def mac(view, inst, x, y):
    return {"view": f"{MV}/{view}", "count": 1, "inst": inst, "at": [round(x, 3), round(y, 3)], "at_exact": True,
            "orient": "R0"}


def stack(x, y0, items):
    out, y = [], y0
    for view, inst in items:
        out.append(mac(view, inst, x, y))
        y += H[view] + P
    return out, y


VM = lambda op, bk: (BIG, f"*u_vm*g_rep?{op}?*g_bank?{bk}?*u_m")
CR = lambda bk, s: (BIG, f"*u_vm*g_crom?{bk}?*u_{s}")
PR = lambda bk, s: (PG, f"*u_vm*g_prog?{bk}?*u_{s}")
BB = lambda bk: (BT, f"*u_vm*g_btb?{bk}?*u_m")


def spec(var):
    name = "qfd_dv_s5_suvm7" if var == "a" else "qfd_dv_s5_suvm7b"
    if var == "a":
        W, Hh, yb = 483.84, 691.2, 129.6
        c0, top0 = stack(43.2, yb, [VM(0, 0), VM(0, 1), VM(1, 0), VM(1, 1), VM(2, 0), PR(0, "lo"), PR(0, "hi"), BB(0), BB(1)])
        c1, top1 = stack(261.36, yb, [VM(2, 1), CR(0, "lo"), CR(0, "hi"), CR(1, "lo"), CR(1, "hi"), PR(1, "lo"), PR(1, "hi"),
                                      BB(2), BB(3)])
        macros = c0 + c1
        geom = "2 abutted columns x 9 (5 x 1024x256 + 2 PROG + 2 BTAB), channels W 43.2 | 43.4 | E 47.7, S band 129.6"
    else:
        W, Hh, yb = 691.2, 561.6, 151.2
        c0, _ = stack(43.2, yb, [VM(0, 0), VM(0, 1), VM(1, 0), VM(1, 1), VM(2, 0)])
        c1, _ = stack(261.36, yb, [VM(2, 1), CR(0, "lo"), CR(0, "hi"), CR(1, "lo"), CR(1, "hi")])
        c2, _ = stack(479.52, yb, [PR(0, "lo"), PR(0, "hi"), PR(1, "lo"), PR(1, "hi"), BB(0), BB(1), BB(2), BB(3)])
        macros = c0 + c1 + c2
        geom = "3 abutted columns (5 big | 5 big | 4 PROG + 4 BTAB), channels 43.2 / 43.4 / 43.4 / E 38.9, S band 151.2"
    pins = {
        # lane answers + live / offset relay stage 1 (to the lane relays)
        "W": ["va_q", "vb_q", "vc_q", "cr_q", "lv1", "pd1"],
        # lane requests / results (from the lane relays)
        "E": ["va_re", "vb_re", "vc_re", "cr_re", "vm_we", "kv_we", "l_retire", "l_last", "l_fault", "l_wrom_re",
              "va_addr", "vb_addr", "vc_addr", "cr_addr", "vm_waddr", "l_wrom_addr", "vm_wdata"],
        # broadcast group relay (both lane sides)
        "N": ["gb", "gv"],
        # ctl / stream / reducer side + clock / reset at the S centre (centre-fed root)
        "S": ["su_cmd", "w16_we", "w16_addr", "w16_data", "w1_we", "w1_addr", "w1_data", "ck", "rst_n", "rd_v",
              "red_busy", "red_fault", "su_nr", "su_idle", "su_fault", "su_prog", "su_rows", "vm_fault",
              "tw_we", "tw_kind", "tw_addr", "tw_data"],
    }
    wdir = "results/arch/qw_slice7_1020/suvm7/bench"
    vl = "export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH && "
    s = {
        "name": name,
        "top": "qfd_dv_s5_suvm7",
        "kind": "tile",
        "sources": ["rtl/qwen_dv/s5/qfd_dv_s5_suvm7.sv",
                    f"{MV}/{BIG}/{BIG}_bb.v", f"{MV}/{BT}/{BT}_bb.v", f"{MV}/{PG}/{PG}_bb.v"],
        "params": {},
        "clock_port": "ck",
        "reset_ports": ["rst_n"],
        "outline": {"w": W, "h": Hh},
        "macros": macros,
        "pins": pins,
        "layer_cap": "M5",
        "recipe": 2,
        "hold_budget": "die",
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 96, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
                  "macro_halo_um": 5.4},
        "pin_regs": {"enable": False, "reason": "qfd_dv_s5_suvm7 lands the VM write bundle in RTL (+1 priced edge) and "
                     "keeps reads edge-for-edge: lane read requests drive the SRAM macro address/enable pins (the macro "
                     "is the input register) and the stage-1 select flops; answers leave the macro capture flops through "
                     "the 2:1 x 8:1 extraction mux (macro clk->q ~550 ps of 770 ps leaves no room before capture); a "
                     "flow pin register would add an unpriced edge inside the lane read round trip (ML 1 / RD 2)"},
        "reset_landing": {"enable": False, "reason": "the RTL lands rst_n in two registered stages (rs1 -> 6 kept rs2 "
                          "replicas) then 10 kept rc replicas, each <= 32 async-reset pins"},
        "safe_design_checklist": {},
        "structural_change": f"QW-SLICE7 safe successor of qfd_dv_s5_suvm (native census 211 > 32 -> kept replicas, landed VM writes): {geom}",
        "children": [],
        "inter": [],
        "job": {
            "owner": "Claude:QW-SLICE7-LEAVES/SUVM",
            "branch": "claude/qw-slice6-suvm-1019",
            "tag": "s7" + var,
            "purpose": "QW-SLICE7 qfd_dv_slice2 one-level slice: SU issue control + VM leaf (18 SRAM), " +
                       ("main" if var == "a" else "parallel fallback (3-column floorplan)"),
            "extra_paths": ["rtl", "tools/hdc_golden.py", "tools/hdc_program.py", "rtl/test/qwen_dv", "rtl/test/full_sm_service",
                            "rtl/test/hbm_rf_visibility", "physical/asap7_memory_macros",
                            "physical/asap7_memory_macros_v2", "results/arch/qw_slice7_1020"],
            "benches": [
                {"name": "suvm7_eq", "cmd": vl + "bash rtl/test/qwen_dv/s5/suvm7/bench.sh {RUN}/eq 0",
                 "expect": "pass", "pass_regex": "SUVM7_EQ PASS", "threads": 8, "peak_ram_gb": 16, "needs": ["verilator"]},
                {"name": "suvm7_mut_loff", "cmd": vl + "bash rtl/test/qwen_dv/s5/suvm7/bench.sh {RUN}/m1 loff",
                 "expect": "fail", "fail_regex": "SUVM7_EQ FAIL", "fail_witness": wdir + "/run_loff.log", "threads": 8,
                 "peak_ram_gb": 16, "needs": ["verilator"]},
                {"name": "suvm7_mut_wpri", "cmd": vl + "bash rtl/test/qwen_dv/s5/suvm7/bench.sh {RUN}/m2 wpri",
                 "expect": "fail", "fail_regex": "SUVM7_EQ FAIL", "fail_witness": wdir + "/run_wpri.log", "threads": 8,
                 "peak_ram_gb": 16, "needs": ["verilator"]},
            ],
            "views_to": f"physical/ref_tile/{name}/views",
            "record_to": f"results/rtl/ref_tile/{name}",
        },
    }
    return s


def main():
    out = ROOT / "tools/ref_tile/specs_qw_slice6"
    out.mkdir(parents=True, exist_ok=True)
    for v in sys.argv[1:] or ["a", "b"]:
        s = spec(v)
        p = out / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", p)


if __name__ == "__main__":
    main()
