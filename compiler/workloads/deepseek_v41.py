"""Pinned DeepSeek-V4.1-Flash acceptance workloads.

This is the V4.1 sibling of :mod:`compiler.workloads.deepseek_v4`, and it keeps
that module's whole shape: each workload is defined once, as content plus a
digest, so the ROM wafer deployment, the ROM array deployment, the HBM
comparator, the cycle model and the independent oracle all consume exactly the
same prompt token IDs.  A comparison between two backends only means something
if the prompt is byte-identical on both sides, so a workload is an artifact with
an identity, not a string literal in a runner.  :class:`Workload` is therefore
the same dataclass with the same digest rule, declared here rather than
imported so that a future change to one model's workload identity cannot
silently restate the other's.

The four workload families are
``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`` section 10's, one each:

* 10.1, short ordinary generation: :data:`PREFIX_PROMPT_TOKENS` prompt tokens
  and :data:`PREFIX_MAX_NEW_TOKENS` greedy tokens, ``TA-DS41-CHAT-1-P32``.
* 10.2, the reduced whole-run ladder: ``TA-DS41-EOS-1``, the G1 workload.
* 10.3, the exact 200,000-token acceptance: ``TA-DS41-CTX-200K-1``, with the
  1K/8K/32K/128K reporting rungs below it.
* 10.4, agentic context: ``TA-DS41-AGENT-1``, a multi-turn tool-call transcript.

Five things differ from the V4 module, all of them forced
--------------------------------------------------------
*The acceptance workload is the prefix.*  In the V4 program the prefixes were a
debugging instrument kept deliberately outside the acceptance set
(``tools/build_deepseek_v4_prefix_workloads.py``).  Plan section 10.1 makes
``TA-DS41-CHAT-1-P32`` V4.1's *first executable claim*, the one that gates
everything after it, so the prefix is defined here, in the acceptance module,
and ``TA-DS41-CHAT-1`` is defined with it as the parent it is truncated from.

*There is no stress rung.*  Section 10 does not ask for one, so none is
invented; ``TA-DS-STRESS-1`` remains V4's.

*The agent workload is multi-turn.*  Section 10.4 asks for a tool-call
transcript, not a tool-call opportunity, so the pinned messages run
system-with-tools, user, assistant-with-a-tool-call, tool-result, and the prompt
ends on the assistant header that follows the result.

*The renderer is the released ``encoding/encoding.py``.*  V4.1's DSML grammar is
not V4's - the tag names changed, reasoning effort became numeric, and
``<｜System｜>`` became a live mid-conversation token - and this repository has
no reimplementation of it yet.  Every builder here therefore takes its renderer
as a callable, exactly as the V4 builders do, and the tool that materialises
the documents supplies the vendor module and records which renderer produced
each prompt.  When a V4.1 reimplementation lands, it is supplied the same way
and required to render byte-identically.

*Identity comes from the committed analytical record.*  Section 13 gives the
release record to WP-B, which needs a complete 510 GB download; until it lands
there is no ``V41_FLASH`` to read a model id, a revision or a context bound
from.  :func:`resolve_identity` reads them from the two committed V4.1
documents instead - ``configs/models/candidates/deepseek-v4.1-flash.json`` and
``data/inventory/deepseek-v4.1-flash.json`` - requires the two to agree, and
cross-checks a release record against them as soon as one exists.  Nothing here
restates a model number that either document already carries.

One prompt, two models
----------------------
The chat question, the agent system prompt, the agent task, the tool schema and
the sandbox are *imported* from the V4 module, and the G1 question from the Qwen
module, rather than copied.  That is deliberate and it is the same reasoning the
V4 module gives for importing the corpus: a figure this program compares across
two models has to be one prompt, defined once.  The workload *identities* are
distinct regardless, because the digest covers the workload id, so a report
cannot silently attribute a V4.1 run to V4's prompt.

It goes further than intended for the plain chat turn.  V4.1's ``encoding.py``
renders a single user message in chat mode byte-identically to V4's
``encoding_dsv4.py``, and V4.1's tokenizer gives the released base vocabulary
and merges of V4's unchanged, so ``TA-DS41-CHAT-1`` and ``TA-DS41-CTX-*-1``
carry *the same prompt token integers* as their ``TA-DS-`` counterparts.  That
makes the two models' runs directly comparable and it is pinned as such in
``tests/compiler/test_deepseek_v41_workload_ladder.py``.  It emphatically does
not make V4's gold V4.1's gold: the same prompt on different weights has a
different answer, and the V4.1 oracle is WP-H's to produce.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

# The corpus identity is pinned once for the whole program; importing it keeps a
# single SHA-256 for the one Project Gutenberg text every model family reads.
# ``CORPUS_PATH`` is re-exported rather than used here, so a reader of this
# module reaches the corpus through the same name the other two use.
from compiler.workloads.qwen3 import (
    CORPUS_PATH as CORPUS_PATH,
    CORPUS_SHA256,
    CORPUS_SOURCE,
    EOS_QUESTION,
    exact_token_window,
    load_corpus,
    natural_body,
)

# The prompt content this program compares across DeepSeek releases, defined
# once in the V4 module and read here rather than restated.
from compiler.workloads.deepseek_v4 import (
    AGENT_EXPECTED_TOTAL,
    AGENT_SANDBOX_FILES,
    AGENT_SYSTEM,
    AGENT_TASK,
    AGENT_TOOLS,
    CHAT_CHECKS,
    CHAT_MAX_NEW_TOKENS,
    CHAT_QUESTION,
)

REPO = Path(__file__).resolve().parents[2]

#: The model id every V4.1 artifact in this repository is filed under: the
#: basename of the committed profile and of the committed inventory, and the
#: name ``tools/profile_hf.py --model`` already takes.
MODEL_ID = "deepseek-v4.1-flash"

#: The workload-id prefix of this release's identities.  A program naming
#: convention rather than a released fact, so it lives here: ``TA-DS`` is V4
#: Flash, ``TA-DSP`` V4 Pro, ``TA-DS41`` this release.
WORKLOAD_ID_PREFIX = "TA-DS41"

#: The two committed V4.1 documents that carry its identity.
PROFILE_PATH = REPO / "configs" / "models" / "candidates" / f"{MODEL_ID}.json"
INVENTORY_PATH = REPO / "data" / "inventory" / f"{MODEL_ID}.json"

#: Exactly 200,000 natural prompt tokens is the mandatory DeepSeek context,
#: unchanged from V4 and restated by plan section 10.3.
LONG_PROMPT_TOKENS = 200_000

#: The reporting ladder.  Every rung is a real, separately digested workload,
#: so the program can report the largest context it *actually* ran rather than
#: only whether it reached the target.  The ladder does not weaken the
#: 200,000-token contract, which is defined here whether or not it can run.
CONTEXT_LADDER: tuple[int, ...] = (1_000, 8_000, 32_000, 128_000, LONG_PROMPT_TOKENS)

#: Plan section 10.1: "a 32-token prefix, greedy decode of 4 tokens on each of
#: the three targets, compared to the external oracle token for token".  Both
#: numbers are that sentence and nothing else; neither is a model dimension.
PREFIX_PROMPT_TOKENS = 32
PREFIX_MAX_NEW_TOKENS = 4

#: A prefix is not a chat turn - it stops mid-sentence and carries no assistant
#: marker - so it does not claim to be one.
PREFIX_KIND = "chat_prefix"

#: The truncation rule, stated once and recorded in every prefix's metadata,
#: because it is what an accelerator runner does when it shortens a run.
PREFIX_RULE = "token_ids[:prefix_tokens]"

DEFAULT_MAX_NEW_TOKENS = 256

#: The G1 horizon, matching ``compiler.workloads.qwen3``: sixteen gives a short
#: run somewhere to disagree after the first token, and a run that reaches the
#: cap has not produced the terminating EOS the gate is about.
EOS_MAX_NEW_TOKENS = 16

#: Both ordinary generation modes V4.1 renders.  Every workload here is pinned
#: in chat (non-thinking) mode: plan section 10 asks for ordinary generation and
#: an agentic transcript, and thinking mode would put the numeric reasoning
#: effort prefix of ``encoding.py`` into the prompt, which is a separate
#: contract nothing in section 10 gates.
THINKING_MODE = "chat"


class DeepSeekV41WorkloadError(RuntimeError):
    """Raised when V4.1's committed identity cannot be resolved or is inconsistent."""


