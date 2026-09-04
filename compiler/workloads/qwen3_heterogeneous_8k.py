"""Authenticated exact-8K Qwen heterogeneous workload-set construction.

This module is deliberately tokenizer-only.  It authenticates and reuses the
official Qwen chat template, the shared ROM semantic suite, the committed
TerminalBench task descriptions, and the governed public-domain corpus.  It
does not import a model framework and it never manufactures expected output
tokens.  A workload set remains preparation evidence until eight separately
executed external-oracle files pass :func:`build_reference_set`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from compiler.qwen3.constants import SESSION_CONTEXT_CAPACITY
from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
from compiler.tensor_accelerator.qwen_agent_protocol import (
    BASH_TOOL,
    BASH_TOOL_SHA256,
    SYSTEM_PROMPT,
)
from compiler.tensor_accelerator.qwen_chat import (
    EOS_TOKEN_IDS,
    EXPLICIT_VOCABULARY_SIZE,
    MODEL_VOCABULARY_SIZE,
    OFFICIAL_CHAT_TEMPLATE_SHA256,
    QwenChatTokenizer,
    SOURCE_FILES,
    SOURCE_REVISION,
)
from compiler.tensor_accelerator.qwen_workload import (
    AGENT_TASK_IDS,
    EXPECTED_ROM_FILES,
    load_shared_workload,
)

from .qwen3 import (
    CORPUS_PATH,
    CORPUS_SHA256,
    CORPUS_SOURCE,
    LONG_PROMPT_TOKENS,
    Workload,
    load_corpus,
    natural_body,
)
from .qwen3_exact_8k import (
    ALGORITHM,
    AuthenticatedWorkloadTokenizer,
    MAX_NEW_TOKENS,
    SEPARATOR,
    build_exact_8k_workload,
    load_construction,
)


REPO = Path(__file__).resolve().parents[2]
WORKLOAD_SET_SCHEMA = "opentallas.abi3.qwen3_heterogeneous_workload_set.v1"
REFERENCE_SET_SCHEMA = "opentallas.abi3.qwen3_heterogeneous_reference_set.v1"
REFERENCE_ORACLE_SCHEMA = "opentallas.abi3.reference_oracle.v1"
WORKLOAD_INDEX_SCHEMA = "opentallas.abi3.workload_index.v1"
VERSION = "1.0.0"
CAMPAIGN_NAME = "qwen3-heterogeneous-exact-8k-v1"
ORACLE_TOOL = "tools/run_qwen3_reference_oracle.py"
HETEROGENEOUS_ORACLE_TOOL_VERSION = "qwen3_reference_oracle.py:v3"
HETEROGENEOUS_GATE_1_LAUNCH_SCHEMA = (
    "opentallas.qwen3.heterogeneous_gate1_launch.v1"
)
HETEROGENEOUS_GATE_1_PROFILE_ID = (
    "qwen3_heterogeneous_exact_8k_external_oracle_v1"
)
WORKLOAD_SET_SCHEMA_PATH = (
    REPO / "schemas/abi3/qwen3_heterogeneous_workload_set_v1.schema.json"
)
REFERENCE_SET_SCHEMA_PATH = (
    REPO / "schemas/abi3/qwen3_heterogeneous_reference_set_v1.schema.json"
)
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)
DEFAULT_CHECKPOINT_LOCK = (
    REPO
    / "results/tensor_accelerator/qwen3_full_model_physical/source/"
    "checkpoint.lock.json"
)
DEFAULT_SHARED_SEMANTICS = (
    REPO / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
)
DEFAULT_TERMINALBENCH_SUITE = (
    REPO / "testdata/compiler/qwen3_8b/terminalbench_tasks.json"
)
DEFAULT_EXACT_8K_CONSTRUCTION = (
    REPO / "configs/abi3/workloads/qwen3_exact_8k_chat_v1.json"
)


class QwenHeterogeneousCampaignError(ArtifactError):
    """A workload-set, source, or independent oracle is not admissible."""


@dataclass(frozen=True, slots=True)
class LaneSpec:
    lane_index: int
    sequence_id: str
    category: str
    source_type: str
    source_id: str
    workload_id: str
    workload_kind: str
    enable_thinking: bool


LANE_SPECS = (
    LaneSpec(
        0,
        "qwen3-8k-lane0-arithmetic",
        "natural_chat",
        "natural",
        "arithmetic",
        "TA-QW-8K-1",
        "long_natural_chat",
        False,
    ),
    LaneSpec(
        1,
        "qwen3-8k-lane1-reasoning",
        "reasoning",
        "natural",
        "reasoning",
        "TA-QW-8K-REASON-1",
        "long_reasoning",
        True,
    ),
    LaneSpec(
        2,
        "qwen3-8k-lane2-agent-hello",
        "agentic_tool",
        "agent",
        "hello-world",
        "TA-QW-8K-AGENT-HELLO-1",
        "long_agentic_tool",
        False,
    ),
    LaneSpec(
        3,
        "qwen3-8k-lane3-stress",
        "stress",
        "stress",
        "repeated-im-start",
        "TA-QW-8K-STRESS-256-1",
        "repeated_special",
        False,
    ),
    LaneSpec(
        4,
        "qwen3-8k-lane4-geography",
        "natural_chat",
        "natural",
        "geography",
        "TA-QW-8K-GEOGRAPHY-1",
        "long_natural_chat",
        False,
    ),
    LaneSpec(
        5,
        "qwen3-8k-lane5-science",
        "natural_chat",
        "natural",
        "science",
        "TA-QW-8K-SCIENCE-1",
        "long_natural_chat",
        False,
    ),
    LaneSpec(
        6,
        "qwen3-8k-lane6-agent-permissions",
        "agentic_tool",
        "agent",
        "fix-permissions",
        "TA-QW-8K-AGENT-PERMISSIONS-1",
        "long_agentic_tool",
        False,
    ),
    LaneSpec(
        7,
        "qwen3-8k-lane7-practical",
        "natural_chat",
        "natural",
        "practical_advice",
        "TA-QW-8K-PRACTICAL-1",
        "long_natural_chat",
        False,
    ),
)
PROFILE_SIZES = (1, 2, 4, 8)


@dataclass(frozen=True, slots=True)
class AuthenticatedInputs:
    chat: QwenChatTokenizer
    checkpoint_lock: dict[str, Any]
    shared_semantics: dict[str, Any]
    terminalbench_suite: dict[str, Any]
    construction: dict[str, Any]
    checkpoint_lock_path: Path
    shared_semantics_path: Path
    terminalbench_suite_path: Path
    construction_path: Path


@dataclass(frozen=True, slots=True)
class CampaignValidation:
    root: Path
    manifest_path: Path
    manifest: dict[str, Any]
    workloads: tuple[dict[str, Any], ...]


def _schema_validate(value: object, path: Path, label: str) -> None:
    try:
        schema = load_strict_json(path)
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
    except Exception as exc:
        if isinstance(exc, QwenHeterogeneousCampaignError):
            raise
        raise QwenHeterogeneousCampaignError(
            f"cannot validate {label} schema: {exc}"
        ) from exc
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors[:8]
        )
        raise QwenHeterogeneousCampaignError(f"{label} schema violation: {details}")


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        body = load_strict_json(path)
        raw = Path(path).read_bytes()
    except (ArtifactError, OSError) as exc:
        raise QwenHeterogeneousCampaignError(f"cannot load {label}: {exc}") from exc
    if raw != canonical_json_bytes(body):
        raise QwenHeterogeneousCampaignError(f"{label} is not canonical JSON")
    return body


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenHeterogeneousCampaignError(f"{label} identity differs")


def _repo_relative(path: Path, repo: Path, label: str) -> str:
    try:
        return Path(path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError as exc:
        raise QwenHeterogeneousCampaignError(
            f"{label} is outside the repository: {path}"
        ) from exc


def _safe_member(root: Path, relative: object, label: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or Path(relative).as_posix() != relative
    ):
        raise QwenHeterogeneousCampaignError(f"{label} path is not normalized")
    candidate = (Path(root).resolve() / relative).resolve()
    try:
        candidate.relative_to(Path(root).resolve())
    except ValueError as exc:
        raise QwenHeterogeneousCampaignError(f"{label} path escapes its root") from exc
    return candidate


def _file_record(path: Path, *, relative_to: Path) -> dict[str, Any]:
    try:
        digest, size = sha256_file(Path(path))
    except OSError as exc:
        raise QwenHeterogeneousCampaignError(f"cannot hash {path}: {exc}") from exc
    return {
        "path": _repo_relative(path, relative_to, "file identity"),
        "sha256": digest,
        "size_bytes": size,
    }


def _recorded_path(path: Path) -> str:
    """Record repository members portably and test fixtures unambiguously."""

    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _oracle_file_record(path: Path) -> dict[str, Any]:
    try:
        digest, size = sha256_file(Path(path))
    except OSError as exc:
        raise QwenHeterogeneousCampaignError(f"cannot hash {path}: {exc}") from exc
    return {
        "path": _recorded_path(path),
        "sha256": digest,
        "size_bytes": size,
    }


def _payload_record(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _check_file_record(
    record: Mapping[str, Any], *, root: Path, label: str
) -> Path:
    path = _safe_member(root, record.get("path"), label)
    try:
        digest, size = sha256_file(path)
    except OSError as exc:
        raise QwenHeterogeneousCampaignError(f"cannot authenticate {label}: {exc}") from exc
    if (digest, size) != (record.get("sha256"), record.get("size_bytes")):
        raise QwenHeterogeneousCampaignError(f"{label} content identity differs")
    return path


def prompt_token_sha256(token_ids: Sequence[int]) -> str:
    return sha256_bytes(canonical_json_bytes(list(token_ids)))


def workload_digest(value: Mapping[str, Any]) -> str:
    try:
        body = {
            "workload_id": value["workload_id"],
            "kind": value["kind"],
            "token_ids": value["token_ids"],
            "max_new_tokens": value["max_new_tokens"],
        }
    except KeyError as exc:
        raise QwenHeterogeneousCampaignError(
            f"workload lacks {exc.args[0]!r} for its semantic identity"
        ) from exc
    return hashlib.sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


def authenticate_campaign_inputs(
    *,
    snapshot: Path = DEFAULT_SNAPSHOT,
    checkpoint_lock_path: Path = DEFAULT_CHECKPOINT_LOCK,
    shared_semantics_path: Path = DEFAULT_SHARED_SEMANTICS,
    terminalbench_suite_path: Path = DEFAULT_TERMINALBENCH_SUITE,
    construction_path: Path = DEFAULT_EXACT_8K_CONSTRUCTION,
) -> AuthenticatedInputs:
    """Authenticate every tokenizer/template/prompt source without a model load."""

    try:
        checkpoint_lock = load_strict_json(Path(checkpoint_lock_path))
        chat = QwenChatTokenizer(Path(snapshot), checkpoint_lock)
        shared = load_shared_workload(Path(shared_semantics_path), chat=chat)
        construction = load_construction(Path(construction_path))
        suite = load_strict_json(Path(terminalbench_suite_path))
    except (ArtifactError, OSError, ValueError) as exc:
        if isinstance(exc, QwenHeterogeneousCampaignError):
            raise
        raise QwenHeterogeneousCampaignError(
            f"Qwen campaign input authentication failed: {exc}"
        ) from exc

    if (
        suite.get("schema") != "opentallas.qwen3.terminalbench_task_suite.v1"
        or suite.get("terminalbench_commit")
        != "d28711d0da2675d0bb1d56de45ae5df6082438a3"
        or suite.get("suite_id") != shared["agent"]["rom_suite_id"]
        or tuple(
            task.get("id") if isinstance(task, Mapping) else None
            for task in suite.get("tasks", [])
        )
        != AGENT_TASK_IDS
    ):
        raise QwenHeterogeneousCampaignError(
            "TerminalBench suite identity or task ordering differs"
        )
    shared_tasks = {task["id"]: task["source"] for task in shared["agent"]["tasks"]}
    if any(task != shared_tasks.get(task["id"]) for task in suite["tasks"]):
        raise QwenHeterogeneousCampaignError(
            "TerminalBench task sources differ from the shared ROM suite"
        )
    expected_suite = EXPECTED_ROM_FILES["agent_suite"]
    suite_digest, _suite_size = sha256_file(Path(terminalbench_suite_path))
    if suite_digest != expected_suite["sha256"]:
        raise QwenHeterogeneousCampaignError(
            "TerminalBench suite bytes differ from the ROM-authenticated source"
        )
    if checkpoint_lock.get("schema") != "opentallas.checkpoint_lock.v1":
        raise QwenHeterogeneousCampaignError("Qwen checkpoint lock schema differs")
    require_sha256(checkpoint_lock.get("lock_id"), "Qwen checkpoint lock ID")
    # load_corpus authenticates the complete public-domain source bytes.
    load_corpus()

    return AuthenticatedInputs(
        chat=chat,
        checkpoint_lock=checkpoint_lock,
        shared_semantics=shared,
        terminalbench_suite=suite,
        construction=construction,
        checkpoint_lock_path=Path(checkpoint_lock_path).resolve(),
        shared_semantics_path=Path(shared_semantics_path).resolve(),
        terminalbench_suite_path=Path(terminalbench_suite_path).resolve(),
        construction_path=Path(construction_path).resolve(),
    )


def _render_prefixed(
    chat: QwenChatTokenizer,
    *,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]] | None,
    enable_thinking: bool,
    corpus_prefix: str,
) -> tuple[str, tuple[int, ...], str]:
    copied = [copy.deepcopy(dict(message)) for message in messages]
    user_positions = [
        index for index, message in enumerate(copied) if message.get("role") == "user"
    ]
    if not user_positions or user_positions[-1] != len(copied) - 1:
        raise QwenHeterogeneousCampaignError(
            "campaign source must end in one canonical user request"
        )
    user = copied[user_positions[-1]]
    query = user.get("content")
    if not isinstance(query, str) or not query:
        raise QwenHeterogeneousCampaignError("canonical user request is empty")
    content = corpus_prefix + SEPARATOR + query
    user["content"] = content
    text = chat.render_chat(
        copied,
        tools=tools,
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )
    ids = tuple(chat.encode(text))
    return text, ids, content


def _maximum_exact_prefix(
    chat: QwenChatTokenizer,
    *,
    corpus: str,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]] | None,
    enable_thinking: bool,
) -> tuple[str, str, tuple[int, ...], str]:
    """Return the greatest corpus character prefix yielding exactly 8K IDs."""

    def at(characters: int) -> tuple[str, tuple[int, ...], str]:
        return _render_prefixed(
            chat,
            messages=messages,
            tools=tools,
            enable_thinking=enable_thinking,
            corpus_prefix=corpus[:characters],
        )

    low, high = 0, len(corpus)
    while low < high:
        middle = (low + high + 1) // 2
        if len(at(middle)[1]) <= LONG_PROMPT_TOKENS:
            low = middle
        else:
            high = middle - 1
    cursor = low
    rendered, ids, content = at(cursor)
    if len(ids) > LONG_PROMPT_TOKENS:
        raise QwenHeterogeneousCampaignError("exact-prefix search crossed 8,000 tokens")
    while cursor < len(corpus):
        candidate = at(cursor + 1)
        if len(candidate[1]) > LONG_PROMPT_TOKENS:
            break
        cursor += 1
        rendered, ids, content = candidate
    if len(ids) != LONG_PROMPT_TOKENS:
        raise QwenHeterogeneousCampaignError(
            f"cannot construct exactly 8,000 rendered tokens; got {len(ids)}"
        )
    prefix = corpus[:cursor]
    if chat.decode(ids, skip_special_tokens=False) != rendered:
        raise QwenHeterogeneousCampaignError(
            "constructed exact-8K prompt does not decode round-trip"
        )
    if tuple(chat.encode(rendered)) != ids:
        raise QwenHeterogeneousCampaignError(
            "constructed exact-8K prompt does not encode round-trip"
        )
    return prefix, rendered, ids, content


def _long_workload(
    inputs: AuthenticatedInputs,
    spec: LaneSpec,
    *,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]] | None,
    source_record: Mapping[str, Any],
) -> Workload:
    prefix, rendered, ids, content = _maximum_exact_prefix(
        inputs.chat,
        corpus=natural_body(load_corpus()),
        messages=messages,
        tools=tools,
        enable_thinking=spec.enable_thinking,
    )
    return Workload(
        workload_id=spec.workload_id,
        kind=spec.workload_kind,
        description=(
            f"Exactly 8,000 authenticated Qwen chat tokens for {spec.category} "
            f"source {spec.source_id!r}, with a deterministic Moby-Dick prefix."
        ),
        rendered_text=rendered,
        token_ids=ids,
        max_new_tokens=MAX_NEW_TOKENS,
        metadata={
            "assembly": {
                "algorithm": ALGORITHM,
                "content_order": ["corpus_prefix", "separator", "canonical_query"],
                "separator": SEPARATOR,
            },
            "campaign_category": spec.category,
            "canonical_source": dict(source_record),
            "canonical_source_sha256": sha256_bytes(
                canonical_json_bytes(dict(source_record))
            ),
            "corpus": CORPUS_SOURCE,
            "corpus_prefix_character_count": len(prefix),
            "corpus_prefix_utf8_sha256": hashlib.sha256(
                prefix.encode("utf-8")
            ).hexdigest(),
            "corpus_sha256": CORPUS_SHA256,
            "enable_thinking": spec.enable_thinking,
            "message_content_utf8_sha256": hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest(),
            "official_chat_template_sha256": OFFICIAL_CHAT_TEMPLATE_SHA256,
            "oracle_output_tokens": "absent_generate_externally",
            "session_context_capacity": SESSION_CONTEXT_CAPACITY,
            "tools": [] if tools is None else [copy.deepcopy(dict(tool)) for tool in tools],
        },
    )


def build_workloads(inputs: AuthenticatedInputs) -> dict[str, dict[str, Any]]:
    """Materialize all eight prompts; no expected output is produced here."""

    natural = {
        row["id"]: row for row in inputs.shared_semantics["natural_questions"]
    }
    agents = {row["id"]: row for row in inputs.shared_semantics["agent"]["tasks"]}
    built: dict[str, dict[str, Any]] = {}
    adapter = AuthenticatedWorkloadTokenizer(inputs.chat)
    for spec in LANE_SPECS:
        if spec.lane_index == 0:
            workload = build_exact_8k_workload(
                adapter,
                inputs.construction,
                construction_path=inputs.construction_path,
            )
        elif spec.source_type == "natural":
            source = natural.get(spec.source_id)
            if source is None or source.get("enable_thinking") is not spec.enable_thinking:
                raise QwenHeterogeneousCampaignError(
                    f"natural source {spec.source_id!r} differs"
                )
            source_record = {
                "enable_thinking": source["enable_thinking"],
                "id": source["id"],
                "messages": source["messages"],
                "source_workload_id": inputs.shared_semantics["workload_id"],
            }
            workload = _long_workload(
                inputs,
                spec,
                messages=source["messages"],
                tools=None,
                source_record=source_record,
            )
        elif spec.source_type == "agent":
            task = agents.get(spec.source_id)
            if task is None:
                raise QwenHeterogeneousCampaignError(
                    f"agent source {spec.source_id!r} differs"
                )
            source_record = {
                "source": task["source"],
                "source_workload_id": inputs.shared_semantics["workload_id"],
                "terminalbench_commit": inputs.shared_semantics["agent"][
                    "terminalbench_commit"
                ],
                "terminalbench_suite_id": inputs.terminalbench_suite["suite_id"],
            }
            workload = _long_workload(
                inputs,
                spec,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": task["source"]["instruction"]},
                ],
                tools=[BASH_TOOL],
                source_record=source_record,
            )
        elif spec.source_type == "stress":
            ids = (151_644,) * LONG_PROMPT_TOKENS
            rendered = inputs.chat.decode(ids, skip_special_tokens=False)
            if tuple(inputs.chat.encode(rendered)) != ids:
                raise QwenHeterogeneousCampaignError(
                    "established repeated-special stress prompt does not round-trip"
                )
            workload = Workload(
                workload_id=spec.workload_id,
                kind=spec.workload_kind,
                description=(
                    "Established 8,000-copy <|im_start|> stress prompt with the "
                    "campaign-wide 256-token terminal cap."
                ),
                rendered_text=rendered,
                token_ids=ids,
                max_new_tokens=MAX_NEW_TOKENS,
                metadata={
                    "campaign_category": spec.category,
                    "derived_from_historical_workload": "TA-QW-STRESS-1",
                    "difference_from_historical_workload": (
                        "max_new_tokens is 256 instead of 32, requiring a new identity"
                    ),
                    "oracle_output_tokens": "absent_generate_externally",
                    "repeated_token_count": LONG_PROMPT_TOKENS,
                    "session_context_capacity": SESSION_CONTEXT_CAPACITY,
                    "special_token": "<|im_start|>",
                    "special_token_id": 151_644,
                },
            )
        else:  # pragma: no cover - static table is exhaustively tested
            raise AssertionError(spec.source_type)
        body = workload.to_dict()
        if (
            body["workload_id"] != spec.workload_id
            or body["kind"] != spec.workload_kind
            or body["prompt_token_count"] != LONG_PROMPT_TOKENS
            or body["max_new_tokens"] != MAX_NEW_TOKENS
            or body["prompt_token_count"] + body["max_new_tokens"]
            > SESSION_CONTEXT_CAPACITY
        ):
            raise QwenHeterogeneousCampaignError(
                f"lane {spec.lane_index} workload boundary differs"
            )
        built[spec.workload_id] = body
    return built


def _source_records(inputs: AuthenticatedInputs, repo: Path) -> dict[str, Any]:
    return {
        "agent_protocol": {
            "bash_tool_sha256": BASH_TOOL_SHA256,
            "suite_id": inputs.terminalbench_suite["suite_id"],
            "system_prompt_sha256": hashlib.sha256(
                SYSTEM_PROMPT.encode("utf-8")
            ).hexdigest(),
            "terminalbench_commit": inputs.terminalbench_suite["terminalbench_commit"],
        },
        "corpus": _file_record(CORPUS_PATH, relative_to=repo),
        "exact_8k_construction": _file_record(
            inputs.construction_path, relative_to=repo
        ),
        "shared_semantics": _file_record(
            inputs.shared_semantics_path, relative_to=repo
        ),
        "terminalbench_suite": _file_record(
            inputs.terminalbench_suite_path, relative_to=repo
        ),
    }


def build_campaign_documents(
    inputs: AuthenticatedInputs,
    *,
    repo: Path = REPO,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Return canonical campaign files ready for create-once publication."""

    workloads = build_workloads(inputs)
    documents: dict[str, bytes] = {}
    lanes: list[dict[str, Any]] = []
    index_entries: dict[str, Any] = {}
    for spec in LANE_SPECS:
        body = workloads[spec.workload_id]
        relative = f"workloads/{spec.workload_id}.json"
        payload = canonical_json_bytes(body)
        documents[relative] = payload
        index_entries[spec.workload_id] = {
            "digest": body["digest"],
            "kind": body["kind"],
            "max_new_tokens": body["max_new_tokens"],
            "path": f"{spec.workload_id}.json",
            "prompt_token_count": body["prompt_token_count"],
        }
        lanes.append(
            {
                "category": spec.category,
                "enable_thinking": spec.enable_thinking,
                "lane_index": spec.lane_index,
                "oracle_binding": {
                    "expected_path": f"references/{spec.workload_id}.json",
                    "file": None,
                    "oracle_result_sha256": None,
                    "producer": ORACLE_TOOL,
                    "required_schema": REFERENCE_ORACLE_SCHEMA,
                    "selected_workload_ids": [spec.workload_id],
                    "status": "pending_production_oracle",
                },
                "sequence_id": spec.sequence_id,
                "source_id": spec.source_id,
                "workload": {
                    "file": _payload_record(relative, payload),
                    "prompt_token_sha256": prompt_token_sha256(body["token_ids"]),
                    "workload_digest": body["digest"],
                    "workload_id": spec.workload_id,
                },
            }
        )

    index = {
        "model_id": "qwen3-8b",
        "schema": WORKLOAD_INDEX_SCHEMA,
        "snapshot": f"Qwen/Qwen3-8B@{SOURCE_REVISION}",
        "tokenizer_sha256": SOURCE_FILES["tokenizer"]["sha256"],
        "workloads": index_entries,
    }
    index_payload = canonical_json_bytes(index)
    documents["workloads/index.json"] = index_payload
    body: dict[str, Any] = {
        "abi_version": "3.0",
        "batch_profiles": [
            {
                "batch_size": size,
                "profile_id": f"qwen3-heterogeneous-exact-8k-b{size}",
                "sequence_ids": [spec.sequence_id for spec in LANE_SPECS[:size]],
            }
            for size in PROFILE_SIZES
        ],
        "campaign_name": CAMPAIGN_NAME,
        "claim_boundary": {
            "accelerator_executed": False,
            "gate1_correctness_passed": False,
            "model_executed": False,
            "oracle_results_frozen": False,
            "runnable_batch_request": False,
            "tokenizer_only_construction": True,
            "tpot_claim": False,
        },
        "execution_contract": {
            "homogeneous_comparison_contract_permitted": False,
            "one_physical_batch_required": True,
            "required_request_schema": (
                "opentallas.abi3.heterogeneous_batch_request.v1"
            ),
        },
        "generation": {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "include_eos_in_output": True,
            "max_new_tokens": MAX_NEW_TOKENS,
            "selection": "greedy_lowest_token_id_argmax",
            "stop_rule": "first_official_eos_or_exact_cap",
        },
        "lanes": lanes,
        "model": {
            "checkpoint_lock": {
                **_file_record(inputs.checkpoint_lock_path, relative_to=repo),
                "lock_id": inputs.checkpoint_lock["lock_id"],
            },
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
            "id": "qwen3-8b",
            "model_vocabulary_size": MODEL_VOCABULARY_SIZE,
            "official_chat_template_sha256": OFFICIAL_CHAT_TEMPLATE_SHA256,
            "repository": "Qwen/Qwen3-8B",
            "revision": SOURCE_REVISION,
            "tokenizer_config_sha256": SOURCE_FILES["tokenizer_config"]["sha256"],
            "tokenizer_sha256": SOURCE_FILES["tokenizer"]["sha256"],
        },
        "schema": WORKLOAD_SET_SCHEMA,
        "sources": _source_records(inputs, Path(repo)),
        "status": "preparation_pending_oracles",
        "version": VERSION,
        "workload_index": _payload_record("workloads/index.json", index_payload),
    }
    body["workload_set_id"] = sha256_bytes(canonical_json_bytes(body))
    documents["manifest.json"] = canonical_json_bytes(body)
    return documents, body


