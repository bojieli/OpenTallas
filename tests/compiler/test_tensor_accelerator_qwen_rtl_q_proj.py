from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import struct

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_qwen3_ta_rtl_q_proj_vectors as vector_builder
from tools import run_qwen3_ta_rtl_q_proj_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_q_proj_vectors.json"
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_q_proj_campaign.json"
VECTOR_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_q_proj_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_q_proj_campaign_v1.schema.json"
)
COMMAND_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
RMSNORM_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_rmsnorm_vectors.json"
)
FIRST_BLOCK_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_matmul_vectors.json"
)
KERNEL_IR = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/ir/tensor_kernel_ir.json"
)
PHYSICAL_PLAN = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/physical/physical_plan.json"
)
INTEGRATION = (
    Path.home()
    / "OpenTallas-ta-integration"
    / "results/tensor_accelerator/qwen3_full_model_physical"
)
COMMAND_PROGRAM = INTEGRATION / "program/commands.bin"
HBM_SHARD = (
    INTEGRATION
    / "memory/hbm/"
    "hbm.00001.656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37.bin"
)
EXECUTION_REPORT = (
    INTEGRATION.parent / "qwen3_full_model_execution_v1.json"
)
INDEPENDENT_REFERENCE = (
    INTEGRATION.parent / "qwen3_full_model_reference_v1.json"
)
EXPECTED_VECTOR_ID = "32dbdaa446fc4192f31a0a26394e04094e74c6459858d8a6b0135c11fc9e324b"
EXPECTED_CAMPAIGN_ID = (
    "af8c787f6c6995527ca0b75ab813b06f9ed05f9c18066ccf3e05ea1fa4d69603"
)
RETAINED_Q_RTL_SOURCE_SHA256 = {
    "rtl/ot_ta_dma_matmul_sequencer.sv": (
        "679efc3f15309137c8520ea619cb3555ad2adad2d19e62fcd4f530adb1662fc0"
    ),
    "rtl/ot_ta_matmul_bf16_sram_engine.sv": (
        "fece9a44fe9c433fabfd83c94057cf6dd07a87ae1b9a2e074c791d63680e29c6"
    ),
}


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


def test_q_proj_vectors_are_source_bound_and_complete_operation_scoped() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    commands = vectors["commands"]
    assert len(commands) == 2_048
    assert [item["expected_index"] for item in commands] == list(range(3, 2_051))
    assert [item["expected_fields"]["opcode"] for item in commands] == [
        1,
        0x10,
    ] * 1_024
    assert [item["last"] for item in commands] == [False] * 2_047 + [True]
    assert commands[31]["expected_index"] == 34
    assert commands[31]["last"] is False
    assert commands[-1]["expected_index"] == 2_050
    assert commands[-1]["last"] is True
    flags = [
        item["expected_fields"]["flags"]
        for item in commands
        if item["expected_fields"]["opcode"] == 0x10
    ]
    assert flags == [1, *([0] * 14), 2] * 64
    assert vectors["composition"]["graph_operation_id"] == "node.0002"
    assert vectors["composition"]["output_block_count"] == 64
    assert vectors["composition"]["weight_tile_count"] == 1_024
    assert vectors["composition"]["auxiliary_write_count"] == 4_096
    assert vectors["composition"]["auxiliary_saturation_count"] == 0
    assert vectors["claim_boundary"]["complete_q_projection_graph_operation"]
    assert not vectors["claim_boundary"]["complete_layer_execution"]
    assert not vectors["claim_boundary"]["ta_rtl_6_closed"]
    assert not vectors["claim_boundary"]["raw_weight_payload_retained"]
    assert "weight_payload_hex" not in vectors


