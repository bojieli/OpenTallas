"""The adopted byte-fluid stage map is not silently treated as an expert map."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_stage_owner_preflight as P  # noqa: E402


def test_every_stage_cut_rounds_to_whole_expert_without_exceeding_coarse_rom():
    record = P.derive()
    assert record["status"] == "coarse_integer_candidate_not_executable"
    assert record["cut_count"] == 27
    assert len(record["layer_owners"]) == 40
    assert record["min_per_die_headroom_bytes"] > 60_000_000
    first = record["cuts"][0]
    assert (first["layer"], first["from_stage"], first["to_stage"],
            first["integer_expert_cut"]) == (1, 0, 1, 152)
    assert first["earlier_expert_ids"] == [0, 151]
    assert first["later_expert_ids"] == [152, 383]
    for owner in record["layer_owners"]:
        parts = owner["routed_expert_candidate_owners"]
        assert parts[0]["expert_ids"][0] == 0
        assert parts[-1]["expert_ids"][1] == 383
        if len(parts) == 2:
            assert parts[0]["expert_ids"][1] + 1 == parts[1]["expert_ids"][0]
