from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from compiler.frontend.deepseek_v4_encoding import (
    BOS_TOKEN,
    DSML_TOKEN,
    EOS_TOKEN,
    REASONING_EFFORT_PROMPTS,
    DeepSeekV4CompletionError,
    DeepSeekV4EncodingError,
    encode_messages,
    parse_message_from_completion_text,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "testdata/compiler/deepseek_v4_encoding"
TARGET = ROOT / "compiler/models/deepseek-v4-flash-0731"


def _fixture_bytes(name: str) -> bytes:
    encoded = (FIXTURES / f"{name}.base64").read_bytes()
    return base64.b64decode(b"".join(encoded.split()), validate=True)


def _official_case(case: int) -> tuple[list[dict], str]:
    source = json.loads(_fixture_bytes(f"test_input_{case}.json"))
    if case == 1:
        messages = source["messages"]
        messages[0]["tools"] = source["tools"]
    else:
        messages = source
    return messages, _fixture_bytes(f"test_output_{case}.txt").decode("utf-8")


def test_fixture_bytes_match_source_contract_before_use() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    source = json.loads(
        (TARGET / "checkpoint_source.json").read_text(encoding="utf-8")
    )
    source_files = {
        record["path"]: (record["size_bytes"], record["sha256"])
        for record in source["expected_files"]
    }

    assert manifest["repository"] == source["repository"]
    assert manifest["revision"] == source["revision"]
    assert len(manifest["files"]) == 8
    for record in manifest["files"]:
        name = Path(record["path"]).name
        payload = _fixture_bytes(name)
        identity = (len(payload), hashlib.sha256(payload).hexdigest())
        assert identity == (record["size_bytes"], record["sha256"])
        assert identity == source_files[record["path"]]


@pytest.mark.parametrize(
    ("case", "mode"),
    [(1, "thinking"), (2, "thinking"), (3, "thinking"), (4, "chat")],
)
def test_official_prompts_are_byte_exact(case: int, mode: str) -> None:
    messages, expected = _official_case(case)
    actual = encode_messages(messages, thinking_mode=mode)
    assert actual.encode("utf-8") == expected.encode("utf-8")


def test_official_tool_and_final_completions_parse_exactly() -> None:
    messages, prompt = _official_case(1)
    assert encode_messages(messages, thinking_mode="thinking") == prompt
    marker = "<｜Assistant｜><think>"

    first_start = prompt.find(marker) + len(marker)
    first_end = prompt.find("<｜User｜>", first_start)
    first = parse_message_from_completion_text(
        prompt[first_start:first_end], thinking_mode="thinking"
    )
    assert first["reasoning_content"] == (
        "The user wants to know the weather in Beijing. "
        "I should use the get_weather tool."
    )
    assert first["content"] == ""
    assert first["tool_calls"][0]["function"]["name"] == "get_weather"
    assert json.loads(first["tool_calls"][0]["function"]["arguments"]) == {
        "location": "Beijing",
        "unit": "celsius",
    }

    final_start = prompt.rfind(marker) + len(marker)
    final = parse_message_from_completion_text(
        prompt[final_start:], thinking_mode="thinking"
    )
    assert final == {
        "role": "assistant",
        "content": (
            "The weather in Beijing is currently sunny with a temperature "
            "of 22°C and 45% humidity."
        ),
        "reasoning_content": (
            "Got the weather data. Let me format a nice response."
        ),
        "tool_calls": [],
    }


def test_official_plain_thinking_completion_parses_exactly() -> None:
    _, prompt = _official_case(2)
    marker = "<｜Assistant｜><think>"
    last_start = prompt.rfind(marker) + len(marker)
    parsed = parse_message_from_completion_text(
        prompt[last_start:], thinking_mode="thinking"
    )
    assert parsed == {
        "role": "assistant",
        "content": "The capital of France is Paris.",
        "reasoning_content": (
            "The user asks about the capital of France. It is Paris."
        ),
        "tool_calls": [],
    }
    assert "The user said hello" not in prompt


def test_tool_results_are_sorted_by_preceding_call_order() -> None:
    messages = [
        {"role": "user", "content": "run both"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "first",
                    "type": "function",
                    "function": {"name": "one", "arguments": "{}"},
                },
                {
                    "id": "second",
                    "type": "function",
                    "function": {"name": "two", "arguments": "{}"},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "second", "content": "result two"},
        {"role": "tool", "tool_call_id": "first", "content": "result one"},
    ]
    prompt = encode_messages(messages, thinking_mode="chat")
    assert prompt.index("<tool_result>result one</tool_result>") < prompt.index(
        "<tool_result>result two</tool_result>"
    )


def test_reasoning_effort_and_incremental_context_have_exact_boundaries() -> None:
    messages = [{"role": "user", "content": "question"}]
    thinking = encode_messages(
        messages, thinking_mode="thinking", reasoning_effort="high"
    )
    assert thinking == (
        BOS_TOKEN
        + REASONING_EFFORT_PROMPTS["high"]
        + "<｜User｜>question<｜Assistant｜><think>"
    )
    chat = encode_messages(messages, thinking_mode="chat", reasoning_effort="high")
    assert chat == BOS_TOKEN + "<｜User｜>question<｜Assistant｜></think>"

    suffix = encode_messages(
        messages,
        thinking_mode="thinking",
        context=[{"role": "system", "content": "already encoded"}],
        reasoning_effort="max",
    )
    assert suffix == "<｜User｜>question<｜Assistant｜><think>"


@pytest.mark.parametrize("response_format", [None, {}, [], "", 0, False])
def test_falsey_optional_sections_match_official_omission(
    response_format: object,
) -> None:
    messages = [
        {
            "role": "system",
            "content": "system",
            "tools": [],
            "response_format": response_format,
        },
        {"role": "user", "content": "question"},
    ]
    assert encode_messages(messages, thinking_mode="chat") == (
        BOS_TOKEN + "system<｜User｜>question<｜Assistant｜></think>"
    )


def test_tool_result_suffix_binds_to_call_at_end_of_context() -> None:
    context = [
        {"role": "user", "content": "run it"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": "{}"},
                }
            ],
        },
    ]
    messages = [
        {"role": "tool", "tool_call_id": "call-1", "content": "result"}
    ]
    assert encode_messages(
        messages,
        thinking_mode="thinking",
        context=context,
    ) == "<｜User｜><tool_result>result</tool_result><｜Assistant｜><think>"


