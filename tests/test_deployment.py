from __future__ import annotations

from pathlib import Path

import pytest

from opentallas.deployment import (
    A100_BF16_EXPANDED,
    A100_PACKED_BF16_EXECUTE,
    deployment_model,
)
from opentallas.schema import ModelProfile
from opentallas.workload import kv_traffic


ROOT = Path(__file__).resolve().parents[1]


def model(slug: str) -> ModelProfile:
    return ModelProfile.load(ROOT / "configs" / "models" / f"{slug}.json")


@pytest.mark.parametrize("slug", ["deepseek-v4-flash-0731", "deepseek-v4-pro-0813"])
def test_a100_expansion_is_larger_and_internally_exact(slug: str) -> None:
    packed = model(slug)
    expanded = deployment_model(packed, A100_BF16_EXPANDED)

    assert expanded.checkpoint_bytes > packed.checkpoint_bytes
    assert expanded.routed_weight_bytes > 3.7 * packed.routed_weight_bytes
    assert sum(expanded.layer_dense_weight_bytes) <= expanded.dense_weight_bytes
    assert sum(expanded.layer_routed_weight_bytes) == expanded.routed_weight_bytes
    assert expanded.metadata["deployment_policy"] == A100_BF16_EXPANDED


def test_a100_cache_expansion_is_derived_from_official_dimensions() -> None:
    packed = model("deepseek-v4-flash-0731")
    expanded = deployment_model(packed, A100_BF16_EXPANDED)
    sparse = next(
        group for group in expanded.attention_groups if group.kind == "compressed_sparse"
    )

    assert sparse.entry_bytes == 2 * 512
    assert sparse.index_entry_bytes == 2 * 128
    assert kv_traffic(expanded, 200_000).read_bytes > kv_traffic(
        packed, 200_000
    ).read_bytes


@pytest.mark.parametrize("slug", ["deepseek-v4-flash-0731", "deepseek-v4-pro-0813"])
def test_a100_packed_execution_retains_exact_released_storage(slug: str) -> None:
    packed = model(slug)
    deployed = deployment_model(packed, A100_PACKED_BF16_EXECUTE)

    assert deployed.checkpoint_bytes == packed.checkpoint_bytes
    assert deployed.dense_weight_bytes == packed.dense_weight_bytes
    assert deployed.routed_weight_bytes == packed.routed_weight_bytes
    assert deployed.attention_groups == packed.attention_groups
    assert deployed.metadata["deployment_policy"] == A100_PACKED_BF16_EXECUTE
    assert "unmeasured" in deployed.metadata["kv_cache_policy_status"]
