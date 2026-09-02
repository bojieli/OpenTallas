"""Fail-closed guards for the W11.2 predictive-ASAP7 readiness audit."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from runtime.abi3.capability import canonical_json
from tools.audit_abi3_asap7_comparison_readiness import (
    COMPARISON_CONTRACTS,
    REPO,
    assess_cycle_document,
    assess_functional_document,
    assess_machine_documents,
    build_report,
    main,
)


ARTIFACT = REPO / "results" / "abi3" / "asap7_comparison_readiness.json"
CAPABILITY_ROOT = REPO / "configs" / "hardware" / "abi3_capability"
HARDWARE_ROOT = REPO / "configs" / "hardware"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cycle() -> dict:
    return {
        "schema": "opentallas.abi3.cycle_result.v1",
        "inputs": {
            "backend": "rom.single_chip",
            "target_id": "qwen3-8b-rom-single-chip",
            "capability_technology_view": "asap7",
            "cost_table": {
                "cost_table_id": "test-asap7",
                "technology_view": "asap7",
            },
            "workload": {
                "workload_id": "TA-QW-8K-1",
                "workload_digest": "workload-digest",
            },
            "comparison_boundary_digest": "boundary-digest",
            "topology_class": 0,
            "node_count": 1,
            "request": {"transactions": 1, "symbols": {"BATCH": 1}},
        },
        "execution": {
            "status": "SUCCESS",
            "trap_class": "NONE",
            "transactions": 1,
        },
        "schedule_audit": {"complete": True, "findings": []},
        "gaps": [],
        "functional_agreement": {"checked": True, "agrees": True},
        "provenance": {"class": "assumed"},
    }


def test_current_full_scope_audit_is_blocked_without_cross_view_mixing() -> None:
    report = build_report(REPO)

    assert report["schema"] == "opentallas.abi3.asap7_comparison_readiness.v1"
    assert report["gate_id"] == "TA-CMP-7-ASAP7"
    assert report["status"] == "blocked"
    assert report["ready"] is False
    assert report["claim_boundary"]["cross_view_inputs_admitted"] is False
    assert report["claim_boundary"]["performance_comparison_admissible"] is False

    codes = {item["code"] for item in report["blockers"]}
    assert {
        "qwen_mandatory_correctness_not_closed",
        "deepseek_mandatory_accelerator_pair_missing",
        "asap7_capability_records_missing",
        "asap7_cluster_cost_model_missing",
        "asap7_wafer_cost_model_missing",
        "qwen_same_view_cycle_pair_missing",
        "deepseek_same_view_cycle_pair_missing",
        "cycle_workload_identity_missing",
        "asap7_engine_coverage_incomplete",
        "asap7_control_plane_missing",
        "asap7_rom_macro_missing",
        "asap7_sram_macro_missing",
        "asap7_cluster_fabric_missing",
        "asap7_wafer_fabric_missing",
        "target_area_energy_uncertainty_missing",
    } <= codes

    assert all(
        not row["admissible"]
        for row in report["cycle_evidence"]["cycle_results"]
    )
    assert all(
        not row["admissible"]
        or (
            row["capability_technology_view"] == "asap7"
            and row["cost_table_technology_view"] == "asap7"
        )
        for row in report["capability_and_cost_model"]["compatibility_matrix"]
    )


def test_current_audit_names_exact_topology_and_physical_gaps() -> None:
    report = build_report(REPO)
    support = report["capability_and_cost_model"]["topology_support"]

    assert support["single_chip"]["model_complete_with_an_asap7_table"] is True
    assert support["cluster_32"]["model_complete_with_an_asap7_table"] is False
    assert "fabric.cluster.link_bytes_per_cycle" in support["cluster_32"][
        "missing_fabric_parameters"
    ]
    assert support["wafer"]["model_complete_with_an_asap7_table"] is False
    assert "fabric.wafer.stitch_bytes_per_cycle" in support["wafer"][
        "missing_fabric_parameters"
    ]

    physical = report["physical_evidence"]
    assert physical["engine_families_covered"] == ["reduction", "tensor", "vector"]
    assert physical["engine_families_missing"] == [
        "attention",
        "dma",
        "link",
        "route",
        "selection",
        "state",
    ]
    assert physical["rom_macro_characterized"] is False
    assert physical["sram_macro_characterized"] is False
    assert physical["full_qwen_targets_characterized"] is False
    assert physical["full_deepseek_targets_characterized"] is False


def test_machine_admission_refuses_a_missing_same_view_fabric_parameter() -> None:
    capability = _json(CAPABILITY_ROOT / "hbm_sram_cluster_32.json")
    capability["technology_view"] = "asap7"
    table = _json(HARDWARE_ROOT / "abi3_cost_cluster32_v2.json")
    table["technology_view"] = "asap7"

    complete = assess_machine_documents(
        capability,
        table,
        capability_path="capability.json",
        cost_path="abi3_cost_test.json",
    )
    assert complete["model_complete"] is True
    assert complete["same_view"] is True
    assert complete["admissible"] is True

    incomplete = copy.deepcopy(table)
    del incomplete["parameters"]["fabric.cluster.credits"]
    refused = assess_machine_documents(
        capability,
        incomplete,
        capability_path="capability.json",
        cost_path="abi3_cost_test.json",
    )
    assert refused["model_complete"] is False
    assert refused["admissible"] is False
    assert refused["missing_fabric_parameters"] == ["fabric.cluster.credits"]
    assert refused["checks"]["fabric.cluster"] is False
    assert any(
        "fabric.cluster.credits" in item["message"] for item in refused["errors"]
    )


def test_machine_admission_refuses_an_other_view_capability() -> None:
    capability = _json(CAPABILITY_ROOT / "rom_qwen3.json")
    table = _json(HARDWARE_ROOT / "abi3_cost_asap7_v2.json")
    assessed = assess_machine_documents(
        capability,
        table,
        capability_path="capability.json",
        cost_path="abi3_cost_test.json",
    )

    assert assessed["model_complete"] is True
    assert assessed["same_view"] is False
    assert assessed["checks"]["technology_view_exact"] is False
    assert assessed["admissible"] is False


def test_cycle_admission_requires_both_views_and_structured_boundaries() -> None:
    contract = COMPARISON_CONTRACTS[0]
    admitted = assess_cycle_document(_cycle(), "cycle.json", contract=contract)
    assert admitted is not None and admitted["admissible"] is True

    mixed = _cycle()
    mixed["inputs"]["cost_table"]["technology_view"] = "cluster32"
    refused = assess_cycle_document(mixed, "cycle.json", contract=contract)
    assert refused is not None and refused["admissible"] is False
    assert refused["failed_checks"] == ["cost_table_view_exact"]

    anonymous = _cycle()
    del anonymous["inputs"]["workload"]["workload_digest"]
    del anonymous["inputs"]["comparison_boundary_digest"]
    refused = assess_cycle_document(anonymous, "cycle.json", contract=contract)
    assert refused is not None and refused["admissible"] is False
    assert set(refused["failed_checks"]) == {
        "workload_digest_present",
        "comparison_boundary_digest_present",
    }


def test_cycle_admission_refuses_failed_execution_and_wrong_topology() -> None:
    contract = COMPARISON_CONTRACTS[0]
    failed = _cycle()
    failed["execution"]["status"] = "FAILED"
    refused = assess_cycle_document(failed, "cycle.json", contract=contract)
    assert refused is not None and refused["admissible"] is False
    assert refused["failed_checks"] == ["execution_status_success"]

    wrong_topology = _cycle()
    wrong_topology["inputs"]["topology_class"] = 1
    wrong_topology["inputs"]["node_count"] = 32
    refused = assess_cycle_document(
        wrong_topology, "cycle.json", contract=contract
    )
    assert refused is not None and refused["admissible"] is False
    assert set(refused["failed_checks"]) == {
        "topology_class_exact",
        "node_count_exact",
    }


def test_functional_eos_cannot_hide_a_shortened_governed_run() -> None:
    contract = build_report(REPO)["acceptance_contract"][
        "required_comparisons"
    ][0]
    body = _json(REPO / "results" / "abi3" / "qwen3_rom_ta-qw-8k-1_execution.json")
    body["record"]["stop_reason"] = "eos_token"
    assessed = assess_functional_document(body, "functional.json", contract)

    assert assessed is not None and assessed["admissible"] is False
    assert assessed["checks"]["mandatory_completion_closed"] is True
    assert assessed["checks"]["declared_run_max_new_tokens_exact"] is False


def test_require_ready_returns_nonzero_but_still_writes_the_audit(
    tmp_path: Path,
) -> None:
    output = tmp_path / "readiness.json"
    assert main(["--output", str(output), "--require-ready"]) == 2
    report = _json(output)
    assert report["status"] == "blocked"
    assert report["blocker_count"] == len(report["blockers"])


def test_checked_in_artifact_is_byte_reproducible() -> None:
    assert ARTIFACT.read_bytes() == canonical_json(build_report(REPO))


def test_makefile_exposes_generation_and_strict_gate_without_umbrella_wiring() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "abi3-comparison-asap7-readiness:" in makefile
    assert "abi3-comparison-asap7-gate:" in makefile
    assert "--check --require-ready" in makefile
    assert (
        "abi3: abi3-spec abi3-test abi3-engines abi3-status "
        "abi3-cost-tables-check"
    ) in makefile


def test_checklist_keeps_w11_2_open_and_points_to_the_blocked_audit() -> None:
    checklist = (REPO / "docs" / "UNIFIED_EXECUTION_CHECKLIST.md").read_text(
        encoding="utf-8"
    )
    assert "- [ ] W11.2 TA-CMP-7-ASAP7" in checklist
    assert "results/abi3/asap7_comparison_readiness.json" in checklist
    assert "preflight status is `blocked`" in checklist
    assert "#blocker_count" in checklist
    assert "fail-closed blockers" in checklist
