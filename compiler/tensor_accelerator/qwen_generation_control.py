"""Authenticated Qwen long-session EOS and token-legitimacy control.

The immutable long-acceptance session describes model-forward transactions and
was originally frozen with early EOS classified as a failed fixed-length
diagnostic.  Production decoding is a host control-plane concern: the selected
EOS token is part of the generated sequence, but no subsequent model-forward
request may consume it.  This module adds that policy without mutating the
admitted graph, Kernel IR, physical deployment, command program, transaction
schemas, checkpoints, or retained restart evidence.

The Qwen checkpoint pads its language-model head to 151,936 rows while the
pinned tokenizer resolves only 151,669 token IDs.  A selected padded row is
therefore a numerical model result but not a legitimate decodable token.  The
controller fails closed rather than silently masking, remapping, or emitting
such an ID.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
from typing import Any

from tokenizers import Tokenizer, __version__ as tokenizers_version

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    publish_bytes_atomic_no_replace,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
from .qwen_full_model_long_acceptance import (
    GENERATED_TOKEN_COUNT,
    MODEL_ID,
    PROMPT_TOKEN_COUNT,
    QwenLongAcceptanceArtifactError,
    validate_long_acceptance_session,
    validate_long_acceptance_request,
    validate_long_acceptance_transaction_report,
)


CONTROL_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_long_generation_control.v1"
)
CONTROL_VERSION = "tensor-accelerator-qwen-long-generation-control-0.1.0"
CONTROLLED_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_controlled_long_session_execution.v1"
)
CONTROLLED_RUNNER_VERSION = (
    "tensor-accelerator-qwen-controlled-long-runner-0.1.0"
)

TOKENIZERS_VERSION = "0.22.2"
EXPLICIT_VOCABULARY_SIZE = 151_669
MODEL_VOCABULARY_SIZE = 151_936
PADDED_TOKEN_ID_START = EXPLICIT_VOCABULARY_SIZE
PADDED_TOKEN_ID_END_EXCLUSIVE = MODEL_VOCABULARY_SIZE
EOS_TOKEN_IDS = (151_645, 151_643)
EOS_TOKEN_STRINGS = ("<|im_end|>", "<|endoftext|>")
BASE_VOCABULARY_SIZE = 151_643

SOURCE_FILES = {
    "config": (
        "config.json",
        "f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30",
        728,
    ),
    "generation_config": (
        "generation_config.json",
        "2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2",
        239,
    ),
    "tokenizer": (
        "tokenizer.json",
        "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
        11_422_654,
    ),
    "tokenizer_config": (
        "tokenizer_config.json",
        "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
        9_732,
    ),
}


class QwenGenerationControlError(ArtifactError):
    """Raised when EOS control or token legitimacy is not proven."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenGenerationControlError(f"{label} identity differs")


def _integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise QwenGenerationControlError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _checkpoint_source_record(
    checkpoint_lock: Mapping[str, Any], key: str
) -> dict[str, Any]:
    expected_path, expected_sha256, expected_size = SOURCE_FILES[key]
    records = [
        record
        for record in checkpoint_lock.get("files", [])
        if isinstance(record, Mapping) and record.get("path") == expected_path
    ]
    if len(records) != 1:
        raise QwenGenerationControlError(
            f"checkpoint lock must contain exactly one {expected_path!r} record"
        )
    record = dict(records[0])
    exact_keys(
        record,
        {"path", "sha256", "size_bytes"},
        set(),
        f"checkpoint source {key}",
    )
    require_sha256(record["sha256"], f"checkpoint source {key}.sha256")
    if record != {
        "path": expected_path,
        "sha256": expected_sha256,
        "size_bytes": expected_size,
    }:
        raise QwenGenerationControlError(f"checkpoint source {key} differs")
    return record


