"""Versioned runtime artifacts for dynamic Qwen prefill and greedy decode.

The complete physical deployment and ABI 2.5 command program are reusable.  A
dynamic session binds tokenizer input, prompt tokens, stopping policy, and a
content-addressed request/report chain without changing fixed request v1 or the
compiled command bytes.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
import hashlib
import os
from pathlib import Path
from typing import Any

from tokenizers import Tokenizer, __version__ as tokenizers_version

from compiler.frontend.checkpoint import CheckpointError, load_checkpoint_lock

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
from .production_model import (
    ProductionModelGraphError,
    load_production_model_graph,
)


SESSION_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_dynamic_session.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_dynamic_request.v1"
EXECUTION_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_dynamic_execution.v1"
SESSION_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_dynamic_session_execution.v1"
)
SESSION_VERSION = "tensor-accelerator-qwen-dynamic-session-0.2.0"
REQUEST_VERSION = "tensor-accelerator-qwen-dynamic-request-0.1.0"
SESSION_RUNNER_VERSION = "tensor-accelerator-qwen-dynamic-session-runner-0.1.0"

MODEL_ID = "qwen3-8b"
VOCABULARY_SIZE = 151_936
STATE_COUNT = 36
CONTEXT_CAPACITY = 8_000
MINIMUM_GENERATED_TOKENS = 32
TOKENIZERS_VERSION = "0.22.2"
TOKENIZER_PATH = "tokenizer.json"
GENERATION_CONFIG_PATH = "generation_config.json"


class QwenDynamicArtifactError(ArtifactError):
    """Raised when a dynamic Qwen session/request chain is not exact."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenDynamicArtifactError(f"{label} identity differs")