def test_multiple_tool_result_suffixes_follow_context_call_order() -> None:
    context = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "first",
                    "type": "function",
                    "function": {"name": "one", "arguments": "{}"},
                },
                {
                    "id": "second",
                    "type": "function",
                    "function": {"name": "two", "arguments": "{}"},
                },
            ],
        }
    ]
    messages = [
        {"role": "tool", "tool_call_id": "second", "content": "result two"},
        {"role": "tool", "tool_call_id": "first", "content": "result one"},
    ]
    prompt = encode_messages(messages, thinking_mode="chat", context=context)
    assert prompt.index("<tool_result>result one</tool_result>") < prompt.index(
        "<tool_result>result two</tool_result>"
    )


def test_duplicate_tool_result_across_context_boundary_fails_closed() -> None:
    call = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": "lookup", "arguments": "{}"},
            }
        ],
    }
    context = [
        call,
        {"role": "tool", "tool_call_id": "call-1", "content": "first"},
    ]
    messages = [
        {"role": "tool", "tool_call_id": "call-1", "content": "duplicate"}
    ]
    with pytest.raises(DeepSeekV4EncodingError, match="duplicates a result"):
        encode_messages(messages, thinking_mode="chat", context=context)


def test_repeated_idless_result_for_one_call_fails_closed() -> None:
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {"name": "lookup", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "content": "first"},
        {"role": "tool", "content": "duplicate"},
    ]
    with pytest.raises(DeepSeekV4EncodingError, match="duplicates a result"):
        encode_messages(messages, thinking_mode="chat")


