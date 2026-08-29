from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct

from jsonschema import Draft202012Validator, ValidationError
import pytest
from referencing import Registry, Resource

from compiler.tensor_accelerator import build_deployment
from compiler.tensor_accelerator.bf16_qualification import (
    qualify_bf16_projection_payloads,
)
from compiler.tensor_accelerator.common import load_strict_json
from runtime.tensor_accelerator import TensorAcceleratorSimulator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas/compiler/tensor_accelerator"
FIXTURE = ROOT / "testdata/compiler/tensor_accelerator_fixture"


def _bf16_qualification() -> dict[str, object]:
    input_payload = struct.pack("<2H", 0x3F80, 0x4000)
    weight_payload = struct.pack("<4H", 0x4040, 0x4080, 0xBF80, 0x3F00)
    return qualify_bf16_projection_payloads(
        checkpoint_lock_id="a" * 64,
        input_record={
            "dtype": "BF16",
            "name": "embedding.weight",
            "payload_sha256": hashlib.sha256(input_payload).hexdigest(),
            "shape": [1, 2],
            "size_bytes": len(input_payload),
        },
        input_row=0,
        input_row_payload=input_payload,
        weight_record={
            "dtype": "BF16",
            "name": "projection.weight",
            "payload_sha256": hashlib.sha256(weight_payload).hexdigest(),
            "shape": [2, 2],
            "size_bytes": len(weight_payload),
        },
        weight_payload=weight_payload,
        selected_rows=[0, 1],
    )


def _schemas() -> tuple[dict[str, object], ...]:
    return tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMA_ROOT.glob("*.schema.json"))
    )


def _registry(schemas: tuple[dict[str, object], ...]) -> Registry:
    registry = Registry()
    for schema in schemas:
        registry = registry.with_resource(
            schema["$id"],
            Resource.from_contents(schema),
        )
    return registry


def _validate(
    instance: dict[str, object],
    schema: dict[str, object],
    registry: Registry,
) -> None:
    Draft202012Validator(schema, registry=registry).validate(instance)


def _attention_state_kernel_ir() -> dict[str, object]:
    return {
        "graph_id": "a" * 64,
        "kernel_ir_id": "b" * 64,
        "kernels": [
            {
                "attributes": {
                    "append_position_symbol": "position_start",
                    "generation_check": "exact_expected_generation",
                    "state_resource": "kv.layer.0",
                    "transaction_scope": "model_forward_request",
                    "visibility": "transaction_private_until_commit",
                },
                "index": 0,
                "inputs": ["layer.0.k_rotary", "layer.0.v"],
                "kind": "KV_PREPARE",
                "numeric_contract": "bf16_byte_preserving_state_v1",
                "outputs": ["state.kv.0"],
                "shape": {
                    "head_dim": 128,
                    "key_value_heads": 8,
                    "max_context_tokens": 8000,
                    "tokens_symbol": "span_tokens",
                },
                "source_operation_id": "node.0008",
            },
            {
                "attributes": {
                    "causal_mask_bf16_code": 0xFF7F,
                    "prepared_state_visibility": "transaction_private",
                    "probability_dtype": "bf16",
                    "query_heads_per_key_value_head": 4,
                    "scale_bf16_code": 0x3DB5,
                    "score_reduction_order": "strictly_increasing_head_dimension",
                    "softmax_compute_dtype": "fp32",
                    "softmax_reduction_lanes": 8,
                    "value_reduction_order": "strictly_increasing_context",
                },
                "index": 1,
                "inputs": ["layer.0.q_rotary", "state.kv.0"],
                "kind": "ATTENTION",
                "numeric_contract": "qwen3_gqa_fp32_softmax_bf16_v1",
                "outputs": ["layer.0.attention"],
                "shape": {
                    "head_dim": 128,
                    "key_value_heads": 8,
                    "max_context_tokens": 8000,
                    "query_heads": 32,
                    "query_tokens_symbol": "span_tokens",
                },
                "source_operation_id": "node.0009",
            },
            {
                "attributes": {
                    "atomic": True,
                    "coverage": "complete_operation",
                    "generation_increment": 1,
                    "source_atomic_state_count": 2,
                    "transaction_scope": "model_forward_request",
                },
                "index": 2,
                "inputs": ["output.logits"],
                "kind": "STATE_COMMIT",
                "numeric_contract": "bf16_byte_preserving_state_v1",
                "outputs": ["output.committed_logits"],
                "shape": {"atomic_state_count": 2},
                "source_operation_id": "state.commit",
                "state_resources": ["kv.layer.0", "kv.layer.1"],
            },
        ],
        "qualification_report_id": "c" * 64,
        "schema": "opentallas.production_tensor_kernel_ir.v1",
    }


