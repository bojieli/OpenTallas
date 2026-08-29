from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import struct

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from runtime.reference.tensor_accelerator_elementwise import (
    ElementwiseReferenceError,
    bf16_add_rne as reference_add,
)
from runtime.tensor_accelerator.elementwise import (
    ElementwiseKernelError,
    bf16_add_rne as optimized_add,
)
from tools import build_qwen3_ta_rtl_add_vectors as vector_builder
from tools import run_qwen3_ta_rtl_add_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)
DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
CHECKPOINT_LOCK = DEPLOYMENT / "source/checkpoint.lock.json"
ATTENTION = ROOT / "results/tensor_accelerator/qwen3_hbm_sram_attention_execution.json"
QUALIFICATION = ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json"
COMMAND_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
KERNEL_IR = DEPLOYMENT / "ir/tensor_kernel_ir.json"
PHYSICAL_PLAN = DEPLOYMENT / "physical/physical_plan.json"
VECTORS = ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_add_vectors.json"
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_add_campaign.json"
VECTOR_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_add_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_add_campaign_v1.schema.json"
)
EXPECTED_VECTOR_ID = (
    "e625aabe70b198319b76f8928d0b99ffe88d6d9e846eb8e0ddaeb3ba72eb7413"
)
EXPECTED_CAMPAIGN_ID = (
    "d7cb9dec3e1bc84e5a5c9f1775a84ecb54c11d85790f8f395e2cbfadf4f0d24c"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _payload(codes: list[int]) -> bytes:
    return struct.pack(f"<{len(codes)}H", *codes)


def test_authentic_add_vectors_are_schema_valid_exact_and_source_bound() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")

    command_vectors = load_strict_json(COMMAND_VECTORS)
    command = next(
        item for item in command_vectors["vectors"] if item["name"] == "add_bf16"
    )
    assert vectors["command"] == command
    assert vectors["command_vector_set_id"] == command_vectors["vector_set_id"]
    assert vectors["command_program_sha256"] == command_vectors[
        "command_program_sha256"
    ]
    assert vectors["operation"] == {
        "command_count": 1,
        "command_start": 5131,
        "inputs": ["hidden.0", "layer.0.attention_projected"],
        "kernel_index": 11,
        "operation_id": "node.0011",
        "output": "layer.0.post_attention",
    }
    assert vectors["claim_boundary"]["complete_add_command"] is True
    assert vectors["claim_boundary"]["complete_layer_execution"] is False
    assert vectors["claim_boundary"]["memory_macro_execution"] is False
    assert vectors["claim_boundary"]["ta_rtl_6_closed"] is False

    for role in ("left", "right", "expected"):
        assert len(vectors[role]["codes"]) == vectors["operand_count"] == 4096
        assert _sha256(_payload(vectors[role]["codes"])) == vectors[role][
            "payload_sha256"
        ]
    assert vectors["left"]["payload_sha256"] == (
        "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
    )
    assert vectors["right"]["payload_sha256"] == (
        "341ef1b0843309008fd558042d0c56733b82bca5cc0753a80424338a29defae5"
    )
    assert vectors["expected"]["payload_sha256"] == (
        "f872ce6f57ca36a30edf6abccfa2877bbb7234a905fe9e1417d99ea89ee79ec3"
    )
    fields = command["expected_fields"]
    assert (
        vectors["left"]["address"],
        vectors["right"]["address"],
        vectors["expected"]["address"],
    ) == (fields["source0"], fields["source1"], fields["destination"])

    reference = reference_add(
        [vectors["left"]["codes"]], [vectors["right"]["codes"]]
    )
    optimized = optimized_add(
        [vectors["left"]["codes"]], [vectors["right"]["codes"]]
    )
    expected = (tuple(vectors["expected"]["codes"]),)
    assert reference.values == expected
    assert tuple(tuple(int(item) for item in row) for row in optimized.values) == (
        expected
    )
    assert reference.output_saturated_element_count == 0
    assert optimized.output_saturated_element_count == 0


def test_directed_add_vectors_match_independent_error_and_rounding_contract() -> None:
    vectors = load_strict_json(VECTORS)
    directed = vectors["directed_vectors"]
    assert len(directed) == 20
    assert len({item["name"] for item in directed}) == len(directed)
    assert {item["expected_error"] for item in directed} == {0, 1, 2}
    assert sum(item["saturated"] for item in directed) == 2
    for vector in directed:
        left = [[vector["left"]]]
        right = [[vector["right"]]]
        if vector["expected_error"] == 0:
            reference = reference_add(left, right)
            optimized = optimized_add(left, right)
            assert reference.values == ((vector["expected"],),)
            assert int(optimized.values[0, 0]) == vector["expected"]
            assert (reference.output_saturated_element_count == 1) == vector[
                "saturated"
            ]
            assert (optimized.output_saturated_element_count == 1) == vector[
                "saturated"
            ]
        else:
            with pytest.raises(ElementwiseReferenceError):
                reference_add(left, right)
            with pytest.raises(ElementwiseKernelError):
                optimized_add(left, right)


def test_retained_add_campaign_is_schema_valid_reproducible_and_source_bound() -> None:
    vectors = load_strict_json(VECTORS)
    campaign = load_strict_json(CAMPAIGN)
    schema = load_strict_json(CAMPAIGN_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)
    assert CAMPAIGN.read_bytes() == canonical_json_bytes(campaign)
    assert campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert campaign["campaign_id"] == _identity(campaign, "campaign_id")
    assert campaign["vector_set_id"] == EXPECTED_VECTOR_ID
    assert campaign["status"] == "pass"
    assert campaign["correlation"] == {
        "add_input_sram_bytes_read": 16384,
        "add_output_sram_bytes_written": 8192,
        "command_index": 5131,
        "destination_address": 3145728,
        "directed_case_count": 20,
        "executor_fault_cases": 2,
        "expected_output_sha256": vectors["expected"]["payload_sha256"],
        "finite_encoding_checks": 130560,
        "operand_count": 4096,
        "residual_additions": 4096,
        "source0_address": 1048576,
        "source1_address": 2097152,
    }
    marker = (
        "PASS: Qwen ADD_BF16 RTL command elements=4096 directed=20 "
        f"exhaustive=130560 vector_set={EXPECTED_VECTOR_ID}"
    )
    for case in campaign["cases"]:
        retained_log = case["compile_log"] + case["run_log"]
        assert case["status"] == "pass"
        assert case["compile_returncode"] == case["run_returncode"] == 0
        assert case["log_sha256"] == _sha256(retained_log.encode("utf-8"))
        assert marker in case["run_log"]
        assert "PASS: Qwen ADD_BF16 RTL executor faults=2" in case["run_log"]
        assert "/tmp/" not in case["command"]
        assert str(ROOT) not in case["command"]

    static = {
        "rtl/ot_bf16_add_rne.sv": ROOT / "rtl/ot_bf16_add_rne.sv",
        "rtl/ot_ta_add_bf16_executor.sv": ROOT
        / "rtl/ot_ta_add_bf16_executor.sv",
        "rtl/ot_ta_command_decoder.sv": ROOT / "rtl/ot_ta_command_decoder.sv",
        "schemas/compiler/tensor_accelerator/qwen_rtl_add_campaign_v1.schema.json": CAMPAIGN_SCHEMA,
        "schemas/compiler/tensor_accelerator/qwen_rtl_add_vectors_v1.schema.json": VECTOR_SCHEMA,
        "testdata/compiler/tensor_accelerator/qwen3_rtl_add_vectors.json": VECTORS,
        "tools/build_qwen3_ta_rtl_add_vectors.py": ROOT
        / "tools/build_qwen3_ta_rtl_add_vectors.py",
        "tools/run_qwen3_ta_rtl_add_campaign.py": ROOT
        / "tools/run_qwen3_ta_rtl_add_campaign.py",
    }
    expected_sources = {name: _sha256_file(path) for name, path in static.items()}
    generated_text = {
        "generated/expected.hex": "".join(
            f"{value:04x}\n" for value in vectors["expected"]["codes"]
        ),
        "generated/left.hex": "".join(
            f"{value:04x}\n" for value in vectors["left"]["codes"]
        ),
        "generated/ot_ta_add_campaign_top.sv": campaign_runner._wrapper(),
        "generated/qwen_ta_add_harness.cpp": campaign_runner._harness(vectors),
        "generated/right.hex": "".join(
            f"{value:04x}\n" for value in vectors["right"]["codes"]
        ),
        "generated/tb_qwen_ta_add.sv": campaign_runner._testbench(vectors),
    }
    expected_sources.update(
        {name: _sha256(value.encode("utf-8")) for name, value in generated_text.items()}
    )
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    not SNAPSHOT.is_dir() or not CHECKPOINT_LOCK.is_file(),
    reason="pinned Qwen checkpoint is unavailable",
)
def test_authentic_add_vector_builder_reproduces_retained_payloads() -> None:
    retained = load_strict_json(VECTORS)
    rebuilt = vector_builder.build(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        attention_execution_path=ATTENTION,
        qualification_path=QUALIFICATION,
        command_vectors_path=COMMAND_VECTORS,
        kernel_ir_path=KERNEL_IR,
        physical_plan_path=PHYSICAL_PLAN,
    )
    assert canonical_json_bytes(rebuilt) == canonical_json_bytes(retained)


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the correlation replay",
)
def test_retained_add_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