def test_q_proj_vectors_cover_every_output_and_accumulator_tile() -> None:
    vectors = load_strict_json(VECTORS)
    assert len(vectors["blocks"]) == 64
    assert len(vectors["tiles"]) == 1_024
    assert len(vectors["expected_accumulator_tiles"]) == 1_024
    assert len(vectors["expected_final_accumulator_codes"]) == 4_096
    assert len(vectors["expected_output_codes"]) == 4_096
    accumulator_digest = hashlib.sha256()
    for tile, evidence in zip(
        vectors["expected_accumulator_tiles"], vectors["tiles"], strict=True
    ):
        payload = struct.pack("<64I", *tile)
        accumulator_digest.update(payload)
        assert _sha256(payload) == evidence["accumulator_payload_sha256"]
    assert (
        accumulator_digest.hexdigest()
        == vectors["composition"]["all_accumulator_tiles_sha256"]
    )
    final_accumulator_payload = struct.pack(
        "<4096I", *vectors["expected_final_accumulator_codes"]
    )
    output_payload = struct.pack("<4096H", *vectors["expected_output_codes"])
    assert (
        _sha256(final_accumulator_payload)
        == vectors["composition"]["accumulator_payload_sha256"]
    )
    assert (
        _sha256(output_payload)
        == vectors["composition"]["auxiliary_payload_sha256"]
        == vectors["source_execution"]["node_0002_output_sha256"]
    )
    for block in range(64):
        evidence = vectors["blocks"][block]
        assert evidence["output_block_index"] == block
        assert evidence["command_start"] == 3 + block * 32
        assert evidence["command_end"] == 34 + block * 32
        assert evidence["auxiliary_address"] == 6_291_456 + block * 128
        assert evidence["tile_evidence_start"] == block * 16
        output_start = block * 64
        block_output = struct.pack(
            "<64H", *vectors["expected_output_codes"][output_start : output_start + 64]
        )
        assert _sha256(block_output) == evidence["output_payload_sha256"]


def test_q_proj_preserves_retained_first_block_payloads_and_records() -> None:
    complete = load_strict_json(VECTORS)
    first = load_strict_json(FIRST_BLOCK_VECTORS)
    for current, retained in zip(complete["commands"][:32], first["commands"], strict=True):
        assert current["record_hex"] == retained["record_hex"]
        assert current["expected_fields"] == retained["expected_fields"]
        assert current["expected_index"] == retained["expected_index"]
    assert complete["commands"][31]["last"] is False
    assert first["commands"][31]["last"] is True
    assert (
        complete["expected_accumulator_tiles"][:16]
        == first["expected_accumulator_tiles"]
    )
    assert complete["expected_output_codes"][:64] == first["expected_output_codes"]
    assert (
        complete["blocks"][0]["accumulator_payload_sha256"]
        == first["composition"]["accumulator_payload_sha256"]
    )
    assert (
        complete["blocks"][0]["output_payload_sha256"]
        == first["composition"]["auxiliary_payload_sha256"]
    )


@pytest.mark.skipif(
    not all(
        path.is_file()
        for path in (
            COMMAND_PROGRAM,
            HBM_SHARD,
            EXECUTION_REPORT,
            INDEPENDENT_REFERENCE,
        )
    ),
    reason="complete immutable Qwen source artifacts are unavailable",
)
def test_q_proj_vector_builder_reproduces_retained_artifact() -> None:
    rebuilt = vector_builder.build(
        command_vectors_path=COMMAND_VECTORS,
        rmsnorm_vectors_path=RMSNORM_VECTORS,
        first_block_vectors_path=FIRST_BLOCK_VECTORS,
        kernel_ir_path=KERNEL_IR,
        physical_plan_path=PHYSICAL_PLAN,
        command_program_path=COMMAND_PROGRAM,
        hbm_shard_path=HBM_SHARD,
        execution_report_path=EXECUTION_REPORT,
        independent_reference_path=INDEPENDENT_REFERENCE,
    )
    assert canonical_json_bytes(rebuilt) == VECTORS.read_bytes()