def _elementwise_kernel_ir() -> dict[str, object]:
    return {
        "graph_id": "a" * 64,
        "kernel_ir_id": "b" * 64,
        "kernels": [
            {
                "attributes": {
                    "addition": "binary32_rne",
                    "input_dtype": "bf16",
                    "output_dtype": "bf16",
                    "output_rounding": "rne",
                    "zero_canonicalization": "positive",
                },
                "index": 0,
                "inputs": ["hidden.0", "layer.0.attention_projected"],
                "kind": "ADD",
                "numeric_contract": "bf16_add_rne_v1",
                "outputs": ["layer.0.post_attention"],
                "shape": {"rows": 1, "width": 4096},
                "source_operation_id": "node.0011",
            },
            {
                "attributes": {
                    "activation_boundary": "bf16_rne_before_up_multiply",
                    "exponential": "correctly_rounded_binary32_rne",
                    "input_dtype": "bf16",
                    "output_dtype": "bf16",
                    "output_rounding": "rne",
                    "sigmoid": "stable_sign_selected_binary32",
                    "zero_canonicalization": "positive",
                },
                "index": 1,
                "inputs": ["layer.0.mlp.gate", "layer.0.mlp.up"],
                "kind": "SILU_MUL",
                "numeric_contract": "qwen3_silu_mul_bf16_v1",
                "outputs": ["layer.0.mlp.gated"],
                "shape": {"rows": 1, "width": 12288},
                "source_operation_id": "node.0015",
            },
        ],
        "qualification_report_id": "c" * 64,
        "schema": "opentallas.production_tensor_kernel_ir.v1",
    }


def _selection_kernel_ir() -> dict[str, object]:
    return {
        "graph_id": "a" * 64,
        "kernel_ir_id": "b" * 64,
        "kernels": [
            {
                "attributes": {
                    "index_dtype": "u32",
                    "input_dtype": "bf16",
                    "output_dtype": "bf16",
                    "selection": "last_logical_row",
                },
                "index": 0,
                "inputs": ["hidden.final_norm"],
                "kind": "LAST_TOKEN_SELECT",
                "numeric_contract": "exact_index_select_v1",
                "outputs": ["hidden.last_token"],
                "shape": {
                    "maximum_rows": 8000,
                    "rows_symbol": "span_tokens",
                    "width": 4096,
                },
                "source_operation_id": "node.0614",
            }
        ],
        "qualification_report_id": "c" * 64,
        "schema": "opentallas.production_tensor_kernel_ir.v1",
    }


def test_production_kernel_ir_admits_neutral_attention_and_state_only() -> None:
    schemas = _schemas()
    by_name = {schema["$id"].rsplit("/", 1)[-1]: schema for schema in schemas}
    registry = _registry(schemas)
    schema = by_name["production_tensor_kernel_ir_v1.schema.json"]
    value = _attention_state_kernel_ir()
    _validate(value, schema, registry)

    physical_leak = copy.deepcopy(value)
    physical_leak["kernels"][1]["hbm_address"] = 0x1000
    with pytest.raises(ValidationError):
        _validate(physical_leak, schema, registry)


