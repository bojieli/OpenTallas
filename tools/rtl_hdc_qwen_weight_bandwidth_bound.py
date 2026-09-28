#!/usr/bin/env python3
"""Summarize a source-pinned matched Qwen weight run as a bandwidth stress gate."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTOR_BYTES = 32
CLK_PS = 1000
BURST_PS = 1024
PCS_PER_STACK = 32
STACKS_PER_PACKAGE = 8


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(raw, raw_path, reference, reference_path):
    assert raw["status"] == "pass" and raw["configuration"]["kv_hbm_pseudo_channels"] == 1
    assert raw["configuration"]["steps_executed"] >= 2
    stale = [name for name, digest in raw["source_sha256"].items()
             if sha(ROOT / name) != digest]
    if stale:
        raise ValueError(f"stale source pins: {stale}")
    if reference["status"] != "pass" or reference["configuration"]["kv_hbm_pseudo_channels"] != 4:
        raise ValueError("matched four-channel reference did not pass")
    if reference["source_sha256"] != raw["source_sha256"]:
        raise ValueError("one- and four-channel source pins differ")
    if reference["image_sha256"] != raw["image_sha256"]:
        raise ValueError("one- and four-channel images differ")
    if reference["model_sha256"] != raw["model_sha256"]:
        raise ValueError("one- and four-channel model checkpoints differ")
    if reference["configuration"]["steps_executed"] != raw["configuration"]["steps_executed"]:
        raise ValueError("one- and four-channel step counts differ")
    rom, hbm = raw["rom"], raw["hbm"]
    rcy = rom["summary"]["total_cycles"]
    hcy = hbm["summary"]["total_cycles"]
    sectors = hbm["weights"]["weight_completed_sectors"]
    weight_bytes = sectors * SECTOR_BYTES
    peak_sectors_per_cycle = CLK_PS / BURST_PS
    ideal_weight_cycles = sectors / peak_sectors_per_cycle
    achieved_sectors_per_cycle = sectors / hcy
    offered_sectors_per_rom_cycle = sectors / rcy
    stalls = hbm["weights"]["weight_stall_cycles"] + hbm["weights"]["embedding_stall_cycles"]
    ref_rom, ref_hbm = reference["rom"], reference["hbm"]
    ref_hcy = ref_hbm["summary"]["total_cycles"]
    ref_stalls = ref_hbm["weights"]["weight_stall_cycles"] + ref_hbm["weights"]["embedding_stall_cycles"]
    checks = {
        "both_arms_bit_exact": rom["pass"] and hbm["pass"],
        "same_tokens_and_state": rom["summary"]["token_mismatches"] == hbm["summary"]["token_mismatches"] == 0
                                 and rom["summary"]["logit_mismatches"] == hbm["summary"]["logit_mismatches"] == 0
                                 and rom["summary"]["vm_mismatches"] == hbm["summary"]["vm_mismatches"] == 0
                                 and rom["summary"]["kv_mismatches"] == hbm["summary"]["kv_mismatches"] == 0,
        "offered_weight_demand_exceeds_channel_peak": offered_sectors_per_rom_cycle > peak_sectors_per_cycle,
        "weight_supply_stalled": stalls > 0,
        "hbm_slower_than_rom": hcy > rcy,
        "hbm_delivered_at_least_70pct_peak": achieved_sectors_per_cycle >= 0.70 * peak_sectors_per_cycle,
        "four_channel_arms_bit_exact": ref_rom["pass"] and ref_hbm["pass"],
        "same_weight_words_consumed": hbm["weights"]["weight_consumed"] == ref_hbm["weights"]["weight_consumed"],
        "same_weight_sectors_delivered": sectors == ref_hbm["weights"]["weight_completed_sectors"],
        "one_channel_slower_than_four": hcy > ref_hcy,
        "one_channel_more_supply_stalls": stalls > ref_stalls,
    }
    return {
        "schema": "opentallas.qwen-matched-weight-bandwidth-bound.v1",
        "status": "pass" if all(checks.values()) else "fail",
        "claim_boundary": "Two or more reduced G4/SW16 Qwen token steps with the same vector controller, "
                          "ISA, arithmetic and timed KV HBM in both arms; only weight source differs. "
                          "One pseudo-channel is a deliberate supply stress, 1/256 of the adopted "
                          "eight-stack package's channel count. The HBM controller is behavioral with "
                          "assumed timings; these cycles are not a full INT8 TP-2 throughput or P&R result.",
        "base_commit": "84585806",
        "raw_source_sha256": {"one_channel": sha(raw_path), "four_channel": sha(reference_path)},
        "postprocessor_sha256": sha(Path(__file__)),
        "source_sha256": raw["source_sha256"],
        "model_sha256": raw["model_sha256"],
        "image_sha256": raw["image_sha256"],
        "configuration": {
            "steps": raw["configuration"]["steps_executed"],
            "pseudo_channels": 1,
            "package_pseudo_channels": PCS_PER_STACK * STACKS_PER_PACKAGE,
            "channel_fraction_of_package": 1 / (PCS_PER_STACK * STACKS_PER_PACKAGE),
            "peak_channel_bytes_per_second": SECTOR_BYTES * 1e12 / BURST_PS,
            "clock_ps": CLK_PS,
            "sector_bytes": SECTOR_BYTES,
            "weight_rate_words_x256": raw["configuration"]["weight_rate_words_x256"],
        },
        "measurements": {
            "rom_core_cycles": rcy,
            "hbm_core_cycles": hcy,
            "hbm_over_rom": hcy / rcy,
            "weight_completed_sectors": sectors,
            "weight_completed_bytes": weight_bytes,
            "weight_words_consumed": hbm["weights"]["weight_consumed"],
            "kv_completed_sectors": hbm["weights"]["kv_completed_sectors"],
            "peak_weight_sectors_per_cycle": peak_sectors_per_cycle,
            "offered_weight_sectors_per_rom_cycle": offered_sectors_per_rom_cycle,
            "delivered_weight_sectors_per_hbm_cycle": achieved_sectors_per_cycle,
            "delivered_fraction_of_peak": achieved_sectors_per_cycle / peak_sectors_per_cycle,
            "ideal_weight_transfer_cycles": ideal_weight_cycles,
            "weight_stall_cycles": hbm["weights"]["weight_stall_cycles"],
            "embedding_stall_cycles": hbm["weights"]["embedding_stall_cycles"],
            "hbm_backpressure_cycles": hbm["hbm_timing"]["backpressure_cycles"],
            "rom_step_cycles": [step["cycles"] for step in rom["steps"]],
            "hbm_step_cycles": [step["cycles"] for step in hbm["steps"]],
        },
        "four_channel_reference": {
            "rom_core_cycles": ref_rom["summary"]["total_cycles"],
            "hbm_core_cycles": ref_hcy,
            "hbm_over_rom": ref_hcy / ref_rom["summary"]["total_cycles"],
            "weight_completed_sectors": ref_hbm["weights"]["weight_completed_sectors"],
            "weight_completed_bytes": ref_hbm["weights"]["weight_completed_sectors"] * SECTOR_BYTES,
            "delivered_weight_sectors_per_hbm_cycle": ref_hbm["weights"]["weight_completed_sectors"] / ref_hcy,
            "delivered_fraction_of_peak": ref_hbm["weights"]["weight_completed_sectors"] /
                                          (ref_hcy * 4 * peak_sectors_per_cycle),
            "weight_words_consumed": ref_hbm["weights"]["weight_consumed"],
            "kv_completed_sectors": ref_hbm["weights"]["kv_completed_sectors"],
            "weight_stall_cycles": ref_hbm["weights"]["weight_stall_cycles"],
            "embedding_stall_cycles": ref_hbm["weights"]["embedding_stall_cycles"],
            "hbm_backpressure_cycles": ref_hbm["hbm_timing"]["backpressure_cycles"],
            "rom_step_cycles": [step["cycles"] for step in ref_rom["steps"]],
            "hbm_step_cycles": [step["cycles"] for step in ref_hbm["steps"]],
        },
        "checks": checks,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True, help="fresh matched four-channel run")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = summarize(json.loads(args.input.read_text()), args.input,
                       json.loads(args.reference.read_text()), args.reference)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"], json.dumps(result["measurements"], sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
