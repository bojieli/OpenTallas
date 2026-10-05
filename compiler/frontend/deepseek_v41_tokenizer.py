"""Hash-verified, local-only tokenizer boundary for DeepSeek-V4.1-Flash.

Why this exists as a sibling instead of a ``release=`` argument to
:mod:`compiler.frontend.deepseek_v4_tokenizer`
-----------------------------------------------------------------------
That module's docstring states the fact it was built on: the two DeepSeek-V4
releases ship *one* tokenizer, so ``release`` selects which checkpoint source
authenticates identical bytes.  V4.1 breaks that premise.  Its
``tokenizer.json`` has a different SHA-256 and a different length from V4's, so
the V4 loader refuses it by construction - correctly, because a loader that
verified the wrong pin would verify nothing.

What actually changed, and how this module proves it
---------------------------------------------------
The change is provably confined to nine *added-token contents* at nine
unchanged ids.  Everything a token id depends on is equal byte for byte between
the two files: ``model.vocab`` (128,000 entries), ``model.merges`` (127,741
entries), ``normalizer``, ``pre_tokenizer``, ``post_processor``, ``decoder``,
``version``, ``truncation`` and ``padding``.  :func:`_verify_added_token_delta`
requires exactly that, and requires every difference to be one of the nine
renames in :data:`ADDED_TOKEN_RENAMES` - so a tokenizer that changed a merge, a
vocabulary entry or a pre-tokenizer rule cannot reach the encode path even if
its digest were substituted for the one pinned here.

The nine renames are not asserted from the tokenizer alone.  Two of them are
corroborated by the release's own files, which is why they are named in the
table: ``128799`` becomes ``<｜System｜>``, the token the released
``encoding/encoding.py`` assigns to ``SYSTEM_SP_TOKEN`` for V4.1's
mid-conversation system messages; and ``129264`` becomes
``<｜deepseek_image｜>``, the id the released ``config.json`` names as
``image_token_id``.

One of the nine is more than a rename, and the table carries whole entries
rather than contents so that it cannot be missed: at ``128799`` V4.1 also flips
``normalized`` from false to true and ``special`` from **true to false**.  The
id still encodes to itself - :func:`_validate_backend` checks that - but
``<｜System｜>`` is not a *special* token in V4.1's file, so
``decode(skip_special_tokens=True)`` keeps it where V4 dropped the placeholder
that used to live there.  Any V4.1 consumer that strips specials to recover
user-visible text must treat that one id itself.

Two authorities, and neither one alone
-------------------------------------
``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`` section 13 gives the
release record and the committed ``checkpoint_source.json`` to WP-B, whose
checkpoint lock needs a complete 510 GB download.  This module therefore does
not *depend* on either, and does not ignore them:

1. a snapshot is bound to a revision by the **committed inventory**,
   ``data/inventory/deepseek-v4.1-flash.json``, which pins ``repo``,
   ``revision`` and ``config_sha256``.  A snapshot whose ``config.json`` does
   not hash to that digest is not the pinned V4.1 release, and that check needs
   nothing that is still downloading; and
2. every digest below is **confronted with the release record** the moment one
   resolves under :data:`MODEL_ID`.  :func:`release_record_pins` reads whatever
   of ``config_sha256``, ``tokenizer_sha256`` and ``tokenizer_config_sha256``
   the record carries and requires each to equal this module's pin, so the day
   WP-B's record lands is the day a disagreement becomes a failure rather than
   two independently plausible provenances.  A record that does not exist, or
   that does not carry a field, degrades the check and is recorded as having
   done so; it never relaxes one.

The structural proof above is what makes any of those digests mean something,
and it stands whichever authority supplied them.

The official tokenizer is data, not remote Python: only the two byte-checked
JSON files are read here.  The *prompt renderer* is a separate question -
V4.1's DSML grammar differs from V4's and this repository has no
reimplementation of it yet - so ``encode_prompt`` is not offered on this class.
A caller that needs a rendered prompt injects a renderer; see
``tools/build_deepseek_v41_workloads.py``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
import hashlib
from importlib import metadata
import json
from pathlib import Path
from typing import Any

from compiler.frontend.deepseek_v4_tokenizer import (
    BASE_VOCAB_SIZE,
    MODEL_MAX_LENGTH,
    PROTOCOL_TOKEN_IDS,
    TOKENIZER_CONFIG_FILENAME,
    TOKENIZER_CONFIG_SHA256,
    TOKENIZER_CONFIG_SIZE_BYTES,
    TOKENIZER_FILENAME,
    TOKENIZER_SHA256 as V4_TOKENIZER_SHA256,
    TOKENIZERS_RUNTIME_VERSION,
    VOCAB_SIZE,
)

REPO = Path(__file__).resolve().parents[2]

#: The model id every V4.1 artifact in this repository is filed under: the
#: basename of the committed profile and of the committed inventory.
MODEL_ID = "deepseek-v4.1-flash"

#: The committed analytical record that authenticates a snapshot until WP-B's
#: ``checkpoint_source.json`` exists.  It pins repo, revision and the released
#: ``config.json`` digest.
INVENTORY_PATH = REPO / "data" / "inventory" / f"{MODEL_ID}.json"

#: Measured on the delivered snapshot of the revision the inventory pins.  This
#: is a measurement of released bytes, not a lock: the checkpoint lock is WP-B's
#: and needs the whole download.  Substituting a different file for this digest
#: does not get past :func:`_verify_added_token_delta`.
TOKENIZER_SHA256 = "c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b"
TOKENIZER_SIZE_BYTES = 6_367_257

#: V4.1 ships V4's ``tokenizer_config.json`` unchanged - equal SHA-256, equal
#: length - so this boundary reuses the V4 module's pin rather than restating
#: it, and a drift in either file shows up as a disagreement between them.
TOKENIZER_CONFIG_SHA256 = TOKENIZER_CONFIG_SHA256
TOKENIZER_CONFIG_SIZE_BYTES = TOKENIZER_CONFIG_SIZE_BYTES

def _added(content: str, *, normalized: bool = False, special: bool = False):
    """One ``added_tokens`` entry, minus its id, in the released field order."""

    return {
        "content": content,
        "single_word": False,
        "lstrip": False,
        "rstrip": False,
        "normalized": normalized,
        "special": special,
    }


#: ``id -> {"v4": entry, "v4.1": entry}`` without the id.  The complete set of
#: differences between the two releases' ``added_tokens``; every other entry is
#: equal.  Eight are pure renames.  ``128799`` also flips ``normalized`` and
#: ``special``, which is why whole entries are pinned and not just contents.
ADDED_TOKEN_DELTA: Mapping[int, Mapping[str, Mapping[str, Any]]] = {
    128_799: {
        "v4": _added("<｜place▁holder▁no▁799｜>", special=True),
        "v4.1": _added("<｜System｜>", normalized=True),
    },
    129_264: {
        "v4": _added("<｜image2｜>"),
        "v4.1": _added("<｜deepseek_image｜>"),
    },
    129_265: {
        "v4": _added("<｜/table>｜"),
        "v4.1": _added("<|place_holder_mm_span_0436|>"),
    },
    129_266: {
        "v4": _added("<｜table｜>"),
        "v4.1": _added("<|place_holder_mm_span_0437|>"),
    },
    129_267: {
        "v4": _added("<｜/td｜>"),
        "v4.1": _added("<|place_holder_mm_span_0438|>"),
    },
    129_268: {
        "v4": _added("<｜td｜>"),
        "v4.1": _added("<|place_holder_mm_span_0439|>"),
    },
    129_269: {
        "v4": _added("<｜/tr｜>"),
        "v4.1": _added("<|place_holder_mm_span_0440|>"),
    },
    129_270: {
        "v4": _added("<｜tr｜>"),
        "v4.1": _added("<|place_holder_mm_span_0441|>"),
    },
    129_279: {
        "v4": _added("<｜image｜>", special=True),
        "v4.1": _added("<|place_holder_mm_span_0442|>", special=True),
    },
}

#: The one id whose *flags* moved, not only its content.  Named so a consumer
#: that strips specials can look it up instead of rediscovering it.
NON_SPECIAL_IN_V41: int = 128_799

#: The keys of ``tokenizer.json`` that decide a token id.  All of them are
#: required to be byte-identical to V4's, which is the whole argument for
#: reusing V4's probe expectations and protocol-token table below.
TOKEN_ID_BEARING_KEYS: tuple[str, ...] = (
    "version",
    "truncation",
    "padding",
    "normalizer",
    "pre_tokenizer",
    "post_processor",
    "decoder",
    "model",
)

#: V4.1's own protocol tokens, over and above the fourteen the V4 boundary
#: pins.  ``<｜System｜>`` is new in this release; it is the one rename that is
#: also a live part of the wire format.
V41_PROTOCOL_TOKEN_IDS: Mapping[str, tuple[str, int]] = {
    "system": ("<｜System｜>", 128_799),
    "deepseek_image": ("<｜deepseek_image｜>", 129_264),
}

#: Released ``config.json`` scalars this boundary confronts.  ``pad_token_id``
#: is 2 in V4.1 where it was 1 in V4, so it is read from the config and never
#: inherited from the V4 module.
CONFIG_TOKEN_KEYS: tuple[str, ...] = (
    "bos_token_id",
    "eos_token_id",
    "pad_token_id",
    "image_token_id",
)

_VERIFIED_CONSTRUCTION_KEY = object()


class DeepSeekV41TokenizerError(RuntimeError):
    """Raised when V4.1 tokenizer identity or runtime behaviour is not exact."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _runtime_version() -> str:
    try:
        version = metadata.version("tokenizers")
    except metadata.PackageNotFoundError as exc:
        raise DeepSeekV41TokenizerError(
            "tokenizers is required; install the pinned compiler dependency"
        ) from exc
    if version != TOKENIZERS_RUNTIME_VERSION:
        raise DeepSeekV41TokenizerError(
            f"tokenizers runtime is {version!r}, expected "
            f"{TOKENIZERS_RUNTIME_VERSION!r}"
        )
    return version


