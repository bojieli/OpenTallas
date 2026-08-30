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

from compiler.workloads.qwen3 import (  # noqa: E402
    AGENT_SANDBOX_FILES,
    AGENT_SYSTEM,
    AGENT_TASK,
    CHAT_CHECKS,
    CHAT_QUESTION,
    Workload,
    build_workloads,
)
from runtime.abi3.capability import canonical_json  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)


#: ``session_context_capacity`` from the pinned Qwen3-8B kernel IR.  Every
#: workload this module authors must satisfy
#: ``prompt_token_count + max_new_tokens <= SESSION_CONTEXT_CAPACITY``.
#: OI-34 records what happens when it does not: the mandatory 8,000-token
#: workload asks for 256 decode tokens against an 8,192-position context, so
#: the last 64 decode steps have nowhere to write and the contract is
#: arithmetically unsatisfiable.  The check below is why that error is not
#: reproduced here.
SESSION_CONTEXT_CAPACITY = 8192


def _check_context_budget(workload: "Workload") -> None:
    """Refuse a workload whose decode cannot fit its own declared context."""
    total = len(workload.token_ids) + workload.max_new_tokens
    if total > SESSION_CONTEXT_CAPACITY:
        raise ValueError(
            f"{workload.workload_id}: prompt {len(workload.token_ids)} + "
            f"max_new {workload.max_new_tokens} = {total} exceeds the "
            f"{SESSION_CONTEXT_CAPACITY}-position session context (OI-34)"
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

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True, trust_remote_code=False
    )
    tokenizer_sha = hashlib.sha256(
        (args.snapshot / "tokenizer.json").read_bytes()
    ).hexdigest()

    if args.reasoning_only:
        workloads = build_reasoning_workloads(
            tokenizer,
            reasoning_max_new_tokens=args.reasoning_max_new_tokens,
            agent_max_new_tokens=args.agent_max_new_tokens,
        )
    else:
        workloads = build_workloads(tokenizer, max_new_tokens=args.max_new_tokens)
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
    index = {
        "schema": "opentallas.abi3.workload_index.v1",
        "model_id": "qwen3-8b",
        "snapshot": str(args.snapshot),
        "tokenizer_sha256": tokenizer_sha,
        "workloads": dict(existing),
    }
    for wid, workload in sorted(workloads.items()):
        body = workload.to_dict()
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
