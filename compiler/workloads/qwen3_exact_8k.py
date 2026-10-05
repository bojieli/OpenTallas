"""Governed construction of the Qwen exact-8K natural chat workload.

The short semantic suite already freezes the official Qwen chat template and
the ROM-authenticated arithmetic question.  This module does not author a new
prompt.  It places a deterministic prefix of the existing public-domain corpus
before that canonical question in the same user message and chooses the prefix
length for an exact 8,000-token *rendered* chat prompt.

Only tokenizer work happens here.  In particular, this module never imports or
runs the language model and never supplies expected output tokens.  Those must
come from the separately executed external oracle after the workload is frozen.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
from typing import Any

from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_sha256,
    sha256_bytes,
)
from compiler.tensor_accelerator.qwen_chat import (
    EOS_TOKEN_IDS,
    EXPLICIT_VOCABULARY_SIZE,
    OFFICIAL_CHAT_TEMPLATE_SHA256,
    QwenChatTokenizer,
)
from compiler.tensor_accelerator.qwen_workload import load_shared_workload

from .qwen3 import (
    CORPUS_PATH,
    CORPUS_SHA256,
    CORPUS_SOURCE,
    LONG_PROMPT_TOKENS,
    Workload,
    load_corpus,
    natural_body,
)


REPO = Path(__file__).resolve().parents[2]
SCHEMA = "opentallas.qwen3.exact_8k_chat_construction.v1"
VERSION = "1.0.0"
ALGORITHM = "maximum_corpus_character_prefix_exact_rendered_tokens_v1"
SEPARATOR = "\n\n"
WORKLOAD_ID = "TA-QW-8K-1"
WORKLOAD_KIND = "long_natural_chat"
MAX_NEW_TOKENS = 256
QUERY_CASE_ID = "arithmetic"
EXPECTED_VISIBLE_ANSWER = "391"


class QwenExact8KError(ArtifactError):
    """Raised when the exact-8K construction or its sources differ."""


class AuthenticatedWorkloadTokenizer:
    """Expose the workload-builder surface over the authenticated tokenizer."""

    def __init__(self, chat: QwenChatTokenizer):
        self.chat = chat

    def apply_chat_template(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
        enable_thinking: bool,
    ) -> str:
        if tokenize is not False:
            raise QwenExact8KError(
                "workload construction requires rendered chat text"
            )
        return self.chat.render_chat(
            messages,
            add_generation_prompt=add_generation_prompt,
            enable_thinking=enable_thinking,
        )

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        if add_special_tokens is not False:
            raise QwenExact8KError(
                "Qwen workload construction adds no implicit tokens"
            )
        return self.chat.encode(text)

    def decode(self, ids: Sequence[int]) -> str:
        return self.chat.decode(list(ids), skip_special_tokens=False)


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenExact8KError(f"{label} identity differs")


def _source_path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise QwenExact8KError(f"{label} is not repository-relative")
    path = (REPO / value).resolve()
    try:
        path.relative_to(REPO.resolve())
    except ValueError as exc:
        raise QwenExact8KError(f"{label} escapes the repository") from exc
    return path


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise QwenExact8KError(f"cannot read construction source {path}: {exc}") from exc


def validate_construction(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the immutable recipe without loading the tokenizer or model."""

    construction = dict(value)
    exact_keys(
        construction,
        {
            "assembly",
            "canonical_semantics",
            "chat_template",
            "construction_id",
            "corpus",
            "generation",
            "schema",
            "version",
            "workload",
        },
        set(),
        "Qwen exact-8K construction",
    )
    _identity(construction, "construction_id", "Qwen exact-8K construction")
    if construction["schema"] != SCHEMA or construction["version"] != VERSION:
        raise QwenExact8KError("Qwen exact-8K construction version differs")

    workload = construction["workload"]
    corpus = construction["corpus"]
    semantics = construction["canonical_semantics"]
    template = construction["chat_template"]
    assembly = construction["assembly"]
    generation = construction["generation"]
    if not all(
        isinstance(item, dict)
        for item in (workload, corpus, semantics, template, assembly, generation)
    ):
        raise QwenExact8KError("Qwen exact-8K construction sections differ")

    if workload != {
        "kind": WORKLOAD_KIND,
        "max_new_tokens": MAX_NEW_TOKENS,
        "prompt_token_count": LONG_PROMPT_TOKENS,
        "workload_id": WORKLOAD_ID,
    }:
        raise QwenExact8KError("Qwen exact-8K workload boundary differs")
    if corpus != {
        "path": str(CORPUS_PATH.relative_to(REPO)),
        "sha256": CORPUS_SHA256,
        "source": CORPUS_SOURCE,
    }:
        raise QwenExact8KError("Qwen exact-8K corpus boundary differs")
    if template != {
        "add_generation_prompt": True,
        "sha256": OFFICIAL_CHAT_TEMPLATE_SHA256,
        "template_id": "qwen3_official_chat_template",
    }:
        raise QwenExact8KError("Qwen exact-8K chat-template boundary differs")
    if assembly != {
        "algorithm": ALGORITHM,
        "content_order": ["corpus_prefix", "separator", "canonical_query"],
        "message_role": "user",
        "separator": SEPARATOR,
    }:
        raise QwenExact8KError("Qwen exact-8K assembly boundary differs")
    if generation != {
        "eos_token_ids": list(EOS_TOKEN_IDS),
        "include_eos_in_output": True,
        "max_new_tokens": MAX_NEW_TOKENS,
        "selection": "greedy_lowest_token_id_argmax",
        "stop_rule": "first_official_eos_or_exact_cap",
        "vocabulary_size": EXPLICIT_VOCABULARY_SIZE,
    }:
        raise QwenExact8KError("Qwen exact-8K generation boundary differs")

    exact_keys(
        semantics,
        {
            "enable_thinking",
            "expected_visible_answer",
            "path",
            "query_case_id",
            "query_messages_sha256",
            "query_prompt_token_sha256",
            "source_sha256",
            "workload_id",
        },
        set(),
        "Qwen exact-8K canonical semantics",
    )
    for field in (
        "query_messages_sha256",
        "query_prompt_token_sha256",
        "source_sha256",
        "workload_id",
    ):
        require_sha256(semantics[field], f"canonical_semantics.{field}")
    if (
        semantics["query_case_id"] != QUERY_CASE_ID
        or semantics["enable_thinking"] is not False
        or semantics["expected_visible_answer"] != EXPECTED_VISIBLE_ANSWER
    ):
        raise QwenExact8KError("Qwen exact-8K canonical query differs")
    semantics_path = _source_path(semantics["path"], "canonical semantics path")
    if _file_sha256(semantics_path) != semantics["source_sha256"]:
        raise QwenExact8KError("Qwen exact-8K canonical semantics source differs")
    return construction


