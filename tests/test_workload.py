from __future__ import annotations

from pathlib import Path

import pytest

from opentallas.schema import ModelProfile
from opentallas.workload import expected_expert_coverage, kv_traffic, rho_one, weight_traffic


ROOT = Path(__file__).resolve().parents[1]


def model(slug: str) -> ModelProfile:
    return ModelProfile.load(ROOT / "configs" / "models" / f"{slug}.json")


def test_expected_coverage_has_correct_limits() -> None:
    assert expected_expert_coverage(256, 6, 1) == pytest.approx(6 / 256)
    values = [expected_expert_coverage(256, 6, batch) for batch in (1, 8, 64, 1024)]
    assert values == sorted(values)
    assert values[-1] > 0.999999


@pytest.mark.parametrize(
    ("slug", "layers", "experts", "top_k"),
    [
        ("deepseek-v4-flash-0731", 43, 256, 6),
        ("deepseek-v4-pro-0813", 61, 384, 6),
        ("kimi-k3", 93, 896, 16),
        ("qwen3-8b", 36, 1, 1),
    ],
)
def test_measured_profiles_load(slug: str, layers: int, experts: int, top_k: int) -> None:
    item = model(slug)
    assert item.num_layers == layers
    assert item.num_experts == experts
    assert item.experts_per_token == top_k
    assert sum(group.count for group in item.attention_groups) == layers
    assert len(item.layer_dense_weight_bytes) == layers
    assert len(item.layer_routed_weight_bytes) == layers


def test_v4_kv_traffic_grows_but_sparse_topk_is_bounded() -> None:
    flash = model("deepseek-v4-flash-0731")
    low = kv_traffic(flash, 200_000)
    high = kv_traffic(flash, 1_000_000)
    assert low.read_bytes < high.read_bytes
    csa_low = next(item for item in low.breakdown if item["kind"] == "compressed_sparse")
    csa_high = next(item for item in high.breakdown if item["kind"] == "compressed_sparse")
    assert csa_low["main_entries_read_per_layer"] == csa_high["main_entries_read_per_layer"]
    assert csa_high["index_entries_scanned_per_layer"] == 250_000


def test_kimi_recurrent_traffic_is_context_independent() -> None:
    kimi = model("kimi-k3")
    low = kv_traffic(kimi, 200_000)
    high = kv_traffic(kimi, 1_000_000)
    low_kda = next(item for item in low.breakdown if item["kind"] == "recurrent")
    high_kda = next(item for item in high.breakdown if item["kind"] == "recurrent")
    assert low_kda["read_bytes"] == high_kda["read_bytes"]
    assert high.read_bytes > low.read_bytes * 4


def test_rho_and_advantage_decline_with_context_and_batch() -> None:
    pro = model("deepseek-v4-pro-0813")
    assert rho_one(pro, 200_000) > rho_one(pro, 1_000_000)
    kv = kv_traffic(pro, 200_000).read_bytes
    advantages = [1 + weight_traffic(pro, batch).total_bytes / (batch * kv) for batch in range(1, 129)]
    assert all(a >= b for a, b in zip(advantages, advantages[1:]))


def test_target_decode_traffic_excludes_resident_draft_and_lookup_weights() -> None:
    pro = model("deepseek-v4-pro-0813")
    streamed = weight_traffic(pro, 1).total_bytes
    assert pro.draft_dense_weight_bytes + pro.draft_routed_weight_bytes > 0
    assert pro.resident_only_weight_bytes > 0
    assert streamed < pro.checkpoint_bytes


def test_qwen_dense_gqa_bf16_traffic_is_exact() -> None:
    qwen = model("qwen3-8b")
    traffic = kv_traffic(qwen, 8_192)
    expected_entry_bytes = 2 * 8 * 128 * 2
    expected_cache_bytes = 36 * 8_192 * expected_entry_bytes
    assert traffic.read_bytes == expected_cache_bytes
    assert traffic.write_bytes == 36 * expected_entry_bytes
    assert traffic.storage_bytes_per_user == expected_cache_bytes
    assert qwen.dense_parameters == qwen.dense_weight_bytes / 2
    assert qwen.routed_parameters == 0
    assert qwen.routed_weight_bytes == 0
    assert qwen.metadata["tie_word_embeddings"] is False
