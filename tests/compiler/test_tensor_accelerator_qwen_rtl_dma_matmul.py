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
from runtime.reference.formats import (
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
)
from runtime.tensor_accelerator.bf16 import (
    accumulate_bf16_tile_fp32,
    finalize_bf16_accumulator,
)
from tools import build_qwen3_ta_rtl_dma_matmul_vectors as vector_builder
from tools import run_qwen3_ta_rtl_dma_matmul_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_matmul_vectors.json"
)
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_dma_matmul_campaign.json"
VECTOR_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_matmul_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_matmul_campaign_v1.schema.json"
)
COMMAND_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
RMSNORM_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_rmsnorm_vectors.json"
)
KERNEL_IR = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/ir/tensor_kernel_ir.json"
)
PHYSICAL_PLAN = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/physical/physical_plan.json"
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
EXPECTED_VECTOR_ID = "4fe481b232112fe5b494cab1ca4445159b91a512a524471bee18267fe5525129"
EXPECTED_CAMPAIGN_ID = (
    "c0dba5230a77daa1eecab33aa43960b2e41f198cd453e6ef139653ef1a14a298"
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
    assert [command["expected_index"] for command in vectors["commands"]] == list(
        range(3, 35)
    )
    assert [
        command["expected_fields"]["opcode"] for command in vectors["commands"]
    ] == [1, 0x10] * 16
    assert [
        command["expected_fields"]["flags"]
        for command in vectors["commands"]
        if command["expected_fields"]["opcode"] == 0x10
    ] == [1, *([0] * 14), 2]
    assert [command["last"] for command in vectors["commands"]] == [
        *([False] * 31),
        True,
    ]
    assert all(
        vectors["commands"][offset]["expected_fields"]["destination"]
        == vectors["commands"][offset + 1]["expected_fields"]["source1"]
        for offset in range(0, 32, 2)
    )
    assert vectors["composition"] == {
        "accumulator_address": 5_242_880,
        "accumulator_count": 64,
        "accumulator_payload_sha256": (
            "9ca6beb437222939a843d9a12d2fc93440de926cf7e0a5b3af40ce2c63a28f49"
        ),
        "auxiliary_address": 6_291_456,
        "auxiliary_payload_sha256": (
            "c485049ad6aa3e7c6e641defacfabee7de0c159cd8d45a65e74409493d17eb5e"
        ),
        "auxiliary_saturation_count": 0,
        "auxiliary_write_count": 64,
        "dma_destination_address": 4_194_304,
        "graph_command_count": 2048,
        "graph_command_end": 2050,
        "graph_command_start": 3,
        "graph_operation_id": "node.0002",
        "graph_output_block_count": 64,
        "input_address": 3_145_728,
        "input_element_count": 4096,
        "input_payload_sha256": (
            "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
        ),
        "k_tile_count": 16,
        "matmul_add_count": 262_144,
        "matmul_multiply_count": 262_144,
        "output_block_count": 1,
        "output_tile_index": 0,
        "parent_deployed_weight_payload_sha256": (
            "27406586791294918cb04052d91f7d47c41aac1af56650c4b47f68ac00f1ff9b"
        ),
        "parent_source_weight_payload_sha256": (
            "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8"
        ),
        "submitted_command_indices": list(range(3, 35)),
        "weight_address": 4_194_304,
        "weight_element_count": 262_144,
        "weight_payload_sha256": (
            "87bb7ad73d67888d91510a5443e2672172fcfccf52a5cd8b31acbe1f80c6be03"
        ),
        "weight_tile_count": 16,
    }
    assert vectors["claim_boundary"] == {
        "authentic_command_records": True,
        "behavioral_hbm_and_sram": True,
        "bf16_final_output_written": True,
        "complete_first_output_block": True,
        "complete_layer_execution": False,
        "complete_matmul_commands": True,
        "complete_q_projection_graph_operation": False,
        "graph_valid_qwen_command_slice": True,
        "preloaded_attention_norm_row": True,
        "program_order_and_fail_stop": True,
        "qualified_hbm_phy": False,
        "qualified_sram_macro": False,
        "raw_fp32_accumulator_tile_written": True,
        "ta_rtl_6_closed": False,
        "timing_or_performance": False,
    }


def test_dma_matmul_retained_payload_hashes_cover_every_k_tile() -> None:
    vectors = load_strict_json(VECTORS)
    input_payload = struct.pack("<4096H", *vectors["input_codes"])
    weight_payload = bytes.fromhex(vectors["weight_payload_hex"])
    accumulator_payload = struct.pack("<64I", *vectors["expected_accumulator_codes"])
    output_payload = struct.pack("<64H", *vectors["expected_output_codes"])
    assert _sha256(input_payload) == vectors["composition"]["input_payload_sha256"]
    assert _sha256(weight_payload) == vectors["composition"]["weight_payload_sha256"]
    assert (
        _sha256(accumulator_payload)
        == vectors["composition"]["accumulator_payload_sha256"]
    )
    assert _sha256(output_payload) == vectors["composition"]["auxiliary_payload_sha256"]
    for tile, evidence in enumerate(vectors["tiles"]):
        start = tile * 32_768
        accumulator = struct.pack("<64I", *vectors["expected_accumulator_tiles"][tile])
        assert (
            _sha256(weight_payload[start : start + 32_768])
            == evidence["weight_payload_sha256"]
        )
        assert _sha256(accumulator) == evidence["accumulator_payload_sha256"]


def test_dma_matmul_full_k_matches_optimized_and_exact_scalar_paths() -> None:
    vectors = load_strict_json(VECTORS)
    inputs = vectors["input_codes"]
    payload = bytes.fromhex(vectors["weight_payload_hex"])
    optimized: np.ndarray[tuple[int, int], np.dtype[np.uint32]] | None = None
    scalar = [0] * 64
    for tile in range(16):
        input_tile = np.asarray(
            inputs[tile * 256 : (tile + 1) * 256], dtype=np.uint16
        ).reshape(1, 256)
        weights = np.frombuffer(
            payload[tile * 32_768 : (tile + 1) * 32_768], dtype="<u2"
        ).reshape(64, 256)
        optimized = accumulate_bf16_tile_fp32(input_tile, weights, optimized).values
        for output, row in enumerate(weights.astype(int).tolist()):
            accumulator = scalar[output]
            for left, right in zip(
                input_tile.reshape(-1).astype(int).tolist(), row, strict=True
            ):
                accumulator = binary32_add(
                    accumulator,
                    binary32_multiply(left << 16, right << 16),
                )
            scalar[output] = accumulator
        assert scalar == vectors["expected_accumulator_tiles"][tile]
        assert optimized.reshape(-1).astype(int).tolist() == scalar
    assert optimized is not None
    finalized = finalize_bf16_accumulator(optimized)
    exact_outputs = [binary32_bits_to_bf16_rne(code) for code in scalar]
    assert [value.code for value in exact_outputs] == vectors["expected_output_codes"]
    assert (
        finalized.values.reshape(-1).astype(int).tolist()
        == vectors["expected_output_codes"]
    )
    assert sum(int(value.saturated) for value in exact_outputs) == 0
    assert finalized.output_saturated_element_count == 0


def test_dma_matmul_sources_identify_one_of_64_node_0002_output_blocks() -> None:
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
    assert tensor["layout_details"]["k_tiles"] == 16
    assert tensor["layout_details"]["n_tiles"] == 64
    assert vectors["composition"]["k_tile_count"] == 16
    assert vectors["composition"]["output_block_count"] == 1
    assert vectors["composition"]["graph_output_block_count"] == 64


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

    false_layer_claim = copy.deepcopy(vectors)
    false_layer_claim["claim_boundary"]["complete_layer_execution"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_layer_claim)

    false_block_count = copy.deepcopy(vectors)
    false_block_count["composition"]["output_block_count"] = 64
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(false_block_count)

    missing_output = copy.deepcopy(vectors)
    missing_output["expected_output_codes"].pop()
    with pytest.raises(ValidationError):
        Draft202012Validator(vector_schema).validate(missing_output)

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
        "finite_success_cases": 19_367,
        "nonfinite_rejection_cases": 597,
        "oracle": "independent_exact_scalar_fraction",
        "overflow_rejection_cases": 36,
        "seed_hex": "5157454e334d4154",
        "signed_add_cases": 20_000,
    }
    correlation = campaign["program_correlation"]
    assert correlation["command_indices"] == list(range(3, 35))
    assert correlation["dma_hbm_request_count"] == 8192
    assert correlation["accumulator_read_count"] == 1920
    assert correlation["matmul_input_read_count"] == 4096
    assert correlation["matmul_weight_read_count"] == 262_144
    assert correlation["matmul_multiply_count"] == 262_144
    assert correlation["matmul_add_count"] == 262_144
    assert correlation["accumulator_write_count"] == 1024
    assert correlation["auxiliary_write_count"] == 64
    assert correlation["auxiliary_saturation_count"] == 0
    assert correlation["numeric_fail_stop_cases"] == 5
    assert correlation["write_suppression_numeric_fault_cases"] == 5