def _integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise QwenDynamicArtifactError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _token_ids(value: object, label: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise QwenDynamicArtifactError(f"{label} must be a nonempty list")
    return [
        _integer(token, f"{label}[{index}]", 0, VOCABULARY_SIZE - 1)
        for index, token in enumerate(value)
    ]


def _file_record(lock: Mapping[str, Any], logical_path: str) -> Mapping[str, Any]:
    records = [item for item in lock["files"] if item.get("path") == logical_path]
    if len(records) != 1:
        raise QwenDynamicArtifactError(
            f"checkpoint lock must contain one {logical_path!r} file record"
        )
    return records[0]


def _canonical_file(snapshot: Path, record: Mapping[str, Any], label: str) -> Path:
    path = Path(snapshot) / str(record["path"])
    digest, size = sha256_file(path)
    if (digest, size) != (record.get("sha256"), record.get("size_bytes")):
        raise QwenDynamicArtifactError(f"{label} differs from its checkpoint lock")
    return path


def validate_dynamic_session(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one canonical dynamic-session value independently of I/O."""

    session = dict(value)
    exact_keys(
        session,
        {
            "build_id",
            "checkpoint_lock_id",
            "claim_boundary",
            "command_program_sha256",
            "context_capacity",
            "generation",
            "graph_id",
            "model_id",
            "prompt",
            "schema",
            "session_id",
            "session_version",
            "tokenizer",
        },
        set(),
        "dynamic session",
    )
    _identity(session, "session_id", "dynamic session")
    for field in (
        "build_id",
        "checkpoint_lock_id",
        "command_program_sha256",
        "graph_id",
    ):
        require_sha256(session[field], f"dynamic session.{field}")
    if (
        session["schema"] != SESSION_SCHEMA
        or session["session_version"] != SESSION_VERSION
        or session["model_id"] != MODEL_ID
        or session["context_capacity"] != CONTEXT_CAPACITY
        or session["claim_boundary"]
        != {
            "exact_8000_token_acceptance": False,
            "short_generation": True,
            "timing_or_performance": False,
        }
    ):
        raise QwenDynamicArtifactError("dynamic session boundary differs")

    tokenizer = session["tokenizer"]
    if not isinstance(tokenizer, dict):
        raise QwenDynamicArtifactError("dynamic session tokenizer must be an object")
    exact_keys(
        tokenizer,
        {
            "decoded_prompt_exact",
            "library",
            "library_version",
            "path",
            "sha256",
            "vocabulary_size",
        },
        set(),
        "dynamic session tokenizer",
    )
    require_sha256(tokenizer["sha256"], "dynamic session tokenizer.sha256")
    if tokenizer != {
        "decoded_prompt_exact": True,
        "library": "tokenizers",
        "library_version": TOKENIZERS_VERSION,
        "path": TOKENIZER_PATH,
        "sha256": tokenizer["sha256"],
        "vocabulary_size": VOCABULARY_SIZE,
    }:
        raise QwenDynamicArtifactError("dynamic session tokenizer boundary differs")

    prompt = session["prompt"]
    if not isinstance(prompt, dict):
        raise QwenDynamicArtifactError("dynamic session prompt must be an object")
    exact_keys(
        prompt,
        {"text", "token_count", "token_ids", "utf8_sha256"},
        set(),
        "dynamic session prompt",
    )
    if not isinstance(prompt["text"], str) or not prompt["text"]:
        raise QwenDynamicArtifactError("dynamic session prompt text must be nonempty")
    prompt_ids = _token_ids(prompt["token_ids"], "dynamic session prompt.token_ids")
    if (
        prompt["token_count"] != len(prompt_ids)
        or prompt["utf8_sha256"]
        != hashlib.sha256(prompt["text"].encode("utf-8")).hexdigest()
    ):
        raise QwenDynamicArtifactError("dynamic session prompt identity differs")

    generation = session["generation"]
    if not isinstance(generation, dict):
        raise QwenDynamicArtifactError("dynamic session generation must be an object")
    exact_keys(
        generation,
        {
            "eos_token_ids",
            "generated_token_limit",
            "selection",
            "unexpected_early_eos",
        },
        set(),
        "dynamic session generation",
    )
    eos_ids = _token_ids(
        generation["eos_token_ids"], "dynamic session generation.eos_token_ids"
    )
    if len(set(eos_ids)) != len(eos_ids):
        raise QwenDynamicArtifactError("dynamic session EOS IDs are not unique")
    generated_limit = _integer(
        generation["generated_token_limit"],
        "dynamic session generated_token_limit",
        MINIMUM_GENERATED_TOKENS,
        CONTEXT_CAPACITY,
    )
    if (
        generation["selection"] != "greedy_lowest_token_id_argmax"
        or generation["unexpected_early_eos"] != "fail"
        or len(prompt_ids) + generated_limit - 1 > CONTEXT_CAPACITY
    ):
        raise QwenDynamicArtifactError("dynamic session generation boundary differs")
    return session


def build_dynamic_session(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    deployment_manifest_path: Path,
    physical_plan_path: Path,
    prompt_text: str,
    generated_token_limit: int = MINIMUM_GENERATED_TOKENS,
) -> dict[str, Any]:
    """Compile tokenizer text and deployment identities into a session artifact."""

    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        model = load_production_model_graph(Path(model_graph_path))
        manifest = load_strict_json(Path(deployment_manifest_path))
        plan = load_strict_json(Path(physical_plan_path))
    except (CheckpointError, OSError, ProductionModelGraphError) as exc:
        raise QwenDynamicArtifactError(
            f"cannot load dynamic-session inputs: {exc}"
        ) from exc
    if model.model_id != MODEL_ID:
        raise QwenDynamicArtifactError("dynamic session model differs")
    for value, field, label in (
        (manifest, "build_id", "deployment manifest"),
        (plan, "physical_plan_id", "physical plan"),
    ):
        _identity(value, field, label)
    if (
        manifest.get("graph_id") != model.graph_id
        or manifest.get("physical_plan_id") != plan["physical_plan_id"]
        or plan.get("graph_id") != model.graph_id
    ):
        raise QwenDynamicArtifactError("dynamic session deployment binding differs")
    if tokenizers_version != TOKENIZERS_VERSION:
        raise QwenDynamicArtifactError(
            f"tokenizers version differs: {tokenizers_version!r}"
        )
    tokenizer_record = _file_record(lock, TOKENIZER_PATH)
    tokenizer_path = _canonical_file(Path(snapshot), tokenizer_record, "Qwen tokenizer")
    generation_record = _file_record(lock, GENERATION_CONFIG_PATH)
    generation_path = _canonical_file(
        Path(snapshot), generation_record, "Qwen generation config"
    )
    try:
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        encoded = tokenizer.encode(prompt_text, add_special_tokens=False).ids
        decoded = tokenizer.decode(encoded, skip_special_tokens=False)
        generation_config = load_strict_json(generation_path)
    except Exception as exc:
        raise QwenDynamicArtifactError(
            f"cannot compile the dynamic-session tokenizer input: {exc}"
        ) from exc
    prompt_ids = _token_ids(list(encoded), "compiled prompt token IDs")
    if (
        decoded != prompt_text
        or tokenizer.get_vocab_size(with_added_tokens=True) != 151_669
    ):
        # Qwen's tokenizer JSON has 151,669 explicit entries while the model
        # vocabulary includes reserved model-output IDs through 151,935.
        raise QwenDynamicArtifactError("compiled prompt tokenizer round trip differs")
    raw_eos = generation_config.get("eos_token_id")
    if not isinstance(raw_eos, list):
        raw_eos = [raw_eos]
    eos_ids = _token_ids(raw_eos, "generation config EOS token IDs")
    body = {
        "build_id": require_sha256(manifest["build_id"], "manifest.build_id"),
        "checkpoint_lock_id": require_sha256(lock["lock_id"], "checkpoint lock ID"),
        "claim_boundary": {
            "exact_8000_token_acceptance": False,
            "short_generation": True,
            "timing_or_performance": False,
        },
        "command_program_sha256": require_sha256(
            plan["command_program"]["sha256"], "command program SHA-256"
        ),
        "context_capacity": CONTEXT_CAPACITY,
        "generation": {
            "eos_token_ids": eos_ids,
            "generated_token_limit": generated_token_limit,
            "selection": "greedy_lowest_token_id_argmax",
            "unexpected_early_eos": "fail",
        },
        "graph_id": model.graph_id,
        "model_id": MODEL_ID,
        "prompt": {
            "text": prompt_text,
            "token_count": len(prompt_ids),
            "token_ids": prompt_ids,
            "utf8_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        },
        "schema": SESSION_SCHEMA,
        "session_version": SESSION_VERSION,
        "tokenizer": {
            "decoded_prompt_exact": True,
            "library": "tokenizers",
            "library_version": TOKENIZERS_VERSION,
            "path": TOKENIZER_PATH,
            "sha256": tokenizer_record["sha256"],
            "vocabulary_size": VOCABULARY_SIZE,
        },
    }
    return validate_dynamic_session(_identified(body, "session_id"))


def _validate_previous_report(
    report: Mapping[str, Any], session: Mapping[str, Any]
) -> dict[str, Any]:
    value = dict(report)
    _identity(value, "report_id", "previous dynamic execution report")
    if (
        value.get("schema") != EXECUTION_SCHEMA
        or value.get("status") != "pass"
        or value.get("session_id") != session["session_id"]
        or value.get("build_id") != session["build_id"]
        or value.get("graph_id") != session["graph_id"]
        or not isinstance(value.get("step_index"), int)
        or not isinstance(value.get("outputs"), dict)
        or not isinstance(value["outputs"].get("committed_logits"), dict)
    ):
        raise QwenDynamicArtifactError("previous dynamic report boundary differs")
    token = value["outputs"]["committed_logits"].get("greedy_token_id")
    _integer(token, "previous dynamic report greedy token", 0, VOCABULARY_SIZE - 1)
    return value


def _transaction_id(body: Mapping[str, Any]) -> int:
    seed = {
        "previous_report_id": body["previous_report_id"],
        "session_id": body["session_id"],
        "step_index": body["step_index"],
        "token_id": body["token_id"],
    }
    transaction = int.from_bytes(
        hashlib.sha256(canonical_json_bytes(seed)).digest()[:8], "big"
    )
    return transaction or 1


def validate_dynamic_request(
    value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate one request against its session and preceding report."""

    session = validate_dynamic_session(session_value)
    request = dict(value)
    exact_keys(
        request,
        {
            "build_id",
            "command_program_sha256",
            "expected_generations",
            "expected_lengths",
            "generated_token_index",
            "graph_id",
            "input_role",
            "last_row_index",
            "output_role",
            "phase",
            "position_end",
            "position_start",
            "previous_report_id",
            "request_id",
            "request_version",
            "schema",
            "session_id",
            "span_tokens",
            "step_index",
            "token_id",
            "transaction_id",
        },
        set(),
        "dynamic request",
    )
    _identity(request, "request_id", "dynamic request")
    prompt_ids = session["prompt"]["token_ids"]
    prompt_count = len(prompt_ids)
    previous = (
        None
        if previous_report is None
        else _validate_previous_report(previous_report, session)
    )
    expected_step = 0 if previous is None else previous["step_index"] + 1
    step = _integer(request["step_index"], "dynamic request.step_index", 0, 7999)
    if step != expected_step:
        raise QwenDynamicArtifactError("dynamic request step is not contiguous")
    prompt_input = step < prompt_count
    generated_index = None if step < prompt_count - 1 else step - prompt_count + 1
    expected_token = (
        prompt_ids[step]
        if prompt_input
        else previous["outputs"]["committed_logits"]["greedy_token_id"]
    )
    expected_previous = None if previous is None else previous["report_id"]
    expected_phase = "prefill" if prompt_input else "decode"
    expected_input_role = "prompt" if prompt_input else "generated"
    expected_output_role = (
        "prefill_intermediate" if generated_index is None else "generated_token"
    )
    expected_state = [step] * STATE_COUNT
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["request_version"] != REQUEST_VERSION
        or request["session_id"] != session["session_id"]
        or request["build_id"] != session["build_id"]
        or request["graph_id"] != session["graph_id"]
        or request["command_program_sha256"] != session["command_program_sha256"]
        or request["previous_report_id"] != expected_previous
        or request["token_id"] != expected_token
        or request["position_start"] != step
        or request["position_end"] != step + 1
        or request["span_tokens"] != 1
        or request["last_row_index"] != 0
        or request["phase"] != expected_phase
        or request["input_role"] != expected_input_role
        or request["output_role"] != expected_output_role
        or request["generated_token_index"] != generated_index
        or request["expected_generations"] != expected_state
        or request["expected_lengths"] != expected_state
        or request["transaction_id"] != _transaction_id(request)
    ):
        raise QwenDynamicArtifactError("dynamic request chain boundary differs")
    return request


def build_dynamic_request(
    session_value: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the next causal request from a session and prior execution report."""

    session = validate_dynamic_session(session_value)
    previous = (
        None
        if previous_report is None
        else _validate_previous_report(previous_report, session)
    )
    step = 0 if previous is None else previous["step_index"] + 1
    prompt_ids = session["prompt"]["token_ids"]
    prompt_count = len(prompt_ids)
    prompt_input = step < prompt_count
    generated_index = None if step < prompt_count - 1 else step - prompt_count + 1
    if (
        generated_index is not None
        and generated_index >= session["generation"]["generated_token_limit"]
    ):
        raise QwenDynamicArtifactError("dynamic session generation is already complete")
    if not prompt_input and previous is None:  # pragma: no cover - derivation invariant
        raise QwenDynamicArtifactError("generated input has no previous report")
    token_id = (
        prompt_ids[step]
        if prompt_input
        else previous["outputs"]["committed_logits"]["greedy_token_id"]
    )
    body: dict[str, Any] = {
        "build_id": session["build_id"],
        "command_program_sha256": session["command_program_sha256"],
        "expected_generations": [step] * STATE_COUNT,
        "expected_lengths": [step] * STATE_COUNT,
        "generated_token_index": generated_index,
        "graph_id": session["graph_id"],
        "input_role": "prompt" if prompt_input else "generated",
        "last_row_index": 0,
        "output_role": (
            "prefill_intermediate" if generated_index is None else "generated_token"
        ),
        "phase": "prefill" if prompt_input else "decode",
        "position_end": step + 1,
        "position_start": step,
        "previous_report_id": None if previous is None else previous["report_id"],
        "request_version": REQUEST_VERSION,
        "schema": REQUEST_SCHEMA,
        "session_id": session["session_id"],
        "span_tokens": 1,
        "step_index": step,
        "token_id": token_id,
    }
    body["transaction_id"] = _transaction_id(body)
    return validate_dynamic_request(_identified(body, "request_id"), session, previous)


def validate_dynamic_transaction_report(
    value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    request_value: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate the causal fields consumed by the aggregate session contract."""

    session = validate_dynamic_session(session_value)
    request = validate_dynamic_request(request_value, session, previous_report)
    report = dict(value)
    _identity(report, "report_id", "dynamic transaction report")
    expected_previous = (
        None
        if previous_report is None
        else _validate_previous_report(previous_report, session)["report_id"]
    )
    expected_input = {
        "generated_token_index": request["generated_token_index"],
        "input_role": request["input_role"],
        "output_role": request["output_role"],
        "phase": request["phase"],
        "position_end": request["position_end"],
        "position_start": request["position_start"],
        "token_id": request["token_id"],
    }
    expected_claim = {
        "complete_model_one_token_execution": True,
        "exact_8000_token_acceptance": False,
        "generated_token_decision": request["output_role"] == "generated_token",
        "session_generation_complete": False,
        "timing_or_performance": False,
    }
    if (
        report.get("schema") != EXECUTION_SCHEMA
        or report.get("status") != "pass"
        or report.get("mode") != "artifact_only_data_bearing_dynamic_transaction"
        or report.get("session_id") != session["session_id"]
        or report.get("build_id") != session["build_id"]
        or report.get("graph_id") != session["graph_id"]
        or report.get("command_program_sha256") != session["command_program_sha256"]
        or report.get("request_id") != request["request_id"]
        or report.get("previous_report_id") != expected_previous
        or report.get("step_index") != request["step_index"]
        or report.get("input") != expected_input
        or report.get("claim_boundary") != expected_claim
        or report.get("artifact_admission")
        != {
            "all_hbm_shards_sha256_verified": True,
            "non_hbm_manifest_artifacts_sha256_verified": True,
        }
        or report.get("command_count") != 924_386
        or report.get("operation_count") != 617
        or report.get("timing")
        != {
            "reason": "capability_uncharacterized",
            "status": "unavailable",
        }
    ):
        raise QwenDynamicArtifactError("dynamic transaction report boundary differs")

    step = request["step_index"]
    state_before = report.get("state_before")
    if state_before != {
        "generations": [step] * STATE_COUNT,
        "lengths": [step] * STATE_COUNT,
    }:
        raise QwenDynamicArtifactError("dynamic transaction prior state differs")
    state = report.get("state")
    if not isinstance(state, list) or len(state) != STATE_COUNT:
        raise QwenDynamicArtifactError("dynamic transaction state coverage differs")
    for layer, record in enumerate(state):
        if not isinstance(record, dict):
            raise QwenDynamicArtifactError(
                "dynamic transaction state record must be an object"
            )
        exact_keys(
            record,
            {
                "generation",
                "key_payload_sha256",
                "layer",
                "length",
                "resource_id",
                "value_payload_sha256",
            },
            set(),
            f"dynamic transaction state[{layer}]",
        )
        require_sha256(
            record["key_payload_sha256"],
            f"dynamic transaction state[{layer}].key_payload_sha256",
        )
        require_sha256(
            record["value_payload_sha256"],
            f"dynamic transaction state[{layer}].value_payload_sha256",
        )
        if record != {
            "generation": step + 1,
            "key_payload_sha256": record["key_payload_sha256"],
            "layer": layer,
            "length": step + 1,
            "resource_id": f"kv.layer.{layer}",
            "value_payload_sha256": record["value_payload_sha256"],
        }:
            raise QwenDynamicArtifactError(
                "dynamic transaction state ordering or generation differs"
            )

    outputs = report.get("outputs")
    logits = outputs.get("committed_logits") if isinstance(outputs, dict) else None
    if not isinstance(logits, dict):
        raise QwenDynamicArtifactError("dynamic transaction logits are absent")
    token = _integer(
        logits.get("greedy_token_id"),
        "dynamic transaction greedy token",
        0,
        VOCABULARY_SIZE - 1,
    )
    require_sha256(
        logits.get("payload_sha256"), "dynamic transaction logits payload SHA-256"
    )
    maximum_count = _integer(
        logits.get("greedy_maximum_count"),
        "dynamic transaction greedy maximum count",
        1,
        VOCABULARY_SIZE,
    )
    if logits.get("size_bytes") != 303_872:
        raise QwenDynamicArtifactError("dynamic transaction logits boundary differs")

    counters = report.get("counters")
    if (
        not isinstance(counters, dict)
        or len(counters) != 70
        or any(
            not isinstance(key, str)
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for key, count in counters.items()
        )
    ):
        raise QwenDynamicArtifactError("dynamic transaction counter coverage differs")
    binding = report.get("runtime_binding")
    if not isinstance(binding, dict):
        raise QwenDynamicArtifactError(
            "dynamic transaction runtime binding must be an object"
        )
    exact_keys(
        binding,
        {
            "request_registers_sha256",
            "request_registers_size_bytes",
            "state_metadata_after_sha256",
            "state_metadata_before_sha256",
            "state_metadata_size_bytes",
            "transaction_descriptors_sha256",
            "transaction_descriptors_size_bytes",
        },
        set(),
        "dynamic transaction runtime binding",
    )
    for field in (
        "request_registers_sha256",
        "state_metadata_after_sha256",
        "state_metadata_before_sha256",
        "transaction_descriptors_sha256",
    ):
        require_sha256(binding[field], f"dynamic transaction runtime binding.{field}")
    if (
        binding["request_registers_size_bytes"] != 16
        or binding["state_metadata_size_bytes"] != 2_304
        or binding["transaction_descriptors_size_bytes"] != 2_304
    ):
        raise QwenDynamicArtifactError("dynamic transaction runtime sizes differ")
    # Preserve the checked integer result for callers while returning the exact report.
    assert token == logits["greedy_token_id"] and maximum_count >= 1
    return report


def validate_dynamic_session_execution(
    value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    *,
    decode_token_ids: Callable[[list[int]], str] | None = None,
) -> dict[str, Any]:
    """Validate a complete short-generation aggregate and its claim boundary."""

    session = validate_dynamic_session(session_value)
    execution = dict(value)
    exact_keys(
        execution,
        {
            "aggregate_counter_sha256",
            "aggregate_counters",
            "build_id",
            "claim_boundary",
            "command_program_sha256",
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
            "session_execution_id",
            "session_id",
            "status",
            "step_chain_sha256",
            "steps",
            "timing",
            "tokenizer",
            "transaction_count",
        },
        set(),
        "dynamic session execution",
    )
    _identity(execution, "session_execution_id", "dynamic session execution")
    prompt_ids = session["prompt"]["token_ids"]
    prompt_count = len(prompt_ids)
    generated_limit = session["generation"]["generated_token_limit"]
    transaction_count = prompt_count + generated_limit - 1
    if (
        execution["schema"] != SESSION_EXECUTION_SCHEMA
        or execution["runner_version"] != SESSION_RUNNER_VERSION
        or execution["status"] != "pass"
        or execution["mode"] != "artifact_only_data_bearing_short_generation"
        or execution["session_id"] != session["session_id"]
        or execution["build_id"] != session["build_id"]
        or execution["graph_id"] != session["graph_id"]
        or execution["command_program_sha256"] != session["command_program_sha256"]
        or execution["claim_boundary"]
        != {
            "artifact_only_short_generation_complete": True,
            "exact_8000_token_acceptance": False,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
        }
        or execution["timing"]
        != {
            "reason": "capability_uncharacterized",
            "status": "unavailable",
        }
        or execution["eos_observed"] is not False
        or execution["prompt_token_count"] != prompt_count
        or execution["prompt_token_ids"] != prompt_ids
        or execution["generated_token_count"] != generated_limit
        or execution["transaction_count"] != transaction_count
        or execution["decode_transaction_count"] != generated_limit - 1
        or execution["tokenizer"] != session["tokenizer"]
    ):
        raise QwenDynamicArtifactError("dynamic session execution boundary differs")

    generated_ids = _token_ids(
        execution["generated_token_ids"],
        "dynamic session execution generated_token_ids",
    )
    if len(generated_ids) != generated_limit:
        raise QwenDynamicArtifactError("dynamic session generated-token count differs")
    steps = execution["steps"]
    if not isinstance(steps, list) or len(steps) != transaction_count:
        raise QwenDynamicArtifactError("dynamic session step coverage differs")
    observed_generated: list[int] = []
    previous_report_id: str | None = None
    previous_output_token: int | None = None
    previous_metadata_after: str | None = None
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise QwenDynamicArtifactError("dynamic session step must be an object")
        exact_keys(
            step,
            {
                "generated_token_index",
                "input_role",
                "input_token_id",
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
            },
            set(),
            f"dynamic session step[{index}]",
        )
        for field in (
            "logits_sha256",
            "report_id",
            "report_sha256",
            "request_id",
            "state_metadata_after_sha256",
            "state_metadata_before_sha256",
        ):
            require_sha256(step[field], f"dynamic session step[{index}].{field}")
        prompt_input = index < prompt_count
        generated_index = None if index < prompt_count - 1 else index - prompt_count + 1
        expected_input = prompt_ids[index] if prompt_input else previous_output_token
        if (
            expected_input is None
            or step["step_index"] != index
            or step["previous_report_id"] != previous_report_id
            or step["input_token_id"] != expected_input
            or step["input_role"] != ("prompt" if prompt_input else "generated")
            or step["phase"] != ("prefill" if prompt_input else "decode")
            or step["output_role"]
            != (
                "prefill_intermediate" if generated_index is None else "generated_token"
            )
            or step["generated_token_index"] != generated_index
            or step["state_generation"] != index + 1
            or step["state_length"] != index + 1
            or isinstance(step["report_size_bytes"], bool)
            or not isinstance(step["report_size_bytes"], int)
            or step["report_size_bytes"] < 1
            or (
                previous_metadata_after is not None
                and step["state_metadata_before_sha256"] != previous_metadata_after
            )
        ):
            raise QwenDynamicArtifactError("dynamic session step chain or role differs")
        output_token = _integer(
            step["output_token_id"],
            f"dynamic session step[{index}].output_token_id",
            0,
            VOCABULARY_SIZE - 1,
        )
        if generated_index is not None:
            observed_generated.append(output_token)
        previous_report_id = step["report_id"]
        previous_output_token = output_token
        previous_metadata_after = step["state_metadata_after_sha256"]
    if observed_generated != generated_ids:
        raise QwenDynamicArtifactError("dynamic session generated tokens differ")
    if execution["step_chain_sha256"] != sha256_bytes(canonical_json_bytes(steps)):
        raise QwenDynamicArtifactError("dynamic session step-chain hash differs")

    counters = execution["aggregate_counters"]
    if (
        not isinstance(counters, dict)
        or len(counters) != 70
        or any(
            not isinstance(key, str)
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for key, count in counters.items()
        )
        or execution["aggregate_counter_sha256"]
        != sha256_bytes(canonical_json_bytes(counters))
    ):
        raise QwenDynamicArtifactError("dynamic session aggregate counters differ")

    final_state = execution["final_state"]
    if not isinstance(final_state, list) or len(final_state) != STATE_COUNT:
        raise QwenDynamicArtifactError("dynamic session final state coverage differs")
    for layer, record in enumerate(final_state):
        if not isinstance(record, dict):
            raise QwenDynamicArtifactError(
                "dynamic session final state must contain objects"
            )
        for field in ("key_payload_sha256", "value_payload_sha256"):
            require_sha256(record.get(field), f"dynamic session final state.{field}")
        if (
            record.get("layer") != layer
            or record.get("resource_id") != f"kv.layer.{layer}"
            or record.get("generation") != transaction_count
            or record.get("length") != transaction_count
        ):
            raise QwenDynamicArtifactError("dynamic session final state differs")

    decoded = execution["decoded"]
    if (
        not isinstance(decoded, dict)
        or set(decoded) != {"full_text", "generated_text", "prompt_text"}
        or decoded["prompt_text"] != session["prompt"]["text"]
        or not isinstance(decoded["generated_text"], str)
        or not isinstance(decoded["full_text"], str)
    ):
        raise QwenDynamicArtifactError("dynamic session decoded text boundary differs")
    if decode_token_ids is not None:
        try:
            expected_prompt = decode_token_ids(list(prompt_ids))
            expected_generated = decode_token_ids(generated_ids)
            expected_full = decode_token_ids([*prompt_ids, *generated_ids])
        except Exception as exc:
            raise QwenDynamicArtifactError(
                f"cannot decode dynamic session token IDs: {exc}"
            ) from exc
        if (
            expected_prompt != session["prompt"]["text"]
            or decoded["generated_text"] != expected_generated
            or decoded["full_text"] != expected_full
        ):
            raise QwenDynamicArtifactError("dynamic session tokenizer decode differs")
    return execution


def build_dynamic_session_execution(
    session_value: Mapping[str, Any],
    request_values: Sequence[Mapping[str, Any]],
    report_values: Sequence[Mapping[str, Any]],
    *,
    decode_token_ids: Callable[[list[int]], str],
) -> dict[str, Any]:
    """Build the canonical aggregate from a complete causal request/report chain."""

    session = validate_dynamic_session(session_value)
    if isinstance(request_values, (str, bytes)) or not isinstance(
        request_values, Sequence
    ):
        raise QwenDynamicArtifactError("dynamic session requests must be a sequence")
    if isinstance(report_values, (str, bytes)) or not isinstance(
        report_values, Sequence
    ):
        raise QwenDynamicArtifactError("dynamic session reports must be a sequence")
    expected_count = (
        len(session["prompt"]["token_ids"])
        + session["generation"]["generated_token_limit"]
        - 1
    )
    if len(request_values) != expected_count or len(report_values) != expected_count:
        raise QwenDynamicArtifactError("dynamic session transaction coverage differs")

    requests: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    generated_tokens: list[int] = []
    aggregate_counters: Counter[str] = Counter()
    counter_keys: set[str] | None = None
    previous: dict[str, Any] | None = None
    previous_metadata_after: str | None = None
    for index, (raw_request, raw_report) in enumerate(
        zip(request_values, report_values, strict=True)
    ):
        request = validate_dynamic_request(raw_request, session, previous)
        report = validate_dynamic_transaction_report(
            raw_report, session, request, previous
        )
        keys = set(report["counters"])
        if counter_keys is None:
            counter_keys = keys
        elif keys != counter_keys:
            raise QwenDynamicArtifactError(
                "dynamic transaction counter key sets differ"
            )
        binding = report["runtime_binding"]
        if (
            previous_metadata_after is not None
            and binding["state_metadata_before_sha256"] != previous_metadata_after
        ):
            raise QwenDynamicArtifactError(
                "dynamic transaction state-metadata chain differs"
            )
        token = report["outputs"]["committed_logits"]["greedy_token_id"]
        if request["output_role"] == "generated_token":
            generated_tokens.append(token)
            if token in session["generation"]["eos_token_ids"]:
                raise QwenDynamicArtifactError(
                    "dynamic session encountered an unexpected early EOS"
                )
        payload = canonical_json_bytes(report)
        state = report["state"][0]
        steps.append(
            {
                "generated_token_index": request["generated_token_index"],
                "input_role": request["input_role"],
                "input_token_id": request["token_id"],
                "logits_sha256": report["outputs"]["committed_logits"][
                    "payload_sha256"
                ],
                "output_role": request["output_role"],
                "output_token_id": token,
                "phase": request["phase"],
                "previous_report_id": request["previous_report_id"],
                "report_id": report["report_id"],
                "report_sha256": hashlib.sha256(payload).hexdigest(),
                "report_size_bytes": len(payload),
                "request_id": request["request_id"],
                "state_generation": state["generation"],
                "state_length": state["length"],
                "state_metadata_after_sha256": binding["state_metadata_after_sha256"],
                "state_metadata_before_sha256": binding["state_metadata_before_sha256"],
                "step_index": index,
            }
        )
        aggregate_counters.update(report["counters"])
        requests.append(request)
        reports.append(report)
        previous = report
        previous_metadata_after = binding["state_metadata_after_sha256"]
    if len(generated_tokens) != session["generation"]["generated_token_limit"]:
        raise QwenDynamicArtifactError(
            "dynamic session did not produce the frozen generated-token count"
        )

    try:
        generated_text = decode_token_ids(generated_tokens)
        full_text = decode_token_ids(
            [*session["prompt"]["token_ids"], *generated_tokens]
        )
    except Exception as exc:
        raise QwenDynamicArtifactError(
            f"cannot decode dynamic session output: {exc}"
        ) from exc
    counters = dict(sorted(aggregate_counters.items()))
    body: dict[str, Any] = {
        "aggregate_counter_sha256": sha256_bytes(canonical_json_bytes(counters)),
        "aggregate_counters": counters,
        "build_id": session["build_id"],
        "claim_boundary": {
            "artifact_only_short_generation_complete": True,
            "exact_8000_token_acceptance": False,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": session["command_program_sha256"],
        "decode_transaction_count": sum(
            request["phase"] == "decode" for request in requests
        ),
        "decoded": {
            "full_text": full_text,
            "generated_text": generated_text,
            "prompt_text": session["prompt"]["text"],
        },
        "eos_observed": False,
        "final_state": reports[-1]["state"],
        "generated_token_count": len(generated_tokens),
        "generated_token_ids": generated_tokens,
        "graph_id": session["graph_id"],
        "mode": "artifact_only_data_bearing_short_generation",
        "prompt_token_count": len(session["prompt"]["token_ids"]),
        "prompt_token_ids": session["prompt"]["token_ids"],
        "runner_version": SESSION_RUNNER_VERSION,
        "schema": SESSION_EXECUTION_SCHEMA,
        "session_id": session["session_id"],
        "status": "pass",
        "step_chain_sha256": sha256_bytes(canonical_json_bytes(steps)),
        "steps": steps,
        "timing": {
            "reason": "capability_uncharacterized",
            "status": "unavailable",
        },
        "tokenizer": session["tokenizer"],
        "transaction_count": len(requests),
    }
    result = _identified(body, "session_execution_id")
    return validate_dynamic_session_execution(
        result, session, decode_token_ids=decode_token_ids
    )


def _publish(value: Mapping[str, Any], output: Path, label: str) -> None:
    path = Path(output)
    if path.exists():
        raise QwenDynamicArtifactError(f"{label} already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(dict(value)))
        handle.flush()
        os.fsync(handle.fileno())


def publish_dynamic_session(session: Mapping[str, Any], output: Path) -> None:
    """Publish a canonical, content-addressed session without overwrite."""

    _publish(validate_dynamic_session(session), output, "dynamic session")


def publish_dynamic_request(
    request: Mapping[str, Any],
    session: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None,
    output: Path,
) -> None:
    """Publish one validated causal request without overwrite."""

    _publish(
        validate_dynamic_request(request, session, previous_report),
        output,
        "dynamic request",
    )


def publish_dynamic_session_execution(
    execution: Mapping[str, Any],
    session: Mapping[str, Any],
    output: Path,
) -> None:
    """Publish one validated short-generation aggregate without overwrite."""

    _publish(
        validate_dynamic_session_execution(execution, session),
        output,
        "dynamic session execution",
    )


__all__ = [
    "EXECUTION_SCHEMA",
    "QwenDynamicArtifactError",
    "REQUEST_SCHEMA",
    "REQUEST_VERSION",
    "SESSION_EXECUTION_SCHEMA",
    "SESSION_RUNNER_VERSION",
    "SESSION_SCHEMA",
    "SESSION_VERSION",
    "build_dynamic_request",
    "build_dynamic_session",
    "build_dynamic_session_execution",
    "publish_dynamic_request",
    "publish_dynamic_session",
    "publish_dynamic_session_execution",
    "validate_dynamic_request",
    "validate_dynamic_session",
    "validate_dynamic_session_execution",
    "validate_dynamic_transaction_report",
]