def build_qwen_long_generation_control(
    session_value: Mapping[str, Any], checkpoint_lock: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the immutable host generation policy above a V1 model session."""

    try:
        session = validate_long_acceptance_session(session_value)
    except QwenLongAcceptanceArtifactError as exc:
        raise QwenGenerationControlError(
            f"base long-acceptance session differs: {exc}"
        ) from exc
    source_files = {
        key: _checkpoint_source_record(checkpoint_lock, key)
        for key in sorted(SOURCE_FILES)
    }
    if (
        checkpoint_lock.get("lock_id") != session["checkpoint_lock_id"]
        or session["generation"]
        != {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "generated_token_limit": GENERATED_TOKEN_COUNT,
            "selection": "greedy_lowest_token_id_argmax",
            "unexpected_early_eos": "fail",
        }
    ):
        raise QwenGenerationControlError(
            "base session or checkpoint-lock generation binding differs"
        )
    body: dict[str, Any] = {
        "base_session_id": session["session_id"],
        "build_id": session["build_id"],
        "checkpoint_lock_id": session["checkpoint_lock_id"],
        "claim_boundary": {
            "changes_model_forward_execution": False,
            "eos_terminated_decode_control": True,
            "semantic_natural_language_quality": False,
            "token_legitimacy_fail_closed": True,
            "timing_or_performance": False,
        },
        "control_version": CONTROL_VERSION,
        "generation": {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "eos_token_included_in_generated_sequence": True,
            "maximum_generated_token_count": GENERATED_TOKEN_COUNT,
            "selection": "greedy_lowest_token_id_argmax",
            "stop_rule": "first_eos_or_maximum_generated_token_count",
            "undecodable_token_policy": "fail_closed",
        },
        "graph_id": session["graph_id"],
        "model_id": MODEL_ID,
        "schema": CONTROL_SCHEMA,
        "source_files": source_files,
        "tokenizer_contract": {
            "base_vocabulary_size": BASE_VOCABULARY_SIZE,
            "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
            "model_vocabulary_size": MODEL_VOCABULARY_SIZE,
            "padded_model_token_id_end_exclusive": PADDED_TOKEN_ID_END_EXCLUSIVE,
            "padded_model_token_id_start": PADDED_TOKEN_ID_START,
            "padded_model_token_policy": "reject_if_selected_for_generation",
        },
    }
    return validate_qwen_long_generation_control(_identified(body, "control_id"), session)


def validate_qwen_long_generation_control(
    value: Mapping[str, Any], session_value: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the exact EOS and decodable-token control contract."""

    try:
        session = validate_long_acceptance_session(session_value)
    except QwenLongAcceptanceArtifactError as exc:
        raise QwenGenerationControlError(
            f"base long-acceptance session differs: {exc}"
        ) from exc
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
            "source_files",
            "tokenizer_contract",
        },
        set(),
        "Qwen generation control",
    )
    _identity(control, "control_id", "Qwen generation control")
    expected_claim = {
        "changes_model_forward_execution": False,
        "eos_terminated_decode_control": True,
        "semantic_natural_language_quality": False,
        "token_legitimacy_fail_closed": True,
        "timing_or_performance": False,
    }
    expected_generation = {
        "eos_token_ids": list(EOS_TOKEN_IDS),
        "eos_token_included_in_generated_sequence": True,
        "maximum_generated_token_count": GENERATED_TOKEN_COUNT,
        "selection": "greedy_lowest_token_id_argmax",
        "stop_rule": "first_eos_or_maximum_generated_token_count",
        "undecodable_token_policy": "fail_closed",
    }
    expected_contract = {
        "base_vocabulary_size": BASE_VOCABULARY_SIZE,
        "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
        "model_vocabulary_size": MODEL_VOCABULARY_SIZE,
        "padded_model_token_id_end_exclusive": PADDED_TOKEN_ID_END_EXCLUSIVE,
        "padded_model_token_id_start": PADDED_TOKEN_ID_START,
        "padded_model_token_policy": "reject_if_selected_for_generation",
    }
    if (
        control["schema"] != CONTROL_SCHEMA
        or control["control_version"] != CONTROL_VERSION
        or control["base_session_id"] != session["session_id"]
        or control["build_id"] != session["build_id"]
        or control["checkpoint_lock_id"] != session["checkpoint_lock_id"]
        or control["graph_id"] != session["graph_id"]
        or control["model_id"] != MODEL_ID
        or control["claim_boundary"] != expected_claim
        or control["generation"] != expected_generation
        or control["tokenizer_contract"] != expected_contract
    ):
        raise QwenGenerationControlError("Qwen generation control boundary differs")
    source_files = control["source_files"]
    if not isinstance(source_files, dict) or set(source_files) != set(SOURCE_FILES):
        raise QwenGenerationControlError("Qwen generation source inventory differs")
    for key in sorted(SOURCE_FILES):
        expected_path, expected_sha256, expected_size = SOURCE_FILES[key]
        record = source_files[key]
        if not isinstance(record, dict):
            raise QwenGenerationControlError(
                f"Qwen generation source {key} must be an object"
            )
        exact_keys(
            record,
            {"path", "sha256", "size_bytes"},
            set(),
            f"Qwen generation source {key}",
        )
        require_sha256(record["sha256"], f"Qwen generation source {key}.sha256")
        if record != {
            "path": expected_path,
            "sha256": expected_sha256,
            "size_bytes": expected_size,
        }:
            raise QwenGenerationControlError(f"Qwen generation source {key} differs")
    return control


