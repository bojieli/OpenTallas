#!/usr/bin/env python3
"""Conditional Qwen O4 lane-slot area and serial DFlash timing sweep.

The area term is a linear replication of the measured G2/W2 ASAP7
pre-layout reducer/scale delta.  It is a planning gate, not a die route.
"""

import hashlib
import json
from pathlib import Path

import dflash_step_timing as DST


ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    Path("results/arch/qwen3_budget.json"),
    Path("results/arch/qwen_m5_area_latency_tradeoff.json"),
    Path("results/physical_hdc/asap7/qwen_m5_reduce_g2w2_n1/physical.json"),
    Path("results/physical_hdc/asap7/qwen_m5_reduce_g2w2_n5/physical.json"),
    Path("results/speculative/dflash_block_acceptance.json"),
    Path("tools/dflash_step_timing.py"),
    Path("tools/qwen_o4_slot_budget.py"),
)
OUTPUT = ROOT / "results/arch/qwen_o4_slot_budget.json"


def derive():
    budget = json.loads((ROOT / INPUTS[0]).read_text())
    trade = json.loads((ROOT / INPUTS[1]).read_text())
    area = budget["area"]
    replica = trade["area"]["production_linear_replication"]
    tile = trade["area"]["tile"]
    assert area["lane_multiplier_m"] == 5
    assert area["groups_per_die"] == 6144
    assert replica["modeled_slack_mm2_per_die"] == area["slack_mm2"]
    assert replica["modeled_mac_only_copy_mm2_per_die"] == 4 * area["lane_copy_mm2"]
    assert tile["incremental_four_slot_area_um2"] == (tile["five_slot_area_um2"] - tile["one_slot_area_um2"])
    assert trade["area"]["timing"]["routed"] is False

    available = replica["modeled_mac_only_copy_mm2_per_die"] + area["slack_mm2"]
    reducer_per_copy = replica["incremental_reducer_scale_mm2_per_die"] / 4
    copy = area["lane_copy_mm2"]
    acceptance = DST.acceptance(json.loads((ROOT / INPUTS[4]).read_text()))
    machine = DST.Machine(DST.design_basis(), 8192, "fp8")
    assert machine.clock == budget["clock_hz"]
    rows = []
    for slots in range(1, 6):
        options = []
        for block in DST.BLOCKS:
            if block not in acceptance:
                continue
            step = machine.serial_step(block, slots)
            tau = acceptance[block]["direct"]
            options.append({"block": block, "tau": round(tau, 4),
                            "step_cycles": round(step["cycles"]),
                            "draft_cycles": round(step["draft"]),
                            "verify_cycles": round(step["verify"]),
                            "tokens_s": round(tau * machine.clock / step["cycles"], 1)})
        best = max(options, key=lambda p: p["tokens_s"])
        required = (slots - 1) * (copy + reducer_per_copy)
        rows.append({"slots": slots, "added_mac_copy_mm2_per_die": round((slots - 1) * copy, 3),
                     "added_reducer_scale_mm2_per_die": round((slots - 1) * reducer_per_copy, 3),
                     "combined_added_mm2_per_die": round(required, 3),
                     "area_margin_mm2_per_die": round(available - required, 3),
                     "fits_linear_tile_estimate": required <= available,
                     "best_serial_model": best})
    assert rows[-1]["best_serial_model"]["tokens_s"] == round(
        budget["dflash"]["rom"]["8192/fp8/m5"]["best"]["tokens_s"], 1)
    best_fitting = max((r for r in rows if r["fits_linear_tile_estimate"]), key=lambda r: r["best_serial_model"]["tokens_s"])
    return {
        "schema": "opentallas.qwen-o4-slot-budget.v1",
        "scope": "8K FP8-KV Qwen3-8B O4 two-die ROM package, one die area ledger, batch-one serial DFlash model",
        "evidence_class": "conditional analytical area and timing; pre-layout G2/W2 area extrapolation",
        "inputs_sha256": {str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS},
        "area": {"available_for_extra_slots_mm2_per_die": round(available, 3),
                 "mac_copy_mm2_per_extra_slot_per_die": copy,
                 "reducer_scale_mm2_per_extra_slot_per_die": round(reducer_per_copy, 6),
                 "die_envelope_mm2": area["die_mm2"]},
        "slot_sweep": rows,
        "best_fitting_linear_estimate": {"slots": best_fitting["slots"], **best_fitting["best_serial_model"]},
        "m5_design_rate_tokens_s": rows[-1]["best_serial_model"]["tokens_s"],
        "claim_boundary": (
            "The m=3 point fits only a linear replication of a G2/W2 ASAP7 pre-layout tile. "
            "Neither m=3 nor m=5 has routed timing, power, full-die area or full-shape exact-token evidence. "
            "The serial step model omits additional reducer stalls and is not a measured rate. "
            "The m=5 design rate should remain conditional until physical closure or a validated time-multiplex schedule."
        ),
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(derive(), indent=2, sort_keys=True) + "\n")
