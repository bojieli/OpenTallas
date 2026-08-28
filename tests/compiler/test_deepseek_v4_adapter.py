from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

from compiler.frontend.deepseek_v4 import (
    CONFIG_SHA256,
    INDEX_SHA256,
    PAYLOAD_BYTES,
    TENSOR_COUNT,
    TENSOR_STRUCTURE_SHA256,
    DeepSeekV4AdapterError,
    TensorSpec,
    build_expected_tensor_contract,
    build_official_tensor_specs,
    load_official_config,
    tensor_structure_sha256,
    validate_observed_tensor_records,
    validate_official_config,
)


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "compiler/models/deepseek-v4-flash-0731"
INVENTORY = ROOT / "data/inventory/deepseek-v4-flash-0731.json"


@pytest.fixture(scope="module")
def official_config() -> dict:
    return load_official_config()


@pytest.fixture(scope="module")
def official_specs(official_config: dict) -> tuple[TensorSpec, ...]:
    return build_official_tensor_specs(official_config)


def _pattern(name: str) -> str:
    value = re.sub(r"(?<=layers\.)\d+", "{layer}", name)
    value = re.sub(r"(?<=experts\.)\d+", "{expert}", value)
    return re.sub(r"(?<=mtp\.)\d+", "{mtp}", value)


def test_committed_config_is_byte_exact_official_source(
    official_config: dict,
) -> None:
    config_path = TARGET / "config.json"
    source = json.loads((TARGET / "checkpoint_source.json").read_text())
    expected = {item["path"]: item for item in source["expected_files"]}
    payload = config_path.read_bytes()

    assert hashlib.sha256(payload).hexdigest() == CONFIG_SHA256
    assert expected["config.json"] == {
        "path": "config.json",
        "sha256": CONFIG_SHA256,
        "size_bytes": len(payload),
    }
    assert expected["model.safetensors.index.json"]["sha256"] == INDEX_SHA256
    assert official_config["num_nextn_predict_layers"] == 1
    assert official_config["compress_ratios"][-3:] == [0, 0, 0]


def test_adapter_recovers_complete_official_header_structure(
    official_specs: tuple[TensorSpec, ...],
) -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    dtype_counts = Counter(spec.storage_dtype for spec in official_specs)
    dtype_bytes = Counter()
    for spec in official_specs:
        dtype_bytes[spec.storage_dtype] += spec.size_bytes

    assert len(official_specs) == TENSOR_COUNT == inventory["tensor_count"]
    assert sum(spec.size_bytes for spec in official_specs) == PAYLOAD_BYTES
    assert (
        PAYLOAD_BYTES
        == inventory["checkpoint_bytes"]
        == inventory["header_storage_bytes"]
    )
    assert tensor_structure_sha256(official_specs) == TENSOR_STRUCTURE_SHA256
    assert dict(sorted(dtype_counts.items())) == inventory["dtype_tensor_counts"]
    assert dict(sorted(dtype_bytes.items())) == inventory["dtype_bytes"]
    assert len({_pattern(spec.name) for spec in official_specs}) == 98


def test_every_scale_and_mxfp4_payload_has_an_exact_owner(
    official_specs: tuple[TensorSpec, ...],
) -> None:
    by_name = {spec.name: spec for spec in official_specs}
    scales = [spec for spec in official_specs if spec.scale_for is not None]
    fp4_weights = [
        spec
        for spec in official_specs
        if spec.logical_dtype == "MXFP4_E2M1_X2"
    ]

    assert len(by_name) == TENSOR_COUNT
    assert len(scales) == 35_718
    assert len(fp4_weights) == 35_328
    assert all(scale.logical_dtype == "UE8M0_SCALE" for scale in scales)
    assert all(scale.scale_for in by_name for scale in scales)
    assert all(by_name[scale.scale_for].semantic_role.endswith(".weight") for scale in scales)
    assert all(weight.expert is not None for weight in fp4_weights)
    assert all(weight.storage_dtype == "I8" for weight in fp4_weights)