@dataclass(frozen=True, slots=True)
class DeepSeekV41Identity:
    """Where this release's model id, revision and context bound came from."""

    model_id: str
    repository: str
    revision: str
    config_sha256: str
    context_bound: int
    authority: tuple[str, ...]
    release_record: str | None


def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    if not path.exists():
        raise DeepSeekV41WorkloadError(
            f"{label} missing at {path}; it is one of the two committed "
            "documents that carry V4.1's identity"
        )
    return json.loads(path.read_text())


def _release_record_crosscheck(identity: Mapping[str, Any]) -> str | None:
    """Confront a V4.1 release record with the committed documents, if one exists.

    WP-B owns ``V41_FLASH``.  This module neither waits for it nor duplicates
    it: as soon as a record under :data:`MODEL_ID` resolves, every field it
    carries that the committed documents also carry is required to agree, so the
    day the record lands is the day a disagreement becomes a test failure
    instead of two independently plausible provenances.  A record that does not
    resolve, or that does not carry a field, leaves the committed documents as
    the sole authority; it never overrides one.
    """

    try:
        from compiler.frontend.deepseek_v4_releases import resolve_release
    except ImportError:  # pragma: no cover - the front end is always present
        return None
    try:
        record = resolve_release(MODEL_ID)
    except Exception:
        return None
    for attribute, key in (
        ("repository", "repository"),
        ("revision", "revision"),
        ("config_sha256", "config_sha256"),
    ):
        observed = getattr(record, attribute, None)
        if observed is not None and observed != identity[key]:
            raise DeepSeekV41WorkloadError(
                f"release record {record.model_id} names {attribute} "
                f"{observed!r}, the committed documents name {identity[key]!r}; "
                "a workload built under one provenance and reported under the "
                "other is a workload nobody can reproduce"
            )
    try:
        bound = int(record.scalar("max_position_embeddings"))
    except Exception:
        bound = None
    if bound is not None and bound != identity["context_bound"]:
        raise DeepSeekV41WorkloadError(
            f"release record {record.model_id} pins "
            f"max_position_embeddings={bound:,}, the committed profile pins a "
            f"context bound of {identity['context_bound']:,}; the ladder is "
            "confronted with one of them and they disagree"
        )
    return record.model_id


