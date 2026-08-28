"""Fail-closed host text protocol for the pinned DeepSeek V4 Flash release.

This module independently implements the behavior of the content-pinned
``encoding/encoding_dsv4.py`` reference. It intentionally does not import or
execute checkpoint Python. Valid official inputs render byte-for-byte like the
release, while malformed or structurally ambiguous inputs raise a typed error
instead of relying on ``assert`` statements, placeholder text, or permissive
JSON fallbacks.

The boundary here is Unicode text. Tokenization is implemented separately so
message-format review does not depend on a tokenizer implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
import json
import re
from typing import Any


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
ENCODING_SOURCE_SHA256 = (
    "abc0d26120250dda0ae077dc64aa28836026e61e970854aaeb792445e6a0dde6"
)

BOS_TOKEN = "<｜begin▁of▁sentence｜>"
EOS_TOKEN = "<｜end▁of▁sentence｜>"
THINKING_START_TOKEN = "<think>"
THINKING_END_TOKEN = "</think>"
DSML_TOKEN = "｜DSML｜"
USER_TOKEN = "<｜User｜>"
ASSISTANT_TOKEN = "<｜Assistant｜>"
LATEST_REMINDER_TOKEN = "<｜latest_reminder｜>"

TASK_TOKENS = {
    "action": "<｜action｜>",
    "query": "<｜query｜>",
    "authority": "<｜authority｜>",
    "domain": "<｜domain｜>",
    "title": "<｜title｜>",
    "read_url": "<｜read_url｜>",
}

REASONING_EFFORT_PROMPTS = {
    "low": "",
    "high": (
        "Reasoning Effort: Absolute maximum with no shortcuts permitted.\n"
        "You MUST be very thorough in your thinking and comprehensively decompose "
        "the problem to resolve the root cause, rigorously stress-testing your logic "
        "against all potential paths, edge cases, and adversarial scenarios.\n"
        "Explicitly write out your entire deliberation process, documenting every "
        "intermediate step, considered alternative, and rejected hypothesis to "
        "ensure absolutely no assumption is left unchecked.\n\n"
    ),
    "max": (
        "Reasoning Effort: Beyond maximum — exhaustive, relentless, and "
        "uncompromising.\n"
        "You MUST reason with the utmost depth and rigor, leaving absolutely nothing "
        "to chance: exhaustively decompose the problem into its most fundamental "
        "components, trace every causal chain to its root, and resolve the underlying "
        "cause rather than any surface symptom.\n"
        "Do not stop reasoning until you have independently verified the solution "
        "from multiple angles and are certain that no assumption remains unchecked "
        "and no error remains undiscovered.\n\n"
    ),
}

_RESPONSE_FORMAT_TEMPLATE = (
    "## Response Format:\n\n"
    "You MUST strictly adhere to the following schema to reply:\n{schema}"
)
_TOOL_CALL_TEMPLATE = (
    '<{dsml}invoke name="{name}">\n{arguments}\n</{dsml}invoke>'
)
_TOOL_CALLS_TEMPLATE = "<{dsml}tool_calls>\n{tool_calls}\n</{dsml}tool_calls>"
_TOOL_OUTPUT_TEMPLATE = "<tool_result>{content}</tool_result>"
_TOOLS_TEMPLATE = """## Tools

You have access to a set of tools to help answer the user's question. You can invoke tools by writing a "<{dsml}tool_calls>" block like the following:

<{dsml}tool_calls>
<{dsml}invoke name="$TOOL_NAME">
<{dsml}parameter name="$PARAMETER_NAME" string="true|false">$PARAMETER_VALUE</{dsml}parameter>
...
</{dsml}invoke>
<{dsml}invoke name="$TOOL_NAME2">
...
</{dsml}invoke>
</{dsml}tool_calls>

String parameters should be specified as is and set `string="true"`. For all other types (numbers, booleans, arrays, objects), pass the value in JSON format and set `string="false"`.

If thinking_mode is enabled (triggered by {thinking_start}), you MUST output your complete reasoning inside {thinking_start}...{thinking_end} BEFORE any tool calls or final response.

Otherwise, output directly after {thinking_end} with tool calls or final response.

### Available Tool Schemas

