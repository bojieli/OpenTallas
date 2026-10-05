#!/usr/bin/env python3
"""Compare scoped V4.1 KV placement with a rack die-placement artifact."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.prefill.v41_hbm_placement import Placement, OWNERS, LAYERS, MAX_CONTEXT


def audit(config_path, placement_path, rack_path):
    config = json.loads(Path(config_path).read_text())
    placed = json.loads(Path(placement_path).read_text())
    rack = json.loads(Path(rack_path).read_text())
    op = config["metadata"]["operator_config"]
    if tuple(op["kv_source_layer_ids"]) != OWNERS or len(op["compress_ratios"]) != LAYERS:
        raise ValueError("released owner list or layer count changed")
    if any(op["compress_ratios"][l] != (2 if l < 20 else 1) for l in range(2, LAYERS)):
        raise ValueError("released compression ratio changed")
    if op["index_source_layer_ids"] != [2, 8, 14, 20, 24, 28, 32, 36]:
        raise ValueError("released index-source list changed")
    if config["max_context_tokens"] != MAX_CONTEXT or op["window_tokens"] != 128:
        raise ValueError("released context or ring geometry changed")
    starts = {}
    for stage in placed["stages"]:
        for item in stage["layers"]:
            starts.setdefault(item["layer"], stage["stage"])
    if set(starts) != set(range(LAYERS)):
        raise ValueError("rack stage placement does not cover 40 layers")
    # KV lives on the 112 layer dies' stacks (4 each = 448); the head dies' stacks (4 x 4 since the
    # head-die HBM decision) hold draft KV and are not part of this map
    counts = rack["logical"]["counts"]
    if placed["hbm_stacks"]["per_layer_die"] != 4 or counts["layer"] != 112:
        raise ValueError("layer-die stack count changed")
    if rack["fill"] != 28 or counts["hbm_stacks"] - counts["head"] * counts.get("head_hbm_stacks_per_die", 0) != 448:
        raise ValueError("rack fill or layer stack count changed")
    results = []
    for stage in range(28):
        owners = tuple(o for o in OWNERS if starts[o] == stage)
        windows = tuple(l for l in range(LAYERS) if starts[l] == stage)
        scoped = Placement(owners=owners, window_layers=windows)
        peak_stack = max(scoped.used_bytes.values())
        results.append(dict(stage=stage, owners=owners, window_layers=windows,
                            per_die_bytes=sum(scoped.used_bytes[(0, s)] for s in range(4)),
                            peak_stack_bytes=peak_stack, fill_28_peak_stack_bytes=28 * peak_stack,
                            fits_budget_22_5GB=28 * peak_stack <= 22_500_000_000,
                            fits_rack_36GB=28 * peak_stack <= 36_000_000_000))
    busiest = max(results, key=lambda r: r["per_die_bytes"])
    return dict(schema="opentallas.v41.prefill_hbm_rack_audit.v1",
                owner_stages={o: starts[o] for o in OWNERS},
                rack_stacks=448, rack_fill=28, stages=results,
                busiest_stage=busiest,
                all_fit_22_5GB=all(r["fits_budget_22_5GB"] for r in results),
                all_fit_36GB=all(r["fits_rack_36GB"] for r in results))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--placement", type=Path, required=True)
    parser.add_argument("--rack", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.config, args.placement, args.rack), indent=2))


if __name__ == "__main__":
    main()