def resolve_identity(
    *,
    profile_path: Path = PROFILE_PATH,
    inventory_path: Path = INVENTORY_PATH,
) -> DeepSeekV41Identity:
    """V4.1's identity, read from the committed documents and cross-checked.

    The profile is the analytical authority on the context bound; the inventory
    is the authority on the released ``config.json`` digest.  Both name the
    repository and the revision, and they are required to agree, so neither is
    a single unchecked source.
    """

    profile = _read_json(profile_path, "the committed V4.1 profile")
    inventory = _read_json(inventory_path, "the committed V4.1 inventory")
    identity = {
        "repository": profile["source_repo"],
        "revision": profile["source_revision"],
        "config_sha256": inventory["config_sha256"],
        "context_bound": int(profile["max_context_tokens"]),
    }
    for key, inventory_key in (("repository", "repo"), ("revision", "revision")):
        if inventory[inventory_key] != identity[key]:
            raise DeepSeekV41WorkloadError(
                f"{profile_path.name} names {key} {identity[key]!r} but "
                f"{inventory_path.name} names {inventory[inventory_key]!r}; the "
                "two committed documents disagree about which checkpoint this is"
            )
    return DeepSeekV41Identity(
        model_id=MODEL_ID,
        repository=identity["repository"],
        revision=identity["revision"],
        config_sha256=identity["config_sha256"],
        context_bound=identity["context_bound"],
        authority=(
            str(profile_path.relative_to(REPO)),
            str(inventory_path.relative_to(REPO)),
        ),
        release_record=_release_record_crosscheck(identity),
    )


