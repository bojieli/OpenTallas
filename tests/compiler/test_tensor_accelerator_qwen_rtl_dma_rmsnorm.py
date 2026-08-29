from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_qwen3_ta_rtl_dma_rmsnorm_vectors as vector_builder
from tools import run_qwen3_ta_rtl_dma_rmsnorm_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = (
    ROOT
    / "testdata/compiler/tensor_accelerator/"
    "qwen3_rtl_dma_rmsnorm_vectors.json"
)
CAMPAIGN = (
    ROOT / "results/tensor_accelerator/qwen3_rtl_dma_rmsnorm_campaign.json"
)
VECTOR_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_rmsnorm_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_rmsnorm_campaign_v1.schema.json"
)
COMMAND_VECTORS = (
    ROOT
    / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
DMA_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_vectors.json"
)
INPUT_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_add_vectors.json"
)
QUALIFICATION = (
    ROOT / "results/tensor_accelerator/qwen3_rmsnorm_qualification.json"
)
KERNEL_IR = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/ir/"
    "tensor_kernel_ir.json"
)
EXPECTED_VECTOR_ID = (
    "ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81"
)
EXPECTED_CAMPAIGN_ID = (
    "5fd24c36de35d32aa390a732040cd7888d474e0a06416de13ca740a7191441fd"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def test_dma_rmsnorm_vectors_are_exact_source_bound_and_graph_valid() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    assert [command["expected_index"] for command in vectors["commands"]] == [1, 2]
    assert [command["expected_fields"]["opcode"] for command in vectors["commands"]] == [
        1,
        0x20,
    ]
    assert vectors["commands"][0]["expected_fields"]["destination"] == vectors[
        "commands"
    ][1]["expected_fields"]["source1"]
    assert vectors["composition"] == {
        "dma_destination_address": 2097152,
        "expected_normalized_payload_sha256": (
            "bf4b81b7e711157b4e8c91bde7294d3be647844dbd7336d462201a246a1da28d"
        ),
        "expected_normalized_saturation_count": 0,
        "expected_output_payload_sha256": (
            "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
        ),
        "expected_output_saturation_count": 0,
        "graph_operation_id": "node.0001",
        "input_address": 1048576,
        "input_payload_sha256": (
            "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
        ),
        "inverse_rms_binary32_code": 0x420A0297,
        "mean_square_binary32_code": 0x3A5BF2CA,
        "output_address": 3145728,
        "rmsnorm_element_count": 4096,
        "submitted_command_indices": [1, 2],
        "weight_address": 2097152,
        "weight_payload_sha256": (
            "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
        ),
    }
    assert vectors["claim_boundary"] == {
        "authentic_command_records": True,
        "behavioral_hbm_and_sram": True,
        "complete_layer_execution": False,
        "complete_rmsnorm_graph_operation": True,
        "graph_valid_qwen_operation_sequence": True,
        "preloaded_hidden_input": True,
        "program_order_and_fail_stop": True,
        "qualified_hbm_phy": False,
        "qualified_sram_macro": False,
        "ta_rtl_6_closed": False,
        "timing_or_performance": False,
    }


def test_dma_rmsnorm_vector_builder_reproduces_retained_artifact() -> None:
    rebuilt = vector_builder.build(
        command_vectors_path=COMMAND_VECTORS,
        dma_vectors_path=DMA_VECTORS,
        input_vectors_path=INPUT_VECTORS,
        qualification_path=QUALIFICATION,
        kernel_ir_path=KERNEL_IR,
    )
    assert canonical_json_bytes(rebuilt) == VECTORS.read_bytes()


def test_dma_rmsnorm_schemas_reject_claim_and_payload_overreach() -> None:
    vectors = load_strict_json(VECTORS)
    vector_schema = load_strict_json(VECTOR_SCHEMA)
    false_layer_claim = copy.deepcopy(vectors)
    false_layer_claim["claim_boundary"]["complete_layer_execution"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_layer_claim)

    missing_payload_element = copy.deepcopy(vectors)
    missing_payload_element["expected_codes"].pop()
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(missing_payload_element)

    campaign = load_strict_json(CAMPAIGN)
    campaign_schema = load_strict_json(CAMPAIGN_SCHEMA)
    false_timing_claim = copy.deepcopy(campaign)
    false_timing_claim["claim_boundary"]["activity_derived_power_or_timing"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(campaign_schema).validate(false_timing_claim)


def test_dma_rmsnorm_campaign_is_schema_valid_and_boundary_scoped() -> None:
    vectors = load_strict_json(VECTORS)
    campaign = load_strict_json(CAMPAIGN)
    schema = load_strict_json(CAMPAIGN_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)
    assert CAMPAIGN.read_bytes() == canonical_json_bytes(campaign)
    assert campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert campaign["campaign_id"] == _identity(campaign, "campaign_id")
    assert campaign["vector_set_id"] == vectors["vector_set_id"]
    assert campaign["status"] == "pass"
    assert campaign["arithmetic_correlation"] == {
        "add_cases": 5000,
        "bf16_conversion_cases": 5000,
        "multiply_cases": 5000,
        "oracle": "independent_exact_scalar_fraction",
        "reciprocal_square_root_cases": 2000,
        "seed_hex": "5157454e33524d53",
    }
    assert campaign["program_correlation"]["command_indices"] == [1, 2]
    assert campaign["program_correlation"]["rmsnorm_sram_read_count"] == 8192
    assert campaign["program_correlation"]["rmsnorm_sram_write_count"] == 4096
    assert campaign["program_correlation"]["numeric_fail_stop_cases"] == 4
    assert campaign["program_correlation"][
        "write_suppression_numeric_fault_cases"
    ] == 4
    assert campaign["claim_boundary"] == {
        "activity_derived_power_or_timing": False,
        "authentic_command_records": True,
        "behavioral_hbm_and_sram": True,
        "complete_layer_execution": False,
        "complete_rmsnorm_graph_operation": True,
        "fp32_arithmetic_differential": True,
        "graph_valid_qwen_operation_sequence": True,
        "preloaded_hidden_input": True,
        "program_order_and_fail_stop": True,
        "qualified_hbm_phy": False,
        "qualified_sram_macro": False,
        "ta_rtl_6_closed": False,
    }


def test_dma_rmsnorm_campaign_logs_and_sources_are_reproducible() -> None:
    vectors = load_strict_json(VECTORS)
    campaign = load_strict_json(CAMPAIGN)
    arithmetic_marker = (
        "PASS: FP32 RTL differential add=5000 multiply=5000 bf16=5000 "
        "rsqrt=2000 seed=5157454e33524d53"
    )
    program_marker = (
        "PASS: Qwen DMA+RMSNorm RTL sequence commands=2 elements=4096 "
        f"faults=7 vector_set={EXPECTED_VECTOR_ID}"
    )
    for case in campaign["cases"]:
        retained_log = case["compile_log"] + case["run_log"]
        marker = arithmetic_marker if case["name"].startswith("arithmetic") else program_marker
        assert case["status"] == "pass"
        assert case["compile_returncode"] == case["run_returncode"] == 0
        assert case["log_sha256"] == _sha256(retained_log.encode("utf-8"))
        assert marker in case["run_log"]
        assert "/tmp/" not in case["command"]
        assert str(ROOT) not in case["command"]

    static_paths = {
        str(path.relative_to(ROOT)): path
        for path in (
            *campaign_runner.RTL_PATHS,
            campaign_runner.ARITHMETIC_TOP,
            campaign_runner.ARITHMETIC_TB,
            campaign_runner.ARITHMETIC_HARNESS,
            campaign_runner.PROGRAM_TB,
            campaign_runner.PROGRAM_HARNESS,
            campaign_runner.CAMPAIGN_SCHEMA_PATH,
            campaign_runner.VECTOR_SCHEMA_PATH,
            campaign_runner.VECTOR_BUILDER_PATH,
            Path(campaign_runner.__file__).resolve(),
            VECTORS,
        )
    }
    expected_sources = {
        name: _sha256_file(path) for name, path in sorted(static_paths.items())
    }
    generated = {
        **campaign_runner._arithmetic_files(),
        **campaign_runner._program_files(vectors),
    }
    for name, payload in sorted(generated.items()):
        expected_sources[f"generated/{name}"] = _sha256(payload.encode("ascii"))
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the RTL correlation replay",
)
def test_retained_dma_rmsnorm_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
