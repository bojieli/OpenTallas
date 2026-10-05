"""First-EOS and token-legitimacy overlay for immutable Qwen dynamic V1."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
import re
from typing import Any

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    publish_bytes_atomic_no_replace,
    require_sha256,
    sha256_bytes,
)
from .qwen_chat import (
    BASE_VOCABULARY_SIZE,
    EOS_TOKEN_IDS,
    EXPLICIT_VOCABULARY_SIZE,
    MODEL_VOCABULARY_SIZE,
    QwenChatTokenizer,
)
from .qwen_full_model_dynamic import (
    QwenDynamicArtifactError,
    validate_dynamic_request,
    validate_dynamic_session,
    validate_dynamic_transaction_report,
)
from .qwen_workload import (
    QwenWorkloadError,
    validate_shared_workload,
)


CONTROL_SCHEMA = "opentallas.tensor_accelerator.qwen_dynamic_generation_control.v1"
CONTROL_VERSION = "tensor-accelerator-qwen-dynamic-generation-control-0.1.0"
EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_controlled_dynamic_session_execution.v1"
)
RUNNER_VERSION = "tensor-accelerator-qwen-controlled-dynamic-runner-0.1.0"

_COUNTER_NAME = re.compile(
    r"^(?:arithmetic|commands|hbm|matrix|sram|state)\.[A-Za-z0-9_.]+$"
)


class QwenDynamicControlError(ArtifactError):
    """Raised when controlled dynamic generation is incomplete or illegitimate."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenDynamicControlError(f"{label} identity differs")


