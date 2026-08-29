from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_qwen3_ta_rtl_dma_add_vectors as vector_builder
from tools import run_qwen3_ta_rtl_dma_add_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
DMA_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_vectors.json"
)
ADD_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_add_vectors.json"
)
VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_add_vectors.json"
)
CAMPAIGN = (
    ROOT / "results/tensor_accelerator/qwen3_rtl_dma_add_campaign.json"
)
VECTOR_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_add_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_add_campaign_v1.schema.json"
)
EXPECTED_VECTOR_ID = (
    "575ddc7ba55ddc76deec04f5747c661b7646baec13020ee29bb572d3f543cd3d"
)
EXPECTED_CAMPAIGN_ID = (
    "6df5e663467f84893f3a92eaf01f3dc398a58cedfde134d66ceff4791991516d"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def test_dma_add_vectors_are_exact_source_bound_and_claim_scoped() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    assert vectors["commands"][0]["expected_index"] == 1
    assert vectors["commands"][0]["last"] is False
    assert vectors["commands"][1]["expected_index"] == 5131
    assert vectors["commands"][1]["last"] is True
    assert vectors["composition"] == {
        "add_destination_address": 3145728,
        "add_element_count": 4096,
        "add_left_address": 1048576,
        "add_left_payload_sha256": (
            "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
        ),
        "add_right_address": 2097152,
        "add_right_payload_sha256": (
            "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
        ),
        "dma_destination_address": 2097152,
        "dma_payload_sha256": (
            "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
        ),
        "expected_output_payload_sha256": (
            "8901268db88a2d0e207c56b01aab6bcd0cdae0c2de2538e7d5a0120c595202ac"
        ),
        "expected_saturation_count": 0,
        "submitted_command_indices": [1, 5131],
    }
    assert vectors["claim_boundary"] == {
        "authentic_command_records": True,
        "behavioral_hbm_and_sram": True,
        "complete_layer_execution": False,
        "graph_valid_qwen_operation_sequence": False,
        "program_order_and_fail_stop": True,
        "qualified_hbm_phy": False,
        "qualified_sram_macro": False,
        "shared_sram_data_dependency": True,
        "ta_rtl_6_closed": False,
        "timing_or_performance": False,
    }


def test_vector_schema_rejects_graph_or_layer_overclaim() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    for field in ("graph_valid_qwen_operation_sequence", "complete_layer_execution"):
        forged = copy.deepcopy(vectors)
        forged["claim_boundary"][field] = True
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(forged)


def test_dma_add_vector_builder_reproduces_retained_payload() -> None:
    retained = load_strict_json(VECTORS)
    rebuilt = vector_builder.build(
        dma_vectors_path=DMA_VECTORS,
        add_vectors_path=ADD_VECTORS,
    )
    assert canonical_json_bytes(rebuilt) == canonical_json_bytes(retained)


def test_retained_dma_add_campaign_is_exact_and_dual_simulator_passing() -> None:
    report = load_strict_json(CAMPAIGN)
    schema = load_strict_json(CAMPAIGN_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
    assert CAMPAIGN.read_bytes() == canonical_json_bytes(report)
    assert report["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert report["campaign_id"] == _identity(report, "campaign_id")
    assert report["vector_set_id"] == EXPECTED_VECTOR_ID
    assert report["status"] == "pass"
    assert report["correlation"] == {
        "add_element_count": 4096,
        "add_output_payload_sha256": (
            "8901268db88a2d0e207c56b01aab6bcd0cdae0c2de2538e7d5a0120c595202ac"
        ),
        "add_sram_read_count": 8192,
        "add_sram_write_count": 4096,
        "command_indices": [1, 5131],
        "crc_fail_stop_cases": 1,
        "dma_hbm_bytes": 8192,
        "dma_hbm_request_count": 128,
        "dma_sram_write_count": 512,
        "hbm_response_fail_stop_cases": 1,
        "nonmonotonic_fail_stop_cases": 1,
        "shared_sram_address": 2097152,
    }
    marker = (
        "PASS: Qwen DMA+ADD RTL sequence commands=2 elements=4096 faults=3 "
        f"vector_set={EXPECTED_VECTOR_ID}"
    )
    assert [case["name"] for case in report["cases"]] == [
        "iverilog",
        "verilator",
    ]
    for case in report["cases"]:
        retained_log = case["compile_log"] + case["run_log"]
        assert case["status"] == "pass"
        assert case["compile_returncode"] == case["run_returncode"] == 0
        assert case["log_sha256"] == _sha256(retained_log.encode("utf-8"))
        assert marker in case["run_log"]
        assert "/tmp/" not in case["command"]
        assert str(ROOT) not in case["command"]


def test_dma_add_campaign_binds_all_static_and_generated_sources() -> None:
    vectors = load_strict_json(VECTORS)
    report = load_strict_json(CAMPAIGN)
    static = {
        str(path.relative_to(ROOT)): path for path in campaign_runner.RTL_PATHS
    }
    static.update(
        {
            str(CAMPAIGN_SCHEMA.relative_to(ROOT)): CAMPAIGN_SCHEMA,
            str(VECTOR_SCHEMA.relative_to(ROOT)): VECTOR_SCHEMA,
            "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_add_vectors.json": VECTORS,
            "tools/build_qwen3_ta_rtl_dma_add_vectors.py": ROOT
            / "tools/build_qwen3_ta_rtl_dma_add_vectors.py",
            "tools/run_qwen3_ta_rtl_dma_add_campaign.py": ROOT
            / "tools/run_qwen3_ta_rtl_dma_add_campaign.py",
        }
    )
    expected_sources = {name: _sha256_file(path) for name, path in static.items()}
    payload = bytes.fromhex(vectors["dma_payload_hex"])
    right_codes = [
        int.from_bytes(payload[index : index + 2], "little")
        for index in range(0, len(payload), 2)
    ]
    generated = {
        "generated/expected.hex": "".join(
            f"{value:04x}\n" for value in vectors["expected_codes"]
        ),
        "generated/left.hex": "".join(
            f"{value:04x}\n" for value in vectors["left_codes"]
        ),
        "generated/payload.hex": "".join(f"{value:02x}\n" for value in payload),
        "generated/qwen_ta_dma_add_harness.cpp": campaign_runner._harness(vectors),
        "generated/right.hex": "".join(
            f"{value:04x}\n" for value in right_codes
        ),
        "generated/tb_qwen_ta_dma_add.sv": campaign_runner._testbench(vectors),
    }
    expected_sources.update(
        {name: _sha256(value.encode("utf-8")) for name, value in generated.items()}
    )
    assert report["source_sha256"] == expected_sources


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the sequencer replay",
)
def test_retained_dma_add_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
