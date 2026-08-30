from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import struct

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_qwen3_ta_rtl_rope_vectors as vector_builder
from tools import run_qwen3_ta_rtl_rope_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_rope_vectors.json"
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_rope_campaign.json"
VECTOR_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_rope_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_rope_campaign_v1.schema.json"
)
HEAD_RMS_VECTORS = (
    ROOT
    / "testdata/compiler/tensor_accelerator/qwen3_rtl_head_rmsnorm_vectors.json"
)
KERNEL_IR = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/ir/tensor_kernel_ir.json"
)
PHYSICAL_PLAN = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/physical/physical_plan.json"
)
QUALIFICATION = ROOT / "results/tensor_accelerator/qwen3_qkv_qualification.json"
INTEGRATION = Path(
    "/home/ubuntu/OpenTallas-ta-integration/"
    "results/tensor_accelerator/qwen3_full_model_physical"
)
COMMAND_PROGRAM = INTEGRATION / "program/commands.bin"
HBM_SHARD = (
    INTEGRATION
    / "memory/hbm/"
    "hbm.00015.4cc984816239b7b9215743b405300e1ecfe26ac1bb62177f2874c20b3889b62b.bin"
)
EXECUTION_REPORT = INTEGRATION.parent / "qwen3_full_model_execution_v1.json"
EXECUTION_REQUEST = INTEGRATION / "request/execution_request.json"
EXPECTED_VECTOR_ID = "3a792b0dec8dd7277540841409accca66521f2f05f977c1cd6b6d9e5361f4f76"
EXPECTED_CAMPAIGN_ID = (
    "c9c8f6c90f6bdeaf52d1185157d0a235ab66307c47bf6941342b3bcb21968603"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _u16(values: list[int]) -> bytes:
    return struct.pack(f"<{len(values)}H", *values)


def test_rope_vectors_are_source_bound_and_operation_complete() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    commands = vectors["commands"]
    assert [item["expected_index"] for item in commands] == [3079, 3080]
    assert [item["expected_fields"]["opcode"] for item in commands] == [2, 0x21]
    assert [item["expected_fields"]["kernel_index"] for item in commands] == [
        7,
        7,
    ]
    assert [item["last"] for item in commands] == [False, True]
    assert commands[0]["expected_fields"] == {
        "auxiliary": 0,
        "destination": 13_631_488,
        "engine": 1,
        "flags": 0,
        "index": 3_079,
        "kernel_index": 7,
        "opcode": 2,
        "size0": 512,
        "size1": 512,
        "size2": 8_000,
        "size3": 4,
        "source0": 16_384_425_984,
        "source1": 4,
    }
    composition = vectors["composition"]
    assert composition["graph_operation_ids"] == ["node.0007"]
    assert composition["dma_index_read_count"] == 2
    assert composition["dma_hbm_request_count"] == 8
    assert composition["coefficient_read_count"] == 256
    assert composition["element_count"] == 5_120
    assert composition["multiplication_count"] == 10_240
    assert composition["addition_count"] == 5_120
    boundary = vectors["claim_boundary"]
    assert boundary["complete_rope_graph_operation"]
    assert boundary["all_qkv_preparation_graph_operations_individually_closed"]
    assert boundary["generic_position_selection"]
    assert not boundary["connected_qkv_preparation_program"]
    assert not boundary["complete_layer_execution"]
    assert not boundary["ta_rtl_6_closed"]
    shard = vectors["hbm_shard"]
    assert shard["size_bytes"] == 1 << 30
    assert shard["table_size_bytes"] == 8_000 * 512
    assert shard["table_offset_bytes"] == 278_298_624


def test_rope_vectors_cover_identity_and_nonidentity_positions_exactly() -> None:
    vectors = load_strict_json(VECTORS)
    q_input = vectors["q_input_codes"]
    k_input = vectors["k_input_codes"]
    assert len(q_input) == 4_096
    assert len(k_input) == 1_024
    assert _sha256(_u16(q_input)) == (
        "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c"
    )
    assert _sha256(_u16(k_input)) == (
        "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66"
    )
    zero, last = vectors["cases"]
    assert [zero["position"], last["position"]] == [0, 7_999]
    assert zero["selected_hbm_address"] == 16_384_425_984
    assert last["selected_hbm_address"] == 16_388_521_472
    assert zero["coefficient_codes"][:128] == [0x3F80] * 128
    assert zero["coefficient_codes"][128:] == [0] * 128
    assert zero["q_output_codes"] == q_input
    assert zero["k_output_codes"] == k_input
    assert last["q_output_codes"] != q_input
    assert last["k_output_codes"] != k_input
    expected = (
        (
            zero,
            "b262f6c135906b739518f2c53c49f425e115901a9e6469e024ee3921efd62e56",
            "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c",
            "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66",
        ),
        (
            last,
            "c3245faed3b4547a5bcb76623152d12a210c5229e59fc72fa41aacb6b16a1af7",
            "a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d",
            "ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858",
        ),
    )
    for case, coefficient_hash, q_hash, k_hash in expected:
        assert len(case["coefficient_codes"]) == 256
        assert len(case["q_output_codes"]) == 4_096
        assert len(case["k_output_codes"]) == 1_024
        assert _sha256(_u16(case["coefficient_codes"])) == coefficient_hash
        assert _sha256(_u16(case["q_output_codes"])) == q_hash
        assert _sha256(_u16(case["k_output_codes"])) == k_hash
        assert case["coefficient_payload_sha256"] == coefficient_hash
        assert case["q_output_payload_sha256"] == q_hash
        assert case["k_output_payload_sha256"] == k_hash
        assert case["multiplication_saturation_count"] == 0
        assert case["addition_saturation_count"] == 0


@pytest.mark.skipif(
    not all(
        path.is_file()
        for path in (
            COMMAND_PROGRAM,
            HBM_SHARD,
            EXECUTION_REPORT,
            EXECUTION_REQUEST,
            QUALIFICATION,
        )
    ),
    reason="complete immutable Qwen source artifacts are unavailable",
)
def test_rope_builder_reproduces_retained_artifact() -> None:
    rebuilt = vector_builder.build(
        head_rmsnorm_vectors_path=HEAD_RMS_VECTORS,
        kernel_ir_path=KERNEL_IR,
        physical_plan_path=PHYSICAL_PLAN,
        command_program_path=COMMAND_PROGRAM,
        hbm_shard_path=HBM_SHARD,
        execution_report_path=EXECUTION_REPORT,
        execution_request_path=EXECUTION_REQUEST,
        qkv_qualification_path=QUALIFICATION,
    )
    assert canonical_json_bytes(rebuilt) == VECTORS.read_bytes()


def test_rope_schemas_reject_claim_overreach_and_case_substitution() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    connected = copy.deepcopy(vectors)
    connected["claim_boundary"]["connected_qkv_preparation_program"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(connected)
    false_layer = copy.deepcopy(vectors)
    false_layer["claim_boundary"]["complete_layer_execution"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(false_layer)
    substituted = copy.deepcopy(vectors)
    substituted["cases"][1]["position"] = 1
    substituted["vector_set_id"] = _identity(substituted, "vector_set_id")
    assert substituted["vector_set_id"] != EXPECTED_VECTOR_ID
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(substituted)

    campaign = load_strict_json(CAMPAIGN)
    campaign_schema = load_strict_json(CAMPAIGN_SCHEMA)
    false_timing = copy.deepcopy(campaign)
    false_timing["claim_boundary"]["activity_derived_power_or_timing"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(campaign_schema).validate(false_timing)
    false_connection = copy.deepcopy(campaign)
    false_connection["claim_boundary"]["connected_qkv_preparation_program"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(campaign_schema).validate(false_connection)


def test_rope_campaign_is_exact_and_boundary_scoped() -> None:
    campaign = load_strict_json(CAMPAIGN)
    schema = load_strict_json(CAMPAIGN_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)
    assert CAMPAIGN.read_bytes() == canonical_json_bytes(campaign)
    assert campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert campaign["campaign_id"] == _identity(campaign, "campaign_id")
    assert campaign["vector_set_id"] == EXPECTED_VECTOR_ID
    assert campaign["status"] == "pass"
    assert [case["status"] for case in campaign["cases"]] == ["pass", "pass"]
    correlation = campaign["program_correlation"]
    assert correlation["command_count"] == 2
    assert correlation["verified_position_count"] == 2
    assert correlation["dma_index_read_count"] == 2
    assert correlation["dma_hbm_request_count"] == 8
    assert correlation["dma_hbm_response_count"] == 8
    assert correlation["dma_sram_write_count"] == 32
    assert correlation["coefficient_read_count"] == 256
    assert correlation["query_input_read_count"] == 4_096
    assert correlation["key_input_read_count"] == 1_024
    assert correlation["query_output_write_count"] == 4_096
    assert correlation["key_output_write_count"] == 1_024
    assert correlation["multiplication_count"] == 10_240
    assert correlation["addition_count"] == 5_120
    assert correlation["early_terminal_fail_stop_cases"] == 1
    assert correlation["index_range_fail_stop_cases"] == 1
    assert correlation["hbm_response_error_fail_stop_cases"] == 1
    boundary = campaign["claim_boundary"]
    assert boundary["complete_rope_graph_operation"]
    assert boundary["hbm_response_error_atomicity"]
    assert not boundary["connected_qkv_preparation_program"]
    assert not boundary["ta_rtl_6_closed"]


def test_rope_campaign_logs_and_sources_are_reproducible() -> None:
    campaign = load_strict_json(CAMPAIGN)
    marker = (
        "PASS: Qwen indexed RoPE RTL commands=2 positions=2 elements=10240 "
        "multiplications=20480 additions=10240 outputs=10240 faults=3"
    )
    for case in campaign["cases"]:
        retained_log = case["compile_log"] + case["run_log"]
        assert marker in case["run_log"]
        assert case["log_sha256"] == _sha256(retained_log.encode("utf-8"))
        assert "/tmp/" not in case["command"]
        assert str(ROOT) not in case["command"]

    static_paths = {
        str(path.relative_to(ROOT)): path
        for path in (
            *campaign_runner.RTL_PATHS,
            campaign_runner.PROGRAM_TB,
            campaign_runner.PROGRAM_HARNESS,
            campaign_runner.CAMPAIGN_SCHEMA_PATH,
            campaign_runner.VECTOR_SCHEMA_PATH,
            campaign_runner.VECTOR_BUILDER_PATH,
            Path(campaign_runner.__file__).resolve(),
            campaign_runner.HEAD_RMS_CAMPAIGN_PATH,
            campaign_runner.QUALIFICATION_PATH,
            VECTORS,
        )
    }
    expected_sources = {
        name: _sha256_file(path) for name, path in sorted(static_paths.items())
    }
    generated = campaign_runner._program_files(load_strict_json(VECTORS))
    for name, payload in sorted(generated.items()):
        expected_sources[f"generated/{name}"] = _sha256(payload.encode("ascii"))
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required",
)
@pytest.mark.skip(reason="controlled dual-simulator replay; run explicitly")
def test_retained_rope_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
