from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.production_model import compute_graph_id
from compiler.tensor_accelerator.qwen_full_model_semantics import (
    QwenFullModelSemanticError,
    build_qwen_full_model_semantics,
)
from compiler.tensor_accelerator.qwen_full_model_semantics_checking import (
    QwenFullModelSemanticCheckError,
    check_qwen_full_model_semantics,
)


ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json"
CAPABILITY = ROOT / "configs/hardware/tensor_accelerator_development_v6.json"
QKV = ROOT / "results/tensor_accelerator/qwen3_qkv_qualification.json"
ATTENTION = ROOT / "results/tensor_accelerator/qwen3_attention_qualification.json"
LAYER = ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json"
FINAL = ROOT / "results/tensor_accelerator/qwen3_final_output_qualification.json"
RETAINED = ROOT / "results/tensor_accelerator/qwen3_full_model_semantics"
COVERAGE = RETAINED / "coverage.json"
KERNEL_IR = RETAINED / "tensor_kernel_ir.json"
CHECK = RETAINED / "independent_check.json"
SCHEMA_ROOT = ROOT / "schemas/compiler/tensor_accelerator"
HAS_REAL_SOURCES = all(
    path.is_file()
    for path in (
        GRAPH,
        CAPABILITY,
        QKV,
        ATTENTION,
        LAYER,
        FINAL,
        COVERAGE,
        KERNEL_IR,
        CHECK,
    )
)
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES,
    reason="complete authentic Qwen semantic sources unavailable",
)

COVERAGE_ID = "00dbdf8dbb0278bac831027a1396f79a08a399a83c6ce0387cd981fabf62b106"
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
CHECK_ID = "280ee81a2229b12d079d0b104a1f88e23df59989e60bd011adfaaa68910a2215"


def _build(graph: Path = GRAPH) -> tuple[dict[str, Any], dict[str, Any]]:
    return build_qwen_full_model_semantics(
        model_graph_path=graph,
        capability_path=CAPABILITY,
        qkv_qualification_path=QKV,
        attention_qualification_path=ATTENTION,
        layer_qualification_path=LAYER,
        final_output_qualification_path=FINAL,
    )


def _reidentify(value: dict[str, Any], field: str) -> None:
    import hashlib

    value[field] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()


@pytest.fixture(scope="module")
def generated() -> tuple[dict[str, Any], dict[str, Any]]:
    if not HAS_REAL_SOURCES:
        pytest.skip("complete authentic Qwen semantic sources unavailable")
    return _build()