def test_dma_matmul_campaign_logs_and_sources_are_reproducible() -> None:
    campaign = load_strict_json(CAMPAIGN)
    arithmetic_marker = (
        "PASS: FP32 signed-add RTL differential cases=20000 seed=5157454e334d4154"
    )
    program_marker = (
        "PASS: Qwen DMA+MATMUL RTL slice commands=32 k_tiles=16 "
        "inputs=4096 weights=262144 accumulators=1024 bf16=64 faults=8 "
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
    current_sources = {
        name: _sha256_file(path) for name, path in sorted(static_paths.items())
    }
    generated = {
        **campaign_runner._signed_add_files(),
        **campaign_runner._program_files(load_strict_json(VECTORS)),
    }
    for name, payload in sorted(generated.items()):
        current_sources[f"generated/{name}"] = _sha256(payload.encode("ascii"))
    historical_sources = dict(current_sources)
    historical_sources["rtl/ot_ta_dma_matmul_sequencer.sv"] = (
        "c61dd19d8fbab32574ff79ef4c22a7761e3268c29b7905c7de4a36e22bd2ff0d"
    )
    historical_sources["rtl/ot_ta_matmul_bf16_sram_engine.sv"] = (
        "3a77bb1b155ac2ca605e03132ac3833f615d688ad96ff8fb7d22af75ecd97b99"
    )
    assert campaign["source_sha256"] == historical_sources
    q_campaign = load_strict_json(
        ROOT / "results/tensor_accelerator/qwen3_rtl_q_proj_campaign.json"
    )
    kv_campaign = load_strict_json(
        ROOT / "results/tensor_accelerator/qwen3_rtl_kv_proj_campaign.json"
    )
    for source in (
        "rtl/ot_ta_dma_matmul_sequencer.sv",
        "rtl/ot_ta_matmul_bf16_sram_engine.sv",
    ):
        assert current_sources[source] == kv_campaign["source_sha256"][source]
        assert current_sources[source] != q_campaign["source_sha256"][source]


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the RTL correlation replay",
)
def test_generalized_engine_preserves_retained_first_block_campaign() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert replayed["campaign_id"] == (
        "f09a219aa0f495bcca848186b288fb773d1866336cb2ff7f1bb83cc546e15253"
    )
    assert replayed["status"] == "pass"
    retained_functional = {
        key: value
        for key, value in retained.items()
        if key not in {"campaign_id", "source_sha256"}
    }
    replayed_functional = {
        key: value
        for key, value in replayed.items()
        if key not in {"campaign_id", "source_sha256"}
    }
    assert canonical_json_bytes(replayed_functional) == canonical_json_bytes(
        retained_functional
    )
    assert set(replayed["source_sha256"]) == set(retained["source_sha256"])
    assert {
        key
        for key in replayed["source_sha256"]
        if replayed["source_sha256"][key] != retained["source_sha256"][key]
    } == {
        "rtl/ot_ta_dma_matmul_sequencer.sv",
        "rtl/ot_ta_matmul_bf16_sram_engine.sv",
    }
