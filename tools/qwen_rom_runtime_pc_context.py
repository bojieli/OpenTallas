#!/usr/bin/env python3
"""Source-pinned selected STREAM4 controller cut and slab enrollment price.

No runtime/controller replacement, simulation, synthesis or physical launch.
The historical closed controller and failed slab records remain separate.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import uarch_model as U

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/rtl/qwen_rom_runtime_pc_context_20261005"
PINS = {
    "ot_hbm_r14_stream_pc.sv": "2dcbec64d86ae8a3288a1cf150080c31a70ca423b5f2f8f73138ca51663c0883",
    "ot_hbm_r14_stream_stack.sv": "43b21ddb2a2ae2c61e5aed61b711a1c22e43e274d57c44d917ce69247484230c",
    "ot_qwen_hbm_stream4_tagged.sv": "f97ab5593d26b2861a5816774e50194b82ff7d4a4d1bdf528a187a9a321ad64e",
}
MACRO = "ot_rom_4096x266_m8"
MACRO_PINS = {
    ".lef": "f35311e2ad164c3a112aa918b73b510b84b2fdf1414a7d8da591fe71cb662611",
    ".v": "a26eebf06605ae3e9bca8d25c6d979a95553ea03ddc5e82cacd3192bf811a16b",
    "_ss.lib": "8612ab20df323464bfcdffd197cd2d087a249c2f6f2a2ec92ec8be219cf3d805",
    "_ff.lib": "d9c7e59c2e13749d2fff34790226704f512bcc767dd89584ebacddbdbbcbe346",
}


def macro_binding(root=ROOT):
    """Bind existing exact views; never regenerate/replace the selected abstract."""
    root = Path(root)
    directory = root / "physical/asap7_memory_macros" / MACRO
    views = {}
    for suffix, expected in MACRO_PINS.items():
        path = directory / (MACRO + suffix)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError("selected macro view substitution: " + str(path))
        views[path.name] = {"path": str(path.relative_to(root)), "sha256": digest}
    corners = {}
    for corner in ("ss", "ff"):
        text = (directory / (MACRO + "_" + corner + ".lib")).read_text()
        def field(block, name):
            return float(re.search(r"\b" + name + r"\s*:\s*([-\d.]+)", block).group(1))
        def block(kind, name):
            return text.split(kind + " (" + name + ") {", 1)[1]
        if 'time_unit : "1ps"' not in text or 'capacitive_load_unit (1, ff)' not in text:
            raise ValueError("macro units must be ps and fF")
        corners[corner] = {
            "clk_pin": "clk", "clk_cap_fF": field(block("pin", "clk"), "capacitance"),
            "ce_pin": "ce_in", "ce_cap_fF": field(block("pin", "ce_in"), "capacitance"),
            "addr_bus": "addr_in[11:0]", "addr_per_bit_cap_fF": field(block("bus", "addr_in"), "capacitance"),
            "output_bus": "rd_out[265:0]", "output_per_bit_max_load_fF": field(block("bus", "rd_out"), "max_capacitance"),
            "clk_min_period_ps": field(block("pin", "clk"), "min_period"),
            "clk_min_pulse_high_ps": field(block("pin", "clk"), "min_pulse_width_high"),
            "clk_min_pulse_low_ps": field(block("pin", "clk"), "min_pulse_width_low"),
            "loaded_clockq": "use complete cell_rise/cell_fall tables over input slew/output load; no scalar ideal clkQ",
            "delay_table_slew_ps": [5, 20, 80, 160, 320],
            "delay_table_load_fF": [.72, 2.88, 11.52, 23.04, 46.08],
        }
    lef = (directory / (MACRO + ".lef")).read_text()
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", lef).groups())
    return {"views": views, "source_producer": "tools/mem_compiler/rom_gen.py",
            "EPYC1_retained_root": "/srv/opentallas/repos/laplace-qwen-tagged-accept1-a60af57e4",
            "remote_three_view_hashes_verified": True,
            "corners": corners, "dimensions_um": [w, h], "macro_count": 624,
            "total_existing_macro_area_um2": 624 * w * h,
            "total_macro_clock_pin_cap_fF": 624 * max(c["clk_cap_fF"] for c in corners.values()),
            "scale_port_address_per_bit_cap_fF": 13 * max(c["addr_per_bit_cap_fF"] for c in corners.values()),
            "payload_bits_used": 256, "physical_output_pins": 266,
            "ECC_logic_added": False, "macro_area_is_existing_once_only": True,
            "physical_clock_driver": "selected_top.g_sc[*].u_bank.clk=clk; re=scale_gre[*] && me_clk_en; bank.u_rom.clk=clk",
            "receiver_output_load_fF": None, "contextual_SS_FF_qualified": False,
            "track_alignment": "exact v1 views match enrollment; v1 mirrored pin-grid limitations retained",
            "aligned_successor": {"directory": "physical/asap7_memory_macros_v2/" + MACRO,
                                  "dimensions_um": [121.848, 62.952],
                                  "extra_area_um2_for_624": 624 * (121.848 * 62.952 - w * h),
                                  "selected": False,
                                  "hook": "tools/run_abi3_physical.py --macro-view NAME=directory",
                                  "requires": "explicit successor geometry/track/slot enrollment; never silent substitution"},
            "landing_owner": "Peirce selected inline FILL8; no historical leaf substitution"}


def compose(inputs=None):
    inputs = Path(inputs) if inputs else BASE / "inputs"
    for name, expected in PINS.items():
        if hashlib.sha256((inputs / name).read_bytes()).hexdigest() != expected:
            raise ValueError("selected runtime source mismatch; no controller substitution: " + name)
    programs = json.loads((inputs / "source_program_counts.json").read_text())
    if not programs["all_rank_counts_equal"] or len(programs["stages"]) != 37:
        raise ValueError("actual full36+HEAD, all four source ranks required")
    count = sum(len(s["ranks"][0]["source_reachable_ME_pcs"]) for s in programs["stages"])
    if count != programs["reachable_ME_commands_per_rank"]:
        raise ValueError("source instruction conservation failure")
    for stage in programs["stages"]:
        if len(stage["ranks"]) != 4 or any(
                r["source_reachable_ME_pcs"] != stage["ranks"][0]["source_reachable_ME_pcs"]
                for r in stage["ranks"]):
            raise ValueError("source rank instruction mismatch")
    # Exact source integer accumulator, measured in fs; metadata, not a DUT run.
    acc, edges = 0, []
    for cycle in range(4096):
        acc += 833333
        if acc >= 1024000:
            acc -= 1024000
            edges.append(cycle * 833333 + 833333 // 2)
    intervals = sorted(set(b-a for a, b in zip(edges, edges[1:])))
    return {
        "schema": "opentallas.qwen.rom.selected-runtime-controller-context.r1",
        "selected_macro_binding": macro_binding(),
        "selected_pc_sha256": PINS["ot_hbm_r14_stream_pc.sv"],
        "historical_closed_pc_sha256": "a2cfb09b7868936ca886c9e92b68f08ecffdd1e8236ee1313f8ffce9d2b33dcf",
        "selection": {"controller": "literal successful runtime 2dcbec64",
                      "postscale_candidate": "LAT6 only, default off and NOT enrolled",
                      "BF16_lane_MUL_LAT": 5, "ACC_LAT": 5, "TREE_LAT": 3},
        "controller": {"stacks": 4, "NCH_per_stack": 16, "PCs": 128,
                       "ENABLE": 1, "REF_MODE": 1, "CRED": 32,
                       "WR_EN": 1, "WQ": 4, "PULLIN": 16, "AQ_RD": 1, "PHASE": 0,
                       "MACs_per_edge": 0, "added_pipeline_edges": 0},
        "function_cut": {
            "top": "ot_hbm_r14_stream_pc", "PC": 0,
            "row_gnt": "actual enclosing stack ties row_gnt=1; no arbitration shortcut",
            "changed_expression": "wq_ne && |(hb_oh & open & ~stale & ((AQ && hr) ? rcd_z : rcdw_z) & ~blk & (AQ ? open_nx : 32'hffffffff))",
            "feedback": ["hr/head register", "row_fire/c_op/c_oh -> open_nx",
                         "bank rcd/rcdw", "wr_ok -> queue and timing state", "rd_ok"],
            "new_experiment_result": None},
        "loaded_context": {
            "top": "ot_qwen_stream4_runtime_controller_context",
            "desc_row_fanout": 128, "desc_n_fanout": 128, "go_fanout": 128,
            "desc_ready_leaf_inputs": 128, "next_posted": 0,
            "command_bits": 128 * (1+3+5+19+1+5+5+1+1),
            "credit_return_bits": 128 * 3,
            "access_queue_request_bits": 128 * (1+1+5+5),
            "actual_PHY_receiver_source": None, "pin_caps_fF": None,
            "loaded_slew_wire_cap_and_routes": None,
            "wide_output_pins_are_not_qualified_PHY": True},
        "area": {
            "historical_different_source_two_PC_slice_cell_um2": 3542.09,
            "historical_64_slice_replication_proxy_um2": 64 * 3542.09,
            "proxy_is_NOT_current_mapped_area_or_floorplan_fit": True,
            "existing_parent_clock_state_bits": 33,
            "clock_state_cell_floor_um2": 33 * U.DFF_UM2,
            "clock_state_is_once_only_existing_source_not_added_per_stack": True,
            "current_mapped_controller_area_um2": None,
            "clock_distribution_and_PHY_area_um2": None, "slot_fit": None},
        "clock": {
            "root_period_fs": 833333, "controller_average_period_fs": 1024000,
            "source": "32-bit accumulator; hclk=~clk & tick_q",
            "observed_source_interval_fs": intervals,
            "minimum_controller_setup_interval_ps": min(intervals) / 1000,
            "controller_high_pulse_ps": 833333 / 2000,
            "setup_uncertainty_ps": 60, "hold_uncertainty_ps": 25,
            "continuous_1p024ns_clock_is_NOT_source_equivalent": True,
            "hardware_clock_gating_and_phase_initialization": None,
            "source_acc_tick_initializers_have_no_reset": True,
            "PHY_absolute_time_vs_logical_CTL_FS_checker_join": None,
            "SS_FF_closed": False},
        "slab_price": {
            "actual_result_ports_per_die": 6144 >> 7,
            "actual_scale_banks_per_port": 13,
            "historical_candidate_ports_per_die": 96, "historical_scale_banks": 16,
            "logical_port_GID_mapping": [{"actual_port": q, "candidate_GID": q} for q in range(48)],
            "physical_slot_assignment": None, "historical_upper_GIDs_48_to_95_are_unselected": True,
            "no_area_reclamation_or_fit_credit": True,
            "BF16_lane_product": "literal MUL_LAT5 unchanged",
            "original_FP32_postscale": "ot_hdc_fmul / ot_hdc_fp32_mul_pipe LAT5",
            "selected_candidate_FP32_postscale": "ot_hdc_fp32_mul_lat LAT6",
            "source_reachable_ME_commands_per_rank": count,
            "source_HEAD_ME_PCs": programs["stages"][-1]["ranks"][0]["source_reachable_ME_pcs"],
            "gross_service_extra_cycles_LAT6": count,
            "gross_service_extra_cycles_LAT7_historical": 2 * count,
            "gross_LAT6_extra_ns_at_logical_root": count * .833333,
            "gross_LAT7_extra_ns_at_logical_root": 2 * count * .833333,
            "whole_token_critical_path_extra_cycles": None,
            "required_join": "actual tag tap, scale13 bank layout, FIFO accepted-word/split/epoch/ready/reset, capture timing and write publication",
            "candidate_enrolled": False},
        "historical_failures": ["twoface CTS hold-buffer failure and GRT congestion",
                                "capture GPL0305 at all three heights; retained unchanged"],
        "physical_build_admitted": False, "runtime_changed": False,
        "remaining_inputs": ["physical C/A + credit/write-return receiver pins and loaded cuts",
                             "real generated-clock implementation, startup phase and minimum-edge/hold constraints",
                             "absolute HBM timing contract under source-gated clock",
                             "selected scale13, actual48 group slot and finite FIFO/capture source enrollment"],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        ap.error("preserve existing evidence; choose an additive output")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(compose(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
