#!/usr/bin/env python3
"""Source-bound item7 capture recipe and finite parent-clock admission equations.

This successor never manufactures launch latency from a fractional IO delay.
The numerical parent is not yet an installed mesochronous ready/valid parent.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import qwen_slab_share_splitface_l7 as previous

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "tools/qwen_slab_capture_contract.py",
    "rtl/physical/ot_qwen_slab_port_group_capture.sv",
    "rtl/test/tb_qwen_slab_port_group_capture.sv",
    "physical/qwen_slab_share/capture_columns_r1.tcl",
    "tools/qwen_slab_capture_gate.sh",
    "rtl/physical/ot_qwen_slab_port_group.sv",
    "rtl/hdc/ot_qwen_w12_matvec.sv",
    "rtl/test/qwen_runtime/ot_qwen_rt_tree.sv",
    "rtl/common/ot_meso_fifo.sv",
    "rtl/test/tb_qwen_slab_port_group.sv",
    "physical/qwen_slab_m5/port_group.sdc",
    "results/uarch/rom_die_clocking_decision_20261003.json",
    "results/uarch/meso_fifo_20261004/verdict.json",
    "results/rtl/qwen_slab_share_20261005/l7_physical_terminal/terminal.json",
    "results/uarch/dsrom_field_native_VM_join_20261003/inputs/native_provider/inputs/5_model.json",
]


def path_slacks(p):
    """All delays in ps, actual propagated parent and slab leaves, no IO waiver.

    Required evidence names identify extracted source/capture clocks and cells.
    Call independently for res_in, tags/control, and tw_v/data/ready reverse.
    SS setup and FF hold are separate source-matched corner records.
    """
    required = ("source_identity", "capture_identity", "ss_evidence_sha256", "ff_evidence_sha256")
    for k in required:
        if not p.get(k):
            raise ValueError("missing " + k)
    for k in ("ss_evidence_sha256", "ff_evidence_sha256"):
        v = p[k]
        if len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
            raise ValueError("invalid " + k)
    for corner in ("ss", "ff"):
        c = p[corner]
        for k in ("launch_clock", "capture_clock", "clk_q", "wire"):
            lo, hi = c[k]
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (lo, hi)) or lo < 0 or hi < lo:
                raise ValueError("invalid finite " + corner + "/" + k)
    ss, ff = p["ss"], p["ff"]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0
               for v in (ss["setup"], ff["hold"])):
        raise ValueError("negative cell constraint")
    setup = (833.333 + ss["capture_clock"][0] - 60 - ss["setup"]
             - ss["launch_clock"][1] - ss["clk_q"][1] - ss["wire"][1])
    hold = (ff["launch_clock"][0] + ff["clk_q"][0] + ff["wire"][0]
            - ff["capture_clock"][1] - ff["hold"] - 25)
    return dict(ss_setup_slack_ps=setup, ff_hold_slack_ps=hold,
                pass_path=setup >= 0 and hold >= 10,
                hold_repair_margin_ps=10)


INPUT_GROUPS = ("bw_rst_n", "bw_v", "bw_d*", "rst_n", "tw_rdy", "p_*", "res_in*")
OUTPUT_GROUPS = ("bw_rdy", "bw_w_fault", "bw_w_live", "tw_v", "tw_d*", "o_we",
                 "o_addr*", "o_mask*", "o_data*", "ov", "am_tv", "am_top*",
                 "am_rmax", "fault", "bw_r_fault", "bw_r_live")


def parent_io_sdc(contract):
    """Replace the fractional IO assumption only with complete finite evidence.

    Delays are root-relative ps, from actual parent leaf/cell/wire bounds.
    Negative output delay represents a finite propagated receiver clock, not
    a timing waiver. All uncertainty, cross-clock guards and fanout survive.
    Numeric loads must be in the evidenced STA library's load units.
    """
    if set(contract) != set(INPUT_GROUPS + OUTPUT_GROUPS):
        raise ValueError("complete 23-group parent IO contract required")
    baseline = (ROOT / "physical/qwen_slab_m5/port_group.sdc").read_text()
    head = baseline.split("# Boundary:", 1)[0]
    lines = [head.rstrip(), "# Source-owned parent IO bounds; no fractional-delay fallback."]
    for name in INPUT_GROUPS + OUTPUT_GROUPS:
        p = contract[name]
        if not path_slacks(p)["pass_path"]:
            raise ValueError("prospective SS/FF path budget fails for " + name)
        clock = "bw_clk" if name.startswith("bw_") and name not in ("bw_r_fault", "bw_r_live") else "clk"
        ss, ff = p["ss"], p["ff"]
        if name in INPUT_GROUPS:
            hi = ss["launch_clock"][1] + ss["clk_q"][1] + ss["wire"][1]
            lo = ff["launch_clock"][0] + ff["clk_q"][0] + ff["wire"][0]
            cmd = "set_input_delay"
        else:
            hi = ss["wire"][1] + ss["setup"] - ss["capture_clock"][0]
            lo = ff["wire"][0] - ff["hold"] - ff["capture_clock"][1]
            cmd = "set_output_delay"
            load = p.get("output_load_sta_units")
            if not isinstance(load, (int, float)) or not math.isfinite(load) or load <= 0:
                raise ValueError("finite positive source-derived load required for " + name)
            units_sha = p.get("load_library_sha256", "")
            if len(units_sha) != 64 or any(c not in "0123456789abcdef" for c in units_sha):
                raise ValueError("load library evidence required for " + name)
            lines.append(f"set_load {load:.9g} [get_ports {{{name}}}]")
        lines.append(f"{cmd} -max {hi:.9g} -clock {clock} [get_ports {{{name}}}]")
        lines.append(f"{cmd} -min {lo:.9g} -clock {clock} [get_ports {{{name}}}]")
    lines.append("set_max_fanout 32 [current_design]")
    return "\n".join(lines) + "\n"


def physical_args():
    args = previous.predecessor.args(570.24)
    i = args.index("^res_in=top")
    constraints = []
    for c in range(4):
        lo = 40 + c * (775.416 - 40) / 4
        hi = 40 + (c+1) * (775.416 - 40) / 4
        pattern = "^res_in\\[(" + "|".join(str(b) for b in range(128*c, 128*(c+1))) + ")\\]$"
        if c:
            constraints.append("--pin-region")
        constraints.append(f"{pattern}=top:{lo:g}-{hi:g}")
    args[i:i+1] = constraints
    return args


def model():
    r = previous.model()
    r.update(schema="opentallas.qwen_slab_capture_contract.v1",
        variant="s570_l7_column_capture_m7", recipe_variant_index=3,
        implementation="rtl/physical/ot_qwen_slab_port_group_capture.sv",
        selection={"top": "ot_qwen_slab_port_group_capture", "COLUMN_CAPTURE": 1,
                   "MUL_LAT": 7, "BW_FIFO": 1},
        capture={"columns": 4, "bits_each": 128, "existing_bits": 512,
                 "new_ff_bits": 0, "ff_cell_area_um2_existing": 512 * 0.2916,
                 "ff_50pct_reservation_um2_existing": 512 * 0.2916 / 0.5,
                 "added_clk_reset_pins": 0, "added_data_muxes": 0,
                 "added_capture_cycles": 0, "enable_or_reset_added_to_data": False,
                 "placement_band_um": [40.0, 540.0, 775.416, 568.08],
                 "placement_band_area_um2": (775.416-40) * (568.08-540),
                 "placement_legal_or_cts_closed": False},
        ports={"res_in_bits_per_cycle": 512, "tw_data_bits_per_cycle": 512,
               "bw_data_bits_per_cycle": 512, "bytes_per_cycle_each": 64,
               "new_boundary_tracks": 0, "new_memory_ports": 0,
               "new_MACs_per_cycle": 0, "new_replicas": 0,
               "existing_fifo_credits_plus_output": 9,
               "existing_fifo_offset_periods": 2,
               "added_fifo_or_output_capture_cycles": 0,
               "route_capacity_proof": None},
        parent={"module": "ot_qwen_w12_matvec_part",
                "producer": "g_lvl[LG].lq -> lvl[LG] -> raw_res -> slab.res_in",
                "capture": "slab.g_capture_columns.g_res_col[c].q -> res_q -> g_mul[*]",
                "tree_input": "slab.g_bw.u_bw.o_v/o_d -> tw_v/tw_d -> parent.t_in -> lvl[LV0]",
                "receiver": "g_lvl[LV0+1].g_add[*].u_add or u_hold",
                "native_parent_instantiates_slab": False,
                "native_t_in_has_ready_valid_handshake": False,
                "native_valid": "vline and split_at from sequenced source timing",
                "required_join": "Bind FIFO accepted word and matched valid/split/tag epoch into the actual tree schedule; export finite receiver capacity. No tw_rdy=1 assumption qualifies this join.",
                "clock_allocation": "Decision C spine_band regional clk and block forwarded bw_clk",
                "producer_clk_q_wire_and_leaf_arrivals": None,
                "receiver_leaf_setup_hold_and_wire": None,
                "startup": {"copy_cycles_clk": 2, "copy_cycles_bw_clk": 1,
                            "fifo_HOLD": 8, "fifo_SETTLE": 8,
                            "peer_state_sync_ff": 3, "peer_state_stable_filter": 1,
                            "owned_parent_reset_release_and_ack": None,
                            "complete_startup_cycles": None,
                            "added_capture_startup_cycles": 0,
                            "readiness_not_inferred_from_idle": True}},
        functional_scope={"historical_1505_arithmetic_gate_BW_FIFO": 0,
                          "physical_BW_FIFO": 1,
                          "isolated_fifo_evidence_reused_only_as_primitive": True,
                          "new_gate_required": "changed column capture arithmetic plus connected FIFO phase/stall/reset traffic",
                          "full_parent_schedule_gate": False,
                          "digital_test_period_ps": 1000,
                          "test_period_is_not_physical_clock_or_STA_evidence": True,
                          "ring_powerup": "arbitrary binary counters explicitly initialized by four-state testbench only; no hardware reset",
                          "tested_seed_pairs_if_gate_passes": [[0,7], [3,2], [5,4], [7,0]]},
        failure_preservation={"lat6_hold_buffers": 33614, "lat7_hold_buffers": 34174,
                              "lat7_setup_endpoint": "tw_v (primary output)",
                              "lat7_hold_endpoint": "res_q[126] D pin",
                              "lat7_ssff_final": None,
                              "external_paths_not_declared_internal_failures": True},
        physical_args=physical_args(),
        physical_launch_admitted=False,
        prerequisites=["Changed RTL connected BW_FIFO=1 gate PASS",
                       "Actual source-owned FIFO-to-tree word/valid/split/tag and readiness join",
                       "Propagated SS/FF parent and slab leaf/cell/wire bounds for all boundary paths",
                       "Column capture pin landing/group census and legal placement",
                       "CTS, routing, slew/cap and SS60/FF25 closure without IO exemptions"],
        parent_io_generator="Complete 23-group finite source-owned SS/FF IO bounds plus evidenced receiver loads; refuses missing groups. No 0.2T fallback; physical path remains unqualified until actual context closes.",
        sourcepins={s: hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES})
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    p.add_argument("--parent-path", type=Path)
    p.add_argument("--parent-io", type=Path)
    p.add_argument("--sdc-out", type=Path)
    a = p.parse_args()
    if bool(a.parent_io) != bool(a.sdc_out):
        p.error("--parent-io and --sdc-out are required together")
    if a.parent_io:
        a.sdc_out.write_text(parent_io_sdc(json.loads(a.parent_io.read_text())))
    r = model()
    if a.parent_path:
        r["provided_parent_path"] = path_slacks(json.loads(a.parent_path.read_text()))
        # One path never admits the complete boundary or the FIFO schedule.
    data = json.dumps(r, indent=2, sort_keys=True) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(data)
    else:
        print(data, end="")


if __name__ == "__main__":
    main()