def _codec_encode(codec: Any, text: str) -> list[int]:
    try:
        value = codec.encode(text)
    except Exception as exc:
        raise QwenHeterogeneousCampaignError(
            f"authenticated tokenizer cannot encode prompt: {exc}"
        ) from exc
    return [int(token) for token in value]


def _codec_decode(codec: Any, ids: Sequence[int], *, special: bool) -> str:
    try:
        return str(codec.decode(list(ids), skip_special_tokens=not special))
    except Exception as exc:
        raise QwenHeterogeneousCampaignError(
            f"authenticated tokenizer cannot decode tokens: {exc}"
        ) from exc


def validate_workload_set(
    manifest_path: Path,
    *,
    codec: Any,
    repo: Path = REPO,
    expected_workloads: Mapping[str, Mapping[str, Any]] | None = None,
    expected_sources: Mapping[str, Any] | None = None,
) -> CampaignValidation:
    """Validate schema, hashes, exact prompts, nesting, and preparation status."""

    path = Path(manifest_path).resolve()
    root = path.parent
    manifest = _load_canonical(path, "heterogeneous workload-set manifest")
    _schema_validate(manifest, WORKLOAD_SET_SCHEMA_PATH, "workload-set manifest")
    _identity(manifest, "workload_set_id", "workload-set manifest")
    if manifest.get("schema") != WORKLOAD_SET_SCHEMA:
        raise QwenHeterogeneousCampaignError("unsupported workload-set schema")
    if manifest["generation"] != {
        "eos_token_ids": list(EOS_TOKEN_IDS),
        "include_eos_in_output": True,
        "max_new_tokens": MAX_NEW_TOKENS,
        "selection": "greedy_lowest_token_id_argmax",
        "stop_rule": "first_official_eos_or_exact_cap",
    }:
        raise QwenHeterogeneousCampaignError("campaign generation contract differs")
    model = manifest["model"]
    expected_model = {
        "eos_token_ids": list(EOS_TOKEN_IDS),
        "explicit_vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
        "id": "qwen3-8b",
        "model_vocabulary_size": MODEL_VOCABULARY_SIZE,
        "official_chat_template_sha256": OFFICIAL_CHAT_TEMPLATE_SHA256,
        "repository": "Qwen/Qwen3-8B",
        "revision": SOURCE_REVISION,
        "tokenizer_config_sha256": SOURCE_FILES["tokenizer_config"]["sha256"],
        "tokenizer_sha256": SOURCE_FILES["tokenizer"]["sha256"],
    }
    if {key: model.get(key) for key in expected_model} != expected_model:
        raise QwenHeterogeneousCampaignError("authenticated Qwen model boundary differs")
    checkpoint_path = _check_file_record(
        model["checkpoint_lock"], root=Path(repo), label="checkpoint lock"
    )
    checkpoint = load_strict_json(checkpoint_path)
    if checkpoint.get("lock_id") != model["checkpoint_lock"].get("lock_id"):
        raise QwenHeterogeneousCampaignError("checkpoint lock identity differs")
    checkpoint_sources = {
        record.get("path"): record
        for record in checkpoint.get("files", [])
        if isinstance(record, Mapping)
    }
    if any(
        checkpoint_sources.get(expected["path"]) != expected
        for expected in SOURCE_FILES.values()
    ):
        raise QwenHeterogeneousCampaignError(
            "checkpoint lock does not bind the pinned Qwen tokenizer sources"
        )
    source_paths: dict[str, Path] = {}
    for name in (
        "corpus",
        "exact_8k_construction",
        "shared_semantics",
        "terminalbench_suite",
    ):
        source_paths[name] = _check_file_record(
            manifest["sources"][name], root=Path(repo), label=f"source {name}"
        )
    if expected_sources is not None and manifest["sources"] != dict(expected_sources):
        raise QwenHeterogeneousCampaignError(
            "campaign source records differ from authenticated inputs"
        )
    if manifest["sources"]["corpus"]["sha256"] != CORPUS_SHA256:
        raise QwenHeterogeneousCampaignError("campaign corpus is not the governed source")
    try:
        load_construction(source_paths["exact_8k_construction"])
        shared_source = load_shared_workload(source_paths["shared_semantics"])
        terminalbench_source = load_strict_json(source_paths["terminalbench_suite"])
    except (ArtifactError, OSError, ValueError) as exc:
        raise QwenHeterogeneousCampaignError(
            f"campaign semantic source validation failed: {exc}"
        ) from exc
    if (
        terminalbench_source.get("schema")
        != "opentallas.qwen3.terminalbench_task_suite.v1"
        or terminalbench_source.get("suite_id")
        != shared_source["agent"]["rom_suite_id"]
        or terminalbench_source.get("terminalbench_commit")
        != shared_source["agent"]["terminalbench_commit"]
        or terminalbench_source.get("tasks")
        != [task["source"] for task in shared_source["agent"]["tasks"]]
    ):
        raise QwenHeterogeneousCampaignError(
            "TerminalBench and shared semantic source identities differ"
        )
    protocol = manifest["sources"]["agent_protocol"]
    if protocol != {
        "bash_tool_sha256": BASH_TOOL_SHA256,
        "suite_id": terminalbench_source["suite_id"],
        "system_prompt_sha256": hashlib.sha256(
            SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "terminalbench_commit": terminalbench_source["terminalbench_commit"],
    }:
        raise QwenHeterogeneousCampaignError("agent protocol boundary differs")

    lanes = manifest["lanes"]
    workloads: list[dict[str, Any]] = []
    prompt_hashes: list[str] = []
    workload_ids: list[str] = []
    workload_digests: list[str] = []
    workload_paths: list[str] = []
    expected_index_entries: dict[str, Any] = {}
    workload_keys = {
        "description",
        "digest",
        "kind",
        "max_new_tokens",
        "metadata",
        "prompt_token_count",
        "rendered_text",
        "rendered_text_sha256",
        "token_ids",
        "workload_id",
    }
    for position, (lane, spec) in enumerate(zip(lanes, LANE_SPECS, strict=True)):
        if {
            "category": lane["category"],
            "enable_thinking": lane["enable_thinking"],
            "lane_index": lane["lane_index"],
            "sequence_id": lane["sequence_id"],
            "source_id": lane["source_id"],
        } != {
            "category": spec.category,
            "enable_thinking": spec.enable_thinking,
            "lane_index": spec.lane_index,
            "sequence_id": spec.sequence_id,
            "source_id": spec.source_id,
        }:
            raise QwenHeterogeneousCampaignError(
                f"lane {position} category, source, or order differs"
            )
        binding = lane["workload"]
        workload_path = _check_file_record(
            binding["file"], root=root, label=f"lane {position} workload"
        )
        workload = _load_canonical(workload_path, f"lane {position} workload")
        if set(workload) != workload_keys:
            raise QwenHeterogeneousCampaignError(
                f"lane {position} workload fields differ"
            )
        ids = workload.get("token_ids")
        if (
            not isinstance(ids, list)
            or len(ids) != LONG_PROMPT_TOKENS
            or any(
                isinstance(token, bool)
                or not isinstance(token, int)
                or not 0 <= token < EXPLICIT_VOCABULARY_SIZE
                for token in ids
            )
            or workload.get("prompt_token_count") != LONG_PROMPT_TOKENS
        ):
            raise QwenHeterogeneousCampaignError(
                f"lane {position} prompt is not exactly 8,000 legal token IDs"
            )
        if workload.get("max_new_tokens") != MAX_NEW_TOKENS:
            raise QwenHeterogeneousCampaignError(
                f"lane {position} max_new_tokens is not 256"
            )
        if workload["prompt_token_count"] + workload["max_new_tokens"] > SESSION_CONTEXT_CAPACITY:
            raise QwenHeterogeneousCampaignError(
                f"lane {position} prompt and decode cap exceed context capacity"
            )
        if (
            workload.get("workload_id") != spec.workload_id
            or workload.get("kind") != spec.workload_kind
            or workload.get("digest") != workload_digest(workload)
            or binding.get("workload_id") != workload.get("workload_id")
            or binding.get("workload_digest") != workload.get("digest")
            or binding.get("prompt_token_sha256") != prompt_token_sha256(ids)
        ):
            raise QwenHeterogeneousCampaignError(
                f"lane {position} workload semantic identity differs"
            )
        rendered = workload.get("rendered_text")
        if (
            not isinstance(rendered, str)
            or hashlib.sha256(rendered.encode("utf-8")).hexdigest()
            != workload.get("rendered_text_sha256")
            or _codec_decode(codec, ids, special=True) != rendered
            or _codec_encode(codec, rendered) != ids
        ):
            raise QwenHeterogeneousCampaignError(
                f"lane {position} prompt does not round-trip through the authenticated tokenizer"
            )
        if expected_workloads is not None and workload != dict(
            expected_workloads[spec.workload_id]
        ):
            raise QwenHeterogeneousCampaignError(
                f"lane {position} differs from its authenticated source reconstruction"
            )
        oracle = lane["oracle_binding"]
        expected_oracle = {
            "expected_path": f"references/{spec.workload_id}.json",
            "file": None,
            "oracle_result_sha256": None,
            "producer": ORACLE_TOOL,
            "required_schema": REFERENCE_ORACLE_SCHEMA,
            "selected_workload_ids": [spec.workload_id],
            "status": "pending_production_oracle",
        }
        if oracle != expected_oracle:
            raise QwenHeterogeneousCampaignError(
                f"lane {position} must retain one explicit pending production oracle binding"
            )
        workloads.append(workload)
        prompt_hashes.append(binding["prompt_token_sha256"])
        workload_ids.append(workload["workload_id"])
        workload_digests.append(workload["digest"])
        workload_paths.append(binding["file"]["path"])
        expected_index_entries[workload["workload_id"]] = {
            "digest": workload["digest"],
            "kind": workload["kind"],
            "max_new_tokens": workload["max_new_tokens"],
            "path": workload_path.name,
            "prompt_token_count": workload["prompt_token_count"],
        }
    for label, values in (
        ("workload IDs", workload_ids),
        ("workload files", workload_paths),
        ("workload digests", workload_digests),
        ("prompt token identities", prompt_hashes),
    ):
        if len(set(values)) != len(values):
            raise QwenHeterogeneousCampaignError(
                f"heterogeneous campaign has cloned or duplicate {label}"
            )

    index_path = _check_file_record(
        manifest["workload_index"], root=root, label="workload index"
    )
    index = _load_canonical(index_path, "workload index")
    expected_index = {
        "model_id": "qwen3-8b",
        "schema": WORKLOAD_INDEX_SCHEMA,
        "snapshot": f"Qwen/Qwen3-8B@{SOURCE_REVISION}",
        "tokenizer_sha256": SOURCE_FILES["tokenizer"]["sha256"],
        "workloads": expected_index_entries,
    }
    if index != expected_index:
        raise QwenHeterogeneousCampaignError("workload index differs from lane files")
    expected_profiles = [
        {
            "batch_size": size,
            "profile_id": f"qwen3-heterogeneous-exact-8k-b{size}",
            "sequence_ids": [spec.sequence_id for spec in LANE_SPECS[:size]],
        }
        for size in PROFILE_SIZES
    ]
    if manifest["batch_profiles"] != expected_profiles:
        raise QwenHeterogeneousCampaignError(
            "B=1/2/4/8 profiles are not exact nested ordered campaign prefixes"
        )
    first_four_categories = {lane["category"] for lane in lanes[:4]}
    if first_four_categories != {"natural_chat", "reasoning", "agentic_tool", "stress"}:
        raise QwenHeterogeneousCampaignError(
            "B=4 profile does not introduce all four required workload categories"
        )
    return CampaignValidation(root, path, manifest, tuple(workloads))


def heterogeneous_gate_1_launch_contract(
    campaign: CampaignValidation, lane_index: int
) -> dict[str, Any]:
    """Return the exact production launch contract for one singleton oracle."""

    if not 0 <= lane_index < len(LANE_SPECS):
        raise QwenHeterogeneousCampaignError("oracle lane index is out of range")
    spec = LANE_SPECS[lane_index]
    lane = campaign.manifest["lanes"][lane_index]
    workload = campaign.workloads[lane_index]
    manifest_file = _oracle_file_record(campaign.manifest_path)
    return {
        "schema": HETEROGENEOUS_GATE_1_LAUNCH_SCHEMA,
        "profile_id": HETEROGENEOUS_GATE_1_PROFILE_ID,
        "workload_set": {
            "manifest_sha256": manifest_file["sha256"],
            "workload_set_id": campaign.manifest["workload_set_id"],
        },
        "lane": {
            "category": spec.category,
            "lane_index": spec.lane_index,
            "sequence_id": spec.sequence_id,
            "source_id": spec.source_id,
        },
        "workload": {
            "max_new_tokens": MAX_NEW_TOKENS,
            "prompt_token_count": LONG_PROMPT_TOKENS,
            "prompt_token_sha256": lane["workload"]["prompt_token_sha256"],
            "workload_digest": workload["digest"],
            "workload_file_sha256": lane["workload"]["file"]["sha256"],
            "workload_id": spec.workload_id,
        },
        "selection": "greedy_lowest_token_id_argmax",
        "terminal": {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "include_eos_in_output": True,
            "rule": "first_official_eos_or_exact_cap",
        },
        "prefill": {
            "chunk_tokens": 512,
            "mode": "chunked_forward_kv_cache",
        },
        "numeric": {
            "attention_implementation": "sdpa",
            "dtype": "bfloat16",
        },
        "placement": {
            "cpu_memory_gib": 80,
            "gpu_memory_gib": 8,
            "policy": "auto",
        },
    }


def heterogeneous_oracle_input_binding(
    campaign: CampaignValidation, lane_index: int
) -> dict[str, Any]:
    """Bind an oracle input record to one exact campaign lane."""

    contract = heterogeneous_gate_1_launch_contract(campaign, lane_index)
    lane = contract["lane"]
    workload = contract["workload"]
    return {
        "manifest_file": _oracle_file_record(campaign.manifest_path),
        "workload_set_id": contract["workload_set"]["workload_set_id"],
        "selected_lane": {
            **lane,
            **workload,
        },
    }


def _command_option_values(argv: Sequence[str], option: str) -> list[str] | None:
    """Return option values, or ``None`` for a missing/malformed value."""

    values: list[str] = []
    position = 0
    while position < len(argv):
        argument = argv[position]
        if argument == option:
            if position + 1 >= len(argv) or argv[position + 1].startswith("--"):
                return None
            values.append(argv[position + 1])
            position += 2
            continue
        prefix = f"{option}="
        if argument.startswith(prefix):
            value = argument[len(prefix) :]
            if not value:
                return None
            values.append(value)
        position += 1
    return values


def _command_path_matches(value: str, expected: Path) -> bool:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve() == Path(expected).resolve()
    return candidate.as_posix() == _recorded_path(expected)


def validate_production_oracle(
    oracle_path: Path,
    *,
    campaign: CampaignValidation,
    lane_index: int,
    codec: Any,
) -> tuple[dict[str, Any], str]:
    """Validate one independent, singleton, full-checkpoint oracle result."""

    if not 0 <= lane_index < len(LANE_SPECS):
        raise QwenHeterogeneousCampaignError("oracle lane index is out of range")
    spec = LANE_SPECS[lane_index]
    lane = campaign.manifest["lanes"][lane_index]
    workload = campaign.workloads[lane_index]
    expected_oracle_path = _safe_member(
        campaign.root,
        lane["oracle_binding"]["expected_path"],
        f"lane {lane_index} expected oracle",
    )
    if Path(oracle_path).resolve() != expected_oracle_path:
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle is not at its manifest-declared path"
        )
    body = _load_canonical(Path(oracle_path), f"lane {lane_index} oracle")
    if body.get("schema") != REFERENCE_ORACLE_SCHEMA:
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle schema differs"
        )
    if (
        body.get("evidence_class") != "external_reference_comparator"
        or body.get("model_id") != "qwen3-8b"
        or body.get("tokenizer_sha256")
        != campaign.manifest["model"]["tokenizer_sha256"]
        or body.get("selection") != "greedy_lowest_token_id_argmax"
        or body.get("dtype") != "bfloat16"
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle model or numeric boundary differs"
        )
    producer = body.get("producer")
    if (
        not isinstance(producer, Mapping)
        or producer.get("tool") != ORACLE_TOOL
        or producer.get("tool_version") != HETEROGENEOUS_ORACLE_TOOL_VERSION
        or producer.get("selected_workload_ids") != [spec.workload_id]
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle was not independently selected as one workload"
        )
    command = producer.get("command_argv")
    heterogeneous_options = (
        _command_option_values(command, "--heterogeneous-gate-1-production")
        if isinstance(command, list)
        and all(isinstance(argument, str) for argument in command)
        else None
    )
    only_options = (
        _command_option_values(command, "--only")
        if isinstance(command, list)
        and all(isinstance(argument, str) for argument in command)
        else None
    )
    output_options = (
        _command_option_values(command, "--output")
        if isinstance(command, list)
        and all(isinstance(argument, str) for argument in command)
        else None
    )
    if (
        not isinstance(command, list)
        or not command
        or command[0] != ORACLE_TOOL
        or heterogeneous_options is None
        or len(heterogeneous_options) != 1
        or not _command_path_matches(
            heterogeneous_options[0], campaign.manifest_path
        )
        or only_options != [spec.workload_id]
        or output_options is None
        or len(output_options) != 1
        or not _command_path_matches(output_options[0], expected_oracle_path)
        or "--gate-1-production" in command
        or "--agent-episode" in command
        or "--force" in command
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle command did not request one heterogeneous production lane"
        )
    results = body.get("results")
    if not isinstance(results, Mapping) or set(results) != {spec.workload_id}:
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle must contain exactly one selected result"
        )
    input_identity = body.get("input_identity")
    if not isinstance(input_identity, Mapping):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle has no authenticated input identity"
        )
    if set(input_identity) != {
        "checkpoint_lock",
        "exact_8k_construction",
        "heterogeneous_workload_set",
        "workload_index",
        "workload_sources",
    }:
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle authenticated input fields differ"
        )
    checkpoint = input_identity.get("checkpoint_lock")
    expected_checkpoint = campaign.manifest["model"]["checkpoint_lock"]
    expected_checkpoint_identity = _oracle_file_record(
        REPO / expected_checkpoint["path"]
    )
    if (
        checkpoint != expected_checkpoint_identity
        or expected_checkpoint_identity["sha256"] != expected_checkpoint["sha256"]
        or expected_checkpoint_identity["size_bytes"]
        != expected_checkpoint["size_bytes"]
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle checkpoint-lock binding differs"
        )
    index_identity = input_identity.get("workload_index")
    source_identities = input_identity.get("workload_sources")
    expected_index_identity = _oracle_file_record(
        campaign.root / campaign.manifest["workload_index"]["path"]
    )
    if (
        index_identity != expected_index_identity
        or expected_index_identity["sha256"]
        != campaign.manifest["workload_index"]["sha256"]
        or expected_index_identity["size_bytes"]
        != campaign.manifest["workload_index"]["size_bytes"]
        or not isinstance(source_identities, Mapping)
        or set(source_identities) != {spec.workload_id}
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle workload-index binding differs"
        )
    source_identity = source_identities[spec.workload_id]
    expected_source = lane["workload"]["file"]
    expected_source_identity = _oracle_file_record(
        campaign.root / expected_source["path"]
    )
    if (
        source_identity != expected_source_identity
        or expected_source_identity["sha256"] != expected_source["sha256"]
        or expected_source_identity["size_bytes"] != expected_source["size_bytes"]
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle workload-file binding differs"
        )
    construction_identity = input_identity.get("exact_8k_construction")
    expected_construction = campaign.manifest["sources"]["exact_8k_construction"]
    expected_construction_identity = _oracle_file_record(
        REPO / expected_construction["path"]
    )
    if (
        construction_identity != expected_construction_identity
        or expected_construction_identity["sha256"]
        != expected_construction["sha256"]
        or expected_construction_identity["size_bytes"]
        != expected_construction["size_bytes"]
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle exact-8K construction binding differs"
        )
    workload_set_identity = input_identity.get("heterogeneous_workload_set")
    if workload_set_identity != heterogeneous_oracle_input_binding(
        campaign, lane_index
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle workload-set or selected-lane binding differs"
        )
    preflight = body.get("production_checkpoint_preflight")
    if (
        not isinstance(preflight, Mapping)
        or preflight.get("completed_before_model_framework_import") is not True
        or preflight.get("full_byte_hash_verified") is not True
        or preflight.get("lock_id") != expected_checkpoint["lock_id"]
        or preflight.get("lock_source_sha256") != expected_checkpoint["sha256"]
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle did not authenticate the complete checkpoint"
        )
    launch = body.get("production_launch")
    contract = launch.get("contract") if isinstance(launch, Mapping) else None
    if (
        not isinstance(launch, Mapping)
        or launch.get("explicitly_requested") is not True
        or contract != heterogeneous_gate_1_launch_contract(campaign, lane_index)
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle production launch contract differs"
        )
    result = results[spec.workload_id]
    if not isinstance(result, Mapping):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle result is not an object"
        )
    ids = result.get("generated_token_ids")
    if (
        not isinstance(ids, list)
        or not ids
        or any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or not 0 <= token < EXPLICIT_VOCABULARY_SIZE
            for token in ids
        )
        or result.get("generated_token_count") != len(ids)
        or result.get("prompt_token_count") != LONG_PROMPT_TOKENS
        or result.get("workload_digest") != workload["digest"]
        or result.get("kind") != workload["kind"]
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle tokens are illegal, padded, or misbound"
        )
    stop = result.get("stop_reason")
    eos_positions = [index for index, token in enumerate(ids) if token in EOS_TOKEN_IDS]
    if stop == "eos":
        terminal_ok = (
            len(ids) <= MAX_NEW_TOKENS
            and eos_positions == [len(ids) - 1]
        )
    elif stop == "max_new_tokens":
        terminal_ok = len(ids) == MAX_NEW_TOKENS and not eos_positions
    else:
        terminal_ok = False
    if not terminal_ok:
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle violates first-EOS-or-exact-256 termination"
        )
    if (
        result.get("raw_decoded_text") != _codec_decode(codec, ids, special=True)
        or result.get("visible_decoded_text")
        != _codec_decode(codec, ids, special=False)
    ):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle decoded text differs from token IDs"
        )
    if not isinstance(result.get("prefill_association"), Mapping):
        raise QwenHeterogeneousCampaignError(
            f"lane {lane_index} oracle lacks prefill-association provenance"
        )
    return dict(result), sha256_bytes(canonical_json_bytes(dict(result)))


