"""Focused checks for exact Qwen ABI 3.0 PC41 RTL evidence."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from tools import build_a3_qwen_output_projection_vectors as vectors
from tools import run_a3_qwen_output_projection_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_qwen_output_projection"
RESULT = ROOT / "results/rtl/a3_qwen_output_projection_campaign.json"


def test_vectors_are_byte_exact_and_source_current() -> None:
    with tempfile.TemporaryDirectory() as name:
        generated = Path(name)
        manifest = vectors.build(generated)
        for filename in campaign.VECTOR_FILES:
            assert (generated / filename).read_bytes() == (
                VECTOR_ROOT / filename
            ).read_bytes()

    assert manifest["schema"] == vectors.SCHEMA
    assert len(manifest["cases"]) == 6
    assert manifest["oracle"]["expected_bf16_sha256"] == (
        "018f52e0834dbe624493704eea505c7d96be52463a82a12e448b8faefd749262"
    )
    assert manifest["oracle"]["independent_scalar_row_count"] == 32
    assert manifest["oracle"]["full_output_independently_scalar_checked"] is False


def test_authentic_operand_binding_and_honest_claim_boundary() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    assert manifest["input"]["bf16_sha256"] == (
        "8992e9d1a0b5303b81b2503df2e23170f838f772e79eb8d7c65c1fce4fac93c2"
    )
    assert manifest["input"]["authentic_current_qkv"] is True
    assert manifest["input"]["authentic_prior_context_kv"] is False
    assert manifest["weight"]["payload_sha256"] == (
        "d6fec091373ead7a102c480d4642a9b135e9e2cf0d0c289e0425967c96877ac2"
    )
    assert manifest["weight"]["shape"] == [4096, 4096]
    boundary = manifest["claim_boundary"]
    assert boundary["complete_layer_zero_output_projection"]
    assert boundary["exact_computed_words"]
    for forbidden in (
        "complete_layer",
        "model_token_generation",
        "eos",
        "architectural_token_commit_ticks",
        "tpot",
    ):
        assert boundary[forbidden] is False


def test_fail_closed_atomicity_and_backpressure_matrix() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    cases = {item["name"]: item["expected"] for item in manifest["cases"]}
    assert cases["rom_pc41_output_projection_exact"]["writes"] == 4096
    assert cases["hbm_pc41_output_projection_backpressure"]["writes"] == 4096
    assert cases["hbm_pc41_output_projection_backpressure"]["stall_mode"] == 1
    late = cases["rom_pc41_late_weight_nonfinite"]
    assert late["memory_reads"] == 16_781_312
    assert late["weight_reads"] == 16_777_216
    assert late["macs"] == 16_777_216
    assert late["writes"] == 0
    assert cases["hbm_pc41_wrong_numeric_valid_crc"]["memory_reads"] == 0
    assert cases["rom_pc41_wrong_output_shape_valid_crc"]["memory_reads"] == 0
    assert cases["rom_pc41_instruction_crc_corrupt"]["records_checked"] == 0


def test_retained_dual_simulator_campaign_is_source_current() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text())
    assert result["status"] == "pass"
    assert result["simulators_agree"]
    assert result["boundary"] == {
        "completed_opcode": "TENSOR.MATMUL",
        "completed_pc": 41,
        "hbm_operator_descriptor_id": 137,
        "new_first_unsupported_opcode": "VECTOR.ADD",
        "new_first_unsupported_pc": 44,
        "previous_first_unsupported_pc": 41,
        "rom_operator_descriptor_id": 134,
    }
    assert result["aggregate"] == {
        "atomic_sentinel_words_checked": 16_384,
        "case_count": 6,
        "checkpoint_weight_reads": 50_331_648,
        "checks_per_simulator": 24_702,
        "computed_output_words_compared": 8_192,
        "input_reads": 12_288,
        "memory_reads": 50_343_936,
        "multiply_adds": 50_331_648,
        "negative_case_count": 4,
        "positive_case_count": 2,
        "rtl_write_beats": 8_192,
    }
    scope = result["scope"]
    assert scope["simulator_cycles_are_verification_cost_only"]
    assert scope["model_token_generation"] is False
    assert scope["architectural_token_commit_ticks"] is False
    assert scope["tpot"] is False
    assert scope["release_gate_1_exact_tokens_through_eos_closed"] is False
    assert scope["release_gate_2_tpot_from_same_token_execution_closed"] is False
