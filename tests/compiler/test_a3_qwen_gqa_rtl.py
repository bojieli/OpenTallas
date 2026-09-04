"""Focused checks for exact Qwen ABI 3.0 PC38 GQA RTL evidence."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from tools import build_a3_qwen_gqa_vectors as vectors
from tools import run_a3_qwen_gqa_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_qwen_gqa"
RESULT = ROOT / "results/rtl/a3_qwen_gqa_campaign.json"


def test_vectors_are_byte_exact_and_source_current() -> None:
    with tempfile.TemporaryDirectory() as name:
        generated = Path(name)
        manifest = vectors.build(generated)
        for filename in campaign.VECTOR_FILES:
            assert (generated / filename).read_bytes() == (
                VECTOR_ROOT / filename
            ).read_bytes()

    assert manifest["schema"] == vectors.SCHEMA
    assert len(manifest["cases"]) == 5
    assert manifest["oracle"] == {
        "expected_bf16_sha256": (
            "8992e9d1a0b5303b81b2503df2e23170f838f772e79eb8d7c65c1fce4fac93c2"
        ),
        "implementation": "runtime/reference/tensor_accelerator_attention.py",
        "independent_of_dut": True,
        "word_count": 4096,
    }


def test_activation_provenance_and_honest_history_boundary() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    assert manifest["authentic_current_activations"] == {
        "key_pc29_bf16_sha256": (
            "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406"
        ),
        "query_pc26_bf16_sha256": (
            "f36db31b14aa59e0b0c7bc444403a7991063c3a0e874dcee151b7428b0ee8150"
        ),
        "value_pc17_bf16_sha256": (
            "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5"
        ),
    }
    assert manifest["history"]["row_count"] == 16
    assert manifest["history"]["authentic"] is False
    boundary = manifest["claim_boundary"]
    assert boundary["exact_pc38_gqa_arithmetic"]
    assert boundary["authentic_current_query_key_value"]
    assert boundary["authentic_prior_context_kv"] is False
    for forbidden in (
        "complete_layer",
        "model_token_generation",
        "eos",
        "architectural_token_commit_ticks",
        "tpot",
    ):
        assert boundary[forbidden] is False


def test_fail_closed_and_backpressure_matrix() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    cases = {item["name"]: item["expected"] for item in manifest["cases"]}
    assert cases["rom_pc38_gqa_exact"]["writes"] == 4096
    assert cases["hbm_pc38_gqa_backpressure"]["writes"] == 4096
    assert cases["hbm_pc38_gqa_backpressure"]["stall_mode"] == 1
    late = cases["rom_pc38_late_value_nonfinite"]
    assert late["memory_reads"] == 143_360
    assert late["value_multiplies"] == 69_632
    assert late["writes"] == 0
    assert cases["hbm_pc38_wrong_numeric_valid_crc"]["memory_reads"] == 0
    assert cases["rom_pc38_instruction_crc_corrupt"]["records_checked"] == 0


def test_retained_dual_simulator_campaign_is_source_current() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text())
    assert result["status"] == "pass"
    assert result["simulators_agree"]
    assert result["boundary"] == {
        "hbm_operator_descriptor_id": 137,
        "new_first_unsupported_opcode": "TENSOR.MATMUL",
        "new_first_unsupported_pc": 41,
        "previous_first_unsupported_pc": 38,
        "rom_operator_descriptor_id": 134,
    }
    assert result["aggregate"] == {
        "atomic_sentinel_words_checked": 12_288,
        "case_count": 5,
        "checks_per_simulator": 20_565,
        "computed_output_words_compared": 8_192,
        "exponential_evaluations": 1_632,
        "memory_reads": 430_080,
        "negative_case_count": 3,
        "positive_case_count": 2,
        "rtl_write_beats": 8_192,
        "score_multiplications": 208_896,
        "value_multiplications": 208_896,
    }
    scope = result["scope"]
    assert scope["shared_certifying_exponential"]
    assert scope["simulator_cycles_are_verification_cost_only"]
    assert scope["model_token_generation"] is False
    assert scope["architectural_token_commit_ticks"] is False
    assert scope["tpot"] is False