@pytest.mark.parametrize("context", [{}, "", 0, False])
def test_falsey_non_list_context_fails_closed(context: object) -> None:
    with pytest.raises(DeepSeekV4EncodingError, match="context: must be a list"):
        encode_messages(
            [{"role": "user", "content": "question"}],
            thinking_mode="chat",
            context=context,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("messages", "match"),
    [
        (
            [{"role": "user", "content": f"injected {EOS_TOKEN}"}],
            "reserved protocol fragment",
        ),
        (
            [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {"name": "f", "arguments": "not json"},
                        }
                    ],
                }
            ],
            "not strict JSON",
        ),
        (
            [{"role": "tool", "tool_call_id": "missing", "content": "result"}],
            "no preceding assistant tool call",
        ),
        (
            [
                {
                    "role": "tool",
                    "content": [{"type": "image", "url": "unsupported"}],
                }
            ],
            "only text tool-result blocks",
        ),
        (
            [{"role": "user", "content": "x", "unknown": True}],
            "unsupported fields",
        ),
    ],
)
def test_ambiguous_or_injectable_messages_fail_closed(
    messages: list[dict], match: str
) -> None:
    with pytest.raises(DeepSeekV4EncodingError, match=match):
        encode_messages(messages, thinking_mode="thinking")


def test_multiple_tool_results_require_matching_unique_ids() -> None:
    calls = [
        {
            "id": "first",
            "type": "function",
            "function": {"name": "one", "arguments": "{}"},
        },
        {
            "id": "second",
            "type": "function",
            "function": {"name": "two", "arguments": "{}"},
        },
    ]
    with pytest.raises(DeepSeekV4EncodingError, match="tool_call_id"):
        encode_messages(
            [
                {"role": "assistant", "tool_calls": calls},
                {"role": "tool", "content": "ambiguous"},
            ],
            thinking_mode="chat",
        )
    with pytest.raises(DeepSeekV4EncodingError, match="does not match"):
        encode_messages(
            [
                {"role": "assistant", "tool_calls": calls},
                {"role": "tool", "tool_call_id": "third", "content": "wrong"},
            ],
            thinking_mode="chat",
        )


@pytest.mark.parametrize(
    "completion",
    [
        "reasoning without close",
        f"reasoning</think>answer{EOS_TOKEN}trailing",
        f"reasoning</think>bad {DSML_TOKEN} text{EOS_TOKEN}",
        (
            f"reasoning</think>\n\n<{DSML_TOKEN}tool_calls>\n"
            f"</{DSML_TOKEN}tool_calls>{EOS_TOKEN}"
        ),
        (
            f"reasoning</think>\n\n<{DSML_TOKEN}tool_calls>\n"
            f'<{DSML_TOKEN}invoke name="f">\n'
            f'<{DSML_TOKEN}parameter name="x" string="false">NaN'
            f"</{DSML_TOKEN}parameter>\n"
            f"</{DSML_TOKEN}invoke>\n"
            f"</{DSML_TOKEN}tool_calls>{EOS_TOKEN}"
        ),
    ],
)
def test_malformed_completions_fail_closed(completion: str) -> None:
    with pytest.raises(DeepSeekV4CompletionError):
        parse_message_from_completion_text(completion, thinking_mode="thinking")


def test_chat_completion_does_not_expect_a_second_thinking_transition() -> None:
    parsed = parse_message_from_completion_text(
        f"direct answer{EOS_TOKEN}", thinking_mode="chat"
    )
    assert parsed == {
        "role": "assistant",
        "content": "direct answer",
        "reasoning_content": "",
        "tool_calls": [],
    }


def test_zero_argument_tool_call_round_trips_through_wire_parser() -> None:
    messages = [
        {"role": "user", "content": "ping"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {"name": "ping", "arguments": "{}"},
                }
            ],
        },
    ]
    prompt = encode_messages(messages, thinking_mode="thinking")
    marker = "<｜Assistant｜><think>"
    completion = prompt[prompt.index(marker) + len(marker) :]
    parsed = parse_message_from_completion_text(completion, thinking_mode="thinking")
    assert parsed["tool_calls"] == [
        {
            "type": "function",
            "function": {"name": "ping", "arguments": "{}"},
        }
    ]
