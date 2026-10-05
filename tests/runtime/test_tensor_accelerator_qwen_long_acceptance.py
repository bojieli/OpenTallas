"""Long-acceptance sessions on the retained ABI 2.5 Qwen physical deployment.

This file belongs to the ABI 2.5 tensor-accelerator lane that ABI 3.0
superseded -- the lane inventoried in ``tests/compiler/README_RETIRED_LANE.md``
and tracked as OI-25.  A green tick here is not evidence for ABI 3.0.

Session authentication, request chaining and checkpoint round-tripping read
only the committed descriptors of
``results/tensor_accelerator/qwen3_long_acceptance_physical_v1`` and run
everywhere.  The single test that loads the deployment through
``QwenFullModelSimulator`` additionally needs the payload the manifest declares
-- seventeen HBM shards and ``program/commands.bin`` -- which ``.gitignore``
excludes because it is tens of gigabytes, and carries the narrower
``LOADABLE`` precondition for exactly that reason.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import numpy as np
import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from compiler.tensor_accelerator.qwen_full_model_long_acceptance import (
    EXECUTION_SCHEMA,
    FINAL_STATE_LENGTH,
    PROMPT_TOKEN_COUNT,
    PROMPT_TOKEN_ID,
    QwenLongAcceptanceArtifactError,
    REQUEST_SCHEMA,
    SESSION_SCHEMA,
    TRANSACTION_COUNT,
    build_long_acceptance_request,
    build_long_acceptance_session,
    prompt_token_ids_sha256,
    publish_long_acceptance_request,
    publish_long_acceptance_session,
    validate_long_acceptance_request,
    validate_long_acceptance_session,
)
from runtime.tensor_accelerator.qwen_full_model_restart import (
    QwenRestartDifferentialError,
    validate_restart_differential,
)
from runtime.tensor_accelerator.attention import make_kv_snapshot
from runtime.tensor_accelerator.qwen_full_model_checkpoint import (
    QwenFullModelCheckpointError,
    load_runtime_checkpoint,
    publish_runtime_checkpoint,
    validate_checkpoint_predecessor,
)
from runtime.tensor_accelerator.qwen_full_model_simulator import (
    QwenFullModelSimulationError,
    QwenFullModelSimulator,
)
from tools.run_qwen3_tensor_accelerator_long_acceptance import (
    _checkpoint_directories,
    _frontier,
)


ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = (
    ROOT / "results/tensor_accelerator/qwen3_long_acceptance_physical_v1"
)
FIXTURE_REPOSITORY = ROOT
RESTART_EVIDENCE = (
    ROOT / "results/tensor_accelerator/qwen3_long_acceptance_restart_v1"
)
SCHEMA_ROOT = ROOT / "schemas/compiler/tensor_accelerator"


def _retained_deployment_is_complete(root: Path) -> bool:
    """Whether every artifact the deployment manifest declares is on disk.

    ``deployment_manifest.json`` is committed; the payload it declares -- the
    seventeen HBM shards under ``memory/hbm/`` and ``program/commands.bin`` --
    is excluded by ``.gitignore`` in the same commit that published the
    deployment, because it is tens of gigabytes.  So testing for the manifest
    alone answers "available" on every checkout, including the ones on which
    ``QwenFullModelSimulator.load`` cannot get past its own file-set check.
    Only the tests that load the simulator need the payload; the ones that
    authenticate the session against the committed descriptors do not, and
    they keep the narrower precondition.
    """

    manifest = root / "deployment_manifest.json"
    if not manifest.is_file():
        return False
    try:
        artifacts = json.loads(manifest.read_text(encoding="utf-8"))["artifacts"]
        return all((root / record["path"]).is_file() for record in artifacts)
    except (OSError, ValueError, KeyError, TypeError):
        return False


HAS_INPUTS = (
    (DEPLOYMENT / "deployment_manifest.json").is_file()
    and (FIXTURE_REPOSITORY / ".git").exists()
)
AUTHENTIC = pytest.mark.skipif(
    not HAS_INPUTS,
    reason="V7 deployment or committed concurrent Qwen fixture is unavailable",
)
LOADABLE = pytest.mark.skipif(
    not (HAS_INPUTS and _retained_deployment_is_complete(DEPLOYMENT)),
    reason=(
        "the retained ABI 2.5 Qwen physical deployment is incomplete: its "
        "HBM shards and program/commands.bin are excluded by .gitignore and "
        "cannot be reproduced from this repository. This is the retired ABI "
        "2.5 lane of tests/compiler/README_RETIRED_LANE.md (OI-25), not ABI "
        "3.0 coverage"
    ),
)
RESTART = pytest.mark.skipif(
    not (RESTART_EVIDENCE / "restart_differential.json").is_file(),
    reason="retained Qwen restart differential is unavailable",
)


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _session() -> dict[str, Any]:
    return build_long_acceptance_session(
        deployment_root=DEPLOYMENT,
        fixture_repository=FIXTURE_REPOSITORY,
    )


def _previous(
    session: dict[str, Any], *, step: int, token: int
) -> dict[str, Any]:
    body = {
        "build_id": session["build_id"],
        "outputs": {"committed_logits": {"greedy_token_id": token}},
        "schema": EXECUTION_SCHEMA,
        "session_id": session["session_id"],
        "status": "pass",
        "step_index": step,
    }
    return _reidentify(body, "report_id")


def _bindings(session: dict[str, Any]) -> dict[str, str]:
    return {
        field: session[field]
        for field in (
            "build_id",
            "capability_id",
            "checkpoint_lock_id",
            "command_program_sha256",
            "graph_id",
            "hbm_logical_sha256",
            "kernel_ir_id",
            "physical_plan_id",
            "session_id",
        )
    }


def _states(length: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for layer in range(36):
        keys = np.full((length, 8, 128), layer + 1, dtype=np.uint16)
        values = np.full((length, 8, 128), layer + 101, dtype=np.uint16)
        result[f"kv.layer.{layer}"] = make_kv_snapshot(
            resource_id=f"kv.layer.{layer}",
            generation=length,
            capacity=8192,
            key_values=keys,
            value_values=values,
        )
    return result


@AUTHENTIC
def test_long_session_authenticates_compact_fixture_and_v7_deployment() -> None:
    session = _session()
    assert validate_long_acceptance_session(session) == session
    assert session["schema"] == SESSION_SCHEMA
    assert session["prompt"] == {
        "encoding": "repeated_token_id_v1",
        "token_count": 8000,
        "token_id": 151643,
        "token_ids_sha256": (
            "8dcbc057d9f4bb2657755ffc4419dae1189837343c093964ed329ad95e43d461"
        ),
    }
    assert prompt_token_ids_sha256() == session["prompt"]["token_ids_sha256"]
    assert PROMPT_TOKEN_COUNT == 8000
    assert TRANSACTION_COUNT == FINAL_STATE_LENGTH == 8031
    assert session["workload_fixture"]["commit"] == (
        "3a985ffcecfd17fb8642cdef819c22e16d8e9f4c"
    )
    assert session["official_prefill_golden"]["comparison_status"] == (
        "pending_common_simulator_execution"
    )

    schema = load_strict_json(
        SCHEMA_ROOT / "qwen_full_model_long_acceptance_session_v1.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(session)

    forged = copy.deepcopy(session)
    forged["workload_fixture"]["commit"] = "f" * 40
    forged = _reidentify(forged, "session_id")
    with pytest.raises(QwenLongAcceptanceArtifactError, match="fixture identity"):
        validate_long_acceptance_session(forged)


@AUTHENTIC
def test_long_request_chain_crosses_prefill_decode_and_8031_boundary() -> None:
    session = _session()
    initial = build_long_acceptance_request(session)
    assert initial["schema"] == REQUEST_SCHEMA
    assert initial["step_index"] == 0
    assert initial["token_id"] == PROMPT_TOKEN_ID
    assert initial["generated_token_index"] is None
    assert initial["output_role"] == "prefill_intermediate"

    last_prefill = build_long_acceptance_request(
        session, _previous(session, step=7998, token=42)
    )
    assert last_prefill["step_index"] == 7999
    assert last_prefill["token_id"] == PROMPT_TOKEN_ID
    assert last_prefill["phase"] == "prefill"
    assert last_prefill["generated_token_index"] == 0
    assert last_prefill["output_role"] == "generated_token"

    first_decode = build_long_acceptance_request(
        session, _previous(session, step=7999, token=33975)
    )
    assert first_decode["step_index"] == 8000
    assert first_decode["token_id"] == 33975
    assert first_decode["phase"] == "decode"
    assert first_decode["generated_token_index"] == 1

    final = build_long_acceptance_request(
        session, _previous(session, step=8029, token=17)
    )
    assert final["step_index"] == 8030
    assert final["position_end"] == 8031
    assert final["generated_token_index"] == 31
    with pytest.raises(QwenLongAcceptanceArtifactError, match="session is complete"):
        build_long_acceptance_request(
            session, _previous(session, step=8030, token=19)
        )

    schema = load_strict_json(
        SCHEMA_ROOT / "qwen_full_model_long_acceptance_request_v1.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    for request in (initial, last_prefill, first_decode, final):
        Draft202012Validator(schema).validate(request)

    forged = copy.deepcopy(final)
    forged["position_end"] = 8192
    forged = _reidentify(forged, "request_id")
    with pytest.raises(QwenLongAcceptanceArtifactError, match="boundary differs"):
        validate_long_acceptance_request(
            forged, session, _previous(session, step=8029, token=17)
        )


@AUTHENTIC
def test_long_artifact_publication_is_canonical_and_no_overwrite(
    tmp_path: Path,
) -> None:
    session = _session()
    request = build_long_acceptance_request(session)
    session_path = tmp_path / "session.json"
    request_path = tmp_path / "request.json"
    publish_long_acceptance_session(session, session_path)
    publish_long_acceptance_request(request, session, None, request_path)
    assert session_path.read_bytes() == canonical_json_bytes(session)
    assert request_path.read_bytes() == canonical_json_bytes(request)
    assert not list(tmp_path.glob(".*.tmp-*"))
    with pytest.raises(QwenLongAcceptanceArtifactError, match="already exists"):
        publish_long_acceptance_session(session, session_path)
    assert not list(tmp_path.glob(".*.tmp-*"))


@AUTHENTIC
def test_runtime_checkpoint_round_trips_all_bytes_and_rejects_corruption(
    tmp_path: Path,
) -> None:
    session = _session()
    bindings = _bindings(session)
    states = _states(2)
    predecessor_body = {
        "outputs": {"committed_logits": {"greedy_token_id": 33975}},
        "state": [
            {
                "generation": 2,
                "key_payload_sha256": hashlib.sha256(
                    np.ascontiguousarray(
                        states[f"kv.layer.{layer}"].key_values, dtype="<u2"
                    ).tobytes()
                ).hexdigest(),
                "layer": layer,
                "length": 2,
                "resource_id": f"kv.layer.{layer}",
                "value_payload_sha256": hashlib.sha256(
                    np.ascontiguousarray(
                        states[f"kv.layer.{layer}"].value_values, dtype="<u2"
                    ).tobytes()
                ).hexdigest(),
            }
            for layer in range(36)
        ],
        "step_index": 1,
    }
    predecessor = _reidentify(predecessor_body, "report_id")
    output = tmp_path / "checkpoint"
    manifest = publish_runtime_checkpoint(
        output=output,
        bindings=bindings,
        next_step_index=2,
        previous_report_id=predecessor["report_id"],
        previous_greedy_token_id=33975,
        states=states,
    )
    assert validate_checkpoint_predecessor(manifest, predecessor) == manifest
    forged_predecessor = copy.deepcopy(predecessor)
    forged_predecessor["state"][0]["key_payload_sha256"] = "0" * 64
    forged_predecessor = _reidentify(forged_predecessor, "report_id")
    forged_manifest = copy.deepcopy(manifest)
    forged_manifest["previous_report_id"] = forged_predecessor["report_id"]
    forged_manifest = _reidentify(forged_manifest, "checkpoint_id")
    with pytest.raises(QwenFullModelCheckpointError, match="state differs"):
        validate_checkpoint_predecessor(forged_manifest, forged_predecessor)
    assert (output / "checkpoint_manifest.json").read_bytes() == canonical_json_bytes(
        manifest
    )
    schema = load_strict_json(
        SCHEMA_ROOT / "qwen_full_model_runtime_checkpoint_v1.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)
    rebuilt_manifest, rebuilt_states = load_runtime_checkpoint(
        output, expected_bindings=bindings
    )
    assert rebuilt_manifest == manifest
    for resource, expected in states.items():
        observed = rebuilt_states[resource]
        assert observed.generation == expected.generation
        assert observed.capacity == expected.capacity
        assert np.array_equal(observed.key_values, expected.key_values)
        assert np.array_equal(observed.value_values, expected.value_values)
        assert not observed.key_values.flags.writeable
        assert not observed.value_values.flags.writeable
    with pytest.raises(QwenFullModelCheckpointError, match="already exists"):
        publish_runtime_checkpoint(
            output=output,
            bindings=bindings,
            next_step_index=2,
            previous_report_id=predecessor["report_id"],
            previous_greedy_token_id=33975,
            states=states,
        )

    wrong = dict(bindings)
    wrong["session_id"] = "0" * 64
    with pytest.raises(QwenFullModelCheckpointError, match="binding differs"):
        load_runtime_checkpoint(output, expected_bindings=wrong)

    shard = output / manifest["state_image"]["shards"][0]["path"]
    with shard.open("r+b") as handle:
        first = handle.read(1)
        handle.seek(0)
        handle.write(bytes([first[0] ^ 1]))
    with pytest.raises(QwenFullModelCheckpointError, match="hash differs"):
        load_runtime_checkpoint(output, expected_bindings=bindings)


@AUTHENTIC
def test_runtime_checkpoint_failure_does_not_publish_partial_root(
    tmp_path: Path,
) -> None:
    session = _session()
    states = _states(2)
    states.pop("kv.layer.35")
    output = tmp_path / "checkpoint"
    with pytest.raises(QwenFullModelCheckpointError, match="resources differ"):
        publish_runtime_checkpoint(
            output=output,
            bindings=_bindings(session),
            next_step_index=2,
            previous_report_id="e" * 64,
            previous_greedy_token_id=1,
            states=states,
        )
    assert not output.exists()
    assert not list(tmp_path.glob(".checkpoint.tmp-*"))


@RESTART
def test_retained_restart_differential_authenticates_every_retained_byte() -> None:
    report = load_strict_json(RESTART_EVIDENCE / "restart_differential.json")
    assert validate_restart_differential(
        report, evidence_root=RESTART_EVIDENCE
    ) == report
    schema = load_strict_json(
        SCHEMA_ROOT / "qwen_full_model_restart_differential_v1.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)

    forged = copy.deepcopy(report)
    forged["comparison"]["transaction_reports_byte_equal"] = False
    forged = _reidentify(forged, "differential_id")
    with pytest.raises(QwenRestartDifferentialError, match="boundary differs"):
        validate_restart_differential(forged)


def test_long_runner_accepts_one_request_only_and_cleans_exact_staging_names(
    tmp_path: Path,
) -> None:
    requests = tmp_path / "requests"
    executions = tmp_path / "executions"
    requests.mkdir()
    executions.mkdir()
    (requests / "request.0000.json").write_bytes(b"{}\n")
    assert _frontier(requests, executions) == (0, True)
    (executions / "execution.0000.json").write_bytes(b"{}\n")
    (requests / ".request.0001.json.tmp-crash").write_bytes(b"partial")
    (executions / ".execution.0001.json.tmp-crash").write_bytes(b"partial")
    assert _frontier(requests, executions) == (1, False)
    assert not list(requests.glob(".*.tmp-*"))
    assert not list(executions.glob(".*.tmp-*"))

    (executions / "execution.0001.json").write_bytes(b"{}\n")
    with pytest.raises(QwenFullModelSimulationError, match="lack requests"):
        _frontier(requests, executions)


def test_long_runner_checkpoint_cleanup_is_narrow_and_complete_step_is_visible(
    tmp_path: Path,
) -> None:
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    staging = checkpoints / ".checkpoint.0002.tmp-crash"
    staging.mkdir()
    (staging / "partial").write_bytes(b"partial")
    complete = checkpoints / "checkpoint.8031"
    complete.mkdir()
    assert _checkpoint_directories(checkpoints) == [(8031, complete)]
    assert not staging.exists()

    unsafe = checkpoints / ".checkpoint.manual.tmp-not-owned"
    unsafe.mkdir()
    with pytest.raises(QwenFullModelSimulationError, match="unexpected"):
        _checkpoint_directories(checkpoints)


@LOADABLE
def test_simulator_binds_long_session_without_broadening_short_v1(
    tmp_path: Path,
) -> None:
    session = _session()
    request = build_long_acceptance_request(session)
    session_path = tmp_path / "session.json"
    request_path = tmp_path / "request.json"
    session_path.write_bytes(canonical_json_bytes(session))
    request_path.write_bytes(canonical_json_bytes(request))
    with QwenFullModelSimulator.load(DEPLOYMENT, verify_hbm_hashes=False) as simulator:
        assert simulator.begin_long_acceptance_session(session_path) == session
        assert simulator._validate_long_acceptance_request(request) == request
        with pytest.raises(QwenFullModelSimulationError, match="cannot share"):
            simulator.execute()
