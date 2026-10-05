"""Pinned DeepSeek-V4 acceptance workloads.

This mirrors :mod:`compiler.workloads.qwen3`: each workload is defined once, as
content plus a digest, so the HBM deployment, the ROM deployment, the cycle
model and the independent oracle all consume exactly the same prompt token IDs.
A comparison between two backends only means something if the prompt is
byte-identical on both sides, so a workload is an artifact with an identity, not
a string literal in a runner.

Two things differ from the Qwen module, both forced by the model:

*There is no chat template.*  ``tokenizer_config.json`` carries no
``chat_template``, so prompts are rendered by the vendor's own
``encoding/encoding_dsv4.py``.  ``compiler.frontend.deepseek_v4_encoding``
reimplements that wire format and is checked against the release's four
fixtures, so either renderer may be supplied here and both are expected to
produce identical text.

*The mandatory long context is 200,000 natural prompt tokens*, an order of
magnitude past the Qwen contract.  Because a single machine may not be able to
execute that, the module also pins a graduated ladder - 1K, 8K, 32K, 128K, 200K
- so the program can report the largest context it *actually* ran rather than
only whether it reached the target.  The ladder is a reporting instrument; it
does not weaken the 200,000-token contract, which is defined here whether or not
it can be executed.

The long-context prompt is drawn from a public-domain source (Project Gutenberg
eBook 2701, *Moby Dick*) rather than synthesised, because the contract requires
*natural* prompt tokens; a repeated-token filler would exercise neither the
tokenizer nor the attention distribution realistically.  The repeated-special
stress workload exists separately and is explicitly not a substitute.

One definition, two releases
----------------------------
The content above is defined once and built against a release record from
:mod:`compiler.frontend.deepseek_v4_releases`, the same way the rest of the
front end is.  The record supplies the model id, the repository and the
revision the index names, and the ``max_position_embeddings`` the ladder is
confronted with; :data:`WORKLOAD_ID_PREFIXES` supplies the identity prefix -
``TA-DS`` for Flash, ``TA-DSP`` for Pro.

The two releases ship the same tokenizer: ``tokenizer.json`` and
``tokenizer_config.json`` have equal SHA-256 in both snapshots and are
byte-identical under ``cmp``.  A rung's prompt token IDs are therefore the same
integers for both releases.  Their workload *identities* are not, because the
digest covers the workload id, so a report cannot silently attribute one
release's run to the other's prompt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from compiler.frontend.deepseek_v4_releases import (
    FLASH,
    PRO,
    DeepSeekV4Release,
    DeepSeekV4ReleaseError,
    resolve_release,
)

# The corpus identity is pinned once for the whole program.  Importing it keeps
# a single SHA-256 for the one Project Gutenberg text both model families read,
# rather than a second copy that could drift out of step with the first.
# ``CORPUS_PATH`` is re-exported rather than used here, so a reader of this
# module reaches the corpus through the same name the Qwen module uses.
from compiler.workloads.qwen3 import (
    CORPUS_PATH as CORPUS_PATH,
    CORPUS_SHA256,
    CORPUS_SOURCE,
    exact_token_window,
    load_corpus,
    natural_body,
)

REPO = Path(__file__).resolve().parents[2]

#: The release every builder defaults to.  Naming a second release does not
#: move this one: the Flash workload documents are byte-identical before and
#: after the generalisation, and their digests are pinned as literals in
#: ``tests/compiler/test_deepseek_v4_workload_ladder.py``.
DEFAULT_MODEL_ID = FLASH.model_id

#: Flash's identity, still exported because callers import these three names.
#: They are read from the release record rather than restated here, so this
#: module cannot drift from the pin the front end enforces.
MODEL_ID = FLASH.model_id
OFFICIAL_REPOSITORY = FLASH.repository
OFFICIAL_REVISION = FLASH.revision

#: The workload-id prefix each release's identities carry.  This is a program
#: naming convention rather than a released fact, so it lives here and not in
#: the release record.  A release absent from this table has no workload
#: family, and :func:`workload_id_prefix` refuses to invent one for it.
WORKLOAD_ID_PREFIXES: Mapping[str, str] = MappingProxyType(
    {
        FLASH.model_id: "TA-DS",
        PRO.model_id: "TA-DSP",
    }
)

#: Exactly 200,000 natural prompt tokens is the mandatory DeepSeek context.
LONG_PROMPT_TOKENS = 200_000

#: The reporting ladder.  Every rung is a real, separately digested workload.
CONTEXT_LADDER: tuple[int, ...] = (1_000, 8_000, 32_000, 128_000, LONG_PROMPT_TOKENS)

#: The separate repeated-special-token stress workload.
STRESS_PROMPT_TOKENS = 8_000

#: ``<｜User｜>``.  Verified to be a single token before use.
STRESS_SPECIAL_TOKEN = "<｜User｜>"

DEFAULT_MAX_NEW_TOKENS = 256


@dataclass(frozen=True, slots=True)
class Workload:
    """One pinned workload: rendered text, token IDs and an identity digest.

    Intentionally the same shape and the same digest rule as
    :class:`compiler.workloads.qwen3.Workload`, so a report can carry both
    families without a per-family special case.  It is declared here rather
    than imported so that a future change to one model's workload identity
    cannot silently restate the other's.
    """

    workload_id: str
    kind: str
    description: str
    rendered_text: str
    token_ids: tuple[int, ...]
    max_new_tokens: int
    metadata: Mapping[str, Any] = dc_field(default_factory=dict)

    @property
    def digest(self) -> str:
        body = json.dumps(
            {
                "workload_id": self.workload_id,
                "kind": self.kind,
                "token_ids": list(self.token_ids),
                "max_new_tokens": self.max_new_tokens,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(body.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "kind": self.kind,
            "description": self.description,
            "digest": self.digest,
            "prompt_token_count": len(self.token_ids),
            "max_new_tokens": self.max_new_tokens,
            "rendered_text_sha256": hashlib.sha256(
                self.rendered_text.encode()
            ).hexdigest(),
            "token_ids": list(self.token_ids),
            "rendered_text": self.rendered_text,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Prompt content (pinned)
# ---------------------------------------------------------------------------
CHAT_QUESTION = (
    "A water tank holds 4,800 litres. Pump A alone fills it in 6 hours; pump B "
    "alone fills it in 10 hours; an open drain empties a full tank in 15 hours. "
    "At 08:00 pump A and the drain are both opened on an empty tank. At 10:00 "
    "pump B is also opened. At what clock time is the tank first full? Work "
    "through the rates step by step, then state the final time on its own line."
)
CHAT_CHECKS = {
    "must_contain_any": ["14:00", "14:0", "2:00 pm", "2 pm"],
    "reasoning_terms": ["rate", "litre", "hour", "pump", "drain"],
    "expected_answer": "14:00",
    "expected_answer_note": (
        "Pump A is 800 l/h, pump B 480 l/h, the drain -320 l/h. From 08:00 to "
        "10:00 the net rate is 480 l/h, so 960 l are in the tank at 10:00. "
        "After 10:00 the net rate is 800+480-320 = 960 l/h and the remaining "
        "3,840 l take 4 hours exactly, giving 14:00. The acceptance check is "
        "deliberately loose on the arithmetic and strict on the structure, "
        "because the gate is that the model produced coherent, on-topic, "
        "legitimately decoded text - not that it is a calculator. The strings "
        "checked for deliberately exclude the figures quoted in the prompt "
        "itself (6, 10 and 15 hours), so a check cannot pass by echoing the "
        "question."
    ),
}

#: The chat workload gets more room than the others because this model answers
#: with worked reasoning: at 256 tokens it is still mid-derivation, so the
#: final-answer line - the part a reader would check - never appears.
CHAT_MAX_NEW_TOKENS = 512

AGENT_SYSTEM = (
    "You are a careful command-line assistant operating on a frozen sandbox "
    "directory. Call exactly one tool per turn and wait for its result before "
    "continuing. When you have the answer, reply with a line beginning "
    "'ANSWER: ' and stop."
)
AGENT_TASK = (
    "The working directory contains a file named inventory.txt with one item "
    "per line in the form '<name>,<count>'. Report the total of all counts."
)
#: OpenAI-format tool schema; ``encode_messages`` renders it through the
#: model's own DSML tool block.
AGENT_TOOLS: tuple[dict[str, Any], ...] = (
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run one shell command in the sandbox directory and return its "
                "standard output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to run, for example 'cat inventory.txt'.",
                    }
                },
                "required": ["command"],
            },
        },
    },
)
AGENT_SANDBOX_FILES = {
    "inventory.txt": "bolts,24\nnuts,17\nwashers,58\nscrews,131\nrivets,9\n"
}
AGENT_EXPECTED_TOTAL = 24 + 17 + 58 + 131 + 9


def workload_id_prefix(release: str | DeepSeekV4Release = DEFAULT_MODEL_ID) -> str:
    """The workload-id prefix of one release, refusing an unknown one."""

    record = resolve_release(release)
    try:
        return WORKLOAD_ID_PREFIXES[record.model_id]
    except KeyError:
        raise DeepSeekV4ReleaseError(
            f"{record.model_id} has no pinned workload-id prefix; add one to "
            "WORKLOAD_ID_PREFIXES before naming its workloads, because a "
            "workload identity that collides with another release's would "
            "make two prompts share one digest"
        ) from None


def _ladder_id(tokens: int, prefix: str) -> str:
    if tokens % 1000:
        return f"{prefix}-CTX-{tokens}-1"
    return f"{prefix}-CTX-{tokens // 1000}K-1"


def build_chat_workload(
    encode_prompt: Callable[..., tuple[str, list[int]]],
    *,
    release: str | DeepSeekV4Release = DEFAULT_MODEL_ID,
    max_new_tokens: int = CHAT_MAX_NEW_TOKENS,
) -> Workload:
    """The pinned reasoning question, rendered through the official encoding."""
    text, ids = encode_prompt(
        [{"role": "user", "content": CHAT_QUESTION}], "chat"
    )
    return Workload(
        workload_id=f"{workload_id_prefix(release)}-CHAT-1",
        kind="chat",
        description=(
            "Pinned multi-rate reasoning question rendered with the official "
            "encoding_dsv4 wire format in chat (non-thinking) mode."
        ),
        rendered_text=text,
        token_ids=tuple(ids),
        max_new_tokens=max_new_tokens,
        metadata={"checks": CHAT_CHECKS, "thinking_mode": "chat"},
    )


def build_agent_workload(
    encode_prompt: Callable[..., tuple[str, list[int]]],
    *,
    release: str | DeepSeekV4Release = DEFAULT_MODEL_ID,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
) -> Workload:
    """A single-tool agent task carrying the model's own tool encoding."""
    text, ids = encode_prompt(
        [
            {
                "role": "system",
                "content": AGENT_SYSTEM,
                "tools": [dict(tool) for tool in AGENT_TOOLS],
            },
            {"role": "user", "content": AGENT_TASK},
        ],
        "chat",
    )
    return Workload(
        workload_id=f"{workload_id_prefix(release)}-AGENT-1",
        kind="agent",
        description=(
            "Single-tool shell agent task executed in a frozen sandbox, with "
            "the tool schema rendered through the official DSML tool block."
        ),
        rendered_text=text,
        token_ids=tuple(ids),
        max_new_tokens=max_new_tokens,
        metadata={
            "sandbox_files": AGENT_SANDBOX_FILES,
            "expected_total": AGENT_EXPECTED_TOTAL,
            "tools": [dict(tool) for tool in AGENT_TOOLS],
            "protocol": "one run_shell tool call per turn, ANSWER: terminates",
        },
    )


