from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import struct

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_qwen3_ta_rtl_kv_proj_vectors as vector_builder
from tools import run_qwen3_ta_rtl_kv_proj_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_kv_proj_vectors.json"
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_kv_proj_campaign.json"
VECTOR_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_kv_proj_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_kv_proj_campaign_v1.schema.json"
)
COMMAND_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
RMSNORM_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_rmsnorm_vectors.json"
)
Q_PROJECTION_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_q_proj_vectors.json"
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
EXECUTION_REPORT = INTEGRATION.parent / "qwen3_full_model_execution_v1.json"
INDEPENDENT_REFERENCE = INTEGRATION.parent / "qwen3_full_model_reference_v1.json"
EXPECTED_VECTOR_ID = "ee711ae0b31985d0215b9f0c14233c3a2cb0cade3f79809bfc00493d369d5873"
EXPECTED_CAMPAIGN_ID = (
    "584e0f388d6295a3abc5d6d6f96e5f32500b493bf81d6a7b09d51b112a735894"
)
EXPECTED_OUTPUTS = (
    "dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403",
    "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
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


def test_kv_proj_vectors_are_source_bound_and_complete_operation_scoped() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")

    commands = vectors["commands"]
    assert len(commands) == 1_024
    assert [item["expected_index"] for item in commands] == list(range(2_051, 3_075))
    assert [item["expected_fields"]["opcode"] for item in commands] == [
        1,
        0x10,
    ] * 512
    assert [item["expected_fields"]["kernel_index"] for item in commands] == (
        [3] * 512 + [4] * 512
    )
    assert [item["last"] for item in commands] == [False] * 1_023 + [True]
    flags = [
        item["expected_fields"]["flags"]
        for item in commands
        if item["expected_fields"]["opcode"] == 0x10
    ]
    assert flags == [1, *([0] * 14), 2] * 32

    composition = vectors["composition"]
    assert composition["graph_operation_ids"] == ["node.0003", "node.0004"]
    assert composition["graph_command_count"] == 1_024
    assert composition["output_block_count"] == 32
    assert composition["weight_tile_count"] == 512
    assert composition["auxiliary_write_count"] == 2_048
    assert composition["auxiliary_saturation_count"] == 0
    assert [item["projection"] for item in composition["projections"]] == [
        "k_proj",
        "v_proj",
    ]
    assert [item["output_payload_sha256"] for item in composition["projections"]] == [
        *EXPECTED_OUTPUTS
    ]
    assert vectors["claim_boundary"]["complete_k_projection_graph_operation"]
    assert vectors["claim_boundary"]["complete_v_projection_graph_operation"]
    assert not vectors["claim_boundary"]["complete_qkv_preparation"]
    assert not vectors["claim_boundary"]["complete_layer_execution"]
    assert not vectors["claim_boundary"]["ta_rtl_6_closed"]
    assert not vectors["claim_boundary"]["raw_weight_payload_retained"]
    assert "weight_payload_hex" not in vectors


def test_kv_proj_vectors_cover_every_output_and_accumulator_tile() -> None:
    vectors = load_strict_json(VECTORS)
    assert len(vectors["blocks"]) == 32
    assert len(vectors["tiles"]) == 512
    assert len(vectors["expected_accumulator_tiles"]) == 512
    assert len(vectors["expected_final_accumulator_codes"]) == 2_048
    assert len(vectors["expected_output_codes"]) == 2_048

    accumulator_digest = hashlib.sha256()
    for tile, evidence in zip(
        vectors["expected_accumulator_tiles"], vectors["tiles"], strict=True
    ):
        payload = struct.pack("<64I", *tile)
        accumulator_digest.update(payload)
        assert _sha256(payload) == evidence["accumulator_payload_sha256"]
    composition = vectors["composition"]
    assert accumulator_digest.hexdigest() == composition["all_accumulator_tiles_sha256"]

    final_payload = struct.pack(
        "<2048I", *vectors["expected_final_accumulator_codes"]
    )
    output_payload = struct.pack("<2048H", *vectors["expected_output_codes"])
    assert _sha256(final_payload) == composition["accumulator_payload_sha256"]
    assert _sha256(output_payload) == composition["combined_output_payload_sha256"]

    for projection_index, expected_hash in enumerate(EXPECTED_OUTPUTS):
        start = projection_index * 1_024
        payload = struct.pack(
            "<1024H", *vectors["expected_output_codes"][start : start + 1_024]
        )
        assert _sha256(payload) == expected_hash
        assert (
            vectors["source_execution"][f"node_000{projection_index + 3}_output_sha256"]
            == expected_hash
        )

    for block_index, evidence in enumerate(vectors["blocks"]):
        projection_index, local_block = divmod(block_index, 16)
        expected_projection = "k_proj" if projection_index == 0 else "v_proj"
        expected_auxiliary = 7_340_032 if projection_index == 0 else 8_388_608
        output_start = block_index * 64
        block_payload = struct.pack(
            "<64H",
            *vectors["expected_output_codes"][output_start : output_start + 64],
        )
        assert evidence["global_output_block_index"] == block_index
        assert evidence["output_block_index"] == local_block
        assert evidence["projection"] == expected_projection
        assert evidence["command_start"] == 2_051 + block_index * 32
        assert evidence["command_end"] == 2_082 + block_index * 32
        assert evidence["auxiliary_address"] == expected_auxiliary + local_block * 128
        assert evidence["tile_evidence_start"] == block_index * 16
        assert evidence["output_saturation_count"] == 0
        assert _sha256(block_payload) == evidence["output_payload_sha256"]


def test_kv_proj_command_boundary_preserves_projection_order() -> None:
    vectors = load_strict_json(VECTORS)
    commands = vectors["commands"]
    assert commands[511]["expected_index"] == 2_562
    assert commands[511]["expected_fields"]["kernel_index"] == 3
    assert commands[511]["expected_fields"]["flags"] == 2
    assert commands[511]["last"] is False
    assert commands[512]["expected_index"] == 2_563
    assert commands[512]["expected_fields"]["kernel_index"] == 4
    assert commands[512]["expected_fields"]["opcode"] == 1
    assert commands[-1]["expected_fields"]["flags"] == 2
    assert commands[-1]["last"] is True


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
def test_kv_proj_vector_builder_reproduces_retained_artifact() -> None:
    rebuilt = vector_builder.build(
        command_vectors_path=COMMAND_VECTORS,
        rmsnorm_vectors_path=RMSNORM_VECTORS,
        q_projection_vectors_path=Q_PROJECTION_VECTORS,
        kernel_ir_path=KERNEL_IR,
        physical_plan_path=PHYSICAL_PLAN,
        command_program_path=COMMAND_PROGRAM,
        hbm_shard_path=HBM_SHARD,
        execution_report_path=EXECUTION_REPORT,
        independent_reference_path=INDEPENDENT_REFERENCE,
    )
    assert canonical_json_bytes(rebuilt) == VECTORS.read_bytes()


def test_kv_proj_schemas_reject_claim_and_completion_overreach() -> None:
    vectors = load_strict_json(VECTORS)
    vector_schema = load_strict_json(VECTOR_SCHEMA)
    false_qkv = copy.deepcopy(vectors)
    false_qkv["claim_boundary"]["complete_qkv_preparation"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_qkv)
    false_layer = copy.deepcopy(vectors)
    false_layer["claim_boundary"]["complete_layer_execution"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_layer)
    false_gate = copy.deepcopy(vectors)
    false_gate["claim_boundary"]["ta_rtl_6_closed"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_gate)

    early_last = copy.deepcopy(vectors)
    early_last["commands"][511]["last"] = True
    early_last["commands"][-1]["last"] = False
    early_last["vector_set_id"] = _identity(early_last, "vector_set_id")
    Draft202012Validator(vector_schema).validate(early_last)
    assert early_last["vector_set_id"] != EXPECTED_VECTOR_ID

    campaign = load_strict_json(CAMPAIGN)
    campaign_schema = load_strict_json(CAMPAIGN_SCHEMA)
    false_timing = copy.deepcopy(campaign)
    false_timing["claim_boundary"]["activity_derived_power_or_timing"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(campaign_schema).validate(false_timing)


def test_kv_proj_campaign_is_schema_valid_and_boundary_scoped() -> None:
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
    assert all(case["observation"]["cycles"] > 48_000_000 for case in campaign["cases"])

    correlation = campaign["program_correlation"]
    assert correlation["command_count"] == 1_024
    assert correlation["command_start"] == 2_051
    assert correlation["command_end"] == 3_074
    assert correlation["dma_hbm_request_count"] == 262_144
    assert correlation["dma_sram_write_count"] == 1_048_576
    assert correlation["accumulator_read_count"] == 61_440
    assert correlation["matmul_input_read_count"] == 131_072
    assert correlation["matmul_weight_read_count"] == 8_388_608
    assert correlation["matmul_multiply_count"] == 8_388_608
    assert correlation["matmul_add_count"] == 8_388_608
    assert correlation["accumulator_write_count"] == 32_768
    assert correlation["auxiliary_write_count"] == 2_048
    assert correlation["auxiliary_saturation_count"] == 0
    assert correlation["early_terminal_fail_stop_cases"] == 1
    assert campaign["claim_boundary"]["complete_k_projection_graph_operation"]
    assert campaign["claim_boundary"]["complete_v_projection_graph_operation"]
    assert not campaign["claim_boundary"]["complete_qkv_preparation"]
    assert not campaign["claim_boundary"]["complete_layer_execution"]
    assert not campaign["claim_boundary"]["ta_rtl_6_closed"]


def test_kv_proj_campaign_logs_and_sources_are_reproducible() -> None:
    campaign = load_strict_json(CAMPAIGN)
    marker = (
        "PASS: complete Qwen K/V projections RTL commands=1024 blocks=32 "
        "tiles=512 inputs=131072 weights=8388608 accumulators=32768 "
        "bf16=2048 faults=1"
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
    generated = campaign_runner._program_files(load_strict_json(VECTORS))
    for name, payload in sorted(generated.items()):
        expected_sources[f"generated/{name}"] = _sha256(payload.encode("ascii"))
    expected_sources["generated/kv_proj_weights.bin"] = (
        "a7d864dfda7e9659bcf297728eed39ce59aa85b09d40c1f63e638dc45fc8a10c"
    )
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    not HBM_SHARD.is_file()
    or any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="complete HBM source and dual RTL simulators are required",
)
@pytest.mark.skip(reason="controlled 30-minute dual-simulator replay; run explicitly")
def test_retained_kv_proj_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS, HBM_SHARD)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
