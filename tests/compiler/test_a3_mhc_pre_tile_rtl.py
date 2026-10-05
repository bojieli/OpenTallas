"""Focused evidence checks for the descriptor-bound DeepSeek HC_PRE tiles."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from tools import build_a3_mhc_pre_tile_vectors as vectors
from tools import run_a3_mhc_pre_tile_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_mhc_pre_tiles"
RESULT = ROOT / "results/rtl/a3_mhc_pre_tile_campaign.json"


def test_vectors_are_byte_exact_and_source_current() -> None:
    with tempfile.TemporaryDirectory() as name:
        generated = Path(name)
        manifest = vectors.build(generated)
        for filename in campaign.VECTOR_FILES:
            assert (generated / filename).read_bytes() == (
                VECTOR_ROOT / filename
            ).read_bytes()

    assert manifest["schema"] == "opentallas.rtl.a3_mhc_pre_tile_vectors.v1"
    assert manifest["positive_case_count"] == 4
    assert manifest["negative_case_count"] == 18
    assert manifest["image_sha256"]["cases.hex"] == vectors.sha256_file(
        VECTOR_ROOT / "cases.hex"
    )


def test_profiles_are_exact_shipped_instruction_and_descriptor_sites() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    rom = manifest["profiles"]["deepseek-v4-flash-rom-wafer"]
    hbm = manifest["profiles"]["deepseek-v4-flash-hbm-cluster"]
    assert (rom["program_counter"], rom["operator_descriptor_id"]) == (15, 381)
    assert (hbm["program_counter"], hbm["operator_descriptor_id"]) == (14, 545)
    assert hbm["authenticated_prior_descriptor_id"] == 546
    assert rom["profile"] == vectors.PROFILE_ROM
    assert hbm["profile"] == vectors.PROFILE_HBM
    assert hbm["instruction_sha256"] == (
        "1495e79701542b0ef97e414465a67b323fa24c8d793a58b176dd3ee2d164c8ec"
    )
    assert len(rom["selected_descriptors"]) == 11
    assert len(hbm["selected_descriptors"]) == 11


def test_exact_extents_and_fail_closed_matrix() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    cases = {case["name"]: case for case in manifest["cases"]}
    assert cases["rom_pc15_decode_t1"]["expected"] == {
        "admitted": True,
        "commit_tiles": 2,
        "error_code": 0,
        "logical_fmas": 393_216,
        "logical_output_words": 24,
        "projection_tiles": 16,
        "total_tiles": 18,
    }
    assert cases["hbm_pc14_authenticated_t512"]["expected"] == {
        "admitted": True,
        "commit_tiles": 24,
        "error_code": 0,
        "logical_fmas": 201_326_592,
        "logical_output_words": 12_288,
        "projection_tiles": 393_216,
        "total_tiles": 393_240,
    }
    assert cases["hbm_pc14_final_block_t320"]["expected"]["total_tiles"] == 245_775
    assert cases["hbm_pc14_decode_t1"]["expected"]["total_tiles"] == 49_155

    negatives = [case for case in manifest["cases"] if not case["expected"]["admitted"]]
    assert len(negatives) == 18
    assert {case["expected"]["error_code"] for case in negatives} == {
        vectors.ERR_INSTRUCTION,
        vectors.ERR_OPERATOR,
        vectors.ERR_NUMERIC,
        vectors.ERR_VIEW,
        vectors.ERR_SCHEDULE,
    }
    assert all(case["expected"]["total_tiles"] == 0 for case in negatives)


def test_functional_golden_is_bound_without_arithmetic_overclaim() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    binding = manifest["functional_output_binding"]
    assert binding["all_functional_words_bitwise_compared"]
    assert binding["combined_words"] == 12_288
    assert binding["combined_sha256"] == (
        "421774b7a8157549784615466e7868d2e44e11ed93fe3a060efd923ed3b75565"
    )
    assert binding["outputs"]["weights"]["sha256"] == (
        "f4d046389962e663ae789177c9e86f2643df701270d5b385ab9840f7c6148a63"
    )
    assert binding["outputs"]["combination"]["sha256"] == (
        "5d9a46a955239c39d423edcdfa0d3cce4b51b93aeebd585fb357ecd7eba186fa"
    )

    claims = manifest["claim_boundary"]
    assert claims["exact_instruction_operator_numeric_view_schedule_admission"]
    assert claims["exact_projection_and_output_coordinate_tiling"]
    assert claims["full_functional_output_digest_bound"]
    for forbidden in (
        "full_hc_pre_rtl_arithmetic",
        "correctly_rounded_sigmoid_rtl",
        "correctly_rounded_exponential_rtl",
        "stable_softmax_frontend_rtl",
        "projection_mac_rtl_in_this_block",
        "model_token_generation",
        "eos",
        "architectural_timing",
        "tpot",
    ):
        assert claims[forbidden] is False


def test_scheduler_and_scoreboard_compile_with_iverilog() -> None:
    iverilog, _, _, _ = campaign.resolve_tools()
    with tempfile.TemporaryDirectory() as name:
        output = Path(name) / "tb.vvp"
        process = subprocess.run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_mhc_pre_tile_scheduler",
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
    assert result["checks"] == 11_346_434
    assert result["aggregate"] == {
        "accepted_tiles": 688_188,
        "commit_tiles": 44,
        "deliberate_stall_cycles": 181_605,
        "negative_cases": 18,
        "positive_cases": 4,
        "projection_tiles": 688_144,
    }
    assert result["active_reset"] == {"accepted": 37, "stalls": 9}
    scope = result["scope"]
    assert scope["exact_rom_pc15_descriptor_381_admission"]
    assert scope["exact_hbm_pc14_descriptor_545_admission"]
    assert scope["authenticated_prior_hbm_descriptor_546_semantic_equivalence"]
    assert scope["functional_t512_golden_digest_bound"]
    assert scope["simulator_cycles_are_verification_cost_only"]
    assert scope["end_to_end_token_correctness"] is False
    assert scope["architectural_timing"] is False
    assert scope["tpot"] is False