def _load_authenticated_json(
    snapshot: Path, record: Mapping[str, Any], label: str
) -> dict[str, Any]:
    path = Path(snapshot) / str(record["path"])
    try:
        digest, size = sha256_file(path)
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise QwenGenerationControlError(
            f"cannot load authenticated {label}: {exc}"
        ) from exc
    if (digest, size) != (record["sha256"], record["size_bytes"]):
        raise QwenGenerationControlError(f"authenticated {label} bytes differ")
    return value


def authenticate_qwen_generation_sources(
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    snapshot: Path,
) -> Tokenizer:
    """Authenticate source files and reconcile every EOS/tokenizer boundary."""

    control = validate_qwen_long_generation_control(control_value, session_value)
    source = control["source_files"]
    config = _load_authenticated_json(snapshot, source["config"], "model config")
    generation = _load_authenticated_json(
        snapshot, source["generation_config"], "generation config"
    )
    tokenizer_config = _load_authenticated_json(
        snapshot, source["tokenizer_config"], "tokenizer config"
    )
    tokenizer_record = source["tokenizer"]
    tokenizer_path = Path(snapshot) / tokenizer_record["path"]
    try:
        digest, size = sha256_file(tokenizer_path)
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
    except (OSError, Exception) as exc:
        raise QwenGenerationControlError(
            f"cannot load authenticated tokenizer: {exc}"
        ) from exc
    if (
        tokenizers_version != TOKENIZERS_VERSION
        or (digest, size)
        != (tokenizer_record["sha256"], tokenizer_record["size_bytes"])
        or config.get("model_type") != "qwen3"
        or config.get("vocab_size") != MODEL_VOCABULARY_SIZE
        or config.get("bos_token_id") != 151_643
        or config.get("eos_token_id") != 151_645
        or generation.get("bos_token_id") != 151_643
        or generation.get("pad_token_id") != 151_643
        or generation.get("eos_token_id") != list(EOS_TOKEN_IDS)
        or tokenizer_config.get("eos_token") != EOS_TOKEN_STRINGS[0]
        or tokenizer_config.get("pad_token") != EOS_TOKEN_STRINGS[1]
        or tokenizer.get_vocab_size(with_added_tokens=True)
        != EXPLICIT_VOCABULARY_SIZE
        or tokenizer.get_vocab_size(with_added_tokens=False)
        != BASE_VOCABULARY_SIZE
        or tuple(tokenizer.id_to_token(token) for token in EOS_TOKEN_IDS)
        != EOS_TOKEN_STRINGS
    ):
        raise QwenGenerationControlError(
            "model, generation, and tokenizer EOS boundaries do not reconcile"
        )
    added = tokenizer.get_added_tokens_decoder()
    for token_id, content in zip(EOS_TOKEN_IDS, EOS_TOKEN_STRINGS, strict=True):
        token = added.get(token_id)
        if token is None or token.content != content or token.special is not True:
            raise QwenGenerationControlError(
                f"EOS token {token_id} is not an authenticated special token"
            )
    return tokenizer