@dataclass(frozen=True, slots=True)
class Workload:
    """One pinned workload: rendered text, token IDs and an identity digest.

    Intentionally the same shape and the same digest rule as
    :class:`compiler.workloads.deepseek_v4.Workload` and
    :class:`compiler.workloads.qwen3.Workload`, so a report can carry all three
    families without a per-family special case.
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

#: The one sandbox file the agent task reads, and the shell command that reads
#: it.  Derived from :data:`AGENT_SANDBOX_FILES` so the transcript cannot name a
#: file the sandbox does not contain.
if len(AGENT_SANDBOX_FILES) != 1:
    raise DeepSeekV41WorkloadError(
        "the pinned agent sandbox is expected to hold exactly one file; the "
        f"transcript's tool call reads it by name, and it holds "
        f"{sorted(AGENT_SANDBOX_FILES)}"
    )
AGENT_SANDBOX_FILE = next(iter(AGENT_SANDBOX_FILES))
AGENT_SHELL_COMMAND = f"cat {AGENT_SANDBOX_FILE}"

#: The name of the one tool the schema offers, read from the schema.
AGENT_TOOL_NAME = AGENT_TOOLS[0]["function"]["name"]

#: The tool-call id the transcript uses.  It is an identifier in the wire
#: format, not a model fact; ``encoding.py`` renders the result block by call
#: order and does not render the id itself.
AGENT_TOOL_CALL_ID = "call_1"

#: Plan section 10.4's transcript, as OpenAI-format messages.  The released
#: ``encoding.py`` has no standalone ``tool`` role - ``merge_tool_messages``
#: folds a tool result into the following user turn as a ``<tool_result>``
#: block - so the transcript is written in the portable form and the released
#: module does the folding, rather than this module anticipating its output.
AGENT_MESSAGES: tuple[Mapping[str, Any], ...] = (
    MappingProxyType(
        {
            "role": "system",
            "content": AGENT_SYSTEM,
            "tools": [dict(tool) for tool in AGENT_TOOLS],
        }
    ),
    MappingProxyType({"role": "user", "content": AGENT_TASK}),
    MappingProxyType(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": AGENT_TOOL_CALL_ID,
                    "type": "function",
                    "function": {
                        "name": AGENT_TOOL_NAME,
                        "arguments": {"command": AGENT_SHELL_COMMAND},
                    },
                }
            ],
        }
    ),
    MappingProxyType(
        {
            "role": "tool",
            "tool_call_id": AGENT_TOOL_CALL_ID,
            "content": AGENT_SANDBOX_FILES[AGENT_SANDBOX_FILE],
        }
    ),
)

#: What the transcript is for, and what it is not for.  Plan section 10.4 is
#: explicit that prefill replay is out of scope, and a workload that claimed
#: otherwise would be read as gating something it cannot reach.
AGENT_SCOPE = {
    "exercises": [
        "the V4.1 DSML calls block, invoke and parameter tag names",
        "the <tool_result> user-turn fold of merge_tool_messages",
        "a decode that reads a window the encoder wrote",
    ],
    "does_not_exercise": [
        "SWA Bounded Replay prefill replay itself",
        "thinking mode and the numeric reasoning-effort prefix",
        "multi-tool or namespaced tool calls",
    ],
    "protocol": (
        f"one {AGENT_TOOL_NAME} call per turn, ANSWER: terminates; the prompt "
        "ends on the assistant header that follows the tool result"
    ),
}

#: What the G1 gold must satisfy.  These are requirements on the oracle WP-H
#: produces, not properties this module established: nothing here has executed
#: the reduced V4.1 model, and whether this prompt's greedy gold terminates in
#: the released EOS is exactly what that oracle decides.  The question itself is
#: the program's existing G1 question, imported from the Qwen module so the two
#: ladders ask one thing.
EOS_CHECKS = (
    "the greedy gold terminates in the released eos_token_id",
    "generation stops before EOS_MAX_NEW_TOKENS; a cap stop is a failed gold",
    "the reduced model keeps 40 layers and the CSA2 mode sequence exactly",
)
EOS_GOLD_STATUS = (
    "unverified: no reduced V4.1 model and no oracle exist yet. WP-H's "
    "results/abi3/deepseek_v41_reduced_reference_oracle.json decides whether "
    "this prompt satisfies EOS_CHECKS; if it does not, the prompt moves and "
    "this workload's digest moves with it."
)


def _ladder_id(tokens: int, prefix: str = WORKLOAD_ID_PREFIX) -> str:
    if tokens % 1000:
        return f"{prefix}-CTX-{tokens}-1"
    return f"{prefix}-CTX-{tokens // 1000}K-1"


def build_chat_workload(
    encode_prompt: Callable[..., tuple[str, list[int]]],
    *,
    max_new_tokens: int = CHAT_MAX_NEW_TOKENS,
) -> Workload:
    """The pinned reasoning question, rendered through the released encoding.

    Defined for its own sake and as the parent
    :func:`build_chat_prefix_workload` truncates: plan section 10.1's gate is
    the prefix, and a prefix is only a gate if the thing it is a prefix *of* has
    an identity too.
    """

    text, ids = encode_prompt(
        [{"role": "user", "content": CHAT_QUESTION}], THINKING_MODE
    )
    return Workload(
        workload_id=f"{WORKLOAD_ID_PREFIX}-CHAT-1",
        kind="chat",
        description=(
            "Pinned multi-rate reasoning question rendered with the released "
            "DeepSeek-V4.1 encoding.py wire format in chat (non-thinking) mode."
        ),
        rendered_text=text,
        token_ids=tuple(ids),
        max_new_tokens=max_new_tokens,
        metadata={"checks": CHAT_CHECKS, "thinking_mode": THINKING_MODE},
    )


def build_chat_prefix_workload(
    parent: Workload,
    decode: Callable[[list[int]], str],
    *,
    prefix_tokens: int = PREFIX_PROMPT_TOKENS,
    max_new_tokens: int = PREFIX_MAX_NEW_TOKENS,
) -> Workload:
    """Plan section 10.1's first executable claim: the parent's first *n* tokens.

    No prompt is invented.  The token IDs are ``parent``'s truncated, which is
    precisely what an accelerator runner does when it shortens a run, so both
    sides answer the same question token for token.  The decoded text is
    required to be a genuine prefix of the parent's rendered text, which is what
    rules out a truncation that split a multi-byte character.
    """

    if not 0 < prefix_tokens <= len(parent.token_ids):
        raise DeepSeekV41WorkloadError(
            f"cannot take a {prefix_tokens}-token prefix of "
            f"{parent.workload_id}, which has {len(parent.token_ids)} tokens"
        )
    token_ids = tuple(parent.token_ids[:prefix_tokens])
    rendered_text = decode(list(token_ids))
    if not parent.rendered_text.startswith(rendered_text):
        raise DeepSeekV41WorkloadError(
            f"the first {prefix_tokens} tokens of {parent.workload_id} decode "
            "to text that is not a prefix of its rendered text"
        )
    return Workload(
        workload_id=f"{parent.workload_id}-P{prefix_tokens}",
        kind=PREFIX_KIND,
        description=(
            f"The first {prefix_tokens} prompt tokens of {parent.workload_id}, "
            f"with {max_new_tokens} greedy tokens: plan section 10.1's short "
            "ordinary generation, the first executable claim of the V4.1 "
            "program."
        ),
        rendered_text=rendered_text,
        token_ids=token_ids,
        max_new_tokens=max_new_tokens,
        metadata={
            "derived_from": {
                "workload_id": parent.workload_id,
                "digest": parent.digest,
                "prompt_token_count": len(parent.token_ids),
                "rule": PREFIX_RULE,
                "prefix_tokens": prefix_tokens,
            },
            "thinking_mode": THINKING_MODE,
            "plan_section": "10.1",
        },
    )


def build_agent_workload(
    encode_prompt: Callable[..., tuple[str, list[int]]],
    *,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
) -> Workload:
    """Plan section 10.4's multi-turn tool-call transcript."""

    text, ids = encode_prompt(
        [dict(message) for message in AGENT_MESSAGES], THINKING_MODE
    )
    return Workload(
        workload_id=f"{WORKLOAD_ID_PREFIX}-AGENT-1",
        kind="agent",
        description=(
            "Multi-turn single-tool shell agent transcript in the released "
            "DeepSeek-V4.1 encoding.py grammar: the tool schema in the system "
            "turn, one DSML tool call, and its result folded into the "
            "following user turn."
        ),
        rendered_text=text,
        token_ids=tuple(ids),
        max_new_tokens=max_new_tokens,
        metadata={
            "sandbox_files": dict(AGENT_SANDBOX_FILES),
            "expected_total": AGENT_EXPECTED_TOTAL,
            "tools": [dict(tool) for tool in AGENT_TOOLS],
            "turns": len(AGENT_MESSAGES),
            "scope": AGENT_SCOPE,
            "thinking_mode": THINKING_MODE,
            "plan_section": "10.4",
        },
    )