{tool_schemas}

You MUST strictly follow the above defined tool name and parameter schemas to invoke tool calls.
"""

_RESERVED_INPUT_FRAGMENTS = (
    BOS_TOKEN,
    EOS_TOKEN,
    THINKING_START_TOKEN,
    THINKING_END_TOKEN,
    DSML_TOKEN,
    USER_TOKEN,
    ASSISTANT_TOKEN,
    LATEST_REMINDER_TOKEN,
    "<tool_result>",
    "</tool_result>",
)
_ROLE_FIELDS = {
    "system": {"role", "content", "tools", "response_format", "mask"},
    "developer": {"role", "content", "tools", "response_format", "mask"},
    "user": {"role", "content", "task", "mask"},
    "assistant": {
        "role",
        "content",
        "reasoning_content",
        "tool_calls",
        "wo_eos",
        "task",
        "mask",
    },
    "tool": {"role", "content", "tool_call_id", "mask"},
    "latest_reminder": {"role", "content", "mask"},
}
_NAME_RE = re.compile(r'^[^"<>\r\n]+$')


class DeepSeekV4EncodingError(ValueError):
    """Raised when a message cannot be represented unambiguously."""


class DeepSeekV4CompletionError(DeepSeekV4EncodingError):
    """Raised when a generated completion violates the pinned wire grammar."""


def _error(path: str, detail: str) -> DeepSeekV4EncodingError:
    return DeepSeekV4EncodingError(f"{path}: {detail}")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value}")


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def _load_json_object(text: str, path: str) -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_reject_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _error(path, f"arguments are not strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise _error(path, "arguments must encode one JSON object")
    return value


def _json_text(value: Any, path: str) -> str:
    try:
        rendered = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise _error(path, f"value is not strict JSON: {exc}") from exc
    _reject_reserved(rendered, path)
    return rendered


def _expect_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(path, "must be an object")
    if not all(isinstance(key, str) for key in value):
        raise _error(path, "all object keys must be strings")
    return value


def _expect_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise _error(path, "must be a list")
    return value


def _reject_reserved(value: str, path: str) -> None:
    for fragment in _RESERVED_INPUT_FRAGMENTS:
        if fragment in value:
            raise _error(path, f"contains reserved protocol fragment {fragment!r}")


def _text(value: Any, path: str, *, empty: bool = True) -> str:
    if value is None and empty:
        return ""
    if not isinstance(value, str):
        raise _error(path, "must be a string")
    if not empty and not value:
        raise _error(path, "must be a non-empty string")
    _reject_reserved(value, path)
    return value


def _name(value: Any, path: str) -> str:
    result = _text(value, path, empty=False)
    if not _NAME_RE.fullmatch(result):
        raise _error(path, "contains a character unsafe in a DSML attribute")
    return result


def _normalize_tools(value: Any, path: str) -> list[dict[str, Any]]:
    tools = _expect_list(value, path)
    result: list[dict[str, Any]] = []
    for index, raw_tool in enumerate(tools):
        item_path = f"{path}[{index}]"
        tool = dict(_expect_mapping(raw_tool, item_path))
        if set(tool) != {"type", "function"} or tool.get("type") != "function":
            raise _error(item_path, "must be an OpenAI function-tool object")
        function = dict(_expect_mapping(tool["function"], f"{item_path}.function"))
        if "name" not in function:
            raise _error(f"{item_path}.function", "is missing name")
        function["name"] = _name(function["name"], f"{item_path}.function.name")
        _json_text(function, f"{item_path}.function")
        result.append({"type": "function", "function": function})
    if not result:
        raise _error(path, "must contain at least one tool")
    return result


def _normalize_tool_calls(value: Any, path: str) -> list[dict[str, Any]]:
    calls = _expect_list(value, path)
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_call in enumerate(calls):
        item_path = f"{path}[{index}]"
        call = dict(_expect_mapping(raw_call, item_path))
        allowed = {"id", "type", "function"}
        if set(call) - allowed or set(call) < {"function"}:
            raise _error(item_path, "must contain only id, type, and function")
        if "type" in call and call["type"] != "function":
            raise _error(f"{item_path}.type", "must equal 'function'")
        function = dict(_expect_mapping(call["function"], f"{item_path}.function"))
        if set(function) != {"name", "arguments"}:
            raise _error(
                f"{item_path}.function", "must contain exactly name and arguments"
            )
        name = _name(function["name"], f"{item_path}.function.name")
        arguments_text = _text(
            function["arguments"], f"{item_path}.function.arguments"
        )
        _load_json_object(arguments_text, f"{item_path}.function.arguments")
        normalized: dict[str, Any] = {
            "type": "function",
            "function": {"name": name, "arguments": arguments_text},
        }
        if "id" in call:
            call_id = _text(call["id"], f"{item_path}.id", empty=False)
            if call_id in seen_ids:
                raise _error(f"{item_path}.id", f"duplicates tool-call id {call_id!r}")
            seen_ids.add(call_id)
            normalized["id"] = call_id
        result.append(normalized)
    return result


def _normalize_tool_content(value: Any, path: str) -> str | list[dict[str, str]]:
    if isinstance(value, str) or value is None:
        return _text(value, path)
    blocks = _expect_list(value, path)
    result: list[dict[str, str]] = []
    for index, raw_block in enumerate(blocks):
        block_path = f"{path}[{index}]"
        block = dict(_expect_mapping(raw_block, block_path))
        if set(block) != {"type", "text"} or block.get("type") != "text":
            raise _error(block_path, "only text tool-result blocks are supported")
        result.append(
            {"type": "text", "text": _text(block["text"], f"{block_path}.text")}
        )
    return result


def _normalize_messages(value: Any, path: str) -> list[dict[str, Any]]:
    messages = _expect_list(value, path)
    result: list[dict[str, Any]] = []
    for index, raw_message in enumerate(messages):
        item_path = f"{path}[{index}]"
        message = dict(_expect_mapping(raw_message, item_path))
        role = message.get("role")
        if role not in _ROLE_FIELDS:
            raise _error(f"{item_path}.role", f"unsupported role {role!r}")
        unexpected = set(message) - _ROLE_FIELDS[role]
        if unexpected:
            raise _error(item_path, f"contains unsupported fields {sorted(unexpected)!r}")

        normalized: dict[str, Any] = {"role": role}
        content = message.get("content")
        if role == "developer":
            normalized["content"] = _text(
                content, f"{item_path}.content", empty=False
            )
        elif role == "tool":
            normalized["content"] = _normalize_tool_content(
                content, f"{item_path}.content"
            )
        else:
            normalized["content"] = _text(content, f"{item_path}.content")

        if "tools" in message:
            if role not in {"system", "developer"}:
                raise _error(f"{item_path}.tools", "tools require system or developer role")
            normalized["tools"] = _normalize_tools(
                message["tools"], f"{item_path}.tools"
            )
        if "response_format" in message:
            _json_text(message["response_format"], f"{item_path}.response_format")
            normalized["response_format"] = copy.deepcopy(message["response_format"])
        if "tool_calls" in message:
            if role != "assistant":
                raise _error(f"{item_path}.tool_calls", "requires assistant role")
            normalized["tool_calls"] = _normalize_tool_calls(
                message["tool_calls"], f"{item_path}.tool_calls"
            )
        if "reasoning_content" in message:
            normalized["reasoning_content"] = _text(
                message["reasoning_content"], f"{item_path}.reasoning_content"
            )
        if "wo_eos" in message:
            if not isinstance(message["wo_eos"], bool):
                raise _error(f"{item_path}.wo_eos", "must be a boolean")
            normalized["wo_eos"] = message["wo_eos"]
        if "task" in message:
            task = message["task"]
            if task not in TASK_TOKENS:
                raise _error(f"{item_path}.task", f"unsupported task {task!r}")
            normalized["task"] = task
        if "tool_call_id" in message:
            normalized["tool_call_id"] = _text(
                message["tool_call_id"], f"{item_path}.tool_call_id"
            )
        if "mask" in message:
            mask = message["mask"]
            if not isinstance(mask, (bool, int)):
                raise _error(f"{item_path}.mask", "must be an integer or boolean")
            normalized["mask"] = mask
        result.append(normalized)
    return result


def _tool_call_id(call: Mapping[str, Any]) -> str:
    value = call.get("id")
    return value if isinstance(value, str) else ""


def _merge_tool_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    active_calls: list[dict[str, Any]] | None = None
    result_ids: set[str] = set()

    for index, original in enumerate(messages):
        message = copy.deepcopy(original)
        role = message["role"]
        if role == "assistant":
            active_calls = message.get("tool_calls")
            result_ids = set()
            merged.append(message)
            continue
        if role == "tool":
            if not active_calls:
                raise _error(
                    f"messages[{index}]", "tool result has no preceding assistant tool call"
                )
            call_ids = [_tool_call_id(call) for call in active_calls]
            result_id = message.get("tool_call_id", "")
            nonempty_call_ids = [call_id for call_id in call_ids if call_id]
            if result_id:
                if result_id not in nonempty_call_ids:
                    raise _error(
                        f"messages[{index}].tool_call_id",
                        f"does not match preceding tool calls: {result_id!r}",
                    )
                if result_id in result_ids:
                    raise _error(
                        f"messages[{index}].tool_call_id",
                        f"duplicates tool result {result_id!r}",
                    )
                result_ids.add(result_id)
            elif len(active_calls) > 1:
                raise _error(
                    f"messages[{index}].tool_call_id",
                    "is required when the preceding assistant made multiple calls",
                )
            block = {
                "type": "tool_result",
                "tool_use_id": result_id,
                "content": message["content"],
            }
            if (
                merged
                and merged[-1].get("role") == "user"
                and "content_blocks" in merged[-1]
            ):
                merged[-1]["content_blocks"].append(block)
            else:
                merged.append({"role": "user", "content_blocks": [block]})
            continue
        if role == "user":
            text_block = {"type": "text", "text": message["content"]}
            if (
                merged
                and merged[-1].get("role") == "user"
                and "content_blocks" in merged[-1]
                and merged[-1].get("task") is None
            ):
                merged[-1]["content_blocks"].append(text_block)
            else:
                new_message: dict[str, Any] = {
                    "role": "user",
                    "content": message["content"],
                    "content_blocks": [text_block],
                }
                for key in ("task", "wo_eos", "mask"):
                    if key in message:
                        new_message[key] = message[key]
                merged.append(new_message)
            active_calls = None
            continue
        merged.append(message)
        active_calls = None
    return merged


def _sort_tool_results(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    call_order: dict[str, int] = {}
    for message in messages:
        if message["role"] == "assistant" and message.get("tool_calls"):
            ids = [_tool_call_id(call) for call in message["tool_calls"]]
            call_order = {
                call_id: index for index, call_id in enumerate(ids) if call_id
            }
            continue
        blocks = message.get("content_blocks")
        if message["role"] != "user" or not blocks:
            continue
        tool_blocks = [block for block in blocks if block["type"] == "tool_result"]
        if len(tool_blocks) <= 1:
            continue
        result_ids = [block["tool_use_id"] for block in tool_blocks]
        if any(not result_id or result_id not in call_order for result_id in result_ids):
            raise _error(
                "messages",
                "multiple tool results require unique IDs matching the preceding calls",
            )
        sorted_blocks = sorted(tool_blocks, key=lambda block: call_order[block["tool_use_id"]])
        iterator = iter(sorted_blocks)
        message["content_blocks"] = [
            next(iterator) if block["type"] == "tool_result" else block
            for block in blocks
        ]
    return messages


def _find_last_user_index(messages: Sequence[Mapping[str, Any]]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].get("role") in {"user", "developer"}:
            return index
    return -1


def _drop_thinking_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last_user_index = _find_last_user_index(messages)
    result: list[dict[str, Any]] = []
    keep_roles = {"user", "system", "tool", "latest_reminder"}
    for index, message in enumerate(messages):
        role = message["role"]
        if role in keep_roles or index >= last_user_index:
            result.append(message)
        elif role == "assistant":
            copied = copy.copy(message)
            copied.pop("reasoning_content", None)
            result.append(copied)
    return result


def _render_tools(tools: list[dict[str, Any]]) -> str:
    schemas = [
        _json_text(tool["function"], f"tools[{index}].function")
        for index, tool in enumerate(tools)
    ]
    return _TOOLS_TEMPLATE.format(
        tool_schemas="\n".join(schemas),
        dsml=DSML_TOKEN,
        thinking_start=THINKING_START_TOKEN,
        thinking_end=THINKING_END_TOKEN,
    )


def _encode_arguments(tool_call: Mapping[str, Any], path: str) -> str:
    arguments = _load_json_object(tool_call["function"]["arguments"], path)
    parameters: list[str] = []
    for key, value in arguments.items():
        safe_key = _name(key, f"{path}.{key}")
        if isinstance(value, str):
            rendered_value = _text(value, f"{path}.{key}")
            is_string = "true"
        else:
            rendered_value = _json_text(value, f"{path}.{key}")
            is_string = "false"
        parameters.append(
            f'<{DSML_TOKEN}parameter name="{safe_key}" string="{is_string}">'
            f"{rendered_value}</{DSML_TOKEN}parameter>"
        )
    return "\n".join(parameters)


def _render_message(
    index: int,
    messages: list[dict[str, Any]],
    *,
    thinking_mode: str,
    drop_thinking: bool,
    reasoning_effort: str,
) -> str:
    message = messages[index]
    role = message["role"]
    prompt = ""
    if index == 0 and thinking_mode == "thinking":
        prompt += REASONING_EFFORT_PROMPTS[reasoning_effort]

    if role == "system":
        prompt += message["content"]
        if message.get("tools"):
            prompt += "\n\n" + _render_tools(message["tools"])
        if "response_format" in message:
            prompt += "\n\n" + _RESPONSE_FORMAT_TEMPLATE.format(
                schema=_json_text(message["response_format"], "response_format")
            )
    elif role == "developer":
        prompt += USER_TOKEN + message["content"]
        if message.get("tools"):
            prompt += "\n\n" + _render_tools(message["tools"])
        if "response_format" in message:
            prompt += "\n\n" + _RESPONSE_FORMAT_TEMPLATE.format(
                schema=_json_text(message["response_format"], "response_format")
            )
    elif role == "user":
        prompt += USER_TOKEN
        parts: list[str] = []
        for block in message["content_blocks"]:
            if block["type"] == "text":
                parts.append(block["text"])
                continue
            content = block["content"]
            if isinstance(content, list):
                content = "\n\n".join(item["text"] for item in content)
            parts.append(_TOOL_OUTPUT_TEMPLATE.format(content=content))
        prompt += "\n\n".join(parts)
    elif role == "latest_reminder":
        prompt += LATEST_REMINDER_TOKEN + message["content"]
    elif role == "assistant":
        tool_content = ""
        if message.get("tool_calls"):
            calls = []
            for call_index, call in enumerate(message["tool_calls"]):
                calls.append(
                    _TOOL_CALL_TEMPLATE.format(
                        dsml=DSML_TOKEN,
                        name=call["function"]["name"],
                        arguments=_encode_arguments(
                            call, f"messages[{index}].tool_calls[{call_index}].arguments"
                        ),
                    )
                )
            tool_content = "\n\n" + _TOOL_CALLS_TEMPLATE.format(
                dsml=DSML_TOKEN, tool_calls="\n".join(calls)
            )
        thinking = ""
        previous_has_task = index > 0 and messages[index - 1].get("task") is not None
        if thinking_mode == "thinking" and not previous_has_task:
            if not drop_thinking or index > _find_last_user_index(messages):
                thinking = message.get("reasoning_content", "") + THINKING_END_TOKEN
        prompt += thinking + message["content"] + tool_content
        if not message.get("wo_eos", False):
            prompt += EOS_TOKEN
    else:  # pragma: no cover - normalization makes this unreachable
        raise _error(f"messages[{index}].role", f"unsupported role {role!r}")

    if index + 1 < len(messages) and messages[index + 1]["role"] not in {
        "assistant",
        "latest_reminder",
    }:
        return prompt

    task = message.get("task")
    if task is not None:
        if task == "action":
            prompt += ASSISTANT_TOKEN
            prompt += (
                THINKING_START_TOKEN
                if thinking_mode == "thinking"
                else THINKING_END_TOKEN
            )
        prompt += TASK_TOKENS[task]
    elif role in {"user", "developer"}:
        prompt += ASSISTANT_TOKEN
        if thinking_mode == "thinking" and (
            not drop_thinking or index >= _find_last_user_index(messages)
        ):
            prompt += THINKING_START_TOKEN
        else:
            prompt += THINKING_END_TOKEN
    return prompt


def encode_messages(
    messages: list[dict[str, Any]],
    thinking_mode: str,
    context: list[dict[str, Any]] | None = None,
    drop_thinking: bool = True,
    add_default_bos_token: bool = True,
    reasoning_effort: str | None = None,
) -> str:
    """Encode validated OpenAI-style messages into the official V4 wire text.

    The output matches the pinned release for its four official fixtures.
    Structural input that the release would silently coerce or ignore is rejected.
    ``context`` affects transitions but is not emitted again.
    """

    if thinking_mode not in {"chat", "thinking"}:
        raise _error("thinking_mode", "must be 'chat' or 'thinking'")
    if not isinstance(drop_thinking, bool):
        raise _error("drop_thinking", "must be a boolean")
    if not isinstance(add_default_bos_token, bool):
        raise _error("add_default_bos_token", "must be a boolean")
    effort = reasoning_effort or "low"
    if effort not in REASONING_EFFORT_PROMPTS:
        raise _error(
            "reasoning_effort",
            f"must be one of {sorted(REASONING_EFFORT_PROMPTS)!r}",
        )

    normalized_context = _normalize_messages(context or [], "context")
    normalized_messages = _normalize_messages(messages, "messages")
    merged_context = _merge_tool_messages(normalized_context)
    merged_messages = _merge_tool_messages(normalized_messages)
    full_messages = _sort_tool_results(merged_context + merged_messages)

    effective_drop = drop_thinking
    if any(message.get("tools") for message in full_messages):
        effective_drop = False

    context_length = len(merged_context)
    if thinking_mode == "thinking" and effective_drop:
        full_messages = _drop_thinking_messages(full_messages)
        dropped_context = _drop_thinking_messages(merged_context)
        render_count = len(full_messages) - len(dropped_context)
        context_length = len(full_messages) - render_count
    else:
        render_count = len(merged_messages)

    prompt = BOS_TOKEN if add_default_bos_token and not normalized_context else ""
    for local_index in range(render_count):
        prompt += _render_message(
            context_length + local_index,
            full_messages,
            thinking_mode=thinking_mode,
            drop_thinking=effective_drop,
            reasoning_effort=effort,
        )
    return prompt


def _completion_error(index: int, detail: str) -> DeepSeekV4CompletionError:
    return DeepSeekV4CompletionError(f"completion byte {index}: {detail}")


def _expect_at(text: str, index: int, expected: str) -> int:
    if not text.startswith(expected, index):
        raise _completion_error(index, f"expected {expected!r}")
    return index + len(expected)


def _take_until(text: str, index: int, delimiter: str, label: str) -> tuple[str, int]:
    end = text.find(delimiter, index)
    if end < 0:
        raise _completion_error(index, f"missing {label}")
    return text[index:end], end + len(delimiter)


def _parse_tool_calls(text: str, index: int) -> tuple[list[dict[str, Any]], int]:
    index = _expect_at(text, index, ">\n")
    calls: list[dict[str, Any]] = []
    invoke_prefix = f'<{DSML_TOKEN}invoke name="'
    invoke_end = f"</{DSML_TOKEN}invoke>"
    parameter_prefix = f'<{DSML_TOKEN}parameter name="'
    parameter_end = f"</{DSML_TOKEN}parameter>"
    block_end = f"</{DSML_TOKEN}tool_calls>"

    while not text.startswith(block_end, index):
        index = _expect_at(text, index, invoke_prefix)
        name, index = _take_until(text, index, '">\n', "tool-name terminator")
        try:
            safe_name = _name(name, "completion.tool_name")
        except DeepSeekV4EncodingError as exc:
            raise _completion_error(index, str(exc)) from exc
        arguments: dict[str, Any] = {}
        while text.startswith(parameter_prefix, index):
            index += len(parameter_prefix)
            parameter_name, index = _take_until(
                text, index, '" string="', "parameter-name terminator"
            )
            try:
                safe_parameter_name = _name(
                    parameter_name, "completion.parameter_name"
                )
            except DeepSeekV4EncodingError as exc:
                raise _completion_error(index, str(exc)) from exc
            if safe_parameter_name in arguments:
                raise _completion_error(
                    index, f"duplicate parameter {safe_parameter_name!r}"
                )
            if text.startswith('true">', index):
                is_string = True
                index += len('true">')
            elif text.startswith('false">', index):
                is_string = False
                index += len('false">')
            else:
                raise _completion_error(index, "parameter string flag must be true or false")
            raw_value, index = _take_until(
                text, index, parameter_end, "parameter closing tag"
            )
            try:
                _reject_reserved(raw_value, "completion.parameter_value")
            except DeepSeekV4EncodingError as exc:
                raise _completion_error(index, str(exc)) from exc
            if is_string:
                value: Any = raw_value
            else:
                try:
                    value = json.loads(
                        raw_value,
                        object_pairs_hook=_pairs_without_duplicates,
                        parse_constant=_reject_constant,
                    )
                except (ValueError, json.JSONDecodeError) as exc:
                    raise _completion_error(
                        index, f"non-string parameter is not strict JSON: {exc}"
                    ) from exc
            arguments[safe_parameter_name] = value
            index = _expect_at(text, index, "\n")
        if not arguments and text.startswith("\n" + invoke_end, index):
            index += 1
        index = _expect_at(text, index, invoke_end)
        index = _expect_at(text, index, "\n")
        calls.append(
            {
                "type": "function",
                "function": {
                    "name": safe_name,
                    "arguments": json.dumps(
                        arguments, ensure_ascii=False, allow_nan=False
                    ),
                },
            }
        )
    if not calls:
        raise _completion_error(index, "tool_calls block must contain at least one call")
    index += len(block_end)
    return calls, index


def parse_message_from_completion_text(
    text: str, thinking_mode: str
) -> dict[str, Any]:
    """Parse one exact V4 assistant completion after the prompt transition token."""

    if not isinstance(text, str):
        raise _completion_error(0, "completion must be a string")
    if thinking_mode not in {"chat", "thinking"}:
        raise _completion_error(0, "thinking_mode must be 'chat' or 'thinking'")
    index = 0
    reasoning = ""
    if thinking_mode == "thinking":
        reasoning, index = _take_until(
            text, index, THINKING_END_TOKEN, "thinking closing token"
        )
    tool_start = f"\n\n<{DSML_TOKEN}tool_calls"
    eos_index = text.find(EOS_TOKEN, index)
    tool_index = text.find(tool_start, index)
    if tool_index >= 0 and (eos_index < 0 or tool_index < eos_index):
        content = text[index:tool_index]
        calls, index = _parse_tool_calls(text, tool_index + len(tool_start))
        index = _expect_at(text, index, EOS_TOKEN)
    else:
        if eos_index < 0:
            raise _completion_error(index, "missing EOS token")
        content = text[index:eos_index]
        calls = []
        index = eos_index + len(EOS_TOKEN)
    if index != len(text):
        raise _completion_error(index, "unexpected content after EOS")
    for label, value in (("content", content), ("reasoning_content", reasoning)):
        try:
            _reject_reserved(value, f"completion.{label}")
        except DeepSeekV4EncodingError as exc:
            raise _completion_error(0, str(exc)) from exc
    return {
        "role": "assistant",
        "content": content,
        "reasoning_content": reasoning,
        "tool_calls": calls,
    }


__all__ = [
    "ASSISTANT_TOKEN",
    "BOS_TOKEN",
    "DSML_TOKEN",
    "DeepSeekV4CompletionError",
    "DeepSeekV4EncodingError",
    "ENCODING_SOURCE_SHA256",
    "EOS_TOKEN",
    "LATEST_REMINDER_TOKEN",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "REASONING_EFFORT_PROMPTS",
    "TASK_TOKENS",
    "THINKING_END_TOKEN",
    "THINKING_START_TOKEN",
    "USER_TOKEN",
    "encode_messages",
    "parse_message_from_completion_text",
]
