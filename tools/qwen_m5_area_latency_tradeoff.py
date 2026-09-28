#!/usr/bin/env python3
"""Measured small-tile area and one-tree throughput sensitivity for Qwen O4 m=5.

The production-area conversion is a linear tile replication estimate, not a
full die synthesis or floorplan. The timing alternative adds engine busy
cycles; whether they all expose on the token chain needs an integrated replay.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT / "results/physical_hdc/asap7/qwen_m5_reduce_g2w2_n1/physical.json"
P5 = ROOT / "results/physical_hdc/asap7/qwen_m5_reduce_g2w2_n5/physical.json"
BUDGET = ROOT / "results/arch/qwen3_budget.json"
TIMING = ROOT / "results/speculative/dflash_step_timing.json"
SPEC = ROOT / "docs/ARCH_QWEN3_O4_RTL_SPEC.md"
RTL = ROOT / "rtl/hdc/ot_hdc_qwen_m5_reduce_scale.sv"
OUT = ROOT / "results/arch/qwen_m5_area_latency_tradeoff.json"


def derive():
    one, five = (json.loads(p.read_text()) for p in (P1, P5))
    for x, n in ((one, 1), (five, 5)):
        assert x["design"]["parameters"] == {"G": 2, "W": 2, "N": n}
        assert x["target_clock_period_ns"] == 0.92
        assert x["corner"]["name"] == "TT" and x["view"]["name"] == "asap7"
        assert x["design"]["sources"][0]["sha256"] == hashlib.sha256(RTL.read_bytes()).hexdigest()
    budget = json.loads(BUDGET.read_text())
    timing = json.loads(TIMING.read_text())
    point = timing["rom"]["8192/fp8/m5"]["best"]
    assert point["block"] == 5 and point["step_cycles"] == 167796
    assert budget["area"]["groups_per_die"] == 6144 and budget["area"]["lane_copies_added"] == 4
    delta = five["design"]["area_um2"] - one["design"]["area_um2"]
    added_lanes_tile = (5 - 1) * 2 * 2
    added_lanes_die = 4 * 6144 * 16
    area_die = delta / added_lanes_tile * added_lanes_die / 1e6
    # One reduction tree retires one slot vector/cycle. For a matrix with K/S
    # issue cycles per 8 result slots, demand is 5*8 result cycles a round.
    # These are the O4 per-die RTL tilings and 8K attention score allocation.
    ops = {"o_projection": (88, 1, 36), "down_projection": (264, 3, 36),
           "lm_head": (3168, 4, 1), "attention_scores": (256, 1, 36)}
    detail = {}
    for name, (sweep, k_per_chunk, count) in ops.items():
        assert sweep % (8 * k_per_chunk) == 0
        rounds = sweep // (8 * k_per_chunk)
        demand = 5 * 8 * rounds
        extra = max(0, demand - sweep)
        detail[name] = dict(sweep_cycles=sweep, k_per_chunk=k_per_chunk, rounds=rounds,
                            reduction_demand_cycles=demand, minimum_extra_cycles_per_op=extra,
                            repetitions=count, minimum_extra_cycles_total=extra * count)
    extra = sum(x["minimum_extra_cycles_total"] for x in detail.values())
    hz = budget["clock_hz"]
    exposed_rate = hz * point["tokens_per_step"] / (point["step_cycles"] + extra)
    files = [P1, P5, BUDGET, TIMING, SPEC, RTL, Path(__file__)]
    return {
        "area": {"evidence_class": "ASAP7 pre-layout synthesis tile and linear die replication estimate",
                 "tile": {"groups": 2, "lanes_per_group": 2, "slots_baseline": 1, "slots_verify": 5,
                          "one_slot_area_um2": one["design"]["area_um2"],
                          "five_slot_area_um2": five["design"]["area_um2"],
                          "incremental_four_slot_area_um2": delta,
                          "incremental_area_per_added_slot_lane_um2": delta / added_lanes_tile,
                          "one_slot_cells": one["design"]["cells"], "five_slot_cells": five["design"]["cells"]},
                 "production_linear_replication": {"added_slot_lanes_per_die": added_lanes_die,
                                                    "incremental_reducer_scale_mm2_per_die": area_die,
                                                    "modeled_slack_mm2_per_die": budget["area"]["slack_mm2"],
                                                    "modeled_mac_only_copy_mm2_per_die": 4 * budget["area"]["lane_copy_mm2"],
                                                    "uncovered_area_vs_slack_mm2": area_die - budget["area"]["slack_mm2"]},
                 "timing": {"one_slot_prelayout_wns_ns": one["static_timing"]["setup_wns_ns"],
                            "five_slot_prelayout_wns_ns": five["static_timing"]["setup_wns_ns"],
                            "target_period_ns": 0.92, "routed": False}},
        "one_tree_time_multiplex": {"evidence_class": "analytical engine-busy-cycle lower bound and fully exposed rate sensitivity",
                                    "matrix_ops": detail, "minimum_additional_verify_engine_cycles": extra,
                                    "baseline_step_cycles": point["step_cycles"],
                                    "baseline_model_tokens_s": point["tokens_s"],
                                    "all_extra_exposed_step_cycles": point["step_cycles"] + extra,
                                    "all_extra_exposed_tokens_s": exposed_rate,
                                    "claim_boundary": "The extra cycles are a reduction service lower bound. "
                                                      "The rate assumes all extra engine cycles hit the serial chain; "
                                                      "an integrated schedule must measure overlap. Drafter penalties omitted."},
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        "claim_boundary": "G2/W2 pre-layout area cannot prove full-die area; both tiles fail 0.92 ns pre-layout timing. "
                          "The die conversion is linear replication only. No place and route, power or full m5 token gate."}


if __name__ == "__main__":
    result = derive()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"area_mm2": result["area"]["production_linear_replication"]["incremental_reducer_scale_mm2_per_die"],
                      "one_tree_extra_cycles": result["one_tree_time_multiplex"]["minimum_additional_verify_engine_cycles"],
                      "one_tree_all_exposed_tokens_s": result["one_tree_time_multiplex"]["all_extra_exposed_tokens_s"]}, indent=2))
