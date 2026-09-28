#!/usr/bin/env python3
"""Size the full-position V4.1 RoPE CROM implied by the emitted ISA."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json"
PLACEMENT = ROOT / "results/arch/v41_die_placement.json"
EMITTER = ROOT / "tools/hdc_replay_v41.py"
GOLDEN = ROOT / "tools/hdc_golden_v41.py"
OUTPUT = ROOT / "results/arch/v41_fullshape_rope_capacity_audit.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive() -> dict:
    config = json.loads(CONFIG.read_text())
    placement = json.loads(PLACEMENT.read_text())
    rd = config["rope_head_dim"]
    if rd <= 0 or rd % 2:
        raise ValueError("RoPE dimension must be positive and even")
    # Machine.crom stores each adjacent-pair (cos,sin) as two FP32 values.
    bytes_per_position = rd // 2 * 2 * 4
    spare = placement["min_layer_die_spare_bytes"]
    contexts = {}
    for length in (200_000, 1_048_576):
        one = length * bytes_per_position
        contexts[str(length)] = {
            "bytes_per_one_plain_or_yarn_table": one,
            "bytes_per_two_tables": 2 * one,
            "one_table_fits_min_spare": one <= spare,
            "one_table_deficit_bytes": max(0, one - spare),
            "two_table_deficit_bytes": max(0, 2 * one - spare),
        }
    return {
        "schema": "opentallas.arch.v41_fullshape_rope_capacity_audit.v1",
        "status": "replicated_full_position_crom_does_not_fit_1m_layer_die",
        "claim_scope": "Capacity check for the current emitted CROM RoPE lookup contract. "
                       "It does not price an HBM-backed table, procedural generator, cache, "
                       "timing, power, or a new placement.",
        "rope_head_dim": rd,
        "cos_sin_format": "two IEEE binary32 values per adjacent pair",
        "crom_bytes_per_position_per_table": bytes_per_position,
        "minimum_token_lookup_bytes_per_table": bytes_per_position,
        "min_layer_die_spare_bytes_after_adopted_placement": spare,
        "contexts": contexts,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          (CONFIG, PLACEMENT, EMITTER, GOLDEN, Path(__file__))},
    }


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(derive(), indent=2) + "\n")
    print(OUTPUT)
