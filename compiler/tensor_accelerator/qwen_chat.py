"""Authenticated Qwen3 tokenizer and official chat-template boundary.

This module is deliberately a host control-plane component.  It may render the
authenticated upstream chat template, tokenize text, and decode selected token
IDs; it never performs a model-forward operation.  Both ROM and HBM/SRAM
workloads are required to reproduce the records emitted here byte for byte.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined, __version__ as jinja_version
from jinja2.sandbox import SandboxedEnvironment
from tokenizers import Tokenizer, __version__ as tokenizers_version

from .common import ArtifactError, canonical_json_bytes, load_strict_json, sha256_file


TOKENIZERS_VERSION = "0.22.2"
JINJA_MINIMUM_VERSION = (3, 1)
MODEL_ID = "qwen3-8b"
MODEL_VOCABULARY_SIZE = 151_936
EXPLICIT_VOCABULARY_SIZE = 151_669
BASE_VOCABULARY_SIZE = 151_643
EOS_TOKEN_IDS = (151_645, 151_643)
EOS_TOKEN_STRINGS = ("<|im_end|>", "<|endoftext|>")
OFFICIAL_CHAT_TEMPLATE_SHA256 = (
    "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8"
)
SOURCE_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
SOURCE_FILES = {
    "config": {
        "path": "config.json",
        "sha256": "f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30",
        "size_bytes": 728,
    },
    "generation_config": {
        "path": "generation_config.json",
        "sha256": "2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2",
        "size_bytes": 239,
    },
    "tokenizer": {
        "path": "tokenizer.json",
        "sha256": "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
        "size_bytes": 11_422_654,
    },
    "tokenizer_config": {
        "path": "tokenizer_config.json",
        "sha256": "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
        "size_bytes": 9_732,
    },
}
RESERVED_DELIMITERS = (
    "<|endoftext|>",
    "<|im_start|>",
    "<|im_end|>",
    "<|object_ref_start|>",
    "<|object_ref_end|>",
    "<|vision_start|>",
    "<|vision_end|>",
)


class QwenChatError(ArtifactError):
    """Raised when Qwen chat/tokenizer inputs are unauthenticated or ambiguous."""


def _version_tuple(value: str) -> tuple[int, ...]:
    pieces: list[int] = []
    for piece in value.split("."):
        digits = "".join(character for character in piece if character.isdigit())
        if not digits:
            break
        pieces.append(int(digits))
    return tuple(pieces)


def _source_record(lock: Mapping[str, Any], logical_path: str) -> dict[str, Any]:
    records = [
        record
        for record in lock.get("files", [])
        if isinstance(record, Mapping) and record.get("path") == logical_path
    ]
    if len(records) != 1:
        raise QwenChatError(
            f"checkpoint lock must contain exactly one {logical_path!r} record"
        )
    record = dict(records[0])
    if set(record) != {"path", "sha256", "size_bytes"}:
        raise QwenChatError(f"checkpoint source {logical_path!r} fields differ")
    return record


def _validate_messages(
    messages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if (
        isinstance(messages, (str, bytes))
        or not isinstance(messages, Sequence)
        or not messages
    ):
        raise QwenChatError("messages must be a nonempty sequence")
    result: list[dict[str, Any]] = []
    allowed = {"role", "content", "reasoning_content", "tool_calls"}
    for index, raw in enumerate(messages):
        if not isinstance(raw, Mapping):
            raise QwenChatError(f"message {index} must be an object")
        unknown = sorted(set(raw) - allowed)
        if unknown or not {"role", "content"} <= set(raw):
            raise QwenChatError(
                f"message {index} fields differ: unknown={unknown}"
            )
        role = raw["role"]
        content = raw["content"]
        if role not in {"system", "user", "assistant", "tool"}:
            raise QwenChatError(f"message {index} has unsupported role {role!r}")
        if not isinstance(content, str):
            raise QwenChatError(f"message {index} content must be text")
        if any(delimiter in content for delimiter in RESERVED_DELIMITERS):
            raise QwenChatError(f"message {index} injects a reserved delimiter")
        item = dict(raw)
        reasoning = item.get("reasoning_content")
        if reasoning is not None and not isinstance(reasoning, str):
            raise QwenChatError(
                f"message {index} reasoning_content must be text"
            )
        calls = item.get("tool_calls")
        if calls is not None:
            try:
                json.dumps(calls, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise QwenChatError(
                    f"message {index} tool_calls are not strict JSON"
                ) from exc
        item.setdefault("reasoning_content", None)
        item.setdefault("tool_calls", [])
        result.append(item)
    return result


class QwenChatTokenizer:
    """Authenticate and reproduce the exact official Qwen3 chat boundary."""

    def __init__(self, snapshot: Path, checkpoint_lock: Mapping[str, Any]):
        root = Path(snapshot).resolve()
        if tokenizers_version != TOKENIZERS_VERSION:
            raise QwenChatError(
                f"tokenizers {tokenizers_version!r} differs from {TOKENIZERS_VERSION!r}"
            )
        if _version_tuple(jinja_version) < JINJA_MINIMUM_VERSION:
            raise QwenChatError(f"jinja2 {jinja_version!r} is unsupported")
        records: dict[str, dict[str, Any]] = {}
        values: dict[str, dict[str, Any]] = {}
        for key, expected in SOURCE_FILES.items():
            record = _source_record(checkpoint_lock, expected["path"])
            if record != expected:
                raise QwenChatError(f"checkpoint source {key!r} differs")
            path = root / expected["path"]
            try:
                digest, size = sha256_file(path)
            except OSError as exc:
                raise QwenChatError(f"cannot authenticate Qwen source {key}: {exc}") from exc
            if (digest, size) != (expected["sha256"], expected["size_bytes"]):
                raise QwenChatError(f"Qwen source {key!r} bytes differ")
            records[key] = dict(record)
            if key != "tokenizer":
                values[key] = load_strict_json(path)
        try:
            tokenizer = Tokenizer.from_file(str(root / SOURCE_FILES["tokenizer"]["path"]))
        except Exception as exc:
            raise QwenChatError(f"cannot load authenticated Qwen tokenizer: {exc}") from exc

        config = values["config"]
        generation = values["generation_config"]
        tokenizer_config = values["tokenizer_config"]
        template = tokenizer_config.get("chat_template")
        if (
            config.get("model_type") != "qwen3"
            or config.get("vocab_size") != MODEL_VOCABULARY_SIZE
            or config.get("bos_token_id") != 151_643
            or config.get("eos_token_id") != 151_645
            or generation.get("bos_token_id") != 151_643
            or generation.get("pad_token_id") != 151_643
            or generation.get("eos_token_id") != list(EOS_TOKEN_IDS)
            or tokenizer_config.get("eos_token") != EOS_TOKEN_STRINGS[0]
            or tokenizer_config.get("pad_token") != EOS_TOKEN_STRINGS[1]
            or not isinstance(template, str)
            or not template
            or hashlib.sha256(template.encode("utf-8")).hexdigest()
            != OFFICIAL_CHAT_TEMPLATE_SHA256
            or tokenizer.get_vocab_size(with_added_tokens=True)
            != EXPLICIT_VOCABULARY_SIZE
            or tokenizer.get_vocab_size(with_added_tokens=False)
            != BASE_VOCABULARY_SIZE
            or tuple(tokenizer.id_to_token(token) for token in EOS_TOKEN_IDS)
            != EOS_TOKEN_STRINGS
        ):
            raise QwenChatError(
                "model, generation, tokenizer, and chat-template boundaries differ"
            )
        expected_tokens = {
            "<|endoftext|>": 151_643,
            "<|im_start|>": 151_644,
            "<|im_end|>": 151_645,
            "<think>": 151_667,
            "</think>": 151_668,
        }
        if {
            token: tokenizer.token_to_id(token) for token in expected_tokens
        } != expected_tokens:
            raise QwenChatError("Qwen protocol token IDs differ")
        added = tokenizer.get_added_tokens_decoder()
        for token_id, content in zip(EOS_TOKEN_IDS, EOS_TOKEN_STRINGS, strict=True):
            token = added.get(token_id)
            if token is None or token.content != content or token.special is not True:
                raise QwenChatError(f"EOS token {token_id} is not a special token")

        self.root = root
        self.source_records = records
        self.chat_template = template
        self._tokenizer = tokenizer

    @property
    def tokenizer(self) -> Tokenizer:
        """Return the authenticated tokenizer for controlled evidence builders."""

        return self._tokenizer

    def render_chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        add_generation_prompt: bool = True,
        enable_thinking: bool = True,
    ) -> str:
        """Render the authenticated official template in a strict sandbox."""

        validated = _validate_messages(messages)
        if tools is not None:
            if isinstance(tools, (str, bytes)) or not isinstance(tools, Sequence):
                raise QwenChatError("tools must be an array")
            try:
                json.dumps(list(tools), allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise QwenChatError("tools are not strict JSON") from exc
        try:
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
            raise QwenChatError(f"chat template rendering failed: {exc}") from exc

    def encode(self, text: str) -> list[int]:
        if not isinstance(text, str):
            raise QwenChatError("text must be a string")
        try:
            return self._tokenizer.encode(text, add_special_tokens=False).ids
        except Exception as exc:
            raise QwenChatError(f"tokenization failed: {exc}") from exc

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
            raise QwenChatError("token IDs must be a sequence")
        if any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or not 0 <= token < EXPLICIT_VOCABULARY_SIZE
            for token in ids
        ):
            raise QwenChatError(
                "cannot decode an invalid or padded model-output token ID"
            )
        try:
            return self._tokenizer.decode(
                list(ids), skip_special_tokens=skip_special_tokens
            )
        except Exception as exc:
            raise QwenChatError(f"token decode failed: {exc}") from exc

    def prompt_record(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        enable_thinking: bool = True,
    ) -> dict[str, Any]:
        """Return text, IDs, and hashes for one governed assistant prompt."""

        text = self.render_chat(
            messages,
            tools=tools,
            add_generation_prompt=True,
            enable_thinking=enable_thinking,
        )
        token_ids = self.encode(text)
        if self.decode(token_ids, skip_special_tokens=False) != text:
            raise QwenChatError("rendered prompt does not round-trip exactly")
        return {
            "prompt_text": text,
            "prompt_text_utf8_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "prompt_token_count": len(token_ids),
            "prompt_token_ids": token_ids,
            "prompt_token_sha256": hashlib.sha256(
                canonical_json_bytes(token_ids)
            ).hexdigest(),
        }


__all__ = [
    "BASE_VOCABULARY_SIZE",
    "EOS_TOKEN_IDS",
    "EOS_TOKEN_STRINGS",
    "EXPLICIT_VOCABULARY_SIZE",
    "MODEL_VOCABULARY_SIZE",
    "OFFICIAL_CHAT_TEMPLATE_SHA256",
    "QwenChatError",
    "QwenChatTokenizer",
    "SOURCE_FILES",
    "SOURCE_REVISION",
    "TOKENIZERS_VERSION",
]