def test_q_proj_schemas_reject_claim_and_completion_overreach() -> None:
    vectors = load_strict_json(VECTORS)
    vector_schema = load_strict_json(VECTOR_SCHEMA)
    false_layer = copy.deepcopy(vectors)
    false_layer["claim_boundary"]["complete_layer_execution"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_layer)
    false_gate = copy.deepcopy(vectors)
    false_gate["claim_boundary"]["ta_rtl_6_closed"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_gate)
    early_last = copy.deepcopy(vectors)
    early_last["commands"][31]["last"] = True
    early_last["commands"][-1]["last"] = False
    early_last["vector_set_id"] = _identity(early_last, "vector_set_id")
    Draft202012Validator(vector_schema).validate(early_last)
    # Unique terminal position is a sequence invariant rather than a JSON
    # shape rule.  The content identity changes, and the campaign runner rejects
    # anything except the retained identity before it launches a simulator.
    assert early_last["vector_set_id"] != EXPECTED_VECTOR_ID

    campaign = load_strict_json(CAMPAIGN)
    campaign_schema = load_strict_json(CAMPAIGN_SCHEMA)
    false_timing = copy.deepcopy(campaign)
    false_timing["claim_boundary"]["activity_derived_power_or_timing"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(campaign_schema).validate(false_timing)


def test_q_proj_campaign_is_schema_valid_and_boundary_scoped() -> None:
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
    assert all(case["observation"]["cycles"] > 97_000_000 for case in campaign["cases"])
    correlation = campaign["program_correlation"]
    assert correlation["command_count"] == 2_048
    assert correlation["dma_hbm_request_count"] == 524_288
    assert correlation["dma_sram_write_count"] == 2_097_152
    assert correlation["accumulator_read_count"] == 122_880
    assert correlation["matmul_input_read_count"] == 262_144
    assert correlation["matmul_weight_read_count"] == 16_777_216
    assert correlation["matmul_multiply_count"] == 16_777_216
    assert correlation["matmul_add_count"] == 16_777_216
    assert correlation["accumulator_write_count"] == 65_536
    assert correlation["auxiliary_write_count"] == 4_096
    assert correlation["auxiliary_saturation_count"] == 0
    assert correlation["early_terminal_fail_stop_cases"] == 1
    assert campaign["claim_boundary"]["complete_q_projection_graph_operation"]
    assert not campaign["claim_boundary"]["complete_layer_execution"]
    assert not campaign["claim_boundary"]["ta_rtl_6_closed"]


def test_q_proj_campaign_logs_and_sources_are_reproducible() -> None:
    campaign = load_strict_json(CAMPAIGN)
    marker = (
        "PASS: complete Qwen q_proj RTL commands=2048 blocks=64 tiles=1024 "
        "inputs=262144 weights=16777216 accumulators=65536 bf16=4096 faults=1"
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
            campaign_runner.PRIOR_CAMPAIGN_PATH,
            VECTORS,
        )
    }
    expected_sources = {
        name: _sha256_file(path) for name, path in sorted(static_paths.items())
    }
    # The Q campaign is immutable evidence for the source revision that ran it.
    # Later K/V generalization changes these two modules without rewriting the
    # retained Q artifact; the K/V campaign binds the current source hashes.
    expected_sources.update(RETAINED_Q_RTL_SOURCE_SHA256)
    generated = campaign_runner._program_files(load_strict_json(VECTORS))
    for name, payload in sorted(generated.items()):
        expected_sources[f"generated/{name}"] = _sha256(payload.encode("ascii"))
    expected_sources["generated/q_proj_weights.bin"] = (
        "27406586791294918cb04052d91f7d47c41aac1af56650c4b47f68ac00f1ff9b"
    )
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    not HBM_SHARD.is_file()
    or any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="complete HBM source and dual RTL simulators are required",
)
@pytest.mark.skip(reason="controlled 50-minute dual-simulator replay; run explicitly")
def test_retained_q_proj_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS, HBM_SHARD)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