def build_reference_set(
    campaign: CampaignValidation,
    *,
    codec: Any,
) -> dict[str, Any]:
    """Freeze all eight existing singleton oracles into one bound set.

    Missing or invalid oracle files fail closed; no pending reference set is
    emitted because such an object could be mistaken for runnable input.
    """

    references: list[dict[str, Any]] = []
    result_ids: list[str] = []
    for lane_index, (lane, workload) in enumerate(
        zip(campaign.manifest["lanes"], campaign.workloads, strict=True)
    ):
        oracle_path = _safe_member(
            campaign.root,
            lane["oracle_binding"]["expected_path"],
            f"lane {lane_index} expected oracle",
        )
        if not oracle_path.is_file():
            raise QwenHeterogeneousCampaignError(
                f"lane {lane_index} production oracle is missing: {oracle_path}"
            )
        _result, result_id = validate_production_oracle(
            oracle_path,
            campaign=campaign,
            lane_index=lane_index,
            codec=codec,
        )
        reference = {
            "oracle_file": _file_record(oracle_path, relative_to=campaign.root),
            "oracle_result_sha256": result_id,
            "prompt_token_sha256": lane["workload"]["prompt_token_sha256"],
            "sequence_id": lane["sequence_id"],
            "workload_digest": workload["digest"],
            "workload_id": workload["workload_id"],
        }
        references.append(reference)
        result_ids.append(result_id)
    if len(set(result_ids)) != len(result_ids):
        raise QwenHeterogeneousCampaignError(
            "independent oracle result identities are duplicated"
        )
    manifest_record = _file_record(
        campaign.manifest_path, relative_to=campaign.root
    )
    body: dict[str, Any] = {
        "abi_version": "3.0",
        "claim_boundary": {
            "accelerator_execution": False,
            "external_oracles_validated": True,
            "gate1_correctness_passed": False,
            "runnable_batch_inputs_complete": True,
            "tpot_claim": False,
        },
        "references": references,
        "schema": REFERENCE_SET_SCHEMA,
        "status": "production_ready",
        "workload_set": {
            "file": manifest_record,
            "workload_set_id": campaign.manifest["workload_set_id"],
        },
    }
    body["reference_set_id"] = sha256_bytes(canonical_json_bytes(body))
    _schema_validate(body, REFERENCE_SET_SCHEMA_PATH, "reference set")
    return body


