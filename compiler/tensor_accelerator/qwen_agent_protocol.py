"""Strict Qwen3 bash-only agent protocol shared with the ROM workload."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from .common import ArtifactError, canonical_json_bytes, sha256_bytes


SYSTEM_PROMPT = (
    "You are a terminal task agent working inside an isolated container. Use the "
    "bash tool to inspect and modify only that container. When using a tool, emit "
    "only the official <tool_call> block. Verify your work with bash, then give a "
    "concise final answer."
)
BASH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Run a shell command inside the isolated TerminalBench task container."
        ),
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}
BASH_TOOL_SHA256 = sha256_bytes(canonical_json_bytes(BASH_TOOL))
_TOOL_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_THINK_BLOCK = re.compile(r"^\s*<think>\s*(.*?)\s*</think>\s*", re.DOTALL)


class QwenAgentProtocolError(ArtifactError):
    """Raised when assistant output is ambiguous or violates the frozen ABI."""


@dataclass(frozen=True)
class ParsedAssistantOutput:
    reasoning: str
    content: str
    calls: tuple[dict[str, Any], ...]


def _strict_json(text: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise QwenAgentProtocolError(f"duplicate JSON field {key!r}")
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise QwenAgentProtocolError(f"non-finite JSON value {token!r}")

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except QwenAgentProtocolError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise QwenAgentProtocolError(f"tool call is not strict JSON: {exc}") from exc


def _without_terminal_token(text: str) -> str:
    result = text
    for token in ("<|im_end|>", "<|endoftext|>"):
        if result.endswith(token):
            result = result[: -len(token)]
            break
    return result.rstrip()


def parse_assistant_output(text: str) -> ParsedAssistantOutput:
    """Parse official Qwen tool envelopes and fail closed on ambiguity."""

    if not isinstance(text, str):
        raise QwenAgentProtocolError("assistant output must be text")
    remainder = _without_terminal_token(text)
    reasoning = ""
    think = _THINK_BLOCK.match(remainder)
    if think is not None:
        reasoning = think.group(1).strip()
        remainder = remainder[think.end() :]
    elif "<think>" in remainder or "</think>" in remainder:
        raise QwenAgentProtocolError("assistant output has a malformed think block")

    blocks = list(_TOOL_BLOCK.finditer(remainder))
    if remainder.count("<tool_call>") != len(blocks) or remainder.count(
        "</tool_call>"
    ) != len(blocks):
        raise QwenAgentProtocolError(
            "assistant output has a malformed tool-call envelope"
        )
    if not blocks:
        if "<tool_call" in remainder or "</tool_call" in remainder:
            raise QwenAgentProtocolError("assistant output has an incomplete tool call")
        return ParsedAssistantOutput(reasoning, remainder.strip(), ())

    calls: list[dict[str, Any]] = []
    cursor = 0
    content_parts: list[str] = []
    for block in blocks:
        content_parts.append(remainder[cursor : block.start()])
        cursor = block.end()
        value = _strict_json(block.group(1))
        if not isinstance(value, dict) or set(value) != {"name", "arguments"}:
            raise QwenAgentProtocolError(
                "tool call must contain exactly name and arguments"
            )
        if value["name"] != "bash":
            raise QwenAgentProtocolError("only the bash tool is available")
        arguments = value["arguments"]
        if not isinstance(arguments, dict) or set(arguments) != {"command"}:
            raise QwenAgentProtocolError(
                "bash arguments must contain exactly the command field"
            )
        command = arguments["command"]
        if (
            not isinstance(command, str)
            or not command.strip()
            or "\x00" in command
            or len(command) > 8192
        ):
            raise QwenAgentProtocolError("bash command must be nonempty bounded text")
        calls.append({"name": "bash", "arguments": {"command": command}})
    content_parts.append(remainder[cursor:])
    content = "".join(content_parts).strip()
    if "<tool_call" in content or "</tool_call" in content:
        raise QwenAgentProtocolError("assistant output has nested tool-call markup")
    return ParsedAssistantOutput(reasoning, content, tuple(calls))


def assistant_message(parsed: ParsedAssistantOutput) -> dict[str, Any]:
    """Convert a parsed assistant turn into official-template message fields."""

    return {
        "role": "assistant",
        "content": parsed.content,
        "reasoning_content": parsed.reasoning,
        "tool_calls": [
            {
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": call["arguments"],
                },
            }
            for call in parsed.calls
        ],
    }


def tool_response(action: dict[str, Any]) -> str:
    """Render only the bounded public action fields into the next model turn."""

    required = {"exit_code", "stderr", "stdout", "timed_out", "truncated"}
    if not required <= set(action):
        raise QwenAgentProtocolError("bash action lacks public response fields")
    public = {key: action[key] for key in sorted(required)}
    try:
        return json.dumps(
            public,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise QwenAgentProtocolError(f"bash response is not strict JSON: {exc}") from exc


__all__ = [
    "BASH_TOOL",
    "BASH_TOOL_SHA256",
    "ParsedAssistantOutput",
    "QwenAgentProtocolError",
    "SYSTEM_PROMPT",
    "assistant_message",
    "parse_assistant_output",
    "tool_response",
]
