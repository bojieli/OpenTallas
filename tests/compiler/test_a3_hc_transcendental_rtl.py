"""Focused evidence checks for the ABI 3.0 HC transcendental RTL."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tools import build_a3_hc_transcendental_vectors as vectors
from tools import run_a3_hc_transcendental_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_hc_transcendental"
RESULT = ROOT / "results/rtl/a3_hc_transcendental_campaign.json"


def test_exact_vectors_are_deterministic_and_source_current(tmp_path: Path) -> None:
    generated = tmp_path / "vectors"
    manifest = vectors.build(generated)
    for filename in campaign.VECTOR_FILES:
        assert (generated / filename).read_bytes() == (
            VECTOR_ROOT / filename
        ).read_bytes()

    assert manifest["case_count"] == 4_200
    assert manifest["counts"] == {
        "accepted": 4_155,
        "exp": 2_100,
        "refused": 45,
        "sigmoid": 2_100,
    }
    assert manifest["oracle"]["host_math_used"] is False
    assert manifest["oracle"]["rtl_implementation_imported"] is False
    assert manifest["claim_boundary"] == {
        "architectural_timing": False,
        "checkpoint_reachable_domain_complete": False,
        "full_hc_pre": False,
        "model_token_generation": False,
        "reusable_arithmetic_vectors": True,
        "tpot": False,
    }


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_transcendental_rtl_compiles_with_iverilog(tmp_path: Path) -> None:
    output = tmp_path / "tb.vvp"
    process = subprocess.run(
        [
            shutil.which("iverilog") or "iverilog",
            "-g2012",
            "-s",
            "tb_a3_hc_transcendental",
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
    result = json.loads(RESULT.read_text())
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    expected_summary, expected_checks = campaign.expected_summary(manifest)

    assert result["status"] == "pass"
    assert result["simulators_agree"] is True
    assert result["checks"] == expected_checks == 169_962
    assert result["normalized_summary"] == expected_summary
    assert result["scope"]["certifying_fixed_point_interval"] is True
    assert result["scope"]["correctly_rounded_nonpositive_exp_tested"] is True
    assert result["scope"]["correctly_rounded_direct_sigmoid_tested"] is True
    assert result["scope"]["independent_exact_rational_oracle"] is True
    assert result["scope"]["input_or_output_indexed_lookup_table"] is False
    for nonclaim in (
        "complete_binary32_exhaustion",
        "checkpoint_reachable_domain_complete",
        "technology_mapping_or_timing",
        "full_hc_pre",
        "pc14_integration",
        "model_token_generation",
        "eos",
        "architectural_timing",
        "tpot",
    ):
        assert result["scope"][nonclaim] is False
