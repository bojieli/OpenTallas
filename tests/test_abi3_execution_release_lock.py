"""Focused tests for the immutable ABI 3.0 execution-release boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

import pytest
from jsonschema import Draft202012Validator

from abi3_comparison_contract_support import make_locked_repository, write_json
from tools.abi3_comparison_boundary import validate_comparison_contract
from tools.freeze_abi3_execution_release import (
    SCHEMA_PATH,
    ReleaseLockError,
    build_release_lock,
    release_digest,
    validate_release_lock,
)


def _run(repo: Path, *command: str) -> None:
    subprocess.run(command, cwd=repo, check=True, capture_output=True, text=True)


def _budget(roles: tuple[str, ...]) -> dict:
    return {
        "schema": "opentallas.abi3.tpot_acceptance_budget.v1",
        "metric": "per_sequence_steady_state_decode_step_latency_seconds",
        "batch_size": 1,
        "steady_state_start_decode_step": 1,
        "roles": {
            role: {
                "maximum_seconds": 1.0,
                "statistic": "p95",
                "eligible_measurement_classes": [
                    "rtl_bound_accelerated_cosimulation"
                ],
                "assumption_dependent_evidence_allowed": False,
            }
            for role in roles
        },
    }


def _release_repository(tmp_path: Path) -> tuple[dict, Path]:
    bundle = make_locked_repository(tmp_path)
    roles = tuple(bundle["contract"]["targets"])
    bundle["contract"]["execution"]["tpot_acceptance"] = _budget(roles)
    write_json(bundle["contract_path"], bundle["contract"])
    validation = validate_comparison_contract(
        bundle["contract"], repo=tmp_path, source_path=bundle["contract_path"]
    )
    assert validation["ready"] is True

    checkpoint_lock = tmp_path / "results/source/checkpoint.lock.json"
    write_json(
        checkpoint_lock,
        {
            "schema": "opentallas.checkpoint_lock.v1",
            "lock_id": "a" * 64,
            "source": {
                "repository": "fixture/model",
                "revision": "b" * 40,
            },
        },
    )
    _run(tmp_path, "git", "init", "-q")
    _run(tmp_path, "git", "config", "user.email", "release-lock@example.invalid")
    _run(tmp_path, "git", "config", "user.name", "Release Lock Test")
    _run(tmp_path, "git", "add", "-A")
    _run(tmp_path, "git", "commit", "-qm", "fixture release")
    return bundle, checkpoint_lock


def _build(tmp_path: Path) -> tuple[dict, dict, Path]:
    bundle, checkpoint = _release_repository(tmp_path)
    document = build_release_lock(
        repo=tmp_path,
        release_id="fixture-release-b1",
        comparison_contracts=[bundle["contract_path"]],
        external_locks={"fixture_checkpoint": checkpoint},
        result_namespace="results/abi3/releases/fixture-release-b1",
    )
    return document, bundle, checkpoint


def test_release_lock_joins_clean_source_contract_budget_and_checkpoint(
    tmp_path: Path,
) -> None:
    document, bundle, checkpoint = _build(tmp_path)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)
    assert validate_release_lock(document, repo=tmp_path) == []
    assert document["abi_version"] == "3.0"
    assert document["source"]["tracked_worktree_clean"] is True
    assert document["source"]["tracked_file_count"] == len(
        document["source"]["tracked_source_map"]
    )
    assert document["comparison_contracts"][0]["comparison_id"] == (
        bundle["contract"]["comparison_id"]
    )
    assert document["comparison_contracts"][0]["batch_size"] == 1
    assert document["comparison_contracts"][0]["context_tokens"] == 3
    assert document["comparison_contracts"][0]["tpot_acceptance_sha256"]
    assert document["external_locks"][0]["path"] == (
        checkpoint.relative_to(tmp_path).as_posix()
    )
    assert document["release_sha256"] == release_digest(document)


def test_release_verification_allows_created_result_directory(
    tmp_path: Path,
) -> None:
    document, _bundle, _checkpoint = _build(tmp_path)
    (tmp_path / document["result_namespace"]["path"]).mkdir(parents=True)

    assert validate_release_lock(document, repo=tmp_path) == []


def test_release_refuses_existing_result_namespace(tmp_path: Path) -> None:
    bundle, checkpoint = _release_repository(tmp_path)
    namespace = tmp_path / "results/abi3/releases/already-used"
    namespace.mkdir(parents=True)

    with pytest.raises(ReleaseLockError, match="already exists"):
        build_release_lock(
            repo=tmp_path,
            release_id="already-used",
            comparison_contracts=[bundle["contract_path"]],
            external_locks={"fixture_checkpoint": checkpoint},
            result_namespace=namespace,
        )


def test_release_refuses_contract_without_numeric_tpot_budget(
    tmp_path: Path,
) -> None:
    bundle, checkpoint = _release_repository(tmp_path)
    del bundle["contract"]["execution"]["tpot_acceptance"]
    write_json(bundle["contract_path"], bundle["contract"])
    _run(tmp_path, "git", "add", "-A")
    _run(tmp_path, "git", "commit", "-qm", "remove performance budget")

    with pytest.raises(ReleaseLockError, match="no explicit TPOT"):
        build_release_lock(
            repo=tmp_path,
            release_id="budget-missing",
            comparison_contracts=[bundle["contract_path"]],
            external_locks={"fixture_checkpoint": checkpoint},
            result_namespace="results/abi3/releases/budget-missing",
        )


def test_release_verification_fails_closed_on_source_or_lock_drift(
    tmp_path: Path,
) -> None:
    document, _bundle, checkpoint = _build(tmp_path)
    body = json.loads(checkpoint.read_text(encoding="utf-8"))
    body["lock_id"] = "c" * 64
    write_json(checkpoint, body)

    problems = validate_release_lock(document, repo=tmp_path)
    assert "tracked worktree is not clean; freeze from one committed source snapshot" in problems
    assert "checkpoint/source locks differ from the frozen release" in problems


def test_release_self_digest_and_contract_identity_are_fail_closed(
    tmp_path: Path,
) -> None:
    document, _bundle, _checkpoint = _build(tmp_path)
    tampered = copy.deepcopy(document)
    tampered["comparison_contracts"][0]["context_tokens"] += 1

    problems = validate_release_lock(tampered, repo=tmp_path)
    assert "release_sha256 is inconsistent" in problems
    assert "comparison contracts differ from the frozen release" in problems


def test_release_refuses_duplicate_contract_identity(tmp_path: Path) -> None:
    bundle, checkpoint = _release_repository(tmp_path)

    with pytest.raises(ReleaseLockError, match="IDs are not unique"):
        build_release_lock(
            repo=tmp_path,
            release_id="duplicate-contract",
            comparison_contracts=[bundle["contract_path"], bundle["contract_path"]],
            external_locks={"fixture_checkpoint": checkpoint},
            result_namespace="results/abi3/releases/duplicate-contract",
        )


def test_release_refuses_symlinked_lock_path(tmp_path: Path) -> None:
    bundle, checkpoint = _release_repository(tmp_path)
    alias = tmp_path / "results/source/checkpoint-alias.json"
    alias.symlink_to(checkpoint.name)

    with pytest.raises(ReleaseLockError, match="may not be symlinks"):
        build_release_lock(
            repo=tmp_path,
            release_id="symlink-lock",
            comparison_contracts=[bundle["contract_path"]],
            external_locks={"fixture_checkpoint": alias},
            result_namespace="results/abi3/releases/symlink-lock",
        )