def test_production_kernel_ir_admits_bounded_neutral_add_and_silu_only() -> None:
    schemas = _schemas()
    by_name = {schema["$id"].rsplit("/", 1)[-1]: schema for schema in schemas}
    registry = _registry(schemas)
    schema = by_name["production_tensor_kernel_ir_v1.schema.json"]
    value = _elementwise_kernel_ir()
    _validate(value, schema, registry)

    physical_leak = copy.deepcopy(value)
    physical_leak["kernels"][0]["sram_bank"] = 3
    with pytest.raises(ValidationError):
        _validate(physical_leak, schema, registry)

    fused_boundary = copy.deepcopy(value)
    fused_boundary["kernels"][1]["attributes"]["activation_boundary"] = (
        "unrounded_host_expression"
    )
    with pytest.raises(ValidationError):
        _validate(fused_boundary, schema, registry)


def test_production_kernel_ir_admits_model_neutral_last_row_selection_only() -> None:
    schemas = _schemas()
    by_name = {schema["$id"].rsplit("/", 1)[-1]: schema for schema in schemas}
    registry = _registry(schemas)
    schema = by_name["production_tensor_kernel_ir_v1.schema.json"]
    value = _selection_kernel_ir()
    _validate(value, schema, registry)

    model_specific = copy.deepcopy(value)
    model_specific["kernels"][0]["attributes"]["selection"] = "qwen_last_token"
    with pytest.raises(ValidationError):
        _validate(model_specific, schema, registry)


def test_production_capability_schema_distinguishes_abi_24_and_25() -> None:
    schemas = _schemas()
    by_name = {schema["$id"].rsplit("/", 1)[-1]: schema for schema in schemas}
    registry = _registry(schemas)
    schema = by_name["production_capability_v1.schema.json"]
    elementwise = load_strict_json(
        ROOT / "configs/hardware/tensor_accelerator_development_v5.json"
    )
    selection = load_strict_json(
        ROOT / "configs/hardware/tensor_accelerator_development_v6.json"
    )
    _validate(elementwise, schema, registry)
    _validate(selection, schema, registry)

    missing_selection_contract = copy.deepcopy(selection)
    missing_selection_contract["qualified_numeric_contracts"].remove(
        "exact_index_select_v1"
    )
    with pytest.raises(ValidationError):
        _validate(missing_selection_contract, schema, registry)

    overclaimed_elementwise = copy.deepcopy(elementwise)
    overclaimed_elementwise["qualified_numeric_contracts"].insert(
        3, "exact_index_select_v1"
    )
    with pytest.raises(ValidationError):
        _validate(overclaimed_elementwise, schema, registry)

    missing_state = copy.deepcopy(selection)
    del missing_state["state_engine"]
    with pytest.raises(ValidationError):
        _validate(missing_state, schema, registry)


def test_layer_qualification_schema_rejects_incomplete_or_forged_evidence() -> None:
    schemas = _schemas()
    by_name = {schema["$id"].rsplit("/", 1)[-1]: schema for schema in schemas}
    registry = _registry(schemas)
    schema = by_name["layer_qualification_v1.schema.json"]
    value = load_strict_json(
        ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json"
    )
    _validate(value, schema, registry)

    incomplete = copy.deepcopy(value)
    del incomplete["sources"]["down_projection_weight"]
    with pytest.raises(ValidationError):
        _validate(incomplete, schema, registry)

    physical_leak = copy.deepcopy(value)
    physical_leak["intermediates"]["down"]["sram_bank"] = 4
    with pytest.raises(ValidationError):
        _validate(physical_leak, schema, registry)

    wrong_width = copy.deepcopy(value)
    wrong_width["output"]["hidden_1"]["shape"] = [1, 12288]
    with pytest.raises(ValidationError):
        _validate(wrong_width, schema, registry)

    false_equivalence = copy.deepcopy(value)
    false_equivalence["official_source_replay"]["status"] = "exact_match"
    with pytest.raises(ValidationError):
        _validate(false_equivalence, schema, registry)


