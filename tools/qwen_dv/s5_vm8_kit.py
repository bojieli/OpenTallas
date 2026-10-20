#!/usr/bin/env python3
"""s5_vm8_kit.py -- QW-SUVM8 10-20: ref_tile specs of the hardened slice2 VM block (rtl/qwen_dv/s5/qfd_dv_s5_vm8.sv),
the structural successor of the doomed suvm7 / suvm7b leaf (one 9.7k-flop root, pin-flop spread 217 / 381 ps, placement
reg->macro -519 / in->macro -406 / reg->out -429 ps).  18 SRAM macros: VM 3 replicas x 2 banks + CROM 2 x {lo, hi}
(10 x 1024x256), PROG 2 x {lo, hi} (4 x 256x256), BTAB SU copy (4 x 128x256).

Same floorplan for both variants (691.2 x 648, aspect 1.07): three macro columns on the 43.2 x-lattice, every macro
origin on the 8.64 track lattice, every macro-macro channel >= 20 um (big pitch 112.32 = 41.8 um std-cell bands between
VM / CROM macros for their capture / write registers; small pitch 69.12 = 28.1 um), full-width S std-cell band 86.4.
  col 0 (x 43.2)  : VM rep0 b0, rep0 b1, rep1 b0 | CROM lo0, hi0      (read faces on the W channel)
  col 1 (x 259.2) : VM rep1 b1, rep2 b0, rep2 b1 | CROM lo1, hi1      (read faces on the W-centre channel, 259 um to W)
  col 2 (x 475.2) : PROG lo0, hi0, lo1, hi1, BTAB 0..3                (read faces 216 um from the E face)
VM macros sit in rows 0-2 (<= 381 um from the S write band); CROM / PROG / BTAB table writes take a second landing stage
(one kept copy per group) so no table-write wire crosses the block in one cycle.
Faces: W = lane operand + CROM reads/answers (ck_rd), E = SU-control BTAB / PROG reads/answers (ck_su), S = VM / table
writes, reset, fault (ck_wr).

  a  qfd_dv_s5_vm8   (main)     three regional CTS roots ck_wr / ck_rd / ck_su (multiple_cts_roots, related same PLL)
  b  qfd_dv_s5_vm8b  (fallback) the same RTL through the single-root wrapper qfd_dv_s5_vm8s, one S-centre-fed tree

  c  qfd_dv_s5_vm8c  (QW-SUVM9) vm8b RTL/single root, floorplan with full W and E std-cell bands 86.4 um (777.6 x 648):
     vm8b r2 CTS measured boundary spread TT 100.3 / FF 88.3 ps; the ~280 late sinks (TT 785-827 vs mean 745) are ONLY the
     E-face p_q / ptw pin registers in the 43.2 um strip beside the PROG column: their level-8 H-tree tap legalised into
     the 28 um PROG channel at x 559 and reached the strip through a 110 um wire hop (+80 ps); W / S faces 727..765.
     The register mass at every face now sits in a real band where the tree's taps can land beside it.
  d  qfd_dv_s5_vm8d  (QW-SUVM9 parallel fallback) vm8c + tighter CTS sink clustering (diameter 40 um, size 16) so leaf
     buffers sit inside each face band.

    python3 tools/qwen_dv/s5_vm8_kit.py a|b|c|d   -> tools/ref_tile/specs_qw_suvm8/<name>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MV = "physical/asap7_memory_macros_v2"
BIG, BT, PG = "ot_sram_1r1w_1024x256_m2_r2c2", "ot_sram_1r1w_128x256_m1_r2c2", "ot_sram_1r1w_256x256_m2_r2c2"
Y0, PB, PS = 86.4, 112.32, 69.12


def mac(view, inst, x, y):
    return {"view": f"{MV}/{view}", "count": 1, "inst": inst, "at": [round(x, 3), round(y, 3)], "at_exact": True,
            "orient": "R0"}


VM = lambda op, bk: (BIG, f"*g_rep?{op}?*g_bank?{bk}?*u_m")
CR = lambda bk, s: (BIG, f"*g_crom?{bk}?*u_{s}")
PR = lambda bk, s: (PG, f"*g_prog?{bk}?*u_{s}")
BB = lambda bk: (BT, f"*g_btb?{bk}?*u_m")

RD_IN = ["a_re", "b_re", "c_re", "a_addr", "b_addr", "c_addr", "cr_re", "cr_addr"]
RD_OUT = ["a_q", "b_q", "c_q", "cr_q"]
SU_IN = ["bs_re", "bs_addr", "p_re", "p_idx"]
SU_OUT = ["bs_q", "p_q"]
WR_IN = ["rst_n", "vm_we", "vm_waddr", "vm_wdata", "w16_we", "w16_addr", "w16_data", "w1_we", "w1_addr", "w1_data",
         "tw_we", "tw_kind", "tw_addr", "tw_data"]
WR_OUT = ["fault"]

CHECKLIST = {
    "1_pins": "PASS: RTL registers every input and every output at its pin (pin regs on 3 roots); rst_n lands rl0 -> rl1 "
              "(2 registered stages) and resets only the sticky fault; no combinational pin arc",
    "2_reach": "PASS (by floorplan): VM macros rows 0-2 <= 381 um from the S write band; table writes land twice (pin + "
               "group copy); read faces <= 259 um (W) / 216 um (E) from their pins; gate wire_reach checks 405 um",
    "3_fanout": "PASS: pre-gate mapped census (results/arch/qw_suvm8_1020/vm8/native*): kept per-(replica, bank) write "
                "registers, kept one-hot read selects, pin registers <= 20 loads",
    "4_depth": "PASS: no logic before any macro pin except the 2-register read-collision compare (10-b eq); answer path "
               "capture -> kept one-hot 2:1 x 8:1 -> answer pin register",
    "5_storage": "PASS: all > 2 kb state in 18 SRAM macros; flops are pin / capture / landing / write-stage registers",
    "6_floorplan": "PASS: x on the 43.2 lattice, y on the 8.64 track lattice, every macro channel >= 20 um (no abutted "
                   "stacks), full-width S band 86.4, aspect 1.07, pin faces W 3.2 / E 1.2 / S 3.0 pins/um",
    "7_clock": "a: three regional related roots (ck_wr S band, ck_rd W + VM/CROM, ck_su E + PROG/BTAB), each < 8k flops "
               "and judged on pin-flop spread <= 80 TT+FF; b: one S-centre root (fallback); io_hold_margin 0.03",
    "8_schedule": "static, no credits/backpressure; PRICED: reads +2 (answer 2 -> 4 edges), VM writes +3 vs suvm "
                  "(write->read distance 1 -> 3), table writes +2 (table write->read distance 1 -> 2), fault +1",
}


def spec(var):
    name = {"a": "qfd_dv_s5_vm8", "h": "qfd_dv_s5_vm8h", "b": "qfd_dv_s5_vm8b", "c": "qfd_dv_s5_vm8c",
            "d": "qfd_dv_s5_vm8d"}[var]
    one = var in ("b", "c", "d")
    top = "qfd_dv_s5_vm8s" if one else "qfd_dv_s5_vm8"
    XB = 86.4 if var in ("c", "d") else 43.2           # W / E std-cell band width (c/d: full 86.4 bands, like S)
    W, Hh = (691.2 + 2 * (XB - 43.2)), 648.0
    c0 = [VM(0, 0), VM(0, 1), VM(1, 0), CR(0, "lo"), CR(0, "hi")]
    c1 = [VM(1, 1), VM(2, 0), VM(2, 1), CR(1, "lo"), CR(1, "hi")]
    c2 = [PR(0, "lo"), PR(0, "hi"), PR(1, "lo"), PR(1, "hi"), BB(0), BB(1), BB(2), BB(3)]
    macros = [mac(v, i, XB, Y0 + k * PB) for k, (v, i) in enumerate(c0)]
    macros += [mac(v, i, XB + 216.0, Y0 + k * PB) for k, (v, i) in enumerate(c1)]
    macros += [mac(v, i, XB + 432.0, Y0 + k * PS) for k, (v, i) in enumerate(c2)]
    # raw macro clock entry index per macro (RTL ckm<i>): order of c0 / c1 / c2 below
    ent = [0, 1, 2, 6, 7] + [3, 4, 5, 8, 9] + [14, 15, 16, 17, 10, 11, 12, 13]
    if var == "h":
        for m, i in zip(macros, ent):
            m["clock_entry"] = {"port": f"ckm{i}", "pin": "clk", "reference": "raw_liberty_clock_pin"}
    km = lambda ids: [f"ckm{i}" for i in ids]
    if not one:
        pins = {"W": RD_IN + RD_OUT + ["ck_rd"] + km(range(10)), "E": SU_IN + SU_OUT + ["ck_su"] + km(range(10, 18)),
                "S": WR_IN + WR_OUT + ["ck_wr"]}
    else:
        pins = {"W": RD_IN + RD_OUT, "E": SU_IN + SU_OUT, "S": WR_IN + WR_OUT + ["ck"]}
    wdir = "results/arch/qw_suvm8_1020/vm8/bench"
    vl = "export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH && "
    mut = lambda m: {"name": f"vm8_mut_{m}", "cmd": vl + f"bash rtl/test/qwen_dv/s5/vm8/bench.sh {{RUN}}/m_{m} {m}",
                     "expect": "fail", "fail_regex": "VM8_EQ FAIL", "fail_witness": f"{wdir}/run_{m}.log", "threads": 8,
                     "peak_ram_gb": 16, "needs": ["verilator"]}
    s = {
        "name": name,
        "top": top,
        "kind": "tile",
        "sources": ["rtl/qwen_dv/s5/qfd_dv_s5_vm8.sv",
                    f"{MV}/{BIG}/{BIG}_bb.v", f"{MV}/{BT}/{BT}_bb.v", f"{MV}/{PG}/{PG}_bb.v"],
        "params": {},
        "clock_port": "ck" if one else "ck_wr",
        "reset_ports": ["rst_n"],
        "outline": {"w": W, "h": Hh},
        "macros": macros,
        "pins": pins,
        "layer_cap": "M5",
        "recipe": 2,
        "hold_budget": "die",
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 96, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
                  "macro_halo_um": 5.4},
        "pin_regs": {"enable": False, "reason": "the RTL registers every input and every output at its pin "
                     "(qfd_dv_s5_vm8: p* input registers, answer / fault output registers; +1 in / +1 out priced in "
                     "the slice2 schedule, bench tb_vm8 proves the edges); a flow pin register would add a second, "
                     "unpriced edge"},
        "reset_landing": {"enable": False, "reason": "the RTL lands rst_n in two registered stages (rl0 -> rl1 on "
                          "ck_wr) and rl1 resets only the sticky fault register"},
        "safe_design_checklist": CHECKLIST,
        "structural_change": ("QW-SUVM8: VM split out of suvm7 as its own hardened block; every pin registered; "
                              "registered write stage at the macros; table writes landed per group; "
                              + ({"a": "three regional related CTS roots", "h": "three regional related CTS roots + 18 raw SRAM clock entries (hybrid_entries)",
                                  "c": "single S-centre root; QW-SUVM9: full 86.4 um W and E std-cell bands so every face register mass has tree taps beside it (vm8b E strip 43.2 um -> +80 ps leaf hop)",
                                  "d": "vm8c + CTS sink clustering 40 um / 16 sinks (parallel fallback)"}.get(var) or "single S-centre root (fallback)")
                              + "; 3 columns, all macro channels >= 20 um"),
        "children": [],
        "inter": [],
        "job": {
            "owner": "Claude:QW-SUVM9" if var in ("c", "d") else "Claude:QW-SUVM8",
            "branch": "claude/qw-suvm9-1020" if var in ("c", "d") else "claude/qw-suvm8-1020",
            "tag": "v8" + var,
            "purpose": "QW-SUVM8 slice2 VM hardened block (18 SRAM), " +
                       ({"a": "3 regional roots", "h": "main: 3 regional roots + raw SRAM clock entries",
                         "c": "single root, full W/E std-cell bands (vm8b spread fix)",
                         "d": "vm8c + tight CTS sink clustering (parallel fallback)"}.get(var) or "parallel fallback: single root, same RTL"),
            "extra_paths": ["rtl", "rtl/test/qwen_dv", "physical/asap7_memory_macros_v2", "results/arch/qw_suvm8_1020"],
            "benches": [
                {"name": "vm8_eq", "cmd": vl + "bash rtl/test/qwen_dv/s5/vm8/bench.sh {RUN}/eq 0",
                 "expect": "pass", "pass_regex": "VM8_EQ PASS", "threads": 8, "peak_ram_gb": 16, "needs": ["verilator"]},
                mut("coll"), mut("wpri"), mut("bsel"),
            ],
            "views_to": f"physical/ref_tile/{name}/views",
            "record_to": f"results/rtl/ref_tile/{name}",
        },
    }
    if var in ("c", "d"):
        s["safe_design_checklist"] = dict(CHECKLIST, **{
            "2_reach": "PASS (by floorplan): VM macros rows 0-2 <= 381 um from the S write band; table writes land twice; "
                       "read faces <= 302 um (W) / 259 um (E) from their pins (+43.2 for the bands); gate checks 405 um",
            "6_floorplan": "PASS: x on the 43.2 lattice (cols 86.4 / 302.4 / 518.4), y on 8.64, every macro channel >= "
                           "20 um, full-width S band 86.4 AND full-height W / E bands 86.4, 777.6 x 648 aspect 1.20",
            "7_clock": "single S-centre root (die delivers one clock); vm8b r2 CTS: boundary TT 726.9..827.2 -- late tail = "
                       "E-strip p_q/ptw pin registers only (tap legalised into a 28 um PROG channel, 110 um leaf hop); "
                       "fix = W/E bands so face register masses have tree taps beside them" +
                       ("; d: CTS sink clustering 40 um / 16" if var == "d" else "") + "; judged pin-flop spread <= 80 TT+FF; io_hold_margin 0.03"})
    if var == "d":
        s["orfs_vars"] = {"CTS_CLUSTER_DIAMETER": "40", "CTS_CLUSTER_SIZE": "16"}
    if var in ("a", "h"):
        s["clock"] = "multiple_cts_roots" if var == "a" else "hybrid_entries"
        s["clock_ports"] = ["ck_wr", "ck_rd", "ck_su"] + (km(range(18)) if var == "h" else [])
        if var == "h":
            s["clock_cts_roots"] = ["ck_wr", "ck_rd", "ck_su"]
        s["clock_data_paths"] = "related_same_frequency"
        s["clock_relationship"] = {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0}
        s["clock_entry_domains"] = {
            "core": {"ratio": [1, 1], "ports": ["ck_wr"], "inputs": WR_IN, "outputs": WR_OUT},
            "rd": {"ratio": [1, 1], "ports": ["ck_rd"], "inputs": RD_IN, "outputs": RD_OUT},
            "su": {"ratio": [1, 1], "ports": ["ck_su"], "inputs": SU_IN, "outputs": SU_OUT},
        }
        if var == "h":
            for i in range(18):
                s["clock_entry_domains"][f"mem{i}"] = {"ratio": [1, 1], "ports": [f"ckm{i}"], "inputs": [], "outputs": []}
    return s


def main():
    out = ROOT / "tools/ref_tile/specs_qw_suvm8"
    out.mkdir(parents=True, exist_ok=True)
    for v in sys.argv[1:] or ["h", "b"]:
        s = spec(v)
        p = out / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", p)


if __name__ == "__main__":
    main()
