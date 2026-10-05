from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import run_qwen3_ta_rtl_add_sram_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_add_vectors.json"
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_add_sram_campaign.json"
SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_add_sram_campaign_v1.schema.json"
)
VECTOR_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_add_vectors_v1.schema.json"
)
EXPECTED_VECTOR_ID = (
    "e625aabe70b198319b76f8928d0b99ffe88d6d9e846eb8e0ddaeb3ba72eb7413"
)
EXPECTED_CAMPAIGN_ID = (
    "7e96454558f15a9c992d5f04a3478d20b656107fdc576e2e4f3b22f4dc8c7b59"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def test_sram_campaign_is_schema_valid_exact_and_boundary_scoped() -> None:
    vectors = load_strict_json(VECTORS)
    campaign = load_strict_json(CAMPAIGN)
    schema = load_strict_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)
    assert CAMPAIGN.read_bytes() == canonical_json_bytes(campaign)
    assert campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert campaign["campaign_id"] == _identity(campaign, "campaign_id")
    assert campaign["vector_set_id"] == vectors["vector_set_id"]
    assert campaign["vector_set_id"] == EXPECTED_VECTOR_ID
    assert campaign["status"] == "pass"
    assert campaign["claim_boundary"] == {
        "behavioral_sram_model": True,
        "complete_add_command": True,
        "complete_layer_execution": False,
        "memory_request_writeback_control": True,
        "qualified_sram_macro": False,
        "ta_rtl_6_closed": False,
        "timing_or_performance": False,
    }
    assert campaign["correlation"] == {
        "add_input_sram_bytes_read": 16384,
        "add_output_sram_bytes_written": 8192,
        "command_index": 5131,
        "destination_address": 3145728,
        "expected_output_sha256": vectors["expected"]["payload_sha256"],
        "fault_write_suppression_cases": 2,
        "maximum_outstanding_reads": 1,
        "operand_count": 4096,
        "residual_additions": 4096,
        "source0_address": 1048576,
        "source1_address": 2097152,
        "sram_read_transactions": 8192,
        "sram_write_transactions": 4096,
    }


def test_sram_campaign_logs_and_sources_are_complete_and_reproducible() -> None:
    vectors = load_strict_json(VECTORS)
    campaign = load_strict_json(CAMPAIGN)
    marker = (
        "PASS: Qwen ADD_BF16 SRAM RTL command elements=4096 reads=8192 "
        f"writes=4096 faults=2 vector_set={EXPECTED_VECTOR_ID}"
    )
    for case in campaign["cases"]:
        retained_log = case["compile_log"] + case["run_log"]
        assert case["status"] == "pass"
        assert case["compile_returncode"] == case["run_returncode"] == 0
        assert case["log_sha256"] == _sha256(retained_log.encode("utf-8"))
        assert marker in case["run_log"]
        assert "/tmp/" not in case["command"]
        assert str(ROOT) not in case["command"]

    static = {
        "rtl/ot_bf16_add_rne.sv": ROOT / "rtl/ot_bf16_add_rne.sv",
        "rtl/ot_ta_add_bf16_executor.sv": ROOT
        / "rtl/ot_ta_add_bf16_executor.sv",
        "rtl/ot_ta_add_bf16_sram_engine.sv": ROOT
        / "rtl/ot_ta_add_bf16_sram_engine.sv",
        "rtl/ot_ta_command_decoder.sv": ROOT / "rtl/ot_ta_command_decoder.sv",
        "schemas/compiler/tensor_accelerator/qwen_rtl_add_sram_campaign_v1.schema.json": SCHEMA,
        "schemas/compiler/tensor_accelerator/qwen_rtl_add_vectors_v1.schema.json": VECTOR_SCHEMA,
        "testdata/compiler/tensor_accelerator/qwen3_rtl_add_vectors.json": VECTORS,
        "tools/run_qwen3_ta_rtl_add_campaign.py": ROOT
        / "tools/run_qwen3_ta_rtl_add_campaign.py",
        "tools/run_qwen3_ta_rtl_add_sram_campaign.py": ROOT
        / "tools/run_qwen3_ta_rtl_add_sram_campaign.py",
    }
    expected_sources = {name: _sha256_file(path) for name, path in static.items()}
    generated = {
        "generated/expected.hex": "".join(
            f"{value:04x}\n" for value in vectors["expected"]["codes"]
        ),
        "generated/left.hex": "".join(
            f"{value:04x}\n" for value in vectors["left"]["codes"]
        ),
        "generated/qwen_ta_add_sram_harness.cpp": campaign_runner._harness(
            vectors
        ),
        "generated/right.hex": "".join(
            f"{value:04x}\n" for value in vectors["right"]["codes"]
        ),
        "generated/tb_qwen_ta_add_sram.sv": campaign_runner._testbench(vectors),
    }
    expected_sources.update(
        {name: _sha256(value.encode("utf-8")) for name, value in generated.items()}
    )
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the SRAM correlation replay",
)
def test_retained_sram_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
