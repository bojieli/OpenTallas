"""Focused evidence checks for current-descriptor T=1 HC_PRE RTL."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tools import build_a3_hc_pre_t1_vectors as vectors
from tools import extract_a3_hc_pre_t1_checkpoint as extractor
from tools import run_a3_hc_pre_t1_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_hc_pre_t1"
CHECKPOINT_ROOT = ROOT / "testdata/rtl/a3_hc_pre_t1_checkpoint"
RESULT = ROOT / "results/rtl/a3_hc_pre_t1_campaign.json"


@pytest.mark.skipif(
    not extractor.DEFAULT_SNAPSHOT.is_dir(),
    reason="pinned DeepSeek checkpoint snapshot is unavailable",
)
def test_checkpoint_extraction_is_authenticated_and_deterministic(
    tmp_path: Path,
) -> None:
    generated = tmp_path / "checkpoint"
    manifest = extractor.build(extractor.DEFAULT_SNAPSHOT, generated)
    for filename in (*extractor.OUTPUT_FILES, "index.json"):
        assert (generated / filename).read_bytes() == (
            CHECKPOINT_ROOT / filename
        ).read_bytes()
    assert manifest["workload_binding"] == {
        "workload_id": "TA-DS-CTX-200K-1",
        "prompt_token_count": 200_000,
        "position": 0,
        "token_id": 18_042,
    }
    assert manifest["claim_boundary"]["authenticated_checkpoint_input"] is True
    assert manifest["claim_boundary"]["model_token_generation"] is False
    assert manifest["claim_boundary"]["tpot"] is False


def test_exact_vectors_are_deterministic_and_bind_current_descriptors(
    tmp_path: Path,
) -> None:
    generated = tmp_path / "vectors"
    manifest = vectors.build(generated)
    for filename in vectors.VECTOR_FILES:
        assert (generated / filename).read_bytes() == (
            VECTOR_ROOT / filename
        ).read_bytes()

    assert manifest["fma"]["counts"] == {
        "total": 4_112,
        "directed": 16,
        "random_finite": 4_096,
        "success": 3_571,
        "argument_errors": 6,
        "overflow_errors": 535,
        "fused_differs_from_separate_rounding": 118,
    }
    assert manifest["witness"]["mean_square"] == "3b98e318"
    assert manifest["witness"]["inverse_rms"] == "416a36cf"
    assert manifest["witness"]["counters"] == {
        "input_bf16_values": 16_384,
        "rms_square_multiplies": 16_384,
        "rms_reduction_adds": 16_383,
        "projection_product_accumulates": 393_216,
        "projection_rms_multiplies": 24,
        "field_affine_multiplies": 24,
        "field_affine_adds": 24,
    }
    assert manifest["descriptors"]["rom_pc15"]["operator_descriptor_id"] == 381
    assert manifest["descriptors"]["hbm_pc14"]["operator_descriptor_id"] == 545
    assert manifest["claim_boundary"]["rtl_execution"] is False
    assert manifest["claim_boundary"]["model_token_generation"] is False
    assert manifest["claim_boundary"]["tpot"] is False


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_full_t1_rtl_compiles_with_iverilog(tmp_path: Path) -> None:
    output = tmp_path / "tb.vvp"
    process = subprocess.run(
        [
            shutil.which("iverilog") or "iverilog",
            "-g2012",
            "-s",
            "tb_a3_hc_pre_t1",
            "-o",
            str(output),
            *[str(ROOT / source) for source in campaign.RTL_SOURCES],
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert process.returncode == 0, process.stdout + process.stderr


def test_retained_dual_simulator_campaign_is_source_current() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text("ascii"))
    assert result["status"] == "pass"
    assert result["simulators_agree"] is True
    assert result["normalized_summary"] == {
        "active_resets": 1,
        "arithmetic_errors": 2,
        "atomic_private_checks": 685_335,
        "checkpoint_words": 148,
        "coefficient_error_cycles": 213_034,
        "descriptor_errors": 1,
        "fma_argument_errors": 6,
        "fma_cases": 4_112,
        "fma_overflow_errors": 535,
        "fma_success": 3_571,
        "hbm_cycles": 236_126,
        "output_stalls": 17,
        "parity_words": 24,
        "rom_cycles": 236_126,
    }
    assert result["scope"]["all_74_numeric_boundary_words_exact"] is True
    assert result["scope"]["rom_hbm_output_parity"] is True
    assert result["scope"]["late_arithmetic_error_single_completion"] is True
    assert result["scope"]["model_token_generation"] is False
    assert result["scope"]["token_correctness"] is False
    assert result["scope"]["eos"] is False
    assert result["scope"]["tpot"] is False
