"""Focused evidence checks for the ABI 3.0 HC stable-softmax RTL."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tools import build_a3_hc_stable_softmax_vectors as vectors
from tools import run_a3_hc_stable_softmax_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_hc_stable_softmax"
RESULT = ROOT / "results/rtl/a3_hc_stable_softmax_campaign.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_checkpoint_record_contains_inputs_only_and_is_source_current() -> None:
    matrices, manifest = vectors.load_checkpoint_inputs(VECTOR_ROOT)
    assert len(matrices) == 832
    assert manifest["matrix_count"] == 832
    assert manifest["binary_sha256"] == (
        "6579ce0d11186dae5cfa06eb6c1bf0db2db45b1594f09d25984dc6ad05239534"
    )
    assert [segment["token_count"] for segment in manifest["segments"]] == [512, 320]
    assert matrices[0] == (
        0x414E3868,
        0xC148C4D7,
        0xC1C6FBCC,
        0xC1B7250E,
        0xC1AC5C6D,
        0x403D5184,
        0xC0C5D0C3,
        0x3FEC860C,
        0xC1A7AF71,
        0x40394A92,
        0x40912776,
        0xC13AD8BA,
        0x4029EE36,
        0xC1EE237E,
        0xC1F12273,
        0xC01847E4,
    )
    assert manifest["claim_boundary"] == {
        "architectural_timing": False,
        "checkpoint_derived_softmax_inputs": True,
        "expected_outputs_in_binary": False,
        "full_hc_pre": False,
        "model_token_generation": False,
        "tpot": False,
    }


def test_independent_vectors_are_deterministic_and_cover_boundaries(
    tmp_path: Path,
) -> None:
    generated = tmp_path / "vectors"
    manifest = vectors.build(generated, VECTOR_ROOT)
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
        "successful_cases": 847,
    }
    assert manifest["coverage"] == {
        "exponential_zero_results": 22,
        "maximum_column_counts": {"0": 1699, "1": 833, "2": 833, "3": 24},
        "nonfinite_refusal_kinds": 5,
        "shifted_subnormal_codes": 27,
        "shifted_zero_codes": 3448,
        "subtraction_overflow_cases": 1,
    }
    binding = manifest["checkpoint_binding"]
    assert binding["prompt_token_count"] == 200_000
    assert binding["first_four_match_retained_service_sentinels"] is True
    assert binding["independent_expected_u32le_sha256"] == (
        "a3e540a4cfaf1ef499cf98199fc60d64b75e782cefdb56af4b12605b15142892"
    )
    assert binding["t1_shape_witness"]["token_id"] == 18_042
    assert manifest["oracle"]["host_floating_point"] is False
    assert manifest["oracle"]["service_arithmetic_imported"] is False
    assert manifest["oracle"]["rtl_implementation_imported"] is False


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_stable_softmax_rtl_compiles_with_iverilog(tmp_path: Path) -> None:
    output = tmp_path / "tb.vvp"
    process = subprocess.run(
        [
            shutil.which("iverilog") or "iverilog",
            "-g2012",
            "-s",
            "tb_a3_hc_stable_softmax",
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
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text(encoding="ascii"))
    campaign.validate_observed(
        result["normalized_summary"], result["checks_per_simulator"], manifest
    )

    assert result["status"] == "pass"
    assert result["simulators_agree"] is True
    assert result["checks_per_simulator"] == 2_394_764
    assert result["normalized_summary"] == {
        "argument_errors": 5,
        "atomic_busy_checks": 2_375_812,
        "busy_refusals": 1_696,
        "cases": 853,
        "checkpoint": 832,
        "checkpoint_words": 13_312,
        "directed": 21,
        "errors": 6,
        "max_cycles": 1_410,
        "overflow_errors": 1,
        "reset_cycles": 31,
        "stalls": 250,
        "success": 847,
        "t1_words": 16,
    }
    assert result["scope"]["source_major_4x4_stable_softmax"] is True
    assert result["scope"]["atomic_fail_closed_output"] is True
    assert result["scope"]["synthesizable_elaboration"] is True
    for nonclaim in (
        "full_200k_checkpoint_domain",
        "full_hc_pre",
        "sinkhorn_composition",
        "pc14_integration",
        "model_token_generation",
        "eos",
        "technology_mapping_or_timing",
        "architectural_timing",
        "tpot",
    ):
        assert result["scope"][nonclaim] is False

    for filename, digest in result["vector_sha256"].items():
        assert sha256(VECTOR_ROOT / filename) == digest
