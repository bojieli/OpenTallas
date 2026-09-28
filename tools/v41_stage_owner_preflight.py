#!/usr/bin/env python3
"""Integer expert-ID candidate for the V4.1 array's fluid stage placement.

The placement record divides layer bytes fractionally. This audit asks whether
whole routed experts can fit at those cuts; it does not bind tensor images,
programs or packets and therefore cannot certify an executable stage map.
"""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
PLACEMENT = ROOT / "results/arch/v41_die_placement.json"
OUT = ROOT / "results/arch/v41_stage_owner_preflight.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(config=CONFIG, placement=PLACEMENT):
    c = json.loads(config.read_text())
    p = json.loads(placement.read_text())
    assert p["n_stages"] == 28 and p["group"] == 4 and len(p["stages"]) == 28
    dense = c["layer_dense_weight_bytes"]
    routed = c["layer_routed_weight_bytes"]
    assert len(dense) == len(routed) == 40
    n_experts = 384
    sizes = [a + b for a, b in zip(dense, routed)]
    stage_bytes = sum(sizes) / p["n_stages"]
    start = 0.0
    cuts, owners, delta = [], [], [0.0] * p["n_stages"]
    for layer, size in enumerate(sizes):
        end = start + size
        crossed = [stage for stage in range(1, p["n_stages"])
                   if start < stage * stage_bytes < end]
        assert len(crossed) <= 1, "one expert layer crosses multiple stage cuts"
        home = int(start // stage_bytes)
        if crossed:
            next_stage = crossed[0]
            cut_bytes = next_stage * stage_bytes - start
            assert cut_bytes > dense[layer], f"dense tensor cut in layer {layer}"
            fractional_experts = (cut_bytes - dense[layer]) / (routed[layer] / n_experts)
            earlier_count = math.ceil(fractional_experts)
            assert 0 < earlier_count < n_experts
            extra = (earlier_count - fractional_experts) * routed[layer] / n_experts
            delta[home] += extra
            delta[next_stage] -= extra
            cuts.append(dict(layer=layer, from_stage=home, to_stage=next_stage,
                             fluid_expert_cut=fractional_experts,
                             integer_expert_cut=earlier_count,
                             earlier_expert_ids=[0, earlier_count - 1],
                             later_expert_ids=[earlier_count, n_experts - 1],
                             earlier_stage_added_bytes=extra))
            parts = [dict(stage=home, expert_ids=[0, earlier_count - 1]),
                     dict(stage=next_stage, expert_ids=[earlier_count, n_experts - 1])]
        else:
            parts = [dict(stage=home, expert_ids=[0, n_experts - 1])]
        owners.append(dict(layer=layer, dense_owner_stage=home,
                           routed_expert_candidate_owners=parts))
        start = end
    assert len(cuts) == 27 and sorted(x["to_stage"] for x in cuts) == list(range(1, 28))
    headroom_before_spill = [p["rom_bytes_per_die"] - st["bytes"] / p["group"] - delta[i] / p["group"]
                             for i, st in enumerate(p["stages"])]
    headroom_after_spill = [x - p["die_table"][i * p["group"]]["engram_spill_bytes"]
                            for i, x in enumerate(headroom_before_spill)]
    return dict(schema="opentallas.v41.stage_owner_preflight.v1",
                status="coarse_integer_candidate_not_executable",
                claim_boundary="Whole routed-expert ID candidate from coarse checkpoint bytes only; no tensor image, "
                               "stage program, data-dependent schedule, inter-stage packet or bit-exact RTL proof.",
                source_sha256={str(config.relative_to(ROOT)): digest(config),
                               str(placement.relative_to(ROOT)): digest(placement),
                               "tools/v41_stage_owner_preflight.py": digest(Path(__file__).resolve())},
                stage_count=28, expert_count=n_experts, cut_count=len(cuts), cuts=cuts,
                layer_owners=owners, per_die_rounding_delta_bytes=[x / p["group"] for x in delta],
                per_die_headroom_after_rounding_before_engram_spill_bytes=headroom_before_spill,
                per_die_headroom_after_rounding_and_engram_spill_bytes=headroom_after_spill,
                min_per_die_headroom_after_rounding_and_engram_spill_bytes=min(headroom_after_spill),
                missing_gates=["checkpoint tensor/scale/metadata placement by ROM address",
                               "program per stage and expert owner lookup for selected IDs",
                               "ordered cross-stage activation, expert-output and HC-state packets",
                               "bit-exact two-stage then 28-stage execution with measured link cycles"])


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(derive(), indent=2) + "\n")
    print(OUT)
