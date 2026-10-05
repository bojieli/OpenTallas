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
    DYNAMIC_REFERENCE_VERSION,
    DYNAMIC_SESSION_REFERENCE_SCHEMA,
    REFERENCE_SCHEMA,
    REFERENCE_VERSION,
    QwenFullModelReferenceError,
    _event,
    _segmented_matrix_block,
    publish_qwen_dynamic_session_reference,
    publish_qwen_full_model_reference,
)
from runtime.tensor_accelerator.bf16 import dense_bf16_linear_bf16


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_REPORT_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_reference_v1.schema.json"
)
DYNAMIC_REFERENCE_REPORT_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_dynamic_session_reference_v1.schema.json"
)
RETAINED_REFERENCE = (
    ROOT / "results/tensor_accelerator/qwen3_full_model_reference_v1.json"
)
RETAINED_DYNAMIC_REFERENCE = (
    ROOT
    / "results/tensor_accelerator/qwen3_short_generation_v1/reference.json"
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


def _dynamic_reference_report() -> dict[str, Any]:
    digest = "a" * 64
    states = [
        {
            "generation": 32,
            "key_payload_sha256": digest,
            "layer": layer,
            "length": 32,
            "resource_id": f"kv.layer.{layer}",
            "value_payload_sha256": digest,
        }
        for layer in range(36)
    ]
    body = {
        "aggregate_counter_sha256": digest,
        "build_id": digest,
        "capability_id": digest,
        "checkpoint_lock_id": digest,
        "checks": {
            "all_checkpoint_tensors_authenticated_per_transaction": True,
            "all_counters_independently_derived": True,
            "all_layer_boundaries_exact": True,
            "all_operation_outputs_exact": True,
            "all_runtime_bindings_independently_derived": True,
            "all_state_transitions_exact": True,
            "complete_logits_ties_and_tokens_exact": True,
            "decoded_text_exact": True,
            "independent_scalar_kernel_cross_checks": True,
            "row_major_checkpoint_not_tiled_hbm_weight_source": True,
            "segmented_k_not_fused_matrix_execution": True,
            "stateful_causal_chain_exact": True,
        },
        "claim_boundary": {
            "artifact_only_short_generation_verified": True,
            "exact_8000_token_acceptance": False,
            "simulator_report_mutated": False,
            "timing_or_performance": False,
        },
        "counts": {
            "checkpoint_tensor_authentications": 12768,
            "checkpoint_tensors_per_transaction": 399,
            "counter_comparisons": 2240,
            "counters_per_transaction": 70,
            "decode_transactions": 31,
            "generated_token_decisions": 32,
            "layer_boundary_comparisons": 1152,
            "operation_comparisons": 19744,
            "operations_per_transaction": 617,
            "rope_rows": 32,
            "state_resources_per_transaction": 36,
            "state_transition_comparisons": 1152,
            "transactions": 32,
        },
        "decoded": {
            "full_text": "!generated",
            "generated_text": "generated",
            "prompt_text": "!",
        },
        "final_state": states,
        "generated_token_ids": list(range(32)),
        "graph_id": digest,
        "hbm_logical_sha256": digest,
        "physical_plan_id": digest,
        "reference_version": DYNAMIC_REFERENCE_VERSION,
        "rope_coefficients": {
            "all_hbm_shards_sha256_verified": True,
            "layout": "position_major_cos_then_sin_bf16",
            "payload_sha256": digest,
            "positions": 8000,
            "qualified_rows_replayed": 32,
            "row_bytes": 512,
            "size_bytes": 4096000,
        },
        "schema": DYNAMIC_SESSION_REFERENCE_SCHEMA,
        "session_execution_id": digest,
        "session_id": digest,
        "status": "pass",
        "step_reference_chain_sha256": digest,
        "steps": [
            {
                "counter_sha256": digest,
                "execution_report_id": digest,
                "greedy_maximum_count": 2 if step == 2 else 1,
                "hidden_36_sha256": digest,
                "logits_sha256": digest,
                "output_token_id": step,
                "request_id": digest,
                "saturation_total": 0,
                "state_generation": step + 1,
                "state_length": step + 1,
                "step_index": step,
                "transaction_reference_id": digest,
            }
            for step in range(32)
        ],
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


def test_dynamic_reference_schema_and_publication_are_strict(
    tmp_path: Path,
) -> None:
    schema = load_strict_json(DYNAMIC_REFERENCE_REPORT_SCHEMA)
    Draft202012Validator.check_schema(schema)
    report = _dynamic_reference_report()
    Draft202012Validator(schema).validate(report)

    broadened = copy.deepcopy(report)
    broadened["claim_boundary"]["exact_8000_token_acceptance"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(broadened)

    output = tmp_path / "dynamic/reference.json"
    publish_qwen_dynamic_session_reference(report, output)
    assert output.read_bytes() == canonical_json_bytes(report)
    with pytest.raises(QwenFullModelReferenceError, match="already exists"):
        publish_qwen_dynamic_session_reference(report, output)

    forged = dict(report)
    forged["aggregate_counter_sha256"] = "b" * 64
    with pytest.raises(QwenFullModelReferenceError, match="identity differs"):
        publish_qwen_dynamic_session_reference(forged, tmp_path / "forged.json")


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


@pytest.mark.skipif(
    not RETAINED_DYNAMIC_REFERENCE.is_file(),
    reason="retained Qwen dynamic-session reference report is unavailable",
)
def test_retained_dynamic_reference_has_the_authentic_exact_identity() -> None:
    report = load_strict_json(RETAINED_DYNAMIC_REFERENCE)
    schema = load_strict_json(DYNAMIC_REFERENCE_REPORT_SCHEMA)
    Draft202012Validator(schema).validate(report)
    assert report["reference_id"] == (
        "9f17054b8a78fb52cbe23f5fb11fd16371045fb3f1814e27297a1fdfc7118151"
    )
    assert report["session_execution_id"] == (
        "9e53f5d79dff7f530652116df3a9196e3a58dd07375a07c2b6f3ae227b83f0f1"
    )
    assert report["step_reference_chain_sha256"] == (
        "8d11c040a5cdbd87e346f949b1dd6cfbb4335e79810126b09e5136e46779c11a"
    )
    assert report["counts"]["transactions"] == 32
    assert report["counts"]["operation_comparisons"] == 19_744
    assert report["counts"]["state_transition_comparisons"] == 1_152
    assert report["generated_token_ids"][12] == 66
    assert report["claim_boundary"]["exact_8000_token_acceptance"] is False
    body = {key: value for key, value in report.items() if key != "reference_id"}
    assert report["reference_id"] == sha256_bytes(canonical_json_bytes(body))