def test_main_and_dspark_tensor_names_cover_exact_stage_topology(
    official_specs: tuple[TensorSpec, ...],
) -> None:
    names = {spec.name for spec in official_specs}
    scope_counts = Counter(spec.scope for spec in official_specs)

    assert scope_counts == {"main": 67_606, "dspark": 4_705, "global": 6}
    assert "layers.0.ffn.gate.tid2eid" in names
    assert "layers.2.ffn.gate.tid2eid" in names
    assert "layers.3.ffn.gate.bias" in names
    assert "layers.2.attn.indexer.wq_b.weight" in names
    assert "layers.3.attn.compressor.ape" in names
    assert "layers.3.attn.indexer.wq_b.weight" not in names
    assert "mtp.0.main_proj.weight" in names
    assert "mtp.2.markov_head.markov_w2.weight" in names
    assert "mtp.2.confidence_head.proj.weight" in names
    assert not any(name.startswith("mtp.3.") for name in names)


def test_expected_contract_is_deterministic_and_keeps_execution_gate_open(
    official_config: dict,
) -> None:
    first = build_expected_tensor_contract(official_config)
    second = build_expected_tensor_contract(official_config)
    assert first == second
    assert first["contract_id"] == (
        "61436c23d676cf110ff57f82a4e68b1ba4f5c134f74aea4528bdb5766ce683f3"
    )
    assert first["pattern_count"] == 98
    assert first["coverage"] == {
        "expected_tensor_count": TENSOR_COUNT,
        "expected_payload_bytes": PAYLOAD_BYTES,
        "extra_tensor_count": None,
        "missing_tensor_count": None,
        "observed_tensor_count": None,
        "unknown_role_count": 0,
        "validation_status": "expected_contract_only",
    }
    assert first["operator_graph_status"] == "not_yet_executable"
    assert first["adaptations"][0]["root_config_value"] == {
        "num_nextn_predict_layers": 1
    }
    assert first["adaptations"][0]["resolved_value"] == {
        "dspark_stage_count": 3
    }
    schema = json.loads(
        (
            ROOT
            / "schemas/compiler/deepseek_v4_tensor_contract_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(first)


def test_observed_tensor_validator_fails_on_any_structural_change(
    official_config: dict, official_specs: tuple[TensorSpec, ...]
) -> None:
    records = [spec.structure_record() for spec in official_specs]
    assert validate_observed_tensor_records(records, official_config) == {
        "payload_bytes": PAYLOAD_BYTES,
        "status": "pass",
        "tensor_count": TENSOR_COUNT,
        "tensor_structure_sha256": TENSOR_STRUCTURE_SHA256,
    }

    changed = copy.deepcopy(records)
    changed[0]["shape"][0] += 1
    with pytest.raises(DeepSeekV4AdapterError, match="mismatched"):
        validate_observed_tensor_records(changed, official_config)

    duplicate = [*records, copy.deepcopy(records[0])]
    with pytest.raises(DeepSeekV4AdapterError, match="duplicate"):
        validate_observed_tensor_records(duplicate, official_config)


def test_architecture_affecting_config_drift_fails_closed(
    official_config: dict,
) -> None:
    changed = copy.deepcopy(official_config)
    changed["num_experts_per_tok"] = 8
    with pytest.raises(DeepSeekV4AdapterError, match="num_experts_per_tok"):
        validate_official_config(changed)

    changed = copy.deepcopy(official_config)
    changed["compress_ratios"][3] = 4
    with pytest.raises(DeepSeekV4AdapterError, match="compress_ratios"):
        build_official_tensor_specs(changed)


def test_deepseek_contract_cli_emits_canonical_document(tmp_path: Path) -> None:
    output = tmp_path / "tensor-contract.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "describe-deepseek-v4",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    value = json.loads(output.read_text(encoding="ascii"))
    assert value["contract_id"] == (
        "61436c23d676cf110ff57f82a4e68b1ba4f5c134f74aea4528bdb5766ce683f3"
    )
    assert "described 72317 official tensors" in result.stdout