def generated_token_record(
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    tokenizer: Tokenizer,
    *,
    generated_token_index: int,
    token_id: int,
) -> dict[str, Any]:
    """Fail closed on padded rows and return exact token/decode evidence."""

    control = validate_qwen_long_generation_control(control_value, session_value)
    index = _integer(
        generated_token_index,
        "generated token index",
        0,
        control["generation"]["maximum_generated_token_count"] - 1,
    )
    token = _integer(
        token_id,
        "generated token ID",
        0,
        MODEL_VOCABULARY_SIZE - 1,
    )
    if token >= EXPLICIT_VOCABULARY_SIZE:
        raise QwenGenerationControlError(
            f"generated token ID {token} selects an undecodable padded model row"
        )
    token_string = tokenizer.id_to_token(token)
    if token_string is None:
        raise QwenGenerationControlError(
            f"generated token ID {token} has no pinned-tokenizer entry"
        )
    try:
        decoded_piece = tokenizer.decode([token], skip_special_tokens=False)
    except Exception as exc:
        raise QwenGenerationControlError(
            f"generated token ID {token} cannot be decoded: {exc}"
        ) from exc
    added_token = tokenizer.get_added_tokens_decoder().get(token)
    body = {
        "decoded_piece": decoded_piece,
        "generated_token_index": index,
        "is_eos": token in EOS_TOKEN_IDS,
        "is_special": bool(added_token is not None and added_token.special),
        "token": token_string,
        "token_id": token,
        "vocabulary_class": "base" if token < BASE_VOCABULARY_SIZE else "added",
    }
    return body


def controlled_stop_reason(
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    *,
    generated_token_count: int,
    latest_generated_token_id: int,
) -> str | None:
    """Return the terminal reason after one admitted generated decision."""

    control = validate_qwen_long_generation_control(control_value, session_value)
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
    if token in control["generation"]["eos_token_ids"]:
        return "eos"
    if count == control["generation"]["maximum_generated_token_count"]:
        return "maximum_generated_token_count"
    return None


