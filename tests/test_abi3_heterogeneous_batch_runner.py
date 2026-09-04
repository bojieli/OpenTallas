"""Focused Gate-1 tests for the governed heterogeneous ABI 3.0 runner."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable

import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from runtime.abi3.capability import canonical_json
from runtime.abi3.constants import StorageClass
from runtime.abi3.fixture import FIXTURE_VOCAB, build_fixture, fixture_capability
from tools import run_abi3_heterogeneous_batch as runner


REPO = Path(__file__).resolve().parents[1]
BASELINE_COST = REPO / "configs/hardware/abi3_cost_baseline_v1.json"
PROMPTS = ([1], [2], [3], [4], [5], [6], [1, 2], [2, 1])


def _write_json(path: Path, body: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(body))


def _read_json(path: Path) -> dict[str, Any]:
    body = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(body, dict)
    return body


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _identity(path: Path, repo: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(repo).as_posix(),
        "sha256": _sha256(path),
    }


def _tokenizer(path: Path) -> Tokenizer:
    tokenizer = Tokenizer(
        WordLevel(
            vocab={f"w{token}": token for token in range(FIXTURE_VOCAB)},
            unk_token="w0",
        )
    )
    tokenizer.pre_tokenizer = Whitespace()
    path.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(str(path))
    return tokenizer


def _fixture_repository(tmp_path: Path, batch_size: int) -> dict[str, Any]:
    repo = tmp_path / "governed-repository"
    repo.mkdir()

    capability = fixture_capability()
    capability.limits = {**capability.limits, "max_sessions": 8}
    capability.technology_view = "generic"
    capability.validate()
    capability_path = repo / "inputs/capability.json"
    _write_json(capability_path, capability.to_dict())

    deployment = build_fixture(
        storage_class=StorageClass.HBM,
        capability=capability,
    )
    deployment_root = repo / "compiled/deployment"
    deployment.write(deployment_root)

    cost_path = repo / "inputs/abi3_cost_fixture.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BASELINE_COST, cost_path)
    checkpoint_root = repo / "checkpoint"
    checkpoint_root.mkdir()
    checkpoint_lock_path = repo / "inputs/checkpoint-lock.json"
    _write_json(
        checkpoint_lock_path,
        {
            "schema": "opentallas.checkpoint_lock.v1",
            "lock_id": "fixture-zero-sources",
        },
    )
    tokenizer_path = repo / "inputs/tokenizer.json"
    tokenizer = _tokenizer(tokenizer_path)
    tokenizer_sha256 = _sha256(tokenizer_path)

    sequences: list[dict[str, Any]] = []
    workload_paths: list[Path] = []
    reference_paths: list[Path] = []
    for lane in range(batch_size):
        prompt = list(PROMPTS[lane])
        cap = lane + 1
        rendered = tokenizer.decode(prompt, skip_special_tokens=False)
        workload: dict[str, Any] = {
            "workload_id": f"fixture-workload-{lane}",
            "kind": "chat" if lane % 2 == 0 else "agent",
            "token_ids": prompt,
            "prompt_token_count": len(prompt),
            "max_new_tokens": cap,
            "rendered_text": rendered,
            "rendered_text_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
        }
        workload["digest"] = runner._workload_digest(workload)
        workload_path = repo / f"inputs/workload-{lane}.json"
        _write_json(workload_path, workload)

        gold = [0] * cap
        reference = {
            "schema": "opentallas.abi3.reference_oracle.v1",
            "model_id": "abi3-fixture",
            "tokenizer_sha256": tokenizer_sha256,
            "results": {
                workload["workload_id"]: {
                    "workload_digest": workload["digest"],
                    "prompt_token_count": len(prompt),
                    "generated_token_ids": gold,
                    "generated_token_count": len(gold),
                    "stop_reason": "max_new_tokens",
                    "raw_decoded_text": tokenizer.decode(
                        gold, skip_special_tokens=False
                    ),
                    "visible_decoded_text": tokenizer.decode(
                        gold, skip_special_tokens=True
                    ),
                }
            },
        }
        reference_path = repo / f"inputs/reference-{lane}.json"
        _write_json(reference_path, reference)
        workload_paths.append(workload_path)
        reference_paths.append(reference_path)
        sequences.append(
            {
                "sequence_id": f"fixture-sequence-{lane}",
                "terminal_contract": "exact_eos_or_cap",
                "workload": _identity(workload_path, repo),
                "reference": _identity(reference_path, repo),
            }
        )

    request = {
        "schema": runner.REQUEST_SCHEMA,
        "abi_version": "3.0",
        "campaign_id": f"fixture-b{batch_size}",
        "execution_scope": "fixture",
        "batch_size": batch_size,
        "model": {
            "model_id": "abi3-fixture",
            "graph_id": None,
            "numeric_profile": None,
        },
        "target": {
            "role": "hbm",
            "target_id": deployment.target_id,
            "backend": deployment.backend,
            "topology_class": int(deployment.topology_class),
            "node_count": 1,
            "technology_view": capability.technology_view,
        },
        "capability": _identity(capability_path, repo),
        "cost_table": _identity(cost_path, repo),
        "checkpoint_lock": _identity(checkpoint_lock_path, repo),
        "checkpoint_root": checkpoint_root.relative_to(repo).as_posix(),
        "tokenizer": _identity(tokenizer_path, repo),
        "deployment": {
            "manifest": _identity(deployment_root / "deployment.json", repo),
            "descriptors": _identity(deployment_root / "descriptors.bin", repo),
            "program": _identity(deployment_root / "program.bin", repo),
        },
        "sequences": sequences,
    }
    request_path = repo / "requests/batch.json"
    _write_json(request_path, request)
    return {
        "repo": repo,
        "request": request,
        "request_path": request_path,
        "output": repo / "results/batch",
        "tokenizer": tokenizer,
        "tokenizer_path": tokenizer_path,
        "workload_paths": workload_paths,
        "reference_paths": reference_paths,
    }


def _rewrite_request(case: dict[str, Any]) -> None:
    _write_json(case["request_path"], case["request"])


def _rewrite_input(
    case: dict[str, Any],
    lane: int,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    path = case[f"{name}_paths"][lane]
    body = _read_json(path)
    mutate(body)
    _write_json(path, body)
    case["request"]["sequences"][lane][name] = _identity(path, case["repo"])
    _rewrite_request(case)
    return body


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value))
    return set()


@pytest.mark.parametrize("batch_size", [1, 2, 4, 8])
def test_fixture_batch_preserves_exact_gate1_and_raw_ticks(
    tmp_path: Path, batch_size: int
) -> None:
    case = _fixture_repository(tmp_path, batch_size)

    body, execution_path = runner.execute_request_file(
        case["request_path"],
        repo=case["repo"],
        output_directory=case["output"],
    )

    assert execution_path == case["output"] / "batch-execution.json"
    assert _read_json(execution_path) == body
    assert body["status"] == "pass"
    assert body["physical_batch_size"] == batch_size
    assert body["shared_execution"]["deployment_loaded_once"] is True
    assert body["shared_execution"]["one_physical_batch"] is True
    assert body["shared_execution"]["wave_count"] == batch_size
    assert body["shared_execution"]["oracle_values_supplied_to_device"] is False
    assert body["shared_execution"]["shared_immutable_weights_and_constants"] is True
    assert body["shared_execution"]["shared_immutable_object_ids"]
    memory = body["shared_execution"]["memory_contract"]
    assert memory["immutable_objects_are_shared"] is True
    assert memory["mutable_objects_are_session_private"] is True

    gate1 = body["acceptance_gates"]["gate1_correctness"]
    assert gate1 == {
        "status": "pass",
        "all_sequences_exact": True,
        "shared_execution_exact": True,
        "source_stable_during_execution": True,
        "full_model_execution": False,
        "production_qualified": False,
    }
    assert body["acceptance_gates"]["gate2_tpot"] == {
        "status": "blocked",
        "consumer": runner.TPOT_CONSUMER,
        "consumer_report": None,
        "exact_execution_consumer_acceptance_required": True,
        "raw_token_commit_ticks_retained": True,
        "target_performance_metrics_published": False,
    }

    assert len({row["sequence_id"] for row in body["sequences"]}) == batch_size
    assert len({row["workload"]["file"]["path"] for row in body["sequences"]}) == batch_size
    assert len({row["workload"]["digest"] for row in body["sequences"]}) == batch_size
    assert len(
        {row["workload"]["prompt_token_ids_sha256"] for row in body["sequences"]}
    ) == batch_size
    assert len({row["oracle"]["result_sha256"] for row in body["sequences"]}) == batch_size

    batch_ids: set[str] = set()
    deployment_ids: set[str] = set()
    for lane, row in enumerate(body["sequences"]):
        cap = lane + 1
        prompt = list(PROMPTS[lane])
        gold = [0] * cap
        assert row["sequence_index"] == lane
        assert row["workload"]["prompt_token_ids"] == prompt
        assert row["workload"]["prompt_token_count"] == len(prompt)
        assert row["generated_token_ids"] == gold
        assert row["generated_token_count"] == cap
        assert row["token_ids_legal"] is True
        assert row["token_legitimacy_problems"] == []
        assert row["stop_reason"] == "max_new_tokens"
        assert row["oracle"]["generated_token_ids"] == gold
        assert row["oracle"]["agreement"] is True
        assert row["oracle"]["compared_token_count"] == cap
        assert row["oracle"]["first_divergence"] is None
        assert row["oracle"]["first_divergence_index"] is None
        expected_text = case["tokenizer"].decode(gold, skip_special_tokens=False)
        assert row["decoded_text"]["input_rendered_text"] == case[
            "tokenizer"
        ].decode(prompt, skip_special_tokens=False)
        assert row["decoded_text"]["input_decode_matches_rendered_text"] is True
        assert row["decoded_text"]["input_encode_round_trip_matches_ids"] is True
        assert row["decoded_text"]["raw_decoded_text"] == expected_text
        assert row["decoded_text"]["visible_decoded_text"] == expected_text
        assert row["decoded_text"]["raw_matches_oracle"] is True
        assert row["decoded_text"]["visible_matches_oracle"] is True
        assert row["oracle"]["raw_decoded_text"] == expected_text
        assert row["oracle"]["visible_decoded_text"] == expected_text
        assert row["terminal"]["accepted"] is True
        assert row["terminal"]["terminal_kind"] == "cap"
        assert row["terminal"]["first_eos_index"] is None
        assert row["terminal"]["exact_cap"] is True
        assert row["terminal"]["no_post_terminal_execution"] is True
        assert all(row["terminal"]["checks"].values())
        assert row["terminal"]["failed_checks"] == []
        timing = row["execution_timing"]
        assert timing["clock_domain"] == "abi3_device_cycle_counter"
        assert timing["same_execution_bindings_complete"] is True
        assert timing["target_performance_interpretation"] is False
        assert len(timing["token_commit_ticks"]) == cap
        assert timing["token_commit_ticks"] == sorted(
            timing["token_commit_ticks"]
        )
        assert len(set(timing["token_commit_ticks"])) == cap
        assert timing["transaction_ids"] == list(range(1, cap + 1))

        record_path = case["repo"] / row["record"]["path"]
        assert _sha256(record_path) == row["record"]["sha256"]
        record = _read_json(record_path)
        assert record["generated_token_ids"] == gold
        assert record["token_ids_legal"] is True
        assert record["oracle"]["agreement"] is True
        assert record["execution_timing"]["token_commit_ticks"] == timing[
            "token_commit_ticks"
        ]
        assert [step["completion_timestamp"] for step in record["per_step"]] == timing[
            "token_commit_ticks"
        ]
        assert [step["transaction_id"] for step in record["per_step"]] == timing[
            "transaction_ids"
        ]
        assert len(record["execution_timing"]["bindings"]) == cap
        assert all(
            binding["produced_token_id"] == 0
            and len(binding["completion_digest"]) == 64
            and len(binding["functional_result_digest"]) == 64
            and len(binding["trace_digest"]) == 64
            for binding in record["execution_timing"]["bindings"]
        )
        assert "wall_seconds" not in _keys(record)
        assert "host_performance" not in _keys(record)
        assert "throughput" not in _keys(record)
        assert "tpot_seconds" not in _keys(record)
        batch_ids.add(record["shared_execution"]["batch_execution_id"])
        deployment_ids.add(record["shared_execution"]["deployment_digest"])
    assert batch_ids == {body["batch_execution_id"]}
    assert deployment_ids == {
        body["shared_execution"]["deployment"]["deployment_digest"]
    }


def test_complete_oracle_divergence_is_published_as_gate1_failure(
    tmp_path: Path,
) -> None:
    case = _fixture_repository(tmp_path, 2)

    def diverge(reference: dict[str, Any]) -> None:
        result = reference["results"]["fixture-workload-1"]
        result["generated_token_ids"] = [0, 1]
        result["raw_decoded_text"] = "w0 w1"
        result["visible_decoded_text"] = "w0 w1"

    _rewrite_input(case, 1, "reference", diverge)
    body, _path = runner.execute_request_file(
        case["request_path"],
        repo=case["repo"],
        output_directory=case["output"],
    )

    assert body["status"] == "failed"
    assert body["acceptance_gates"]["gate1_correctness"]["status"] == "fail"
    assert body["acceptance_gates"]["gate2_tpot"]["status"] == "blocked"
    row = body["sequences"][1]
    assert row["generated_token_ids"] == [0, 0]
    assert row["oracle"]["generated_token_ids"] == [0, 1]
    assert row["oracle"]["agreement"] is False
    assert row["oracle"]["first_divergence_index"] == 1
    assert row["oracle"]["first_divergence"] == {
        "index": 1,
        "accelerator_token_id": 0,
        "oracle_token_id": 1,
    }
    assert row["decoded_text"]["raw_matches_oracle"] is False
    record = _read_json(case["repo"] / row["record"]["path"])
    assert record["status"] == "diverged"
    assert record["oracle"]["divergence"] == row["oracle"]["first_divergence"]


def test_oracle_workload_mispairing_is_refused_before_publication(
    tmp_path: Path,
) -> None:
    case = _fixture_repository(tmp_path, 1)

    def mispair(reference: dict[str, Any]) -> None:
        reference["results"]["fixture-workload-0"]["workload_digest"] = "f" * 64

    _rewrite_input(case, 0, "reference", mispair)
    with pytest.raises(runner.GovernedBatchError, match="different workload"):
        runner.execute_request_file(
            case["request_path"],
            repo=case["repo"],
            output_directory=case["output"],
        )
    assert not case["output"].exists()


def test_cloned_prompt_identity_is_refused_as_not_heterogeneous(
    tmp_path: Path,
) -> None:
    case = _fixture_repository(tmp_path, 2)
    first = _read_json(case["workload_paths"][0])

    def clone_prompt(workload: dict[str, Any]) -> None:
        for name in (
            "token_ids",
            "prompt_token_count",
            "rendered_text",
            "rendered_text_sha256",
        ):
            workload[name] = first[name]
        workload["digest"] = runner._workload_digest(workload)

    second = _rewrite_input(case, 1, "workload", clone_prompt)

    def rebind(reference: dict[str, Any]) -> None:
        result = reference["results"]["fixture-workload-1"]
        result["workload_digest"] = second["digest"]
        result["prompt_token_count"] = second["prompt_token_count"]

    _rewrite_input(case, 1, "reference", rebind)
    with pytest.raises(runner.GovernedBatchError, match="prompt token identities"):
        runner.execute_request_file(
            case["request_path"],
            repo=case["repo"],
            output_directory=case["output"],
        )
    assert not case["output"].exists()


def test_tokenizer_illegal_oracle_id_is_refused_before_execution(
    tmp_path: Path,
) -> None:
    case = _fixture_repository(tmp_path, 1)

    def illegal(reference: dict[str, Any]) -> None:
        result = reference["results"]["fixture-workload-0"]
        result["generated_token_ids"] = [FIXTURE_VOCAB]
        result["raw_decoded_text"] = ""
        result["visible_decoded_text"] = ""

    _rewrite_input(case, 0, "reference", illegal)
    with pytest.raises(runner.GovernedBatchError, match="tokenizer-illegal"):
        runner.execute_request_file(
            case["request_path"],
            repo=case["repo"],
            output_directory=case["output"],
        )
    assert not case["output"].exists()


def test_wrong_tokenizer_digest_is_refused(tmp_path: Path) -> None:
    case = _fixture_repository(tmp_path, 1)
    case["request"]["tokenizer"]["sha256"] = "0" * 64
    _rewrite_request(case)

    with pytest.raises(runner.GovernedBatchError, match="tokenizer SHA-256 mismatch"):
        runner.execute_request_file(
            case["request_path"],
            repo=case["repo"],
            output_directory=case["output"],
        )
    assert not case["output"].exists()


def test_existing_output_directory_is_refused_create_once(tmp_path: Path) -> None:
    case = _fixture_repository(tmp_path, 1)
    case["output"].mkdir(parents=True)

    with pytest.raises(runner.GovernedBatchError, match="create-once"):
        runner.execute_request_file(
            case["request_path"],
            repo=case["repo"],
            output_directory=case["output"],
        )


def test_parent_traversal_is_refused_by_request_schema(tmp_path: Path) -> None:
    case = _fixture_repository(tmp_path, 1)
    case["request"]["tokenizer"]["path"] = "../tokenizer.json"
    _rewrite_request(case)

    with pytest.raises(runner.GovernedBatchError, match="schema violation"):
        runner.execute_request_file(
            case["request_path"],
            repo=case["repo"],
            output_directory=case["output"],
        )
    assert not case["output"].exists()


def test_tampered_token_commit_binding_fails_gate1_and_blocks_tpot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _fixture_repository(tmp_path, 1)
    original = runner.CycleBatchScheduler.evidence

    def tampered_evidence(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        evidence = original(self, *args, **kwargs)
        evidence["sequences"][0]["token_commit_ticks"][0] += 1
        return evidence

    monkeypatch.setattr(runner.CycleBatchScheduler, "evidence", tampered_evidence)
    body, _path = runner.execute_request_file(
        case["request_path"],
        repo=case["repo"],
        output_directory=case["output"],
    )

    assert body["status"] == "failed"
    assert body["acceptance_gates"]["gate1_correctness"]["status"] == "fail"
    assert body["acceptance_gates"]["gate2_tpot"]["status"] == "blocked"
    timing = body["sequences"][0]["execution_timing"]
    assert timing["same_execution_bindings_complete"] is False
    assert any("token-commit ticks" in problem for problem in body["problems"])


def test_terminal_evidence_accepts_only_final_eos_without_later_execution() -> None:
    generated = [0, FIXTURE_VOCAB - 1]
    steps = [
        {
            "step": index,
            "produced_tokens": [token],
            "final_token_id": token,
            "status": "SUCCESS",
            "trap": "NONE",
        }
        for index, token in enumerate(generated)
    ]
    scheduler = {
        "no_post_eos_transaction": True,
        "post_retirement_transaction_count": 0,
    }

    evidence, problems = runner._terminal_evidence(
        generated=generated,
        stop_reason="eos",
        oracle_stop_reason="eos",
        max_new_tokens=8,
        eos_token_ids=[FIXTURE_VOCAB - 1],
        per_step=steps,
        scheduler_sequence=scheduler,
    )
    assert problems == []
    assert evidence["accepted"] is True
    assert evidence["terminal_kind"] == "eos"
    assert evidence["first_eos_index"] == 1
    assert evidence["no_post_terminal_execution"] is True

    scheduler["no_post_eos_transaction"] = False
    scheduler["post_retirement_transaction_count"] = 1
    evidence, problems = runner._terminal_evidence(
        generated=generated,
        stop_reason="eos",
        oracle_stop_reason="eos",
        max_new_tokens=8,
        eos_token_ids=[FIXTURE_VOCAB - 1],
        per_step=steps,
        scheduler_sequence=scheduler,
    )
    assert evidence["accepted"] is False
    assert evidence["no_post_terminal_execution"] is False
    assert problems == ["no_post_terminal_execution"]
