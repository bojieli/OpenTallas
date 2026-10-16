"""Measured sizing of the default-off S81 BF column clock partition.

The historical ABC cone census is a warning about cuts, not a floorplan.  A
new source-hierarchy leaf must carry its own real interface and pin/cut proof.
This option does not change an immutable stage price or authorize a route.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CENSUS_PATH = "results/rtl/s81_bf_clock_1015/c10/recovery_0253/column_root_census.json"
CENSUS_SHA256 = "97b43328302067df1c82fd53beb1fb2d14f031a28e0daaef4be3af13420a2aa8"
NATIVE_SOURCE = "ea1b0c30b794aacaa897b3416f90c4824b3617fb"
EVIDENCE_COMMIT = "7fd9a1f7e"
GROUPS = {
    0: "boundary_memory", 1: "fp4_leg0_chain_pair", 2: "fp4_leg1_chain",
    3: "segment_tree", 4: "bf16_lane4_0", 5: "bf16_lane4_1",
    6: "bf16_lane4_2", 7: "bf16_lane4_3", 8: "bf16_tree_level0",
    9: "bf16_tree_levels1_3",
}


def load_census(path: Path, expected_sha256: str) -> dict:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("BF census source hash mismatch")
    census = json.loads(data)
    groups = census["groups"]
    if set(groups) != {str(g) for g in GROUPS}:
        raise ValueError("BF census must cover all ten actual groups")
    if census["sequential_cells"] != 53493 or sum(g["sinks"] for g in groups.values()) != 53493:
        raise ValueError("BF census does not cover all 53,493 actual sequential cells")
    if any(g["area_um2"] <= 0 or g["sinks"] <= 0 for g in groups.values()):
        raise ValueError("BF group area/sinks missing")
    seen = set()
    for edge in census["data_cut_edges"]:
        pair = edge["source"], edge["destination"]
        if (any(g not in GROUPS for g in pair) or pair[0] == pair[1]
                or pair in seen or not isinstance(edge["bits"], int) or edge["bits"] <= 0):
            raise ValueError("BF census cut is invalid or duplicated")
        seen.add(pair)
    if not seen:
        raise ValueError("BF census cut graph is missing")
    return census


def model(*, census_path=None, census_sha256=CENSUS_SHA256, columns=1):
    if not isinstance(columns, int) or isinstance(columns, bool) or columns <= 0:
        raise ValueError("columns must be an actual positive integer instance count")
    census = load_census(Path(census_path) if census_path else ROOT / CENSUS_PATH, census_sha256)
    area = sum(g["area_um2"] for g in census["groups"].values())
    # Canonical NSEG=8, MTP=1 -> outer tree width4 -> BF lane tree width TG=7.
    # The generated leaf's default TRW=6 is NOT the production parameter.
    nchb, trw = 8, 7
    tag = math.ceil(math.log2(nchb)) + 3 + trw
    lane_in = 64 + 64 + tag + 1 + 1  # weights, activations, tag, valid, gate enable
    lane_out = 4 + 4 + 4 + 4 * 32 + 4 * (trw + 1)
    face_span, pitch = 95.04 - 2 * 2.16, .048
    return {
        "schema": "opentallas.s81.bf-ten-root.candidate.v1",
        "default_off": True, "adopted": False,
        "source": {"native_component_commit": NATIVE_SOURCE,
                   "census_evidence_commit": EVIDENCE_COMMIT,
                   "census_path": CENSUS_PATH, "census_sha256": census_sha256,
                   "mapped_netlist_sha256_zstd": census["mapped_netlist_sha256_zstd"],
                   "routed_def_sha256_zstd": census["routed_def_sha256_zstd"]},
        "replicas": {"columns_requested": columns, "roots_per_column": 10,
                     "root_delivery_pins_total": columns * 10,
                     "four_lane_master_per_column": 4,
                     "other_group_instances_per_column": 6,
                     "distinct_master_families_upper_bound": 7},
        "actual_old_sequential_cells_per_column": 53493,
        "actual_old_root_groups": {GROUPS[int(k)]: v for k, v in census["groups"].items()},
        "compute": {"bf16_macs_per_active_bf_issue": 16,
                    "macs_per_cycle_delta": 0,
                    "production_macs_per_calendar_cycle": None,
                    "basis": "Existing reviewed arithmetic and issue schedule unchanged; native component exactness alone is not a sustained-rate measurement."},
        "memory": {"roms_per_column": 2, "macro": "ot_rom_4096x274_m8",
                   "read_port_bits_each": 274, "physical_read_port_bits_total": 548,
                   "normal_read_enables_per_column_cycle_max": 1,
                   "normal_raw_read_bytes_per_cycle_max": 274 / 8,
                   "useful_weight_bytes_per_read": 32,
                   "bf16_macs_per_useful_weight_byte": 16 / 32,
                   "read_bytes_per_cycle_delta": 0,
                   "write_bytes_per_cycle": 0,
                   "basis": "Two ping-pong 4096x274 real macros; b_a_ctr[0] selects mutually exclusive read enables."},
        "column_boundary": {"ci_input_bits": 776, "result_output_bits": 64,
                            "clock_pins": 10, "reset_pins": 1,
                            "data_boundary_bits_per_cycle_delta": 0,
                            "added_clock_delivery_pins_per_column": 9},
        "four_lane_source_interface": {"NCHB": nchb, "TRW": trw,
            "tag_bits": tag, "input_data_bits": lane_in, "output_data_bits": lane_out,
            "clock_and_reset_bits": 2, "total_pin_bits": lane_in + lane_out + 2,
            "source": "ot_v41_bf_lane4 real source-hierarchy extraction; no ABC cone cut substituted"},
        "historical_flat_cone_cuts": census["data_cut_edges"],
        "historical_flat_cut_bits_max": max(e["bits"] for e in census["data_cut_edges"]),
        "routing": {"new_parent_actual_pin_edges": None, "new_parent_channel_capacity": None,
                    "new_parent_worst_reach_um": None, "new_parent_cut_ratio": None,
                    "track_count_lower_bound_per_parallel_bit": 1,
                    "lane4_prototype_only": {"outline_um": [95.04, 95.04],
                        "edge_guard_um": 2.16, "M4_pitch_um": pitch,
                        "usable_face_tracks_before_other_reservations": math.floor(face_span / pitch),
                        "W_input_fraction_before_other_reservations": lane_in / (face_span / pitch),
                        "E_output_fraction_before_other_reservations": lane_out / (face_span / pitch),
                        "source_std_area_um2_max": 4170.507,
                        "core_area_um2": face_span * face_span,
                        "source_std_fraction_before_CTS_hold": 4170.507 / (face_span * face_span),
                        "assigned_pins": None, "slot_granted": False,
                        "probe_scope": "Single representative CTS probe only after actual317-bit pin map and full-shape leaf exactness/mutant. Does not admit full-column replication or die adoption."},
                    "scope": "Flat cuts up to 1246 bits and old spans up to 417um are historical failure evidence. Source extraction, actual pins/PG/clock reservations and every incident edge must replace them before capacity is accepted."},
        "area": {"historical_cells_excluding_clock_um2_per_column": round(area, 3),
                 "historical_clock_cells_excluded": census["clock_cells_excluded"],
                 "lane4_historical_area_um2": [census["groups"][str(i)]["area_um2"] for i in range(4, 8)],
                 "new_local_clock_reset_hold_and_seam_area_um2": None,
                 "new_total_area_um2": None, "parent_outline_um": None,
                 "parent_slot_fit": None,
                 "basis": "Measured original mapped area is a sizing bound, not a new synthesized or placed leaf area."},
        "fanout_and_mux": {"lane_payload": "One native 64b weight and 64b activation bundle per four-lane master",
                           "shared_tag_and_enable": "Four local copies; real source/driver and parent cut/fanout cost still required",
                           "runtime_arbitration_added": False, "runtime_credits_added": False},
        "latency": {"added_logical_cycles": 0, "native_component_cycles": 124422,
                    "native_component_rows": 456, "native_component_values": 912,
                    "native_component_config_checks": 448, "compiled_phases": 13,
                    "measured_lag_ns_min_max_mean": [6.664, 15.827, 9.923],
                    "actual_clock_stop_mutant": "FAIL transaction16, as required",
                    "new_physical_seam_cycles": None,
                    "compiler_and_token_rate_adopted": False},
        "clock_contract": "Each real leaf clock is same-PLL/frequency/phase, die delivered at phi-R; preserve all TT setup/FF hold checks. New views must meet launch220/capture190/spread80 and DRC0.",
        "physical_build_admissible": False,
        "native_physical_qualified": False, "production_throughput_qualified": False,
        "fail_closed_reasons": ["new source leaf physical areas and assigned pins/slots absent",
                                "new parent complete actual incident graph/capacity/reach absent",
                                "local physical clock/TT/FF/DRC/native views absent",
                                "any added physical seam stage must enter compiler and rate model"],
        "price_policy": "No preset, immutable price, accepted-cost ledger, workload or headline-rate change.",
    }