def build_controlled_long_session_execution(
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    request_values: Sequence[Mapping[str, Any]],
    report_values: Sequence[Mapping[str, Any]],
    *,
    tokenizer: Tokenizer,
) -> dict[str, Any]:
    """Aggregate a complete EOS-terminated or maximum-bounded long session."""

    session = validate_long_acceptance_session(session_value)
    control = validate_qwen_long_generation_control(control_value, session)
    if len(request_values) != len(report_values):
        raise QwenGenerationControlError("controlled request/report coverage differs")
    transaction_count = len(report_values)
    if not PROMPT_TOKEN_COUNT <= transaction_count <= (
        PROMPT_TOKEN_COUNT + GENERATED_TOKEN_COUNT - 1
    ):
        raise QwenGenerationControlError("controlled transaction count differs")

    generated_ids: list[int] = []
    token_records: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    aggregate_counters: dict[str, int] = {}
    previous: dict[str, Any] | None = None
    previous_metadata: str | None = None
    for index, (raw_request, raw_report) in enumerate(
        zip(request_values, report_values, strict=True)
    ):
        try:
            request = validate_long_acceptance_request(raw_request, session, previous)
            report = validate_long_acceptance_transaction_report(
                raw_report, session, request, previous
            )
        except QwenLongAcceptanceArtifactError as exc:
            raise QwenGenerationControlError(
                f"controlled transaction {index} differs: {exc}"
            ) from exc
        binding = report["runtime_binding"]
        if (
            previous_metadata is not None
            and binding["state_metadata_before_sha256"] != previous_metadata
        ):
            raise QwenGenerationControlError(
                "controlled state-metadata chain differs"
            )
        output_token = report["outputs"]["committed_logits"]["greedy_token_id"]
        generated_index = request["generated_token_index"]
        token_record: dict[str, Any] | None = None
        if generated_index is not None:
            token_record = generated_token_record(
                control,
                session,
                tokenizer,
                generated_token_index=generated_index,
                token_id=output_token,
            )
            generated_ids.append(output_token)
            token_records.append(token_record)
            if token_record["is_eos"] and index != transaction_count - 1:
                raise QwenGenerationControlError(
                    "controlled execution continues after the first EOS token"
                )
        for key, count in report["counters"].items():
            aggregate_counters[key] = aggregate_counters.get(key, 0) + count
        payload = canonical_json_bytes(report)
        state = report["state"][0]
        steps.append(
            {
                "generated_token_index": generated_index,
                "input_role": request["input_role"],
                "input_token_id": request["token_id"],
                "is_terminal_decision": bool(
                    token_record is not None
                    and (
                        token_record["is_eos"]
                        or generated_index == GENERATED_TOKEN_COUNT - 1
                    )
                ),
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
        previous = report
        previous_metadata = binding["state_metadata_after_sha256"]

    if not generated_ids or previous is None:
        raise QwenGenerationControlError(
            "controlled execution has no generated-token decision"
        )
    terminal = controlled_stop_reason(
        control,
        session,
        generated_token_count=len(generated_ids),
        latest_generated_token_id=generated_ids[-1],
    )
    if terminal is None:
        raise QwenGenerationControlError(
            "controlled execution stops before EOS or the generated-token maximum"
        )
    expected_transactions = PROMPT_TOKEN_COUNT + len(generated_ids) - 1
    if transaction_count != expected_transactions:
        raise QwenGenerationControlError(
            "controlled transaction/generated-token derivation differs"
        )
    prompt_ids = [session["prompt"]["token_id"]] * PROMPT_TOKEN_COUNT
    try:
        decoded = {
            "full_text_raw": tokenizer.decode(
                [*prompt_ids, *generated_ids], skip_special_tokens=False
            ),
            "full_text_visible": tokenizer.decode(
                [*prompt_ids, *generated_ids], skip_special_tokens=True
            ),
            "generated_text_raw": tokenizer.decode(
                generated_ids, skip_special_tokens=False
            ),
            "generated_text_visible": tokenizer.decode(
                generated_ids, skip_special_tokens=True
            ),
            "prompt_text_raw": tokenizer.decode(
                prompt_ids, skip_special_tokens=False
            ),
            "prompt_text_visible": tokenizer.decode(
                prompt_ids, skip_special_tokens=True
            ),
        }
    except Exception as exc:
        raise QwenGenerationControlError(
            f"controlled token sequence cannot be decoded: {exc}"
        ) from exc
    counters = dict(sorted(aggregate_counters.items()))
    body: dict[str, Any] = {
        "aggregate_counter_sha256": sha256_bytes(canonical_json_bytes(counters)),
        "aggregate_counters": counters,
        "base_session_id": session["session_id"],
        "build_id": session["build_id"],
        "claim_boundary": {
            "artifact_only_full_acceptance_executed": True,
            "exact_8000_prompt_executed": True,
            "official_golden_verified": False,
            "semantic_natural_language_quality": False,
            "target_precision_reference_verified": False,
            "token_legitimacy_verified": True,
            "timing_or_performance": False,
        },
        "control_id": control["control_id"],
        "decode_transaction_count": len(generated_ids) - 1,
        "decoded": decoded,
        "eos_observed": terminal == "eos",
        "final_state": previous["state"],
        "generated_token_count": len(generated_ids),
        "generated_token_ids": generated_ids,
        "graph_id": session["graph_id"],
        "mode": "artifact_only_data_bearing_controlled_long_acceptance_candidate",
        "prefill_transaction_count": PROMPT_TOKEN_COUNT,
        "runner_version": CONTROLLED_RUNNER_VERSION,
        "schema": CONTROLLED_EXECUTION_SCHEMA,
        "status": "execution_complete_reference_pending",
        "step_chain_sha256": sha256_bytes(canonical_json_bytes(steps)),
        "steps": steps,
        "stop_reason": terminal,
        "timing": {"reason": "capability_uncharacterized", "status": "unavailable"},
        "token_legitimacy": {
            "all_generated_token_ids_resolve": True,
            "all_generated_token_ids_within_explicit_vocabulary": True,
            "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
            "padded_model_rows_rejected": True,
            "records": token_records,
        },
        "transaction_count": transaction_count,
    }
    result = _identified(body, "controlled_execution_id")
    return validate_controlled_long_session_execution(
        result, control, session, tokenizer=tokenizer
    )


def validate_controlled_long_session_execution(
    value: Mapping[str, Any],
    control_value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    *,
    tokenizer: Tokenizer | None = None,
) -> dict[str, Any]:
    """Validate the aggregate and optionally reproduce tokenizer evidence."""

    session = validate_long_acceptance_session(session_value)
    control = validate_qwen_long_generation_control(control_value, session)
    execution = dict(value)
    exact_keys(
        execution,
        {
            "aggregate_counter_sha256",
            "aggregate_counters",
            "base_session_id",
            "build_id",
            "claim_boundary",
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
            "prefill_transaction_count",
            "runner_version",
            "schema",
            "status",
            "step_chain_sha256",
            "steps",
            "stop_reason",
            "timing",
            "token_legitimacy",
            "transaction_count",
        },
        set(),
        "controlled long execution",
    )
    _identity(execution, "controlled_execution_id", "controlled long execution")
    generated = execution["generated_token_ids"]
    if (
        execution["schema"] != CONTROLLED_EXECUTION_SCHEMA
        or execution["runner_version"] != CONTROLLED_RUNNER_VERSION
        or execution["status"] != "execution_complete_reference_pending"
        or execution["mode"]
        != "artifact_only_data_bearing_controlled_long_acceptance_candidate"
        or execution["base_session_id"] != session["session_id"]
        or execution["control_id"] != control["control_id"]
        or execution["build_id"] != session["build_id"]
        or execution["graph_id"] != session["graph_id"]
        or execution["prefill_transaction_count"] != PROMPT_TOKEN_COUNT
        or not isinstance(generated, list)
        or not 1 <= len(generated) <= GENERATED_TOKEN_COUNT
        or execution["generated_token_count"] != len(generated)
        or execution["decode_transaction_count"] != len(generated) - 1
        or execution["transaction_count"] != PROMPT_TOKEN_COUNT + len(generated) - 1
        or execution["eos_observed"]
        != (execution["stop_reason"] == "eos")
        or execution["timing"]
        != {"reason": "capability_uncharacterized", "status": "unavailable"}
    ):
        raise QwenGenerationControlError("controlled long execution boundary differs")
    if any(
        isinstance(token, bool)
        or not isinstance(token, int)
        or not 0 <= token < EXPLICIT_VOCABULARY_SIZE
        for token in generated
    ):
        raise QwenGenerationControlError("controlled generated tokens differ")
    expected_reason = (
        "eos"
        if generated[-1] in EOS_TOKEN_IDS
        else "maximum_generated_token_count"
        if len(generated) == GENERATED_TOKEN_COUNT
        else None
    )
    if execution["stop_reason"] != expected_reason:
        raise QwenGenerationControlError("controlled stop reason differs")
    if any(token in EOS_TOKEN_IDS for token in generated[:-1]):
        raise QwenGenerationControlError("controlled tokens continue after EOS")
    expected_claim = {
        "artifact_only_full_acceptance_executed": True,
        "exact_8000_prompt_executed": True,
        "official_golden_verified": False,
        "semantic_natural_language_quality": False,
        "target_precision_reference_verified": False,
        "token_legitimacy_verified": True,
        "timing_or_performance": False,
    }
    if execution["claim_boundary"] != expected_claim:
        raise QwenGenerationControlError("controlled execution claim differs")
    steps = execution["steps"]
    if (
        not isinstance(steps, list)
        or len(steps) != execution["transaction_count"]
        or execution["step_chain_sha256"]
        != sha256_bytes(canonical_json_bytes(steps))
    ):
        raise QwenGenerationControlError("controlled execution steps differ")
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or step.get("step_index") != index:
            raise QwenGenerationControlError("controlled step order differs")
        terminal = index == len(steps) - 1
        if step.get("is_terminal_decision") is not terminal:
            raise QwenGenerationControlError("controlled terminal step differs")
    counters = execution["aggregate_counters"]
    if (
        not isinstance(counters, dict)
        or len(counters) != 70
        or execution["aggregate_counter_sha256"]
        != sha256_bytes(canonical_json_bytes(counters))
    ):
        raise QwenGenerationControlError("controlled aggregate counters differ")
    final_state = execution["final_state"]
    if not isinstance(final_state, list) or len(final_state) != 36:
        raise QwenGenerationControlError("controlled final state coverage differs")
    for layer, state in enumerate(final_state):
        if (
            not isinstance(state, dict)
            or state.get("layer") != layer
            or state.get("resource_id") != f"kv.layer.{layer}"
            or state.get("generation") != execution["transaction_count"]
            or state.get("length") != execution["transaction_count"]
        ):
            raise QwenGenerationControlError("controlled final state differs")
    legitimacy = execution["token_legitimacy"]
    if (
        not isinstance(legitimacy, dict)
        or legitimacy.get("all_generated_token_ids_resolve") is not True
        or legitimacy.get("all_generated_token_ids_within_explicit_vocabulary")
        is not True
        or legitimacy.get("explicit_vocabulary_size")
        != EXPLICIT_VOCABULARY_SIZE
        or legitimacy.get("padded_model_rows_rejected") is not True
        or not isinstance(legitimacy.get("records"), list)
        or len(legitimacy["records"]) != len(generated)
    ):
        raise QwenGenerationControlError("controlled token legitimacy differs")
    if tokenizer is not None:
        expected_records = [
            generated_token_record(
                control,
                session,
                tokenizer,
                generated_token_index=index,
                token_id=token,
            )
            for index, token in enumerate(generated)
        ]
        if legitimacy["records"] != expected_records:
            raise QwenGenerationControlError(
                "controlled tokenizer record reproduction differs"
            )
        prompt_ids = [session["prompt"]["token_id"]] * PROMPT_TOKEN_COUNT
        expected_decoded = {
            "full_text_raw": tokenizer.decode(
                [*prompt_ids, *generated], skip_special_tokens=False
            ),
            "full_text_visible": tokenizer.decode(
                [*prompt_ids, *generated], skip_special_tokens=True
            ),
            "generated_text_raw": tokenizer.decode(
                generated, skip_special_tokens=False
            ),
            "generated_text_visible": tokenizer.decode(
                generated, skip_special_tokens=True
            ),
            "prompt_text_raw": tokenizer.decode(
                prompt_ids, skip_special_tokens=False
            ),
            "prompt_text_visible": tokenizer.decode(
                prompt_ids, skip_special_tokens=True
            ),
        }
        if execution["decoded"] != expected_decoded:
            raise QwenGenerationControlError(
                "controlled tokenizer decode reproduction differs"
            )
    return execution


def publish_qwen_long_generation_control(
    value: Mapping[str, Any], session: Mapping[str, Any], output: Path
) -> None:
    control = validate_qwen_long_generation_control(value, session)
    try:
        publish_bytes_atomic_no_replace(Path(output), canonical_json_bytes(control))
    except FileExistsError as exc:
        raise QwenGenerationControlError(
            f"Qwen generation control already exists: {output}"
        ) from exc
    except OSError as exc:
        raise QwenGenerationControlError(
            f"cannot publish Qwen generation control: {exc}"
        ) from exc


def publish_controlled_long_session_execution(
    value: Mapping[str, Any],
    control: Mapping[str, Any],
    session: Mapping[str, Any],
    output: Path,
) -> None:
    execution = validate_controlled_long_session_execution(value, control, session)
    try:
        publish_bytes_atomic_no_replace(Path(output), canonical_json_bytes(execution))
    except FileExistsError as exc:
        raise QwenGenerationControlError(
            f"controlled long execution already exists: {output}"
        ) from exc
    except OSError as exc:
        raise QwenGenerationControlError(
            f"cannot publish controlled long execution: {exc}"
        ) from exc


__all__ = [
    "CONTROLLED_EXECUTION_SCHEMA",
    "CONTROLLED_RUNNER_VERSION",
    "CONTROL_SCHEMA",
    "CONTROL_VERSION",
    "EOS_TOKEN_IDS",
    "EXPLICIT_VOCABULARY_SIZE",
    "MODEL_VOCABULARY_SIZE",
    "QwenGenerationControlError",
    "authenticate_qwen_generation_sources",
    "build_controlled_long_session_execution",
    "build_qwen_long_generation_control",
    "controlled_stop_reason",
    "generated_token_record",
    "publish_controlled_long_session_execution",
    "publish_qwen_long_generation_control",
    "validate_controlled_long_session_execution",
    "validate_qwen_long_generation_control",
]
