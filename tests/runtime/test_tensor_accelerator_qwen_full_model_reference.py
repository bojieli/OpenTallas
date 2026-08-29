from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jsonschema import Draft202012Validator, ValidationError
import numpy as np
import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from runtime.reference.qwen_full_model import (
    REFERENCE_SCHEMA,
    REFERENCE_VERSION,
    QwenFullModelReferenceError,
    _event,
    _segmented_matrix_block,
    publish_qwen_full_model_reference,
)
from runtime.tensor_accelerator.bf16 import dense_bf16_linear_bf16


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_REPORT_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_reference_v1.schema.json"
)
RETAINED_REFERENCE = (
    ROOT / "results/tensor_accelerator/qwen3_full_model_reference_v1.json"
)


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _reference_report() -> dict[str, Any]:
    digest = "a" * 64
    body = {
        "capability_id": digest,
        "checkpoint_lock_id": digest,
        "checks": {
            "all_399_checkpoint_tensors_authenticated": True,
            "all_617_operation_outputs_exact": True,
            "all_36_layer_boundaries_exact": True,
            "all_36_prepared_and_committed_states_exact": True,
            "all_70_counters_independently_derived": True,
            "complete_logits_and_unique_greedy_token_exact": True,
            "independent_scalar_kernel_cross_checks": True,
            "row_major_checkpoint_not_tiled_hbm_source": True,
            "segmented_k_not_fused_matrix_execution": True,
        },
        "counter_sha256": digest,
        "execution_report_id": digest,
        "graph_id": digest,
        "layer_outputs": [
            {
                "layer": layer,
                "payload_sha256": digest,
                "size_bytes": 8192,
                "tensor_id": f"hidden.{layer}",
            }
            for layer in range(1, 37)
        ],
        "outputs": {
            "committed_logits": {
                "greedy_maximum_count": 1,
                "greedy_token_id": 50994,
                "payload_sha256": digest,
                "size_bytes": 303872,
            },
            "final_normalization": {
                "payload_sha256": digest,
                "size_bytes": 8192,
            },
            "hidden_36": {"payload_sha256": digest, "size_bytes": 8192},
            "last_token": {"payload_sha256": digest, "size_bytes": 8192},
        },
        "reference_version": REFERENCE_VERSION,
        "request_id": digest,
        "saturation": {
            "by_kernel": {str(index): 0 for index in range(578)},
            "total": 0,
        },
        "schema": REFERENCE_SCHEMA,
        "state": [
            {
                "generation": 1,
                "key_payload_sha256": digest,
                "layer": layer,
                "length": 1,
                "resource_id": f"kv.layer.{layer}",
                "value_payload_sha256": digest,
            }
            for layer in range(36)
        ],
        "status": "pass",
    }
    return _reidentify(body, "reference_id")


def test_segmented_reference_matrix_matches_independent_fused_kernel() -> None:
    rng = np.random.default_rng(0x52454651)
    vocabulary = np.asarray(
        [
            0x0000,
            0x3D00,
            0x3E00,
            0x3F00,
            0x3F80,
            0x4000,
            0xBD00,
            0xBE00,
            0xBF00,
            0xBF80,
            0xC000,
        ],
        dtype=np.uint16,
    )
    inputs = rng.choice(vocabulary, size=(1, 512))
    weights = rng.choice(vocabulary, size=(64, 512))

    segmented, saturation = _segmented_matrix_block(inputs, weights)
    fused = dense_bf16_linear_bf16(
        inputs,
        weights,
        input_tile_rows=1,
        output_tile_rows=64,
    )
    np.testing.assert_array_equal(segmented, fused.values)
    assert saturation == fused.output_saturated_element_count


def test_reference_rejects_the_first_corrupted_operation_event() -> None:
    operation = SimpleNamespace(index=7, kind="MATMUL", operation_id="node.0007")
    observed = {
        "command_count": 2,
        "command_start": 10,
        "kernel_index": 7,
        "kind": "MATMUL",
        "operation_id": "node.0007",
        "outputs": {"tensor.output": {"payload_sha256": "b" * 64, "size_bytes": 2}},
    }
    with pytest.raises(
        QwenFullModelReferenceError,
        match="first execution divergence at 'node.0007'",
    ):
        _event(
            observed,
            operation,
            command_start=10,
            command_count=2,
            outputs={
                "tensor.output": {
                    "payload_sha256": "a" * 64,
                    "size_bytes": 2,
                }
            },
        )


def test_reference_has_no_simulator_compiler_checker_or_framework_import() -> None:
    source = (ROOT / "runtime/reference/qwen_full_model.py").read_text(encoding="utf-8")
    forbidden = (
        "runtime.tensor_accelerator",
        "qwen_full_model_simulator import",
        "qwen_full_model_physical import",
        "qwen_full_model_physical_checking import",
        "import torch",
        "import transformers",
        "from transformers",
    )
    assert not any(fragment in source for fragment in forbidden)


def test_reference_report_schema_is_strict_and_rejects_overclaim() -> None:
    schema = load_strict_json(REFERENCE_REPORT_SCHEMA)
    Draft202012Validator.check_schema(schema)
    report = _reference_report()
    Draft202012Validator(schema).validate(report)

    extra = copy.deepcopy(report)
    extra["timing_characterized"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(extra)

    weakened = copy.deepcopy(report)
    weakened["checks"]["all_617_operation_outputs_exact"] = False
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(weakened)


def test_reference_publication_is_canonical_content_addressed_and_no_overwrite(
    tmp_path: Path,
) -> None:
    report = _reference_report()
    output = tmp_path / "nested/reference.json"
    publish_qwen_full_model_reference(report, output)
    assert output.read_bytes() == canonical_json_bytes(report)
    with pytest.raises(QwenFullModelReferenceError, match="already exists"):
        publish_qwen_full_model_reference(report, output)

    forged = dict(report)
    forged["counter_sha256"] = "b" * 64
    with pytest.raises(QwenFullModelReferenceError, match="identity differs"):
        publish_qwen_full_model_reference(forged, tmp_path / "forged.json")


@pytest.mark.skipif(
    not RETAINED_REFERENCE.is_file(),
    reason="retained complete Qwen independent-reference report is unavailable",
)
def test_retained_reference_has_the_authentic_exact_identity() -> None:
    report = load_strict_json(RETAINED_REFERENCE)
    assert report["reference_id"] == (
        "9033bc2ca0d078ff1bf85a624c952f207d2d8042eb0a1bc8bd1830d9b28007fb"
    )
    assert report["execution_report_id"] == (
        "77b849e49608cacf9522eb16fad289385523c39618425e1e1c5f30126e504746"
    )
    assert report["outputs"]["committed_logits"]["greedy_token_id"] == 50994
    body = {key: value for key, value in report.items() if key != "reference_id"}
    assert report["reference_id"] == sha256_bytes(canonical_json_bytes(body))