def load_construction(path: Path) -> dict[str, Any]:
    try:
        value = load_strict_json(Path(path))
    except ArtifactError as exc:
        raise QwenExact8KError(f"cannot load exact-8K construction: {exc}") from exc
    return validate_construction(value)


def canonical_query(construction: Mapping[str, Any]) -> dict[str, Any]:
    """Return the one ROM-authenticated query selected by the recipe."""

    checked = validate_construction(construction)
    semantics = checked["canonical_semantics"]
    source = load_shared_workload(_source_path(semantics["path"], "semantic source"))
    if source["workload_id"] != semantics["workload_id"]:
        raise QwenExact8KError("canonical semantic workload identity differs")
    matches = [
        item
        for item in source["natural_questions"]
        if item["id"] == semantics["query_case_id"]
    ]
    if len(matches) != 1:
        raise QwenExact8KError("canonical arithmetic query is absent or duplicated")
    query = matches[0]
    if (
        query["enable_thinking"] != semantics["enable_thinking"]
        or query["prompt"]["prompt_token_sha256"]
        != semantics["query_prompt_token_sha256"]
        or query["expected"]["generated_text_visible"]
        != semantics["expected_visible_answer"]
        or sha256_bytes(canonical_json_bytes(query["messages"]))
        != semantics["query_messages_sha256"]
    ):
        raise QwenExact8KError("canonical arithmetic query evidence differs")
    return query


def _render(
    tokenizer: Any,
    *,
    corpus_prefix: str,
    query_messages: Sequence[Mapping[str, Any]],
    enable_thinking: bool,
) -> tuple[str, tuple[int, ...], str]:
    if len(query_messages) != 1 or query_messages[0].get("role") != "user":
        raise QwenExact8KError("exact-8K query must be one canonical user message")
    query_text = query_messages[0].get("content")
    if not isinstance(query_text, str) or not query_text:
        raise QwenExact8KError("exact-8K canonical query text differs")
    content = corpus_prefix + SEPARATOR + query_text
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": content}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )
    if not isinstance(text, str):
        raise QwenExact8KError("official chat template did not return text")
    ids = tuple(tokenizer.encode(text, add_special_tokens=False))
    return text, ids, content


