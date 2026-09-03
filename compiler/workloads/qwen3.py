"""Pinned Qwen3-8B acceptance workloads.

Section 5 of the plan revision fixes four Qwen workload contracts.  Each is
defined here once, as content plus a digest, so that the HBM deployment, the
ROM deployment, the cycle model and the independent oracle all consume exactly
the same prompt token IDs.  A comparison between two backends is only meaningful
if the prompt is byte-identical on both sides, so the workload is an artifact
with an identity, not a string literal in a runner.

The long-context prompt is supplied by the governed exact-8K constructor.  It
combines a public-domain source (Project Gutenberg eBook 2701, *Moby Dick*)
with a canonical ROM-authenticated query through the official Qwen chat
template.  A repeated-token filler would exercise neither the tokenizer nor the
attention distribution realistically; the repeated-special stress workload
exists separately and is explicitly not a substitute.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[2]

CORPUS_PATH = REPO / "data" / "corpus" / "pg2701_moby_dick.txt"
CORPUS_SHA256 = "9a6844ac0703853720010787c7b6c70b0020f1ab1862dcd74452fa46474d1215"
CORPUS_SOURCE = {
    "title": "Moby Dick; Or, The Whale",
    "author": "Herman Melville",
    "source": "Project Gutenberg eBook 2701",
    "url": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
    "licence": "public domain in the United States",
}

#: Exactly 8,000 natural prompt tokens is the mandatory Qwen context.
LONG_PROMPT_TOKENS = 8000

#: The separate repeated-special-token stress workload.
STRESS_PROMPT_TOKENS = 8000


@dataclass(frozen=True, slots=True)
class Workload:
    """One pinned workload: rendered text, token IDs and an identity digest."""

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
    "A cargo ship leaves port A at 06:00 travelling at 18 knots toward port B, "
    "which is 234 nautical miles away. Two hours later a second ship leaves "
    "port B toward port A at 24 knots. At what clock time do the two ships "
    "pass each other? Show your reasoning step by step, then state the final "
    "time on its own line."
)
CHAT_CHECKS = {
    "must_contain_any": ["10:", "10 ", "ten"],
    "reasoning_terms": ["knot", "distance", "speed", "hour"],
    "expected_answer_note": (
        "Ships close the remaining 198 nm at a combined 42 knots after 08:00, "
        "giving 4.714 h, i.e. about 12:43. The check is deliberately loose on "
        "the arithmetic and strict on the structure, because the acceptance "
        "gate is that the model produced coherent, on-topic, legitimately "
        "decoded text - not that an 8B model is a calculator."
    ),
}

AGENT_SYSTEM = (
    "You are a careful command-line assistant. You may run shell commands by "
    "emitting a single fenced block of the form:\n"
    "```bash\n<command>\n```\n"
    "Emit exactly one command per turn and wait for its output before "
    "continuing. When you have the answer, reply with a line beginning "
    "'ANSWER: ' and stop."
)
AGENT_TASK = (
    "The working directory contains a file named inventory.txt with one item "
    "per line in the form '<name>,<count>'. Report the total of all counts."
)
AGENT_SANDBOX_FILES = {
    "inventory.txt": "bolts,24\nnuts,17\nwashers,58\nscrews,131\nrivets,9\n"
}
AGENT_EXPECTED_TOTAL = 24 + 17 + 58 + 131 + 9


def load_corpus() -> str:
    """Return the verified public-domain corpus text."""
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(
            f"corpus missing at {CORPUS_PATH}; fetch {CORPUS_SOURCE['url']}"
        )
    raw = CORPUS_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CORPUS_SHA256:
        raise ValueError(
            f"corpus digest {digest} does not match the pinned {CORPUS_SHA256}"
        )
    return raw.decode("utf-8")


def natural_body(text: str) -> str:
    """Strip the Project Gutenberg header and licence, keeping the prose."""
    start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK"
    end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK"
    start = text.index(start_marker)
    start = text.index("\n", start) + 1
    end = text.index(end_marker)
    return text[start:end].strip()


def exact_token_window(
    encode, text: str, target_tokens: int
) -> tuple[str, tuple[int, ...]]:
    """Return a prose prefix that encodes to exactly ``target_tokens`` tokens.

    Truncating the *token* stream and decoding back would risk splitting a
    multi-byte character or a merged token, so the window is found on the text
    and then confirmed on the tokens.
    """
    ids = tuple(encode(text))
    if len(ids) < target_tokens:
        raise ValueError(
            f"corpus yields {len(ids)} tokens, fewer than the required "
            f"{target_tokens}"
        )
    low, high = 0, len(text)
    # Binary search the character count whose encoding is closest from below.
    while low < high:
        mid = (low + high + 1) // 2
        if len(encode(text[:mid])) <= target_tokens:
            low = mid
        else:
            high = mid - 1
    window = text[:low]
    ids = tuple(encode(window))
    # Extend one character at a time until the count is exact.
    cursor = low
    while len(ids) < target_tokens and cursor < len(text):
        cursor += 1
        window = text[:cursor]
        ids = tuple(encode(window))
    if len(ids) != target_tokens:
        raise ValueError(
            f"could not land on exactly {target_tokens} tokens; got {len(ids)}"
        )
    return window, ids


def build_workloads(
    tokenizer,
    *,
    exact_8k_workload: Workload,
    max_new_tokens: int = 256,
) -> dict[str, Workload]:
    """Build all four pinned Qwen workloads against a loaded tokenizer.

    ``tokenizer`` must expose ``apply_chat_template`` and ``encode`` compatible
    with the pinned Qwen3-8B tokenizer.
    """

    def encode(text: str) -> list[int]:
        return tokenizer.encode(text, add_special_tokens=False)

    chat_text = tokenizer.apply_chat_template(
        [{"role": "user", "content": CHAT_QUESTION}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    chat = Workload(
        workload_id="TA-QW-CHAT-1",
        kind="chat",
        description="Pinned reasoning question rendered with the official chat template.",
        rendered_text=chat_text,
        token_ids=tuple(encode(chat_text)),
        max_new_tokens=max_new_tokens,
        metadata={"checks": CHAT_CHECKS, "enable_thinking": False},
    )

    agent_text = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": AGENT_TASK},
        ],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    agent = Workload(
        workload_id="TA-QW-AGENT-1",
        kind="agent",
        description="Single-tool bash agent task executed in a frozen sandbox.",
        rendered_text=agent_text,
        token_ids=tuple(encode(agent_text)),
        max_new_tokens=max_new_tokens,
        metadata={
            "sandbox_files": AGENT_SANDBOX_FILES,
            "expected_total": AGENT_EXPECTED_TOTAL,
            "protocol": "single fenced bash block per turn, ANSWER: terminates",
        },
    )

    if (
        exact_8k_workload.workload_id != "TA-QW-8K-1"
        or exact_8k_workload.kind != "long_natural_chat"
        or len(exact_8k_workload.token_ids) != LONG_PROMPT_TOKENS
        or exact_8k_workload.max_new_tokens != max_new_tokens
    ):
        raise ValueError(
            "the mandatory Qwen long workload must be the governed exact-8K "
            "official-chat construction"
        )

    # Repeated-special-token stress: a legal but pathological token stream.
    special = tokenizer.encode("<|im_start|>", add_special_tokens=False)
    if len(special) != 1:
        raise ValueError("expected <|im_start|> to be a single special token")
    stress_ids = tuple(special * STRESS_PROMPT_TOKENS)
    stress = Workload(
        workload_id="TA-QW-STRESS-1",
        kind="repeated_special",
        description=(
            "Repeated-special-token stress workload. Separate from the natural "
            "8,000-token contract and never a substitute for it."
        ),
        rendered_text=tokenizer.decode(stress_ids),
        token_ids=stress_ids,
        max_new_tokens=32,
        metadata={"special_token_id": special[0]},
    )

    return {
        w.workload_id: w for w in (chat, agent, exact_8k_workload, stress)
    }
