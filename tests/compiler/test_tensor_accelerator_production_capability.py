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
