#!/usr/bin/env python3
"""Assemble coll/rows.json from the committed route records (coll/routes/<label>/{physical,corner_sta}.json)."""
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1]
REL = "results/rtl/hbm_accel_fmax_inventory_20261004/qwen_core/coll"
F = "rtl/hbm_accel/qwen/fmax"


def route(label):
    r = D / "routes" / label
    if not (r / "corner_sta.json").exists():
        return {"route": f"{REL}/routes/{label}", "status": "missing"}
    c = json.loads((r / "corner_sta.json").read_text())
    p = json.loads((r / "physical.json").read_text())
    s = p.get("synthesis", {})
    return {
        "route_record": [f"{REL}/routes/{label}/physical.json", f"{REL}/routes/{label}/corner_sta.json"],
        "period_ns": 0.833,
        "ss_r2r_ps": c["setup_ss"]["worst_reg_to_reg_slack_ps"],
        "ss_worst_ps": c["setup_ss"]["worst_slack_ps"],
        "ss_input_to_reg_ps": c["setup_ss"]["worst_input_to_reg_slack_ps"],
        "ss_output_port_ps": c["setup_ss"]["worst_output_port_slack_ps"],
        "ff_hold_ps": c["hold_ff"]["worst_slack_ps"],
        "closes_signoff": c["closes_signoff"],
        "false_path_io": "no: IO constrained at 20% input/output delay; the c_*/r_* sequencer<->engine handshake is internal to the context wrapper",
        "cell_area_um2": s.get("cell_area_um2"),
        "macro_count": s.get("macro_count"),
    }


def main():
    ex = json.loads((D / "exactness.json").read_text())
    a, b = route("ctx_a_n2d16"), route("ctx_b_n4d1024")
    common_seq = {
        "file": f"{F}/ot_qwen_tp_seq_w12_f12.sv",
        "on_token_path": "yes: every all-reduce / argmax segment of every layer and the head runs through it "
                         "(ot_qwen_hbmacc_rt_die_w12 instance 'seq')",
        "fix": "REG_OUT=1: vm_re, vm_raddr, c_valid, c_last, c_mode are registers loaded from the FSM's next state "
               "(zero-cycle look-ahead); internal rd_go / c_fire read those registers",
        "cycles_added": {"per_collective": 0, "per_token": 0},
        "exactness": ex["tp_seq"],
    }
    common_os = {
        "file": f"{F}/ot_rom_oneshot_die_f12.sv",
        "on_token_path": "yes: every all-reduce (2 per layer) and the head argmax gather (HA8 'coll' model)",
        "exactness": ex["oneshot"],
    }
    rows = [
        dict(module="ot_qwen_tp_seq_w12 -> ot_qwen_tp_seq_w12_f12", build="a TP2",
             params={"N": 2, "REG_OUT": 1, "NW": 18, "QWEN_FULLSHAPE": 1, "ENABLE_AR256": 0},
             before={"evidence": "never routed at N=2", "period_ns": None, "ss_r2r_ps": None, "ff_hold_ps": None},
             after=dict(a, context="ot_qwen_coll_ctx_f12 N=2 DEPTH=16 FIFO_IMPL=1 ADD_IMPL=1"), **common_seq),
        dict(module="ot_qwen_tp_seq_w12 -> ot_qwen_tp_seq_w12_f12", build="b TP4",
             params={"N": 4, "REG_OUT": 1, "NW": 18, "QWEN_FULLSHAPE": 1, "ENABLE_AR256": 0},
             before={"evidence": "results/rtl/risk_clock_loops_20261003/routes/qwen_tp_seq_0833/corner_sta.json",
                     "period_ns": 0.833, "ss_r2r_ps": 6.99, "ss_worst_ps": -73.69, "ff_hold_ps": 10.6,
                     "note": "output ports c_last / vm_raddr -73.7 ps"},
             after=dict(b, context="ot_qwen_coll_ctx_f12 N=4 DEPTH=1024 FIFO_IMPL=2 ADD_IMPL=1"), **common_seq),
        dict(module="ot_rom_oneshot_die -> ot_rom_oneshot_die_f12", build="a TP2",
             params={"N": 2, "DEPTH": 16, "LANES": 16, "TAGW": 32, "FIFO_IMPL": 1, "ADD_IMPL": 1, "OQD": 4},
             before={"evidence": "results/rtl/risk_clock_loops_20261003/screens/qwen/oneshot_die_d32_833.json "
                                 "(screen, N=4 DEPTH=32; N=2 DEPTH=16 never measured)",
                     "period_ns": 0.833, "ss_r2r_ps": -1208, "ff_hold_ps": None},
             after=dict(a, context="ot_qwen_coll_ctx_f12 (with the tp_seq successor)"),
             fix="registered output queue (OQD 4) per source in front of flop storage with push bypass: head, "
                 "mode bit and non-empty are registers, pop is an AND of registered flags; adders "
                 "ot_fp32_add_rne_pipe (LAT5, ~1.09 GHz SS) -> ot_hdc_fp32_add_lat LAT7 (keep-prefix)",
             cycles_added={"per_all_reduce": 2, "per_gather": 0, "fifo_change_alone": 0,
                           "per_token": "2 x all-reduces per token (72 at 36 layers x 2) = +144 cycles",
                           "note": "serial-sequencer bench, no stalls: every all-reduce exactly +2 (2 x (N-1)), "
                                   "gathers +0; ADD_IMPL=0 (FIFO change alone) +0 on every collective"},
             **common_os),
        dict(module="ot_rom_oneshot_die -> ot_rom_oneshot_die_f12", build="b TP4",
             params={"N": 4, "DEPTH": 1024, "LANES": 16, "TAGW": 32, "FIFO_IMPL": 2, "ADD_IMPL": 1, "OQD": 4,
                     "macros": "per source 2 banks x 3 ot_sram_1r1w_512x256_m1_r2c2 (24 total)"},
             before={"evidence": "results/rtl/risk_clock_loops_20261003/screens/qwen/oneshot_die_d32_833.json "
                                 "(screen at DEPTH=32; the DEPTH-1024 flop FIFO (2.2 Mbit of flops) is not physical)",
                     "period_ns": 0.833, "ss_r2r_ps": -1208, "ff_hold_ps": None},
             after=dict(b, context="ot_qwen_coll_ctx_f12 (with the tp_seq successor)",
                        sdc=f"{F}/ot_rom_oneshot_die_f12_mc2.sdc"),
             fix="SRAM storage (even/odd 512x256 macro banks, two-cycle macro capture as the closed bulk copy) + "
                 "registered 4-entry output queue with push bypass; pop from registered flags; LAT7 adders",
             cycles_added={"per_all_reduce": 6, "per_gather": 0, "fifo_change_alone": 0,
                           "per_token": "6 x all-reduces per token (72) = +432 cycles",
                           "note": "serial-sequencer bench, no stalls: every all-reduce exactly +6 (2 x (N-1)), "
                                   "gathers +0; the SRAM FIFO alone (ADD_IMPL=0) +0"},
             **common_os),
    ]
    (D / "rows.json").write_text(json.dumps({"schema": "opentallas.hbm_accel.fmax_closure_rows.v1",
                                             "family": "qwen-core/coll", "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
