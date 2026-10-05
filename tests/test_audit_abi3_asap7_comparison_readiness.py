"""Fail-closed guards for the W11.2 predictive-ASAP7 readiness audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from abi3_comparison_contract_support import (
    as_full_workload_boundary,
    cycle_inputs,
    make_boundary,
    make_functional_evidence,
    make_locked_repository,
    request_trajectory_rows,
    sha256_file,
    write_json,
)
from runtime.abi3.capability import canonical_json
from runtime.cycle.model import CycleRequest
from tools.abi3_comparison_boundary import (
    boundary_digest,
    request_trajectory_digest,
    validate_boundary,
)
from tools.audit_abi3_asap7_comparison_readiness import (
    REPO,
    _cycle_inventory,
    _functional_inventory,
    _load_authoritative_contracts,
    _required_functional_sources,
    assess_cycle_document,
    assess_functional_document,
    assess_machine_documents,
    build_report,
    main,
)

ARTIFACT = REPO / "results/abi3/asap7_comparison_readiness.json"
CAPABILITY_ROOT = REPO / "configs/hardware/abi3_capability"
HARDWARE_ROOT = REPO / "configs/hardware"
QWEN_ID = "qwen3_rom_single_chip_vs_hbm_single_chip"
DEEPSEEK_ID = "deepseek_v4_rom_wafer_vs_hbm_cluster_32"
WAFER_ARRAY_ID = "deepseek_v4_rom_wafer_vs_rom_array_32"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract(repo: Path, comparison_id: str = QWEN_ID) -> dict:
    return next(
        item
        for item in _load_authoritative_contracts(repo)
        if item["comparison_id"] == comparison_id
    )


def _cycle(
    bundle: dict,
    role: str = "rom",
    *,
    full: bool = True,
    generated_token_ids: list[int] | None = None,
) -> dict:
    generated = list(
        generated_token_ids
        if generated_token_ids is not None
        else bundle["oracle_generated_token_ids"]
    )
    boundary = make_boundary(bundle, role)
    trajectory_rows = request_trajectory_rows(bundle, role, len(generated))
    if full:
        boundary = as_full_workload_boundary(boundary, trajectory_rows)
    inputs = cycle_inputs(bundle, boundary)
    source_validation = validate_boundary(
        boundary,
        repo=bundle["repo"],
        cycle_inputs=inputs,
    )
    if full:
        evidence = make_functional_evidence(
            bundle,
            role,
            generated_token_ids=generated,
            aggregate_inputs=inputs,
            trajectory_rows=trajectory_rows,
        )
        workload_execution = {
            "scope": "full_workload",
            **evidence,
        }
    else:
        workload_execution = {
            "scope": "measurement_slice",
            "functional_artifact": None,
            "external_oracle": None,
        }
    return {
        "schema": "opentallas.abi3.cycle_result.v1",
        "inputs": inputs,
        "comparison_boundary": boundary,
        "comparison_boundary_validation": {
            **source_validation,
            "acceptance_checks": {"full_workload_scope": full},
            "admissible": source_validation["valid"] and full,
        },
        "workload_execution": workload_execution,
        "execution": {
            "status": "SUCCESS",
            "trap_class": "NONE",
            "transactions": len(trajectory_rows) if full else 1,
        },
        "schedule_audit": {"complete": True, "findings": []},
        "gaps": [],
        "functional_agreement": {"checked": True, "agrees": True},
        "provenance": {"class": "assumed"},
    }


def _assess(bundle: dict, body: dict, role: str = "rom") -> dict:
    assessed = assess_cycle_document(
        body,
        f"{role}.json",
        contract=_contract(bundle["repo"], bundle["contract"]["comparison_id"]),
        repo=bundle["repo"],
    )
    assert assessed is not None
    return assessed


def _rewrite_evidence(
    bundle: dict,
    body: dict,
    source: str,
    mutate,
    *,
    relock: bool = True,
) -> tuple[Path, dict]:
    record = body["workload_execution"][source]
    path = bundle["repo"] / record["path"]
    document = _json(path)
    mutate(document)
    write_json(path, document)
    if relock:
        record["sha256"] = sha256_file(path)
    return path, document


def _relock_functional_oracle_link(bundle: dict, body: dict) -> None:
    oracle_ref = body["workload_execution"]["external_oracle"]
    functional_ref = body["workload_execution"]["functional_artifact"]
    functional_path = bundle["repo"] / functional_ref["path"]
    functional = _json(functional_path)
    functional["oracle"]["artifact_sha256"] = oracle_ref["sha256"]
    write_json(functional_path, functional)
    functional_ref["sha256"] = sha256_file(functional_path)


def _rewrite_measurement(
    bundle: dict,
    body: dict,
    mutate,
    *,
    transaction_index: int = 0,
) -> tuple[Path, dict]:
    reference = body["workload_execution"]["request_trajectory"]["transactions"][
        transaction_index
    ]["measurement"]
    path = bundle["repo"] / reference["path"]
    document = _json(path)
    mutate(document)
    write_json(path, document)
    reference["sha256"] = sha256_file(path)
    return path, document


def _relock_trajectory(body: dict) -> None:
    trajectory = body["workload_execution"]["request_trajectory"]
    digest = request_trajectory_digest(trajectory["transactions"])
    trajectory["sha256"] = digest
    body["comparison_boundary"]["request_trajectory_sha256"] = digest
    body["comparison_boundary"]["boundary_sha256"] = boundary_digest(
        body["comparison_boundary"]
    )
    body["inputs"]["request_trajectory_sha256"] = digest
    body["inputs"]["comparison_boundary_digest"] = body["comparison_boundary"][
        "boundary_sha256"
    ]


def test_current_report_uses_valid_authoritative_contracts_but_pending_targets() -> None:
    report = build_report(REPO)

    assert report["schema"] == "opentallas.abi3.asap7_comparison_readiness.v1"
    assert report["gate_id"] == "TA-CMP-7-ASAP7"
    assert report["status"] == "blocked"
    assert report["ready"] is False
    acceptance = report["acceptance_contract"]
    assert acceptance["comparison_contracts_source_valid"] is True
    assert acceptance["comparison_contracts_target_sources_ready"] is False
    assert acceptance["comparison_contracts_external_oracles_ready"] is False
    assert len(acceptance["required_comparisons"]) == 3
    expected_roles = {
        QWEN_ID: {"rom", "hbm"},
        DEEPSEEK_ID: {"rom", "hbm"},
        WAFER_ARRAY_ID: {"rom", "rom_array"},
    }
    for contract in acceptance["required_comparisons"]:
        assert contract["contract_source_valid"] is True
        assert contract["contract_ready"] is False
        assert len(contract["contract_sha256"]) == 64
        lock_status = contract["target_lock_status"]
        assert set(lock_status) == expected_roles[contract["comparison_id"]]
        for role in lock_status:
            assert lock_status[role]["source_ready"] is False
    contracts = {
        item["comparison_id"]: item for item in acceptance["required_comparisons"]
    }
    assert set(contracts) == set(expected_roles)
    # The Qwen contract re-targeted its external oracle at the exact-8K chat
    # oracle with status pending (version 1.2.0); every oracle is now pending.
    assert contracts[QWEN_ID]["external_oracle_lock_status"] == "pending"
    assert contracts[QWEN_ID]["external_oracle_source_ready"] is False
    assert contracts[DEEPSEEK_ID]["external_oracle_lock_status"] == "pending"
    assert contracts[DEEPSEEK_ID]["external_oracle_source_ready"] is False
    assert contracts[WAFER_ARRAY_ID]["external_oracle_lock_status"] == "pending"
    assert contracts[WAFER_ARRAY_ID]["external_oracle_source_ready"] is False
    assert report["claim_boundary"]["cross_view_inputs_admitted"] is False
    assert report["claim_boundary"]["performance_comparison_admissible"] is False
    assert report["cycle_evidence"]["admissible_cycle_result_count"] == 0
    assert all(
        not row["admissible"]
        for row in report["cycle_evidence"]["cycle_results"]
    )

    provenance = report["provenance"]["source_sha256"]
    assert "schemas/abi3/comparison_contract_v1.schema.json" in provenance
    assert (
        "configs/abi3/comparison_contracts/"
        "qwen3_rom_single_chip_vs_hbm_single_chip_v1.json"
    ) in provenance


def test_current_report_preserves_existing_fail_closed_blockers() -> None:
    report = build_report(REPO)
    codes = {item["code"] for item in report["blockers"]}
    assert {
        "qwen_mandatory_correctness_not_closed",
        "deepseek_mandatory_accelerator_pair_missing",
        "asap7_capability_records_missing",
        "asap7_cluster_cost_model_missing",
        "asap7_wafer_cost_model_missing",
        "deepseek_wafer_array_mandatory_accelerator_pair_missing",
        "qwen_same_view_cycle_pair_missing",
        "deepseek_same_view_cycle_pair_missing",
        "deepseek_wafer_array_same_view_cycle_pair_missing",
        "cycle_workload_identity_missing",
        "asap7_engine_coverage_incomplete",
        "asap7_control_plane_missing",
        "asap7_rom_macro_missing",
        "asap7_sram_macro_missing",
        "asap7_cluster_fabric_missing",
        "asap7_wafer_fabric_missing",
        "target_area_energy_uncertainty_missing",
    } <= codes
    assert report["blocker_count"] == len(report["blockers"])


def test_machine_admission_requires_same_view_and_complete_fabric_parameters() -> None:
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

    del table["parameters"]["fabric.cluster.credits"]
    incomplete = assess_machine_documents(
        capability,
        table,
        capability_path="capability.json",
        cost_path="abi3_cost_test.json",
    )
    assert incomplete["model_complete"] is False
    assert incomplete["admissible"] is False
    assert incomplete["missing_fabric_parameters"] == ["fabric.cluster.credits"]

    other_view = _json(CAPABILITY_ROOT / "rom_qwen3.json")
    asap7 = _json(HARDWARE_ROOT / "abi3_cost_asap7_v2.json")
    refused = assess_machine_documents(
        other_view,
        asap7,
        capability_path="capability.json",
        cost_path="abi3_cost_test.json",
    )
    assert refused["checks"]["technology_view_exact"] is False
    assert refused["admissible"] is False


def test_full_workload_cycle_with_exact_contract_and_target_is_admissible(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    assessed = _assess(bundle, _cycle(bundle, "rom"))

    assert assessed["admissible"] is True
    assert assessed["failed_checks"] == []
    assert all(assessed["checks"].values())
    assert assessed["comparison_digest"] == assessed["comparison_contract_digest"]


def test_measurement_slice_boundary_is_source_valid_but_never_w11_2_admissible(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    assessed = _assess(bundle, _cycle(bundle, "rom", full=False))

    assert assessed["boundary_source_validation"]["valid"] is True
    assert assessed["admissible"] is False
    assert {
        "comparison_execution_scope_exact",
        "full_workload_scope",
        "functional_artifact_reference_complete",
        "functional_artifact_source_exact",
        "functional_workload_identity_exact",
        "generated_token_ids_valid",
        "external_oracle_reference_complete",
        "external_oracle_source_exact",
        "functional_oracle_agreement_complete",
        "execution_transactions_match_full_workload",
    } <= set(assessed["failed_checks"])


def test_omitted_generation_phase_and_terminal_evidence_is_rejected(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    body.pop("workload_execution")

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert {
        "full_workload_scope",
        "functional_artifact_reference_complete",
        "functional_artifact_source_exact",
        "generated_token_ids_valid",
        "terminal_reason_exact",
        "external_oracle_reference_complete",
        "external_oracle_source_exact",
    } <= set(assessed["failed_checks"])


@pytest.mark.parametrize(
    ("source", "expected", "mutate"),
    [
        (
            "functional_artifact",
            "functional_artifact_schema_exact",
            lambda row: row.update(schema="opentallas.abi3.wrong.v1"),
        ),
        (
            "functional_artifact",
            "functional_artifact_evidence_class_exact",
            lambda row: row.update(evidence_class="self_reported_claim"),
        ),
        (
            "functional_artifact",
            "functional_producer_exact",
            lambda row: row.update(tool="tools/not_the_accelerator_runner.py"),
        ),
        (
            "functional_artifact",
            "functional_source_map_nonempty",
            lambda row: row.pop("source_sha256"),
        ),
        (
            "functional_artifact",
            "functional_source_map_required",
            lambda row: row["source_sha256"].pop(
                "compiler/backends/rom/qwen3.py"
            ),
        ),
        (
            "functional_artifact",
            "functional_source_map_exact",
            lambda row: row["source_sha256"].update(
                {"runtime/driver.py": "0" * 64}
            ),
        ),
        (
            "functional_artifact",
            "functional_artifact_status_pass",
            lambda row: row.update(status="fail"),
        ),
        (
            "functional_artifact",
            "functional_model_identity_exact",
            lambda row: row["model"].update(graph_id="0" * 64),
        ),
        (
            "functional_artifact",
            "functional_model_identity_exact",
            lambda row: row["model"].update(numeric_profile="wrong_numeric_v1"),
        ),
        (
            "functional_artifact",
            "functional_target_identity_exact",
            lambda row: row["target"].update(backend="wrong.backend"),
        ),
        (
            "functional_artifact",
            "functional_target_sources_exact",
            lambda row: row["target"].update(deployment_digest="0" * 64),
        ),
        (
            "functional_artifact",
            "functional_target_sources_exact",
            lambda row: row["target"].update(capability_digest="0" * 64),
        ),
        (
            "functional_artifact",
            "functional_workload_identity_exact",
            lambda row: row.update(comparison_workload_sha256="0" * 64),
        ),
        (
            "functional_artifact",
            "functional_workload_identity_exact",
            lambda row: row["workload"]["template"].update(
                source_sha256="0" * 64
            ),
        ),
        (
            "functional_artifact",
            "functional_input_tokens_exact",
            lambda row: row["workload"].update(prompt_token_ids=[1, 2, 4]),
        ),
        (
            "functional_artifact",
            "functional_execution_contract_exact",
            lambda row: row["comparison_execution"].update(batch=2),
        ),
        (
            "functional_artifact",
            "generated_token_ids_valid",
            lambda row: row.update(generated_token_ids=[4, 5, True]),
        ),
        (
            "functional_artifact",
            "generated_token_ids_valid",
            lambda row: row.update(generated_token_ids=[4, 5, 8]),
        ),
        (
            "functional_artifact",
            "generated_token_count_exact",
            lambda row: row.update(generated_token_count=2),
        ),
        (
            "functional_artifact",
            "generated_token_count_within_cap",
            lambda row: row.update(generated_token_count=4),
        ),
        (
            "functional_artifact",
            "per_step_tokens_exact",
            lambda row: row["per_step"][1].update(final_token_id=6),
        ),
        (
            "functional_artifact",
            "per_step_success",
            lambda row: row["per_step"][1].update(status="FAILED"),
        ),
        (
            "functional_artifact",
            "per_step_success",
            lambda row: row["per_step"][1].update(trap="ENGINE"),
        ),
        (
            "functional_artifact",
            "per_step_phases_exact",
            lambda row: row["per_step"][0].update(phase="decode"),
        ),
        (
            "functional_artifact",
            "per_step_transactions_strict",
            lambda row: row["per_step"][0].update(transaction_id=9),
        ),
        (
            "functional_artifact",
            "terminal_reason_exact",
            lambda row: row.update(generated_token_ids=[4, 7, 5]),
        ),
        (
            "functional_artifact",
            "no_post_eos_transactions",
            lambda row: row.update(generated_token_ids=[4, 7, 5]),
        ),
        (
            "functional_artifact",
            "terminal_reason_exact",
            lambda row: row.update(stop_reason="max_new_tokens"),
        ),
        (
            "external_oracle",
            "external_oracle_schema_exact",
            lambda row: row.update(schema="opentallas.abi3.wrong_oracle.v1"),
        ),
        (
            "external_oracle",
            "external_oracle_evidence_class_exact",
            lambda row: row.update(evidence_class="accelerator_self_report"),
        ),
        (
            "external_oracle",
            "external_oracle_model_identity_exact",
            lambda row: row.update(model_id="wrong-model"),
        ),
        (
            "external_oracle",
            "external_oracle_workload_identity_exact",
            lambda row: next(iter(row["results"].values())).update(
                workload_digest="0" * 64
            ),
        ),
        (
            "external_oracle",
            "external_oracle_tokens_exact",
            lambda row: next(iter(row["results"].values())).update(
                generated_token_ids=[4, 6, 7]
            ),
        ),
        (
            "external_oracle",
            "external_oracle_tokens_exact",
            lambda row: next(iter(row["results"].values())).update(
                generated_token_count=2
            ),
        ),
    ],
)
def test_cycle_admission_reopens_and_rechecks_source_locked_evidence(
    tmp_path: Path, source: str, expected: str, mutate
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_evidence(bundle, body, source, mutate)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("functional_artifact", "functional_artifact_source_exact"),
        ("external_oracle", "external_oracle_source_exact"),
    ],
)
def test_stale_evidence_source_sha_is_rejected(
    tmp_path: Path, source: str, expected: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_evidence(
        bundle,
        body,
        source,
        lambda row: row.update(unlocked_mutation=True),
        relock=False,
    )

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


def test_functional_source_map_rehashes_every_declared_source(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    source_path = tmp_path / "runtime/driver.py"
    write_json(source_path, {"fixture_source": "tampered-after-capture"})

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert "functional_source_map_exact" in assessed["failed_checks"]


def test_functional_source_map_rejects_an_unreadable_extra_entry(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_evidence(
        bundle,
        body,
        "functional_artifact",
        lambda row: row["source_sha256"].update(
            {"runtime/does_not_exist.py": "0" * 64}
        ),
    )

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert "functional_source_map_exact" in assessed["failed_checks"]


@pytest.mark.parametrize(
    ("expected", "mutate"),
    [
        (
            "functional_oracle_link_exact",
            lambda row: row["oracle"].update(artifact_sha256="0" * 64),
        ),
        (
            "functional_oracle_agreement_complete",
            lambda row: row["oracle"].update(agreement=False),
        ),
        (
            "functional_oracle_agreement_complete",
            lambda row: row["oracle"].update(compared_tokens=2),
        ),
        (
            "functional_oracle_agreement_complete",
            lambda row: row["oracle"].update(oracle_token_count=2),
        ),
        (
            "functional_oracle_agreement_complete",
            lambda row: row["oracle"].update(first_divergence_index=1),
        ),
    ],
)
def test_functional_artifact_must_prove_complete_external_oracle_agreement(
    tmp_path: Path, expected: str, mutate
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_evidence(bundle, body, "functional_artifact", mutate)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


def test_inline_tokens_and_claim_booleans_cannot_replace_source_artifacts(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle, full=False)
    boundary = body["comparison_boundary"]
    boundary["execution_scope"] = "full_workload"
    boundary.pop("request_sha256")
    boundary["request_trajectory_sha256"] = "0" * 64
    boundary["boundary_sha256"] = boundary_digest(boundary)
    body["inputs"].pop("request")
    body["inputs"]["request_trajectory_sha256"] = "0" * 64
    body["inputs"]["comparison_execution_scope"] = "full_workload"
    body["inputs"]["comparison_boundary_digest"] = boundary["boundary_sha256"]
    body["workload_execution"].update(
        scope="full_workload",
        full_workload_consumed=True,
        terminal_condition_proved=True,
        phases_completed=["prefill", "decode"],
        generated_token_ids=[4, 5, 7],
        generated_token_count=3,
        stop_reason="eos",
    )
    body["comparison_boundary_validation"].update(
        valid=True,
        admissible=True,
        failed_checks=[],
    )

    assessed = _assess(bundle, body)
    assert assessed["boundary_source_validation"]["valid"] is True
    assert assessed["admissible"] is False
    assert {
        "functional_artifact_reference_complete",
        "functional_artifact_source_exact",
        "external_oracle_reference_complete",
        "external_oracle_source_exact",
    } <= set(assessed["failed_checks"])


def test_producer_boundary_verdict_is_not_an_admission_input(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    body["comparison_boundary_validation"] = {
        "valid": False,
        "admissible": False,
        "failed_checks": ["forged_producer_failure"],
        "acceptance_checks": {"full_workload_scope": False},
    }

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is True
    assert assessed["failed_checks"] == []


@pytest.mark.parametrize(
    ("expected", "mutate"),
    [
        ("execution_status_success", lambda body: body["execution"].update(status="FAILED")),
        ("execution_trap_none", lambda body: body["execution"].update(trap_class="ENGINE")),
        ("execution_transactions_complete", lambda body: body["execution"].update(transactions=2)),
        ("schedule_audit_complete", lambda body: body["schedule_audit"].update(complete=False)),
        ("contract_gaps_empty", lambda body: body["gaps"].append({"kind": "gap"})),
        ("functional_counter_agreement", lambda body: body["functional_agreement"].update(agrees=False)),
    ],
)
def test_cycle_admission_keeps_independent_execution_guards(
    tmp_path: Path, expected: str, mutate
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    mutate(body)
    assessed = _assess(bundle, body)

    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


@pytest.mark.parametrize(
    ("expected", "mutate"),
    [
        ("target_role_exact", lambda body: body["comparison_boundary"]["target"].update(role="hbm")),
        ("target_backend_exact", lambda body: body["inputs"].update(backend="unknown.backend")),
        ("target_id_exact", lambda body: body["inputs"].update(target_id="wrong-target")),
        ("target_storage_class_exact", lambda body: body["comparison_boundary"]["target"].update(storage_class="HBM")),
        ("topology_class_exact", lambda body: body["inputs"].update(topology_class=1)),
        ("node_count_exact", lambda body: body["inputs"].update(node_count=32)),
    ],
)
def test_cycle_admission_requires_exact_contract_target_slot(
    tmp_path: Path, expected: str, mutate
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    mutate(body)
    body["comparison_boundary"]["boundary_sha256"] = boundary_digest(
        body["comparison_boundary"]
    )
    assessed = _assess(bundle, body)

    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


def test_target_role_cannot_be_spoofed_with_rom_or_hbm_substrings(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    body["comparison_boundary"]["target"].update(
        backend="not-rom-but-contains-rom",
        target_id="hbm-looking-rom-spoof",
    )
    body["inputs"].update(
        backend="not-rom-but-contains-rom",
        target_id="hbm-looking-rom-spoof",
    )
    body["comparison_boundary"]["boundary_sha256"] = boundary_digest(
        body["comparison_boundary"]
    )

    assessed = _assess(bundle, body)
    assert assessed["role"] == "rom"
    assert assessed["admissible"] is False
    assert {
        "comparison_boundary_source_valid",
        "target_role_exact",
        "target_backend_exact",
        "target_id_exact",
    } <= set(assessed["failed_checks"])


def test_forged_producer_verdict_cannot_hide_a_stale_boundary_source(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    body["comparison_boundary"]["deployment"]["sha256"] = "0" * 64
    body["comparison_boundary"]["boundary_sha256"] = boundary_digest(
        body["comparison_boundary"]
    )
    body["comparison_boundary_validation"].update(
        valid=True,
        admissible=True,
        failed_checks=[],
    )

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert "comparison_boundary_source_valid" in assessed["failed_checks"]
    assert "deployment_source_exact" in assessed[
        "boundary_source_validation"
    ]["failed_checks"]


def test_real_8k_workload_attached_to_one_transaction_slice_is_rejected() -> None:
    contract = _contract(REPO, QWEN_ID)
    governed = contract["workload"]
    real_workload = _json(REPO / governed["path"])
    tiny_request = CycleRequest(transactions=1).to_dict()
    assert real_workload["workload_id"] == "TA-QW-8K-1"
    assert (
        real_workload["prompt_token_count"]
        == len(real_workload["token_ids"])
        == 8_000
    )
    body = {
        "schema": "opentallas.abi3.cycle_result.v1",
        "inputs": {
            "workload": {
                "workload_id": governed["workload_id"],
                "workload_digest": governed["digest"],
            },
            "request": tiny_request,
            "comparison_execution_scope": "measurement_slice",
            "comparison_contract_digest": contract["contract_sha256"],
        },
        "comparison_boundary": {"comparison_id": QWEN_ID},
        "comparison_boundary_validation": {
            "valid": True,
            "admissible": True,
            "failed_checks": [],
            "acceptance_checks": {"full_workload_scope": True},
        },
        "workload_execution": {
            "scope": "measurement_slice",
            "functional_artifact": None,
            "external_oracle": None,
        },
        "execution": {"status": "SUCCESS", "trap_class": "NONE", "transactions": 1},
        "schedule_audit": {"complete": True, "findings": []},
        "gaps": [],
        "functional_agreement": {"checked": True, "agrees": True},
    }
    assessed = assess_cycle_document(
        body,
        "forged-one-transaction.json",
        contract=contract,
        repo=REPO,
    )

    assert assessed is not None and assessed["admissible"] is False
    assert assessed["workload_id"] == "TA-QW-8K-1"
    assert {
        "comparison_boundary_source_valid",
        "acceptance_contract_target_sources_ready",
        "comparison_execution_scope_exact",
        "full_workload_scope",
        "functional_artifact_reference_complete",
        "functional_artifact_source_exact",
        "external_oracle_reference_complete",
        "external_oracle_source_exact",
        "execution_transactions_match_full_workload",
    } <= set(assessed["failed_checks"])


def test_rom_and_hbm_from_different_contracts_cannot_form_a_pair(
    tmp_path: Path,
) -> None:
    first = make_locked_repository(
        tmp_path,
        comparison_id=QWEN_ID,
        namespace="first",
    )
    second = make_locked_repository(
        tmp_path,
        comparison_id=DEEPSEEK_ID,
        namespace="second",
    )
    result_root = tmp_path / "results/abi3"
    write_json(result_root / "first-rom.json", _cycle(first, "rom"))
    write_json(result_root / "second-hbm.json", _cycle(second, "hbm"))

    inventory, _ = _cycle_inventory(
        tmp_path,
        _load_authoritative_contracts(tmp_path),
    )
    assert inventory["comparisons"][QWEN_ID]["ready"] is False
    assert inventory["comparisons"][DEEPSEEK_ID]["ready"] is False
    assert inventory["comparisons"][QWEN_ID]["admissible_candidate_counts"] == {
        "rom": 1,
        "hbm": 0,
    }
    assert inventory["comparisons"][DEEPSEEK_ID]["admissible_candidate_counts"] == {
        "rom": 0,
        "hbm": 1,
    }


def test_one_exact_pair_is_ready_only_with_distinct_target_and_deployment_ids(
    tmp_path: Path,
) -> None:
    first = make_locked_repository(
        tmp_path,
        comparison_id=QWEN_ID,
        namespace="first",
    )
    result_root = tmp_path / "results/abi3"
    write_json(result_root / "rom.json", _cycle(first, "rom"))
    write_json(result_root / "hbm.json", _cycle(first, "hbm"))

    inventory, _ = _cycle_inventory(tmp_path, [_contract(tmp_path, QWEN_ID)])
    pair = inventory["comparisons"][QWEN_ID]
    assert pair["ready"] is True
    assert pair["admissible_candidate_counts"] == {"rom": 1, "hbm": 1}


def test_rom_versus_rom_pair_is_matched_by_the_roles_its_contract_declares(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(
        tmp_path,
        comparison_id=WAFER_ARRAY_ID,
        namespace="packaging",
        roles=("rom", "rom_array"),
    )
    result_root = tmp_path / "results/abi3"
    write_json(result_root / "rom.json", _cycle(bundle, "rom"))
    write_json(result_root / "rom_array.json", _cycle(bundle, "rom_array"))

    contract = _contract(tmp_path, WAFER_ARRAY_ID)
    assert set(contract["target_lock_status"]) == {"rom", "rom_array"}
    inventory, _ = _cycle_inventory(tmp_path, [contract])
    pair = inventory["comparisons"][WAFER_ARRAY_ID]
    assert pair["admissible_candidate_counts"] == {"rom": 1, "rom_array": 1}
    assert pair["matched_pair"] == {
        "rom": "results/abi3/rom.json",
        "rom_array": "results/abi3/rom_array.json",
    }
    assert pair["ready"] is True
    assert pair["strict_functional_candidate_counts"] == {"rom": 1, "rom_array": 1}
    assert pair["functional_ready"] is True

    # An HBM-shaped record cannot occupy either ROM slot of this pair.
    for row in inventory["cycle_results"]:
        assert row["role"] in {"rom", "rom_array"}
        assert row["checks"]["target_role_exact"] is True


def test_rom_versus_rom_pair_refuses_two_records_on_the_same_rom_slot(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(
        tmp_path,
        comparison_id=WAFER_ARRAY_ID,
        namespace="packaging",
        roles=("rom", "rom_array"),
    )
    result_root = tmp_path / "results/abi3"
    write_json(result_root / "rom.json", _cycle(bundle, "rom"))
    write_json(result_root / "rom-again.json", _cycle(bundle, "rom"))

    inventory, _ = _cycle_inventory(tmp_path, [_contract(tmp_path, WAFER_ARRAY_ID)])
    pair = inventory["comparisons"][WAFER_ARRAY_ID]
    assert pair["admissible_candidate_counts"] == {"rom": 2, "rom_array": 0}
    assert pair["matched_pair"] is None
    assert pair["ready"] is False


def test_pair_refuses_different_generated_token_sequences(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    result_root = tmp_path / "results/abi3"
    write_json(result_root / "rom.json", _cycle(bundle, "rom"))
    write_json(
        result_root / "hbm.json",
        _cycle(bundle, "hbm", generated_token_ids=[4, 6, 7]),
    )

    inventory, _ = _cycle_inventory(tmp_path, [_contract(tmp_path, QWEN_ID)])
    pair = inventory["comparisons"][QWEN_ID]
    assert pair["admissible_candidate_counts"] == {"rom": 1, "hbm": 0}
    assert pair["matched_pair"] is None
    assert pair["ready"] is False


def test_pair_refuses_different_external_oracle_source_digest(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    rom = _cycle(bundle, "rom")
    hbm = _cycle(bundle, "hbm")
    governed_oracle = bundle["repo"] / bundle["contract"]["external_oracle"]["path"]
    alternate_oracle = _json(governed_oracle)
    alternate_oracle["producer_build_id"] = "run-chosen-fabricated-oracle"
    alternate_path = tmp_path / "results/abi3/run-chosen-oracle.json"
    write_json(alternate_path, alternate_oracle)
    hbm["workload_execution"]["external_oracle"].update(
        path=alternate_path.relative_to(tmp_path).as_posix(),
        sha256=sha256_file(alternate_path),
    )
    _relock_functional_oracle_link(bundle, hbm)
    result_root = tmp_path / "results/abi3"
    write_json(result_root / "rom.json", rom)
    write_json(result_root / "hbm.json", hbm)

    inventory, _ = _cycle_inventory(tmp_path, [_contract(tmp_path, QWEN_ID)])
    pair = inventory["comparisons"][QWEN_ID]
    assert pair["admissible_candidate_counts"] == {"rom": 1, "hbm": 0}
    assert pair["matched_pair"] is None
    assert pair["ready"] is False


def test_functional_eos_label_cannot_hide_a_shortened_or_nonterminal_run() -> None:
    contract = _contract(REPO, QWEN_ID)
    body = _json(REPO / "results/abi3/qwen3_rom_ta-qw-8k-1_execution.json")
    body["record"]["stop_reason"] = "eos"
    assessed = assess_functional_document(body, "functional.json", contract)

    assert assessed is not None and assessed["admissible"] is False
    assert assessed["checks"]["mandatory_completion_closed"] is False
    assert assessed["checks"]["declared_run_max_new_tokens_exact"] is False


def test_auditor_functional_source_boundary_matches_the_producer_exactly() -> None:
    from tools.run_accelerator_tokens import _functional_source_sha256

    cases = (
        (QWEN_ID, "rom", "rom_qwen3"),
        (QWEN_ID, "hbm", "hbm_sram"),
        (DEEPSEEK_ID, "rom", "rom_deepseek_v4"),
        (DEEPSEEK_ID, "hbm", "hbm_sram"),
        (WAFER_ARRAY_ID, "rom", "rom_deepseek_v4"),
        (WAFER_ARRAY_ID, "rom_array", "rom_deepseek_v4_array"),
    )
    for comparison_id, role, backend in cases:
        assert _required_functional_sources(REPO, comparison_id, role) == set(
            _functional_source_sha256(backend)
        )


@pytest.mark.parametrize(
    "missing",
    [
        "runtime/driver.py",
        "runtime/sim/engines/tensor.py",
        "compiler/backends/rom/common/program.py",
    ],
)
def test_functional_source_map_rejects_missing_common_engine_and_backend_sources(
    tmp_path: Path, missing: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_evidence(
        bundle,
        body,
        "functional_artifact",
        lambda row: row["source_sha256"].pop(missing),
    )

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert "functional_source_map_required" in assessed["failed_checks"]


def test_functional_source_map_rejects_even_a_readable_extra_source(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    extra = tmp_path / "runtime/readable_but_ungoverned.py"
    write_json(extra, {"fixture": "not in producer boundary"})
    _rewrite_evidence(
        bundle,
        body,
        "functional_artifact",
        lambda row: row["source_sha256"].update(
            {extra.relative_to(tmp_path).as_posix(): sha256_file(extra)}
        ),
    )

    assessed = _assess(bundle, body)
    assert assessed["checks"]["functional_source_map_exact"] is True
    assert assessed["checks"]["functional_source_map_required"] is False
    assert assessed["admissible"] is False


def test_legitimate_one_step_prefill_eos_is_admissible(tmp_path: Path) -> None:
    bundle = make_locked_repository(
        tmp_path,
        oracle_generated_token_ids=[7],
        oracle_stop_reason="eos",
    )

    assessed = _assess(bundle, _cycle(bundle))
    assert assessed["admissible"] is True
    assert assessed["checks"]["per_step_phases_exact"] is True
    assert assessed["workload_execution"]["request_trajectory"]["transactions"][0][
        "phase"
    ] == "prefill"


def test_legitimate_one_step_prefill_at_cap_one_is_admissible(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(
        tmp_path,
        max_new_tokens=1,
        oracle_generated_token_ids=[4],
        oracle_stop_reason="max_new_tokens",
    )

    assessed = _assess(bundle, _cycle(bundle))
    assert assessed["admissible"] is True
    assert assessed["checks"]["terminal_reason_exact"] is True


def test_every_step_after_prefill_must_be_decode(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_evidence(
        bundle,
        body,
        "functional_artifact",
        lambda row: row["per_step"][1].update(phase="prefill"),
    )

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert "per_step_phases_exact" in assessed["failed_checks"]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda row: row.pop("timing"), "cycle_measurement_timing_valid"),
        (lambda row: row.pop("rates"), "cycle_measurement_throughput_valid"),
        (lambda row: row.pop("counters"), "cycle_measurement_counters_valid"),
        (lambda row: row.pop("memory"), "cycle_measurement_memory_valid"),
        (lambda row: row.pop("engines"), "cycle_measurement_utilisation_valid"),
        (
            lambda row: row["timing"].pop("stall_cycles"),
            "cycle_measurement_stalls_valid",
        ),
    ],
)
def test_each_source_measurement_dimension_is_mandatory(
    tmp_path: Path, mutate, expected: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_measurement(bundle, body, mutate)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda row: row["producer"].update(tool="tools/not_the_cycle_runner.py"),
            "cycle_measurement_producer_source_valid",
        ),
        (
            lambda row: row["producer"].update(source_sha256="0" * 64),
            "cycle_measurement_producer_source_valid",
        ),
        (
            lambda row: row["producer"].update(evidence_class="self_reported"),
            "cycle_measurement_producer_source_valid",
        ),
        (
            lambda row: row["provenance"].update({"class": "self_reported"}),
            "cycle_measurement_provenance_source_valid",
        ),
    ],
)
def test_each_source_measurement_binds_exact_producer_and_provenance(
    tmp_path: Path, mutate, expected: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_measurement(bundle, body, mutate)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert assessed["functional_evidence_admissible"] is False
    assert expected in assessed["failed_checks"]


def test_empty_cycle_measurement_shell_is_rejected(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    reference = body["workload_execution"]["request_trajectory"]["transactions"][0][
        "measurement"
    ]
    path = tmp_path / reference["path"]
    write_json(path, {"schema": "opentallas.abi3.cycle_result.v1"})
    reference["sha256"] = sha256_file(path)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert {
        "cycle_measurement_timing_valid",
        "cycle_measurement_throughput_valid",
        "cycle_measurement_counters_valid",
        "cycle_measurement_memory_valid",
        "cycle_measurement_utilisation_valid",
        "cycle_measurement_stalls_valid",
    } <= set(assessed["failed_checks"])


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda row: row["timing"].update(total_cycles=-1),
            "cycle_measurement_timing_valid",
        ),
        (
            lambda row: row["rates"][0].update(value=-1),
            "cycle_measurement_throughput_valid",
        ),
        (
            lambda row: row["memory"]["rom"].update(bytes_read=-1),
            "cycle_measurement_memory_valid",
        ),
        (
            lambda row: row["engines"]["tensor"].update(utilisation=float("inf")),
            "cycle_measurement_utilisation_valid",
        ),
        (
            lambda row: row["timing"].update(seconds=1.0),
            "cycle_measurement_timing_valid",
        ),
    ],
)
def test_measurements_reject_negative_infinite_and_inconsistent_values(
    tmp_path: Path, mutate, expected: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    if expected == "cycle_measurement_utilisation_valid":
        reference = body["workload_execution"]["request_trajectory"]["transactions"][
            0
        ]["measurement"]
        path = tmp_path / reference["path"]
        document = _json(path)
        mutate(document)
        path.write_text(json.dumps(document, sort_keys=True, allow_nan=True) + "\n")
        reference["sha256"] = sha256_file(path)
    else:
        _rewrite_measurement(bundle, body, mutate)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda row: row["timing"].update(stall_cycles=3.0),
            "cycle_measurement_stalls_valid",
        ),
        (
            lambda row: row["memory"]["rom"].update(accesses=1.0),
            "cycle_measurement_memory_valid",
        ),
        (
            lambda row: row["memory"]["rom"].update(bytes_read=True),
            "cycle_measurement_memory_valid",
        ),
        (
            lambda row: row["engines"]["tensor"].update(operations=1.0),
            "cycle_measurement_utilisation_valid",
        ),
        (
            lambda row: row["engines"]["tensor"].update(utilisation=0.5),
            "cycle_measurement_utilisation_valid",
        ),
    ],
)
def test_measurement_counts_are_exact_integers_and_utilisation_is_consistent(
    tmp_path: Path, mutate, expected: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    _rewrite_measurement(bundle, body, mutate)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert assessed["functional_evidence_admissible"] is False
    assert expected in assessed["failed_checks"]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda request: request.update(entrypoint_id=999),
            "request_trajectory_entrypoints_exact",
        ),
        (
            lambda request: request.update(generation_policy_id=123),
            "request_trajectory_generation_policies_exact",
        ),
        (
            lambda request: request["symbols"].update(POSITION_END=999),
            "request_trajectory_dynamic_symbols_exact",
        ),
        (
            lambda request: request["symbols"].update(UNRELATED=1),
            "request_trajectory_request_shape_exact",
        ),
    ],
)
def test_request_trajectory_rejects_arbitrary_ids_and_symbols(
    tmp_path: Path, mutate, expected: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = _cycle(bundle)
    request = body["workload_execution"]["request_trajectory"]["transactions"][0][
        "request"
    ]
    mutate(request)
    _relock_trajectory(body)

    assessed = _assess(bundle, body)
    assert assessed["admissible"] is False
    assert expected in assessed["failed_checks"]


def test_rom_and_hbm_with_different_semantic_trajectories_do_not_pair(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    rom = _cycle(bundle, "rom")
    hbm = _cycle(bundle, "hbm")
    hbm_request = hbm["workload_execution"]["request_trajectory"]["transactions"][
        1
    ]["request"]
    hbm_request["symbols"]["POSITION_END"] += 1
    _relock_trajectory(hbm)
    assert rom["inputs"]["request_trajectory_sha256"] != hbm["inputs"][
        "request_trajectory_sha256"
    ]
    write_json(tmp_path / "results/abi3/rom.json", rom)
    write_json(tmp_path / "results/abi3/hbm.json", hbm)

    inventory, _ = _cycle_inventory(tmp_path, [_contract(tmp_path, QWEN_ID)])
    pair = inventory["comparisons"][QWEN_ID]
    assert pair["matched_pair"] is None
    assert pair["strict_functional_matched_pair"] is None
    assert pair["ready"] is False
    assert pair["functional_ready"] is False


def test_legacy_reference_agreement_is_diagnostic_only(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    contract = _contract(tmp_path, QWEN_ID)
    target = bundle["contract"]["targets"]["rom"]
    legacy = {
        "schema": "opentallas.abi3.accelerator_tokens.v1",
        "status": "pass",
        "workload": {
            "workload_id": contract["workload_id"],
            "model_id": contract["model_id"],
            "graph_id": contract["model_digest"],
            "numeric_profile": contract["numeric_profile"],
            "workload_digest": contract["workload_digest"],
            "prompt_token_count": contract["prompt_token_count"],
            "max_new_tokens": contract["max_new_tokens"],
            "tokenizer_sha256": contract["tokenizer_sha256"],
        },
        "target": {
            "backend": target["backend"],
            "target_id": target["target_id"],
            "topology_class": target["topology_class"],
            "node_count": target["node_count"],
        },
        "generated_token_ids": [4, 5, 7],
        "generated_token_count": 3,
        "stop_reason": "eos",
        "oracle": {"agreement": True},
    }
    write_json(tmp_path / "results/abi3/forged-legacy.json", legacy)

    inventory, _, _ = _functional_inventory(tmp_path, [contract])
    row = inventory[QWEN_ID]
    assert row["legacy_matching_pair"] is None
    assert row["diagnostic_only"] is True
    assert row["ready"] is False


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


def test_makefile_and_checklist_keep_the_gate_explicit_and_open() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "abi3-comparison-asap7-readiness:" in makefile
    assert "abi3-comparison-asap7-gate:" in makefile
    assert "--check --require-ready" in makefile

    checklist = (REPO / "docs/UNIFIED_EXECUTION_CHECKLIST.md").read_text(
        encoding="utf-8"
    )
    assert "- [ ] W11.2 TA-CMP-7-ASAP7" in checklist
    assert "results/abi3/asap7_comparison_readiness.json" in checklist
    assert "preflight status is `blocked`" in checklist
