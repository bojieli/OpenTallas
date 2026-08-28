from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from compiler.tensor_accelerator.production_capability import (
    ProductionCapabilityError,
    load_production_capability,
    parse_production_capability,
)


ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = ROOT / "configs/hardware/tensor_accelerator_development_v1.json"
CAPABILITY_V2_PATH = ROOT / "configs/hardware/tensor_accelerator_development_v2.json"
CAPABILITY_V3_PATH = ROOT / "configs/hardware/tensor_accelerator_development_v3.json"
CAPABILITY_V4_PATH = ROOT / "configs/hardware/tensor_accelerator_development_v4.json"


def _rehash(value: dict[str, object]) -> None:
    body = {key: item for key, item in value.items() if key != "capability_id"}
    value["capability_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_development_capability_covers_both_models_without_performance_claims() -> None:
    capability = load_production_capability(CAPABILITY_PATH)
    assert capability.declared_model_profiles == (
        "deepseek-v4-flash-0731-ordinary-target",
        "qwen3-8b",
    )
    assert capability.qualified_execution_modes == ("bf16_tensor",)
    assert capability.qualified_numeric_contracts == (
        "bf16_bf16_fp32_sequential_rne_v1",
    )
    assert capability.hbm.external_at_130nm_boundary is True
    assert capability.hbm.capacity_bytes == 256 * 1024**3
    assert capability.sram.capacity_bytes == 16 * 1024**2
    assert capability.sram.bank_base(3) == 3 * 1024**2
    evidence = capability.to_dict()["evidence"]
    assert evidence == {
        "classification": "uncharacterized_development",
        "performance_claims_permitted": False,
        "physical_characterization_id": None,
        "process_node_nm": None,
    }
    assert "clock" not in capability.to_dict()
    assert "latency" not in canonical_json_bytes(capability.to_dict()).decode("ascii")
    assert "energy" not in canonical_json_bytes(capability.to_dict()).decode("ascii")


def test_v21_capability_adds_only_bounded_uncharacterized_rmsnorm() -> None:
    capability = load_production_capability(CAPABILITY_V2_PATH)
    assert (capability.command_abi_major, capability.command_abi_minor) == (2, 1)
    assert capability.qualified_execution_modes == (
        "bf16_tensor",
        "vector_fp32",
    )
    assert capability.qualified_numeric_contracts == (
        "bf16_bf16_fp32_sequential_rne_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
    )
    assert capability.vector_engine is not None
    assert capability.vector_engine.max_rows == 64
    assert capability.vector_engine.max_width == 16384
    assert capability.vector_engine.max_rope_positions is None
    assert capability.to_dict()["evidence"]["performance_claims_permitted"] is False

    missing_vector = copy.deepcopy(capability.to_dict())
    del missing_vector["vector_engine"]
    _rehash(missing_vector)
    with pytest.raises(ProductionCapabilityError, match="must include"):
        parse_production_capability(missing_vector)

    overclaimed_legacy = copy.deepcopy(load_strict_json(CAPABILITY_PATH))
    overclaimed_legacy["qualified_execution_modes"] = [
        "bf16_tensor",
        "vector_fp32",
    ]
    overclaimed_legacy["qualified_numeric_contracts"] = [
        "bf16_bf16_fp32_sequential_rne_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
    ]
    overclaimed_legacy["vector_engine"] = {"max_rows": 64, "max_width": 16384}
    _rehash(overclaimed_legacy)
    with pytest.raises(ProductionCapabilityError, match="must remain"):
        parse_production_capability(overclaimed_legacy)


def test_v22_capability_adds_bounded_qwen_rope_without_timing_claims() -> None:
    capability = load_production_capability(CAPABILITY_V3_PATH)
    assert (capability.command_abi_major, capability.command_abi_minor) == (2, 2)
    assert capability.qualified_numeric_contracts == (
        "bf16_bf16_fp32_sequential_rne_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
        "qwen3_rope_fp32_bf16_v1",
    )
    vector = capability.vector_engine
    assert vector is not None
    assert vector.max_rows == 64
    assert vector.max_width == 16384
    assert vector.max_rope_positions == 8000
    assert vector.max_query_heads == 32
    assert vector.max_key_value_heads == 8
    assert vector.rope_head_dim == 128
    assert capability.to_dict()["evidence"]["performance_claims_permitted"] is False

    incomplete = copy.deepcopy(capability.to_dict())
    del incomplete["vector_engine"]["rope_head_dim"]
    _rehash(incomplete)
    with pytest.raises(ProductionCapabilityError, match="complete group"):
        parse_production_capability(incomplete)

    underbounded = copy.deepcopy(capability.to_dict())
    underbounded["vector_engine"]["max_rope_positions"] = 7999
    _rehash(underbounded)
    with pytest.raises(ProductionCapabilityError, match="do not cover"):
        parse_production_capability(underbounded)


def test_v23_capability_adds_bounded_qwen_attention_and_transactional_state() -> None:
    capability = load_production_capability(CAPABILITY_V4_PATH)
    assert (capability.command_abi_major, capability.command_abi_minor) == (2, 3)
    assert capability.qualified_execution_modes == (
        "bf16_tensor",
        "transactional_state",
        "vector_fp32",
    )
    assert capability.qualified_numeric_contracts == (
        "bf16_bf16_fp32_sequential_rne_v1",
        "bf16_byte_preserving_state_v1",
        "qwen3_gqa_fp32_softmax_bf16_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
        "qwen3_rope_fp32_bf16_v1",
    )
    vector = capability.vector_engine
    assert vector is not None
    assert vector.max_attention_context_tokens == 8000
    assert vector.attention_head_dim == 128
    assert vector.softmax_reduction_lanes == 8
    state = capability.state_engine
    assert state is not None
    assert state.generation_bits == 64
    assert state.transaction_id_bits == 64
    assert state.position_bits == 20
    assert state.length_bits == 21
    assert state.max_inflight_transactions == 8
    assert state.max_resources_per_transaction == 64
    assert capability.to_dict()["evidence"]["performance_claims_permitted"] is False

    missing_state = copy.deepcopy(capability.to_dict())
    del missing_state["state_engine"]
    _rehash(missing_state)
    with pytest.raises(ProductionCapabilityError, match="must include"):
        parse_production_capability(missing_state)

    incomplete_attention = copy.deepcopy(capability.to_dict())
    del incomplete_attention["vector_engine"]["softmax_reduction_lanes"]
    _rehash(incomplete_attention)
    with pytest.raises(ProductionCapabilityError, match="complete group"):
        parse_production_capability(incomplete_attention)

    underbounded_state = copy.deepcopy(capability.to_dict())
    underbounded_state["state_engine"]["max_resources_per_transaction"] = 36
    _rehash(underbounded_state)
    with pytest.raises(ProductionCapabilityError, match="cross-model union"):
        parse_production_capability(underbounded_state)


def test_all_committed_capability_minors_remain_canonical_and_loadable() -> None:
    observed = tuple(
        load_production_capability(path).command_abi_minor
        for path in (
            CAPABILITY_PATH,
            CAPABILITY_V2_PATH,
            CAPABILITY_V3_PATH,
            CAPABILITY_V4_PATH,
        )
    )
    assert observed == (0, 1, 2, 3)


def test_capability_rejects_identity_ordering_and_union_drift() -> None:
    source = load_strict_json(CAPABILITY_PATH)
    bad_id = copy.deepcopy(source)
    bad_id["tensor_engine"]["max_k"] = 128
    with pytest.raises(ProductionCapabilityError, match="capability_id mismatch"):
        parse_production_capability(bad_id)

    bad_order = copy.deepcopy(source)
    bad_order["formats"] = list(reversed(bad_order["formats"]))
    _rehash(bad_order)
    with pytest.raises(ProductionCapabilityError, match="lexicographically sorted"):
        parse_production_capability(bad_order)

    missing_model = copy.deepcopy(source)
    missing_model["declared_model_profiles"] = ["qwen3-8b"]
    _rehash(missing_model)
    with pytest.raises(ProductionCapabilityError, match="both target model"):
        parse_production_capability(missing_model)


def test_capability_rejects_characterized_or_internal_hbm_overclaim() -> None:
    source = load_strict_json(CAPABILITY_PATH)
    characterized = copy.deepcopy(source)
    characterized["evidence"]["performance_claims_permitted"] = True
    characterized["evidence"]["process_node_nm"] = 130
    _rehash(characterized)
    with pytest.raises(ProductionCapabilityError, match="uncharacterized"):
        parse_production_capability(characterized)

    internal_hbm = copy.deepcopy(source)
    internal_hbm["hbm"]["external_at_130nm_boundary"] = False
    _rehash(internal_hbm)
    with pytest.raises(ProductionCapabilityError, match="must be true"):
        parse_production_capability(internal_hbm)
