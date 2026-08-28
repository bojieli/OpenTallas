from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from compiler.tensor_accelerator import build_deployment
from compiler.tensor_accelerator.common import load_strict_json
from runtime.tensor_accelerator import TensorAcceleratorSimulator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas/compiler/tensor_accelerator"
FIXTURE = ROOT / "testdata/compiler/tensor_accelerator_fixture"


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
    assert len(schemas) == 11
    by_name = {
        schema["$id"].rsplit("/", 1)[-1]: schema
        for schema in schemas
    }
    assert set(by_name) == {
        "capability_v1.schema.json",
        "deployment_v1.schema.json",
        "execution_expectations_v1.schema.json",
        "execution_report_v1.schema.json",
        "execution_request_v1.schema.json",
        "independent_check_v1.schema.json",
        "model_graph_v1.schema.json",
        "operator_coverage_v1.schema.json",
        "physical_plan_v1.schema.json",
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
    assert set(instances) == set(by_name)
    for schema_name, values in instances.items():
        for value in values:
            _validate(value, by_name[schema_name], registry)
