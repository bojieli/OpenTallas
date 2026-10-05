from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_qwen3_ta_rtl_dma_vectors as vector_builder
from tools import run_qwen3_ta_rtl_dma_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)
DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
CHECKPOINT_LOCK = DEPLOYMENT / "source/checkpoint.lock.json"
PHYSICAL_PLAN = DEPLOYMENT / "physical/physical_plan.json"
COMMAND_VECTORS = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
VECTORS = ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_vectors.json"
CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_dma_campaign.json"
VECTOR_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_campaign_v1.schema.json"
)
EXPECTED_VECTOR_ID = (
    "98806ae5e1b8f3dbe1e516084b099a5f592f98acf6adb74edb0198d82ae10216"
)
EXPECTED_CAMPAIGN_ID = (
    "033c073ff5c3cfede3d95364a857ff7ebb23d2c39c6d7d8e483c7df20f55b17d"
)
EXPECTED_PAYLOAD_SHA256 = (
    "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def test_authentic_dma_vectors_are_schema_valid_exact_and_source_bound() -> None:
    vectors = load_strict_json(VECTORS)
    schema = load_strict_json(VECTOR_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_ID
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    payload = bytes.fromhex(vectors["hbm"]["payload_hex"])
    assert len(payload) == vectors["hbm"]["size_bytes"] == 8192
    assert _sha256(payload) == vectors["hbm"]["payload_sha256"]
    assert vectors["hbm"]["payload_sha256"] == EXPECTED_PAYLOAD_SHA256
    assert vectors["operation"] == {
        "command_count": 2,
        "command_start": 1,
        "kernel_index": 1,
        "operation_id": "node.0001",
        "selected_command_index": 1,
        "tensor_id": "model.layers.0.input_layernorm.weight",
    }
    assert vectors["hbm"]["burst_count"] == 128
    assert vectors["sram"]["write_count"] == 512
    assert vectors["claim_boundary"]["complete_dma_command"] is True
    assert vectors["claim_boundary"]["qualified_hbm_phy"] is False
    assert vectors["claim_boundary"]["qualified_sram_macro"] is False
    assert vectors["claim_boundary"]["complete_layer_execution"] is False
    assert vectors["claim_boundary"]["ta_rtl_6_closed"] is False


def test_retained_dma_campaign_is_schema_valid_reproducible_and_bound() -> None:
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
        "command_index": 1,
        "expected_payload_sha256": EXPECTED_PAYLOAD_SHA256,
        "hbm_address": 1244659712,
        "hbm_burst_bytes": 64,
        "hbm_bytes_read": 8192,
        "hbm_error_cases": 1,
        "hbm_request_count": 128,
        "maximum_outstanding_hbm_requests": 1,
        "sram_address": 2097152,
        "sram_bytes_written": 8192,
        "sram_word_bytes": 16,
        "sram_write_count": 512,
    }
    marker = (
        "PASS: Qwen DMA RTL bytes=8192 hbm_requests=128 sram_writes=512 "
        f"faults=1 vector_set={EXPECTED_VECTOR_ID}"
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
        "rtl/ot_ta_command_decoder.sv": ROOT / "rtl/ot_ta_command_decoder.sv",
        "rtl/ot_ta_dma_hbm_to_sram.sv": ROOT / "rtl/ot_ta_dma_hbm_to_sram.sv",
        "schemas/compiler/tensor_accelerator/qwen_rtl_dma_campaign_v1.schema.json": CAMPAIGN_SCHEMA,
        "schemas/compiler/tensor_accelerator/qwen_rtl_dma_vectors_v1.schema.json": VECTOR_SCHEMA,
        "testdata/compiler/tensor_accelerator/qwen3_rtl_dma_vectors.json": VECTORS,
        "tools/build_qwen3_ta_rtl_dma_vectors.py": ROOT
        / "tools/build_qwen3_ta_rtl_dma_vectors.py",
        "tools/run_qwen3_ta_rtl_dma_campaign.py": ROOT
        / "tools/run_qwen3_ta_rtl_dma_campaign.py",
    }
    expected_sources = {name: _sha256_file(path) for name, path in static.items()}
    payload_text = "".join(
        f"{value:02x}\n" for value in bytes.fromhex(vectors["hbm"]["payload_hex"])
    )
    generated = {
        "generated/payload.hex": payload_text,
        "generated/qwen_ta_dma_harness.cpp": campaign_runner._harness(vectors),
        "generated/tb_qwen_ta_dma.sv": campaign_runner._testbench(vectors),
    }
    expected_sources.update(
        {name: _sha256(value.encode("utf-8")) for name, value in generated.items()}
    )
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    not SNAPSHOT.is_dir() or not CHECKPOINT_LOCK.is_file(),
    reason="pinned Qwen checkpoint is unavailable",
)
def test_authentic_dma_vector_builder_reproduces_retained_payload() -> None:
    retained = load_strict_json(VECTORS)
    rebuilt = vector_builder.build(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        physical_plan_path=PHYSICAL_PLAN,
        command_vectors_path=COMMAND_VECTORS,
    )
    assert canonical_json_bytes(rebuilt) == canonical_json_bytes(retained)


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the DMA correlation replay",
)
def test_retained_dma_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN)
    replayed = campaign_runner.run(VECTORS)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
