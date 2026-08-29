from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import pytest
from referencing import Registry, Resource

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from compiler.tensor_accelerator.qwen_chat import QwenChatTokenizer
from compiler.tensor_accelerator.qwen_dynamic_control import (
    QwenDynamicControlError,
    build_controlled_dynamic_execution,
    build_dynamic_generation_control,
    controlled_stop_reason,
    generated_token_record,
    validate_controlled_dynamic_execution,
    validate_dynamic_generation_control,
)
from compiler.tensor_accelerator.qwen_full_model_dynamic import (
    EXECUTION_SCHEMA,
    SESSION_SCHEMA,
    SESSION_VERSION,
    build_dynamic_request,
)
from compiler.tensor_accelerator.qwen_workload import load_shared_workload


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/"
    "snapshots/b968826d9c46dd6066d109eabc6255188de91218"
)
LOCK = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/source/"
    "checkpoint.lock.json"
)
WORKLOAD_PATH = (
    ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
)
SCHEMA_ROOT = ROOT / "schemas/compiler/tensor_accelerator"
HAS_AUTHENTIC_SOURCES = all(
    path.is_file()
    for path in (SNAPSHOT / "tokenizer.json", SNAPSHOT / "tokenizer_config.json", LOCK)
)
AUTHENTIC = pytest.mark.skipif(
    not HAS_AUTHENTIC_SOURCES, reason="pinned Qwen tokenizer sources are unavailable"
)


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _chat() -> QwenChatTokenizer:
    return QwenChatTokenizer(SNAPSHOT, load_strict_json(LOCK))


def _workload(chat: QwenChatTokenizer) -> dict[str, Any]:
    return load_shared_workload(WORKLOAD_PATH, chat=chat)


def _session(workload: dict[str, Any], case_id: str = "arithmetic") -> dict[str, Any]:
    record = next(item for item in workload["natural_questions"] if item["id"] == case_id)
    prompt = record["prompt"]
    generated_limit = 8000 - prompt["prompt_token_count"] + 1
    body = {
        "build_id": "a" * 64,
        "checkpoint_lock_id": workload["model"]["checkpoint_lock_id"],
        "claim_boundary": {
            "exact_8000_token_acceptance": False,
            "short_generation": True,
            "timing_or_performance": False,
        },
        "command_program_sha256": "c" * 64,
        "context_capacity": 8000,
        "generation": {
            "eos_token_ids": [151645, 151643],
            "generated_token_limit": generated_limit,
            "selection": "greedy_lowest_token_id_argmax",
            "unexpected_early_eos": "fail",
        },
        "graph_id": "d" * 64,
        "model_id": "qwen3-8b",
        "prompt": {
            "text": prompt["prompt_text"],
            "token_count": prompt["prompt_token_count"],
            "token_ids": prompt["prompt_token_ids"],
            "utf8_sha256": prompt["prompt_text_utf8_sha256"],
        },
        "schema": SESSION_SCHEMA,
        "session_version": SESSION_VERSION,
        "tokenizer": {
            "decoded_prompt_exact": True,
            "library": "tokenizers",
            "library_version": "0.22.2",
            "path": "tokenizer.json",
            "sha256": workload["model"]["source_files"]["tokenizer"]["sha256"],
            "vocabulary_size": 151936,
        },
    }
    return _reidentify(body, "session_id")


def _report(
    session: dict[str, Any],
    request: dict[str, Any],
    previous: dict[str, Any] | None,
    token: int,
) -> dict[str, Any]:
    step = request["step_index"]
    before = (
        hashlib.sha256(b"initial-state-metadata").hexdigest()
        if previous is None
        else previous["runtime_binding"]["state_metadata_after_sha256"]
    )
    after = hashlib.sha256(f"state-metadata-{step + 1}".encode()).hexdigest()
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
        "counters": {
            f"commands.fake_{index:02d}": index + step for index in range(70)
        },
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
                "greedy_maximum_count": 1,
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
        "state": [
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
        ],
        "state_before": {
            "generations": [step] * 36,
            "lengths": [step] * 36,
        },
        "status": "pass",
        "step_index": step,
        "timing": {"reason": "capability_uncharacterized", "status": "unavailable"},
    }
    return _reidentify(body, "report_id")


