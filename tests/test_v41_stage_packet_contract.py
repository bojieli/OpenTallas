"""The integer owner candidate must preserve exact split-layer data order."""

import sys
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import v41_stage_owner_preflight as P  # noqa: E402
import v41_stage_packet_contract as C  # noqa: E402


def test_full_checkpoint_tensor_names_have_one_candidate_owner():
    if not C.SNAPSHOT.exists():
        pytest.skip("released checkpoint headers unavailable")
    record = C.derive()
    assert record["status"] == "candidate_packet_dependency_not_executable"
    assert record["candidate_preflight_min_per_die_headroom_after_spill_bytes"] < 5_000_000
    assert len(record["layer_tensor_ownership"]) == 40
    for rule in record["layer_tensor_ownership"]:
        assert len(rule["rank_ownership"]) == 4
        assert len(rule["dense_source_tensors"]) >= 30
        assert all(name.startswith(f"layers.{rule['layer']}.") for name in rule["dense_source_tensors"])
        for rank in rule["rank_ownership"]:
            assert rank["home_die"] == 4 * rule["home_stage"] + rank["rank"]
            assert rank["physical_rom_bank"] is None
            ranges = rank["routed_expert_ranges"]
            assert ranges[0]["expert_ids"][0] == 0
            assert ranges[-1]["expert_ids"][1] == 383
            for left, right in zip(ranges, ranges[1:]):
                assert left["expert_ids"][1] + 1 == right["expert_ids"][0]
    layer1 = record["layer_tensor_ownership"][1]
    assert layer1["engram_table_source_tensors"] == [
        "layers.1.engram.embed.scale", "layers.1.engram.embed.weight"]
    assert layer1["engram_table_owner"] == "unbound_table_die_or_spill"
    pinned = json.loads(C.OUT.read_text())
    assert pinned == record


def test_split_packets_cover_both_owner_sides_and_form_an_ordered_dag():
    owner = P.derive()["layer_owners"][1]
    split = C.representative_packets(owner, (0, 1, 151, 152, 200, 383))
    assert split["home_stage"] == 0 and split["remote_stage"] == 1
    assert split["local_expert_ids"] == [0, 1, 151]
    assert split["remote_expert_ids"] == [152, 200, 383]
    objects = {x["id"]: x for x in split["nodes"] + split["packets"]}
    assert len(objects) == len(split["nodes"]) + len(split["packets"])
    for item in objects.values():
        assert all(dep in objects for dep in item["depends_on"])
    # The serialized program order is topological even though local and remote
    # work may overlap after the activation packet arrives.
    done = set()
    pending = dict(objects)
    while pending:
        ready = [key for key, item in pending.items() if set(item["depends_on"]) <= done]
        assert ready, "cycle or missing data dependency"
        for key in ready:
            done.add(key)
            del pending[key]
    for rank in range(4):
        packets = [p for p in split["packets"] if p["rank"] == rank]
        assert [(p["phase"], p["useful_bytes"]) for p in packets] == [
            ("activation_forward", 20528), ("partial_forward", 5120),
            ("accumulator_return", 5120), ("continuation_forward", 40976)]
        assert [p["from_stage"] for p in packets] == [0, 0, 1, 0]
        assert [p["to_stage"] for p in packets] == [1, 1, 0, 1]
        assert packets[2]["payload"][0]["after_expert_ids"] == list(split["selected_expert_ids"])


def test_split_replay_matches_golden_order_and_detects_reassociation():
    split = C.representative_packets(P.derive()["layer_owners"][1],
                                     (0, 1, 151, 152, 200, 383))
    # These are post-w2, post-routing-weight BF16 values, the arithmetic
    # boundary used by golden.moe. Magnitudes make a reordered sum diverge.
    samples = [np.array(v, dtype=np.float32) for v in (
        (1e20, 1e20, 1e20), (1, -1e20, 3), (-1e20, 1, -1e20),
        (1, 4, 5), (2, 3, -1e20), (-2, -4, 1e20))]
    samples = [G.to_bf16(v) for v in samples]
    shared = G.to_bf16(np.array((7, -2, 1), dtype=np.float32))
    golden = np.zeros(3, dtype=np.float32)
    for expert in samples:
        golden = G.add(golden, expert)
    golden = G.to_bf16(G.add(golden, shared))
    partial = np.zeros(3, dtype=np.float32)
    for expert_id in split["local_expert_ids"]:
        partial = G.add(partial, samples[split["selected_expert_ids"].index(expert_id)])
    remote = partial.copy()  # transmitted FP32 bits, no BF16 round here
    for expert_id in split["remote_expert_ids"]:
        remote = G.add(remote, samples[split["selected_expert_ids"].index(expert_id)])
    replay = G.to_bf16(G.add(remote, shared))
    assert np.array_equal(golden.view(np.uint32), replay.view(np.uint32))
    wrong = np.zeros(3, dtype=np.float32)
    for expert in reversed(samples):
        wrong = G.add(wrong, expert)
    wrong = G.to_bf16(G.add(wrong, shared))
    assert not np.array_equal(golden.view(np.uint32), wrong.view(np.uint32))


def test_route_fails_closed_when_all_selected_experts_are_on_one_side():
    owner = P.derive()["layer_owners"][1]
    with pytest.raises(ValueError, match="both split stages"):
        C.representative_packets(owner, (0, 1, 2, 3, 4, 5))
