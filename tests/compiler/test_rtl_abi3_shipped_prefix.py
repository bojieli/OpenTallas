"""Focused checks for the shipped ABI 3.0 sequencer/engine prefix witness."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from tools import build_abi3_shipped_prefix_vectors as generator
from tools import rtl_abi3_shipped_prefix_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
VECTOR_JSON = VECTOR_DIR / "abi3_shipped_prefix_vectors.json"
CAMPAIGN_JSON = ROOT / "results/rtl/abi3_shipped_prefix_campaign.json"

TOOLS_AVAILABLE = all(
    shutil.which(tool) is not None for tool in ("iverilog", "vvp", "g++")
) and (
    shutil.which("verilator") is not None
    or (
        campaign.TOOLS_ROOT
        / f"verilator-{campaign.PINNED_VERILATOR_VERSION}/bin/verilator"
    ).is_file()
)


def _vectors() -> dict:
    return json.loads(VECTOR_JSON.read_text(encoding="utf-8"))


def _retained_campaign() -> dict:
    return json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))


def test_vector_builder_reproduces_every_retained_image(tmp_path: Path) -> None:
    assert generator.build(["--output", str(tmp_path)]) == 0
    rebuilt = json.loads(
        (tmp_path / VECTOR_JSON.name).read_text(encoding="utf-8")
    )
    assert rebuilt == _vectors()
    for name in sorted(rebuilt["image_sha256"]):
        assert (tmp_path / name).read_bytes() == (VECTOR_DIR / name).read_bytes()


def test_witness_is_exactly_the_small_abi3_fail_stop_prefix() -> None:
    vectors = _vectors()
    assert vectors["schema"] == generator.VECTOR_SCHEMA
    assert vectors["abi"] == {"major": 3, "minor": 0}
    assert vectors["state_compat"] == 0
    assert vectors["case_count"] == 4
    assert vectors["real_engine_launch_count"] == 6
    assert vectors["result_word_count"] == 1_024
    assert vectors["resolved_view_count"] == 30
    assert vectors["capability_fault_count"] == 4
    assert [case["name"] for case in vectors["cases"]] == [
        "qwen3-8b-rom-single-chip/decode",
        "qwen3-8b-hbm-single-chip/decode",
        "deepseek-v4-flash-rom-wafer/decode",
        "deepseek-v4-flash-hbm-cluster/decode",
    ]
    assert [case["first_unsupported"] for case in vectors["cases"]] == [
        {"pc": 4, "family": 32, "sub": 3, "descriptor_id": 41,
         "trap_class": 4},
        {"pc": 4, "family": 32, "sub": 3, "descriptor_id": 54,
         "trap_class": 4},
        {"pc": 7, "family": 32, "sub": 3, "descriptor_id": 356,
         "trap_class": 4},
        {"pc": 7, "family": 32, "sub": 3, "descriptor_id": 527,
         "trap_class": 4},
    ]
    for case in vectors["cases"]:
        assert not case["expected"]["complete"]
        assert case["expected"]["state_compat"] == 0
        assert case["expected"]["retired"] + 1 == case["expected"]["fetched"]


def test_vector_and_deployment_images_are_fresh() -> None:
    vectors = campaign.load_vectors()
    assert vectors == _vectors()
    for name, expected in vectors["image_sha256"].items():
        assert campaign.sha256_file(VECTOR_DIR / name) == expected
    source = vectors["input_deployment_vectors"]
    assert campaign.sha256_file(ROOT / source["path"]) == source["sha256"]
    for name, expected in source["images"].items():
        assert campaign.sha256_file(campaign.DEPLOYMENT_VECTOR_DIR / name) == expected


def test_retained_campaign_is_current_and_states_the_simple_boundary() -> None:
    retained = _retained_campaign()
    assert CAMPAIGN_JSON.read_bytes() == (
        json.dumps(retained, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    assert retained["status"] == "pass"
    assert retained["evidence_class"] == "public_open_tool_rtl_simulation"
    assert retained["abi"] == {"major": 3, "minor": 0}
    assert retained["state_compat"] == 0
    assert retained["state_activity"] == {
        "compatibility_controller_elaborated": False,
        "configured_state_descriptor_count": 0,
        "prepare_count": 0,
        "commit_count": 0,
        "discard_count": 0,
        "read_count": 0,
        "generation_advance_count": 0,
        "commit_apply_count": 0,
        "rows_committed": 0,
        "bytes_written": 0,
        "apply_overflow_count": 0,
    }
    assert retained["post_fault_write_count"] == 0
    assert retained["simulators_agree"]
    assert retained["simulator_checks"] == {
        "iverilog": 3_289,
        "verilator": 3_289,
    }
    assert [site["pc"] for site in retained["fault_sites"]] == [4, 4, 7, 7]
    assert [site["descriptor_id"] for site in retained["fault_sites"]] == [
        41, 54, 356, 527
    ]
    for path, record in retained["source"].items():
        source_path = ROOT / path
        assert source_path.stat().st_size == record["bytes"]
        assert campaign.sha256_file(source_path) == record["sha256"], path
    assert retained["vector_set"]["sha256"] == campaign.sha256_file(VECTOR_JSON)


def test_campaign_refuses_to_overwrite_an_existing_artifact(
    tmp_path: Path,
) -> None:
    target = tmp_path / "campaign.json"
    target.write_text("{}\n", encoding="utf-8")
    assert campaign.main(["--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "{}\n"


@pytest.mark.skipif(
    not TOOLS_AVAILABLE,
    reason="Icarus, vvp, Verilator, and a C++ compiler are required",
)
def test_focused_campaign_replays_both_independent_simulators(
    tmp_path: Path,
) -> None:
    summary = campaign.run(tmp_path / "build")
    assert summary["status"] == "pass", summary["cases"]
    assert summary["simulators_agree"]
    assert summary["simulator_checks"] == {
        "iverilog": 3_289,
        "verilator": 3_289,
    }
    assert summary["post_fault_write_count"] == 0
    assert [case["name"] for case in summary["cases"]] == [
        "iverilog", "verilator"
    ]
    for simulator in summary["cases"]:
        assert simulator["status"] == "pass"
        assert simulator["compile_returncode"] == 0, simulator["compile_log"]
        assert simulator["run_returncode"] == 0, simulator["run_log"]
        assert simulator["marker_present"]
        assert simulator["observed_cases"] == summary["expected_cases"]