def _chain(
    session: dict[str, Any], generated: list[int]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    count = session["prompt"]["token_count"] + len(generated) - 1
    requests: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for step in range(count):
        request = build_dynamic_request(session, previous)
        generated_index = request["generated_token_index"]
        token = (
            1000 + step
            if generated_index is None
            else generated[generated_index]
        )
        report = _report(session, request, previous, token)
        requests.append(request)
        reports.append(report)
        previous = report
    return requests, reports


@AUTHENTIC
def test_dynamic_control_exact_arithmetic_reconstructs_full_eos_chain() -> None:
    chat = _chat()
    workload = _workload(chat)
    session = _session(workload)
    control = build_dynamic_generation_control(
        session, workload, kind="natural_question", case_id="arithmetic"
    )
    generated = [18, 24, 16, 151645]
    requests, reports = _chain(session, generated)
    execution = build_controlled_dynamic_execution(
        control, session, workload, requests, reports, chat=chat
    )

    assert execution["status"] == "pass"
    assert execution["stop_reason"] == "eos"
    assert execution["eos_observed"] is True
    assert execution["generated_token_ids"] == generated
    assert execution["decoded"]["generated_text_visible"] == "391"
    assert execution["transaction_count"] == 31
    assert execution["decode_transaction_count"] == 3
    assert execution["steps"][-1]["output_token_id"] == 151645
    assert execution["steps"][-1]["is_terminal_decision"] is True
    assert validate_controlled_dynamic_execution(
        execution, control, session, workload, chat=chat
    ) == execution

    schemas = [
        load_strict_json(
            SCHEMA_ROOT / "qwen_dynamic_generation_control_v1.schema.json"
        ),
        load_strict_json(
            SCHEMA_ROOT
            / "qwen_controlled_dynamic_session_execution_v1.schema.json"
        ),
    ]
    registry = Registry()
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    Draft202012Validator(schemas[0], registry=registry).validate(control)
    Draft202012Validator(schemas[1], registry=registry).validate(execution)


@AUTHENTIC
def test_dynamic_control_records_first_decision_eos_and_golden_mismatch() -> None:
    chat = _chat()
    workload = _workload(chat)
    session = _session(workload)
    control = build_dynamic_generation_control(
        session, workload, kind="natural_question", case_id="arithmetic"
    )
    requests, reports = _chain(session, [151645])
    execution = build_controlled_dynamic_execution(
        control, session, workload, requests, reports, chat=chat
    )
    assert execution["status"] == "fail"
    assert execution["stop_reason"] == "eos"
    assert execution["generated_token_ids"] == [151645]
    assert execution["comparison"]["first_token_divergence_index"] == 0


@AUTHENTIC
def test_dynamic_control_rejects_post_eos_and_padded_model_rows() -> None:
    chat = _chat()
    workload = _workload(chat)
    session = _session(workload)
    control = build_dynamic_generation_control(
        session, workload, kind="natural_question", case_id="arithmetic"
    )
    requests, reports = _chain(session, [151645, 0])
    with pytest.raises(QwenDynamicControlError, match="continues after the first EOS"):
        build_controlled_dynamic_execution(
            control, session, workload, requests, reports, chat=chat
        )
    with pytest.raises(QwenDynamicControlError, match="undecodable padded model row"):
        generated_token_record(
            control,
            session,
            workload,
            chat,
            generated_token_index=0,
            token_id=151669,
        )


@AUTHENTIC
def test_dynamic_control_maximum_stop_and_malformed_evidence_fail_closed() -> None:
    chat = _chat()
    workload = _workload(chat)
    session = _session(workload)
    control = build_dynamic_generation_control(
        session, workload, kind="natural_question", case_id="arithmetic"
    )
    maximum = control["generation"]["maximum_generated_token_count"]
    assert controlled_stop_reason(
        control,
        session,
        workload,
        generated_token_count=maximum,
        latest_generated_token_id=42,
    ) == "maximum_generated_token_count"
    assert controlled_stop_reason(
        control,
        session,
        workload,
        generated_token_count=maximum - 1,
        latest_generated_token_id=42,
    ) is None

    requests, reports = _chain(session, [18, 24, 16, 151645])
    execution = build_controlled_dynamic_execution(
        control, session, workload, requests, reports, chat=chat
    )
    forged = copy.deepcopy(execution)
    forged["token_legitimacy"]["records"][0]["token_id"] = 17
    forged = _reidentify(forged, "controlled_execution_id")
    with pytest.raises(QwenDynamicControlError, match="token record boundary"):
        validate_controlled_dynamic_execution(
            forged, control, session, workload, chat=chat
        )

    broken_causality = copy.deepcopy(execution)
    broken_causality["steps"][-1]["input_token_id"] = 0
    broken_causality["step_chain_sha256"] = sha256_bytes(
        canonical_json_bytes(broken_causality["steps"])
    )
    broken_causality = _reidentify(broken_causality, "controlled_execution_id")
    with pytest.raises(QwenDynamicControlError, match="token causality differs"):
        validate_controlled_dynamic_execution(
            broken_causality, control, session, workload, chat=chat
        )


@AUTHENTIC
def test_dynamic_control_rejects_prompt_workload_and_source_identity_drift() -> None:
    chat = _chat()
    workload = _workload(chat)
    session = _session(workload)
    control = build_dynamic_generation_control(
        session, workload, kind="natural_question", case_id="arithmetic"
    )

    prompt_drift = copy.deepcopy(session)
    prompt_drift["prompt"]["token_ids"][0] = 0
    prompt_drift = _reidentify(prompt_drift, "session_id")
    with pytest.raises(QwenDynamicControlError, match="control boundary differs"):
        validate_dynamic_generation_control(control, prompt_drift, workload)

    workload_drift = copy.deepcopy(workload)
    workload_drift["natural_questions"][0]["expected"]["rom_result_id"] = "f" * 64
    workload_drift = _reidentify(workload_drift, "workload_id")
    with pytest.raises(QwenDynamicControlError, match="control boundary differs"):
        validate_dynamic_generation_control(control, session, workload_drift)

    source_drift = copy.deepcopy(workload)
    source_drift["model"]["checkpoint_lock_id"] = "0" * 64
    source_drift = _reidentify(source_drift, "workload_id")
    with pytest.raises(QwenDynamicControlError, match="control boundary differs"):
        validate_dynamic_generation_control(control, session, source_drift)
