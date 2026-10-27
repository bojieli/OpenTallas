#!/usr/bin/env python3
"""QW-S5-XHEAD 10-21: ref_tile specs of qfd_dv_s5_xhead3 (structural successor of the slice2 column head leaf
qfd_dv_s5_xhead, same ports as qfd_dv_s5b_su8p2_lp u_xh0..3), main + structurally different parallel fallback.
python3 tools/ref_tile/specs_qw_s5_xhead/gen_xhead3_specs.py"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
SRC = ["rtl/lib/ot_rst_relay.sv", "rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv"]
EXTRA = ["rtl/lib", "rtl/hdc/ot_hdc_delay.sv", "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv", "rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv",
         "rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv", "rtl/test/qwen_dv/s5/xhead3", "results/arch/qw_s5_xhead_1021"]
RUN = "bash rtl/test/qwen_dv/s5/xhead3/run.sh"
WIT = "results/arch/qw_s5_xhead_1021/witness"


def bench(name, mode, expect):
    b = {"name": name, "cmd": f"{RUN} {{RUN}}/{name} {mode}", "expect": expect, "threads": 8, "peak_ram_gb": 24,
         "needs": ["verilator"]}
    if expect == "pass":
        b["pass_regex"] = "S5_XH3_EQ ALL PASS"
    else:
        b["fail_regex"] = "S5_XH3_EQ FAIL"
        b["fail_witness"] = f"{WIT}/mut_{mode}.log"
    return b


W = {"ck": 1, "rst_n": 1, "cid": 6, "fault_i": 1, "a_d": 1567, "n_d": 516, "s_d": 516, "lw_v": 2, "lw_ep": 2, "lc_v": 2,
     "lc_ep": 2, "lw_off": 12, "lw_m": 128, "lw_d": 2048, "lw_ctl": 144, "lr_v": 8, "lr_t": 8, "lr_ep": 8, "lr_p": 224,
     "lq": 512, "lq_v": 8, "lq_bad": 8, "l_rst_n": 1, "fault": 1}
PINS = {"N": ["n_d", "cid", "ck", "rst_n", "l_rst_n", "fault", "s_d"],
        "E": ["fault_i", "a_d"],
        "W": ["lc_v", "lc_ep", "lw_v", "lw_ep", "lw_off", "lw_ctl", "lw_m", "lw_d"],
        "S": ["lr_v", "lr_t", "lr_ep", "lr_p", "lq_v", "lq_bad", "lq"]}


def ranges(pins, w, h, margin=4.32):
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


def checklist(w, h, census, price):
    dens = {f: round(sum(W[p] for p in ps) / ((w if f in "NS" else h) - 8.64), 2) for f, ps in PINS.items()}
    return {
        "1_pins": "PASS: every input lands in a pin flop (stage P: p_g/p_ib/p_f/p_foff x3, cid_q, lqp/lqvp/lqbp, fi_q); every "
                  "output is a flop Q (lw/lc kept per-chain regs, lr0_*, n_q/s_q with the retag moved before them, fault_r, "
                  "l_rst_n = relay copy); rst_n -> ot_rst_relay 2 sync + 1 kept relay stage",
        "2_reach": f"PASS: {w} x {h} tile, every hop < 405 um",
        "3_fanout": "PASS (mapped census): " + census + "; kept register copies, no buffer trees",
        "4_depth": "PASS (mapped textbook depth): see census; no adder after adder in one stage, registered one-hot selects",
        "5_storage": "PASS: largest indexed arrays: windows e_W[2][16] x 18 + e_lo[2][16] x 6 = 768 b, epoch fields 2 x 71 b: < 2 kb",
        "6_floorplan": f"pin-bound leaf (no macros, full std-cell area): pins spread over whole faces by pin_ranges ({dens} pins/um); "
                       f"aspect {round(max(w, h) / min(w, h), 2)}:1",
        "7_clock": "one centre-fed TritonCTS root (~12k sinks, one region); io_hold_margin 0.03",
        "8_schedule": price}


PRICE = ("+1 edge on every a_d path (fill -> leaf write, go/ib -> corridor DX 14 -> 15, read request issue), +1 reset release "
         "(3 edges incl. l_rst_n); lq answers and fault_i -> fault latency unchanged; all intra-column relative timing "
         "(FILL_LEAD 5, QD 8, TDM) unchanged; throughput unchanged (a go every >= 8 k tiles edges as before)")


def spec(name, w, h, purpose, tag, census, why_fb=None):
    s = {"name": name, "top": "qfd_dv_s5_xhead3", "kind": "tile", "sources": SRC, "params": {}, "clock_port": "ck",
         "reset_ports": ["rst_n"], "outline": {"w": w, "h": h, "exact": True}, "layer_cap": "M5", "recipe": 4,
         "hold_budget": "die", "pins": PINS,
         "pin_regs": {"enable": False, "reason": "the RTL registers every input at its pin (stage P) and drives every output "
                      "from a flop; flow pin registers would add unpriced cycles"},
         "reset_landing": {"enable": False, "reason": "the RTL lands rst_n in ot_rst_relay (2 sync stages + 12 kept regional relay copies)"},
         "keep_pin_regs": True, "inhold": False, "outhold": False, "io_flop_at_pins": {"cols": 4, "allow_none": True},
         "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 48, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
                   "pin_min_tracks": 2, "period_ps": 833.333, "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}},
         "fill_reason": {"pin_bound": "5,726 signal pins (a_d 1,567 E, lw 2,340 W, corridor 1,032 N, leaf read 776 S) set the outline; logic ~12k flops"},
         "safe_design_checklist": checklist(w, h, census, PRICE), "children": [], "inter": [],
         "job": {"owner": "Claude:QW-S5-XHEAD", "branch": "claude/qw-s5-xhead-1021", "tag": tag, "purpose": purpose,
                 "extra_paths": EXTRA,
                 "benches": [bench("xh3_eq", "pass", "pass"), bench("xh3_mut_retag", "retag", "fail"),
                             bench("xh3_mut_rot", "rot", "fail"), bench("xh3_mut_poolw", "poolw", "fail"),
                             bench("xh3_mut_fwd", "fwd", "fail")]},
         "structural_change": why_fb or ("successor of qfd_dv_s5_xhead (census FAIL 75 drivers > 32, max 2,585; xheadJ 771.8 ps): "
                                         "input stage + kept per-consumer copies, retimed window pipeline, registered read-sequencer selects"),
         "pin_ranges": ranges(PINS, w, h)}
    return s


def main(census="see results/arch/qw_s5_xhead_1021/native"):
    out = {"qfd_dv_s5_xhead3": spec("qfd_dv_s5_xhead3", 216.0, 432.0,
                                    "QW-S5-XHEAD: slice2 column head leaf successor (fanout/depth-safe), one master x 4", "xh3", census),
           "qfd_dv_s5_xhead3b": spec("qfd_dv_s5_xhead3b", 259.2, 518.4,
                                     "QW-S5-XHEAD parallel fallback of qfd_dv_s5_xhead3: 259.2 x 518.4 (+44% area), lower pin density",
                                     "xh3b", census,
                                     "fallback: 259.2 x 518.4 (W 4.6 / N 4.2 pins/um vs 5.5 / 5.0) for pin access and placement room")}
    for n, s in out.items():
        (D / f"{n}.json").write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", D / f"{n}.json")


if __name__ == "__main__":
    import sys
    main(*sys.argv[1:2])
