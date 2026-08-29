from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import struct

from jsonschema import Draft202012Validator, ValidationError
import numpy as np
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from runtime.reference.formats import binary32_add, binary32_multiply
from runtime.tensor_accelerator.bf16 import accumulate_bf16_tile_fp32
from tools import build_qwen3_ta_rtl_dma_matmul_vectors as vector_builder
from tools import run_qwen3_ta_rtl_dma_matmul_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_matmul_vectors.json"
)
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_dma_matmul_campaign.json"
VECTOR_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_matmul_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_matmul_campaign_v1.schema.json"
)
COMMAND_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
RMSNORM_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_rmsnorm_vectors.json"
)
KERNEL_IR = (
    ROOT / "results/tensor_accelerator/qwen3_full_model_physical/ir/"
    "tensor_kernel_ir.json"
)
PHYSICAL_PLAN = (
    ROOT / "results/tensor_accelerator/qwen3_full_model_physical/physical/"
    "physical_plan.json"
)
INTEGRATION = Path(
    "/home/ubuntu/OpenTallas-ta-integration/"
    "results/tensor_accelerator/qwen3_full_model_physical"
)
COMMAND_PROGRAM = INTEGRATION / "program/commands.bin"
HBM_SHARD = (
    INTEGRATION / "memory/hbm/"
    "hbm.00001.656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37.bin"
)
EXPECTED_VECTOR_ID = "ad2d94e71e7a24d98e92cff7a097d616e3c84e3540d033650119d81dbaaa1dc5"
EXPECTED_CAMPAIGN_ID = (
    "02733c4556fdeb9abac45735df80abd440bcbfc2edaf01998e3e0522c6588478"
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


def test_dma_matmul_vectors_are_exact_source_bound_and_boundary_scoped() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    assert [command["expected_index"] for command in vectors["commands"]] == [3, 4]
    assert [
        command["expected_fields"]["opcode"] for command in vectors["commands"]
    ] == [
        1,
        0x10,
    ]
    assert (
        vectors["commands"][0]["expected_fields"]["destination"]
        == vectors["commands"][1]["expected_fields"]["source1"]
    )
    assert vectors["composition"] == {
        "accumulator_address": 5_242_880,
        "accumulator_count": 64,
        "accumulator_payload_sha256": (
            "c82ca04197419306b6bbc545be882163e3ccccfb013773107541d3441dee8776"
        ),
        "auxiliary_address": 6_291_456,
        "auxiliary_write_count": 0,
        "dma_destination_address": 4_194_304,
        "graph_command_count": 2048,
        "graph_command_end": 2050,
        "graph_command_start": 3,
        "graph_operation_id": "node.0002",
        "input_address": 3_145_728,
        "input_element_count": 256,
        "input_payload_sha256": (
            "3e95a6a07ba5eff942a866e767b856aeb6d83def5b7f12d55983acb2afdb2551"
        ),
        "matmul_add_count": 16384,
        "matmul_multiply_count": 16384,
        "output_tile_index": 0,
        "parent_deployed_weight_payload_sha256": (
            "27406586791294918cb04052d91f7d47c41aac1af56650c4b47f68ac00f1ff9b"
        ),
        "parent_source_weight_payload_sha256": (
            "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8"
        ),
        "submitted_command_indices": [3, 4],
        "weight_address": 4_194_304,
        "weight_element_count": 16384,
        "weight_tile_index": 0,
        "weight_tile_payload_sha256": (
            "c9b6213f04cfd269acdb7124e76d3b9775965145d15defb663f02e21e34418bc"
        ),
    }
    assert vectors["claim_boundary"] == {
        "authentic_command_records": True,
        "behavioral_hbm_and_sram": True,
        "bf16_final_output_written": False,
        "complete_layer_execution": False,
        "complete_matmul_command": True,
        "complete_q_projection_graph_operation": False,
        "graph_valid_qwen_command_slice": True,
        "preloaded_attention_norm_slice": True,
        "program_order_and_fail_stop": True,
        "qualified_hbm_phy": False,
        "qualified_sram_macro": False,
        "raw_fp32_accumulator_tile_written": True,
        "ta_rtl_6_closed": False,
        "timing_or_performance": False,
    }

    input_payload = struct.pack("<256H", *vectors["input_codes"])
    weight_payload = bytes.fromhex(vectors["weight_tile_payload_hex"])
    accumulator_payload = struct.pack("<64I", *vectors["expected_accumulator_codes"])
    assert _sha256(input_payload) == vectors["composition"]["input_payload_sha256"]
    assert (
        _sha256(weight_payload) == vectors["composition"]["weight_tile_payload_sha256"]
    )
    assert (
        _sha256(accumulator_payload)
        == vectors["composition"]["accumulator_payload_sha256"]
    )


def test_dma_matmul_accumulators_match_optimized_and_exact_scalar_paths() -> None:
    vectors = load_strict_json(VECTORS)
    inputs = vectors["input_codes"]
    weights = np.frombuffer(
        bytes.fromhex(vectors["weight_tile_payload_hex"]), dtype="<u2"
    ).reshape(64, 256)
    optimized = (
        accumulate_bf16_tile_fp32(
            np.asarray(inputs, dtype=np.uint16).reshape(1, 256), weights
        )
        .values.reshape(-1)
        .astype(int)
        .tolist()
    )
    scalar: list[int] = []
    for row in weights.astype(int).tolist():
        accumulator = 0
        for left, right in zip(inputs, row, strict=True):
            accumulator = binary32_add(
                accumulator,
                binary32_multiply(left << 16, right << 16),
            )
        scalar.append(accumulator)
    assert scalar == optimized == vectors["expected_accumulator_codes"]


def test_dma_matmul_sources_identify_first_node_0002_tile_pair() -> None:
    vectors = load_strict_json(VECTORS)
    kernel_ir = load_strict_json(KERNEL_IR)
    physical_plan = load_strict_json(PHYSICAL_PLAN)
    kernel = kernel_ir["kernels"][2]
    assert kernel["source_operation_id"] == "node.0002"
    assert kernel["numeric_contract"] == vectors["numeric_contract"]
    operation_range = next(
        item
        for item in physical_plan["command_program"]["kernel_command_ranges"]
        if item["kernel_index"] == 2
    )
    assert operation_range == {
        "command_count": 2048,
        "command_start": 3,
        "kernel_index": 2,
        "operation_id": "node.0002",
    }
    tensor = next(
        item
        for item in physical_plan["hbm"]["weights"]
        if item["tensor_id"] == "model.layers.0.self_attn.q_proj.weight"
    )
    assert tensor["address"] == 1_244_692_480
    assert tensor["access_unit_bytes"] == 32_768
    assert tensor["layout_details"]["tile_count"] == 1024
    assert (
        tensor["deployed_payload_sha256"]
        == vectors["composition"]["parent_deployed_weight_payload_sha256"]
    )


@pytest.mark.skipif(
    not COMMAND_PROGRAM.is_file() or not HBM_SHARD.is_file(),
    reason="complete immutable Qwen physical artifacts are unavailable",
)
def test_dma_matmul_vector_builder_reproduces_retained_artifact() -> None:
    rebuilt = vector_builder.build(
        command_vectors_path=COMMAND_VECTORS,
        rmsnorm_vectors_path=RMSNORM_VECTORS,
        kernel_ir_path=KERNEL_IR,
        physical_plan_path=PHYSICAL_PLAN,
        command_program_path=COMMAND_PROGRAM,
        hbm_shard_path=HBM_SHARD,
    )
    assert canonical_json_bytes(rebuilt) == VECTORS.read_bytes()


def test_dma_matmul_schemas_reject_claim_and_payload_overreach() -> None:
    vectors = load_strict_json(VECTORS)
    vector_schema = load_strict_json(VECTOR_SCHEMA)
    false_graph_claim = copy.deepcopy(vectors)
    false_graph_claim["claim_boundary"]["complete_q_projection_graph_operation"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_graph_claim)

    false_final_write = copy.deepcopy(vectors)
    false_final_write["claim_boundary"]["bf16_final_output_written"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_final_write)

    missing_accumulator = copy.deepcopy(vectors)
    missing_accumulator["expected_accumulator_codes"].pop()
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(missing_accumulator)

    campaign = load_strict_json(CAMPAIGN)
    campaign_schema = load_strict_json(CAMPAIGN_SCHEMA)
    false_timing_claim = copy.deepcopy(campaign)
    false_timing_claim["claim_boundary"]["activity_derived_power_or_timing"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(campaign_schema).validate(false_timing_claim)


def test_dma_matmul_campaign_is_schema_valid_and_boundary_scoped() -> None:
    campaign = load_strict_json(CAMPAIGN)
    schema = load_strict_json(CAMPAIGN_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)
    assert CAMPAIGN.read_bytes() == canonical_json_bytes(campaign)
    assert campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert campaign["campaign_id"] == _identity(campaign, "campaign_id")
    assert campaign["vector_set_id"] == EXPECTED_VECTOR_ID
    assert campaign["status"] == "pass"
    assert campaign["arithmetic_correlation"] == {
        "finite_success_cases": 19367,
        "nonfinite_rejection_cases": 597,
        "oracle": "independent_exact_scalar_fraction",
        "overflow_rejection_cases": 36,
        "seed_hex": "5157454e334d4154",
        "signed_add_cases": 20000,
    }
    assert campaign["program_correlation"]["command_indices"] == [3, 4]
    assert campaign["program_correlation"]["dma_hbm_request_count"] == 512
    assert campaign["program_correlation"]["matmul_input_read_count"] == 256
    assert campaign["program_correlation"]["matmul_weight_read_count"] == 16384
    assert campaign["program_correlation"]["matmul_multiply_count"] == 16384
    assert campaign["program_correlation"]["matmul_add_count"] == 16384
    assert campaign["program_correlation"]["accumulator_write_count"] == 64
    assert campaign["program_correlation"]["auxiliary_write_count"] == 0
    assert campaign["program_correlation"]["numeric_fail_stop_cases"] == 4
    assert campaign["program_correlation"]["write_suppression_numeric_fault_cases"] == 4


def test_dma_matmul_campaign_logs_and_sources_are_reproducible() -> None:
    campaign = load_strict_json(CAMPAIGN)
    arithmetic_marker = (
        "PASS: FP32 signed-add RTL differential cases=20000 seed=5157454e334d4154"
    )
    program_marker = (
        "PASS: Qwen DMA+MATMUL RTL slice commands=2 inputs=256 "
        "weights=16384 outputs=64 faults=7 "
        f"vector_set={EXPECTED_VECTOR_ID}"
    )
    for case in campaign["cases"]:
        retained_log = case["compile_log"] + case["run_log"]
        marker = (
            arithmetic_marker
            if case["name"].startswith("signed_add")
            else program_marker
        )
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
        **campaign_runner._signed_add_files(),
        **campaign_runner._program_files(load_strict_json(VECTORS)),
    }
    for name, payload in sorted(generated.items()):
        expected_sources[f"generated/{name}"] = _sha256(payload.encode("ascii"))
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the RTL correlation replay",
)
def test_retained_dma_matmul_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
