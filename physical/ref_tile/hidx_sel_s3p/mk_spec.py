#!/usr/bin/env python3
"""L2H-IDXSEL s3: the landed parent kit spec hidx_sel_s3p (top = the lp.py module ot_hidx_s3_flat_lp)."""
import json, sys
from pathlib import Path
WT = Path(__file__).resolve().parents[3]
QV = sys.argv[1] if len(sys.argv) > 1 else 'b'      # CLOSED s3u quadrant variant
CV = sys.argv[2] if len(sys.argv) > 2 else 'a'      # which ctl child kit
SRAM = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2'
cw, ch = (43.2, 54.0) if CV == 'a' else (54.0, 64.8)
# 600 x 450 (the d4g idx_sel slot): W margin 10.8 | q 259.2 | centre column 60 | q 259.2 | E margin 10.8
# rows: bottom 4.32 | q 216 | 9.36 | q 216 | 4.32 ; top row u_q0 (W) / u_q1 (E), bottom row u_q2 (W) / u_q3 (E)
xW, xE, yB, yT = 43.2, 388.8, 43.2, 388.8
cx, cy = 302.4, 302.4
ins = ["rst_n", "op", "pass", "addr", "k", "in_line_0", "in_line_1", "in_line_2", "in_line_3"]
outs_q = {q: [f"selected_v_{q}", f"selected_line_{q}"] for q in range(4)}
s = dict(
    name="hidx_sel_s3p", top="ot_hidx_s3_flat_lp", kind="cluster",
    sources=["rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp_hard.sv", "rtl/common/landed_parent/ot_pl_land.sv",
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
    outline={"w": 691.2, "h": 648.0, "exact": True},
    macros=[],
    children=[
        {"view": f"physical/ref_tile/hidx_sel_s3u_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q0", "at": [xW, yT]},
        {"view": f"physical/ref_tile/hidx_sel_s3u_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q1", "at": [xE, yT]},
        {"view": f"physical/ref_tile/hidx_sel_s3u_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q2", "at": [xW, yB]},
        {"view": f"physical/ref_tile/hidx_sel_s3u_{QV}/views/ot_hidx_s3_q", "count": 1, "inst": "u_q3", "at": [xE, yB]},
        {"view": f"physical/ref_tile/hidx_sel_s3d_{CV}/views/ot_hidx_s3_ctl", "count": 1, "inst": "u_ctl", "at": [cx, cy], "at_exact": True}],
    pins={"W": ["in_line_0", "in_line_1", "in_line_2", "in_line_3"],
          "E": ["selected_v_0", "selected_line_0", "selected_v_1", "selected_line_1", "selected_v_2", "selected_line_2",
                "selected_v_3", "selected_line_3"],
          "S": ["ck_ctl", "ck_q0", "ck_q1", "ck_q2", "ck_q3", "rst_n", "op", "pass", "addr", "k", "fault"]},
    pin_ranges={
        # W: top row (u_q0 W quadrant, u_q1 crosses over u_q0 on M6/M7), bottom row (u_q2, u_q3)
        "in_line_0": [391.2, 497.2], "in_line_1": [498.2, 604.2], "in_line_2": [44.0, 150.0], "in_line_3": [151.0, 257.0],
        "selected_v_0": [391.2, 391.4], "selected_line_0": [392.2, 497.2], "selected_v_1": [498.2, 498.4], "selected_line_1": [499.2, 604.2],
        "selected_v_2": [44.0, 44.2], "selected_line_2": [45.0, 150.0], "selected_v_3": [151.0, 151.2], "selected_line_3": [152.0, 257.0],
        "ck_ctl": [299.0, 299.2], "ck_q0": [280.0, 280.2], "ck_q1": [318.0, 318.2], "ck_q2": [276.0, 276.2], "ck_q3": [322.0, 322.2],
        "rst_n": [301.0, 301.2], "op": [289.0, 290.0], "pass": [290.2, 290.8], "addr": [291.0, 293.0], "k": [293.2, 296.0],
        "fault": [303.0, 303.2]},
    route={"pd": 0.5, "threads": 16, "peak_ram_gb": 64, "period_ps": 833.333333, "macro_halo_um": 5.4, "hold_margin_ns": 0.03,
           "io_hold_margin_ns": 0.03, "pin_balance": {"group_max": 1, "h": "M6", "v": "M7"}},
    structural_change=("L2H-IDXSEL s3 (LEAD3-HBM route B 10-19/20): the HBM IDX selector as a LANDED-REGION cluster (lp.py, "
                       "reschedule mode): ONE hardened quadrant tile ot_hidx_s3_q x4 (2 x 2, 259.2 x 216 each) + the ctl tile in the "
                       "centre column; parent691.2x648.0 grows relay channels from invalid snapped600x450; 5 local clock regions (ck_ctl, ck_q0..3), 20 landed control crossings (1,252 flops), 1-bit "
                       "reset runs only; the line faces are per-quadrant ports on their quadrant clock (W in_line, E selected). "
                       "Die master ot_hbm_idx_selector_s3 = zero-logic port rename of this top (port list == ot_hbm_idx_selector_static_sel)."),
    slot_change_request=("d4g idx_sel slot grows 600 x 450 -> 691.2 x 648.0; 86.4um vertical /129.6um horizontal centre bands and43.2um outer channels; faces: W in_line (as granted), E selected (as granted), S = control / "
                         "clocks / reset / fault (the granted S face, freed by the removed out_line emit face); the line ports are "
                         "split per quadrant (die master wrapper restores the die port list)."),
    job=dict(owner="Codex CODEX-HBM-IDX-1021", branch="codex/hbm-idx-s3p-1021", tag=f"s3p{QV}{CV}",
             purpose=f"CLOSED s3u_b + s3d_a: L2H-IDXSEL s3 landed IDX selector parent (children hidx_sel_s3u_{QV} x4 + hidx_sel_s3d_{CV}).",
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
