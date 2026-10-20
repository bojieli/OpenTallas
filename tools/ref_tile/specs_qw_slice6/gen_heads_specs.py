#!/usr/bin/env python3
"""QW-SLICE6-HEADS 10-19: ref_tile specs of the slice2 head-band leaves qfd_dv_s5_xhead (x4 per slice) and qfd_dv_s5_tap
(x1), main + structurally different parallel fallback.  python3 tools/ref_tile/specs_qw_slice6/gen_heads_specs.py"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
SRC = ["rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv", "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv", "rtl/hdc/ot_hdc_delay.sv"]
EXTRA = ["rtl/qwen_dv", "rtl/qwen_sys/dvm_20261014", "rtl/hdc", "rtl/physical", "rtl/lib", "rtl/common", "rtl/test",
         "physical/asap7_memory_macros_v2", "physical/asap7_memory_macros/ot_rom_4096x266_m8", "tools/hdc_golden.py",
         "tools/hdc_program.py", "results/arch/qw_slice6_1019"]
RUN = "bash rtl/test/qwen_dv/s5/run_s5.sh"


def bench(name, kind, m, expect):
    b = {"name": name, "cmd": f"{RUN} {{RUN}}/{name} {kind} {m}", "expect": expect, "threads": 16, "peak_ram_gb": 48,
         "needs": ["verilator"]}
    if kind == "eq":
        b["pass_regex" if expect == "pass" else "fail_regex"] = "S5_EQ PASS" if expect == "pass" else "S5_EQ FAIL"
    else:
        b["pass_regex" if expect == "pass" else "fail_regex"] = r"bench2 \(o\) MUT=0: PASS" if expect == "pass" else "bench2 .*: FAIL"
    return b


def common(name, top, w, h, pins, purpose, tag, mut, witness, checklist, why_fb=None):
    s = {"name": name, "top": top, "kind": "tile", "sources": SRC, "params": {}, "clock_port": "ck",
         "reset_ports": ["rst_n"], "outline": {"w": w, "h": h, "exact": True}, "layer_cap": "M5", "recipe": 4,
         "hold_budget": "die", "pins": pins,
         "pin_regs": {"enable": False, "reason": "the RTL registers every input at its pin (ot_qfd_xhead g_pin / ib_pin / f_q / "
                      "tid_q / fi_q / lqp; ot_qfd_xs_tap E1 pin registers) and drives every output from a flop; flow pin "
                      "registers would add unpriced cycles"},
         "reset_landing": {"enable": False, "reason": "the RTL lands rst_n in two registered stages (qfd_dv_s5_rst2) at the face"},
         "keep_pin_regs": True, "inhold": False, "outhold": False, "io_flop_at_pins": {"cols": 4, "allow_none": True},
         "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 48, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
                   "pin_min_tracks": 2, "period_ps": 833.333},
         "safe_design_checklist": checklist, "children": [], "inter": [],
         "job": {"owner": "Claude:QW-SLICE6-HEADS", "branch": "claude/qw-slice6-heads-1019", "tag": tag, "purpose": purpose,
                 "extra_paths": EXTRA,
                 "benches": [bench("s5_eq", "eq", "0", "pass"), bench("s5_b2", "b2", "0", "pass"),
                             dict(bench(f"s5_eq_mut_{mut}", "eq", mut, "fail"), fail_witness=witness)]}}
    if why_fb:
        s["structural_change"] = why_fb
    return s


XH_CL = {"1_pins": "PASS: every input lands in one pin flop (g_pin/ib_pin/f_q/tid_q/fi_q/lqp/lqvp/lqbp), every output is flop Q "
                    "(lw/lc face regs, lr0, n_q/s_q, fault); rst_n 2-stage landing (qfd_dv_s5_rst2)",
         "2_reach": "PASS: 216 x 432 tile, every hop < 405 um; the leaf buses leave W (chain 0) / E (chain 1) to leaves beside it",
         "3_fanout": "checked by the gate textbook_lint high_fanout (fd rotate 6 levels of 2:1; tids constant after SETID)",
         "4_depth": "inherited ot_qfd_xhead (closed in qfd_dv_heads_w130 at 0.77 ns); --cts path classes confirm",
         "5_storage": "PASS: largest indexed arrays wb/wbp/wbm/wo/ro [2][16] (<= 608 b), first_abs [2][16][4] x 8 = 1,024 b: all < 2 kb",
         "6_floorplan": "pin-bound (util ~6%: 5.7k um2 std for 5.8k pins): pins spread over whole faces by pin_ranges (W 3.7, E 4.6, S 5.7, N 4.8 pins/um); aspect 2:1; no macros; full std-cell band; chain write bundles low on W/E beside the S fill input (reach)",
         "7_clock": "one centre-fed TritonCTS root (8.1k sinks); io_hold_margin 0.03",
         "8_schedule": "0 added cycles (qfd_dv_heads w130 timing: FILL_LEAD 5, DX 14, LEAF_READ_PIN_PIPE 1); reset release +2 (= the slice synchroniser)"}
TAP_CL = {"1_pins": "PASS: ot_qfd_xs_tap registers its inputs (E1 pin registers) and launches hw from flops; cid HARD 1 register; "
                     "lq_bad OR -> fault join is sticky status; rst_n 2-stage landing",
          "2_reach": "PASS: < 405 um across the tile", "3_fanout": "gate textbook_lint high_fanout (hw broadcast: one copy, the parent lands 4 column copies)",
          "4_depth": "inherited ot_qfd_xs_tap STATIC_SCHEDULE 1 (closed in the heads cluster)",
          "5_storage": "PASS: no indexed flop array > 2 kb (tap queue <= 2 entries)",
          "6_floorplan": "pin-bound (util ~5%: 2.4k um2 std, 6.2k flops, 3.1k pins): hw 1,567 over the whole N face (5.3/um), hr+xt 1,503 over S (5.0/um) by pin_ranges; aspect 2:1; no macros",
          "7_clock": "one centre-fed root; io_hold_margin 0.03",
          "8_schedule": "HARD 1: cid (4 sid + c, static after SETID) +1 edge = 0 steady cycles; everything else as qfd_dv_heads"}


W = {"cid": 6, "ck": 1, "rst_n": 1, "fault_i": 1, "fault": 1, "l_rst_n": 1, "a_f": 1187, "a_ib": 380, "n_d": 516, "s_d": 516,
     "w0_v": 1, "w0_ep": 1, "w0_off": 6, "w0_m": 64, "w0_d": 1024, "w0_ctl": 72, "c0_v": 1, "c0_ep": 1, "r0_v": 4, "r0_t": 4,
     "r0_ep": 4, "r0_p": 112, "q0": 256, "q0_v": 4, "q0_bad": 4,
     "hw": 1567, "hr_q": 453, "xt_v": 1, "xt_a": 24, "xt_d": 1024, "xt_bad": 1, "lq_bad": 32, "sid": 4, "tap_fault": 1}
for k in list(W):
    if k[:2] in ("w0", "c0", "r0", "q0"):
        W[k[0] + "1" + k[2:]] = W[k]


def ranges(pins, w, h, margin=4.32):
    """pin_ranges {port: [lo, hi]}: each face's ports in list order (from the left / bottom end), spread over the whole
    face in proportion to their bits (>= 1 um each), so no face segment exceeds its average density"""
    out = {}
    for f, ports in pins.items():
        L = (w if f in "NS" else h) - 2 * margin
        tot = sum(max(W[p], 6) for p in ports)
        x = margin
        for p in ports:
            d = L * max(W[p], 6) / tot
            out[p] = [round(x, 3), round(x + d - 0.25, 3)]
            x += d
    return out


def xh_pins(alt=False):
    w0 = ["w0_v", "w0_ep", "w0_off", "w0_m", "w0_d", "w0_ctl", "c0_v", "c0_ep", "r0_v", "r0_t", "r0_ep", "r0_p", "q0", "q0_v", "q0_bad"]
    w1 = [x.replace("0", "1", 1) if x[1] == "0" else x for x in w0]
    w1 = ["w1_v", "w1_ep", "w1_off", "w1_m", "w1_d", "w1_ctl", "c1_v", "c1_ep", "r1_v", "r1_t", "r1_ep", "r1_p", "q1", "q1_v", "q1_bad"]
    # bottom -> top on W / E: the chain-head write bundle low (beside the S fill input), the read buses above it
    if not alt:
        return {"N": ["n_d", "cid", "ck", "rst_n", "s_d"], "W": w0 + ["fault", "l_rst_n"], "E": ["a_ib"] + w1 + ["fault_i"], "S": ["a_f"]}
    # fallback (259.2 wide): {ib, go} with the fill word on the wider S face
    return {"N": ["n_d", "cid", "ck", "rst_n", "s_d"], "W": w0 + ["fault", "l_rst_n"], "E": w1 + ["fault_i"], "S": ["a_ib", "a_f"]}


def main():
    out = {
        "qfd_dv_s5_xhead": common("qfd_dv_s5_xhead", "qfd_dv_s5_xhead", 216.0, 432.0, xh_pins(),
                                  "QW-SLICE6 Q.STA.SLICE.2: slice2 column head leaf (ot_qfd_xhead w130 + tids + retag), one master x 4",
                                  "xh", "xh", "results/arch/qw_slice6_1019/witness/xhead_xh.log", XH_CL),
        "qfd_dv_s5_xheadb": common("qfd_dv_s5_xheadb", "qfd_dv_s5_xhead", 259.2, 432.0, xh_pins(True),
                                   "QW-SLICE6 parallel fallback of qfd_dv_s5_xhead: 259.2-wide head, corridor words both N, {ib,go}+fill S",
                                   "xhb", "xh", "results/arch/qw_slice6_1019/witness/xhead_xh.log", XH_CL,
                                   "fallback: 259.2 x 432 (+20% width, N 4.0 / S 6.0 pins/um) with n_d + s_d on N and a_ib + a_f on S"),
        "qfd_dv_s5_tap": common("qfd_dv_s5_tap", "qfd_dv_s5_tap", 302.4, 151.2,
                                {"N": ["hw"], "S": ["hr_q", "xt_v", "xt_a", "xt_d", "xt_bad"], "E": ["lq_bad", "cid"],
                                 "W": ["sid", "ck", "rst_n", "tap_fault"]},
                                "QW-SLICE6 Q.STA.SLICE.2: slice2 heads fill tap leaf (ot_qfd_xs_tap + x expansion + fault join + cid)",
                                "tap", "d9", "results/arch/qw_slice6_1019/witness/tap_d9.log", TAP_CL),
        "qfd_dv_s5_tapb": common("qfd_dv_s5_tapb", "qfd_dv_s5_tap", 345.6, 172.8,
                                 {"N": ["hw"], "S": ["xt_v", "xt_a", "xt_d", "xt_bad"], "W": ["ck", "rst_n", "sid", "hr_q", "tap_fault"],
                                  "E": ["lq_bad", "cid"]},
                                 "QW-SLICE6 parallel fallback of qfd_dv_s5_tap: 345.6 x 172.8, hr on W, x beat alone on S",
                                 "tapb", "d9", "results/arch/qw_slice6_1019/witness/tap_d9.log", TAP_CL,
                                 "fallback: 345.6 x 172.8 (2:1), hr_q moved to W so S carries only the x beat (3.0 pins/um)"),
    }
    for n, s in out.items():
        s["pin_ranges"] = ranges(s["pins"], s["outline"]["w"], s["outline"]["h"])
        s["route"]["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M5"}
        (D / f"{n}.json").write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", D / f"{n}.json")


if __name__ == "__main__":
    main()
