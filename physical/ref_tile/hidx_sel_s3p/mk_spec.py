#!/usr/bin/env python3
"""L2H-IDXSEL s3: the landed parent kit spec hidx_sel_s3p (top = the lp.py module ot_hidx_s3_flat_lp)."""
import json, sys
from pathlib import Path
WT = Path(__file__).resolve().parents[3]
QV = sys.argv[1] if len(sys.argv) > 1 else 'a'      # which quadrant child kit (a | b)
CV = sys.argv[2] if len(sys.argv) > 2 else 'a'      # which ctl child kit
SRAM = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2'
cw, ch = (43.2, 54.0) if CV == 'a' else (54.0, 64.8)
# 600 x 450 (the d4g idx_sel slot): W margin 10.8 | q 259.2 | centre column 60 | q 259.2 | E margin 10.8
# rows: bottom 4.32 | q 216 | 9.36 | q 216 | 4.32 ; top row u_q0 (W) / u_q1 (E), bottom row u_q2 (W) / u_q3 (E)
xW, xE, yB, yT = 10.8, 330.0, 4.32, 229.68
cx, cy = round(300.0 - cw / 2, 3), round(225.0 - ch / 2, 3)
ins = ["rst_n", "op", "pass", "addr", "k", "in_line_0", "in_line_1", "in_line_2", "in_line_3"]
outs_q = {q: [f"selected_v_{q}", f"selected_line_{q}"] for q in range(4)}
s = dict(
    name="hidx_sel_s3p", top="ot_hidx_s3_flat_lp", kind="cluster",
    sources=["rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp.sv", "rtl/common/landed_parent/ot_pl_land.sv",
             "rtl/hbm_accel/index/sel_s3/ot_hidx_s3_ctl.sv", "rtl/hbm_accel/index/sel_s3/ot_hidx_s3_q.sv",
             "rtl/lib/ot_rst_relay.sv", f"{SRAM}/ot_sram_1r1w_256x256_m2_r2c2_bb.v"],
    params={}, clock="multiple_cts_roots", clock_port="ck_ctl",
    clock_ports=["ck_ctl", "ck_q0", "ck_q1", "ck_q2", "ck_q3"],
    clock_data_paths="related_same_frequency",
    clock_relationship={"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0},
    clock_entry_domains={
        "core": {"ratio": [1, 1], "ports": ["ck_ctl"], "inputs": ["rst_n", "op", "pass", "addr", "k"], "outputs": ["fault"]},
        **{f"q{q}": {"ratio": [1, 1], "ports": [f"ck_q{q}"], "inputs": [f"in_line_{q}"], "outputs": outs_q[q]} for q in range(4)}},
    landed_record="results/rtl/hbm_idx_static/selector_s3/ot_hidx_s3_flat_lp_record.json",
    reset_ports=["rst_n"],
    reset_landing={"enable": False, "reason": "the lp.py RTL lands it: rst_n -> u_lpr_root (1 stage, ck_ctl) -> regional runs u_lpr_<r> -> per-child u_lprc_* pads -> each child's ot_rst_relay (2 sync + region stage); the port net has ONE sink"},
    outline={"w": 600.0, "h": 450.0, "exact": True},
    macros=[],
    children=[
        {"view": f"physical/ref_tile/hidx_sel_s3q_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q0", "at": [xW, yT]},
        {"view": f"physical/ref_tile/hidx_sel_s3q_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q1", "at": [xE, yT]},
        {"view": f"physical/ref_tile/hidx_sel_s3q_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q2", "at": [xW, yB]},
        {"view": f"physical/ref_tile/hidx_sel_s3q_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q3", "at": [xE, yB]},
        {"view": f"physical/ref_tile/hidx_sel_s3c_{CV}/views/ot_hidx_s3_ctl", "count": 1, "inst": "u_ctl", "at": [cx, cy]}],
    pins={"W": ["in_line_0", "in_line_1", "in_line_2", "in_line_3"],
          "E": ["selected_v_0", "selected_line_0", "selected_v_1", "selected_line_1", "selected_v_2", "selected_line_2",
                "selected_v_3", "selected_line_3"],
          "S": ["ck_ctl", "ck_q0", "ck_q1", "ck_q2", "ck_q3", "rst_n", "op", "pass", "addr", "k", "fault"]},
    pin_ranges={
        # W: top row (u_q0 W quadrant, u_q1 crosses over u_q0 on M6/M7), bottom row (u_q2, u_q3)
        "in_line_0": [232.0, 338.0], "in_line_1": [339.0, 445.0], "in_line_2": [6.0, 112.0], "in_line_3": [113.0, 219.0],
        "selected_v_0": [232.0, 232.2], "selected_line_0": [233.0, 338.0], "selected_v_1": [339.0, 339.2], "selected_line_1": [340.0, 445.0],
        "selected_v_2": [6.0, 6.2], "selected_line_2": [7.0, 112.0], "selected_v_3": [113.0, 113.2], "selected_line_3": [114.0, 219.0],
        "ck_ctl": [299.0, 299.2], "ck_q0": [280.0, 280.2], "ck_q1": [318.0, 318.2], "ck_q2": [276.0, 276.2], "ck_q3": [322.0, 322.2],
        "rst_n": [301.0, 301.2], "op": [289.0, 290.0], "pass": [290.2, 290.8], "addr": [291.0, 293.0], "k": [293.2, 296.0],
        "fault": [303.0, 303.2]},
    route={"pd": 0.5, "threads": 16, "peak_ram_gb": 64, "period_ps": 833.333333, "macro_halo_um": 5.4, "hold_margin_ns": 0.03,
           "io_hold_margin_ns": 0.03},
    structural_change=("L2H-IDXSEL s3 (LEAD3-HBM route B 10-19/20): the HBM IDX selector as a LANDED-REGION cluster (lp.py, "
                       "reschedule mode): ONE hardened quadrant tile ot_hidx_s3_q x4 (2 x 2, 259.2 x 216 each) + the ctl tile in the "
                       "centre column; 5 local clock regions (ck_ctl, ck_q0..3), 20 landed control crossings (1,252 flops), 1-bit "
                       "reset runs only; the line faces are per-quadrant ports on their quadrant clock (W in_line, E selected). "
                       "Die master ot_hbm_idx_selector_s3 = zero-logic port rename of this top (port list == ot_hbm_idx_selector_static_sel)."),
    slot_change_request=("d4g idx_sel slot 600 x 450 kept; faces: W in_line (as granted), E selected (as granted), S = control / "
                         "clocks / reset / fault (the granted S face, freed by the removed out_line emit face); the line ports are "
                         "split per quadrant (die master wrapper restores the die port list)."),
    job=dict(owner="Claude LEAD3-HBM/L2H-IDXSEL-S3", branch="claude/l2h-idxsel-s3-1019", tag=f"s3p{QV}{CV}",
             purpose=f"L2H-IDXSEL s3 landed IDX selector parent (children hidx_sel_s3q_{QV} x4 + hidx_sel_s3c_{CV}).",
             extra_paths=[SRAM, "rtl/lib", "rtl/common/landed_parent", "rtl/hbm_accel/index/sel_s3", "rtl/test/hbm_idx_static",
                          "tools/hbm_idx_s3_selector_vectors.py", "tools/landed_parent", "results/rtl/hbm_idx_static/selector_s3"],
             benches=[{"name": "selector_s3_lp_lockstep", "cmd": "LP_ROOT=$PWD SIM=verilator VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator bash rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp_bench.sh {RUN}/lp",
                       "expect": "pass", "threads": 8, "peak_ram_gb": 16, "pass_regex": "BENCH_EXIT 0",
                       "pass_witness": "results/rtl/hbm_idx_static/selector_s3/lp/bench.log"}]),
    inter=[], recipe=4, io_flop_at_pins={"cols": 4, "allow_none": True}, inhold=True, outhold=True, keep_pin_regs=True,
    pin_reg_split=True, hold_pad={"cell": "HB2xp67_ASAP7_75t_R"},
    pin_regs={"enable": False, "reason": "wires-only landed parent: every port lands in a hard child's pin flop (quadrant in_line_<q> -> in_p1, ctl op/pass/addr/k -> cw_r/k_r) or leaves from a child output register; the lp rings / reads are the only parent flops"})
(WT / "physical/ref_tile/hidx_sel_s3p/spec.json").write_text(json.dumps(s, indent=1) + "\n")
print("ok", QV, CV)