def build_eos_workload(
    encode_prompt: Callable[..., tuple[str, list[int]]],
    *,
    max_new_tokens: int = EOS_MAX_NEW_TOKENS,
) -> Workload:
    """Plan section 10.2's reduced whole-run ladder workload."""

    text, ids = encode_prompt(
        [{"role": "user", "content": EOS_QUESTION}], THINKING_MODE
    )
    return Workload(
        workload_id=f"{WORKLOAD_ID_PREFIX}-EOS-1",
        kind="chat",
        description=(
            "G1 governed workload of plan section 10.2: the short chat prompt "
            "the reduced-dimension V4.1 ladder runs whole, at 40 layers with "
            "the CSA2 mode sequence kept exactly."
        ),
        rendered_text=text,
        token_ids=tuple(ids),
        max_new_tokens=max_new_tokens,
        metadata={
            "checks": list(EOS_CHECKS),
            "gold_status": EOS_GOLD_STATUS,
            "gate": "G1",
            "thinking_mode": THINKING_MODE,
            "plan_section": "10.2",
            "reduced_model_contract": (
                "hidden, expert width and expert count reduced; 40 layers and "
                "the CSA2 mode sequence kept exactly, because the mode "
                "sequence is what is under test"
            ),
        },
    )


def build_context_workload(
    encode: Callable[[str], list[int]],
    target_tokens: int,
    body: str | None = None,
    *,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
) -> Workload:
    """One rung of the natural-prose context ladder, exact to the token."""

    if body is None:
        body = natural_body(load_corpus())
    window, ids = exact_token_window(encode, body, target_tokens)
    mandatory = target_tokens == LONG_PROMPT_TOKENS
    return Workload(
        workload_id=_ladder_id(target_tokens),
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
            **(
                {
                    "plan_section": "10.3",
                    # Deliberately a reference and not a copy.  Plan section
                    # 10.3's acceptance arithmetic - the per-position global KV
                    # bytes, the owner layers and the index scan widths - lives
                    # in the profile and the released config, and a second copy
                    # of it inside a workload document is the mirrored-constant
                    # defect this program keeps paying for.  The checker reads
                    # the authorities; the workload names them.
                    "counter_authority": {
                        "profile": str(PROFILE_PATH.relative_to(REPO)),
                        "profile_keys": [
                            "metadata.global_kv_bytes_per_token",
                            "metadata.kv_cache_policy",
                            "metadata.index_topk",
                        ],
                        "released_config_keys": [
                            "text_config.kv_source_layer_ids",
                            "text_config.index_source_layer_ids",
                        ],
                        "checker_shape": (
                            "tools/check_deepseek_v4_200k_accelerator_"
                            "acceptance.py"
                        ),
                    },
                }
                if mandatory
                else {}
            ),
        },
    )


