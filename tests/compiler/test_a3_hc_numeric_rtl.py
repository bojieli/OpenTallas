"""Focused evidence checks for the ABI 3.0 HC_PRE numeric RTL."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tools import build_a3_hc_numeric_vectors as vectors
from tools import run_a3_hc_numeric_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_hc_numeric"
RESULT = ROOT / "results/rtl/a3_hc_numeric_campaign.json"


def test_exact_fraction_vectors_are_deterministic_and_source_current(
    tmp_path: Path,
) -> None:
    generated = tmp_path / "vectors"
    manifest = vectors.build(generated)
    for filename in campaign.VECTOR_FILES:
        assert (generated / filename).read_bytes() == (
            VECTOR_ROOT / filename
        ).read_bytes()

    assert manifest["oracle"] == {
        "method": "exact Fraction decode, rational arithmetic, integer RNE encode",
        "host_floating_point": False,
        "imports_opentallas_arithmetic": False,
        "division_contract": "finite signed binary32 RNE; canonical positive zero; fail-closed nonfinite/zero-divisor/overflow",
        "sinkhorn_contract": "source-major 4x4; initial column then 19 row/column pairs; balanced four-term positive sums; epsilon 0x358637bd",
    }


def test_vector_manifest_covers_checkpoint_random_and_exception_boundaries() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    assert manifest["counts"] == {
        "checkpoint_sinkhorn_divisions": 2496,
        "division_cases": 6641,
        "division_categories": {
            "checkpoint_derived": 2496,
            "directed": 49,
            "random_finite": 4096,
        },
        "division_errors": {"0": 6145, "1": 9, "2": 487},
        "sinkhorn_cases": 81,
        "sinkhorn_categories": {
            "checkpoint_derived": 4,
            "directed": 6,
            "directed_overflow": 1,
            "invalid": 6,
            "random_moderate": 48,
            "random_wide": 16,
        },
        "sinkhorn_errors": {"0": 74, "1": 6, "2": 1},
        "successful_sinkhorn_divisions_per_case": 624,
    }
    binding = manifest["checkpoint_binding"]
    assert binding["workload_id"] == "TA-DS-CTX-200K-1"
    assert binding["prompt_token_count"] == 200_000
    assert binding["positions"] == [0, 1, 2, 3]
    assert binding["token_ids"] == [18042, 41514, 6897, 33523]
    assert binding["all_four_outputs_match_qualified_prefix"] is True
    assert (
        binding["independent_output_u32le_sha256"]
        == binding["qualified_output_prefix_u32le_sha256"]
        == "16ca2e2ad0c991b6b14110ebc69de0bfed766dc3323189f78ca68d66496cec6f"
    )
    assert manifest["claim_boundary"] == {
        "architectural_timing": False,
        "eos": False,
        "exponential": False,
        "full_hc_pre": False,
        "model_token_generation": False,
        "sigmoid": False,
        "stable_softmax_front_end": False,
        "tpot": False,
        "vectors_only": True,
    }


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_numeric_rtl_compiles_with_iverilog(tmp_path: Path) -> None:
    output = tmp_path / "tb.vvp"
    process = subprocess.run(
        [
            shutil.which("iverilog") or "iverilog",
            "-g2012",
            "-s",
            "tb_a3_hc_numeric",
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


def test_retained_dual_simulator_campaign_is_exact_and_source_current() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text())
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    expected_summary, expected_checks = campaign.expected_summary(manifest)

    assert result["status"] == "pass"
    assert result["simulators_agree"] is True
    assert result["checks"] == expected_checks == 73_040
    assert result["normalized_summary"] == expected_summary
    assert result["scope"]["independent_fraction_oracle"] is True
    assert result["scope"]["host_floating_point_oracle"] is False
    assert result["scope"]["synthesizable_elaboration"] is True
    for nonclaim in (
        "technology_mapping_or_timing",
        "full_hc_pre",
        "stable_softmax_front_end",
        "correctly_rounded_exponential",
        "correctly_rounded_sigmoid",
        "pc14_integration",
        "model_token_generation",
        "eos",
        "architectural_timing",
        "tpot",
    ):
        assert result["scope"][nonclaim] is False