def build_context_workload(
    encode: Callable[[str], list[int]],
    target_tokens: int,
    body: str | None = None,
    *,
    release: str | DeepSeekV4Release = DEFAULT_MODEL_ID,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
) -> Workload:
    """One rung of the natural-prose context ladder, exact to the token."""
    if body is None:
        body = natural_body(load_corpus())
    window, ids = exact_token_window(encode, body, target_tokens)
    mandatory = target_tokens == LONG_PROMPT_TOKENS
    return Workload(
        workload_id=_ladder_id(target_tokens, workload_id_prefix(release)),
        kind="long_natural",
        description=(
            f"Exactly {target_tokens:,} natural prompt tokens of public-domain "
            "prose"
            + (
                ", the mandatory DeepSeek context."
                if mandatory
                else ", a rung of the reporting ladder below the mandatory "
                f"{LONG_PROMPT_TOKENS:,}-token context."
            )
        ),
        rendered_text=window,
        token_ids=ids,
        max_new_tokens=max_new_tokens,
        metadata={
            "corpus": CORPUS_SOURCE,
            "corpus_sha256": CORPUS_SHA256,
            "mandatory_contract": mandatory,
            "ladder_position": CONTEXT_LADDER.index(target_tokens)
            if target_tokens in CONTEXT_LADDER
            else None,
        },
    )