def _integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise QwenDynamicControlError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _resolve_case(
    workload: Mapping[str, Any], kind: str, case_id: str, turn: int | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    if kind == "natural_question" and turn is None:
        records = [
            record
            for record in workload["natural_questions"]
            if record["id"] == case_id
        ]
        if len(records) != 1:
            raise QwenDynamicControlError("natural workload case differs")
        return records[0]["prompt"], records[0]["expected"]
    if kind == "agent_turn" and turn is not None:
        tasks = [record for record in workload["agent"]["tasks"] if record["id"] == case_id]
        if len(tasks) != 1:
            raise QwenDynamicControlError("agent workload case differs")
        turns = [record for record in tasks[0]["expected"]["turns"] if record["turn"] == turn]
        if len(turns) != 1:
            raise QwenDynamicControlError("agent workload turn differs")
        return turns[0]["prompt"], turns[0]["expected"]
    raise QwenDynamicControlError("controlled workload binding differs")


def _binding(
    workload: Mapping[str, Any], kind: str, case_id: str, turn: int | None
) -> dict[str, Any]:
    prompt, expected = _resolve_case(workload, kind, case_id, turn)
    return {
        "case_id": case_id,
        "expected_generated_token_count": expected["generated_token_count"],
        "expected_generated_token_sha256": sha256_bytes(
            canonical_json_bytes(expected["generated_token_ids"])
        ),
        "expected_rom_result_id": expected["rom_result_id"],
        "kind": kind,
        "prompt_text_utf8_sha256": prompt["prompt_text_utf8_sha256"],
        "prompt_token_count": prompt["prompt_token_count"],
        "prompt_token_sha256": prompt["prompt_token_sha256"],
        "turn": turn,
    }


def build_dynamic_generation_control(
    session_value: Mapping[str, Any],
    workload_value: Mapping[str, Any],
    *,
    kind: str,
    case_id: str,
    turn: int | None = None,
) -> dict[str, Any]:
    """Bind one immutable V1 session to one frozen semantic workload case."""

    session = validate_dynamic_session(session_value)
    workload = validate_shared_workload(workload_value)
    binding = _binding(workload, kind, case_id, turn)
    prompt, _ = _resolve_case(workload, kind, case_id, turn)
    expected_limit = (
        session["context_capacity"] - prompt["prompt_token_count"] + 1
        if kind == "natural_question"
        else min(
            workload["agent"]["maximum_new_tokens_per_turn"],
            session["context_capacity"] - prompt["prompt_token_count"] + 1,
        )
    )
    if (
        session["checkpoint_lock_id"] != workload["model"]["checkpoint_lock_id"]
        or session["prompt"]
        != {
            "text": prompt["prompt_text"],
            "token_count": prompt["prompt_token_count"],
            "token_ids": prompt["prompt_token_ids"],
            "utf8_sha256": prompt["prompt_text_utf8_sha256"],
        }
        or session["generation"]
        != {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "generated_token_limit": expected_limit,
            "selection": "greedy_lowest_token_id_argmax",
            "unexpected_early_eos": "fail",
        }
    ):
        raise QwenDynamicControlError(
            "base dynamic session does not match its governed workload"
        )
    body: dict[str, Any] = {
        "base_session_id": session["session_id"],
        "build_id": session["build_id"],
        "checkpoint_lock_id": session["checkpoint_lock_id"],
        "claim_boundary": {
            "changes_model_forward_execution": False,
            "eos_terminated_decode_control": True,
            "semantic_golden_bound": True,
            "token_legitimacy_fail_closed": True,
            "timing_or_performance": False,
        },
        "control_version": CONTROL_VERSION,
        "generation": {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "eos_token_included_in_generated_sequence": True,
            "maximum_generated_token_count": expected_limit,
            "selection": "greedy_lowest_token_id_argmax",
            "stop_rule": "first_eos_or_maximum_generated_token_count",
            "undecodable_token_policy": "fail_closed_before_report_publication",
        },
        "graph_id": session["graph_id"],
        "model_id": "qwen3-8b",
        "schema": CONTROL_SCHEMA,
        "tokenizer_contract": {
            "base_vocabulary_size": BASE_VOCABULARY_SIZE,
            "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
            "model_vocabulary_size": MODEL_VOCABULARY_SIZE,
            "padded_model_token_policy": "reject_if_selected_for_generation",
        },
        "workload_binding": binding,
        "workload_id": workload["workload_id"],
    }
    return validate_dynamic_generation_control(
        _identified(body, "control_id"), session, workload
    )


def validate_dynamic_generation_control(
    value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    workload_value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a dynamic EOS overlay without changing its V1 base session."""

    try:
        session = validate_dynamic_session(session_value)
        workload = validate_shared_workload(workload_value)
    except (QwenDynamicArtifactError, QwenWorkloadError) as exc:
        raise QwenDynamicControlError(f"controlled base artifact differs: {exc}") from exc
    control = dict(value)
    exact_keys(
        control,
        {
            "base_session_id",
            "build_id",
            "checkpoint_lock_id",
            "claim_boundary",
            "control_id",
            "control_version",
            "generation",
            "graph_id",
            "model_id",
            "schema",
            "tokenizer_contract",
            "workload_binding",
            "workload_id",
        },
        set(),
        "dynamic generation control",
    )
    _identity(control, "control_id", "dynamic generation control")
    binding = control["workload_binding"]
    if not isinstance(binding, dict):
        raise QwenDynamicControlError("controlled workload binding must be an object")
    exact_keys(
        binding,
        {
            "case_id",
            "expected_generated_token_count",
            "expected_generated_token_sha256",
            "expected_rom_result_id",
            "kind",
            "prompt_text_utf8_sha256",
            "prompt_token_count",
            "prompt_token_sha256",
            "turn",
        },
        set(),
        "controlled workload binding",
    )
    expected_binding = _binding(
        workload, binding["kind"], binding["case_id"], binding["turn"]
    )
    prompt, _ = _resolve_case(
        workload, binding["kind"], binding["case_id"], binding["turn"]
    )
    expected_limit = (
        session["context_capacity"] - prompt["prompt_token_count"] + 1
        if binding["kind"] == "natural_question"
        else min(
            workload["agent"]["maximum_new_tokens_per_turn"],
            session["context_capacity"] - prompt["prompt_token_count"] + 1,
        )
    )
    if (
        control["schema"] != CONTROL_SCHEMA
        or control["control_version"] != CONTROL_VERSION
        or control["base_session_id"] != session["session_id"]
        or control["build_id"] != session["build_id"]
        or control["checkpoint_lock_id"] != session["checkpoint_lock_id"]
        or control["graph_id"] != session["graph_id"]
        or control["model_id"] != "qwen3-8b"
        or control["workload_id"] != workload["workload_id"]
        or binding != expected_binding
        or control["claim_boundary"]
        != {
            "changes_model_forward_execution": False,
            "eos_terminated_decode_control": True,
            "semantic_golden_bound": True,
            "token_legitimacy_fail_closed": True,
            "timing_or_performance": False,
        }
        or control["generation"]
        != {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "eos_token_included_in_generated_sequence": True,
            "maximum_generated_token_count": expected_limit,
            "selection": "greedy_lowest_token_id_argmax",
            "stop_rule": "first_eos_or_maximum_generated_token_count",
            "undecodable_token_policy": "fail_closed_before_report_publication",
        }
        or control["tokenizer_contract"]
        != {
            "base_vocabulary_size": BASE_VOCABULARY_SIZE,
            "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
            "model_vocabulary_size": MODEL_VOCABULARY_SIZE,
            "padded_model_token_policy": "reject_if_selected_for_generation",
        }
        or session["prompt"]["token_ids"] != prompt["prompt_token_ids"]
        or session["prompt"]["text"] != prompt["prompt_text"]
        or session["generation"]["generated_token_limit"] != expected_limit
    ):
        raise QwenDynamicControlError("dynamic generation control boundary differs")
    return control


def generated_token_record(
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    workload_value: Mapping[str, Any],
    chat: QwenChatTokenizer,
    *,
    generated_token_index: int,
    token_id: int,
) -> dict[str, Any]:
    """Reject padded rows and retain exact per-token decoding evidence."""

    control = validate_dynamic_generation_control(
        control_value, session_value, workload_value
    )
    index = _integer(
        generated_token_index,
        "generated token index",
        0,
        control["generation"]["maximum_generated_token_count"] - 1,
    )
    token = _integer(token_id, "generated token ID", 0, MODEL_VOCABULARY_SIZE - 1)
    if token >= EXPLICIT_VOCABULARY_SIZE:
        raise QwenDynamicControlError(
            f"generated token ID {token} selects an undecodable padded model row"
        )
    token_string = chat.tokenizer.id_to_token(token)
    if token_string is None:
        raise QwenDynamicControlError(
            f"generated token ID {token} has no authenticated tokenizer entry"
        )
    added = chat.tokenizer.get_added_tokens_decoder().get(token)
    return {
        "decoded_piece_raw": chat.decode([token], skip_special_tokens=False),
        "decoded_piece_visible": chat.decode([token], skip_special_tokens=True),
        "generated_token_index": index,
        "is_eos": token in EOS_TOKEN_IDS,
        "is_special": bool(added is not None and added.special),
        "token": token_string,
        "token_id": token,
        "vocabulary_class": "base" if token < BASE_VOCABULARY_SIZE else "added",
    }


def controlled_stop_reason(
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    workload_value: Mapping[str, Any],
    *,
    generated_token_count: int,
    latest_generated_token_id: int,
) -> str | None:
    control = validate_dynamic_generation_control(
        control_value, session_value, workload_value
    )
    count = _integer(
        generated_token_count,
        "generated token count",
        1,
        control["generation"]["maximum_generated_token_count"],
    )
    token = _integer(
        latest_generated_token_id,
        "latest generated token ID",
        0,
        EXPLICIT_VOCABULARY_SIZE - 1,
    )
    if token in EOS_TOKEN_IDS:
        return "eos"
    if count == control["generation"]["maximum_generated_token_count"]:
        return "maximum_generated_token_count"
    return None


def _comparison(
    expected: Mapping[str, Any], generated: list[int], raw: str, visible: str
) -> dict[str, Any]:
    expected_ids = expected["generated_token_ids"]
    first_divergence: int | None = None
    for index in range(max(len(expected_ids), len(generated))):
        left = expected_ids[index] if index < len(expected_ids) else None
        right = generated[index] if index < len(generated) else None
        if left != right:
            first_divergence = index
            break
    exact_ids = generated == expected_ids
    exact_raw = raw == expected["generated_text_raw"]
    exact_visible = visible == expected["generated_text_visible"]
    exact_eos = bool(
        generated
        and generated[-1] == expected["eos_token_id"]
        and not any(token in EOS_TOKEN_IDS for token in generated[:-1])
    )
    return {
        "exact_eos": exact_eos,
        "exact_generated_text_raw": exact_raw,
        "exact_generated_text_visible": exact_visible,
        "exact_generated_token_ids": exact_ids,
        "first_token_divergence_index": first_divergence,
        "rom_result_id": expected["rom_result_id"],
        "status": (
            "exact_match"
            if exact_ids and exact_raw and exact_visible and exact_eos
            else "mismatch"
        ),
    }


def _validate_token_record(
    value: object,
    *,
    generated_token_index: int,
    token_id: int,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QwenDynamicControlError("controlled token record must be an object")
    exact_keys(
        value,
        {
            "decoded_piece_raw",
            "decoded_piece_visible",
            "generated_token_index",
            "is_eos",
            "is_special",
            "token",
            "token_id",
            "vocabulary_class",
        },
        set(),
        f"controlled token record {generated_token_index}",
    )
    if (
        value["generated_token_index"] != generated_token_index
        or value["token_id"] != token_id
        or value["is_eos"] != (token_id in EOS_TOKEN_IDS)
        or value["vocabulary_class"]
        != ("base" if token_id < BASE_VOCABULARY_SIZE else "added")
        or not isinstance(value["is_special"], bool)
        or not isinstance(value["token"], str)
        or not value["token"]
        or not isinstance(value["decoded_piece_raw"], str)
        or not isinstance(value["decoded_piece_visible"], str)
    ):
        raise QwenDynamicControlError("controlled token record boundary differs")
    return value


def _validate_step_chain(
    steps_value: object,
    *,
    execution: Mapping[str, Any],
    session: Mapping[str, Any],
    generated: Sequence[int],
) -> list[dict[str, Any]]:
    if (
        not isinstance(steps_value, list)
        or len(steps_value) != execution["transaction_count"]
        or execution["step_chain_sha256"]
        != sha256_bytes(canonical_json_bytes(steps_value))
    ):
        raise QwenDynamicControlError("controlled step chain differs")
    required = {
        "generated_token_index",
        "input_role",
        "input_token_id",
        "is_terminal_decision",
        "logits_sha256",
        "output_role",
        "output_token_id",
        "phase",
        "previous_report_id",
        "report_id",
        "report_sha256",
        "report_size_bytes",
        "request_id",
        "state_generation",
        "state_length",
        "state_metadata_after_sha256",
        "state_metadata_before_sha256",
        "step_index",
    }
    prompt_ids = session["prompt"]["token_ids"]
    prompt_count = len(prompt_ids)
    previous_report_id: str | None = None
    previous_metadata: str | None = None
    for index, step in enumerate(steps_value):
        if not isinstance(step, dict):
            raise QwenDynamicControlError("controlled step must be an object")
        exact_keys(step, required, set(), f"controlled step {index}")
        prompt_input = index < prompt_count
        generated_index = None if index < prompt_count - 1 else index - prompt_count + 1
        expected_input = (
            prompt_ids[index]
            if prompt_input
            else generated[generated_index - 1]
        )
        expected_output = (
            None if generated_index is None else generated[generated_index]
        )
        for field in (
            "logits_sha256",
            "report_id",
            "report_sha256",
            "request_id",
            "state_metadata_after_sha256",
            "state_metadata_before_sha256",
        ):
            require_sha256(step[field], f"controlled step {index}.{field}")
        if step["previous_report_id"] is not None:
            require_sha256(
                step["previous_report_id"],
                f"controlled step {index}.previous_report_id",
            )
        if (
            step["step_index"] != index
            or step["generated_token_index"] != generated_index
            or step["input_role"] != ("prompt" if prompt_input else "generated")
            or step["input_token_id"] != expected_input
            or step["output_role"]
            != ("prefill_intermediate" if generated_index is None else "generated_token")
            or (expected_output is not None and step["output_token_id"] != expected_output)
            or isinstance(step["output_token_id"], bool)
            or not isinstance(step["output_token_id"], int)
            or not 0 <= step["output_token_id"] < MODEL_VOCABULARY_SIZE
            or step["phase"] != ("prefill" if prompt_input else "decode")
            or step["previous_report_id"] != previous_report_id
            or step["state_generation"] != index + 1
            or step["state_length"] != index + 1
            or step["is_terminal_decision"] != (index == len(steps_value) - 1)
            or isinstance(step["report_size_bytes"], bool)
            or not isinstance(step["report_size_bytes"], int)
            or step["report_size_bytes"] < 1
            or (
                previous_metadata is not None
                and step["state_metadata_before_sha256"] != previous_metadata
            )
        ):
            raise QwenDynamicControlError(
                "controlled step chain or token causality differs"
            )
        previous_report_id = step["report_id"]
        previous_metadata = step["state_metadata_after_sha256"]
    return steps_value


def build_controlled_dynamic_execution(
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    workload_value: Mapping[str, Any],
    request_values: Sequence[Mapping[str, Any]],
    report_values: Sequence[Mapping[str, Any]],
    *,
    chat: QwenChatTokenizer,
) -> dict[str, Any]:
    """Aggregate one EOS-terminated or maximum-bounded dynamic session."""

    session = validate_dynamic_session(session_value)
    workload = validate_shared_workload(workload_value, chat=chat)
    control = validate_dynamic_generation_control(control_value, session, workload)
    if len(request_values) != len(report_values):
        raise QwenDynamicControlError("controlled request/report coverage differs")
    prompt_count = session["prompt"]["token_count"]
    if not prompt_count <= len(report_values) <= (
        prompt_count + control["generation"]["maximum_generated_token_count"] - 1
    ):
        raise QwenDynamicControlError("controlled transaction count differs")

    generated: list[int] = []
    token_records: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    counter_keys: set[str] | None = None
    previous: dict[str, Any] | None = None
    previous_metadata: str | None = None
    for index, (raw_request, raw_report) in enumerate(
        zip(request_values, report_values, strict=True)
    ):
        try:
            request = validate_dynamic_request(raw_request, session, previous)
            report = validate_dynamic_transaction_report(
                raw_report, session, request, previous
            )
        except QwenDynamicArtifactError as exc:
            raise QwenDynamicControlError(
                f"controlled transaction {index} differs: {exc}"
            ) from exc
        keys = set(report["counters"])
        if counter_keys is None:
            counter_keys = keys
        elif keys != counter_keys:
            raise QwenDynamicControlError("controlled counter key sets differ")
        binding = report["runtime_binding"]
        if (
            previous_metadata is not None
            and binding["state_metadata_before_sha256"] != previous_metadata
        ):
            raise QwenDynamicControlError("controlled state-metadata chain differs")
        output_token = report["outputs"]["committed_logits"]["greedy_token_id"]
        token_record: dict[str, Any] | None = None
        if request["output_role"] == "generated_token":
            token_record = generated_token_record(
                control,
                session,
                workload,
                chat,
                generated_token_index=request["generated_token_index"],
                token_id=output_token,
            )
            generated.append(output_token)
            token_records.append(token_record)
            if token_record["is_eos"] and index != len(report_values) - 1:
                raise QwenDynamicControlError(
                    "controlled execution continues after the first EOS token"
                )
        payload = canonical_json_bytes(report)
        state = report["state"][0]
        steps.append(
            {
                "generated_token_index": request["generated_token_index"],
                "input_role": request["input_role"],
                "input_token_id": request["token_id"],
                "is_terminal_decision": index == len(report_values) - 1,
                "logits_sha256": report["outputs"]["committed_logits"][
                    "payload_sha256"
                ],
                "output_role": request["output_role"],
                "output_token_id": output_token,
                "phase": request["phase"],
                "previous_report_id": request["previous_report_id"],
                "report_id": report["report_id"],
                "report_sha256": hashlib.sha256(payload).hexdigest(),
                "report_size_bytes": len(payload),
                "request_id": request["request_id"],
                "state_generation": state["generation"],
                "state_length": state["length"],
                "state_metadata_after_sha256": binding[
                    "state_metadata_after_sha256"
                ],
                "state_metadata_before_sha256": binding[
                    "state_metadata_before_sha256"
                ],
                "step_index": index,
            }
        )
        counters.update(report["counters"])
        previous = report
        previous_metadata = binding["state_metadata_after_sha256"]
    if not generated or previous is None:
        raise QwenDynamicControlError("controlled execution has no token decision")
    stop_reason = controlled_stop_reason(
        control,
        session,
        workload,
        generated_token_count=len(generated),
        latest_generated_token_id=generated[-1],
    )
    if stop_reason is None:
        raise QwenDynamicControlError(
            "controlled execution stops before EOS or the generated-token maximum"
        )
    if len(report_values) != prompt_count + len(generated) - 1:
        raise QwenDynamicControlError(
            "controlled transaction/generated-token derivation differs"
        )
    decoded = {
        "full_text_raw": chat.decode(
            [*session["prompt"]["token_ids"], *generated],
            skip_special_tokens=False,
        ),
        "full_text_visible": chat.decode(
            [*session["prompt"]["token_ids"], *generated],
            skip_special_tokens=True,
        ),
        "generated_text_raw": chat.decode(generated, skip_special_tokens=False),
        "generated_text_visible": chat.decode(generated, skip_special_tokens=True),
        "prompt_text_raw": chat.decode(
            session["prompt"]["token_ids"], skip_special_tokens=False
        ),
        "prompt_text_visible": chat.decode(
            session["prompt"]["token_ids"], skip_special_tokens=True
        ),
    }
    _, expected = _resolve_case(
        workload,
        control["workload_binding"]["kind"],
        control["workload_binding"]["case_id"],
        control["workload_binding"]["turn"],
    )
    comparison = _comparison(
        expected,
        generated,
        decoded["generated_text_raw"],
        decoded["generated_text_visible"],
    )
    aggregate = dict(sorted(counters.items()))
    body: dict[str, Any] = {
        "aggregate_counter_sha256": sha256_bytes(canonical_json_bytes(aggregate)),
        "aggregate_counters": aggregate,
        "base_session_id": session["session_id"],
        "build_id": session["build_id"],
        "claim_boundary": {
            "artifact_only_dynamic_session_executed": True,
            "semantic_rom_golden_exact": comparison["status"] == "exact_match",
            "target_precision_reference_verified": False,
            "token_legitimacy_verified": True,
            "timing_or_performance": False,
        },
        "comparison": comparison,
        "control_id": control["control_id"],
        "decode_transaction_count": sum(
            step["phase"] == "decode" for step in steps
        ),
        "decoded": decoded,
        "eos_observed": stop_reason == "eos",
        "final_state": previous["state"],
        "generated_token_count": len(generated),
        "generated_token_ids": generated,
        "graph_id": session["graph_id"],
        "mode": "artifact_only_data_bearing_controlled_dynamic_session",
        "prompt_token_count": prompt_count,
        "prompt_token_ids": session["prompt"]["token_ids"],
        "runner_version": RUNNER_VERSION,
        "schema": EXECUTION_SCHEMA,
        "status": "pass" if comparison["status"] == "exact_match" else "fail",
        "step_chain_sha256": sha256_bytes(canonical_json_bytes(steps)),
        "steps": steps,
        "stop_reason": stop_reason,
        "timing": {"reason": "capability_uncharacterized", "status": "unavailable"},
        "token_legitimacy": {
            "all_generated_token_ids_resolve": True,
            "all_generated_token_ids_within_explicit_vocabulary": True,
            "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
            "padded_model_rows_rejected": True,
            "records": token_records,
        },
        "transaction_count": len(report_values),
        "workload_binding": control["workload_binding"],
        "workload_id": workload["workload_id"],
    }
    return validate_controlled_dynamic_execution(
        _identified(body, "controlled_execution_id"),
        control,
        session,
        workload,
        chat=chat,
    )


def validate_controlled_dynamic_execution(
    value: Mapping[str, Any],
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    workload_value: Mapping[str, Any],
    *,
    chat: QwenChatTokenizer | None = None,
) -> dict[str, Any]:
    """Independently validate a controlled aggregate and optional tokenizer data."""

    session = validate_dynamic_session(session_value)
    workload = validate_shared_workload(workload_value, chat=chat)
    control = validate_dynamic_generation_control(control_value, session, workload)
    execution = dict(value)
    required = {
        "aggregate_counter_sha256",
        "aggregate_counters",
        "base_session_id",
        "build_id",
        "claim_boundary",
        "comparison",
        "control_id",
        "controlled_execution_id",
        "decode_transaction_count",
        "decoded",
        "eos_observed",
        "final_state",
        "generated_token_count",
        "generated_token_ids",
        "graph_id",
        "mode",
        "prompt_token_count",
        "prompt_token_ids",
        "runner_version",
        "schema",
        "status",
        "step_chain_sha256",
        "steps",
        "stop_reason",
        "timing",
        "token_legitimacy",
        "transaction_count",
        "workload_binding",
        "workload_id",
    }
    exact_keys(execution, required, set(), "controlled dynamic execution")
    _identity(execution, "controlled_execution_id", "controlled dynamic execution")
    generated = execution["generated_token_ids"]
    if (
        not isinstance(generated, list)
        or not generated
        or any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or not 0 <= token < EXPLICIT_VOCABULARY_SIZE
            for token in generated
        )
    ):
        raise QwenDynamicControlError("controlled generated tokens differ")
    stop_reason = (
        "eos"
        if generated[-1] in EOS_TOKEN_IDS
        else "maximum_generated_token_count"
        if len(generated) == control["generation"]["maximum_generated_token_count"]
        else None
    )
    if any(token in EOS_TOKEN_IDS for token in generated[:-1]):
        raise QwenDynamicControlError("controlled tokens continue after EOS")
    prompt_count = session["prompt"]["token_count"]
    if (
        execution["schema"] != EXECUTION_SCHEMA
        or execution["runner_version"] != RUNNER_VERSION
        or execution["mode"]
        != "artifact_only_data_bearing_controlled_dynamic_session"
        or execution["base_session_id"] != session["session_id"]
        or execution["control_id"] != control["control_id"]
        or execution["build_id"] != session["build_id"]
        or execution["graph_id"] != session["graph_id"]
        or execution["workload_id"] != workload["workload_id"]
        or execution["workload_binding"] != control["workload_binding"]
        or execution["prompt_token_count"] != prompt_count
        or execution["prompt_token_ids"] != session["prompt"]["token_ids"]
        or execution["generated_token_count"] != len(generated)
        or execution["transaction_count"] != prompt_count + len(generated) - 1
        or execution["decode_transaction_count"] != len(generated) - 1
        or execution["stop_reason"] != stop_reason
        or execution["eos_observed"] != (stop_reason == "eos")
        or execution["timing"]
        != {"reason": "capability_uncharacterized", "status": "unavailable"}
    ):
        raise QwenDynamicControlError("controlled dynamic execution boundary differs")
    _, expected = _resolve_case(
        workload,
        control["workload_binding"]["kind"],
        control["workload_binding"]["case_id"],
        control["workload_binding"]["turn"],
    )
    decoded = execution["decoded"]
    if not isinstance(decoded, dict) or set(decoded) != {
        "full_text_raw",
        "full_text_visible",
        "generated_text_raw",
        "generated_text_visible",
        "prompt_text_raw",
        "prompt_text_visible",
    }:
        raise QwenDynamicControlError("controlled decoded boundary differs")
    if (
        any(not isinstance(item, str) for item in decoded.values())
        or decoded["prompt_text_raw"] != session["prompt"]["text"]
    ):
        raise QwenDynamicControlError("controlled decoded text differs")
    expected_comparison = _comparison(
        expected,
        generated,
        decoded["generated_text_raw"],
        decoded["generated_text_visible"],
    )
    comparison = execution["comparison"]
    if not isinstance(comparison, dict):
        raise QwenDynamicControlError("controlled comparison must be an object")
    exact_keys(
        comparison,
        {
            "exact_eos",
            "exact_generated_text_raw",
            "exact_generated_text_visible",
            "exact_generated_token_ids",
            "first_token_divergence_index",
            "rom_result_id",
            "status",
        },
        set(),
        "controlled comparison",
    )
    if (
        comparison != expected_comparison
        or execution["status"]
        != ("pass" if expected_comparison["status"] == "exact_match" else "fail")
        or execution["claim_boundary"]
        != {
            "artifact_only_dynamic_session_executed": True,
            "semantic_rom_golden_exact": expected_comparison["status"]
            == "exact_match",
            "target_precision_reference_verified": False,
            "token_legitimacy_verified": True,
            "timing_or_performance": False,
        }
    ):
        raise QwenDynamicControlError("controlled semantic comparison differs")
    _validate_step_chain(
        execution["steps"],
        execution=execution,
        session=session,
        generated=generated,
    )
    counters = execution["aggregate_counters"]
    if (
        not isinstance(counters, dict)
        or len(counters) != 70
        or any(
            not isinstance(key, str)
            or _COUNTER_NAME.fullmatch(key) is None
            or isinstance(counter, bool)
            or not isinstance(counter, int)
            or counter < 0
            for key, counter in counters.items()
        )
        or execution["aggregate_counter_sha256"]
        != sha256_bytes(canonical_json_bytes(counters))
    ):
        raise QwenDynamicControlError("controlled aggregate counters differ")
    final_state = execution["final_state"]
    if not isinstance(final_state, list) or len(final_state) != 36:
        raise QwenDynamicControlError("controlled final state coverage differs")
    for layer, state in enumerate(final_state):
        if not isinstance(state, dict):
            raise QwenDynamicControlError("controlled final state must be an object")
        exact_keys(
            state,
            {
                "generation",
                "key_payload_sha256",
                "layer",
                "length",
                "resource_id",
                "value_payload_sha256",
            },
            set(),
            f"controlled final state {layer}",
        )
        require_sha256(
            state["key_payload_sha256"],
            f"controlled final state {layer}.key_payload_sha256",
        )
        require_sha256(
            state["value_payload_sha256"],
            f"controlled final state {layer}.value_payload_sha256",
        )
        if (
            state["layer"] != layer
            or state.get("resource_id") != f"kv.layer.{layer}"
            or state.get("generation") != execution["transaction_count"]
            or state.get("length") != execution["transaction_count"]
        ):
            raise QwenDynamicControlError("controlled final state differs")
    legitimacy = execution["token_legitimacy"]
    records = legitimacy.get("records") if isinstance(legitimacy, dict) else None
    if (
        not isinstance(legitimacy, dict)
        or set(legitimacy)
        != {
            "all_generated_token_ids_resolve",
            "all_generated_token_ids_within_explicit_vocabulary",
            "explicit_vocabulary_size",
            "padded_model_rows_rejected",
            "records",
        }
        or legitimacy.get("all_generated_token_ids_resolve") is not True
        or legitimacy.get("all_generated_token_ids_within_explicit_vocabulary")
        is not True
        or legitimacy.get("explicit_vocabulary_size") != EXPLICIT_VOCABULARY_SIZE
        or legitimacy.get("padded_model_rows_rejected") is not True
        or not isinstance(records, list)
        or len(records) != len(generated)
    ):
        raise QwenDynamicControlError("controlled token legitimacy differs")
    for index, (record, token) in enumerate(zip(records, generated, strict=True)):
        _validate_token_record(
            record,
            generated_token_index=index,
            token_id=token,
        )
    if chat is not None:
        expected_records = [
            generated_token_record(
                control,
                session,
                workload,
                chat,
                generated_token_index=index,
                token_id=token,
            )
            for index, token in enumerate(generated)
        ]
        expected_decoded = {
            "full_text_raw": chat.decode(
                [*session["prompt"]["token_ids"], *generated],
                skip_special_tokens=False,
            ),
            "full_text_visible": chat.decode(
                [*session["prompt"]["token_ids"], *generated],
                skip_special_tokens=True,
            ),
            "generated_text_raw": chat.decode(generated, skip_special_tokens=False),
            "generated_text_visible": chat.decode(
                generated, skip_special_tokens=True
            ),
            "prompt_text_raw": chat.decode(
                session["prompt"]["token_ids"], skip_special_tokens=False
            ),
            "prompt_text_visible": chat.decode(
                session["prompt"]["token_ids"], skip_special_tokens=True
            ),
        }
        if records != expected_records or decoded != expected_decoded:
            raise QwenDynamicControlError("controlled tokenizer evidence differs")
    return execution


def publish_dynamic_generation_control(
    value: Mapping[str, Any],
    session: Mapping[str, Any],
    workload: Mapping[str, Any],
    output: Path,
) -> None:
    control = validate_dynamic_generation_control(value, session, workload)
    try:
        publish_bytes_atomic_no_replace(Path(output), canonical_json_bytes(control))
    except FileExistsError as exc:
        raise QwenDynamicControlError(
            f"dynamic generation control already exists: {output}"
        ) from exc
    except OSError as exc:
        raise QwenDynamicControlError(
            f"cannot publish dynamic generation control: {exc}"
        ) from exc


def publish_controlled_dynamic_execution(
    value: Mapping[str, Any],
    control: Mapping[str, Any],
    session: Mapping[str, Any],
    workload: Mapping[str, Any],
    output: Path,
) -> None:
    execution = validate_controlled_dynamic_execution(
        value, control, session, workload
    )
    try:
        publish_bytes_atomic_no_replace(Path(output), canonical_json_bytes(execution))
    except FileExistsError as exc:
        raise QwenDynamicControlError(
            f"controlled dynamic execution already exists: {output}"
        ) from exc
    except OSError as exc:
        raise QwenDynamicControlError(
            f"cannot publish controlled dynamic execution: {exc}"
        ) from exc


__all__ = [
    "CONTROL_SCHEMA",
    "CONTROL_VERSION",
    "EXECUTION_SCHEMA",
    "QwenDynamicControlError",
    "RUNNER_VERSION",
    "build_controlled_dynamic_execution",
    "build_dynamic_generation_control",
    "controlled_stop_reason",
    "generated_token_record",
    "publish_controlled_dynamic_execution",
    "publish_dynamic_generation_control",
    "validate_controlled_dynamic_execution",
    "validate_dynamic_generation_control",
]
