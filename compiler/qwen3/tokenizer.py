"""Hash-bound local Qwen3 tokenizer and sandboxed chat-template boundary."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from compiler.ir.model import load_strict_json

from .constants import TARGET_CONTEXT_TOKENS, TOKENIZER_CONFIG_SHA256, TOKENIZER_SHA256


TOKENIZERS_VERSION = "0.22.2"
RESERVED_DELIMITERS = (
    "<|endoftext|>",
    "<|im_start|>",
    "<|im_end|>",
    "<|object_ref_start|>",
    "<|object_ref_end|>",
    "<|vision_start|>",
    "<|vision_end|>",
)


class Qwen3TokenizerError(RuntimeError):
    """Raised on an unpinned tokenizer or ambiguous host message boundary."""


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class Qwen3Tokenizer:
    """Load only the exact deployment tokenizer and enforce the 8K product limit."""

    def __init__(self, deployment: Path):
        root = Path(deployment).resolve()
        tokenizer_path = root / "tokenizer/tokenizer.json"
        config_path = root / "tokenizer/tokenizer_config.json"
        if _sha256_file(tokenizer_path) != TOKENIZER_SHA256:
            raise Qwen3TokenizerError("tokenizer.json differs from the pinned release")
        if _sha256_file(config_path) != TOKENIZER_CONFIG_SHA256:
            raise Qwen3TokenizerError(
                "tokenizer_config.json differs from the pinned release"
            )
        try:
            observed_version = importlib.metadata.version("tokenizers")
        except importlib.metadata.PackageNotFoundError as exc:
            raise Qwen3TokenizerError("tokenizers is not installed") from exc
        if observed_version != TOKENIZERS_VERSION:
            raise Qwen3TokenizerError(
                f"tokenizers {observed_version} is unsupported; expected {TOKENIZERS_VERSION}"
            )
        try:
            from tokenizers import Tokenizer

            self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        except Exception as exc:
            raise Qwen3TokenizerError(f"cannot load pinned tokenizer: {exc}") from exc
        try:
            self.config = load_strict_json(config_path)
        except (OSError, ValueError) as exc:
            raise Qwen3TokenizerError(f"invalid tokenizer config: {exc}") from exc
        template = self.config.get("chat_template")
        if not isinstance(template, str) or not template:
            raise Qwen3TokenizerError("tokenizer config lacks its chat template")
        self.chat_template = template
        expected_tokens = {
            "<|endoftext|>": 151643,
            "<|im_start|>": 151644,
            "<|im_end|>": 151645,
            "<think>": 151667,
            "</think>": 151668,
        }
        observed_tokens = {
            token: self._tokenizer.token_to_id(token) for token in expected_tokens
        }
        if observed_tokens != expected_tokens:
            raise Qwen3TokenizerError("Qwen3 protocol token IDs differ")
        if (
            self._tokenizer.get_vocab_size(with_added_tokens=False) != 151643
            or self._tokenizer.get_vocab_size(with_added_tokens=True) != 151669
        ):
            raise Qwen3TokenizerError("Qwen3 tokenizer vocabulary size differs")

    @staticmethod
    def _validate_messages(
        messages: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        if (
            isinstance(messages, (str, bytes))
            or not isinstance(messages, Sequence)
            or not messages
        ):
            raise Qwen3TokenizerError("messages must be a nonempty sequence")
        result: list[dict[str, Any]] = []
        allowed = {"role", "content", "reasoning_content", "tool_calls"}
        for index, raw in enumerate(messages):
            if not isinstance(raw, Mapping):
                raise Qwen3TokenizerError(f"message {index} must be an object")
            unknown = sorted(set(raw) - allowed)
            if unknown or set(raw) < {"role", "content"}:
                raise Qwen3TokenizerError(
                    f"message {index} fields differ: unknown={unknown}"
                )
            role = raw["role"]
            content = raw["content"]
            if role not in {"system", "user", "assistant", "tool"}:
                raise Qwen3TokenizerError(
                    f"message {index} has unsupported role {role!r}"
                )
            if not isinstance(content, str):
                raise Qwen3TokenizerError(f"message {index} content must be text")
            if any(delimiter in content for delimiter in RESERVED_DELIMITERS):
                raise Qwen3TokenizerError(
                    f"message {index} injects a reserved delimiter"
                )
            item = dict(raw)
            reasoning = item.get("reasoning_content")
            if reasoning is not None and not isinstance(reasoning, str):
                raise Qwen3TokenizerError(
                    f"message {index} reasoning_content must be text"
                )
            tool_calls = item.get("tool_calls")
            if tool_calls is not None:
                try:
                    json.dumps(tool_calls, allow_nan=False)
                except (TypeError, ValueError) as exc:
                    raise Qwen3TokenizerError(
                        f"message {index} tool_calls are not JSON"
                    ) from exc
            item.setdefault("reasoning_content", None)
            item.setdefault("tool_calls", [])
            result.append(item)
        return result

    def encode(self, text: str) -> list[int]:
        if not isinstance(text, str):
            raise Qwen3TokenizerError("text must be a string")
        ids = self._tokenizer.encode(text, add_special_tokens=False).ids
        if len(ids) > TARGET_CONTEXT_TOKENS:
            raise Qwen3TokenizerError(
                "encoded text exceeds the 8,000-token product limit"
            )
        return ids

    def render_chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        add_generation_prompt: bool = True,
        enable_thinking: bool = True,
    ) -> str:
        validated = self._validate_messages(messages)
        if tools is not None:
            if isinstance(tools, (str, bytes)) or not isinstance(tools, Sequence):
                raise Qwen3TokenizerError("tools must be an array")
            try:
                json.dumps(list(tools), allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise Qwen3TokenizerError("tools are not strict JSON") from exc
        try:
            from jinja2 import StrictUndefined
            from jinja2.sandbox import SandboxedEnvironment

            environment = SandboxedEnvironment(
                undefined=StrictUndefined,
                trim_blocks=False,
                lstrip_blocks=False,
                autoescape=False,
            )
            template = environment.from_string(self.chat_template)
            return template.render(
                messages=validated,
                tools=None if tools is None else list(tools),
                add_generation_prompt=bool(add_generation_prompt),
                enable_thinking=bool(enable_thinking),
            )
        except Exception as exc:
            raise Qwen3TokenizerError(f"chat template rendering failed: {exc}") from exc

    def encode_chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        add_generation_prompt: bool = True,
        enable_thinking: bool = True,
    ) -> list[int]:
        return self.encode(
            self.render_chat(
                messages,
                tools=tools,
                add_generation_prompt=add_generation_prompt,
                enable_thinking=enable_thinking,
            )
        )

    def decode(self, ids: Sequence[int], *, skip_special_tokens: bool = False) -> str:
        if isinstance(ids, (str, bytes)) or not isinstance(ids, Sequence):
            raise Qwen3TokenizerError("token IDs must be a sequence")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in ids):
            raise Qwen3TokenizerError("token IDs must be integers")
        tokenizer_size = self._tokenizer.get_vocab_size(with_added_tokens=True)
        if any(item < 0 or item >= tokenizer_size for item in ids):
            raise Qwen3TokenizerError(
                "cannot decode a padded output-head ID absent from the tokenizer"
            )
        try:
            return self._tokenizer.decode(
                list(ids), skip_special_tokens=skip_special_tokens
            )
        except Exception as exc:
            raise Qwen3TokenizerError(f"token decode failed: {exc}") from exc


__all__ = ["Qwen3Tokenizer", "Qwen3TokenizerError", "TOKENIZERS_VERSION"]