def load_inventory(path: Path = INVENTORY_PATH) -> Mapping[str, Any]:
    """The committed V4.1 inventory: repo, revision and the config digest."""

    if not path.exists():
        raise DeepSeekV41TokenizerError(
            f"committed V4.1 inventory missing at {path}; it is what "
            "authenticates a snapshot until WP-B lands the release record"
        )
    document = json.loads(path.read_text())
    for key in ("repo", "revision", "config_sha256"):
        if key not in document:
            raise DeepSeekV41TokenizerError(f"{path} carries no {key!r}")
    return document


def release_record_pins() -> dict[str, Any]:
    """Confront this module's digests with a V4.1 release record, if one exists.

    WP-B owns ``V41_FLASH``.  Every field it carries that this module also pins
    is required to agree; a field it does not carry, or a record that does not
    resolve, is recorded as unavailable.  Nothing here reads a digest *out* of
    the record - that would make the pin whatever the record says and check
    nothing - so a drift fails instead of being adopted.
    """

    report: dict[str, Any] = {"available": False}
    try:
        from compiler.frontend.deepseek_v4_releases import resolve_release
    except ImportError:  # pragma: no cover - the front end is always present
        report["unavailable"] = "compiler.frontend.deepseek_v4_releases absent"
        return report
    try:
        record = resolve_release(MODEL_ID)
    except Exception as exc:
        report["unavailable"] = f"{type(exc).__name__}: {exc}"
        return report
    report["available"] = True
    report["model_id"] = record.model_id
    agreed: dict[str, str] = {}
    missing: list[str] = []
    for field, pinned in (
        ("tokenizer_sha256", TOKENIZER_SHA256),
        ("tokenizer_config_sha256", TOKENIZER_CONFIG_SHA256),
    ):
        observed = getattr(record, field, None)
        if observed is None:
            missing.append(field)
            continue
        if observed != pinned:
            raise DeepSeekV41TokenizerError(
                f"release record {record.model_id} pins {field}={observed}, "
                f"this boundary verifies {pinned}; one of the two is looking at "
                "a different tokenizer and neither may be silently adopted"
            )
        agreed[field] = pinned
    report["agreed"] = agreed
    if missing:
        report["not_carried"] = missing
    for field in ("checkpoint_lock_id", "checkpoint_source_pending"):
        if hasattr(record, field):
            report[field] = getattr(record, field)
    return report