@REAL
def test_complete_qwen_semantics_are_exact_dynamic_and_retained(
    generated: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    coverage, kernel_ir = generated
    assert coverage == load_strict_json(COVERAGE)
    assert kernel_ir == load_strict_json(KERNEL_IR)
    assert coverage["report_id"] == COVERAGE_ID
    assert kernel_ir["kernel_ir_id"] == KERNEL_IR_ID
    assert coverage["operation_count"] == coverage["kernel_count"] == 617
    assert coverage["state_coverage"]["resource_count"] == 36
    assert coverage["unknown_operations"] == []
    assert coverage["claim_boundary"] == {
        "complete_graph_operation_coverage": True,
        "complete_graph_state_contract_coverage": True,
        "complete_neutral_kernel_lowering": True,
        "full_model_execution": False,
        "physical_plan": False,
        "timing_or_performance": False,
    }
    kernels = kernel_ir["kernels"]
    assert len(kernels) == 617
    assert [kernel["index"] for kernel in kernels] == list(range(617))
    assert kernels[0]["shape"] == {
        "rows": {"maximum": 8000, "multiplier": 1, "symbol": "span_tokens"},
        "width": 4096,
    }
    assert kernels[0]["attributes"]["source_index_dtype"] == "i64"
    assert kernels[0]["attributes"]["index_dtype"] == "u32"
    assert kernels[0]["attributes"]["index_conversion"] == ("checked_nonnegative_u32")
    assert kernels[5]["shape"] == {
        "rows": {"maximum": 256000, "multiplier": 32, "symbol": "span_tokens"},
        "width": 128,
    }
    assert kernels[6]["shape"] == {
        "rows": {"maximum": 64000, "multiplier": 8, "symbol": "span_tokens"},
        "width": 128,
    }
    assert kernels[7]["attributes"]["position_symbol"] == "position_start"
    assert kernels[7]["attributes"]["position_count_symbol"] == "span_tokens"
    assert kernels[7]["attributes"]["position_progression"] == (
        "consecutive_from_start"
    )
    assert kernels[613]["shape"] == {
        "rows": {"maximum": 8000, "multiplier": 1, "symbol": "span_tokens"},
        "width": 4096,
    }
    assert kernels[614]["shape"] == {
        "maximum_rows": 8000,
        "rows_symbol": "span_tokens",
        "width": 4096,
    }
    assert kernels[615]["shape"] == {
        "reduction_width": 4096,
        "rows": 1,
        "width": 151936,
    }
    assert kernels[616]["attributes"]["coverage"] == "complete_operation"
    assert len(kernels[616]["state_resources"]) == 36
    encoded = canonical_json_bytes(kernel_ir)
    for forbidden in (
        b"HBM_",
        b"ROM_",
        b"SRAM_",
        b"bank_id",
        b"command_opcode",
        b"physical_address",
    ):
        assert forbidden not in encoded


@REAL
def test_independent_semantic_check_is_exact_and_retained() -> None:
    check = check_qwen_full_model_semantics(
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        coverage_path=COVERAGE,
        kernel_ir_path=KERNEL_IR,
        qkv_qualification_path=QKV,
        attention_qualification_path=ATTENTION,
        layer_qualification_path=LAYER,
        final_output_qualification_path=FINAL,
    )
    assert check == load_strict_json(CHECK)
    assert check["check_id"] == CHECK_ID
    assert check["operation_count"] == 617
    assert check["state_resource_count"] == 36
    assert all(check["checks"].values())


@REAL
def test_complete_semantic_artifacts_validate_strict_schemas() -> None:
    cases = (
        (
            "qwen_full_model_semantic_coverage_v1.schema.json",
            COVERAGE,
        ),
        ("production_tensor_kernel_ir_v1.schema.json", KERNEL_IR),
        ("qwen_full_model_semantic_check_v1.schema.json", CHECK),
    )
    for schema_name, artifact_path in cases:
        schema = load_strict_json(SCHEMA_ROOT / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(load_strict_json(artifact_path))


@REAL
def test_complete_semantic_builder_rejects_contract_drift(tmp_path: Path) -> None:
    graph = load_strict_json(GRAPH)
    graph["operations"][614]["numeric_contract"] = "bf16_add_rne_v1"
    graph["graph_id"] = compute_graph_id(graph)
    path = tmp_path / "contract-drift.json"
    write_canonical_json(path, graph)
    with pytest.raises(QwenFullModelSemanticError, match="semantic contract differs"):
        _build(path)


@REAL
def test_independent_checker_rejects_dynamic_shape_and_claim_forgery(
    tmp_path: Path,
) -> None:
    kernel_ir = copy.deepcopy(load_strict_json(KERNEL_IR))
    kernel_ir["kernels"][5]["shape"]["rows"]["multiplier"] = 31
    _reidentify(kernel_ir, "kernel_ir_id")
    forged_kernel = tmp_path / "forged-kernel.json"
    write_canonical_json(forged_kernel, kernel_ir)
    with pytest.raises(QwenFullModelSemanticCheckError, match="shape differs"):
        check_qwen_full_model_semantics(
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            coverage_path=COVERAGE,
            kernel_ir_path=forged_kernel,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )

    coverage = copy.deepcopy(load_strict_json(COVERAGE))
    coverage["claim_boundary"]["full_model_execution"] = True
    _reidentify(coverage, "report_id")
    forged_coverage = tmp_path / "forged-coverage.json"
    write_canonical_json(forged_coverage, coverage)
    with pytest.raises(QwenFullModelSemanticCheckError, match="claim boundary differs"):
        check_qwen_full_model_semantics(
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            coverage_path=forged_coverage,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )
    schema = load_strict_json(
        SCHEMA_ROOT / "qwen_full_model_semantic_coverage_v1.schema.json"
    )
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(coverage)


@REAL
def test_independent_checker_rejects_numeric_and_qualification_drift(
    tmp_path: Path,
) -> None:
    kernel_ir = copy.deepcopy(load_strict_json(KERNEL_IR))
    kernel_ir["kernels"][2]["attributes"]["reduction_order"] = "reassociated"
    _reidentify(kernel_ir, "kernel_ir_id")
    forged_kernel = tmp_path / "numeric-drift.json"
    write_canonical_json(forged_kernel, kernel_ir)
    with pytest.raises(QwenFullModelSemanticCheckError, match="numeric attributes"):
        check_qwen_full_model_semantics(
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            coverage_path=COVERAGE,
            kernel_ir_path=forged_kernel,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )

    qkv = copy.deepcopy(load_strict_json(QKV))
    qkv["numeric_contracts"].remove("qwen3_rope_fp32_bf16_v1")
    _reidentify(qkv, "report_id")
    forged_qkv = tmp_path / "qualification-drift.json"
    write_canonical_json(forged_qkv, qkv)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="qualification source binding differs",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            coverage_path=COVERAGE,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=forged_qkv,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )


@REAL
def test_semantic_paths_reject_dynamic_request_and_checkpoint_graph_drift(
    tmp_path: Path,
) -> None:
    graph = load_strict_json(GRAPH)
    graph["entrypoints"][0]["predicate"]["terms"][1]["value"] = 7999
    graph["graph_id"] = compute_graph_id(graph)
    request_drift = tmp_path / "request-drift.json"
    write_canonical_json(request_drift, graph)
    with pytest.raises(QwenFullModelSemanticError, match="dynamic request boundary"):
        _build(request_drift)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="dynamic request boundary",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=request_drift,
            capability_path=CAPABILITY,
            coverage_path=COVERAGE,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )

    graph = load_strict_json(GRAPH)
    graph["tensors"][1]["binding"]["checkpoint_lock_id"] = "0" * 64
    graph["graph_id"] = compute_graph_id(graph)
    checkpoint_drift = tmp_path / "checkpoint-drift.json"
    write_canonical_json(checkpoint_drift, graph)
    with pytest.raises(QwenFullModelSemanticError, match="checkpoint-lock identities"):
        _build(checkpoint_drift)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="checkpoint-binding coverage",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=checkpoint_drift,
            capability_path=CAPABILITY,
            coverage_path=COVERAGE,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )


@REAL
def test_semantic_paths_reject_unlowered_attributes_and_relocated_state_effects(
    tmp_path: Path,
) -> None:
    graph = load_strict_json(GRAPH)
    graph["operations"][0]["attributes"]["unreviewed_semantic"] = 1
    graph["graph_id"] = compute_graph_id(graph)
    attribute_drift = tmp_path / "attribute-drift.json"
    write_canonical_json(attribute_drift, graph)
    with pytest.raises(QwenFullModelSemanticError, match="source attributes differ"):
        _build(attribute_drift)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="embedding source operation contract differs",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=attribute_drift,
            capability_path=CAPABILITY,
            coverage_path=COVERAGE,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )

    graph = load_strict_json(GRAPH)
    read_committed = graph["operations"][8]["effects"].pop(0)
    graph["operations"][7]["effects"].append(read_committed)
    graph["graph_id"] = compute_graph_id(graph)
    effect_drift = tmp_path / "effect-drift.json"
    write_canonical_json(effect_drift, graph)
    with pytest.raises(QwenFullModelSemanticError, match="state effects differ"):
        _build(effect_drift)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="source state effects differ",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=effect_drift,
            capability_path=CAPABILITY,
            coverage_path=COVERAGE,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )


@REAL
def test_independent_checker_rejects_checkpoint_and_family_rebinding(
    tmp_path: Path,
) -> None:
    coverage = copy.deepcopy(load_strict_json(COVERAGE))
    coverage["checkpoint_lock_id"] = "0" * 64
    _reidentify(coverage, "report_id")
    forged_checkpoint = tmp_path / "forged-checkpoint-coverage.json"
    write_canonical_json(forged_checkpoint, coverage)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="coverage checkpoint identity differs",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            coverage_path=forged_checkpoint,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )

    coverage = copy.deepcopy(load_strict_json(COVERAGE))
    families = {item["kind"]: item for item in coverage["operator_families"]}
    (
        families["ADD"]["qualification_report_ids"],
        families["ATTENTION"]["qualification_report_ids"],
    ) = (
        families["ATTENTION"]["qualification_report_ids"],
        families["ADD"]["qualification_report_ids"],
    )
    _reidentify(coverage, "report_id")
    forged_family = tmp_path / "forged-family-coverage.json"
    write_canonical_json(forged_family, coverage)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="qualification binding differs",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            coverage_path=forged_family,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )


@REAL
def test_independent_checker_derives_loaded_capability_contract(
    tmp_path: Path,
) -> None:
    capability = load_strict_json(CAPABILITY)
    capability["vector_engine"]["max_attention_context_tokens"] = 8001
    _reidentify(capability, "capability_id")
    forged_capability = tmp_path / "drifted-capability.json"
    write_canonical_json(forged_capability, capability)
    with pytest.raises(
        QwenFullModelSemanticCheckError,
        match="development capability contract differs",
    ):
        check_qwen_full_model_semantics(
            model_graph_path=GRAPH,
            capability_path=forged_capability,
            coverage_path=COVERAGE,
            kernel_ir_path=KERNEL_IR,
            qkv_qualification_path=QKV,
            attention_qualification_path=ATTENTION,
            layer_qualification_path=LAYER,
            final_output_qualification_path=FINAL,
        )


@REAL
def test_complete_semantic_bundle_is_reproducible_and_nonoverwriting(
    tmp_path: Path,
) -> None:
    output = tmp_path / "semantic-bundle"
    command = [
        sys.executable,
        str(ROOT / "tools/build_qwen3_tensor_accelerator_full_semantics.py"),
        "--output",
        str(output),
    ]
    first = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert COVERAGE_ID in first.stdout
    assert KERNEL_IR_ID in first.stdout
    assert CHECK_ID in first.stdout
    for filename in (
        "coverage.json",
        "tensor_kernel_ir.json",
        "independent_check.json",
    ):
        assert (output / filename).read_bytes() == (RETAINED / filename).read_bytes()
    before = {child.name: child.read_bytes() for child in output.iterdir()}
    second = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert second.returncode != 0
    assert "will not be overwritten" in second.stderr
    assert {child.name: child.read_bytes() for child in output.iterdir()} == before


def test_independent_checker_does_not_import_semantic_builder() -> None:
    source = (
        ROOT / "compiler/tensor_accelerator/qwen_full_model_semantics_checking.py"
    ).read_text(encoding="utf-8")
    assert "qwen_full_model_semantics import" not in source
