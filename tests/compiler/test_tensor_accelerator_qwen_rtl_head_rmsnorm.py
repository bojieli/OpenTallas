from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import struct

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_qwen3_ta_rtl_head_rmsnorm_vectors as vector_builder
from tools import run_qwen3_ta_rtl_head_rmsnorm_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = (
    ROOT
    / "testdata/compiler/tensor_accelerator/qwen3_rtl_head_rmsnorm_vectors.json"
)
CAMPAIGN = (
    ROOT / "results/tensor_accelerator/qwen3_rtl_head_rmsnorm_campaign.json"
)
VECTOR_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_head_rmsnorm_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_head_rmsnorm_campaign_v1.schema.json"
)
COMMAND_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
Q_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_q_proj_vectors.json"
)
KV_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_kv_proj_vectors.json"
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
    "hbm.00001.656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37.bin"
)
EXECUTION_REPORT = INTEGRATION.parent / "qwen3_full_model_execution_v1.json"
EXPECTED_VECTOR_ID = "9d6ff4c9ad10e03592d02ec3edebaf6bc341285fac8c69bc09b7daa7891ee791"
EXPECTED_CAMPAIGN_ID = (
    "d7153d61372e1470310e578d71fda690ccda2fe361a30386399a60d6f0b36c37"
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


def _u32(values: list[int]) -> bytes:
    return struct.pack(f"<{len(values)}I", *values)


def test_head_rmsnorm_vectors_are_source_bound_and_operation_complete() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    commands = vectors["commands"]
    assert [item["expected_index"] for item in commands] == list(range(3075, 3079))
    assert [item["expected_fields"]["opcode"] for item in commands] == [
        1,
        0x20,
        1,
        0x20,
    ]
    assert [item["expected_fields"]["kernel_index"] for item in commands] == [
        5,
        5,
        6,
        6,
    ]
    assert [item["last"] for item in commands] == [False, False, False, True]
    composition = vectors["composition"]
    assert composition["graph_operation_ids"] == ["node.0005", "node.0006"]
    assert composition["row_count"] == 40
    assert composition["input_read_count"] == 5_120
    assert composition["reduction_add_count"] == 5_080
    assert composition["reciprocal_square_root_count"] == 40
    assert composition["sram_output_write_count"] == 5_120
    assert vectors["claim_boundary"]["complete_q_head_rmsnorm_graph_operation"]
    assert vectors["claim_boundary"]["complete_k_head_rmsnorm_graph_operation"]
    assert not vectors["claim_boundary"]["complete_qkv_preparation"]
    assert not vectors["claim_boundary"]["complete_layer_execution"]
    assert not vectors["claim_boundary"]["ta_rtl_6_closed"]
    weights = bytes.fromhex(vectors["weight_payload_hex"])
    assert len(weights) == 512
    assert _sha256(weights) == vectors["weight_payload_sha256"]


def test_head_rmsnorm_vectors_cover_all_rows_and_intermediates() -> None:
    vectors = load_strict_json(VECTORS)
    operations = vectors["composition"]["operations"]
    expected = (
        (
            "q",
            32,
            "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c",
        ),
        (
            "k",
            8,
            "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66",
        ),
    )
    for operation, (prefix, rows, output_hash) in zip(
        operations, expected, strict=True
    ):
        assert len(vectors[f"{prefix}_input_codes"]) == rows * 128
        assert len(vectors[f"{prefix}_weight_codes"]) == 128
        assert len(vectors[f"{prefix}_normalized_codes"]) == rows * 128
        assert len(vectors[f"{prefix}_mean_square_codes"]) == rows
        assert len(vectors[f"{prefix}_inverse_rms_codes"]) == rows
        assert len(vectors[f"{prefix}_output_codes"]) == rows * 128
        assert (
            _sha256(_u16(vectors[f"{prefix}_input_codes"]))
            == operation["input_payload_sha256"]
        )
        assert (
            _sha256(_u16(vectors[f"{prefix}_weight_codes"]))
            == operation["weight_payload_sha256"]
        )
        assert (
            _sha256(_u16(vectors[f"{prefix}_normalized_codes"]))
            == operation["normalized_payload_sha256"]
        )
        assert (
            _sha256(_u32(vectors[f"{prefix}_mean_square_codes"]))
            == operation["mean_square_payload_sha256"]
        )
        assert (
            _sha256(_u32(vectors[f"{prefix}_inverse_rms_codes"]))
            == operation["inverse_rms_payload_sha256"]
        )
        assert (
            _sha256(_u16(vectors[f"{prefix}_output_codes"]))
            == operation["output_payload_sha256"]
            == output_hash
        )
        assert operation["normalized_saturation_count"] == 0
        assert operation["output_saturation_count"] == 0


@pytest.mark.skipif(
    not all(
        path.is_file()
        for path in (COMMAND_PROGRAM, HBM_SHARD, EXECUTION_REPORT, QUALIFICATION)
    ),
    reason="complete immutable Qwen source artifacts are unavailable",
)
def test_head_rmsnorm_builder_reproduces_retained_artifact() -> None:
    rebuilt = vector_builder.build(
        command_vectors_path=COMMAND_VECTORS,
        q_projection_vectors_path=Q_VECTORS,
        kv_projection_vectors_path=KV_VECTORS,
        kernel_ir_path=KERNEL_IR,
        physical_plan_path=PHYSICAL_PLAN,
        command_program_path=COMMAND_PROGRAM,
        hbm_shard_path=HBM_SHARD,
        execution_report_path=EXECUTION_REPORT,
        qkv_qualification_path=QUALIFICATION,
    )
    assert canonical_json_bytes(rebuilt) == VECTORS.read_bytes()


def test_head_rmsnorm_schemas_reject_claim_overreach() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    false_qkv = copy.deepcopy(vectors)
    false_qkv["claim_boundary"]["complete_qkv_preparation"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(false_qkv)
    false_layer = copy.deepcopy(vectors)
    false_layer["claim_boundary"]["complete_layer_execution"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(false_layer)
    early_last = copy.deepcopy(vectors)
    early_last["commands"][0]["last"] = True
    early_last["commands"][-1]["last"] = False
    early_last["vector_set_id"] = _identity(early_last, "vector_set_id")
    assert early_last["vector_set_id"] != EXPECTED_VECTOR_ID
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(early_last)

    campaign = load_strict_json(CAMPAIGN)
    campaign_schema = load_strict_json(CAMPAIGN_SCHEMA)
    false_timing = copy.deepcopy(campaign)
    false_timing["claim_boundary"]["activity_derived_power_or_timing"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(campaign_schema).validate(false_timing)


def test_head_rmsnorm_campaign_is_exact_and_boundary_scoped() -> None:
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
    assert correlation["command_count"] == 4
    assert correlation["dma_hbm_request_count"] == 8
    assert correlation["dma_sram_write_count"] == 32
    assert correlation["input_read_count"] == 5_120
    assert correlation["weight_read_count"] == 5_120
    assert correlation["output_write_count"] == 5_120
    assert correlation["reduction_add_count"] == 5_080
    assert correlation["reciprocal_square_root_count"] == 40
    assert correlation["normalized_saturation_count"] == 0
    assert correlation["output_saturation_count"] == 0
    assert correlation["early_terminal_fail_stop_cases"] == 1
    assert not campaign["claim_boundary"]["complete_qkv_preparation"]
    assert not campaign["claim_boundary"]["ta_rtl_6_closed"]


def test_head_rmsnorm_campaign_logs_and_sources_are_reproducible() -> None:
    campaign = load_strict_json(CAMPAIGN)
    marker = (
        "PASS: Qwen Q/K head RMSNorm RTL commands=4 rows=40 elements=5120 "
        "reductions=5080 rsqrt=40 outputs=5120 faults=1"
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
            campaign_runner.Q_CAMPAIGN_PATH,
            campaign_runner.KV_CAMPAIGN_PATH,
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
def test_retained_head_rmsnorm_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
