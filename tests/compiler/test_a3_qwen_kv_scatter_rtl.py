"""Focused checks for the exact Qwen ABI 3.0 KV-scatter continuation."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from tools import build_a3_qwen_kv_scatter_vectors as vectors
from tools import run_a3_qwen_kv_scatter_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_qwen_kv_scatter"
RESULT = ROOT / "results/rtl/a3_qwen_kv_scatter_campaign.json"


def test_vectors_are_byte_exact_and_source_current() -> None:
    with tempfile.TemporaryDirectory() as name:
        generated = Path(name)
        manifest = vectors.build(generated)
        for filename in campaign.VECTOR_FILES:
            assert (generated / filename).read_bytes() == (
                VECTOR_ROOT / filename
            ).read_bytes()

    assert manifest["schema"] == vectors.SCHEMA
    assert manifest["positive_scatter_case_count"] == 4
    assert manifest["gqa_boundary_case_count"] == 2
    assert manifest["negative_case_count"] == 6


def test_exact_shipped_sites_and_upstream_results() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    profiles = manifest["profiles"]
    assert profiles["qwen3-8b-rom-single-chip/pc32"]["ids"]["operator"] == 111
    assert profiles["qwen3-8b-rom-single-chip/pc35"]["ids"]["operator"] == 118
    assert profiles["qwen3-8b-rom-single-chip/pc38"]["ids"]["operator"] == 127
    assert profiles["qwen3-8b-hbm-single-chip/pc32"]["ids"]["operator"] == 114
    assert profiles["qwen3-8b-hbm-single-chip/pc35"]["ids"]["operator"] == 120
    assert profiles["qwen3-8b-hbm-single-chip/pc38"]["ids"]["operator"] == 131
    assert manifest["source_binding"]["key"] == {
        "bf16_payload_sha256": (
            "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406"
        ),
        "producer_pc": 29,
        "word_count": 1024,
        "word_payload_sha256": (
            "33c6ee79b782b709bb6ead0342e265cf1d9694a0734d7008c735227524862862"
        ),
    }
    assert manifest["source_binding"]["value"] == {
        "bf16_payload_sha256": (
            "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5"
        ),
        "producer_pc": 17,
        "word_count": 1024,
        "word_payload_sha256": (
            "bc68d29a1ea0775432087a7faff1303774092dba465483ca95178ed90d4a8ac7"
        ),
    }


def test_fail_closed_matrix_and_claim_boundary() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    cases = {case["name"]: case for case in manifest["cases"]}
    for name in (
        "rom_pc32_key_scatter",
        "rom_pc35_value_scatter",
        "hbm_pc32_key_scatter",
        "hbm_pc35_value_scatter",
    ):
        assert cases[name]["expected"] == {
            "compare_output": True,
            "failed": False,
            "gqa_boundary": False,
            "indices_checked": 1,
            "moved_elements": 1024,
            "records_checked": 5,
            "refusal_reason": 0,
            "trap_class": 0,
            "write_count": 18_432,
        }
    for name in ("rom_pc38_gqa_boundary", "hbm_pc38_gqa_boundary"):
        assert cases[name]["expected"]["gqa_boundary"]
        assert cases[name]["expected"]["trap_class"] == vectors.TRAP_CAPABILITY
        assert cases[name]["expected"]["write_count"] == 0
    negatives = [
        case
        for case in manifest["cases"]
        if case["expected"]["failed"] and not case["expected"]["gqa_boundary"]
    ]
    assert len(negatives) == 6
    assert all(case["expected"]["write_count"] == 0 for case in negatives)

    boundary = manifest["claim_boundary"]
    assert boundary["exact_rom_and_hbm_pc32_pc35_instruction_records"]
    assert boundary["exact_upstream_key_from_pc29_rope"]
    assert boundary["exact_upstream_value_from_pc17_projection"]
    assert boundary["all_active_plane_words_compared"]
    for forbidden in (
        "gqa_arithmetic",
        "authentic_prior_context_kv",
        "complete_layer",
        "model_token_generation",
        "eos",
        "architectural_timing",
        "tpot",
        "verification_cycles_are_tpot",
    ):
        assert boundary[forbidden] is False


def test_rtl_compiles_with_iverilog() -> None:
    iverilog, _, _, _ = campaign.resolve_tools()
    with tempfile.TemporaryDirectory() as name:
        output = Path(name) / "tb.vvp"
        process = subprocess.run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_qwen_kv_scatter",
                "-o",
                str(output),
                *[str(ROOT / source) for source in campaign.RTL_SOURCES],
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    assert process.returncode == 0, process.stdout + process.stderr


def test_retained_dual_simulator_campaign_is_source_current() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text())
    assert result["status"] == "pass"
    assert result["simulators_agree"]
    assert result["boundary"] == {
        "hbm_operator_descriptor_id": 131,
        "new_first_unsupported_opcode": "ATTENTION.GQA",
        "new_first_unsupported_pc": 38,
        "previous_first_unsupported_pc": 32,
        "rom_operator_descriptor_id": 127,
    }
    assert result["aggregate"] == {
        "case_count": 12,
        "checks_per_simulator": 209_076,
        "destination_words_compared": 69_632,
        "gqa_boundary_case_count": 2,
        "indices_checked": 5,
        "moved_elements": 4_096,
        "negative_case_count": 6,
        "preserved_words_compared": 65_536,
        "records_checked": 57,
        "replaced_words_compared": 4_096,
        "rtl_write_beats": 73_728,
        "scatter_case_count": 4,
    }
    scope = result["scope"]
    assert scope["exact_rom_pc32_pc35_scatter"]
    assert scope["exact_hbm_pc32_pc35_scatter"]
    assert scope["exact_pc38_gqa_metadata_admitted"]
    assert scope["simulator_cycles_are_verification_cost_only"]
    assert scope["model_token_generation"] is False
    assert scope["independent_oracle_token_match"] is False
    assert scope["eos_and_no_post_eos"] is False
    assert scope["architectural_token_commit_ticks"] is False
    assert scope["tpot"] is False
