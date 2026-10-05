"""Focused checks for atomic HC stable-softmax/Sinkhorn-20 RTL evidence."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tools import build_a3_hc_softmax_sinkhorn20_vectors as vectors
from tools import run_a3_hc_softmax_sinkhorn20_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_hc_softmax_sinkhorn20"
RESULT = ROOT / "results/rtl/a3_hc_softmax_sinkhorn20_campaign.json"


def test_composed_exact_vectors_are_deterministic_and_source_current(
    tmp_path: Path,
) -> None:
    generated = tmp_path / "vectors"
    manifest = vectors.build(generated)
    for filename in campaign.GENERATED_VECTOR_FILES:
        assert (generated / filename).read_bytes() == (
            VECTOR_ROOT / filename
        ).read_bytes()

    assert manifest["counts"] == {
        "cases": 853,
        "categories": {
            "checkpoint_final_t320": 320,
            "checkpoint_first_t512": 512,
            "directed_extreme": 2,
            "directed_ordering": 7,
            "directed_overflow": 1,
            "directed_rounding": 4,
            "directed_underflow": 2,
            "nonfinite_refusal": 5,
        },
        "checkpoint_cases": 832,
        "directed_cases": 21,
        "errors": {"0": 847, "1": 5, "2": 1},
        "refused_cases": 6,
        "sinkhorn_successes": 847,
        "stable_softmax_successes": 847,
        "successful_cases": 847,
        "successful_sinkhorn_divisions": 528_528,
    }
    checkpoint = manifest["checkpoint_binding"]
    assert checkpoint["prompt_token_count"] == 200_000
    assert checkpoint["checkpoint_output_u32le_sha256"] == (
        "51684cad947f996d08e01b7674b2be7b864874bed137eff03582012af8f3e63b"
    )
    assert checkpoint["first_t512_output"] == {
        "byte_identical_to_authenticated_functional_output": True,
        "qualified_path": "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_combination.u32le",
        "qualified_sha256": "5d9a46a955239c39d423edcdfa0d3cce4b51b93aeebd585fb357ecd7eba186fa",
        "sha256": "5d9a46a955239c39d423edcdfa0d3cce4b51b93aeebd585fb357ecd7eba186fa",
    }
    assert checkpoint["final_t320_output_u32le_sha256"] == (
        "dbdc4f90828960793c1a5f31bd0d223c402df6d77e1939f314648a9c4d4684bd"
    )
    assert checkpoint["t1_shape_witness"]["token_id"] == 18_042
    assert manifest["oracle"] == {
        "exponential": "independent exact-rational adaptive interval",
        "host_floating_point": False,
        "rtl_implementation_imported": False,
        "service_arithmetic_imported": False,
        "sinkhorn_binary32": "self-contained exact Fraction arithmetic and integer RNE encoding",
        "stable_softmax_binary32": "self-contained exact Fraction arithmetic and integer RNE encoding",
    }


def test_vectors_bind_current_hbm_and_rom_hc_descriptors() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text(encoding="ascii"))
    binding = manifest["descriptor_binding"]
    assert binding["abi"] == {"major": 3, "minor": 0}
    assert binding["numeric_contract"]["contract_digest"] == (
        "202e8be635a9cf690f3d81f322698168c72912faf735bd5b76fd29fd462cd586"
    )
    assert binding["numeric_contract"]["epsilon_bits"] == 0x358637BD
    assert binding["numeric_contract"]["rounding_mode"] == 0
    assert binding["numeric_contract"]["reduction_order"] == 1

    hbm = binding["profiles"]["deepseek-v4-flash-hbm-cluster"]
    rom = binding["profiles"]["deepseek-v4-flash-rom-wafer"]
    assert (hbm["profile"], hbm["program_counter"], hbm["operator_descriptor_id"]) == (
        1,
        14,
        545,
    )
    assert (rom["profile"], rom["program_counter"], rom["operator_descriptor_id"]) == (
        0,
        15,
        381,
    )
    assert hbm["numeric_descriptor_sha256"] == rom["numeric_descriptor_sha256"]
    assert hbm["combination_capacity_tokens"] == 512
    assert rom["combination_capacity_tokens"] == 131_072
    assert hbm["deployment_identity_evidence_hash_verified"] is True
    assert rom["deployment_identity_evidence_hash_verified"] is True

    qualification = binding["authenticated_functional_qualification"]
    assert qualification["all_output_words_bitwise_compared"] is True
    assert qualification["combination_output_sha256"] == (
        "5d9a46a955239c39d423edcdfa0d3cce4b51b93aeebd585fb357ecd7eba186fa"
    )
    assert qualification["workload"]["prompt_token_count"] == 200_000
    assert qualification["model_token_generation"] is False
    assert qualification["eos"] is False
    assert qualification["tpot"] is False

    evidence = manifest["evidence_sha256"]
    assert evidence[
        "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json"
    ] == "3a37a973339cf7abe6e06b595f17445a4a80307a8c87773f7f1950d66a5c9c60"
    assert evidence[
        "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json"
    ] == "21dbb02b406cb4cdf39d5d140e5bcaa6b6014946a5af4228f0c3e646757642f1"


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_composed_rtl_compiles_with_iverilog(tmp_path: Path) -> None:
    output = tmp_path / "tb.vvp"
    process = subprocess.run(
        [
            shutil.which("iverilog") or "iverilog",
            "-g2012",
            "-s",
            "tb_a3_hc_softmax_sinkhorn20",
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


def test_retained_campaign_is_exact_source_current_and_bounded() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text(encoding="ascii"))
    assert result["status"] == "pass"
    assert result["simulators_agree"] is True
    assert result["checks_per_simulator"] == 19_313_653
    assert result["normalized_summary"] == {
        "active_resets": 1,
        "argument_errors": 5,
        "busy_atomic_checks": 19_292_960,
        "cases": 853,
        "checkpoint": 832,
        "checkpoint_words": 13_312,
        "directed": 21,
        "errors": 6,
        "max_cycles": 22_786,
        "overflow_errors": 1,
        "reset_cycles": 31,
        "sinkhorn_entries": 847,
        "stalls": 250,
        "success": 847,
        "t1_words": 16,
    }
    assert result["scope"]["atomic_stable_softmax_sinkhorn20_composition"] is True
    assert result["scope"]["authenticated_t512_final_output_bitwise_match"] is True
    assert result["scope"]["current_rom_and_hbm_descriptor_identity_bound"] is True
    assert result["scope"]["active_reset_in_sinkhorn"] is True
    assert result["scope"]["synthesizable_elaboration"] is True
    for nonclaim in (
        "full_200k_checkpoint_domain",
        "full_hc_pre",
        "descriptor_execution",
        "pc14_or_pc15_integration",
        "model_token_generation",
        "token_correctness",
        "eos",
        "technology_mapping_or_timing",
        "architectural_timing",
        "tpot",
    ):
        assert result["scope"][nonclaim] is False