def build_stress_workload(
    encode: Callable[[str], list[int]],
    decode: Callable[[list[int]], str],
    *,
    release: str | DeepSeekV4Release = DEFAULT_MODEL_ID,
    max_new_tokens: int = 32,
) -> Workload:
    """A legal but pathological repeated-special-token stream."""
    special = encode(STRESS_SPECIAL_TOKEN)
    if len(special) != 1:
        raise ValueError(
            f"expected {STRESS_SPECIAL_TOKEN!r} to be a single special token, "
            f"got {special}"
        )
    ids = tuple(special * STRESS_PROMPT_TOKENS)
    return Workload(
        workload_id=f"{workload_id_prefix(release)}-STRESS-1",
        kind="repeated_special",
        description=(
            "Repeated-special-token stress workload. Separate from the natural "
            f"{LONG_PROMPT_TOKENS:,}-token contract and never a substitute for "
            "it."
        ),
        rendered_text=decode(list(ids)),
        token_ids=ids,
        max_new_tokens=max_new_tokens,
        metadata={"special_token_id": special[0], "special_token": STRESS_SPECIAL_TOKEN},
    )


def build_workloads(
    tokenizer,
    *,
    release: str | DeepSeekV4Release = DEFAULT_MODEL_ID,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    ladder: tuple[int, ...] = CONTEXT_LADDER,
) -> dict[str, Workload]:
    """Build every pinned DeepSeek workload against a loaded tokenizer.

    ``tokenizer`` must expose ``encode``/``decode`` and an ``encode_prompt``
    that renders through the official ``encoding_dsv4`` wire format -
    :class:`compiler.frontend.deepseek_v4_tokenizer.VerifiedDeepSeekV4Tokenizer`
    satisfies this.  It must be the tokenizer ``release`` names; nothing here
    can tell one tokenizer from another, so the caller binds that and the
    index records the digest it used.

    Every rung is confronted with the release's own
    ``max_position_embeddings``: a ladder that reaches past the context the
    model was released with would be asking for prompts the model cannot hold.
    """

    record = resolve_release(release)
    context_bound = int(record.scalar("max_position_embeddings"))
    beyond = [rung for rung in ladder if rung > context_bound]
    if beyond:
        raise ValueError(
            f"{record.model_id} pins max_position_embeddings="
            f"{context_bound:,}; ladder rungs {beyond} exceed it"
        )

    def encode(text: str) -> list[int]:
        return tokenizer.encode(text, enforce_max_length=False)

    def decode(ids: list[int]) -> str:
        return tokenizer.decode(ids)

    def encode_prompt(messages, thinking_mode):  # noqa: ANN001
        return tokenizer.encode_prompt(messages, thinking_mode)

    workloads: list[Workload] = [
        build_chat_workload(encode_prompt, release=record),
        build_agent_workload(
            encode_prompt, release=record, max_new_tokens=max_new_tokens
        ),
        build_stress_workload(encode, decode, release=record),
    ]
    body = natural_body(load_corpus())
    for target in ladder:
        workloads.append(
            build_context_workload(
                encode,
                target,
                body,
                release=record,
                max_new_tokens=max_new_tokens,
            )
        )
    return {workload.workload_id: workload for workload in workloads}


def index_document(
    workloads: Mapping[str, Workload],
    *,
    release: str | DeepSeekV4Release = DEFAULT_MODEL_ID,
    **extra: Any,
) -> dict[str, Any]:
    """The ``index.json`` shape the oracle and the deployments read."""
    record = resolve_release(release)
    document = {
        "schema": "opentallas.workload_index.v1",
        "model_id": record.model_id,
        "source": {
            "repository": record.repository,
            "revision": record.revision,
        },
        "mandatory_context_tokens": LONG_PROMPT_TOKENS,
        "context_ladder": list(CONTEXT_LADDER),
        "workloads": {
            workload_id: {
                "path": f"{workload_id}.json",
                "kind": workload.kind,
                "digest": workload.digest,
                "prompt_token_count": len(workload.token_ids),
                "max_new_tokens": workload.max_new_tokens,
            }
            for workload_id, workload in sorted(workloads.items())
        },
    }
    document.update(extra)
    return document
