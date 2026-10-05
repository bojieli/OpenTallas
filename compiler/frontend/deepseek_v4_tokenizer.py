"""Hash-verified, local-only tokenizer boundary for DeepSeek V4.

The official tokenizer is data, not remote Python. This module accepts only the
two byte-exact tokenizer files named by the immutable checkpoint source, loads
the Rust ``tokenizers`` implementation from local bytes, verifies its complete
vocabulary shape and protocol-token IDs, and runs independent golden probes
before exposing encode/decode operations.

The pinned identities below are one tokenizer, and both released DeepSeek-V4
snapshots carry it: ``tokenizer.json`` and ``tokenizer_config.json`` have the
same SHA-256 in the Flash and Pro snapshots and are byte-identical under
``cmp``. ``release`` therefore selects which checkpoint source authenticates
the files - the repository and revision differ - and not which bytes are
expected. A release whose record named different tokenizer digests would be a
different tokenizer than the one verified here, so the loader refuses it rather
than verifying the wrong pin.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
import hashlib
from importlib import metadata
import json
from pathlib import Path
from typing import Any

from compiler.frontend.checkpoint import CheckpointError, load_checkpoint_source
from compiler.frontend.deepseek_v4_encoding import (
    ASSISTANT_TOKEN,
    BOS_TOKEN,
    DSML_TOKEN,
    EOS_TOKEN,
    LATEST_REMINDER_TOKEN,
    TASK_TOKENS,
    THINKING_END_TOKEN,
    THINKING_START_TOKEN,
    USER_TOKEN,
    encode_messages,
)
from compiler.frontend.deepseek_v4_releases import (
    DeepSeekV4Release,
    resolve_release,
)
from compiler.ir.model import canonical_json_bytes


TOKENIZER_FILENAME = "tokenizer.json"
TOKENIZER_CONFIG_FILENAME = "tokenizer_config.json"
TOKENIZER_SHA256 = "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf"
TOKENIZER_SIZE_BYTES = 6_367_146
TOKENIZER_CONFIG_SHA256 = (
    "6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547"
)
TOKENIZER_CONFIG_SIZE_BYTES = 801
TOKENIZERS_RUNTIME_VERSION = "0.22.2"
MODEL_MAX_LENGTH = 1_048_576
BASE_VOCAB_SIZE = 128_000
VOCAB_SIZE = 129_280
BOS_TOKEN_ID = 0
EOS_TOKEN_ID = 1
PAD_TOKEN_ID = 1

DEFAULT_MODEL_ID = "deepseek-v4-flash-0731"
DEFAULT_SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "models"
    / DEFAULT_MODEL_ID
    / "checkpoint_source.json"
)

PROTOCOL_TOKEN_IDS = {
    "assistant": (ASSISTANT_TOKEN, 128_804),
    "authority_task": (TASK_TOKENS["authority"], 128_831),
    "begin_of_sentence": (BOS_TOKEN, BOS_TOKEN_ID),
    "domain_task": (TASK_TOKENS["domain"], 128_832),
    "dsml": (DSML_TOKEN, 128_825),
    "end_of_sentence": (EOS_TOKEN, EOS_TOKEN_ID),
    "latest_reminder": (LATEST_REMINDER_TOKEN, 128_828),
    "query_task": (TASK_TOKENS["query"], 128_830),
    "read_url_task": (TASK_TOKENS["read_url"], 128_845),
    "search_action_task": (TASK_TOKENS["action"], 128_829),
    "thinking_end": (THINKING_END_TOKEN, 128_822),
    "thinking_start": (THINKING_START_TOKEN, 128_821),
    "title_task": (TASK_TOKENS["title"], 128_836),
    "user": (USER_TOKEN, 128_803),
}

_EXPECTED_CONFIG = {
    "add_bos_token": False,
    "add_eos_token": False,
    "bos_token": {
        "__type": "AddedToken",
        "content": BOS_TOKEN,
        "lstrip": False,
        "normalized": True,
        "rstrip": False,
        "single_word": False,
    },
    "clean_up_tokenization_spaces": False,
    "eos_token": {
        "__type": "AddedToken",
        "content": EOS_TOKEN,
        "lstrip": False,
        "normalized": True,
        "rstrip": False,
        "single_word": False,
    },
    "legacy": True,
    "model_max_length": MODEL_MAX_LENGTH,
    "pad_token": {
        "__type": "AddedToken",
        "content": EOS_TOKEN,
        "lstrip": False,
        "normalized": True,
        "rstrip": False,
        "single_word": False,
    },
    "sp_model_kwargs": {},
    "unk_token": None,
    "tokenizer_class": "PreTrainedTokenizerFast",
}

_PROBES: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("", ()),
    (
        "Hello, world! 123\nsecond line",
        (19_923, 14, 2_058, 3, 223, 6_895, 201, 10_930, 2_562),
    ),
    (
        "你好，世界！ Καλημέρα κόσμε 🌍",
        (
            30_594,
            303,
            3_427,
            1_175,
            51_901,
            25_696,
            29_537,
            11_983,
            122_189,
            2_781,
            30_619,
            73_369,
            238,
        ),
    ),
    (
        (
            f"{BOS_TOKEN}{USER_TOKEN}question{ASSISTANT_TOKEN}"
            f"{THINKING_START_TOKEN}reason{THINKING_END_TOKEN}answer{EOS_TOKEN}"
        ),
        (0, 128_803, 20_072, 128_804, 128_821, 86_512, 128_822, 19_995, 1),
    ),
    (
        (
            f"{DSML_TOKEN}{TASK_TOKENS['action']}{TASK_TOKENS['query']}"
            f"{TASK_TOKENS['authority']}{TASK_TOKENS['domain']}"
            f"{TASK_TOKENS['title']}{TASK_TOKENS['read_url']}"
            f"{LATEST_REMINDER_TOKEN}"
        ),
        (128_825, 128_829, 128_830, 128_831, 128_832, 128_836, 128_845, 128_828),
    ),
)
_VERIFIED_CONSTRUCTION_KEY = object()


class DeepSeekV4TokenizerError(RuntimeError):
    """Raised when tokenizer identity or runtime behavior is not exact."""


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4TokenizerError(
                    f"{label} contains duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise DeepSeekV4TokenizerError(
            f"{label} contains non-finite JSON number {token!r}"
        )

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4TokenizerError(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DeepSeekV4TokenizerError(f"{label} must contain one JSON object")
    return value


def _expected_file(source: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    records = [
        record for record in source["expected_files"] if record["path"] == name
    ]
    if len(records) != 1:
        raise DeepSeekV4TokenizerError(
            f"checkpoint source must contain exactly one {name!r} record"
        )
    return records[0]


def _validate_release(release: DeepSeekV4Release) -> None:
    """Refuse a release whose record names a tokenizer this module has not pinned."""

    identity = (release.tokenizer_sha256, release.tokenizer_config_sha256)
    if identity != (TOKENIZER_SHA256, TOKENIZER_CONFIG_SHA256):
        raise DeepSeekV4TokenizerError(
            f"{release.model_id} pins tokenizer identity {identity!r}, which "
            f"is not the one this module verifies "
            f"({(TOKENIZER_SHA256, TOKENIZER_CONFIG_SHA256)!r}); its vocabulary "
            "shape, protocol-token IDs and golden probes would have to be "
            "established before it could be loaded here"
        )


def _validate_source(
    source: Mapping[str, Any], release: DeepSeekV4Release
) -> None:
    if source["repository"] != release.repository:
        raise DeepSeekV4TokenizerError(
            f"tokenizer source repository is {source['repository']!r}, "
            f"expected {release.repository!r}"
        )
    if source["revision"] != release.revision:
        raise DeepSeekV4TokenizerError(
            f"tokenizer source revision is {source['revision']!r}, "
            f"expected {release.revision!r}"
        )
    if source["remote_code_policy"] != "disabled":
        raise DeepSeekV4TokenizerError(
            "official tokenizer requires remote_code_policy='disabled'"
        )
    expected = {
        TOKENIZER_FILENAME: (TOKENIZER_SIZE_BYTES, TOKENIZER_SHA256),
        TOKENIZER_CONFIG_FILENAME: (
            TOKENIZER_CONFIG_SIZE_BYTES,
            TOKENIZER_CONFIG_SHA256,
        ),
    }
    for name, identity in expected.items():
        record = _expected_file(source, name)
        observed = (record["size_bytes"], record["sha256"])
        if observed != identity:
            raise DeepSeekV4TokenizerError(
                f"checkpoint source {name!r} identity is {observed!r}, "
                f"expected {identity!r}"
            )


def _read_verified_file(
    snapshot: Path, name: str, expected_size: int, expected_sha256: str
) -> bytes:
    path = snapshot / name
    if not path.is_file():
        raise DeepSeekV4TokenizerError(
            f"local checkpoint snapshot is missing {name!r}"
        )
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                if size > expected_size:
                    raise DeepSeekV4TokenizerError(
                        f"{name!r} exceeds pinned size {expected_size}"
                    )
                digest.update(chunk)
                chunks.append(chunk)
    except OSError as exc:
        raise DeepSeekV4TokenizerError(f"cannot read local {name!r}: {exc}") from exc
    observed_sha256 = digest.hexdigest()
    if size != expected_size:
        raise DeepSeekV4TokenizerError(
            f"{name!r} size is {size}, expected {expected_size}"
        )
    if observed_sha256 != expected_sha256:
        raise DeepSeekV4TokenizerError(
            f"{name!r} SHA-256 is {observed_sha256}, expected {expected_sha256}"
        )
    return b"".join(chunks)


def _validate_config(config: Mapping[str, Any]) -> None:
    if config != _EXPECTED_CONFIG:
        differing = sorted(
            key
            for key in set(config) | set(_EXPECTED_CONFIG)
            if config.get(key) != _EXPECTED_CONFIG.get(key)
        )
        raise DeepSeekV4TokenizerError(
            f"tokenizer_config.json semantics differ at keys {differing!r}"
        )


def _integer_id(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DeepSeekV4TokenizerError(f"{label} must be a nonnegative integer")
    return value


def _validate_payload_structure(payload: Mapping[str, Any]) -> None:
    expected_top_keys = {
        "added_tokens",
        "decoder",
        "model",
        "normalizer",
        "padding",
        "post_processor",
        "pre_tokenizer",
        "truncation",
        "version",
    }
    if set(payload) != expected_top_keys:
        raise DeepSeekV4TokenizerError(
            "tokenizer.json has unexpected top-level structure"
        )
    if payload["version"] != "1.0":
        raise DeepSeekV4TokenizerError("tokenizer.json version must be '1.0'")
    if payload["truncation"] is not None or payload["padding"] is not None:
        raise DeepSeekV4TokenizerError(
            "tokenizer.json must not apply implicit truncation or padding"
        )

    model = payload["model"]
    if not isinstance(model, dict):
        raise DeepSeekV4TokenizerError("tokenizer model must be an object")
    model_controls = {
        "type": "BPE",
        "dropout": None,
        "unk_token": None,
        "continuing_subword_prefix": None,
        "end_of_word_suffix": None,
        "fuse_unk": False,
        "byte_fallback": False,
    }
    if any(model.get(key) != value for key, value in model_controls.items()):
        raise DeepSeekV4TokenizerError("tokenizer BPE controls differ from the pin")
    vocab = model.get("vocab")
    if not isinstance(vocab, dict) or len(vocab) != BASE_VOCAB_SIZE:
        raise DeepSeekV4TokenizerError(
            f"base vocabulary must contain {BASE_VOCAB_SIZE} entries"
        )
    if not all(isinstance(token, str) for token in vocab):
        raise DeepSeekV4TokenizerError("base vocabulary tokens must be strings")
    vocab_ids = [_integer_id(value, f"vocab[{token!r}]") for token, value in vocab.items()]
    if set(vocab_ids) != set(range(BASE_VOCAB_SIZE)):
        raise DeepSeekV4TokenizerError(
            "base vocabulary IDs must be a contiguous 0..127999 permutation"
        )
    merges = model.get("merges")
    if not isinstance(merges, list) or len(merges) != 127_741:
        raise DeepSeekV4TokenizerError(
            "BPE merge table must contain exactly 127741 entries"
        )

    added = payload["added_tokens"]
    if not isinstance(added, list) or len(added) != 1_283:
        raise DeepSeekV4TokenizerError(
            "tokenizer must contain exactly 1283 added-token records"
        )
    added_ids: set[int] = set()
    added_contents: dict[str, int] = {}
    for index, raw_record in enumerate(added):
        if not isinstance(raw_record, dict):
            raise DeepSeekV4TokenizerError(
                f"added_tokens[{index}] must be an object"
            )
        expected_keys = {
            "content",
            "id",
            "lstrip",
            "normalized",
            "rstrip",
            "single_word",
            "special",
        }
        if set(raw_record) != expected_keys:
            raise DeepSeekV4TokenizerError(
                f"added_tokens[{index}] has unexpected fields"
            )
        token_id = _integer_id(raw_record["id"], f"added_tokens[{index}].id")
        content = raw_record["content"]
        if not isinstance(content, str) or not content:
            raise DeepSeekV4TokenizerError(
                f"added_tokens[{index}].content must be a non-empty string"
            )
        if token_id in added_ids or content in added_contents:
            raise DeepSeekV4TokenizerError(
                f"added_tokens[{index}] duplicates an ID or content"
            )
        for flag in ("lstrip", "normalized", "rstrip", "single_word", "special"):
            if not isinstance(raw_record[flag], bool):
                raise DeepSeekV4TokenizerError(
                    f"added_tokens[{index}].{flag} must be a boolean"
                )
        added_ids.add(token_id)
        added_contents[content] = token_id
    expected_added_ids = {0, 1, 2, *range(BASE_VOCAB_SIZE, VOCAB_SIZE)}
    if added_ids != expected_added_ids:
        raise DeepSeekV4TokenizerError(
            "added-token IDs differ from 0,1,2 plus contiguous 128000..129279"
        )
    for label, (token, expected_id) in PROTOCOL_TOKEN_IDS.items():
        if added_contents.get(token) != expected_id:
            raise DeepSeekV4TokenizerError(
                f"protocol token {label!r} has ID {added_contents.get(token)!r}, "
                f"expected {expected_id}"
            )


def _runtime_version() -> str:
    try:
        version = metadata.version("tokenizers")
    except metadata.PackageNotFoundError as exc:
        raise DeepSeekV4TokenizerError(
            "tokenizers is required; install the pinned compiler dependency"
        ) from exc
    if version != TOKENIZERS_RUNTIME_VERSION:
        raise DeepSeekV4TokenizerError(
            f"tokenizers runtime is {version!r}, expected "
            f"{TOKENIZERS_RUNTIME_VERSION!r}"
        )
    return version


def _load_backend(payload: bytes) -> Any:
    _runtime_version()
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:  # pragma: no cover - metadata check handles normal absence
        raise DeepSeekV4TokenizerError("cannot import tokenizers runtime") from exc
    try:
        return Tokenizer.from_str(payload.decode("utf-8"))
    except Exception as exc:
        raise DeepSeekV4TokenizerError(
            f"tokenizers runtime rejected pinned tokenizer.json: {exc}"
        ) from exc


def _ids_digest(ids: Sequence[int]) -> str:
    digest = hashlib.sha256()
    for token_id in ids:
        digest.update(token_id.to_bytes(4, "little", signed=False))
    return digest.hexdigest()


def _validate_backend(backend: Any) -> list[dict[str, Any]]:
    if backend.get_vocab_size(with_added_tokens=False) != BASE_VOCAB_SIZE:
        raise DeepSeekV4TokenizerError("runtime base-vocabulary size differs")
    if backend.get_vocab_size(with_added_tokens=True) != VOCAB_SIZE:
        raise DeepSeekV4TokenizerError("runtime total-vocabulary size differs")
    for label, (token, expected_id) in PROTOCOL_TOKEN_IDS.items():
        token_id = backend.token_to_id(token)
        encoded = backend.encode(token, add_special_tokens=False).ids
        if token_id != expected_id or encoded != [expected_id]:
            raise DeepSeekV4TokenizerError(
                f"runtime protocol token {label!r} maps to "
                f"{token_id!r}/{encoded!r}, expected {expected_id}"
            )
        if backend.decode([expected_id], skip_special_tokens=False) != token:
            raise DeepSeekV4TokenizerError(
                f"runtime protocol token {label!r} does not decode exactly"
            )

    reports: list[dict[str, Any]] = []
    for index, (text, expected_ids) in enumerate(_PROBES):
        observed = tuple(backend.encode(text, add_special_tokens=False).ids)
        if observed != expected_ids:
            raise DeepSeekV4TokenizerError(
                f"runtime tokenizer probe {index} differs: "
                f"{observed!r} versus {expected_ids!r}"
            )
        decoded = backend.decode(list(observed), skip_special_tokens=False)
        if decoded != text:
            raise DeepSeekV4TokenizerError(
                f"runtime tokenizer probe {index} is not decode-stable"
            )
        reports.append(
            {
                "id": f"probe-{index}",
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "token_count": len(observed),
                "token_ids_sha256": _ids_digest(observed),
            }
        )
    return reports


class VerifiedDeepSeekV4Tokenizer:
    """A tokenizer instance whose local bytes and runtime behavior were verified."""

    def __init__(
        self,
        backend: Any,
        validation_report: dict[str, Any],
        *,
        _construction_key: object | None = None,
    ):
        if _construction_key is not _VERIFIED_CONSTRUCTION_KEY:
            raise DeepSeekV4TokenizerError(
                "verified tokenizer instances must be created by the local loader"
            )
        self._backend = backend
        self._validation_report = copy.deepcopy(validation_report)

    @property
    def bos_token_id(self) -> int:
        return BOS_TOKEN_ID

    @property
    def eos_token_id(self) -> int:
        return EOS_TOKEN_ID

    @property
    def pad_token_id(self) -> int:
        return PAD_TOKEN_ID

    @property
    def model_max_length(self) -> int:
        return MODEL_MAX_LENGTH

    @property
    def vocab_size(self) -> int:
        return VOCAB_SIZE

    @property
    def validation_report(self) -> dict[str, Any]:
        return copy.deepcopy(self._validation_report)

    def encode(self, text: str, *, enforce_max_length: bool = True) -> list[int]:
        if not isinstance(text, str):
            raise DeepSeekV4TokenizerError("text to encode must be a string")
        if not isinstance(enforce_max_length, bool):
            raise DeepSeekV4TokenizerError("enforce_max_length must be a boolean")
        try:
            ids = list(
                self._backend.encode(text, add_special_tokens=False).ids
            )
        except Exception as exc:
            raise DeepSeekV4TokenizerError(f"tokenization failed: {exc}") from exc
        if enforce_max_length and len(ids) > MODEL_MAX_LENGTH:
            raise DeepSeekV4TokenizerError(
                f"encoded text has {len(ids)} tokens, exceeding "
                f"model_max_length={MODEL_MAX_LENGTH}"
            )
        self._validate_ids(ids)
        return ids

    def encode_prompt(
        self,
        messages: list[dict[str, Any]],
        thinking_mode: str,
        **encoding_options: Any,
    ) -> tuple[str, list[int]]:
        prompt = encode_messages(
            messages, thinking_mode=thinking_mode, **encoding_options
        )
        return prompt, self.encode(prompt)

    def decode(
        self, token_ids: Sequence[int], *, skip_special_tokens: bool = False
    ) -> str:
        if not isinstance(skip_special_tokens, bool):
            raise DeepSeekV4TokenizerError("skip_special_tokens must be a boolean")
        if isinstance(token_ids, (str, bytes)) or not isinstance(token_ids, Sequence):
            raise DeepSeekV4TokenizerError("token_ids must be an integer sequence")
        ids = list(token_ids)
        self._validate_ids(ids)
        try:
            return self._backend.decode(
                ids, skip_special_tokens=skip_special_tokens
            )
        except Exception as exc:
            raise DeepSeekV4TokenizerError(f"token decoding failed: {exc}") from exc

    def batch_decode(
        self,
        batches: Sequence[Sequence[int]],
        *,
        skip_special_tokens: bool = False,
    ) -> list[str]:
        if isinstance(batches, (str, bytes)) or not isinstance(batches, Sequence):
            raise DeepSeekV4TokenizerError(
                "batches must be a sequence of token-ID sequences"
            )
        return [
            self.decode(ids, skip_special_tokens=skip_special_tokens)
            for ids in batches
        ]

    @staticmethod
    def _validate_ids(ids: Sequence[Any]) -> None:
        for index, token_id in enumerate(ids):
            if (
                isinstance(token_id, bool)
                or not isinstance(token_id, int)
                or not 0 <= token_id < VOCAB_SIZE
            ):
                raise DeepSeekV4TokenizerError(
                    f"token_ids[{index}]={token_id!r} is outside 0..{VOCAB_SIZE - 1}"
                )


def load_verified_deepseek_v4_tokenizer(
    snapshot: Path,
    source_path: Path | None = None,
    *,
    release: str | DeepSeekV4Release = DEFAULT_MODEL_ID,
) -> VerifiedDeepSeekV4Tokenizer:
    """Load the exact official tokenizer from a verified local snapshot.

    No network client, Transformers auto-loader, or checkpoint Python is invoked.
    A tokenizer-only snapshot containing the two pinned files is sufficient.

    ``release`` names which DeepSeek-V4 release's checkpoint source
    authenticates the snapshot; it defaults to Flash, and ``source_path``
    defaults to that release's committed ``checkpoint_source.json``.
    """

    record = resolve_release(release)
    _validate_release(record)
    if source_path is None:
        source_path = record.checkpoint_source_path
    try:
        snapshot = Path(snapshot)
        source_path = Path(source_path)
    except TypeError as exc:
        raise DeepSeekV4TokenizerError(
            "snapshot and source_path must be filesystem paths"
        ) from exc
    if not snapshot.is_dir():
        raise DeepSeekV4TokenizerError(
            f"local tokenizer snapshot is not a directory: {snapshot}"
        )
    try:
        source = load_checkpoint_source(source_path)
    except CheckpointError as exc:
        raise DeepSeekV4TokenizerError(
            f"cannot validate tokenizer checkpoint source: {exc}"
        ) from exc
    _validate_source(source, record)
    tokenizer_bytes = _read_verified_file(
        snapshot, TOKENIZER_FILENAME, TOKENIZER_SIZE_BYTES, TOKENIZER_SHA256
    )
    config_bytes = _read_verified_file(
        snapshot,
        TOKENIZER_CONFIG_FILENAME,
        TOKENIZER_CONFIG_SIZE_BYTES,
        TOKENIZER_CONFIG_SHA256,
    )
    config = _strict_json(config_bytes, TOKENIZER_CONFIG_FILENAME)
    payload = _strict_json(tokenizer_bytes, TOKENIZER_FILENAME)
    _validate_config(config)
    _validate_payload_structure(payload)
    backend = _load_backend(tokenizer_bytes)
    probes = _validate_backend(backend)

    report: dict[str, Any] = {
        "schema": "opentallas.deepseek_v4_tokenizer_validation.v1",
        "source": {
            "repository": record.repository,
            "revision": record.revision,
            "remote_code_policy": "disabled",
            "tokenizer_config_sha256": TOKENIZER_CONFIG_SHA256,
            "tokenizer_config_size_bytes": TOKENIZER_CONFIG_SIZE_BYTES,
            "tokenizer_sha256": TOKENIZER_SHA256,
            "tokenizer_size_bytes": TOKENIZER_SIZE_BYTES,
        },
        "runtime": {
            "implementation": "tokenizers",
            "version": TOKENIZERS_RUNTIME_VERSION,
        },
        "contract": {
            "add_bos_token": False,
            "add_eos_token": False,
            "base_vocab_size": BASE_VOCAB_SIZE,
            "bos_token_id": BOS_TOKEN_ID,
            "eos_token_id": EOS_TOKEN_ID,
            "model_max_length": MODEL_MAX_LENGTH,
            "pad_token_id": PAD_TOKEN_ID,
            "protocol_token_ids": {
                label: token_id
                for label, (_, token_id) in sorted(PROTOCOL_TOKEN_IDS.items())
            },
            "total_vocab_size": VOCAB_SIZE,
        },
        "probes": probes,
        "status": "verified_official_local_tokenizer",
    }
    report["validation_id"] = hashlib.sha256(canonical_json_bytes(report)).hexdigest()
    return VerifiedDeepSeekV4Tokenizer(
        backend, report, _construction_key=_VERIFIED_CONSTRUCTION_KEY
    )


__all__ = [
    "BASE_VOCAB_SIZE",
    "BOS_TOKEN_ID",
    "DEFAULT_MODEL_ID",
    "DeepSeekV4TokenizerError",
    "EOS_TOKEN_ID",
    "MODEL_MAX_LENGTH",
    "PAD_TOKEN_ID",
    "PROTOCOL_TOKEN_IDS",
    "TOKENIZER_CONFIG_SHA256",
    "TOKENIZER_SHA256",
    "TOKENIZERS_RUNTIME_VERSION",
    "VOCAB_SIZE",
    "VerifiedDeepSeekV4Tokenizer",
    "load_verified_deepseek_v4_tokenizer",
]
