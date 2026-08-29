from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from compiler.tensor_accelerator.qwen_full_model_dynamic import (
    EXECUTION_SCHEMA,
    REQUEST_SCHEMA,
    REQUEST_VERSION,
    SESSION_SCHEMA,
    SESSION_VERSION,
    QwenDynamicArtifactError,
    build_dynamic_request,
    build_dynamic_session_execution,
    publish_dynamic_request,
    publish_dynamic_session,
    publish_dynamic_session_execution,
    validate_dynamic_request,
    validate_dynamic_session,
    validate_dynamic_session_execution,
)
from runtime.tensor_accelerator.qwen_full_model_simulator import (
    QwenFullModelSimulationError,
    QwenFullModelSimulator,
)


ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
RETAINED_SESSION = ROOT / "results/tensor_accelerator/qwen3_short_generation_v1"
DYNAMIC_SCHEMA_ROOT = ROOT / "schemas/compiler/tensor_accelerator"
HAS_DEPLOYMENT = (DEPLOYMENT / "deployment_manifest.json").is_file()
AUTHENTIC = pytest.mark.skipif(
    not HAS_DEPLOYMENT,
    reason="retained complete Qwen physical deployment is unavailable",
)
HAS_RETAINED_SESSION = (RETAINED_SESSION / "reference.json").is_file()
RETAINED = pytest.mark.skipif(
    not HAS_RETAINED_SESSION,
    reason="retained independently verified Qwen short-generation session unavailable",
)


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _session() -> dict[str, Any]:
    prompt = "!"
    body = {
        "build_id": "a" * 64,
        "checkpoint_lock_id": "b" * 64,
        "claim_boundary": {
            "exact_8000_token_acceptance": False,
            "short_generation": True,
            "timing_or_performance": False,
        },
        "command_program_sha256": "c" * 64,
        "context_capacity": 8000,
        "generation": {
            "eos_token_ids": [151645, 151643],
            "generated_token_limit": 32,
            "selection": "greedy_lowest_token_id_argmax",
            "unexpected_early_eos": "fail",
        },
        "graph_id": "d" * 64,
        "model_id": "qwen3-8b",
        "prompt": {
            "text": prompt,
            "token_count": 1,
            "token_ids": [0],
            "utf8_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        },
        "schema": SESSION_SCHEMA,
        "session_version": SESSION_VERSION,
        "tokenizer": {
            "decoded_prompt_exact": True,
            "library": "tokenizers",
            "library_version": "0.22.2",
            "path": "tokenizer.json",
            "sha256": "e" * 64,
            "vocabulary_size": 151936,
        },
    }
    return _reidentify(body, "session_id")


def _previous_report(
    session: dict[str, Any], *, step: int, token: int
) -> dict[str, Any]:
    body = {
        "build_id": session["build_id"],
        "graph_id": session["graph_id"],
        "outputs": {"committed_logits": {"greedy_token_id": token}},
        "schema": EXECUTION_SCHEMA,
        "session_id": session["session_id"],
        "status": "pass",
        "step_index": step,
    }
    return _reidentify(body, "report_id")


def _decode(token_ids: list[int]) -> str:
    if token_ids == [0]:
        return "!"
    return "tokens:" + ",".join(str(token) for token in token_ids)


def _dynamic_report(
    session: dict[str, Any],
    request: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    step = request["step_index"]
    token = 1000 + step
    before = (
        hashlib.sha256(b"initial-state-metadata").hexdigest()
        if previous is None
        else previous["runtime_binding"]["state_metadata_after_sha256"]
    )
    after = hashlib.sha256(f"state-metadata-{step + 1}".encode()).hexdigest()
    state = [
        {
            "generation": step + 1,
            "key_payload_sha256": hashlib.sha256(
                f"key-{step}-{layer}".encode()
            ).hexdigest(),
            "layer": layer,
            "length": step + 1,
            "resource_id": f"kv.layer.{layer}",
            "value_payload_sha256": hashlib.sha256(
                f"value-{step}-{layer}".encode()
            ).hexdigest(),
        }
        for layer in range(36)
    ]
    body = {
        "artifact_admission": {
            "all_hbm_shards_sha256_verified": True,
            "non_hbm_manifest_artifacts_sha256_verified": True,
        },
        "build_id": session["build_id"],
        "claim_boundary": {
            "complete_model_one_token_execution": True,
            "exact_8000_token_acceptance": False,
            "generated_token_decision": request["output_role"] == "generated_token",
            "session_generation_complete": False,
            "timing_or_performance": False,
        },
        "command_count": 924386,
        "command_program_sha256": session["command_program_sha256"],
        "counters": {f"commands.fake_{index:02d}": index + step for index in range(70)},
        "graph_id": session["graph_id"],
        "input": {
            "generated_token_index": request["generated_token_index"],
            "input_role": request["input_role"],
            "output_role": request["output_role"],
            "phase": request["phase"],
            "position_end": request["position_end"],
            "position_start": request["position_start"],
            "token_id": request["token_id"],
        },
        "mode": "artifact_only_data_bearing_dynamic_transaction",
        "operation_count": 617,
        "outputs": {
            "committed_logits": {
                "greedy_maximum_count": 2 if step == 2 else 1,
                "greedy_token_id": token,
                "payload_sha256": hashlib.sha256(f"logits-{step}".encode()).hexdigest(),
                "size_bytes": 303872,
            }
        },
        "previous_report_id": None if previous is None else previous["report_id"],
        "request_id": request["request_id"],
        "runtime_binding": {
            "request_registers_sha256": hashlib.sha256(
                f"registers-{step}".encode()
            ).hexdigest(),
            "request_registers_size_bytes": 16,
            "state_metadata_after_sha256": after,
            "state_metadata_before_sha256": before,
            "state_metadata_size_bytes": 2304,
            "transaction_descriptors_sha256": hashlib.sha256(
                f"descriptors-{step}".encode()
            ).hexdigest(),
            "transaction_descriptors_size_bytes": 2304,
        },
        "schema": EXECUTION_SCHEMA,
        "session_id": session["session_id"],
        "state": state,
        "state_before": {
            "generations": [step] * 36,
            "lengths": [step] * 36,
        },
        "status": "pass",
        "step_index": step,
        "timing": {
            "reason": "capability_uncharacterized",
            "status": "unavailable",
        },
    }
    return _reidentify(body, "report_id")


def _dynamic_chain() -> tuple[
    dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]
]:
    session = _session()
    requests: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for _ in range(session["generation"]["generated_token_limit"]):
        request = build_dynamic_request(session, previous)
        report = _dynamic_report(session, request, previous)
        requests.append(request)
        reports.append(report)
        previous = report
    return session, requests, reports


def test_dynamic_session_and_request_chain_are_content_addressed() -> None:
    session = validate_dynamic_session(_session())
    initial = build_dynamic_request(session)
    assert initial["schema"] == REQUEST_SCHEMA
    assert initial["request_version"] == REQUEST_VERSION
    assert initial["step_index"] == 0
    assert initial["token_id"] == 0
    assert initial["phase"] == "prefill"
    assert initial["generated_token_index"] == 0
    assert initial["previous_report_id"] is None

    previous = _previous_report(session, step=0, token=50994)
    second = build_dynamic_request(session, previous)
    assert second["step_index"] == 1
    assert second["token_id"] == 50994
    assert second["phase"] == "decode"
    assert second["input_role"] == "generated"
    assert second["generated_token_index"] == 1
    assert second["previous_report_id"] == previous["report_id"]

    forged = copy.deepcopy(second)
    forged["expected_lengths"][0] = 0
    forged = _reidentify(forged, "request_id")
    with pytest.raises(QwenDynamicArtifactError, match="chain boundary differs"):
        validate_dynamic_request(forged, session, previous)


def test_dynamic_artifact_publication_is_canonical_and_no_overwrite(
    tmp_path: Path,
) -> None:
    session = _session()
    request = build_dynamic_request(session)
    session_path = tmp_path / "session.json"
    request_path = tmp_path / "request.json"
    publish_dynamic_session(session, session_path)
    publish_dynamic_request(request, session, None, request_path)
    assert session_path.read_bytes() == canonical_json_bytes(session)
    assert request_path.read_bytes() == canonical_json_bytes(request)
    with pytest.raises(QwenDynamicArtifactError, match="already exists"):
        publish_dynamic_session(session, session_path)
    with pytest.raises(QwenDynamicArtifactError, match="already exists"):
        publish_dynamic_request(request, session, None, request_path)


def test_dynamic_schemas_are_strict() -> None:
    session = _session()
    request = build_dynamic_request(session)
    for name, value in (
        ("qwen_full_model_dynamic_session_v1.schema.json", session),
        ("qwen_full_model_dynamic_request_v1.schema.json", request),
    ):
        schema = load_strict_json(DYNAMIC_SCHEMA_ROOT / name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)

    execution = load_strict_json(
        DYNAMIC_SCHEMA_ROOT / "qwen_full_model_dynamic_execution_v1.schema.json"
    )
    Draft202012Validator.check_schema(execution)
    assert execution["additionalProperties"] is False


def test_dynamic_session_aggregate_distinguishes_decisions_and_decode() -> None:
    session, requests, reports = _dynamic_chain()
    result = build_dynamic_session_execution(
        session, requests, reports, decode_token_ids=_decode
    )
    assert result["generated_token_count"] == 32
    assert result["decode_transaction_count"] == 31
    assert result["transaction_count"] == 32
    assert len(result["steps"]) == 32
    assert [step["generated_token_index"] for step in result["steps"]] == list(
        range(32)
    )
    assert result["steps"][0]["phase"] == "prefill"
    assert all(step["phase"] == "decode" for step in result["steps"][1:])
    assert result["claim_boundary"] == {
        "artifact_only_short_generation_complete": True,
        "exact_8000_token_acceptance": False,
        "target_precision_reference_verified": False,
        "timing_or_performance": False,
    }
    schema = load_strict_json(
        DYNAMIC_SCHEMA_ROOT / "qwen_full_model_dynamic_session_execution_v1.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    assert (
        validate_dynamic_session_execution(result, session, decode_token_ids=_decode)
        == result
    )


def test_dynamic_session_builder_rejects_incomplete_reordered_or_broken_chain() -> None:
    session, requests, reports = _dynamic_chain()
    with pytest.raises(QwenDynamicArtifactError, match="transaction coverage differs"):
        build_dynamic_session_execution(
            session, requests[:-1], reports[:-1], decode_token_ids=_decode
        )
    with pytest.raises(QwenDynamicArtifactError, match="transaction coverage differs"):
        build_dynamic_session_execution(
            session,
            [*requests, requests[-1]],
            [*reports, reports[-1]],
            decode_token_ids=_decode,
        )

    reordered_requests = copy.deepcopy(requests)
    reordered_reports = copy.deepcopy(reports)
    reordered_requests[0], reordered_requests[1] = (
        reordered_requests[1],
        reordered_requests[0],
    )
    reordered_reports[0], reordered_reports[1] = (
        reordered_reports[1],
        reordered_reports[0],
    )
    with pytest.raises(QwenDynamicArtifactError, match="step is not contiguous"):
        build_dynamic_session_execution(
            session,
            reordered_requests,
            reordered_reports,
            decode_token_ids=_decode,
        )

    broken = copy.deepcopy(reports)
    broken[1]["runtime_binding"]["state_metadata_before_sha256"] = "f" * 64
    broken[1] = _reidentify(broken[1], "report_id")
    with pytest.raises(QwenDynamicArtifactError, match="state-metadata chain differs"):
        build_dynamic_session_execution(
            session, requests, broken, decode_token_ids=_decode
        )


def test_dynamic_session_aggregate_rejects_forged_scope_order_and_decode() -> None:
    session, requests, reports = _dynamic_chain()
    result = build_dynamic_session_execution(
        session, requests, reports, decode_token_ids=_decode
    )

    broadened = copy.deepcopy(result)
    broadened["claim_boundary"]["target_precision_reference_verified"] = True
    broadened = _reidentify(broadened, "session_execution_id")
    with pytest.raises(QwenDynamicArtifactError, match="boundary differs"):
        validate_dynamic_session_execution(broadened, session)

    reordered = copy.deepcopy(result)
    reordered["steps"][0], reordered["steps"][1] = (
        reordered["steps"][1],
        reordered["steps"][0],
    )
    reordered["step_chain_sha256"] = sha256_bytes(
        canonical_json_bytes(reordered["steps"])
    )
    reordered = _reidentify(reordered, "session_execution_id")
    with pytest.raises(QwenDynamicArtifactError, match="step chain or role differs"):
        validate_dynamic_session_execution(reordered, session)

    bad_counter = copy.deepcopy(result)
    bad_counter["aggregate_counters"]["commands.fake_00"] += 1
    bad_counter = _reidentify(bad_counter, "session_execution_id")
    with pytest.raises(QwenDynamicArtifactError, match="aggregate counters differ"):
        validate_dynamic_session_execution(bad_counter, session)

    bad_decode = copy.deepcopy(result)
    bad_decode["decoded"]["generated_text"] += "forged"
    bad_decode = _reidentify(bad_decode, "session_execution_id")
    with pytest.raises(QwenDynamicArtifactError, match="tokenizer decode differs"):
        validate_dynamic_session_execution(
            bad_decode, session, decode_token_ids=_decode
        )


def test_dynamic_session_aggregate_publication_is_canonical_and_no_overwrite(
    tmp_path: Path,
) -> None:
    session, requests, reports = _dynamic_chain()
    result = build_dynamic_session_execution(
        session, requests, reports, decode_token_ids=_decode
    )
    output = tmp_path / "session_execution.json"
    publish_dynamic_session_execution(result, session, output)
    assert output.read_bytes() == canonical_json_bytes(result)
    with pytest.raises(QwenDynamicArtifactError, match="already exists"):
        publish_dynamic_session_execution(result, session, output)


@RETAINED
def test_retained_dynamic_session_rebuilds_to_the_authentic_exact_identity() -> None:
    session = load_strict_json(RETAINED_SESSION / "session.json")
    requests = [
        load_strict_json(RETAINED_SESSION / f"requests/request.{step:04d}.json")
        for step in range(32)
    ]
    reports = [
        load_strict_json(RETAINED_SESSION / f"executions/execution.{step:04d}.json")
        for step in range(32)
    ]
    expected = load_strict_json(RETAINED_SESSION / "session_execution.json")
    generated = expected["generated_token_ids"]

    def retained_decode(token_ids: list[int]) -> str:
        if token_ids == session["prompt"]["token_ids"]:
            return expected["decoded"]["prompt_text"]
        if token_ids == generated:
            return expected["decoded"]["generated_text"]
        if token_ids == [*session["prompt"]["token_ids"], *generated]:
            return expected["decoded"]["full_text"]
        raise AssertionError("unexpected retained token sequence")

    rebuilt = build_dynamic_session_execution(
        session,
        requests,
        reports,
        decode_token_ids=retained_decode,
    )
    assert rebuilt == expected
    assert expected["session_execution_id"] == (
        "9e53f5d79dff7f530652116df3a9196e3a58dd07375a07c2b6f3ae227b83f0f1"
    )
    assert expected["generated_token_ids"] == [
        50994,
        67,
        21,
        19,
        19,
        19,
        19,
        20,
        19,
        19,
        20,
        19,
        66,
        19,
        19,
        24,
        20,
        23,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
        15,
    ]
    assert all(
        state["generation"] == state["length"] == 32
        for state in expected["final_state"]
    )


@RETAINED
def test_retained_dynamic_session_rejects_a_forged_transaction_chain() -> None:
    session = load_strict_json(RETAINED_SESSION / "session.json")
    requests = [
        load_strict_json(RETAINED_SESSION / f"requests/request.{step:04d}.json")
        for step in range(32)
    ]
    reports = [
        load_strict_json(RETAINED_SESSION / f"executions/execution.{step:04d}.json")
        for step in range(32)
    ]
    forged = copy.deepcopy(reports)
    forged[11]["previous_report_id"] = "f" * 64
    forged[11] = _reidentify(forged[11], "report_id")
    with pytest.raises(QwenDynamicArtifactError, match="report boundary differs"):
        build_dynamic_session_execution(
            session,
            requests,
            forged,
            decode_token_ids=lambda _: "unreachable",
        )


@AUTHENTIC
def test_simulator_binds_dynamic_session_and_preserves_fixed_v1(tmp_path: Path) -> None:
    manifest = load_strict_json(DEPLOYMENT / "deployment_manifest.json")
    source_lock = load_strict_json(DEPLOYMENT / "source.lock.json")
    plan = load_strict_json(DEPLOYMENT / "physical/physical_plan.json")
    checkpoint_lock = load_strict_json(DEPLOYMENT / "source/checkpoint.lock.json")
    tokenizer = next(
        item for item in checkpoint_lock["files"] if item["path"] == "tokenizer.json"
    )
    session = _session()
    session.update(
        {
            "build_id": manifest["build_id"],
            "checkpoint_lock_id": source_lock["checkpoint_lock_id"],
            "command_program_sha256": plan["command_program"]["sha256"],
            "graph_id": manifest["graph_id"],
        }
    )
    session["tokenizer"]["sha256"] = tokenizer["sha256"]
    session = _reidentify(session, "session_id")
    request = build_dynamic_request(session)
    session_path = tmp_path / "session.json"
    request_path = tmp_path / "request.json"
    session_path.write_bytes(canonical_json_bytes(session))
    request_path.write_bytes(canonical_json_bytes(request))

    with QwenFullModelSimulator.load(DEPLOYMENT, verify_hbm_hashes=False) as simulator:
        assert simulator.begin_dynamic_session(session_path) == session
        assert simulator._validate_dynamic_request(request) == request
        with pytest.raises(QwenFullModelSimulationError, match="cannot share"):
            simulator.execute()

    noncanonical = tmp_path / "noncanonical.json"
    noncanonical.write_text(json.dumps(session, indent=2), encoding="utf-8")
    with QwenFullModelSimulator.load(DEPLOYMENT, verify_hbm_hashes=False) as simulator:
        with pytest.raises(QwenFullModelSimulationError, match="not canonical"):
            simulator.begin_dynamic_session(noncanonical)
