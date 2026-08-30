"""The thinking-mode half of the agent protocol.

Qwen3's chat template has two renderings and they are not interchangeable.
With ``enable_thinking=False`` the template appends a *pre-closed* thinking
block to the prompt, so the model cannot reason before it acts; with
``enable_thinking=True`` the prompt ends at the generation header and the model
opens its own block.  These tests pin the consequences for the loop: which text
is parsed for an action, and what the history carries forward.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.agent import (
    THINK_CLOSE_TOKEN_ID,
    THINK_OPEN_TOKEN_ID,
    AgentProtocolError,
    parse_turn,
    split_thinking,
)

ROOT = Path(__file__).resolve().parents[2]
WORKLOADS = ROOT / "build" / "workloads" / "qwen3-8b"

#: The four prompt tokens the template appends when reasoning is suppressed:
#: ``<think>``, ``\n\n``, ``</think>``, ``\n\n``.
SUPPRESSED_TAIL = (THINK_OPEN_TOKEN_ID, 271, THINK_CLOSE_TOKEN_ID, 271)


def test_split_thinking_returns_none_without_a_closed_block() -> None:
    thinking, visible = split_thinking("no block here")
    assert thinking is None
    assert visible == "no block here"


def test_split_thinking_separates_reasoning_from_action() -> None:
    thinking, visible = split_thinking(
        "<think>\nI could use wc, or awk.\n</think>\n\n```bash\nawk '{}' f\n```"
    )
    assert thinking == "I could use wc, or awk."
    assert visible == "```bash\nawk '{}' f\n```"


def test_a_drafted_command_inside_the_thinking_block_is_not_an_action() -> None:
    """The failure this split exists to prevent.

    A reasoning model drafts candidate commands while it thinks.  Parsing the
    whole turn would count those drafts, see several fenced blocks and fail the
    episode for a protocol violation the model never committed -- so the parse
    runs on what the model emitted *after* it stopped thinking.
    """
    turn = (
        "<think>\nMaybe ```bash\nwc -l f\n``` or maybe sum the column.\n</think>\n\n"
        "```bash\nawk -F, '{s+=$2} END{print s}' f\n```"
    )
    with pytest.raises(AgentProtocolError):
        parse_turn(turn)
    _, visible = split_thinking(turn)
    parsed = parse_turn(visible)
    assert parsed.kind == "command"
    assert parsed.command == "awk -F, '{s+=$2} END{print s}' f"


def test_an_answer_inside_the_thinking_block_does_not_end_the_episode() -> None:
    turn = "<think>\nANSWER: 239 maybe?\nLet me check.\n</think>\n\n```bash\ncat f\n```"
    _, visible = split_thinking(turn)
    assert parse_turn(visible).kind == "command"


def test_a_truncated_thought_carries_no_action() -> None:
    """A generation cut off mid-thought is not a turn the protocol can act on."""
    thinking, visible = split_thinking("<think>\nStill working on it and then")
    assert thinking is None
    assert parse_turn(visible).kind == "neither"


@pytest.mark.parametrize(
    "workload_id, thinking_enabled",
    [
        ("TA-QW-CHAT-1", False),
        ("TA-QW-AGENT-1", False),
        ("TA-QW-REASON-1", True),
        ("TA-QW-AGENT-2", True),
    ],
)
def test_pinned_workloads_render_the_thinking_mode_they_declare(
    workload_id: str, thinking_enabled: bool
) -> None:
    """The metadata flag and the rendered prompt must agree.

    A workload that says ``enable_thinking: true`` while its prompt still ends
    in the suppressing four tokens would be reported as a reasoning run and
    would not be one.
    """
    path = WORKLOADS / f"{workload_id}.json"
    if not path.exists():
        pytest.skip(f"{workload_id} has not been built")
    body = json.loads(path.read_text())
    declared = bool(body.get("metadata", {}).get("enable_thinking", False))
    assert declared is thinking_enabled
    tail = tuple(body["token_ids"][-4:])
    assert (tail == SUPPRESSED_TAIL) is (not thinking_enabled)
    assert (SUPPRESSED_TAIL[0] in body["token_ids"]) is (not thinking_enabled)


@pytest.mark.parametrize(
    "workload_id", ["TA-QW-CHAT-1", "TA-QW-AGENT-1", "TA-QW-REASON-1", "TA-QW-AGENT-2"]
)
def test_a_workload_can_decode_every_token_it_asks_for(workload_id: str) -> None:
    """OI-34: ``prompt + max_new`` must fit the declared session context.

    The mandatory 8,000-token workload asks for 256 decode tokens against an
    8,192-position context, which leaves the last 64 steps nowhere to write.
    Every workload authored since is checked here so the error is not repeated.
    """
    path = WORKLOADS / f"{workload_id}.json"
    if not path.exists():
        pytest.skip(f"{workload_id} has not been built")
    body = json.loads(path.read_text())
    capacity = int(body.get("metadata", {}).get("session_context_capacity", 8192))
    total = int(body["prompt_token_count"]) + int(body["max_new_tokens"])
    assert total <= capacity, (
        f"{workload_id}: {body['prompt_token_count']} prompt + "
        f"{body['max_new_tokens']} max_new = {total} exceeds {capacity}"
    )
