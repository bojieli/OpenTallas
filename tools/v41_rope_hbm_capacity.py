#!/usr/bin/env python3
"""Charge read-only RoPE tables to the shared V4.1 layer-die HBM capacity."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACEMENT = ROOT / "results/arch/v41_die_placement.json"
REGION = ROOT / "results/arch/v41_hbm_region_preflight.json"
OUT = ROOT / "results/arch/v41_rope_hbm_capacity.json"
CONTEXTS = (200_000, 1_048_576)
PAIR_BYTES = 8  # one FP32 cosine and one FP32 sine
PAIRS_PER_POSITION = 32


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive():
    placement = json.loads(PLACEMENT.read_text())
    region = json.loads(REGION.read_text())
    assert placement["n_stages"] == 28 and placement["group"] == 4
    assert placement["counts"]["layer"] == 112
    assert placement["hbm_stacks"]["per_layer_die"] == 4
    assert region["inputs"]["context"] == 1_048_576
    assert region["inputs"]["stacks_per_die"] == 4
    assert region["capacity"]["users_model_striped_keys"] == 866

    # The attention/dense portion belongs to the stage at which a layer starts;
    # later fractional expert spill does not duplicate its RoPE reads.
    first_stage = {}
    for stage in placement["stages"]:
        for part in stage["layers"]:
            first_stage.setdefault(part["layer"], stage["stage"])
    assert set(first_stage) == set(range(40))
    kinds_by_stage = {s: set() for s in range(28)}
    for layer, stage in first_stage.items():
        kinds_by_stage[stage].add("plain" if layer == 0 else "yarn")
    assert kinds_by_stage[0] == {"plain", "yarn"}
    assert all(kinds_by_stage[s] == {"yarn"} for s in range(1, 28))

    usable = region["capacity"]["usable_bytes_per_stack"]
    per_user = region["per_stack_per_user_bytes"]["model_striped_keys"]
    assert usable // per_user == 866
    scenarios = {}
    for context in CONTEXTS:
        table_bytes = context * PAIRS_PER_POSITION * PAIR_BYTES
        assert table_bytes % 4 == 0
        stage_rows = []
        for stage in range(28):
            kinds = sorted(kinds_by_stage[stage])
            per_die = len(kinds) * table_bytes
            per_stack = per_die // 4
            row = {
                "stage": stage,
                "table_kinds": kinds,
                "physical_dies": 4,
                "table_bytes_per_die": per_die,
                "table_bytes_per_stack": per_stack,
                "sectors_per_stack": per_stack // 32,
            }
            if context == 1_048_576:
                row["users_with_striped_keys_capacity_only"] = (usable - per_stack) // per_user
                row["room_at_model_866_users_bytes_per_stack"] = usable - 866 * per_user - per_stack
            stage_rows.append(row)
        scenarios[str(context)] = {
            "single_table_bytes_per_die": table_bytes,
            "single_table_bytes_per_stack": table_bytes // 4,
            "physical_table_copies": sum(len(kinds_by_stage[s]) * 4 for s in range(28)),
            "fleet_table_bytes": sum(r["table_bytes_per_die"] * 4 for r in stage_rows),
            "max_table_bytes_per_die": max(r["table_bytes_per_die"] for r in stage_rows),
            "min_capacity_users_with_striped_keys": min(
                r.get("users_with_striped_keys_capacity_only", 10**9) for r in stage_rows
            ) if context == 1_048_576 else None,
            "stages": stage_rows,
        }
    return {
        "schema": "opentallas.v41x.rope_hbm_capacity.v1",
        "status": "capacity_only; physical region allocation and bandwidth arbitration pending",
        "source_sha256": {
            str(PLACEMENT.relative_to(ROOT)): digest(PLACEMENT),
            str(REGION.relative_to(ROOT)): digest(REGION),
            str(Path(__file__).resolve().relative_to(ROOT)): digest(Path(__file__).resolve()),
        },
        "assumptions": {
            "cos_sin_format": "32 FP32 cos/sin pairs per position per table",
            "allocation": "one table per kind per physical layer die; no separate HBM port",
            "attention_owner": "first placement stage containing each layer",
            "per_token_fill": "256 bytes: two 32-byte sectors from each of four stacks; retained for all RoPE ops at that token position",
            "capacity_reference": "1M striped-index preflight; other state/overhead outside that preflight is not established",
        },
        "scenarios": scenarios,
    }


def main():
    record = derive()
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    million = record["scenarios"]["1048576"]
    assert million["physical_table_copies"] == 116
    assert million["stages"][0]["users_with_striped_keys_capacity_only"] == 860
    assert million["stages"][1]["users_with_striped_keys_capacity_only"] == 863
    print(f"PASS: {million['physical_table_copies']} tables; 1M min {million['min_capacity_users_with_striped_keys']} users")


if __name__ == "__main__":
    main()