def test_tensor_accelerator_schemas_are_strict_and_cover_artifacts(
    tmp_path: Path,
) -> None:
    schemas = _schemas()
    assert len(schemas) == 83
    by_name = {schema["$id"].rsplit("/", 1)[-1]: schema for schema in schemas}
    assert set(by_name) == {
        "attention_deployment_v1.schema.json",
        "attention_execution_v1.schema.json",
        "attention_expectations_v1.schema.json",
        "attention_independent_check_v1.schema.json",
        "attention_physical_plan_v1.schema.json",
        "attention_qualification_v1.schema.json",
        "attention_request_v1.schema.json",
        "attention_source_lock_v1.schema.json",
        "bf16_projection_qualification_v1.schema.json",
        "bf16_projection_deployment_v1.schema.json",
        "bf16_projection_execution_v1.schema.json",
        "bf16_projection_expectations_v1.schema.json",
        "bf16_projection_independent_check_v1.schema.json",
        "bf16_projection_kernel_v1.schema.json",
        "bf16_projection_physical_plan_v1.schema.json",
        "bf16_projection_request_v1.schema.json",
        "bf16_projection_source_lock_v1.schema.json",
        "capability_v1.schema.json",
        "connected_layer_deployment_v1.schema.json",
        "connected_layer_execution_v1.schema.json",
        "connected_layer_expectations_v1.schema.json",
        "connected_layer_independent_check_v1.schema.json",
        "connected_layer_physical_plan_v1.schema.json",
        "connected_layer_request_v1.schema.json",
        "connected_layer_source_lock_v1.schema.json",
        "deployment_v1.schema.json",
        "execution_expectations_v1.schema.json",
        "execution_report_v1.schema.json",
        "execution_request_v1.schema.json",
        "independent_check_v1.schema.json",
        "layer_downstream_deployment_v1.schema.json",
        "layer_downstream_execution_v1.schema.json",
        "layer_downstream_expectations_v1.schema.json",
        "layer_downstream_independent_check_v1.schema.json",
        "layer_downstream_physical_plan_v1.schema.json",
        "layer_downstream_request_v1.schema.json",
        "layer_downstream_source_lock_v1.schema.json",
        "layer_qualification_v1.schema.json",
        "model_graph_v1.schema.json",
        "model_graph_v2.schema.json",
        "operator_coverage_v1.schema.json",
        "physical_plan_v1.schema.json",
        "production_tensor_kernel_ir_v1.schema.json",
        "production_capability_v1.schema.json",
        "qkv_deployment_v1.schema.json",
        "qkv_execution_v1.schema.json",
        "qkv_expectations_v1.schema.json",
        "qkv_independent_check_v1.schema.json",
        "qkv_physical_plan_v1.schema.json",
        "qkv_qualification_v1.schema.json",
        "qkv_request_v1.schema.json",
        "qkv_source_lock_v1.schema.json",
        "qwen_final_output_qualification_v1.schema.json",
        "qwen_full_model_capacity_v1.schema.json",
        "qwen_full_model_deployment_v1.schema.json",
        "qwen_full_model_execution_v1.schema.json",
        "qwen_full_model_physical_check_v1.schema.json",
        "qwen_full_model_physical_plan_v1.schema.json",
        "qwen_full_model_reference_v1.schema.json",
        "qwen_full_model_request_v1.schema.json",
        "qwen_full_model_semantic_check_v1.schema.json",
        "qwen_full_model_semantic_coverage_v1.schema.json",
        "qwen_full_model_source_lock_v1.schema.json",
        "qwen_rtl_add_campaign_v1.schema.json",
        "qwen_rtl_add_sram_campaign_v1.schema.json",
        "qwen_rtl_add_vectors_v1.schema.json",
        "qwen_rtl_command_campaign_v1.schema.json",
        "qwen_rtl_command_vectors_v1.schema.json",
        "qwen_rtl_dma_campaign_v1.schema.json",
        "qwen_rtl_dma_add_campaign_v1.schema.json",
        "qwen_rtl_dma_add_vectors_v1.schema.json",
        "qwen_rtl_dma_vectors_v1.schema.json",
        "qwen_rtl_physical_campaign_v1.schema.json",
        "rmsnorm_deployment_v1.schema.json",
        "rmsnorm_execution_v1.schema.json",
        "rmsnorm_expectations_v1.schema.json",
        "rmsnorm_independent_check_v1.schema.json",
        "rmsnorm_physical_plan_v1.schema.json",
        "rmsnorm_qualification_v1.schema.json",
        "rmsnorm_request_v1.schema.json",
        "rmsnorm_source_lock_v1.schema.json",
        "source_lock_v1.schema.json",
        "tensor_kernel_ir_v1.schema.json",
    }
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
    registry = _registry(schemas)

    output = tmp_path / "deployment"
    build_deployment(
        FIXTURE / "model_graph.json",
        FIXTURE / "capability.json",
        output,
    )
    report = TensorAcceleratorSimulator.load(output).execute(
        FIXTURE / "execution_request.json"
    )
    instances = {
        "bf16_projection_qualification_v1.schema.json": [_bf16_qualification()],
        "capability_v1.schema.json": [
            load_strict_json(FIXTURE / "capability.json"),
            load_strict_json(output / "capability.json"),
        ],
        "deployment_v1.schema.json": [
            load_strict_json(output / "deployment_manifest.json")
        ],
        "execution_expectations_v1.schema.json": [
            load_strict_json(output / "execution_expectations.json")
        ],
        "execution_report_v1.schema.json": [report],
        "execution_request_v1.schema.json": [
            load_strict_json(FIXTURE / "execution_request.json")
        ],
        "independent_check_v1.schema.json": [
            load_strict_json(output / "checks/independent_check.json")
        ],
        "layer_qualification_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json"
            )
        ],
        "model_graph_v1.schema.json": [
            load_strict_json(FIXTURE / "model_graph.json"),
            load_strict_json(output / "ir/model_graph.json"),
        ],
        "model_graph_v2.schema.json": [
            load_strict_json(FIXTURE / "production_model_graph.json")
        ],
        "operator_coverage_v1.schema.json": [
            load_strict_json(output / "ir/operator_coverage.json")
        ],
        "physical_plan_v1.schema.json": [
            load_strict_json(output / "physical/physical_plan.json")
        ],
        "production_capability_v1.schema.json": [
            load_strict_json(
                ROOT / f"configs/hardware/tensor_accelerator_development_v{minor}.json"
            )
            for minor in range(1, 7)
        ],
        "qwen_final_output_qualification_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/"
                "qwen3_final_output_qualification.json"
            )
        ],
        "qwen_full_model_capacity_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_physical/"
                "physical/capacity_certificate.json"
            )
        ],
        "qwen_full_model_deployment_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_physical/"
                "deployment_manifest.json"
            )
        ],
        "qwen_full_model_physical_check_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_physical/"
                "checks/independent_check.json"
            )
        ],
        "qwen_full_model_physical_plan_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_physical/"
                "physical/physical_plan.json"
            )
        ],
        "qwen_full_model_reference_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_reference_v1.json"
            )
        ],
        "qwen_full_model_request_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_physical/"
                "request/execution_request.json"
            )
        ],
        "qwen_full_model_semantic_check_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_semantics/"
                "independent_check.json"
            )
        ],
        "qwen_full_model_semantic_coverage_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_semantics/"
                "coverage.json"
            )
        ],
        "qwen_full_model_source_lock_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_physical/"
                "source.lock.json"
            )
        ],
        "qwen_rtl_add_campaign_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_rtl_add_campaign.json"
            )
        ],
        "qwen_rtl_add_sram_campaign_v1.schema.json": [
            load_strict_json(
                ROOT
                / "results/tensor_accelerator/qwen3_rtl_add_sram_campaign.json"
            )
        ],
        "qwen_rtl_add_vectors_v1.schema.json": [
            load_strict_json(
                ROOT
                / "testdata/compiler/tensor_accelerator/qwen3_rtl_add_vectors.json"
            )
        ],
        "qwen_rtl_command_campaign_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_rtl_command_campaign.json"
            )
        ],
        "qwen_rtl_command_vectors_v1.schema.json": [
            load_strict_json(
                ROOT
                / "testdata/compiler/tensor_accelerator/"
                "qwen3_rtl_command_vectors.json"
            )
        ],
        "qwen_rtl_dma_campaign_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_rtl_dma_campaign.json"
            )
        ],
        "qwen_rtl_dma_add_campaign_v1.schema.json": [
            load_strict_json(
                ROOT
                / "results/tensor_accelerator/qwen3_rtl_dma_add_campaign.json"
            )
        ],
        "qwen_rtl_dma_add_vectors_v1.schema.json": [
            load_strict_json(
                ROOT
                / "testdata/compiler/tensor_accelerator/"
                "qwen3_rtl_dma_add_vectors.json"
            )
        ],
        "qwen_rtl_dma_vectors_v1.schema.json": [
            load_strict_json(
                ROOT
                / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_vectors.json"
            )
        ],
        "qwen_rtl_physical_campaign_v1.schema.json": [
            load_strict_json(
                ROOT
                / "results/tensor_accelerator/"
                "qwen3_rtl_ihp_sg13g2_physical_campaign.json"
            )
        ],
        "production_tensor_kernel_ir_v1.schema.json": [
            load_strict_json(
                ROOT / "results/tensor_accelerator/qwen3_full_model_semantics/"
                "tensor_kernel_ir.json"
            )
        ],
        "source_lock_v1.schema.json": [load_strict_json(output / "source.lock.json")],
        "tensor_kernel_ir_v1.schema.json": [
            load_strict_json(output / "ir/tensor_kernel_ir.json")
        ],
    }
    assert set(instances) == {
        name
        for name in by_name
        if not name.startswith("bf16_projection_")
        or name == "bf16_projection_qualification_v1.schema.json"
    } - {
        "attention_deployment_v1.schema.json",
        "attention_execution_v1.schema.json",
        "attention_expectations_v1.schema.json",
        "attention_independent_check_v1.schema.json",
        "attention_physical_plan_v1.schema.json",
        "attention_qualification_v1.schema.json",
        "attention_request_v1.schema.json",
        "attention_source_lock_v1.schema.json",
        "connected_layer_deployment_v1.schema.json",
        "connected_layer_execution_v1.schema.json",
        "connected_layer_expectations_v1.schema.json",
        "connected_layer_independent_check_v1.schema.json",
        "connected_layer_physical_plan_v1.schema.json",
        "connected_layer_request_v1.schema.json",
        "connected_layer_source_lock_v1.schema.json",
        "layer_downstream_deployment_v1.schema.json",
        "layer_downstream_execution_v1.schema.json",
        "layer_downstream_expectations_v1.schema.json",
        "layer_downstream_independent_check_v1.schema.json",
        "layer_downstream_physical_plan_v1.schema.json",
        "layer_downstream_request_v1.schema.json",
        "layer_downstream_source_lock_v1.schema.json",
        "qkv_deployment_v1.schema.json",
        "qkv_execution_v1.schema.json",
        "qkv_expectations_v1.schema.json",
        "qkv_independent_check_v1.schema.json",
        "qkv_physical_plan_v1.schema.json",
        "qkv_qualification_v1.schema.json",
        "qkv_request_v1.schema.json",
        "qkv_source_lock_v1.schema.json",
        "qwen_full_model_execution_v1.schema.json",
        "rmsnorm_deployment_v1.schema.json",
        "rmsnorm_execution_v1.schema.json",
        "rmsnorm_expectations_v1.schema.json",
        "rmsnorm_independent_check_v1.schema.json",
        "rmsnorm_physical_plan_v1.schema.json",
        "rmsnorm_qualification_v1.schema.json",
        "rmsnorm_request_v1.schema.json",
        "rmsnorm_source_lock_v1.schema.json",
    }
    for schema_name, values in instances.items():
        for value in values:
            _validate(value, by_name[schema_name], registry)