def _exact_prefix(
    tokenizer: Any,
    *,
    corpus: str,
    query: Mapping[str, Any],
) -> tuple[str, str, tuple[int, ...], str]:
    """Find the maximum character prefix yielding exactly 8,000 tokens."""

    messages = query["messages"]
    enable_thinking = query["enable_thinking"]

    def at(characters: int) -> tuple[str, tuple[int, ...], str]:
        return _render(
            tokenizer,
            corpus_prefix=corpus[:characters],
            query_messages=messages,
            enable_thinking=enable_thinking,
        )

    low, high = 0, len(corpus)
    while low < high:
        middle = (low + high + 1) // 2
        if len(at(middle)[1]) <= LONG_PROMPT_TOKENS:
            low = middle
        else:
            high = middle - 1

    # BPE length is almost monotonic over this ASCII corpus but the boundary
    # merge can occasionally keep the same length for several characters.
    # Walk to the greatest exact solution so the algorithm is unambiguous.
    cursor = low
    rendered, ids, content = at(cursor)
    if len(ids) > LONG_PROMPT_TOKENS:
        raise QwenExact8KError("exact-8K prefix search crossed its token target")
    while cursor < len(corpus):
        candidate = at(cursor + 1)
        if len(candidate[1]) > LONG_PROMPT_TOKENS:
            break
        cursor += 1
        rendered, ids, content = candidate
    if len(ids) != LONG_PROMPT_TOKENS:
        raise QwenExact8KError(
            f"cannot construct exactly {LONG_PROMPT_TOKENS} rendered tokens; "
            f"nearest prefix yields {len(ids)}"
        )
    return corpus[:cursor], rendered, ids, content


def build_exact_8k_workload(
    tokenizer: Any,
    construction: Mapping[str, Any],
    *,
    construction_path: Path,
) -> Workload:
    """Materialize the exact official-template prompt, with no oracle output."""

    checked = validate_construction(construction)
    query = canonical_query(checked)
    prefix, rendered, ids, content = _exact_prefix(
        tokenizer,
        corpus=natural_body(load_corpus()),
        query=query,
    )
    if len(ids) != LONG_PROMPT_TOKENS:
        raise QwenExact8KError("materialized exact-8K prompt length differs")
    resolved_construction = Path(construction_path).resolve()
    try:
        construction_relative = str(resolved_construction.relative_to(REPO))
    except ValueError as exc:
        raise QwenExact8KError("construction path is outside the repository") from exc
    return Workload(
        workload_id=WORKLOAD_ID,
        kind=WORKLOAD_KIND,
        description=(
            "Exactly 8,000 rendered official-chat tokens: a deterministic "
            "public-domain natural-text prefix followed by the canonical "
            "ROM-authenticated arithmetic question."
        ),
        rendered_text=rendered,
        token_ids=ids,
        max_new_tokens=MAX_NEW_TOKENS,
        metadata={
            "canonical_semantics": {
                "enable_thinking": query["enable_thinking"],
                "expected_visible_answer": EXPECTED_VISIBLE_ANSWER,
                "query_case_id": query["id"],
                "query_messages_sha256": checked["canonical_semantics"][
                    "query_messages_sha256"
                ],
                "query_prompt_token_sha256": query["prompt"][
                    "prompt_token_sha256"
                ],
                "source_path": checked["canonical_semantics"]["path"],
                "source_sha256": checked["canonical_semantics"]["source_sha256"],
                "workload_id": checked["canonical_semantics"]["workload_id"],
            },
            "construction": {
                "algorithm": ALGORITHM,
                "construction_id": checked["construction_id"],
                "source_path": construction_relative,
                "source_sha256": _file_sha256(resolved_construction),
            },
            "corpus": CORPUS_SOURCE,
            "corpus_prefix_character_count": len(prefix),
            "corpus_prefix_utf8_sha256": hashlib.sha256(
                prefix.encode("utf-8")
            ).hexdigest(),
            "corpus_sha256": CORPUS_SHA256,
            "message_content_utf8_sha256": hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest(),
            "official_chat_template_sha256": OFFICIAL_CHAT_TEMPLATE_SHA256,
            "oracle_output_tokens": "absent_generate_externally",
            "session_context_capacity": LONG_PROMPT_TOKENS + MAX_NEW_TOKENS,
        },
    )


def validate_materialized_workload(
    value: Mapping[str, Any],
    tokenizer: Any,
    construction: Mapping[str, Any],
    *,
    construction_path: Path,
) -> dict[str, Any]:
    """Reconstruct the prompt and require byte-for-byte workload equality."""

    expected = build_exact_8k_workload(
        tokenizer, construction, construction_path=construction_path
    ).to_dict()
    observed = dict(value)
    if observed != expected:
        raise QwenExact8KError("materialized exact-8K workload differs from its recipe")
    if observed.get("prompt_token_count") != LONG_PROMPT_TOKENS:
        raise QwenExact8KError("materialized exact-8K prompt is not 8,000 tokens")
    return observed


__all__ = [
    "ALGORITHM",
    "AuthenticatedWorkloadTokenizer",
    "EXPECTED_VISIBLE_ANSWER",
    "MAX_NEW_TOKENS",
    "QUERY_CASE_ID",
    "QwenExact8KError",
    "SCHEMA",
    "SEPARATOR",
    "VERSION",
    "WORKLOAD_ID",
    "WORKLOAD_KIND",
    "build_exact_8k_workload",
    "canonical_query",
    "load_construction",
    "validate_construction",
    "validate_materialized_workload",
]