def validate_reference_set(
    reference_set_path: Path,
    *,
    campaign: CampaignValidation,
    codec: Any,
) -> dict[str, Any]:
    body = _load_canonical(Path(reference_set_path), "heterogeneous reference set")
    _schema_validate(body, REFERENCE_SET_SCHEMA_PATH, "reference set")
    _identity(body, "reference_set_id", "reference set")
    manifest_record = body["workload_set"]["file"]
    if (
        body["workload_set"]["workload_set_id"]
        != campaign.manifest["workload_set_id"]
        or manifest_record
        != _file_record(campaign.manifest_path, relative_to=campaign.root)
    ):
        raise QwenHeterogeneousCampaignError(
            "reference set names a different workload set"
        )
    expected = build_reference_set(campaign, codec=codec)
    if body != expected:
        raise QwenHeterogeneousCampaignError(
            "reference set differs from its independently validated oracle files"
        )
    return body


__all__ = [
    "AuthenticatedInputs",
    "CAMPAIGN_NAME",
    "CampaignValidation",
    "DEFAULT_CHECKPOINT_LOCK",
    "DEFAULT_EXACT_8K_CONSTRUCTION",
    "DEFAULT_SHARED_SEMANTICS",
    "DEFAULT_SNAPSHOT",
    "DEFAULT_TERMINALBENCH_SUITE",
    "HETEROGENEOUS_GATE_1_LAUNCH_SCHEMA",
    "HETEROGENEOUS_GATE_1_PROFILE_ID",
    "HETEROGENEOUS_ORACLE_TOOL_VERSION",
    "LANE_SPECS",
    "MAX_NEW_TOKENS",
    "PROFILE_SIZES",
    "QwenHeterogeneousCampaignError",
    "REFERENCE_SET_SCHEMA",
    "WORKLOAD_SET_SCHEMA",
    "authenticate_campaign_inputs",
    "build_campaign_documents",
    "build_reference_set",
    "build_workloads",
    "heterogeneous_gate_1_launch_contract",
    "heterogeneous_oracle_input_binding",
    "prompt_token_sha256",
    "validate_production_oracle",
    "validate_reference_set",
    "validate_workload_set",
    "workload_digest",
]
