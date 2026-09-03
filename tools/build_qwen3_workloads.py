#!/usr/bin/env python3
"""Materialise the pinned Qwen3-8B acceptance workloads.

Writes one canonical JSON per workload plus an index, so that every backend,
the cycle model and the independent oracle consume byte-identical prompts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.qwen3.constants import SESSION_CONTEXT_CAPACITY  # noqa: E402
from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    QwenChatTokenizer,
    SOURCE_FILES,
)
from compiler.tensor_accelerator.qwen_workload import (  # noqa: E402
    load_shared_workload,
)
from compiler.workloads.qwen3 import (  # noqa: E402
    AGENT_SANDBOX_FILES,
    AGENT_SYSTEM,
    AGENT_TASK,
    CHAT_CHECKS,
    CHAT_QUESTION,
    Workload,
    build_workloads,
)
from compiler.workloads.qwen3_exact_8k import (  # noqa: E402
    AuthenticatedWorkloadTokenizer,
    build_exact_8k_workload,
    load_construction,
)
from runtime.abi3.capability import canonical_json  # noqa: E402

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
DEFAULT_EXACT_8K_CONSTRUCTION = (
    REPO / "configs/abi3/workloads/qwen3_exact_8k_chat_v1.json"
)


#: ``session_context_capacity`` from the pinned Qwen3-8B kernel IR.  Every
#: workload this module authors must satisfy
#: ``prompt_token_count + max_new_tokens <= SESSION_CONTEXT_CAPACITY``.
#: OI-34 records the retired failure mode: the mandatory 8,000-token workload
#: asked for 256 decode tokens against an 8,192-position context, so the last
#: 64 decode steps had nowhere to write.  The shared 8,256-position product
#: bound and the check below keep the frozen workload satisfiable.


def _check_context_budget(workload: "Workload") -> None:
    """Refuse a workload whose decode cannot fit its own declared context."""
    total = len(workload.token_ids) + workload.max_new_tokens
    if total > SESSION_CONTEXT_CAPACITY:
        raise ValueError(
            f"{workload.workload_id}: prompt {len(workload.token_ids)} + "
            f"max_new {workload.max_new_tokens} = {total} exceeds the "
            f"{SESSION_CONTEXT_CAPACITY}-position session context (OI-34)"
        )


def _validated_body(workload: "Workload") -> dict:
    """Return one publishable workload only after enforcing its full budget."""

    _check_context_budget(workload)
    body = workload.to_dict()
    body["metadata"] = dict(body["metadata"])
    body["metadata"]["session_context_capacity"] = SESSION_CONTEXT_CAPACITY
    return body


def _validate_retained_workloads(output: Path, records: dict) -> None:
    """Fail closed on base workloads retained by ``--reasoning-only``."""

    for workload_id, record in sorted(records.items()):
        try:
            path = output / str(record["path"])
            body = json.loads(path.read_text())
            prompt_tokens = int(body["prompt_token_count"])
            actual_prompt_tokens = len(body["token_ids"])
            max_new_tokens = int(body["max_new_tokens"])
            declared_capacity = int(
                body["metadata"]["session_context_capacity"]
            )
        except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"retained workload {workload_id} has no valid capacity contract"
            ) from exc
        if body.get("workload_id") != workload_id:
            raise ValueError(
                f"retained workload {workload_id} has a different document identity"
            )
        if prompt_tokens != actual_prompt_tokens:
            raise ValueError(
                f"retained workload {workload_id} declares {prompt_tokens} prompt "
                f"tokens but carries {actual_prompt_tokens}"
            )
        if declared_capacity != SESSION_CONTEXT_CAPACITY:
            raise ValueError(
                f"retained workload {workload_id} declares session capacity "
                f"{declared_capacity}, expected {SESSION_CONTEXT_CAPACITY}"
            )
        total = prompt_tokens + max_new_tokens
        if total > SESSION_CONTEXT_CAPACITY:
            raise ValueError(
                f"retained workload {workload_id}: prompt {prompt_tokens} + "
                f"max_new {max_new_tokens} = {total} exceeds the "
                f"{SESSION_CONTEXT_CAPACITY}-position session context"
            )


def build_reasoning_workloads(
    tokenizer, *, reasoning_max_new_tokens: int, agent_max_new_tokens: int
) -> dict[str, Workload]:
    """Build the thinking-enabled reasoning and agentic workloads.

    The four pinned acceptance workloads render with ``enable_thinking=False``,
    which makes the official Qwen3 template emit a *pre-closed* thinking block
    -- ``<think>\n\n</think>\n\n``, token ids 151667, 271, 151668, 271 --
    as the last four prompt tokens.  The model therefore never opens a thinking
    block of its own: it is structurally prevented from reasoning before it
    answers.  Rendering with ``enable_thinking=True`` ends the prompt at
    ``<|im_start|>assistant\n`` instead, so the model emits ``<think>`` itself
    and the reasoning is *generated* rather than suppressed.

    These are separate workload identities rather than edits to the pinned
    four, because a workload digest is an identity: changing the prompt of
    ``TA-QW-CHAT-1`` would silently invalidate every comparison already made
    against it.
    """

    def render(messages: list[dict[str, str]]) -> tuple[str, tuple[int, ...]]:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True,
        )
        return text, tuple(tokenizer.encode(text, add_special_tokens=False))

    workloads: dict[str, Workload] = {}

    # -- reasoning ----------------------------------------------------
    text, ids = render([{"role": "user", "content": CHAT_QUESTION}])
    if ids[-4:] == (151667, 271, 151668, 271):
        raise ValueError(
            "the reasoning prompt still ends in a pre-closed thinking block; "
            "enable_thinking did not take effect"
        )
    reasoning = Workload(
        workload_id="TA-QW-REASON-1",
        kind="reasoning",
        description=(
            "The TA-QW-CHAT-1 question rendered with thinking enabled, so the "
            "model opens and generates its own <think> block."
        ),
        rendered_text=text,
        token_ids=ids,
        max_new_tokens=reasoning_max_new_tokens,
        metadata={
            "enable_thinking": True,
            "derived_from": "TA-QW-CHAT-1",
            "difference_from_source": (
                "identical user content; the generation prompt ends at "
                "'<|im_start|>assistant\n' instead of a pre-closed "
                "'<think>\n\n</think>\n\n' block, so the four suppressing "
                "prompt tokens 151667, 271, 151668, 271 are absent"
            ),
            "thinking_open_token_id": 151667,
            "thinking_close_token_id": 151668,
            "checks": dict(CHAT_CHECKS),
            "session_context_capacity": SESSION_CONTEXT_CAPACITY,
        },
    )
    _check_context_budget(reasoning)
    workloads[reasoning.workload_id] = reasoning

    # -- agentic ------------------------------------------------------
    # Turn 0 only: an episode's later prompts are a function of what the
    # accelerator decoded and what the sandbox returned, so they cannot be
    # pinned in advance without pinning the answer too.  What is pinned is the
    # opening context, the sandbox contents and the protocol.
    text, ids = render(
        [
            {"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": AGENT_TASK},
        ]
    )
    agent = Workload(
        workload_id="TA-QW-AGENT-2",
        kind="agent",
        description=(
            "Closed-loop single-tool bash agent, thinking enabled.  Turn 0 of "
            "an episode whose later turns carry the sandbox's real output."
        ),
        rendered_text=text,
        token_ids=ids,
        max_new_tokens=agent_max_new_tokens,
        metadata={
            "enable_thinking": True,
            "derived_from": "TA-QW-AGENT-1",
            "closed_loop": True,
            "protocol": (
                "single fenced bash block per turn, executed in a frozen "
                "sandbox, output rendered back as the next user turn; "
                "'ANSWER: ' terminates"
            ),
            "sandbox_files": dict(AGENT_SANDBOX_FILES),
            "expected_total": sum(
                int(line.split(",")[1])
                for line in AGENT_SANDBOX_FILES["inventory.txt"].splitlines()
                if line.strip()
            ),
            "max_turns": 4,
            "session_context_capacity": SESSION_CONTEXT_CAPACITY,
        },
    )
    _check_context_budget(agent)
    workloads[agent.workload_id] = agent
    return workloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--checkpoint-lock", type=Path, default=DEFAULT_CHECKPOINT_LOCK
    )
    parser.add_argument(
        "--shared-semantics", type=Path, default=DEFAULT_SHARED_SEMANTICS
    )
    parser.add_argument(
        "--exact-8k-construction",
        type=Path,
        default=DEFAULT_EXACT_8K_CONSTRUCTION,
    )
    parser.add_argument(
        "--output", type=Path, default=REPO / "build" / "workloads" / "qwen3-8b"
    )
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument(
        "--reasoning-only",
        action="store_true",
        help=(
            "Author only the thinking-enabled reasoning and agentic workloads "
            "and merge them into the existing index, leaving the four pinned "
            "acceptance workloads and their digests untouched."
        ),
    )
    parser.add_argument("--reasoning-max-new-tokens", type=int, default=1024)
    parser.add_argument("--agent-max-new-tokens", type=int, default=512)
    args = parser.parse_args()

    checkpoint_lock = load_strict_json(args.checkpoint_lock)
    chat = QwenChatTokenizer(args.snapshot, checkpoint_lock)
    # This also authenticates every reused ROM prompt, decode and agent turn.
    # It is intentionally done even though exact-8K selects only the arithmetic
    # query: the construction source must remain the canonical shared suite.
    load_shared_workload(args.shared_semantics, chat=chat)
    construction = load_construction(args.exact_8k_construction)
    tokenizer = AuthenticatedWorkloadTokenizer(chat)
    tokenizer_sha = hashlib.sha256(
        (args.snapshot / SOURCE_FILES["tokenizer"]["path"]).read_bytes()
    ).hexdigest()
    if tokenizer_sha != SOURCE_FILES["tokenizer"]["sha256"]:
        raise ValueError("authenticated Qwen tokenizer digest differs")
    exact_8k = build_exact_8k_workload(
        tokenizer,
        construction,
        construction_path=args.exact_8k_construction,
    )

    if args.reasoning_only:
        workloads = build_reasoning_workloads(
            tokenizer,
            reasoning_max_new_tokens=args.reasoning_max_new_tokens,
            agent_max_new_tokens=args.agent_max_new_tokens,
        )
    else:
        workloads = build_workloads(
            tokenizer,
            exact_8k_workload=exact_8k,
            max_new_tokens=args.max_new_tokens,
        )
        workloads.update(
            build_reasoning_workloads(
                tokenizer,
                reasoning_max_new_tokens=args.reasoning_max_new_tokens,
                agent_max_new_tokens=args.agent_max_new_tokens,
            )
        )
    args.output.mkdir(parents=True, exist_ok=True)
    index_path = args.output / "index.json"
    existing: dict = {}
    if args.reasoning_only and index_path.exists():
        existing = json.loads(index_path.read_text()).get("workloads", {})
        _validate_retained_workloads(args.output, existing)
    index = {
        "schema": "opentallas.abi3.workload_index.v1",
        "model_id": "qwen3-8b",
        "snapshot": str(args.snapshot),
        "tokenizer_sha256": tokenizer_sha,
        "workloads": dict(existing),
    }
    for wid, workload in sorted(workloads.items()):
        body = _validated_body(workload)
        path = args.output / f"{wid}.json"
        path.write_bytes(canonical_json(body))
        index["workloads"][wid] = {
            "path": path.name,
            "kind": workload.kind,
            "digest": workload.digest,
            "prompt_token_count": len(workload.token_ids),
            "max_new_tokens": workload.max_new_tokens,
        }
        print(
            f"{wid:18s} kind={workload.kind:16s} "
            f"tokens={len(workload.token_ids):6d} digest={workload.digest[:16]}"
        )
    index_path.write_bytes(canonical_json(index))
    print(f"\nwrote {len(workloads)} workloads to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
