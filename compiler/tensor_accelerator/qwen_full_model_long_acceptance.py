"""Strict artifacts for the exact Qwen3-8B 8,000+32 acceptance session.

This ABI is intentionally separate from the admitted dynamic short-session v1
ABI.  The short ABI has an 8,000-row physical bound; the acceptance workload
needs 8,031 committed rows and therefore binds the separately versioned V7
8,192-row deployment.  The prompt is an authenticated token-ID fixture, not
text to be retokenized.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

from tokenizers import __version__ as tokenizers_version

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    publish_bytes_atomic_no_replace,
    require_sha256,
    sha256_bytes,
)


SESSION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_long_acceptance_session.v1"
)
REQUEST_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_long_acceptance_request.v1"
)
EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_long_acceptance_execution.v1"
)
SESSION_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator."
    "qwen_full_model_long_acceptance_session_execution.v1"
)
SESSION_VERSION = "tensor-accelerator-qwen-long-acceptance-session-0.1.0"
REQUEST_VERSION = "tensor-accelerator-qwen-long-acceptance-request-0.1.0"
RUNNER_VERSION = "tensor-accelerator-qwen-long-acceptance-runner-0.1.0"

MODEL_ID = "qwen3-8b"
VOCABULARY_SIZE = 151_936
TOKENIZERS_VERSION = "0.22.2"
TOKENIZER_PATH = "tokenizer.json"
STATE_COUNT = 36
CONTEXT_CAPACITY = 8_192
PROMPT_TOKEN_COUNT = 8_000
PROMPT_TOKEN_ID = 151_643
GENERATED_TOKEN_COUNT = 32
TRANSACTION_COUNT = PROMPT_TOKEN_COUNT + GENERATED_TOKEN_COUNT - 1
FINAL_STATE_LENGTH = TRANSACTION_COUNT
PROMPT_TOKEN_IDS_SHA256 = (
    "8dcbc057d9f4bb2657755ffc4419dae1189837343c093964ed329ad95e43d461"
)

FIXTURE_COMMIT = "3a985ffcecfd17fb8642cdef819c22e16d8e9f4c"
FIXTURE_TREE = "71613b6eb97390884b8c409d11b05d85b6f19a79"
FIXTURE_PATH = "testdata/compiler/qwen3_8b/workload_manifest.json"
FIXTURE_BLOB = "ddb325754b103ce04aa9e09a0aa5f529c9d43878"
FIXTURE_FILE_SHA256 = (
    "124fad68b395250caf87e1ee37e7914d87ba9b23fc85fc23ef1cce92a9e11f84"
)
FIXTURE_WORKLOAD_ID = (
    "340ec91558350b2e52259bcf9dedd919bd6022473a7ad24318afd99f1e55183e"
)
RELEASE_PATH = "results/compiler/qwen3-8b/release_gate.json"
RELEASE_BLOB = "f3464f2f77abab75cfae074ff647e3c44ab8f72e"
RELEASE_FILE_SHA256 = (
    "257263925d380047546b51c3211404d00882e5873a269e7b8356ea1c907c6b59"
)
RELEASE_REPORT_ID = (
    "a79d454e73d3566c9d6f9a44d87eb5c1d14470bc3cadbdf79beb8c2529738267"
)
OFFICIAL_PREFILL_LOGITS_SHA256 = (
    "d7a3fd7b6e94a82ed503c489998173c88f05d368cb259a46461169ea4d69d1e8"
)
OFFICIAL_PREFILL_GREEDY_TOKEN_ID = 33_975

EXPECTED_BUILD_ID = (
    "6445ef52a940af167f3bde52e0a326258bb8c8da013d4bb25a3b16e18f171bad"
)
EXPECTED_GRAPH_ID = (
    "738f3cd8cb5db1ce400c0a44c12385cef6c42ddb2854e22d473251e97a1a51e3"
)
EXPECTED_CAPABILITY_ID = (
    "a9b231b5f146f845257325e68031f02440f0a3712db42d4e4e2b54c69031f6cd"
)
EXPECTED_KERNEL_IR_ID = (
    "35bae3f71666c72ec886875abf336fefc68dd1635288d3b49720c4297d4cc1e1"
)
EXPECTED_PHYSICAL_PLAN_ID = (
    "2bb30b4bc970b3c0af716eb78b86d3158ed06108218735b515d8e2133dc407a2"
)
EXPECTED_COMMAND_SHA256 = (
    "dfc7ee4d89a091aea616f602174f8bd41cae319ceec92d31fda4cb43636dce6d"
)
EXPECTED_HBM_SHA256 = (
    "55fbb4f91ff9a081dede418edec25d7373553a591ce3c031a27d219048b90b97"
)
EXPECTED_CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)

_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class QwenLongAcceptanceArtifactError(ArtifactError):
    """Raised when the exact long-acceptance artifact chain differs."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenLongAcceptanceArtifactError(f"{label} identity differs")


