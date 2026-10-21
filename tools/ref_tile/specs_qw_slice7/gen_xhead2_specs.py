#!/usr/bin/env python3
"""QW-SLICE7-LEAVES 10-20: ref_tile specs of qfd_dv_s5_xhead2 (bounded successor of qfd_dv_s5_xhead, x4 per slice) main
216 x 432 (the xhead gate3 outline: spread 52.0/48.8 WARN) + structurally different fallback 302.4 x 345.6 (aspect 1.14:
the 259.2 x 432 xheadb failed pin-flop spread 88.3/84.5).  python3 tools/ref_tile/specs_qw_slice7/gen_xhead2_specs.py"""
import json, sys
from pathlib import Path
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parent / "specs_qw_slice6"))
import gen_heads_specs as H

SRC = ["rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded.sv", "rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded_helpers.sv",
       "rtl/qwen_dv/s5/qfd_dv_s5_xhead2.sv"]
RUN = "bash rtl/test/qwen_dv/s5/xhead7/bench.sh"
EV = "results/arch/qw_slice7_1020/xhead"
CENSUS = json.loads((D.parents[2] / EV / "native/census_summary.json").read_text()) if (D.parents[2] / EV / "native/census_summary.json").exists() else {}
CL = {
 "1_pins": "FIXED: the slice retag moved in front of the n_q/s_q output registers (qfd_dv_s5_xhead_rt; was 1 comb level after "
           "the last flop): every output is flop Q; every input lands in a pin register (a_d IN_PIPE stage, lqp/lqvp/lqbp, fi_q, "
           "tids); rst_n 2-stage landing (qfd_dv_s5_rst2), mapped census rst_n loads 2",
 "2_reach": "PASS: tile <= 432 um side, every intra-tile hop < 405 um; leaf buses leave W (chain 0) / E (chain 1)",
 "3_fanout": "FIXED (structural): bounded constructor (tools/qwen_dv/bound_math_netlist.py --load-cap 16, retained operator "
             "boundaries) replicates every FF / comb root incl. the shared fill selects b_d/f_q (2585), fep (1707), fill-go "
             "line (877), g_pin (759) and reset; the foff rotate selects need >= 34 same-edge copies, so the a_d input "
             "lands in one extra pin stage (IN_PIPE, +1 edge) and the replica tree grows from it. ASAP7 mapped census: "
             + CENSUS.get("text", "see " + EV + "/native/census.json"),
 "4_depth": "PASS: inherited ot_qfd_xhead stage depth (predecessor 481.8 ps / 11 lv); AO21/OA21 fusion; mapped estimate "
            + str(CENSUS.get("depth_ps", "in census")) + " ps",
 "5_storage": "PASS: largest runtime-indexed arrays wb/wbp/wbm/wo/ro [2][16] (<= 608 b), first_abs [2][16][4] x 8 = 1,024 b, "
              "all < 2 kb; go/phase delay lines (u_fill_go 5x1, u_gdx 9x1, u_phd 8x3, u_vd 8x1, u_pd 8x1 = 54 b) WAIVED from "
              "ring conversion: 1-3 bit fixed-age control lines, a ring pointer would fan out more than the line it replaces",
 "6_floorplan": "pin-bound (~5.8k pins at <= 6 pins/um per face; std area from the mapped census); no macros; one full std-cell "
                "band; pins spread over whole faces (pin_ranges)",
 "7_clock": "one centre-fed TritonCTS root; judged on pin-flop spread <= 80 ps TT+FF; io_hold_margin 0.03",
 "8_schedule": "static. +1 edge on the head-row input a_d (go, descriptor, fill data, ib together: x column op latency +1, "
               "NOTICE to QW-SLICE7 / QW-GRT4 / GEN3); 0 edges from the retag move; reset release +2 as the predecessor",
}


def spec(name, w, h, pins, tag, why=None):
    s = {"name": name, "top": "qfd_dv_s5_xhead2", "kind": "tile", "sources": SRC, "params": {}, "clock_port": "ck",
         "reset_ports": ["rst_n"], "outline": {"w": w, "h": h, "exact": True}, "layer_cap": "M5", "recipe": 4,
         "hold_budget": "die", "pins": pins,
         "fill_reason": {"pin_bound": "~5,800 port bits (fill word 1,187 + ib 380 + two corridor words 1,032 + two leaf "
                         "write/read bundles 2 x 1,670): the perimeter at <= 6 pins/um sets the outline, not the area"},
         "pin_regs": {"enable": False, "reason": "the RTL registers every input at its pin and launches every output from a "
                      "flop; flow pin registers would add an unpriced edge"},
         "reset_landing": {"enable": False, "reason": "the RTL lands rst_n in two registered stages (qfd_dv_s5_rst2)"},
         "keep_pin_regs": True, "inhold": False, "outhold": False, "io_flop_at_pins": {"cols": 4, "allow_none": True},
         "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 48, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
                   "pin_min_tracks": 2, "period_ps": 833.333, "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}},
         "safe_design_checklist": CL, "children": [], "inter": [],
         "structural_change": why or ("QW-SLICE7 successor of qfd_dv_s5_xhead after its gate3 mapped census FAIL (75 drivers "
                                      ">32, max 2585) and reg->out comb retag: bounded netlist + in-core retag + IN_PIPE"),
         "job": {"owner": "Claude:QW-SLICE7-LEAVES", "branch": "claude/qw-slice7-xhead-1020", "tag": tag,
                 "purpose": "QW-SLICE7 Q.STA.SLICE.2: slice2 column head leaf xhead2 (bounded fanout, registered retag), one master x 4",
                 "extra_paths": ["rtl", "tools/die_port_bind.py", EV],
                 "benches": [
                     {"name": "xh7_eq", "cmd": f"{RUN} {{RUN}}/bench/eq eq", "expect": "pass", "pass_regex": "XH7_EQ PASS",
                      "threads": 8, "peak_ram_gb": 32, "needs": ["verilator"]},
                     {"name": "xh7_mut", "cmd": f"{RUN} {{RUN}}/bench/mut mut", "expect": "fail", "fail_regex": "XH7_EQ FAIL mismatches=",
                      "threads": 8, "peak_ram_gb": 32, "needs": ["verilator"], "fail_witness": EV + "/bench/mut.log"}],
                 "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}"},
         "macros": []}
    s["pin_ranges"] = H.ranges(pins, w, h)
    return s


def main():
    alt = {"N": ["n_d", "cid", "ck", "rst_n", "s_d"], "W": H.xh_pins()["W"], "E": H.xh_pins()["E"], "S": ["a_f"]}
    out = {"qfd_dv_s5_xhead2": spec("qfd_dv_s5_xhead2", 216.0, 432.0, H.xh_pins(), "xh2"),
           "qfd_dv_s5_xhead2b": spec("qfd_dv_s5_xhead2b", 302.4, 345.6, alt, "xh2b",
                                     "fallback of qfd_dv_s5_xhead2: 302.4 x 345.6 (aspect 1.14, same perimeter) for a shorter clock "
                                     "span (xheadb 259.2 x 432 failed spread 88.3/84.5)")}
    for n, s in out.items():
        (D / f"{n}.json").write_text(json.dumps(s, indent=1) + "\n"); print("wrote", D / f"{n}.json")


if __name__ == "__main__":
    main()