def _read_exact(
    snapshot: Path, name: str, expected_sha256: str, expected_bytes: int
) -> bytes:
    path = snapshot / name
    if not path.exists():
        raise DeepSeekV41TokenizerError(f"{name} missing from snapshot {snapshot}")
    payload = path.read_bytes()
    if len(payload) != expected_bytes:
        raise DeepSeekV41TokenizerError(
            f"{name} is {len(payload)} bytes, expected {expected_bytes}"
        )
    digest = _sha256(payload)
    if digest != expected_sha256:
        raise DeepSeekV41TokenizerError(
            f"{name} hashes to {digest}, expected {expected_sha256}"
        )
    return payload


def _authenticate_snapshot(
    snapshot: Path, inventory: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind a snapshot directory to the revision the inventory pins."""

    config_path = snapshot / "config.json"
    if not config_path.exists():
        raise DeepSeekV41TokenizerError(
            f"config.json missing from snapshot {snapshot}; a snapshot with no "
            "released config cannot be bound to a revision"
        )
    payload = config_path.read_bytes()
    digest = _sha256(payload)
    if digest != inventory["config_sha256"]:
        raise DeepSeekV41TokenizerError(
            f"{config_path} hashes to {digest}, which is not "
            f"{inventory['repo']}@{inventory['revision']}'s "
            f"{inventory['config_sha256']}; the DeepSeek releases share "
            "tokenizer bytes, so the released config is what identifies a "
            "snapshot"
        )
    config = json.loads(payload)
    return {
        "repository": inventory["repo"],
        "revision": inventory["revision"],
        "config_sha256": digest,
        "config_authority": str(INVENTORY_PATH.relative_to(REPO)),
        "config_tokens": {
            key: config[key] for key in CONFIG_TOKEN_KEYS if key in config
        },
        "text_config_max_position_embeddings": config["text_config"][
            "max_position_embeddings"
        ],
    }


def _v4_tokenizer_payload() -> bytes:
    """V4's ``tokenizer.json`` bytes, re-verified against the V4 module's pin.

    The structural proof is only as good as the thing it compares against, so
    the reference file is hash-checked here rather than trusted for being on
    disk.  It is looked for in the V4 snapshot the V4 boundary already reads.
    """

    from compiler.frontend.deepseek_v4_releases import FLASH

    path = FLASH.snapshot / TOKENIZER_FILENAME
    if not path.exists():
        raise DeepSeekV41TokenizerError(
            f"V4 {TOKENIZER_FILENAME} missing at {path}; the V4.1 boundary "
            "proves its tokenizer equal to V4's outside nine added tokens, so "
            "it needs V4's verified file to compare against"
        )
    payload = path.read_bytes()
    digest = _sha256(payload)
    if digest != V4_TOKENIZER_SHA256:
        raise DeepSeekV41TokenizerError(
            f"{path} hashes to {digest}, not the V4 boundary's pinned "
            f"{V4_TOKENIZER_SHA256}"
        )
    return payload


def _verify_added_token_delta(
    v41_document: Mapping[str, Any], v4_document: Mapping[str, Any]
) -> dict[str, Any]:
    """Require the two tokenizers to differ only in the nine renamed contents."""

    if set(v41_document) != set(v4_document):
        raise DeepSeekV41TokenizerError(
            "V4.1 tokenizer.json has different top-level keys from V4's: "
            f"{sorted(set(v41_document) ^ set(v4_document))}"
        )
    for key in TOKEN_ID_BEARING_KEYS:
        if v41_document[key] != v4_document[key]:
            raise DeepSeekV41TokenizerError(
                f"V4.1 tokenizer.json {key!r} differs from V4's; a token id "
                "produced by this file cannot be assumed to be V4's, so the "
                "reused probe and protocol-token expectations do not hold"
            )
    v41_added = {entry["id"]: entry for entry in v41_document["added_tokens"]}
    v4_added = {entry["id"]: entry for entry in v4_document["added_tokens"]}
    if set(v41_added) != set(v4_added):
        raise DeepSeekV41TokenizerError(
            "V4.1 added_tokens cover different ids from V4's: "
            f"{sorted(set(v41_added) ^ set(v4_added))}"
        )
    observed: dict[int, dict[str, dict[str, Any]]] = {}
    for token_id, v4_entry in v4_added.items():
        v41_entry = v41_added[token_id]
        if v41_entry == v4_entry:
            continue
        observed[token_id] = {
            "v4": {k: v for k, v in v4_entry.items() if k != "id"},
            "v4.1": {k: v for k, v in v41_entry.items() if k != "id"},
        }
    expected = {
        token_id: {"v4": dict(pair["v4"]), "v4.1": dict(pair["v4.1"])}
        for token_id, pair in ADDED_TOKEN_DELTA.items()
    }
    if observed != expected:
        raise DeepSeekV41TokenizerError(
            "V4.1 added_tokens differ from V4's outside the pinned delta "
            f"table: observed {observed}, pinned {expected}"
        )
    return {
        "token_id_bearing_keys_identical": list(TOKEN_ID_BEARING_KEYS),
        "base_vocabulary_entries": len(v41_document["model"]["vocab"]),
        "merges": len(v41_document["model"]["merges"]),
        "added_token_count": len(v41_added),
        "changed_added_tokens": {
            str(token_id): observed[token_id] for token_id in sorted(observed)
        },
        "non_special_in_v41": NON_SPECIAL_IN_V41,
    }


def _load_backend(payload: bytes) -> Any:
    _runtime_version()
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:  # pragma: no cover - version check handles absence
        raise DeepSeekV41TokenizerError("cannot import tokenizers runtime") from exc
    try:
        return Tokenizer.from_str(payload.decode("utf-8"))
    except Exception as exc:
        raise DeepSeekV41TokenizerError(
            f"tokenizers runtime rejected V4.1 tokenizer.json: {exc}"
        ) from exc


def _validate_backend(
    backend: Any, config_tokens: Mapping[str, Any]
) -> dict[str, Any]:
    if backend.get_vocab_size(with_added_tokens=False) != BASE_VOCAB_SIZE:
        raise DeepSeekV41TokenizerError("runtime base-vocabulary size differs")
    if backend.get_vocab_size(with_added_tokens=True) != VOCAB_SIZE:
        raise DeepSeekV41TokenizerError("runtime total-vocabulary size differs")
    checked: dict[str, int] = {}
    for label, (token, expected_id) in {
        **PROTOCOL_TOKEN_IDS,
        **V41_PROTOCOL_TOKEN_IDS,
    }.items():
        token_id = backend.token_to_id(token)
        encoded = backend.encode(token, add_special_tokens=False).ids
        if token_id != expected_id or encoded != [expected_id]:
            raise DeepSeekV41TokenizerError(
                f"runtime protocol token {label!r} maps to {token_id} / "
                f"{encoded}, expected {expected_id}"
            )
        checked[label] = expected_id
    for key, expected in (
        ("bos_token_id", PROTOCOL_TOKEN_IDS["begin_of_sentence"][1]),
        ("eos_token_id", PROTOCOL_TOKEN_IDS["end_of_sentence"][1]),
        ("image_token_id", V41_PROTOCOL_TOKEN_IDS["deepseek_image"][1]),
    ):
        if key in config_tokens and config_tokens[key] != expected:
            raise DeepSeekV41TokenizerError(
                f"released config {key}={config_tokens[key]} disagrees with the "
                f"tokenizer's {expected}"
            )
    return checked


def _validate_probes(backend: Any) -> list[dict[str, Any]]:
    """Re-run the V4 boundary's golden probes on V4.1's runtime.

    They are the V4 module's own expectations, imported rather than restated:
    the structural proof above is exactly the statement that they must still
    hold, so a probe that moved would mean the proof is wrong.
    """

    from compiler.frontend.deepseek_v4_tokenizer import _PROBES

    reports: list[dict[str, Any]] = []
    for text, expected in _PROBES:
        observed = tuple(backend.encode(text, add_special_tokens=False).ids)
        if observed != expected:
            raise DeepSeekV41TokenizerError(
                f"probe {text!r} encodes to {observed}, expected {expected} - "
                "V4.1's tokenizer is not V4's outside its added-token renames"
            )
        reports.append(
            {
                "text_sha256": _sha256(text.encode()),
                "token_count": len(observed),
                "source": "compiler.frontend.deepseek_v4_tokenizer._PROBES",
            }
        )
    return reports


class VerifiedDeepSeekV41Tokenizer:
    """A V4.1 tokenizer whose local bytes and runtime behaviour were verified."""

    def __init__(
        self,
        backend: Any,
        validation_report: dict[str, Any],
        *,
        _construction_key: object | None = None,
    ):
        if _construction_key is not _VERIFIED_CONSTRUCTION_KEY:
            raise DeepSeekV41TokenizerError(
                "verified tokenizer instances must be created by the local loader"
            )
        self._backend = backend
        self._validation_report = copy.deepcopy(validation_report)

    @property
    def bos_token_id(self) -> int:
        return PROTOCOL_TOKEN_IDS["begin_of_sentence"][1]

    @property
    def eos_token_id(self) -> int:
        return PROTOCOL_TOKEN_IDS["end_of_sentence"][1]

    @property
    def pad_token_id(self) -> int:
        """V4.1's released ``pad_token_id``, which is not V4's."""

        return int(self._validation_report["source"]["config_tokens"]["pad_token_id"])

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
            raise DeepSeekV41TokenizerError("text to encode must be a string")
        if not isinstance(enforce_max_length, bool):
            raise DeepSeekV41TokenizerError("enforce_max_length must be a boolean")
        try:
            ids = list(self._backend.encode(text, add_special_tokens=False).ids)
        except Exception as exc:
            raise DeepSeekV41TokenizerError(f"tokenization failed: {exc}") from exc
        if enforce_max_length and len(ids) > MODEL_MAX_LENGTH:
            raise DeepSeekV41TokenizerError(
                f"encoded text has {len(ids)} tokens, exceeding "
                f"model_max_length={MODEL_MAX_LENGTH}"
            )
        self._validate_ids(ids)
        return ids

    def decode(
        self, token_ids: Sequence[int], *, skip_special_tokens: bool = False
    ) -> str:
        if not isinstance(skip_special_tokens, bool):
            raise DeepSeekV41TokenizerError("skip_special_tokens must be a boolean")
        if isinstance(token_ids, (str, bytes)) or not isinstance(token_ids, Sequence):
            raise DeepSeekV41TokenizerError("token_ids must be an integer sequence")
        ids = list(token_ids)
        self._validate_ids(ids)
        try:
            return self._backend.decode(ids, skip_special_tokens=skip_special_tokens)
        except Exception as exc:
            raise DeepSeekV41TokenizerError(f"token decoding failed: {exc}") from exc

    @staticmethod
    def _validate_ids(ids: Sequence[Any]) -> None:
        for index, token_id in enumerate(ids):
            if (
                isinstance(token_id, bool)
                or not isinstance(token_id, int)
                or not 0 <= token_id < VOCAB_SIZE
            ):
                raise DeepSeekV41TokenizerError(
                    f"token_ids[{index}]={token_id!r} is outside 0..{VOCAB_SIZE - 1}"
                )


def load_verified_deepseek_v41_tokenizer(
    snapshot: Path,
    *,
    inventory_path: Path = INVENTORY_PATH,
) -> VerifiedDeepSeekV41Tokenizer:
    """Load V4.1's tokenizer from a snapshot bound to the committed inventory."""

    inventory = load_inventory(inventory_path)
    source = _authenticate_snapshot(Path(snapshot), inventory)
    config_payload = _read_exact(
        Path(snapshot),
        TOKENIZER_CONFIG_FILENAME,
        TOKENIZER_CONFIG_SHA256,
        TOKENIZER_CONFIG_SIZE_BYTES,
    )
    payload = _read_exact(
        Path(snapshot), TOKENIZER_FILENAME, TOKENIZER_SHA256, TOKENIZER_SIZE_BYTES
    )
    delta = _verify_added_token_delta(
        json.loads(payload), json.loads(_v4_tokenizer_payload())
    )
    backend = _load_backend(payload)
    protocol = _validate_backend(backend, source["config_tokens"])
    probes = _validate_probes(backend)
    report = {
        "model_id": MODEL_ID,
        "source": {
            **source,
            "snapshot": str(snapshot),
            "tokenizer_sha256": TOKENIZER_SHA256,
            "tokenizer_bytes": TOKENIZER_SIZE_BYTES,
            "tokenizer_config_sha256": TOKENIZER_CONFIG_SHA256,
            "tokenizer_config_bytes": len(config_payload),
        },
        "structural_proof_against_v4": delta,
        "release_record": release_record_pins(),
        "protocol_token_ids": protocol,
        "probes": probes,
        "tokenizers_runtime": TOKENIZERS_RUNTIME_VERSION,
    }
    return VerifiedDeepSeekV41Tokenizer(
        backend, report, _construction_key=_VERIFIED_CONSTRUCTION_KEY
    )


__all__ = [
    "ADDED_TOKEN_DELTA",
    "DeepSeekV41TokenizerError",
    "INVENTORY_PATH",
    "MODEL_ID",
    "NON_SPECIAL_IN_V41",
    "TOKENIZER_SHA256",
    "TOKENIZER_SIZE_BYTES",
    "V41_PROTOCOL_TOKEN_IDS",
    "VerifiedDeepSeekV41Tokenizer",
    "load_inventory",
    "release_record_pins",
    "load_verified_deepseek_v41_tokenizer",
]