def build_workloads(
    tokenizer,
    encode_prompt: Callable[..., tuple[str, list[int]]],
    *,
    identity: DeepSeekV41Identity | None = None,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    ladder: Sequence[int] = CONTEXT_LADDER,
    prefix_tokens: int = PREFIX_PROMPT_TOKENS,
) -> dict[str, Workload]:
    """Build every pinned V4.1 workload against a loaded tokenizer and renderer.

    ``tokenizer`` must expose ``encode``/``decode``;
    :class:`compiler.frontend.deepseek_v41_tokenizer.VerifiedDeepSeekV41Tokenizer`
    satisfies this.  ``encode_prompt`` takes the message list and returns
    ``(rendered_text, token_ids)``.  It is a separate argument rather than a
    method on the tokenizer because V4.1's renderer is the released
    ``encoding.py`` and the tokenizer boundary deliberately does not carry
    remote Python; the caller binds the two and the index records which
    renderer it bound.

    Every rung is confronted with the release's own context bound: a ladder
    that reached past the context the model was released with would be asking
    for prompts the model cannot hold.
    """

    record = identity if identity is not None else resolve_identity()
    beyond = [rung for rung in ladder if rung > record.context_bound]
    if beyond:
        raise DeepSeekV41WorkloadError(
            f"{record.model_id} pins a context bound of "
            f"{record.context_bound:,} tokens; ladder rungs {beyond} exceed it"
        )

    def encode(text: str) -> list[int]:
        return tokenizer.encode(text, enforce_max_length=False)

    def decode(ids: list[int]) -> str:
        return tokenizer.decode(ids)

    chat = build_chat_workload(encode_prompt)
    workloads: list[Workload] = [
        chat,
        build_chat_prefix_workload(chat, decode, prefix_tokens=prefix_tokens),
        build_agent_workload(encode_prompt, max_new_tokens=max_new_tokens),
        build_eos_workload(encode_prompt),
    ]
    body = natural_body(load_corpus())
    for target in ladder:
        workloads.append(
            build_context_workload(
                encode, target, body, max_new_tokens=max_new_tokens
            )
        )
    return {workload.workload_id: workload for workload in workloads}


def index_document(
    workloads: Mapping[str, Workload],
    *,
    identity: DeepSeekV41Identity | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """The ``index.json`` shape the oracle and the deployments read.

    Deliberately ``opentallas.workload_index.v1``, the same schema the V4 and
    Qwen indexes carry, so a reader that already handles one handles this.
    """

    record = identity if identity is not None else resolve_identity()
    document = {
        "schema": "opentallas.workload_index.v1",
        "model_id": record.model_id,
        "source": {
            "repository": record.repository,
            "revision": record.revision,
            "config_sha256": record.config_sha256,
            "identity_authority": list(record.authority),
            "release_record": record.release_record,
        },
        "mandatory_context_tokens": LONG_PROMPT_TOKENS,
        "context_ladder": list(CONTEXT_LADDER),
        "context_bound": record.context_bound,
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