def _integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise QwenLongAcceptanceArtifactError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _safe_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise QwenLongAcceptanceArtifactError(
            f"{label} must be a safe relative POSIX path"
        )
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or parsed.as_posix() != value
    ):
        raise QwenLongAcceptanceArtifactError(
            f"{label} must be a safe relative POSIX path"
        )
    return value


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise QwenLongAcceptanceArtifactError(
                    f"{label} contains duplicate key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise QwenLongAcceptanceArtifactError(
            f"{label} contains non-finite number {token!r}"
        )

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_pairs,
            parse_constant=reject_constant,
        )
    except QwenLongAcceptanceArtifactError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QwenLongAcceptanceArtifactError(
            f"cannot parse {label}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise QwenLongAcceptanceArtifactError(f"{label} must be a JSON object")
    return value


def _git(repository: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(Path(repository)), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise QwenLongAcceptanceArtifactError(
            f"cannot authenticate committed Qwen workload fixture: {exc}"
        ) from exc
    return completed.stdout


def _committed_payload(
    repository: Path,
    *,
    commit: str,
    path: str,
    expected_blob: str,
    expected_sha256: str,
) -> tuple[dict[str, Any], int]:
    if not _COMMIT.fullmatch(commit):
        raise QwenLongAcceptanceArtifactError("fixture commit must be full SHA-1")
    _safe_path(path, "fixture path")
    observed_commit = _git(repository, "rev-parse", "--verify", f"{commit}^{{commit}}")
    if observed_commit.decode("ascii").strip() != commit:
        raise QwenLongAcceptanceArtifactError("fixture commit identity differs")
    observed_blob = _git(repository, "rev-parse", f"{commit}:{path}")
    if observed_blob.decode("ascii").strip() != expected_blob:
        raise QwenLongAcceptanceArtifactError(f"committed blob for {path!r} differs")
    payload = _git(repository, "show", f"{commit}:{path}")
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise QwenLongAcceptanceArtifactError(f"committed payload for {path!r} differs")
    return _strict_json_payload(payload, path), len(payload)


def _tokenizer_record(checkpoint_lock: Mapping[str, Any]) -> Mapping[str, Any]:
    records = [
        item
        for item in checkpoint_lock.get("files", [])
        if isinstance(item, Mapping) and item.get("path") == TOKENIZER_PATH
    ]
    if len(records) != 1:
        raise QwenLongAcceptanceArtifactError(
            "checkpoint lock must contain exactly one tokenizer.json record"
        )
    return records[0]


def prompt_token_ids_sha256() -> str:
    """Derive the governed expanded prompt-token identity."""

    return sha256_bytes(canonical_json_bytes([PROMPT_TOKEN_ID] * PROMPT_TOKEN_COUNT))


def prompt_token_id(session_value: Mapping[str, Any], index: int) -> int:
    """Return one prompt token without materializing the 8,000-element list."""

    session = validate_long_acceptance_session(session_value)
    parsed = _integer(index, "long prompt index", 0, PROMPT_TOKEN_COUNT - 1)
    assert session["prompt"]["encoding"] == "repeated_token_id_v1"
    return int(session["prompt"]["token_id"]) if parsed >= 0 else PROMPT_TOKEN_ID


def _validate_fixture_record(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QwenLongAcceptanceArtifactError("workload fixture must be an object")
    record = dict(value)
    exact_keys(
        record,
        {
            "commit",
            "file_sha256",
            "file_size_bytes",
            "git_blob",
            "git_tree",
            "long_context_release_report_id",
            "path",
            "release_file_sha256",
            "release_file_size_bytes",
            "release_git_blob",
            "release_path",
            "schema",
            "workload_id",
        },
        set(),
        "long acceptance workload fixture",
    )
    for field in (
        "file_sha256",
        "long_context_release_report_id",
        "release_file_sha256",
        "workload_id",
    ):
        require_sha256(record[field], f"workload fixture.{field}")
    for field in ("commit", "git_blob", "git_tree", "release_git_blob"):
        if not isinstance(record[field], str) or not _COMMIT.fullmatch(record[field]):
            raise QwenLongAcceptanceArtifactError(
                f"workload fixture.{field} must be a full Git object ID"
            )
    for field in ("file_size_bytes", "release_file_size_bytes"):
        _integer(record[field], f"workload fixture.{field}", 1, 1 << 30)
    _safe_path(record["path"], "workload fixture.path")
    _safe_path(record["release_path"], "workload fixture.release_path")
    expected = {
        "commit": FIXTURE_COMMIT,
        "file_sha256": FIXTURE_FILE_SHA256,
        "file_size_bytes": record["file_size_bytes"],
        "git_blob": FIXTURE_BLOB,
        "git_tree": FIXTURE_TREE,
        "long_context_release_report_id": RELEASE_REPORT_ID,
        "path": FIXTURE_PATH,
        "release_file_sha256": RELEASE_FILE_SHA256,
        "release_file_size_bytes": record["release_file_size_bytes"],
        "release_git_blob": RELEASE_BLOB,
        "release_path": RELEASE_PATH,
        "schema": "opentallas.qwen3.workload_manifest.v1",
        "workload_id": FIXTURE_WORKLOAD_ID,
    }
    if record != expected:
        raise QwenLongAcceptanceArtifactError("workload fixture identity differs")
    return record


def validate_long_acceptance_session(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact immutable 8,000+32 workload contract."""

    session = dict(value)
    exact_keys(
        session,
        {
            "build_id",
            "capability_id",
            "checkpoint_lock_id",
            "claim_boundary",
            "command_program_sha256",
            "context_capacity",
            "generation",
            "graph_id",
            "hbm_logical_sha256",
            "kernel_ir_id",
            "model_id",
            "official_prefill_golden",
            "physical_plan_id",
            "prompt",
            "schema",
            "session_id",
            "session_version",
            "tokenizer",
            "workload_fixture",
        },
        set(),
        "long acceptance session",
    )
    _identity(session, "session_id", "long acceptance session")
    expected_identities = {
        "build_id": EXPECTED_BUILD_ID,
        "capability_id": EXPECTED_CAPABILITY_ID,
        "checkpoint_lock_id": EXPECTED_CHECKPOINT_LOCK_ID,
        "command_program_sha256": EXPECTED_COMMAND_SHA256,
        "graph_id": EXPECTED_GRAPH_ID,
        "hbm_logical_sha256": EXPECTED_HBM_SHA256,
        "kernel_ir_id": EXPECTED_KERNEL_IR_ID,
        "physical_plan_id": EXPECTED_PHYSICAL_PLAN_ID,
    }
    for field, expected in expected_identities.items():
        require_sha256(session[field], f"long acceptance session.{field}")
        if session[field] != expected:
            raise QwenLongAcceptanceArtifactError(
                f"long acceptance session {field} differs"
            )
    if (
        session["schema"] != SESSION_SCHEMA
        or session["session_version"] != SESSION_VERSION
        or session["model_id"] != MODEL_ID
        or session["context_capacity"] != CONTEXT_CAPACITY
        or session["claim_boundary"]
        != {
            "exact_8000_token_acceptance": True,
            "separate_8192_resident_boundary": False,
            "timing_or_performance": False,
        }
    ):
        raise QwenLongAcceptanceArtifactError("long acceptance session boundary differs")

    prompt = session["prompt"]
    if not isinstance(prompt, dict):
        raise QwenLongAcceptanceArtifactError("long acceptance prompt must be an object")
    exact_keys(
        prompt,
        {"encoding", "token_count", "token_id", "token_ids_sha256"},
        set(),
        "long acceptance prompt",
    )
    require_sha256(prompt["token_ids_sha256"], "long acceptance prompt hash")
    if prompt != {
        "encoding": "repeated_token_id_v1",
        "token_count": PROMPT_TOKEN_COUNT,
        "token_id": PROMPT_TOKEN_ID,
        "token_ids_sha256": PROMPT_TOKEN_IDS_SHA256,
    } or prompt_token_ids_sha256() != PROMPT_TOKEN_IDS_SHA256:
        raise QwenLongAcceptanceArtifactError("long acceptance prompt differs")

    generation = session["generation"]
    if not isinstance(generation, dict):
        raise QwenLongAcceptanceArtifactError("long generation must be an object")
    exact_keys(
        generation,
        {
            "eos_token_ids",
            "generated_token_limit",
            "selection",
            "unexpected_early_eos",
        },
        set(),
        "long generation",
    )
    if generation != {
        "eos_token_ids": [151_645, 151_643],
        "generated_token_limit": GENERATED_TOKEN_COUNT,
        "selection": "greedy_lowest_token_id_argmax",
        "unexpected_early_eos": "fail",
    }:
        raise QwenLongAcceptanceArtifactError("long generation policy differs")

    tokenizer = session["tokenizer"]
    if not isinstance(tokenizer, dict):
        raise QwenLongAcceptanceArtifactError("long tokenizer must be an object")
    exact_keys(
        tokenizer,
        {
            "explicit_vocabulary_size",
            "library",
            "library_version",
            "model_vocabulary_size",
            "path",
            "prompt_source",
            "sha256",
        },
        set(),
        "long tokenizer",
    )
    require_sha256(tokenizer["sha256"], "long tokenizer.sha256")
    if tokenizer != {
        "explicit_vocabulary_size": 151_669,
        "library": "tokenizers",
        "library_version": TOKENIZERS_VERSION,
        "model_vocabulary_size": VOCABULARY_SIZE,
        "path": TOKENIZER_PATH,
        "prompt_source": "authenticated_token_id_fixture_no_retokenization",
        "sha256": tokenizer["sha256"],
    }:
        raise QwenLongAcceptanceArtifactError("long tokenizer boundary differs")

    golden = session["official_prefill_golden"]
    if golden != {
        "comparison_status": "pending_common_simulator_execution",
        "greedy_token_id": OFFICIAL_PREFILL_GREEDY_TOKEN_ID,
        "logits_sha256": OFFICIAL_PREFILL_LOGITS_SHA256,
        "release_report_id": RELEASE_REPORT_ID,
    }:
        raise QwenLongAcceptanceArtifactError("official prefill golden differs")
    _validate_fixture_record(session["workload_fixture"])
    if PROMPT_TOKEN_COUNT + GENERATED_TOKEN_COUNT - 1 != FINAL_STATE_LENGTH:
        raise QwenLongAcceptanceArtifactError("long state-length derivation differs")
    if FINAL_STATE_LENGTH > CONTEXT_CAPACITY:
        raise QwenLongAcceptanceArtifactError("long session exceeds physical capacity")
    return session


def build_long_acceptance_session(
    *,
    deployment_root: Path,
    fixture_repository: Path,
) -> dict[str, Any]:
    """Bind the committed fixture and exact V7 deployment into one session."""

    root = Path(deployment_root)
    try:
        manifest = load_strict_json(root / "deployment_manifest.json")
        plan = load_strict_json(root / "physical/physical_plan.json")
        capability = load_strict_json(root / "capability.json")
        checkpoint_lock = load_strict_json(root / "source/checkpoint.lock.json")
    except (OSError, ArtifactError) as exc:
        raise QwenLongAcceptanceArtifactError(
            f"cannot load V7 long deployment: {exc}"
        ) from exc
    for artifact, field, label in (
        (manifest, "build_id", "deployment manifest"),
        (plan, "physical_plan_id", "physical plan"),
        (capability, "capability_id", "capability"),
        (checkpoint_lock, "lock_id", "checkpoint lock"),
    ):
        _identity(artifact, field, label)
    command = plan.get("command_program")
    image = plan.get("hbm", {}).get("image")
    if (
        manifest.get("build_id") != EXPECTED_BUILD_ID
        or manifest.get("graph_id") != EXPECTED_GRAPH_ID
        or manifest.get("capability_id") != EXPECTED_CAPABILITY_ID
        or manifest.get("kernel_ir_id") != EXPECTED_KERNEL_IR_ID
        or manifest.get("physical_plan_id") != EXPECTED_PHYSICAL_PLAN_ID
        or plan.get("graph_id") != EXPECTED_GRAPH_ID
        or plan.get("capability_id") != EXPECTED_CAPABILITY_ID
        or not isinstance(command, dict)
        or command.get("sha256") != EXPECTED_COMMAND_SHA256
        or not isinstance(image, dict)
        or image.get("logical_sha256") != EXPECTED_HBM_SHA256
        or checkpoint_lock.get("lock_id") != EXPECTED_CHECKPOINT_LOCK_ID
        or capability.get("capability_id") != EXPECTED_CAPABILITY_ID
        or capability.get("vector_engine", {}).get("max_attention_context_tokens")
        != CONTEXT_CAPACITY
        or capability.get("vector_engine", {}).get("max_rope_positions")
        != CONTEXT_CAPACITY
    ):
        raise QwenLongAcceptanceArtifactError("V7 long deployment identity differs")

    workload, workload_size = _committed_payload(
        fixture_repository,
        commit=FIXTURE_COMMIT,
        path=FIXTURE_PATH,
        expected_blob=FIXTURE_BLOB,
        expected_sha256=FIXTURE_FILE_SHA256,
    )
    release, release_size = _committed_payload(
        fixture_repository,
        commit=FIXTURE_COMMIT,
        path=RELEASE_PATH,
        expected_blob=RELEASE_BLOB,
        expected_sha256=RELEASE_FILE_SHA256,
    )
    tree = _git(fixture_repository, "rev-parse", f"{FIXTURE_COMMIT}^{{tree}}")
    long_context = workload.get("long_context")
    generator = long_context.get("token_generator") if isinstance(long_context, dict) else None
    release_long = release.get("long_context")
    if (
        tree.decode("ascii").strip() != FIXTURE_TREE
        or workload.get("schema") != "opentallas.qwen3.workload_manifest.v1"
        or workload.get("workload_id") != FIXTURE_WORKLOAD_ID
        or not isinstance(long_context, dict)
        or generator != {"repeat_count": PROMPT_TOKEN_COUNT, "token_id": PROMPT_TOKEN_ID}
        or long_context.get("context_tokens") != PROMPT_TOKEN_COUNT
        or long_context.get("input_token_sha256") != PROMPT_TOKEN_IDS_SHA256
        or long_context.get("expected_logits_sha256")
        != OFFICIAL_PREFILL_LOGITS_SHA256
        or long_context.get("expected_argmax_token_id")
        != OFFICIAL_PREFILL_GREEDY_TOKEN_ID
        or long_context.get("release_report_id") != RELEASE_REPORT_ID
        or workload.get("generation_policy", {}).get("generated_tokens")
        != GENERATED_TOKEN_COUNT
        or workload.get("generation_policy", {}).get("eos_token_ids")
        != [151_645, 151_643]
        or release.get("schema") != "opentallas.qwen3.release_gate.v1"
        or release.get("report_id") != RELEASE_REPORT_ID
        or not isinstance(release_long, dict)
        or release_long.get("input_token_count") != PROMPT_TOKEN_COUNT
        or release_long.get("input_token_sha256") != PROMPT_TOKEN_IDS_SHA256
        or release_long.get("service_argmax_token_id")
        != OFFICIAL_PREFILL_GREEDY_TOKEN_ID
        or release_long.get("logits_differential", {}).get("service_sha256")
        != OFFICIAL_PREFILL_LOGITS_SHA256
    ):
        raise QwenLongAcceptanceArtifactError(
            "committed long-context workload or release evidence differs"
        )
    tokenizer_record = _tokenizer_record(checkpoint_lock)
    require_sha256(tokenizer_record.get("sha256"), "checkpoint tokenizer SHA-256")
    if tokenizers_version != TOKENIZERS_VERSION:
        raise QwenLongAcceptanceArtifactError(
            f"tokenizers version differs: {tokenizers_version!r}"
        )
    body: dict[str, Any] = {
        "build_id": EXPECTED_BUILD_ID,
        "capability_id": EXPECTED_CAPABILITY_ID,
        "checkpoint_lock_id": EXPECTED_CHECKPOINT_LOCK_ID,
        "claim_boundary": {
            "exact_8000_token_acceptance": True,
            "separate_8192_resident_boundary": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": EXPECTED_COMMAND_SHA256,
        "context_capacity": CONTEXT_CAPACITY,
        "generation": {
            "eos_token_ids": [151_645, 151_643],
            "generated_token_limit": GENERATED_TOKEN_COUNT,
            "selection": "greedy_lowest_token_id_argmax",
            "unexpected_early_eos": "fail",
        },
        "graph_id": EXPECTED_GRAPH_ID,
        "hbm_logical_sha256": EXPECTED_HBM_SHA256,
        "kernel_ir_id": EXPECTED_KERNEL_IR_ID,
        "model_id": MODEL_ID,
        "official_prefill_golden": {
            "comparison_status": "pending_common_simulator_execution",
            "greedy_token_id": OFFICIAL_PREFILL_GREEDY_TOKEN_ID,
            "logits_sha256": OFFICIAL_PREFILL_LOGITS_SHA256,
            "release_report_id": RELEASE_REPORT_ID,
        },
        "physical_plan_id": EXPECTED_PHYSICAL_PLAN_ID,
        "prompt": {
            "encoding": "repeated_token_id_v1",
            "token_count": PROMPT_TOKEN_COUNT,
            "token_id": PROMPT_TOKEN_ID,
            "token_ids_sha256": PROMPT_TOKEN_IDS_SHA256,
        },
        "schema": SESSION_SCHEMA,
        "session_version": SESSION_VERSION,
        "tokenizer": {
            "explicit_vocabulary_size": 151_669,
            "library": "tokenizers",
            "library_version": TOKENIZERS_VERSION,
            "model_vocabulary_size": VOCABULARY_SIZE,
            "path": TOKENIZER_PATH,
            "prompt_source": "authenticated_token_id_fixture_no_retokenization",
            "sha256": tokenizer_record["sha256"],
        },
        "workload_fixture": {
            "commit": FIXTURE_COMMIT,
            "file_sha256": FIXTURE_FILE_SHA256,
            "file_size_bytes": workload_size,
            "git_blob": FIXTURE_BLOB,
            "git_tree": FIXTURE_TREE,
            "long_context_release_report_id": RELEASE_REPORT_ID,
            "path": FIXTURE_PATH,
            "release_file_sha256": RELEASE_FILE_SHA256,
            "release_file_size_bytes": release_size,
            "release_git_blob": RELEASE_BLOB,
            "release_path": RELEASE_PATH,
            "schema": "opentallas.qwen3.workload_manifest.v1",
            "workload_id": FIXTURE_WORKLOAD_ID,
        },
    }
    return validate_long_acceptance_session(_identified(body, "session_id"))


def _validate_previous_report(
    report: Mapping[str, Any], session: Mapping[str, Any]
) -> dict[str, Any]:
    value = dict(report)
    _identity(value, "report_id", "previous long execution report")
    if (
        value.get("schema") != EXECUTION_SCHEMA
        or value.get("status") != "pass"
        or value.get("session_id") != session["session_id"]
        or value.get("build_id") != session["build_id"]
        or not isinstance(value.get("step_index"), int)
        or not isinstance(value.get("outputs"), dict)
        or not isinstance(value["outputs"].get("committed_logits"), dict)
    ):
        raise QwenLongAcceptanceArtifactError(
            "previous long execution report boundary differs"
        )
    _integer(
        value["outputs"]["committed_logits"].get("greedy_token_id"),
        "previous long greedy token",
        0,
        VOCABULARY_SIZE - 1,
    )
    return value


def _transaction_id(body: Mapping[str, Any]) -> int:
    seed = {
        "previous_report_id": body["previous_report_id"],
        "session_id": body["session_id"],
        "step_index": body["step_index"],
        "token_id": body["token_id"],
    }
    value = int.from_bytes(hashlib.sha256(canonical_json_bytes(seed)).digest()[:8], "big")
    return value or 1


def validate_long_acceptance_request(
    value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate one causal request in the exact 8,031-transaction chain."""

    session = validate_long_acceptance_session(session_value)
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
        "long acceptance request",
    )
    _identity(request, "request_id", "long acceptance request")
    previous = (
        None
        if previous_report is None
        else _validate_previous_report(previous_report, session)
    )
    expected_step = 0 if previous is None else previous["step_index"] + 1
    step = _integer(
        request["step_index"], "long acceptance request.step_index", 0, TRANSACTION_COUNT - 1
    )
    if step != expected_step:
        raise QwenLongAcceptanceArtifactError("long request step is not contiguous")
    prompt_input = step < PROMPT_TOKEN_COUNT
    generated_index = (
        None if step < PROMPT_TOKEN_COUNT - 1 else step - PROMPT_TOKEN_COUNT + 1
    )
    expected_token = (
        PROMPT_TOKEN_ID
        if prompt_input
        else previous["outputs"]["committed_logits"]["greedy_token_id"]
    )
    expected_previous = None if previous is None else previous["report_id"]
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
        or request["phase"] != ("prefill" if prompt_input else "decode")
        or request["input_role"] != ("prompt" if prompt_input else "generated")
        or request["output_role"]
        != ("prefill_intermediate" if generated_index is None else "generated_token")
        or request["generated_token_index"] != generated_index
        or request["expected_generations"] != expected_state
        or request["expected_lengths"] != expected_state
        or request["transaction_id"] != _transaction_id(request)
    ):
        raise QwenLongAcceptanceArtifactError("long request chain boundary differs")
    return request


def build_long_acceptance_request(
    session_value: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive the next long request from only the session and predecessor."""

    session = validate_long_acceptance_session(session_value)
    previous = (
        None
        if previous_report is None
        else _validate_previous_report(previous_report, session)
    )
    step = 0 if previous is None else previous["step_index"] + 1
    if step >= TRANSACTION_COUNT:
        raise QwenLongAcceptanceArtifactError("long acceptance session is complete")
    prompt_input = step < PROMPT_TOKEN_COUNT
    generated_index = (
        None if step < PROMPT_TOKEN_COUNT - 1 else step - PROMPT_TOKEN_COUNT + 1
    )
    token = (
        PROMPT_TOKEN_ID
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
        "token_id": token,
    }
    body["transaction_id"] = _transaction_id(body)
    return validate_long_acceptance_request(
        _identified(body, "request_id"), session, previous
    )


def validate_long_acceptance_transaction_report(
    value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    request_value: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate the causal and claim-critical fields of one long report."""

    session = validate_long_acceptance_session(session_value)
    request = validate_long_acceptance_request(
        request_value, session, previous_report
    )
    report = dict(value)
    _identity(report, "report_id", "long transaction report")
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
        "session_generation_complete": request["step_index"] == TRANSACTION_COUNT - 1,
        "timing_or_performance": False,
    }
    if (
        report.get("schema") != EXECUTION_SCHEMA
        or report.get("status") != "pass"
        or report.get("mode")
        != "artifact_only_data_bearing_long_acceptance_transaction"
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
        != {"reason": "capability_uncharacterized", "status": "unavailable"}
    ):
        raise QwenLongAcceptanceArtifactError("long transaction report boundary differs")
    step = request["step_index"]
    if report.get("state_before") != {
        "generations": [step] * STATE_COUNT,
        "lengths": [step] * STATE_COUNT,
    }:
        raise QwenLongAcceptanceArtifactError("long transaction prior state differs")
    states = report.get("state")
    if not isinstance(states, list) or len(states) != STATE_COUNT:
        raise QwenLongAcceptanceArtifactError("long transaction state coverage differs")
    for layer, state in enumerate(states):
        if (
            not isinstance(state, dict)
            or state.get("layer") != layer
            or state.get("resource_id") != f"kv.layer.{layer}"
            or state.get("generation") != step + 1
            or state.get("length") != step + 1
        ):
            raise QwenLongAcceptanceArtifactError("long transaction state differs")
        require_sha256(state.get("key_payload_sha256"), "long state key hash")
        require_sha256(state.get("value_payload_sha256"), "long state value hash")
    logits = report.get("outputs", {}).get("committed_logits")
    if not isinstance(logits, dict):
        raise QwenLongAcceptanceArtifactError("long transaction logits are absent")
    _integer(logits.get("greedy_token_id"), "long greedy token", 0, VOCABULARY_SIZE - 1)
    _integer(
        logits.get("greedy_maximum_count"),
        "long greedy maximum count",
        1,
        VOCABULARY_SIZE,
    )
    require_sha256(logits.get("payload_sha256"), "long logits hash")
    if logits.get("size_bytes") != 303_872:
        raise QwenLongAcceptanceArtifactError("long logits byte count differs")
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
        raise QwenLongAcceptanceArtifactError("long counter coverage differs")
    binding = report.get("runtime_binding")
    if not isinstance(binding, dict):
        raise QwenLongAcceptanceArtifactError("long runtime binding is absent")
    for field in (
        "request_registers_sha256",
        "state_metadata_after_sha256",
        "state_metadata_before_sha256",
        "transaction_descriptors_sha256",
    ):
        require_sha256(binding.get(field), f"long runtime binding.{field}")
    if (
        binding.get("request_registers_size_bytes") != 16
        or binding.get("state_metadata_size_bytes") != 2_304
        or binding.get("transaction_descriptors_size_bytes") != 2_304
    ):
        raise QwenLongAcceptanceArtifactError("long runtime binding sizes differ")
    return report


def build_long_acceptance_session_execution(
    session_value: Mapping[str, Any],
    request_values: Sequence[Mapping[str, Any]],
    report_values: Sequence[Mapping[str, Any]],
    *,
    decode_token_ids: Callable[[list[int]], str],
) -> dict[str, Any]:
    """Build the restart-neutral aggregate for one complete 8,000+32 run."""

    session = validate_long_acceptance_session(session_value)
    if len(request_values) != TRANSACTION_COUNT or len(report_values) != TRANSACTION_COUNT:
        raise QwenLongAcceptanceArtifactError("long transaction coverage differs")
    steps: list[dict[str, Any]] = []
    generated: list[int] = []
    counters: Counter[str] = Counter()
    previous: dict[str, Any] | None = None
    previous_metadata_after: str | None = None
    for index, (raw_request, raw_report) in enumerate(
        zip(request_values, report_values, strict=True)
    ):
        request = validate_long_acceptance_request(raw_request, session, previous)
        report = validate_long_acceptance_transaction_report(
            raw_report, session, request, previous
        )
        binding = report["runtime_binding"]
        if (
            previous_metadata_after is not None
            and binding["state_metadata_before_sha256"] != previous_metadata_after
        ):
            raise QwenLongAcceptanceArtifactError("long state-metadata chain differs")
        output_token = report["outputs"]["committed_logits"]["greedy_token_id"]
        if request["output_role"] == "generated_token":
            generated.append(output_token)
            if output_token in session["generation"]["eos_token_ids"]:
                raise QwenLongAcceptanceArtifactError(
                    "long acceptance encountered unexpected early EOS"
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
        previous_metadata_after = binding["state_metadata_after_sha256"]
    if len(generated) != GENERATED_TOKEN_COUNT or previous is None:
        raise QwenLongAcceptanceArtifactError("long generated-token count differs")
    prompt_ids = [PROMPT_TOKEN_ID] * PROMPT_TOKEN_COUNT
    try:
        prompt_text = decode_token_ids(prompt_ids)
        generated_text = decode_token_ids(generated)
        full_text = decode_token_ids([*prompt_ids, *generated])
    except Exception as exc:
        raise QwenLongAcceptanceArtifactError(
            f"cannot decode long acceptance output: {exc}"
        ) from exc
    aggregate_counters = dict(sorted(counters.items()))
    body: dict[str, Any] = {
        "aggregate_counter_sha256": sha256_bytes(
            canonical_json_bytes(aggregate_counters)
        ),
        "aggregate_counters": aggregate_counters,
        "build_id": session["build_id"],
        "claim_boundary": {
            "artifact_only_full_acceptance_executed": True,
            "exact_8000_prompt_executed": True,
            "generated_32_token_decisions_executed": True,
            "official_golden_verified": False,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": session["command_program_sha256"],
        "decode_transaction_count": GENERATED_TOKEN_COUNT - 1,
        "decoded": {
            "full_text": full_text,
            "generated_text": generated_text,
            "prompt_text": prompt_text,
        },
        "eos_observed": False,
        "final_state": previous["state"],
        "generated_token_count": len(generated),
        "generated_token_ids": generated,
        "graph_id": session["graph_id"],
        "mode": "artifact_only_data_bearing_long_acceptance_candidate",
        "prefill_transaction_count": PROMPT_TOKEN_COUNT,
        "prompt": session["prompt"],
        "runner_version": RUNNER_VERSION,
        "schema": SESSION_EXECUTION_SCHEMA,
        "session_id": session["session_id"],
        "status": "execution_complete_reference_pending",
        "step_chain_sha256": sha256_bytes(canonical_json_bytes(steps)),
        "steps": steps,
        "timing": {"reason": "capability_uncharacterized", "status": "unavailable"},
        "tokenizer": session["tokenizer"],
        "transaction_count": TRANSACTION_COUNT,
        "workload_fixture": session["workload_fixture"],
    }
    result = _identified(body, "session_execution_id")
    return validate_long_acceptance_session_execution(
        result, session, decode_token_ids=decode_token_ids
    )


def validate_long_acceptance_session_execution(
    value: Mapping[str, Any],
    session_value: Mapping[str, Any],
    *,
    decode_token_ids: Callable[[list[int]], str] | None = None,
) -> dict[str, Any]:
    """Validate a complete candidate without overclaiming reference closure."""

    session = validate_long_acceptance_session(session_value)
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
            "prefill_transaction_count",
            "prompt",
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
            "workload_fixture",
        },
        set(),
        "long session execution",
    )
    _identity(execution, "session_execution_id", "long session execution")
    expected_claim = {
        "artifact_only_full_acceptance_executed": True,
        "exact_8000_prompt_executed": True,
        "generated_32_token_decisions_executed": True,
        "official_golden_verified": False,
        "target_precision_reference_verified": False,
        "timing_or_performance": False,
    }
    if (
        execution["schema"] != SESSION_EXECUTION_SCHEMA
        or execution["runner_version"] != RUNNER_VERSION
        or execution["status"] != "execution_complete_reference_pending"
        or execution["mode"]
        != "artifact_only_data_bearing_long_acceptance_candidate"
        or execution["session_id"] != session["session_id"]
        or execution["build_id"] != session["build_id"]
        or execution["graph_id"] != session["graph_id"]
        or execution["command_program_sha256"]
        != session["command_program_sha256"]
        or execution["claim_boundary"] != expected_claim
        or execution["prompt"] != session["prompt"]
        or execution["tokenizer"] != session["tokenizer"]
        or execution["workload_fixture"] != session["workload_fixture"]
        or execution["prefill_transaction_count"] != PROMPT_TOKEN_COUNT
        or execution["decode_transaction_count"] != GENERATED_TOKEN_COUNT - 1
        or execution["generated_token_count"] != GENERATED_TOKEN_COUNT
        or execution["transaction_count"] != TRANSACTION_COUNT
        or execution["eos_observed"] is not False
        or execution["timing"]
        != {"reason": "capability_uncharacterized", "status": "unavailable"}
    ):
        raise QwenLongAcceptanceArtifactError("long session execution boundary differs")
    generated = execution["generated_token_ids"]
    if (
        not isinstance(generated, list)
        or len(generated) != GENERATED_TOKEN_COUNT
        or any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or not 0 <= token < VOCABULARY_SIZE
            for token in generated
        )
    ):
        raise QwenLongAcceptanceArtifactError("long generated tokens differ")
    steps = execution["steps"]
    if not isinstance(steps, list) or len(steps) != TRANSACTION_COUNT:
        raise QwenLongAcceptanceArtifactError("long step coverage differs")
    previous_report_id: str | None = None
    previous_output: int | None = None
    previous_metadata: str | None = None
    observed_generated: list[int] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise QwenLongAcceptanceArtifactError("long step must be an object")
        prompt_input = index < PROMPT_TOKEN_COUNT
        generated_index = (
            None if index < PROMPT_TOKEN_COUNT - 1 else index - PROMPT_TOKEN_COUNT + 1
        )
        expected_input = PROMPT_TOKEN_ID if prompt_input else previous_output
        for field in (
            "logits_sha256",
            "report_id",
            "report_sha256",
            "request_id",
            "state_metadata_after_sha256",
            "state_metadata_before_sha256",
        ):
            require_sha256(step.get(field), f"long step[{index}].{field}")
        if (
            expected_input is None
            or step.get("step_index") != index
            or step.get("previous_report_id") != previous_report_id
            or step.get("input_token_id") != expected_input
            or step.get("input_role") != ("prompt" if prompt_input else "generated")
            or step.get("phase") != ("prefill" if prompt_input else "decode")
            or step.get("output_role")
            != ("prefill_intermediate" if generated_index is None else "generated_token")
            or step.get("generated_token_index") != generated_index
            or step.get("state_generation") != index + 1
            or step.get("state_length") != index + 1
            or (
                previous_metadata is not None
                and step.get("state_metadata_before_sha256") != previous_metadata
            )
        ):
            raise QwenLongAcceptanceArtifactError("long step chain differs")
        output = _integer(
            step.get("output_token_id"),
            f"long step[{index}].output_token_id",
            0,
            VOCABULARY_SIZE - 1,
        )
        if generated_index is not None:
            observed_generated.append(output)
        previous_report_id = step["report_id"]
        previous_output = output
        previous_metadata = step["state_metadata_after_sha256"]
    if observed_generated != generated:
        raise QwenLongAcceptanceArtifactError("long generated-token chain differs")
    if execution["step_chain_sha256"] != sha256_bytes(canonical_json_bytes(steps)):
        raise QwenLongAcceptanceArtifactError("long step-chain hash differs")
    counters = execution["aggregate_counters"]
    if (
        not isinstance(counters, dict)
        or len(counters) != 70
        or execution["aggregate_counter_sha256"]
        != sha256_bytes(canonical_json_bytes(counters))
    ):
        raise QwenLongAcceptanceArtifactError("long aggregate counters differ")
    final_state = execution["final_state"]
    if not isinstance(final_state, list) or len(final_state) != STATE_COUNT:
        raise QwenLongAcceptanceArtifactError("long final state coverage differs")
    for layer, state in enumerate(final_state):
        if (
            not isinstance(state, dict)
            or state.get("layer") != layer
            or state.get("resource_id") != f"kv.layer.{layer}"
            or state.get("generation") != FINAL_STATE_LENGTH
            or state.get("length") != FINAL_STATE_LENGTH
        ):
            raise QwenLongAcceptanceArtifactError("long final state differs")
    decoded = execution["decoded"]
    if not isinstance(decoded, dict) or set(decoded) != {
        "full_text",
        "generated_text",
        "prompt_text",
    }:
        raise QwenLongAcceptanceArtifactError("long decoded output differs")
    if decode_token_ids is not None:
        prompt_ids = [PROMPT_TOKEN_ID] * PROMPT_TOKEN_COUNT
        if decoded != {
            "full_text": decode_token_ids([*prompt_ids, *generated]),
            "generated_text": decode_token_ids(generated),
            "prompt_text": decode_token_ids(prompt_ids),
        }:
            raise QwenLongAcceptanceArtifactError("long tokenizer decode differs")
    return execution


def _publish(value: Mapping[str, Any], output: Path, label: str) -> None:
    path = Path(output)
    try:
        publish_bytes_atomic_no_replace(path, canonical_json_bytes(dict(value)))
    except FileExistsError as exc:
        raise QwenLongAcceptanceArtifactError(
            f"{label} already exists: {path}"
        ) from exc
    except OSError as exc:
        raise QwenLongAcceptanceArtifactError(
            f"cannot publish {label}: {exc}"
        ) from exc


def publish_long_acceptance_session(value: Mapping[str, Any], output: Path) -> None:
    _publish(validate_long_acceptance_session(value), output, "long acceptance session")


def publish_long_acceptance_request(
    value: Mapping[str, Any],
    session: Mapping[str, Any],
    previous_report: Mapping[str, Any] | None,
    output: Path,
) -> None:
    _publish(
        validate_long_acceptance_request(value, session, previous_report),
        output,
        "long acceptance request",
    )


def publish_long_acceptance_session_execution(
    value: Mapping[str, Any], session: Mapping[str, Any], output: Path
) -> None:
    _publish(
        validate_long_acceptance_session_execution(value, session),
        output,
        "long acceptance session execution",
    )


__all__ = [
    "CONTEXT_CAPACITY",
    "EXECUTION_SCHEMA",
    "FINAL_STATE_LENGTH",
    "GENERATED_TOKEN_COUNT",
    "PROMPT_TOKEN_COUNT",
    "PROMPT_TOKEN_ID",
    "QwenLongAcceptanceArtifactError",
    "REQUEST_SCHEMA",
    "REQUEST_VERSION",
    "RUNNER_VERSION",
    "SESSION_EXECUTION_SCHEMA",
    "SESSION_SCHEMA",
    "SESSION_VERSION",
    "TRANSACTION_COUNT",
    "build_long_acceptance_request",
    "build_long_acceptance_session",
    "build_long_acceptance_session_execution",
    "prompt_token_id",
    "prompt_token_ids_sha256",
    "publish_long_acceptance_request",
    "publish_long_acceptance_session",
    "publish_long_acceptance_session_execution",
    "validate_long_acceptance_request",
    "validate_long_acceptance_session",
    "validate_long_acceptance_session_execution",
    "validate_long_acceptance_transaction_report",
]
