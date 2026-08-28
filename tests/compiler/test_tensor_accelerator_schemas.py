from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

from jsonschema import Draft202012Validator
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


def test_tensor_accelerator_schemas_are_strict_and_cover_artifacts(
    tmp_path: Path,
) -> None:
    schemas = _schemas()
    assert len(schemas) == 39
    by_name = {
        schema["$id"].rsplit("/", 1)[-1]: schema
        for schema in schemas
    }
    assert set(by_name) == {
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
        "deployment_v1.schema.json",
        "execution_expectations_v1.schema.json",
        "execution_report_v1.schema.json",
        "execution_request_v1.schema.json",
        "independent_check_v1.schema.json",
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
        "bf16_projection_qualification_v1.schema.json": [
            _bf16_qualification()
        ],
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
        "source_lock_v1.schema.json": [
            load_strict_json(output / "source.lock.json")
        ],
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
        "production_capability_v1.schema.json",
        "production_tensor_kernel_ir_v1.schema.json",
        "qkv_deployment_v1.schema.json",
        "qkv_execution_v1.schema.json",
        "qkv_expectations_v1.schema.json",
        "qkv_independent_check_v1.schema.json",
        "qkv_physical_plan_v1.schema.json",
        "qkv_qualification_v1.schema.json",
        "qkv_request_v1.schema.json",
        "qkv_source_lock_v1.schema.json",
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
