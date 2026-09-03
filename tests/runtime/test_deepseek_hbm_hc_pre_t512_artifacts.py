"""Focused checks for the retained full-shape PC-14 functional qualification."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import tools.qualify_deepseek_hbm_hc_pre_t512 as qualification


ROOT = Path(__file__).resolve().parents[2]
VECTOR_DIR = ROOT / "testdata/runtime/deepseek_hbm_hc_pre_t512"
RESULT = ROOT / "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json"
BLOCKERS = ROOT / "results/abi3/deepseek_hbm_hc_pre_t512_rtl_blockers.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_retained_pc14_t512_artifacts_are_self_authenticating() -> None:
    qualification.verify_artifacts(VECTOR_DIR, RESULT)


def test_retained_vector_is_the_complete_first_issue_not_a_reduced_probe() -> None:
    vector = load(VECTOR_DIR / qualification.VECTOR_FILE)
    assert vector["workload"]["workload_id"] == "TA-DS-CTX-200K-1"
    assert vector["workload"]["prompt_token_count"] == 200_000
    assert vector["workload"]["first_issue_token_count"] == 512
    assert len(vector["first_issue_token_ids"]) == 512
    assert vector["first_issue_token_ids"][0] == 18_042
    assert len(set(vector["first_issue_token_ids"])) == 162
    assert vector["geometry"] == {
        "hidden": [512, 4, 4096],
        "projection": [24, 16384],
        "weights_output": [512, 2, 4],
        "combination_output": [512, 4, 4],
        "ordered_projection_fused_product_adds": 201_326_592,
    }

    weights = np.fromfile(
        VECTOR_DIR / qualification.WEIGHTS_FILE, dtype="<u4"
    ).reshape(512, 2, 4)
    combination = np.fromfile(
        VECTOR_DIR / qualification.COMBINATION_FILE, dtype="<u4"
    ).reshape(512, 4, 4)
    assert np.array_equal(weights[0], qualification.FIRST_WEIGHTS)
    assert np.array_equal(combination[0], qualification.FIRST_COMBINATION)
    assert weights.size + combination.size == 12_288


def test_service_composition_covers_every_position_once_in_128_commands() -> None:
    result = load(RESULT)
    commands = result["service_composition"]["commands"]
    assert len(commands) == 128
    positions: list[int] = []
    for index, command in enumerate(commands):
        assert command["command_index"] == index
        assert command["position_stop_exclusive"] - command["position_start"] == 4
        assert len(command["token_ids"]) == 4
        assert command["status"] == "service_completed_and_self_checked"
        assert command["bitwise_match_to_functional_slice"] is True
        positions.extend(
            range(command["position_start"], command["position_stop_exclusive"])
        )
    assert positions == list(range(512))
    assert result["comparison"]["compared_word_count"] == 12_288
    assert result["comparison"]["mismatched_words"] == 0


def test_result_draws_the_required_evidence_boundary() -> None:
    result = load(RESULT)
    assert result["status"] == "pass"
    assert result["claims"] == {
        "full_pc14_first_issue_functional_operator": True,
        "all_pc14_output_words_bitwise_compared": True,
        "rtl_execution": False,
        "model_token_generation": False,
        "end_to_end_decode": False,
        "eos": False,
        "architectural_timing": False,
        "tpot": False,
    }
    assert result["lane_independence"]["separated"] is True
    assert result["functional_execution"]["transaction_status"] == "success"
    assert result["functional_execution"]["architectural_counters"][
        "vector.mhc_sites"
    ] == 512
    assert result["functional_execution"]["architectural_counters"][
        "vector.elements"
    ] == 8_388_608
    assert all("TPOT" not in item or "No host duration" in item for item in result["nonclaims"])


def test_rtl_blocker_record_requires_reusable_arithmetic_not_a_table_witness() -> None:
    blockers = load(BLOCKERS)
    assert blockers["status"] == "open"
    assert blockers["descriptor_id"] == 546
    assert blockers["program_counter"] == 14
    ids = {record["id"] for record in blockers["blockers"]}
    assert ids == {
        "RTL-HCPRE-CR32-EXP",
        "RTL-HCPRE-CR32-SIGMOID",
        "RTL-HCPRE-RN32-DIVIDE",
        "RTL-HCPRE-SINKHORN20",
        "RTL-HCPRE-PROJECTION-SCHEDULE",
        "RTL-HCPRE-PC14-INTEGRATION",
    }
    assert all(record["status"] == "open" for record in blockers["blockers"])
    forbidden = " ".join(blockers["forbidden_shortcuts"]).lower()
    assert "lookup table" in forbidden
    assert "host precomputation" in forbidden
    assert "reduced hidden width" in forbidden


def test_retained_vector_still_names_the_current_shipped_artifact_when_available() -> None:
    if not qualification.DEFAULT_DEPLOYMENT.is_dir() or not qualification.DEFAULT_WORKLOAD.is_file():
        pytest.skip("ignored shipped build/workload artifacts are unavailable")
    _, shipped = qualification._validate_shipped_pc14(  # noqa: SLF001
        qualification.DEFAULT_DEPLOYMENT
    )
    token_ids, workload = qualification._load_workload(  # noqa: SLF001
        qualification.DEFAULT_WORKLOAD
    )
    vector = load(VECTOR_DIR / qualification.VECTOR_FILE)
    assert vector["first_issue_token_ids"] == token_ids
    assert vector["workload"] == workload
    for field, value in vector["shipped_artifact"].items():
        assert shipped[field] == value
