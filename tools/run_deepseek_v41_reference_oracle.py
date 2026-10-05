#!/usr/bin/env python3
"""Independent DeepSeek-V4.1-Flash reference oracle: an EXTERNAL comparator.

This program runs the VENDOR's own pinned modelling code -- ``inference/model.py``
and ``inference/engram.py`` of revision
``dba1be0a40aa45a94ad051997016db3960a90277`` -- and records what it did, so that
the accelerator's own output can be checked against something it did not
compute.  It never produces accelerator tokens, never supplies an activation,
and labels its results as an external reference in every record.  ADR-003
section 18 permits exactly this use and forbids the other one.

Follows ``tools/run_deepseek_v4_reference_oracle.py``: same schema, same
producer/input identity discipline, same "measured beside predicted, never
instead of" reporting, same greedy lowest-token-id selection.

THE TWO THINGS THIS PROGRAM EXISTS TO GET RIGHT
-----------------------------------------------
1. ``Indexer.forward`` AND ``Engram.forward`` ARE WRAPPED BEFORE THE FIRST RUN.
   Not after a first pass, not conditionally, not only on the tiled path.  The
   V4 ladder under-counted index scans by up to 1.60x because its indexer was
   not wrapped on the untiled path, and an untiled rung reported ZERO index
   (layer, position) pairs -- indistinguishable from an implementation that had
   declined to scan its index.  :func:`install_counters` therefore installs both
   wraps and then REFUSES to run until it has verified, by identity, that the
   bodies it installed are the bodies the model will call
   (:func:`verify_wraps_installed`); and every stage that runs vendor code
   asserts a non-zero count for each wrapped symbol afterwards, so a silently
   bypassed wrap fails the stage instead of reporting a small number.

2. THE KV ENTRY WIDTHS ARE MEASURED, NOT READ OFF THE RECIPE.  For V4 the
   measured width differed from the published serving recipe by 1.8x (1,024 B
   against 583 B), and a hardcoded copy of the engine width went on being wrong
   silently.  Here nothing is hardcoded: :func:`measure_entry_widths`
   constructs the vendor's own modules at the released geometry and reads
   ``buffer.size(-1) * buffer.element_size()`` off the buffers the vendor itself
   registered.  The recipe widths are read from the profile, never restated, and
   both appear side by side with their ratio.

WHAT A WIDTH IS, AND WHY MEASURING IT NEEDS NO WEIGHTS.  An entry width is the
last-axis extent of a cache times its element size.  Both are fixed by
``head_dim`` / ``index_head_dim`` and the storage dtype; neither depends on
``max_seq_len``, on the batch, or on any weight value.  So the width stage
allocates a short cache and reads the width off it, and the number it reports is
the width of the released cache.  ``--max-seq-len`` is therefore an allocation
convenience and is recorded as one; it is NOT a model bound, and the stage
refuses to report a width it did not read from a buffer.

NO FROZEN GEOMETRY.  Every shape this program uses comes from the pinned
``config.json`` at run time via :func:`released_model_args`.  There is no
transcribed layer count, head count, ``head_dim``, window, block size or table
row count anywhere below.  A field the released config does not carry is a hard
error, not a default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from runtime.reference.candidate_pool import (  # noqa: E402
    NEGATIVE_INFINITY,
    select_candidate_blocks,
)
from runtime.reference.engram import (  # noqa: E402
    engram_gate_pinned_divergences,
    prove_pinned_form_differs,
)

SCHEMA = "opentallas.abi3.reference_oracle.v1"
MODEL_ID = "deepseek-v4.1-flash"
REVISION = "dba1be0a40aa45a94ad051997016db3960a90277"

#: The pinned snapshot.  Overridable, but every record carries the digests of
#: what was actually loaded, so a substituted snapshot is visible rather than
#: assumed away.
DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--deepseek-ai--DeepSeek-V4.1-Flash"
    / "snapshots"
    / REVISION
)
DEFAULT_LOCK = Path.home() / ".cache/opentallas/deepseek-v4.1-flash/checkpoint.lock.json"

#: SRC-DSV41-FLASH-MODEL and SRC-DSV41-FLASH-CONFIG in docs/SOURCES.md.  The
#: vendor sources are NOT vendored into this repository, so these are the only
#: statement of which bytes the records below describe.
PINNED_VENDOR_SHA256 = {
    "inference/model.py": (
        "4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65"
    ),
    "inference/engram.py": (
        "11f35ecbead8150c35aa002b3d180ef290b05a25afe883a11884f94d476d3897"
    ),
    "config.json": (
        "8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879"
    ),
}

#: The complete repository-owned implementation boundary that can alter what
#: this program reports.  Kept small on purpose: it is a comparator, not part of
#: the compiler or the runtime.
PRODUCER_SOURCE_PATHS = (
    "runtime/reference/candidate_pool.py",
    "runtime/reference/engram.py",
    "runtime/reference/fp4_kv.py",
    "tools/run_deepseek_v41_reference_oracle.py",
)

#: The candidate profile whose recipe widths the measured widths are set beside.
PROFILE_PATH = REPO / "configs/models/candidates/deepseek-v4.1-flash.json"

#: Where the greedy-token stages would write.  Named here so the blocked-stage
#: record can say exactly which artifact is absent (plan section 4.3).
TOKEN_OUTPUTS = {
    "prefix": "results/abi3/deepseek_v41_reference_oracle_prefix.json",
    "context_ladder": "results/abi3/deepseek_v41_reference_oracle_context_ladder.json",
}


class OracleError(RuntimeError):
    """A refusal: a digest, a wrap, a width or a prerequisite did not hold."""


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def producer_identity() -> dict[str, Any]:
    """Hash every repository file that can change this program's answers."""
    source_map = {
        relative: _sha256_file(REPO / relative) for relative in PRODUCER_SOURCE_PATHS
    }
    return {
        "tool": "tools/run_deepseek_v41_reference_oracle.py",
        "tool_source_sha256": source_map[
            "tools/run_deepseek_v41_reference_oracle.py"
        ],
        "source_map": source_map,
        "source_map_sha256": _canonical_digest(source_map),
    }


def verify_vendor_sources(snapshot: Path) -> dict[str, Any]:
    """Refuse to run against vendor bytes that are not the pinned ones."""
    observed: dict[str, str] = {}
    problems: list[str] = []
    for relative, expected in sorted(PINNED_VENDOR_SHA256.items()):
        path = snapshot / relative
        if not path.is_file():
            problems.append(f"{relative} is absent from {snapshot}")
            continue
        digest = _sha256_file(path)
        observed[relative] = digest
        if digest != expected:
            problems.append(
                f"{relative} has SHA-256 {digest}, not the pinned {expected}"
            )
    if problems:
        raise OracleError("vendor source identity failed: " + "; ".join(problems))
    return {
        "snapshot": str(snapshot),
        "revision": REVISION,
        "pinned_sha256": dict(PINNED_VENDOR_SHA256),
        "observed_sha256": observed,
        "all_match": True,
    }


def checkpoint_lock_identity(lock_path: Path) -> dict[str, Any]:
    """Read the locked checkpoint identity.  Nothing here is restated.

    Only the fields that identify the release are lifted; the per-tensor body is
    left in the lock, whose own digest covers it.
    """
    if not lock_path.is_file():
        return {"present": False, "path": str(lock_path)}
    document = json.loads(lock_path.read_text())
    checkpoint = document.get("checkpoint", {})
    return {
        "present": True,
        "path": str(lock_path),
        "schema": document.get("schema"),
        "lock_id": document.get("lock_id"),
        "tensor_count": checkpoint.get("tensor_count"),
        "payload_bytes": checkpoint.get("payload_bytes"),
        "shard_count": checkpoint.get("shard_count"),
        "tensor_content_sha256": checkpoint.get("tensor_content_sha256"),
    }


# ---------------------------------------------------------------------------
# released geometry, read from the pinned config at run time
# ---------------------------------------------------------------------------


def _require(mapping: dict[str, Any], key: str, source: str) -> Any:
    if key not in mapping:
        raise OracleError(f"{source} does not carry the required key {key!r}")
    return mapping[key]


def released_model_args(snapshot: Path, vendor: Any, max_seq_len: int) -> Any:
    """Build the vendor's own ``ModelArgs`` from the pinned ``config.json``.

    Every value is read from the released config.  ``max_batch_size`` and
    ``max_seq_len`` are the only arguments, and they size caches rather than
    describe the model -- the vendor's own comment says so.  A missing config key
    raises: a default here would be a frozen geometry wearing a config's name.
    """
    config = json.loads((snapshot / "config.json").read_text())
    text = _require(config, "text_config", "config.json")
    source = "config.json:text_config"
    return vendor.ModelArgs(
        max_batch_size=1,
        max_seq_len=max_seq_len,
        dtype="fp8",
        vocab_size=_require(text, "vocab_size", source),
        dim=_require(text, "hidden_size", source),
        moe_inter_dim=_require(text, "moe_intermediate_size", source),
        n_layers=_require(text, "num_hidden_layers", source),
        n_heads=_require(text, "num_attention_heads", source),
        n_routed_experts=_require(text, "n_routed_experts", source),
        n_shared_experts=_require(text, "n_shared_experts", source),
        n_activated_experts=_require(text, "num_experts_per_tok", source),
        score_func=_require(text, "scoring_func", source),
        norm_topk_prob=_require(text, "norm_topk_prob", source),
        route_scale=_require(text, "routed_scaling_factor", source),
        swiglu_limit=_require(text, "swiglu_limit", source),
        q_lora_rank=_require(text, "q_lora_rank", source),
        head_dim=_require(text, "head_dim", source),
        rope_head_dim=_require(text, "qk_rope_head_dim", source),
        norm_eps=_require(text, "rms_norm_eps", source),
        o_groups=_require(text, "o_groups", source),
        o_lora_rank=_require(text, "o_lora_rank", source),
        window_size=_require(text, "sliding_window", source),
        compress_ratios=tuple(_require(text, "compress_ratios", source)),
        kv_source_layers=tuple(_require(text, "kv_source_layer_ids", source)),
        index_source_layers=tuple(_require(text, "index_source_layer_ids", source)),
        compress_rope_theta=_require(text, "compress_rope_theta", source),
        original_seq_len=_require(
            _require(text, "rope_scaling", source),
            "original_max_position_embeddings",
            source + ":rope_scaling",
        ),
        rope_theta=_require(text, "rope_theta", source),
        rope_factor=_require(
            _require(text, "rope_scaling", source), "factor", source + ":rope_scaling"
        ),
        beta_fast=_require(
            _require(text, "rope_scaling", source),
            "beta_fast",
            source + ":rope_scaling",
        ),
        beta_slow=_require(
            _require(text, "rope_scaling", source),
            "beta_slow",
            source + ":rope_scaling",
        ),
        index_n_heads=_require(text, "index_n_heads", source),
        index_head_dim=_require(text, "index_head_dim", source),
        index_topk=_require(text, "index_topk", source),
        candidate_source_layer=_require(text, "candidate_source_layer_id", source),
        candidate_topk_blocks=_require(text, "candidate_topk_blocks", source),
        candidate_block_size=_require(text, "candidate_block_size", source),
        hc_mult=_require(text, "hc_mult", source),
        hc_sinkhorn_iters=_require(text, "hc_sinkhorn_iters", source),
        hc_eps=_require(text, "hc_eps", source),
        engram_layer_ids=tuple(_require(text, "engram_layer_ids", source)),
        engram_num_embeddings=tuple(_require(text, "engram_num_embeddings", source)),
        engram_max_ngram_size=_require(text, "engram_max_ngram_size", source),
        engram_vocab_size=_require(text, "engram_vocab_size", source),
        engram_n_heads=_require(text, "engram_n_heads", source),
        engram_head_dim=_require(text, "engram_head_dim", source),
        engram_pad_id=_require(text, "engram_pad_token_id", source),
        engram_compressed_vocab_size=_require(
            text, "engram_compressed_vocab_size", source
        ),
    )


def import_vendor(snapshot: Path) -> Any:
    """Import the pinned ``inference/model.py`` after verifying its digest.

    The vendor modules import each other by bare name, so the snapshot's
    ``inference`` directory goes on ``sys.path`` as the vendor's own
    ``generate.py`` arranges.  ``torch``'s default dtype is set to bfloat16
    first, exactly as ``inference/generate.py`` does before constructing the
    model: the cache buffers are allocated at the default dtype, so setting it
    afterwards would measure a width the released launch never has.
    """
    import torch

    inference = snapshot / "inference"
    if not inference.is_dir():
        raise OracleError(f"{inference} is not a directory")
    if str(inference) not in sys.path:
        sys.path.insert(0, str(inference))
    torch.set_default_dtype(torch.bfloat16)
    import model as vendor  # noqa: PLC0415

    return vendor


# ---------------------------------------------------------------------------
# the counters, and the wraps that feed them
# ---------------------------------------------------------------------------


class VendorCounters:
    """Counts what the vendor's own code read, from the tensors it was handed.

    Every count comes from an operand's own shape and an operand's own
    ``element_size()``.  No width, stride or row count is transcribed, so a
    geometry change shows up as a different count rather than as a stale
    constant.
    """

    def __init__(self) -> None:
        self.enabled = False
        self.indexer_calls = 0
        self.engram_calls = 0
        self.attention_calls = 0
        self.layers: dict[int, dict[str, Any]] = {}
        #: Which layer the next wrapped call belongs to.  An ``Indexer`` does
        #: not carry a layer id, so whoever drives it says which layer it is;
        #: ``Attention.forward``'s wrap sets this from ``self.layer_id``, and a
        #: stage that calls an indexer directly sets it explicitly.  ``None``
        #: means "nobody said", which is recorded as such rather than as 0.
        self.layer_id: int | None = None
        #: Measured widths, keyed by role, each recorded with the buffer it was
        #: read from so a reader can see it was read and not restated.
        self.widths: dict[str, dict[str, Any]] = {}

    def _layer(self, layer_id: int | None) -> dict[str, Any]:
        if layer_id is None:
            raise OracleError(
                "a wrapped vendor call was counted with no layer id; the count "
                "would be attributed to a layer nobody named"
            )
        return self.layers.setdefault(
            int(layer_id),
            {
                "index_calls": 0,
                "index_queries": 0,
                "index_positions_scored": 0,
                "index_positions_admitted": None,
                "index_selected_per_query": None,
                "index_bytes_scored": 0,
                "engram_calls": 0,
                "engram_tokens": 0,
                "engram_rows_gathered": 0,
                "engram_row_bytes": None,
                "engram_bytes_gathered": 0,
            },
        )

    def note_width(self, role: str, buffer: Any, origin: str) -> None:
        """Record one measured entry width, from the buffer itself."""
        extent = int(buffer.size(-1))
        element = int(buffer.element_size())
        self.widths[role] = {
            "entry_bytes": extent * element,
            "last_axis_extent": extent,
            "element_size_bytes": element,
            "dtype": str(buffer.dtype),
            "read_from": origin,
            "shape": [int(value) for value in buffer.shape],
        }

    def note_index_scan(
        self,
        layer_id: int | None,
        queries: int,
        positions: int,
        index_k: Any,
        selected: int,
        admitted: int | None,
    ) -> None:
        if not self.enabled:
            return
        self.indexer_calls += 1
        entry_bytes = int(index_k.size(-1)) * int(index_k.element_size())
        layer = self._layer(layer_id)
        layer["index_calls"] += 1
        layer["index_queries"] += int(queries)
        layer["index_positions_scored"] += int(queries) * int(positions)
        layer["index_bytes_scored"] += int(queries) * int(positions) * entry_bytes
        layer["index_selected_per_query"] = int(selected)
        layer["index_positions_admitted"] = admitted
        self.note_width(
            "index",
            index_k,
            f"Indexer.k_cache handed to Indexer.forward at layer {layer_id}",
        )

    def note_engram(
        self, layer_id: int, tokens: int, hash_ids: Any, embed: Any
    ) -> None:
        if not self.enabled:
            return
        self.engram_calls += 1
        rows = int(hash_ids.numel())
        row_bytes = int(embed.weight.size(-1)) * int(embed.weight.element_size()) + int(
            embed.scale.size(-1)
        ) * int(embed.scale.element_size())
        layer = self._layer(layer_id)
        layer["engram_calls"] += 1
        layer["engram_tokens"] += int(tokens)
        layer["engram_rows_gathered"] += rows
        layer["engram_row_bytes"] = row_bytes
        layer["engram_bytes_gathered"] += rows * row_bytes
        self.widths["engram_row"] = {
            "entry_bytes": row_bytes,
            "value_bytes": int(embed.weight.size(-1))
            * int(embed.weight.element_size()),
            "scale_bytes": int(embed.scale.size(-1)) * int(embed.scale.element_size()),
            "value_dtype": str(embed.weight.dtype),
            "scale_dtype": str(embed.scale.dtype),
            "read_from": (
                "ParallelEngramEmbedding.weight/.scale inside Engram.forward at "
                f"layer {layer_id}"
            ),
            "shape": [int(value) for value in embed.weight.shape],
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "indexer_forward_calls": self.indexer_calls,
            "engram_forward_calls": self.engram_calls,
            "attention_forward_calls": self.attention_calls,
            "measured_widths": dict(self.widths),
            "per_layer": {str(key): value for key, value in sorted(self.layers.items())},
        }


COUNTERS = VendorCounters()

#: Set by :func:`install_counters` to the exact function objects it installed,
#: so :func:`verify_wraps_installed` can prove the model will call them.
_INSTALLED: dict[str, Any] = {}
#: The vendor bodies the wraps delegate to, kept so a run can be repeated
#: without them.
_VENDOR_BODIES: dict[str, Any] = {}


def install_counters(vendor: Any) -> dict[str, Any]:
    """Wrap ``Indexer.forward`` and ``Engram.forward`` BEFORE the first run.

    This is the single most important function in this program.  It is called
    once, before any vendor module is constructed or called, and it is followed
    by :func:`verify_wraps_installed`, which refuses to proceed unless the
    attributes the model will look up are the wraps this installed.

    Both wraps delegate to the vendor body unchanged and read their counts off
    the operands the vendor body was handed, so wrapping cannot alter a value.
    ``Attention.forward`` is wrapped too, but only to make the current layer id
    available: an ``Indexer`` does not carry one.
    """
    if _INSTALLED:
        raise OracleError("the counters are already installed; install once")

    vendor_indexer = vendor.Indexer.forward
    vendor_engram = vendor.Engram.forward
    vendor_attention = vendor.Attention.forward
    _VENDOR_BODIES.update(
        {
            "Indexer.forward": vendor_indexer,
            "Engram.forward": vendor_engram,
            "Attention.forward": vendor_attention,
        }
    )
    def counted_indexer(self, x, qr, latent, start_pos, offset):  # noqa: ANN001
        out = vendor_indexer(self, x, qr, latent, start_pos, offset)
        queries = int(x.size(1))
        end_pos = int(start_pos) + queries
        ratio = int(self.compress_ratio)
        #: The width the vendor's own einsum scored: it slices
        #: `shared_attn.index_k[:bsz, : end_pos // ratio]` and scores ALL of it,
        #: then masks.  A candidate layer's mask reduces what is SELECTED, not
        #: what is scored -- which is the whole reason this is measured.
        positions = end_pos // ratio if ratio else 0
        index_k = vendor.shared_attn.index_k
        admitted = None
        candidates = vendor.shared_attn.candidates
        if getattr(self, "uses_candidates", False) and candidates is not None:
            admitted = int(candidates.sum().item())
        COUNTERS.note_index_scan(
            layer_id=COUNTERS.layer_id,
            queries=queries,
            positions=positions,
            index_k=index_k,
            selected=int(out.size(-1)),
            admitted=admitted,
        )
        return out

    def counted_engram(self, x, hash_ids, token_mask=None):  # noqa: ANN001
        out = vendor_engram(self, x, hash_ids, token_mask)
        COUNTERS.note_engram(
            layer_id=int(self.layer_id),
            tokens=int(x.size(1)),
            hash_ids=hash_ids,
            embed=self.embed,
        )
        return out

    def counted_attention(self, x, start_pos, *rest):  # noqa: ANN001
        COUNTERS.layer_id = int(self.layer_id)
        if COUNTERS.enabled:
            COUNTERS.attention_calls += 1
            COUNTERS.note_width(
                "window",
                self.window_kv_cache,
                f"Attention.window_kv_cache at layer {self.layer_id}",
            )
            if getattr(self, "is_kv_source", False):
                COUNTERS.note_width(
                    "main",
                    self.compress_kv_cache,
                    f"Attention.compress_kv_cache at layer {self.layer_id}",
                )
        return vendor_attention(self, x, start_pos, *rest)

    vendor.Indexer.forward = counted_indexer
    vendor.Engram.forward = counted_engram
    vendor.Attention.forward = counted_attention
    _INSTALLED.update(
        {
            "Indexer.forward": counted_indexer,
            "Engram.forward": counted_engram,
            "Attention.forward": counted_attention,
        }
    )
    return {
        "wrapped_before_first_run": True,
        "wrapped_symbols": sorted(_INSTALLED),
        "required_symbols": ["Engram.forward", "Indexer.forward"],
    }


def verify_wraps_installed(vendor: Any) -> dict[str, Any]:
    """Prove, by identity, that the model will call the wraps we installed.

    ``install_counters`` succeeding is not evidence: a later import, a
    ``copy``, or a second patch could put the vendor body back.  This compares
    the attribute the model will actually look up against the object installed.
    """
    checks = {}
    problems = []
    for symbol, installed in sorted(_INSTALLED.items()):
        class_name, attribute = symbol.split(".")
        current = getattr(getattr(vendor, class_name), attribute)
        match = current is installed
        checks[symbol] = {
            "installed_is_current": match,
            "current_qualname": getattr(current, "__qualname__", repr(current)),
        }
        if not match:
            problems.append(f"{symbol} is not the installed wrap")
    for required in ("Indexer.forward", "Engram.forward"):
        if required not in checks:
            problems.append(f"{required} was never wrapped")
    if problems:
        raise OracleError("wrap verification failed: " + "; ".join(problems))
    return {"all_installed": True, "checks": checks}


def require_counts(*symbols: str) -> dict[str, Any]:
    """Assert every named wrap actually fired.  A zero is a failure, not a zero.

    This is the V4 lesson stated as a check: a rung that reports zero index
    scans looks exactly like an implementation that declined to scan its index.
    """
    observed = {
        "Indexer.forward": COUNTERS.indexer_calls,
        "Engram.forward": COUNTERS.engram_calls,
        "Attention.forward": COUNTERS.attention_calls,
    }
    missing = [symbol for symbol in symbols if observed.get(symbol, 0) == 0]
    if missing:
        raise OracleError(
            "a wrapped vendor symbol recorded zero calls, so its count is not "
            f"evidence: {', '.join(missing)} (observed {observed})"
        )
    return {symbol: observed[symbol] for symbol in symbols}


# ---------------------------------------------------------------------------
# stage: measured entry widths beside the profile's recipe widths
# ---------------------------------------------------------------------------


def profile_recipe_widths() -> dict[str, Any]:
    """The widths the PROFILE charges, read from the profile.  Never restated.

    Read through ``ModelProfile`` so a profile the loader rejects cannot supply
    a comparison, and grouped by role: ``main`` is ``entry_bytes`` of a
    compressed group, ``index`` its ``index_entry_bytes``, ``window`` the window
    entry -- ``window_entry_bytes`` where a compressed group carries one, and
    ``entry_bytes`` of a pure window group otherwise.
    """
    from opentallas.schema import ModelProfile  # noqa: PLC0415

    profile = ModelProfile.load(PROFILE_PATH)
    groups = []
    main: set[float] = set()
    index: set[float] = set()
    window: set[float] = set()
    for group in profile.attention_groups:
        label = group.label or group.kind
        window_entry = getattr(group, "window_entry_bytes", None)
        record = {
            "label": label,
            "kind": group.kind,
            "count": group.count,
            "entry_bytes": float(group.entry_bytes),
            "index_entry_bytes": float(group.index_entry_bytes),
            "window_entry_bytes": (
                None if window_entry is None else float(window_entry)
            ),
        }
        groups.append(record)
        if group.kind == "window":
            window.add(float(group.entry_bytes))
        else:
            main.add(float(group.entry_bytes))
            if float(group.index_entry_bytes):
                index.add(float(group.index_entry_bytes))
            if window_entry is not None:
                window.add(float(window_entry))

    def single(values: set[float], role: str) -> float | None:
        if len(values) == 1:
            return next(iter(values))
        if not values:
            return None
        raise OracleError(
            f"the profile charges more than one {role} entry width "
            f"({sorted(values)}); a single recipe width is not defined"
        )

    return {
        "profile_path": str(PROFILE_PATH.relative_to(REPO)),
        "num_layers": profile.num_layers,
        "groups": groups,
        "recipe_entry_bytes": {
            "main": single(main, "main"),
            "index": single(index, "index"),
            "window": single(window, "window"),
        },
    }


def measure_entry_widths(vendor: Any, args: Any) -> dict[str, Any]:
    """Read the three entry widths off the vendor's own registered buffers.

    Constructs one ``Attention`` per distinct role the released
    ``compress_ratios`` / ``kv_source_layer_ids`` / ``index_source_layer_ids``
    produce and reads each cache's own last-axis extent and element size.  No
    weights are loaded and no forward runs: a width is a property of the buffer.
    """
    import torch  # noqa: PLC0415

    roles: dict[str, dict[str, Any]] = {}
    per_layer: list[dict[str, Any]] = []
    #: One layer per distinct (ratio, owns kv, owns index) class, picked from the
    #: released config rather than named.
    seen: set[tuple[int, bool, bool]] = set()
    for layer_id in range(args.n_layers):
        ratio = args.compress_ratios[layer_id]
        signature = (
            int(ratio),
            layer_id in args.kv_source_layers,
            layer_id in args.index_source_layers,
        )
        if signature in seen:
            continue
        seen.add(signature)
        attention = vendor.Attention(layer_id, args)
        record: dict[str, Any] = {
            "layer_id": layer_id,
            "compress_ratio": int(ratio),
            "is_kv_source": bool(attention.is_kv_source),
            "is_index_source": bool(attention.is_index_source),
            "measured": {},
        }

        def take(role: str, buffer: Any, origin: str) -> None:
            extent = int(buffer.size(-1))
            element = int(buffer.element_size())
            entry = {
                "entry_bytes": extent * element,
                "last_axis_extent": extent,
                "element_size_bytes": element,
                "dtype": str(buffer.dtype),
                "read_from": origin,
                "shape": [int(value) for value in buffer.shape],
            }
            record["measured"][role] = entry
            previous = roles.get(role)
            if previous is not None and previous["entry_bytes"] != entry["entry_bytes"]:
                raise OracleError(
                    f"the {role} entry width is not one number: "
                    f"{previous['entry_bytes']} at {previous['read_from']} against "
                    f"{entry['entry_bytes']} at {origin}"
                )
            roles[role] = entry

        take(
            "window",
            attention.window_kv_cache,
            f"Attention.window_kv_cache, layer {layer_id}",
        )
        if attention.is_kv_source:
            take(
                "main",
                attention.compress_kv_cache,
                f"Attention.compress_kv_cache, layer {layer_id}",
            )
            if attention.indexer is not None and attention.indexer.owns_k:
                take(
                    "index",
                    attention.indexer.k_cache,
                    f"Indexer.k_cache, layer {layer_id}",
                )
        per_layer.append(record)
        del attention

    missing = [role for role in ("main", "index", "window") if role not in roles]
    if missing:
        raise OracleError(
            "the released geometry produced no buffer for: " + ", ".join(missing)
        )
    return {
        "grade": "executed",
        "method": (
            "constructed the pinned vendor Attention/Indexer at the released "
            "geometry and read buffer.size(-1) * buffer.element_size() off each "
            "registered cache; no width is transcribed in this program"
        ),
        "torch_default_dtype": str(torch.get_default_dtype()),
        "torch_default_dtype_note": (
            "inference/generate.py calls torch.set_default_dtype(torch.bfloat16) "
            "before constructing the Transformer, and every cache is registered "
            "with torch.zeros at the default dtype, so this IS the released "
            "launch's storage dtype"
        ),
        "allocation_only_arguments": {
            "max_batch_size": args.max_batch_size,
            "max_seq_len": args.max_seq_len,
            "note": (
                "these size the allocation, not the width: an entry width is the "
                "last-axis extent times the element size and neither depends on "
                "either value"
            ),
        },
        "measured_entry_bytes": {
            role: roles[role]["entry_bytes"] for role in sorted(roles)
        },
        "measured": roles,
        "per_layer_class": per_layer,
    }


def compare_widths(measured: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    """Set measured beside recipe, with the ratio, for each of the three roles."""
    rows = []
    for role in ("main", "index", "window"):
        measured_bytes = measured["measured_entry_bytes"].get(role)
        recipe_bytes = recipe["recipe_entry_bytes"].get(role)
        rows.append(
            {
                "role": role,
                "measured_entry_bytes": measured_bytes,
                "measured_grade": "executed",
                "recipe_entry_bytes": recipe_bytes,
                "recipe_grade": "read_from_profile",
                "measured_over_recipe": (
                    measured_bytes / recipe_bytes
                    if measured_bytes and recipe_bytes
                    else None
                ),
                "agrees": measured_bytes == recipe_bytes,
            }
        )
    return {
        "note": (
            "the measured width is what the vendor's own cache holds; the recipe "
            "width is what the profile charges. Both are reported. NEITHER is "
            "corrected into the other here: a storage format the accelerator "
            "chooses is a design decision, and the ratio is the size of that "
            "decision"
        ),
        "rows": rows,
        "all_agree": all(row["agrees"] for row in rows),
    }


# ---------------------------------------------------------------------------
# stage: the candidate pool, vendor against reference
# ---------------------------------------------------------------------------


def compare_candidate_pool(vendor: Any, args: Any, trials: int) -> dict[str, Any]:
    """Run the pinned ``select_candidate_blocks`` against the repo reference.

    Pure tensor code with no quantized kernel, so this runs wherever torch does.
    The reference is independent: it works on exact values with a sentinel for
    -inf and never calls torch.  Rows whose admitted set is not determined by
    the scores alone (``tie_at_threshold``) are reported separately, because a
    disagreement there is not evidence either way.
    """
    import torch  # noqa: PLC0415

    block_size = int(args.candidate_block_size)
    topk_blocks = int(args.candidate_topk_blocks)
    generator = torch.Generator().manual_seed(41)
    rows = []
    agreements = 0
    tied = 0
    disagreements = []
    for trial in range(trials):
        #: A width that is deliberately NOT a multiple of the block size for
        #: most trials, so the -inf pad of the partial final block is exercised.
        width = int(torch.randint(1, 40, (1,), generator=generator).item()) * block_size
        width += trial % block_size
        width = max(width, 1)
        reach = int(torch.randint(1, width + 1, (1,), generator=generator).item())
        scores = torch.randn(width, generator=generator, dtype=torch.float32)
        #: The pinned contract: positions the query cannot reach arrive at -inf.
        scores[reach:] = -float("inf")
        vendor_mask = vendor.select_candidate_blocks(
            scores.unsqueeze(0), reach, topk_blocks, block_size
        )[0]
        exact = [
            NEGATIVE_INFINITY if value == -float("inf") else _exact_float(value)
            for value in scores.tolist()
        ]
        reference = select_candidate_blocks(exact, reach, topk_blocks, block_size)
        match = [bool(value) for value in vendor_mask.tolist()] == list(
            reference["mask"]
        )
        if reference["tie_at_threshold"]:
            tied += 1
        elif match:
            agreements += 1
        else:
            disagreements.append(
                {
                    "trial": trial,
                    "width": width,
                    "compress_lens": reach,
                    "reference_blocks": list(reference["blocks"]),
                    "vendor_population": int(vendor_mask.sum().item()),
                    "reference_population": reference["population"],
                }
            )
        rows.append(
            {
                "trial": trial,
                "width": width,
                "compress_lens": reach,
                "block_size": block_size,
                "topk_blocks": topk_blocks,
                "partial_final_block": width % block_size != 0,
                "pinned_block": reference["pinned_block"],
                "pinned_block_is_axis_last": reference["pinned_block"]
                == (width + block_size - 1) // block_size - 1,
                "vendor_population": int(vendor_mask.sum().item()),
                "reference_population": reference["population"],
                "tie_at_threshold": reference["tie_at_threshold"],
                "masks_identical": match,
            }
        )
    return {
        "grade": "executed",
        "vendor_symbol": "model.select_candidate_blocks",
        "reference": "runtime.reference.candidate_pool.select_candidate_blocks",
        "trials": trials,
        "untied_agreements": agreements,
        "tied_rows_not_counted": tied,
        "disagreements": disagreements,
        "all_untied_rows_agree": not disagreements,
        "rows": rows,
    }


def _exact_float(value: float):
    """The exact rational value of a finite float, with no host rounding."""
    from fractions import Fraction  # noqa: PLC0415

    return Fraction(value)


# ---------------------------------------------------------------------------
# stage: the FP4 main-KV contract, vendor kernel against the repo reference
# ---------------------------------------------------------------------------


def compare_fp4_kv(vendor_snapshot: Path, args: Any, rows: int) -> dict[str, Any]:
    """Run the pinned ``fp4_act_quant`` and check the reference dequantize.

    The vendor is called TWICE on the same input: once with ``inplace=False``,
    which returns the E2M1 codes and the E4M3 scales, and once with
    ``inplace=True``, which returns the vendor's OWN dequantized reconstruction.
    ``runtime.reference.fp4_kv.dequantize_to_bf16_values`` is then given the
    vendor's own codes and scales, and its exact products are compared against
    the vendor's reconstruction element by element, as rationals.

    This is a real cross-check rather than a tautology: the reference decodes
    E2M1 and E4M3FN from their field definitions with ``fractions.Fraction`` and
    never calls torch, so agreement is evidence about the two format
    definitions.  It is an EQUALITY check, not a tolerance: the reference claims
    every product is exactly representable in the vendor's bfloat16 destination,
    so any difference at all would refute that claim.

    The scale group is the released ``16`` of the main-KV path, taken from the
    reference's own ``DEFAULT_SCALE_GROUP`` rather than written here.
    """
    import torch  # noqa: PLC0415

    from runtime.reference.fp4_kv import (  # noqa: PLC0415
        CONTRACT,
        DEFAULT_SCALE_GROUP,
        dequantize_to_bf16_values,
    )

    inference = vendor_snapshot / "inference"
    if str(inference) not in sys.path:
        sys.path.insert(0, str(inference))
    from kernel import fp4_act_quant  # noqa: PLC0415

    if not torch.cuda.is_available():
        return {
            "grade": "not_run",
            "reason": "the pinned fp4_act_quant is a CUDA kernel and no device is available",
        }

    group = int(DEFAULT_SCALE_GROUP)
    #: One row is one owned global KV latent: the released head_dim.
    width = int(args.head_dim)
    torch.cuda.set_device(0)
    generator = torch.Generator(device="cpu").manual_seed(416)
    sample = (
        torch.randn((rows, width), generator=generator, dtype=torch.float32) * 3
    ).to(torch.bfloat16).to("cuda")

    started = time.time()
    codes_packed, scales = fp4_act_quant(
        sample.clone(), group, False, scale_dtype=torch.float8_e4m3fn
    )
    reconstructed = fp4_act_quant(
        sample.clone(), group, True, scale_dtype=torch.float8_e4m3fn
    )
    torch.cuda.synchronize()
    elapsed = time.time() - started

    packed = codes_packed.view(torch.uint8).cpu().numpy()
    scale_bytes = scales.view(torch.uint8).cpu().numpy()
    vendor_values = reconstructed.float().cpu().tolist()

    from fractions import Fraction  # noqa: PLC0415

    #: The packing order is DETERMINED, not assumed: both readings are tried and
    #: the one that reproduces the vendor's own reconstruction is reported.  A
    #: guess here would silently compare the wrong nibbles.
    findings: dict[str, Any] = {}
    for order in ("low_nibble_first", "high_nibble_first"):
        mismatches = 0
        checked = 0
        first: dict[str, Any] | None = None
        for row in range(rows):
            nibbles: list[int] = []
            for byte in packed[row].tolist():
                nibbles.extend(
                    [byte & 0xF, byte >> 4]
                    if order == "low_nibble_first"
                    else [byte >> 4, byte & 0xF]
                )
            products = dequantize_to_bf16_values(
                nibbles, scale_bytes[row].tolist(), group=group
            )
            for index, (product, value) in enumerate(
                zip(products, vendor_values[row])
            ):
                checked += 1
                if Fraction(value) != product:
                    mismatches += 1
                    if first is None:
                        first = {
                            "row": row,
                            "element": index,
                            "reference_exact_product": str(product),
                            "vendor_value": repr(value),
                        }
        findings[order] = {
            "elements_checked": checked,
            "mismatches": mismatches,
            "exact_agreement": mismatches == 0,
            "first_mismatch": first,
        }
    determined = [
        order for order, row in findings.items() if row["exact_agreement"]
    ]
    return {
        "grade": "executed",
        "contract": CONTRACT,
        "vendor_symbol": "kernel.fp4_act_quant",
        "reference": "runtime.reference.fp4_kv.dequantize_to_bf16_values",
        "scale_group": group,
        "scale_dtype": "torch.float8_e4m3fn",
        "latent_elements": width,
        "rows": rows,
        "seconds": round(elapsed, 3),
        "element_packing_order": determined[0] if len(determined) == 1 else None,
        "packing_order_determined": len(determined) == 1,
        "orders_tried": findings,
        "comparison": "exact rational equality, not a tolerance",
        "reference_reproduces_vendor_dequantize": bool(determined),
        "what_this_establishes": (
            "the E2M1 and E4M3FN field definitions in runtime/reference/fp4_kv.py "
            "reproduce the pinned kernel's own dequantized reconstruction exactly, "
            "over every element checked, for the released latent extent and the "
            "released scale group"
        ),
        "what_this_does_not_establish": [
            "the FORWARD direction: quantize_group_to_fp4 is documented as "
            "representative and is not compared here",
            "any released latent value: the input is a sample, not a checkpoint row",
            "that the accelerator's FP8 destination format loses nothing; the "
            "reference states BF16 represents every product exactly and that is "
            "what is checked, not the FP8 rounding",
        ],
        "storage_note": (
            "fp4_act_quant(inplace=True) writes DEQUANTIZED values back at the "
            "INPUT dtype, so on the vendor's own reference path the compressed KV "
            "cache holds bfloat16 round-tripped values and the FP4 codes are "
            "never stored. That is why the measured main entry width is the "
            "bfloat16 width and not the FP4 serving recipe"
        ),
    }


# ---------------------------------------------------------------------------
# stage: index scans, which is what the V4 ladder got wrong
# ---------------------------------------------------------------------------


def _init_vendor_parameters(module: Any, generator: Any, scale: float) -> None:
    """Fill a vendor module's parameters so its own forward can run.

    Block scales are set to one and everything else to a small normal sample.
    These are NOT released weights: this stage measures HOW MUCH a layer reads,
    which is decided by the released shapes and the released selection rules and
    not by any weight value.  No output value from this stage is reported.
    """
    import torch  # noqa: PLC0415

    for parameter in module.parameters():
        with torch.no_grad():
            shape = tuple(parameter.shape)
            if parameter.dtype == torch.float8_e8m0fnu:
                filled = torch.ones(shape, dtype=torch.float32, device="cpu")
            else:
                filled = (
                    torch.randn(
                        shape, generator=generator, dtype=torch.float32, device="cpu"
                    )
                    * scale
                )
            parameter.copy_(filled.to(parameter.dtype))


def sparse_attn_device_limit(vendor: Any, args: Any) -> dict[str, Any]:
    """Attempt the released ``sparse_attn`` and record what the device said.

    This does not MODEL the kernel's shared-memory request -- an arithmetic
    guess at a generated kernel's allocation would be a number nobody measured.
    It launches the pinned kernel at the released ``n_heads`` and ``head_dim``
    with the smallest possible operands and records the outcome verbatim, beside
    the device's own limits.
    """
    import torch  # noqa: PLC0415

    if not torch.cuda.is_available():
        return {"attempted": False, "runnable": False, "reason": "no CUDA device"}
    properties = torch.cuda.get_device_properties(0)
    record: dict[str, Any] = {
        "attempted": True,
        "device": properties.name,
        "compute_capability": list(torch.cuda.get_device_capability(0)),
        "shared_memory_per_block_bytes": int(properties.shared_memory_per_block),
        "shared_memory_per_block_optin_bytes": int(
            getattr(properties, "shared_memory_per_block_optin", 0)
        ),
        "launched_at": {
            "n_heads": int(args.n_heads),
            "head_dim": int(args.head_dim),
            "queries": 1,
            "topk": 64,
            "note": "n_heads and head_dim are the released values",
        },
    }
    try:
        heads, dim = int(args.n_heads), int(args.head_dim)
        query = torch.zeros((1, 1, heads, dim), dtype=torch.bfloat16, device="cuda")
        kv = torch.zeros((1, 64, dim), dtype=torch.bfloat16, device="cuda")
        sink = torch.zeros((heads,), dtype=torch.float32, device="cuda")
        idxs = torch.zeros((1, 1, 64), dtype=torch.int32, device="cuda")
        out = vendor.sparse_attn(query, kv, sink, idxs, dim**-0.5)
        torch.cuda.synchronize()
        record["runnable"] = True
        record["output_shape"] = [int(value) for value in out.shape]
    except Exception as error:
        record["runnable"] = False
        record["error_type"] = type(error).__name__
        record["error_verbatim"] = str(error).strip().splitlines()[-1][:300]
        record["consequence"] = (
            "model.sparse_attn cannot launch on this device, so the complete "
            "Attention.forward and therefore the greedy token ladder cannot run "
            "here. Indexer.forward runs BEFORE sparse_attn inside "
            "Attention.forward and is exercised directly below"
        )
    return record


def measure_index_scans(
    vendor: Any,
    args: Any,
    max_seq_len: int,
    decode_start_pos: int,
    prefill_tokens: int,
) -> dict[str, Any]:
    """Run the WRAPPED ``Indexer.forward`` and measure what it scored.

    This is the stage the V4 lesson is about.  It exercises the pinned indexer on
    both branches that exist -- the candidate SOURCE layer and a layer that
    CONSUMES the pool -- in both phases, and records, per layer:

    * ``index_positions_scored``: how many compressed positions the vendor's own
      ``einsum`` scored.  The pinned ``Indexer.forward`` slices
      ``shared_attn.index_k[:bsz, : end_pos // ratio]`` and scores ALL of it,
      then masks.  So a Reindex layer's SCAN is the full reachable width;
    * ``index_positions_admitted``: how many the candidate mask left finite,
      which is bounded by ``candidate_topk_blocks * candidate_block_size``.

    Those two are different numbers and the profile charges one of them, which
    is exactly the sort of thing that is invisible unless the indexer is
    wrapped.  Both are reported; neither is corrected into the other.

    ``decode_start_pos`` is chosen large enough that the candidate bound BINDS:
    a decode query reaching more compressed positions than the pool can hold is
    the only configuration in which the two numbers can differ, and a stage that
    never reaches it would report agreement it had not tested.
    """
    import torch  # noqa: PLC0415

    torch.cuda.set_device(0)
    #: inference/generate.py sets the default device before the first forward;
    #: get_window_topk_idxs and the indexer's own aranges rely on it.
    torch.set_default_device("cuda")
    generator = torch.Generator(device="cpu").manual_seed(411)
    rows: list[dict[str, Any]] = []
    bound = int(args.candidate_topk_blocks) * int(args.candidate_block_size)

    #: The candidate source first: it is what publishes the pool every later
    #: layer reads, so the order is the released order, not a convenience.
    source_layer = int(args.candidate_source_layer)
    consumer_layer = next(
        (
            layer
            for layer in args.index_source_layers
            if layer > source_layer
        ),
        None,
    )
    if consumer_layer is None:
        raise OracleError(
            "the released config has no index source layer after the candidate "
            "source, so the pool-consuming branch cannot be exercised"
        )

    built: dict[int, Any] = {}
    for layer_id in (source_layer, int(consumer_layer)):
        with torch.device("cuda"):
            attention = vendor.Attention(layer_id, args)
        _init_vendor_parameters(attention, generator, 0.05)
        built[layer_id] = attention

    def run(layer_id: int, start_pos: int, tokens: int, phase: str) -> dict[str, Any]:
        attention = built[layer_id]
        indexer = attention.indexer
        if indexer is None:
            raise OracleError(f"layer {layer_id} carries no indexer")
        if indexer.freqs_cis is None:
            #: Exactly what Attention._compress_topk_idxs does.
            indexer.freqs_cis = attention.freqs_cis
        hidden = (
            torch.randn(
                (1, tokens, args.dim),
                generator=generator,
                dtype=torch.float32,
                device="cpu",
            )
            * 0.5
        ).to(torch.bfloat16).to("cuda")
        #: Both operands are produced by the vendor's own modules.
        qr = attention.q_norm(attention.wq_a(hidden))
        latent = (
            attention.compressor(hidden, start_pos)
            if attention.compressor is not None
            else None
        )
        offset = (
            min(tokens, int(args.window_size))
            if start_pos == 0
            else int(args.window_size)
        )
        #: An Indexer does not carry a layer id, so this stage says which layer
        #: it is driving.  Inside a real Attention.forward the wrap sets the same
        #: field from self.layer_id.
        COUNTERS.layer_id = layer_id
        before = COUNTERS.indexer_calls
        #: The per-layer counters ACCUMULATE across calls, so a rung reports the
        #: delta this call added.  Reporting the running total would have made
        #: the decode rung look as if it scanned the prefill's positions again.
        baseline = dict(COUNTERS.layers.get(layer_id, {}))
        started = time.time()
        selected = indexer(hidden, qr, latent, start_pos, offset)
        torch.cuda.synchronize()
        elapsed = time.time() - started
        fired = COUNTERS.indexer_calls - before
        if fired != 1:
            raise OracleError(
                f"Indexer.forward at layer {layer_id} fired the wrap {fired} "
                "times; the count is not evidence"
            )
        total = dict(COUNTERS.layers[layer_id])
        measured = {
            "index_positions_scored": total["index_positions_scored"]
            - int(baseline.get("index_positions_scored", 0)),
            "index_bytes_scored": total["index_bytes_scored"]
            - int(baseline.get("index_bytes_scored", 0)),
            "index_positions_admitted": total["index_positions_admitted"],
        }
        ratio = int(args.compress_ratios[layer_id])
        reachable = (start_pos + tokens) // ratio if ratio else 0
        candidates = vendor.shared_attn.candidates
        return {
            "layer_id": layer_id,
            "phase": phase,
            "role": (
                "candidate_source"
                if indexer.is_candidate_source
                else ("pool_consumer" if indexer.uses_candidates else "independent")
            ),
            "compress_ratio": ratio,
            "owns_index_keys": bool(indexer.owns_k),
            "start_pos": start_pos,
            "queries": tokens,
            "reachable_compressed_positions_per_query": reachable,
            "index_positions_scored_total": measured["index_positions_scored"],
            "index_positions_scored_per_query": (
                measured["index_positions_scored"] / tokens if tokens else None
            ),
            "index_positions_admitted_total": measured["index_positions_admitted"],
            "candidate_pool_position_bound": bound,
            "selected_per_query": int(selected.size(-1)),
            "index_topk_configured": int(args.index_topk),
            "candidate_mask_shape": (
                None if candidates is None else [int(v) for v in candidates.shape]
            ),
            "measured_index_entry_bytes": (
                COUNTERS.widths.get("index", {}).get("entry_bytes")
            ),
            "index_bytes_scored": measured["index_bytes_scored"],
            "layer_running_total_positions_scored": total["index_positions_scored"],
            "seconds": round(elapsed, 3),
            "scan_exceeds_pool_bound": (
                measured["index_positions_scored"] > bound * tokens
            ),
        }

    #: Prefill exercises the per-query masking branch, where `compress_lens` is
    #: a tensor and every query pins a different block.
    for layer_id in (source_layer, int(consumer_layer)):
        rows.append(run(layer_id, 0, prefill_tokens, "prefill"))
    #: Decode exercises the branch where `compress_lens` is a plain int, and at a
    #: start position where the candidate bound BINDS.
    for layer_id in (source_layer, int(consumer_layer)):
        rows.append(run(layer_id, decode_start_pos, 1, "decode"))

    torch.set_default_device("cpu")
    binding = [row for row in rows if row["scan_exceeds_pool_bound"]]
    return {
        "grade": "executed",
        "vendor_symbol": "model.Indexer.forward",
        "wrapped_before_first_run": True,
        "allocation": {"max_seq_len": max_seq_len, "max_batch_size": 1},
        "candidate_pool_position_bound": bound,
        "bound_derivation": (
            "candidate_topk_blocks * candidate_block_size, both read from the "
            "released config at run time"
        ),
        "rows": rows,
        "rungs_where_scan_exceeds_the_pool_bound": len(binding),
        "finding": (
            "the pinned Indexer.forward scores every reachable compressed "
            "position and masks afterwards, so a pool-consuming layer's SCAN is "
            "the full reachable width while its ADMITTED population is bounded "
            "by candidate_topk_blocks * candidate_block_size. These are "
            "different measurements and both are reported"
        ),
        "adaptations": [
            {
                "id": "indexer_exercised_without_sparse_attn",
                "vendor_symbol": "model.Indexer.forward",
                "reason": (
                    "model.sparse_attn cannot launch on this device (see "
                    "sparse_attn_device_limit), so the enclosing "
                    "Attention.forward cannot complete"
                ),
                "change": (
                    "Indexer.forward is called directly, with `qr` and `latent` "
                    "produced by the same vendor modules Attention.forward "
                    "produces them with, and `offset` the value "
                    "Attention.forward passes"
                ),
                "fidelity": (
                    "the indexer body is the pinned body, unmodified, and the "
                    "counts come from its own operands. What is NOT established "
                    "is any value downstream of it: no attention output, no "
                    "logit and no token is produced or claimed"
                ),
            },
            {
                "id": "index_scan_weights_not_released",
                "vendor_symbol": "model.Indexer",
                "reason": (
                    "streaming the released indexer rows needs the layer-"
                    "streaming engine the token stage lists as absent"
                ),
                "change": "the indexer's parameters are a small normal sample",
                "fidelity": (
                    "a scan WIDTH is set by the released shapes and the released "
                    "selection rules, not by a weight value, and no value "
                    "produced by these parameters is reported. WHICH positions "
                    "win is weight-dependent and is NOT claimed here"
                ),
            },
        ],
    }


# ---------------------------------------------------------------------------
# stage: the Engram gate, vendor against both contracts
# ---------------------------------------------------------------------------


def compare_engram_gate(vendor: Any, args: Any, device: str) -> dict[str, Any]:
    """Run the pinned ``Engram.forward`` and report the counters and the gate.

    This runs the REAL wrapped ``Engram.forward``, so it is also the evidence
    that the Engram wrap fires and counts.  The table is allocated with a small
    row count -- the released table is 384,006,168 rows of 264 B (about 101 GB)
    and does not fit this device -- which is declared as an adaptation.  The row
    WIDTH is measured from the buffer either way, and the gate arithmetic does
    not depend on the row count.
    """
    import torch  # noqa: PLC0415
    from engram import EngramLayout  # noqa: PLC0415

    #: Released Engram geometry, with the table row count reduced.  Everything
    #: the gate touches -- hc_mult, dim, n_heads, head_dim, orders, norm_eps --
    #: is the released value.
    from dataclasses import replace  # noqa: PLC0415

    rows = 4096
    reduced = replace(
        args,
        engram_layer_ids=(args.engram_layer_ids[0],),
        engram_num_embeddings=(rows,),
    )
    layout = EngramLayout.from_args(reduced)
    if layout is None:
        raise OracleError("the released config declares no Engram layer")
    layer_id = int(args.engram_layer_ids[0])
    engram = vendor.Engram(reduced, layer_id, layout).to(device)

    generator = torch.Generator(device="cpu").manual_seed(410)

    def fill(parameter: Any, scale: float) -> None:
        sample = torch.randn(
            tuple(parameter.shape), generator=generator, dtype=torch.float32
        )
        with torch.no_grad():
            parameter.copy_((sample * scale).to(parameter.dtype).to(device))

    def ones(parameter: Any) -> None:
        with torch.no_grad():
            parameter.copy_(
                torch.ones(tuple(parameter.shape), dtype=torch.float32)
                .to(parameter.dtype)
                .to(device)
            )

    fill(engram.embed.weight, 1.0)
    ones(engram.embed.scale)
    fill(engram.wkv.weight, 0.05)
    ones(engram.wkv.scale)
    fill(engram.q_weight, 1.0)
    fill(engram.k_weight, 1.0)

    tokens = 3
    hidden = (
        torch.randn(
            (1, tokens, args.hc_mult, args.dim), generator=generator, dtype=torch.float32
        )
        .to(torch.bfloat16)
        .to(device)
    )
    hash_ids = torch.randint(
        0, rows, (1, tokens, layout.n_heads * (layout.max_ngram_size - 1)),
        generator=generator,
    ).to(device)

    before = COUNTERS.engram_calls
    started = time.time()
    output = engram(hidden, hash_ids)
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.time() - started
    fired = COUNTERS.engram_calls - before

    #: Recompute the pinned expression DAG independently of the module, to show
    #: which expression the module evaluated.  This is a transcription check,
    #: not an independent numeric reference: it uses the same library.
    with torch.no_grad():
        kv = engram.wkv(engram.embed(hash_ids).flatten(-2))
        key, value = kv.split([engram.hc_mult * engram.dim, engram.dim], dim=-1)
        key = key.float().unflatten(-1, (engram.hc_mult, engram.dim))
        weight = engram.q_weight.float() * engram.k_weight.float()
        stream, eps = hidden.float(), engram.eps
        rstd = torch.rsqrt(stream.square().mean(-1) + eps) * torch.rsqrt(
            key.square().mean(-1) + eps
        )
        dot = (stream * weight * key).sum(-1) * rstd * engram.dim**-0.5
        gate = torch.sigmoid(
            torch.copysign(dot.abs().clamp_min(engram.clamp_value).sqrt(), dot)
        )
        transcribed = (
            stream + gate.unsqueeze(-1) * value.float().unsqueeze(-2)
        ).to(hidden.dtype)
    difference = float((output.float() - transcribed.float()).abs().max().item())

    return {
        "grade": "executed",
        "vendor_symbol": "model.Engram.forward",
        "device": device,
        "seconds": round(elapsed, 3),
        "engram_forward_calls_this_stage": fired,
        "wrap_fired": fired > 0,
        "released_values_used": {
            "hc_mult": int(args.hc_mult),
            "dim": int(args.dim),
            "engram_n_heads": int(layout.n_heads),
            "engram_head_dim": int(layout.head_dim),
            "engram_max_ngram_size": int(layout.max_ngram_size),
            "n_hash_cols": int(layout.n_heads * (layout.max_ngram_size - 1)),
            "norm_eps": float(engram.eps),
            "clamp_value": float(engram.clamp_value),
        },
        "measured_row_bytes": int(
            engram.embed.weight.size(-1) * engram.embed.weight.element_size()
            + engram.embed.scale.size(-1) * engram.embed.scale.element_size()
        ),
        "adaptations": [
            {
                "id": "engram_table_rows_reduced",
                "vendor_symbol": "model.ParallelEngramEmbedding",
                "reason": (
                    "the released table for this layer is "
                    f"{args.engram_num_embeddings[0]:,} rows of 264 B, about "
                    "101 GB, and ParallelEngramEmbedding.forward calls "
                    "F.embedding over the whole table, so it cannot be "
                    "materialised on this device"
                ),
                "change": f"the table is allocated with {rows:,} rows",
                "fidelity": (
                    "the row WIDTH is measured from the buffer and is unchanged; "
                    "the gate arithmetic depends on the row VALUES, not the row "
                    "count. This stage is therefore evidence about the gate "
                    "expression and the wrap, and NOT about any released row"
                ),
            }
        ],
        "transcription_check": {
            "max_abs_difference": difference,
            "identical": difference == 0.0,
            "what_this_shows": (
                "the module evaluated the expression DAG recorded in "
                "runtime.reference.engram's D1-D4 comment; it does NOT show "
                "agreement with an independent numeric reference, because both "
                "sides here are torch"
            ),
        },
        "pinned_form_against_contract_v1": prove_pinned_form_differs(),
        "divergences": list(engram_gate_pinned_divergences()),
    }


# ---------------------------------------------------------------------------
# stage: the blocked token ladder, stated precisely
# ---------------------------------------------------------------------------


def token_stage_prerequisites(snapshot: Path, lock_path: Path) -> dict[str, Any]:
    """State exactly what a greedy-token run needs and what is missing.

    ``complete_but_failing`` with the reason is useful; a token that was not
    computed is not.  This stage produces no token and says so.
    """
    streaming = REPO / "runtime/reference/deepseek_v41_oracle.py"
    tokenizer = REPO / "compiler/frontend/deepseek_v41_tokenizer.py"
    workloads = REPO / "build/workloads" / MODEL_ID / "index.json"
    prerequisites = [
        {
            "id": "streaming_engine",
            "requirement": (
                "a V4.1 layer-streaming engine, the analogue of "
                "runtime/reference/deepseek_v4_oracle.py::StreamingDeepSeekV4, "
                "that materialises one block and one routed expert at a time "
                "from the 48 released shards"
            ),
            "path": str(streaming.relative_to(REPO)),
            "present": streaming.is_file(),
            "why_needed": (
                "the released checkpoint is 510,286,023,000 bytes of weights "
                "against 101.97 GB of device memory, so no run holds the model"
            ),
        },
        {
            "id": "engram_table_residency",
            "requirement": (
                "a residency policy for the two Engram tables (202.76 GB) that "
                "ParallelEngramEmbedding.forward's F.embedding over the whole "
                "table can be served from"
            ),
            "path": None,
            "present": False,
            "why_needed": (
                "plan section 3.4 decides where the tables live; a host-gather "
                "adaptation would have to be declared and is not written"
            ),
        },
        {
            "id": "tokenizer_for_compressed_map",
            "requirement": (
                "a tokenizer NgramHashState.__init__ can build the compressed "
                "token map from, asserting 99,092 compressed ids"
            ),
            "path": str(tokenizer.relative_to(REPO)),
            "present": tokenizer.is_file(),
            "why_needed": (
                "every Engram hash multiplier derives from the compressed vocab "
                "size, so a mismatch rehashes the whole table"
            ),
        },
        {
            "id": "workload_documents",
            "requirement": "the pinned V4.1 workload documents and index",
            "path": str(workloads.relative_to(REPO)),
            "present": workloads.is_file(),
            "why_needed": "the prompts the ladder decodes",
        },
    ]
    missing = [row["id"] for row in prerequisites if not row["present"]]
    return {
        "grade": "not_run",
        "tokens_produced": 0,
        "selection_rule_that_would_be_used": "greedy_lowest_token_id_argmax",
        "artifacts_not_produced": dict(TOKEN_OUTPUTS),
        "prerequisites": prerequisites,
        "missing_prerequisites": missing,
        "blocked": bool(missing),
        "command_that_would_run_it": (
            "PATH=/usr/local/cuda/bin:$PATH tools/run_deepseek_v41_reference_oracle.py "
            f"--stage tokens --snapshot {snapshot} --lock {lock_path} "
            "--only TA-DS41-CHAT-1-P32 --max-new-tokens 32 "
            "--output results/abi3/deepseek_v41_reference_oracle_prefix.json"
        ),
        "note": (
            "no number in this record is a token, a TPOT or a measurement of "
            "the model's output. Planned behaviour is not implemented evidence"
        ),
    }


# ---------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------


def environment() -> dict[str, Any]:
    """What ran this, measured.  A capability claim is checked, not assumed."""
    import torch  # noqa: PLC0415

    record: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
        "nvcc_on_path": None,
        "device": None,
        "compute_capability": None,
        "device_total_memory_bytes": None,
        "nvml": "unavailable",
    }
    try:
        import subprocess  # noqa: PLC0415

        found = subprocess.run(
            ["which", "nvcc"], capture_output=True, text=True, check=False
        )
        if found.returncode == 0:
            nvcc = found.stdout.strip()
            version = subprocess.run(
                [nvcc, "--version"], capture_output=True, text=True, check=False
            )
            record["nvcc_on_path"] = {
                "path": nvcc,
                "release": next(
                    (
                        line.strip()
                        for line in version.stdout.splitlines()
                        if "release" in line
                    ),
                    None,
                ),
            }
    except Exception as error:  # pragma: no cover - diagnostic only
        record["nvcc_on_path"] = {"error": repr(error)}
    if torch.cuda.is_available():
        try:
            probe = torch.zeros(8, device="cuda")
            record["device_allocation_verified"] = float(probe.sum().item()) == 0.0
            record["device"] = torch.cuda.get_device_name(0)
            record["compute_capability"] = list(torch.cuda.get_device_capability(0))
            record["device_total_memory_bytes"] = int(
                torch.cuda.get_device_properties(0).total_memory
            )
        except Exception as error:
            record["device_allocation_verified"] = False
            record["device_error"] = repr(error)
    try:
        import subprocess  # noqa: PLC0415

        smi = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, check=False
        )
        record["nvml"] = (
            "available" if smi.returncode == 0 else smi.stderr.strip()[:200]
        )
    except Exception as error:  # pragma: no cover - diagnostic only
        record["nvml"] = repr(error)
    return record


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

ALL_STAGES = (
    "widths",
    "fp4_kv",
    "index_scans",
    "instrumentation",
    "candidate_pool",
    "engram_gate",
    "tokens",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--stage",
        action="append",
        choices=("all", *ALL_STAGES),
        help="stage to run; repeatable. Default: all",
    )
    parser.add_argument(
        "--max-seq-len",
        type=int,
        default=4096,
        help=(
            "cache ALLOCATION length. Not a model bound and not a width: the "
            "widths reported are read off the buffers"
        ),
    )
    parser.add_argument("--candidate-trials", type=int, default=64)
    parser.add_argument(
        "--index-max-seq-len",
        type=int,
        default=24_576,
        help="cache allocation for the index-scan stage",
    )
    parser.add_argument(
        "--index-decode-start-pos",
        type=int,
        default=20_000,
        help=(
            "decode position for the index-scan stage. Must be large enough "
            "that the candidate pool bound binds, or the stage reports an "
            "agreement it did not test"
        ),
    )
    parser.add_argument("--index-prefill-tokens", type=int, default=256)
    parser.add_argument("--fp4-rows", type=int, default=8)
    parser.add_argument(
        "--device",
        default="auto",
        choices=("auto", "cpu", "cuda"),
        help="device for the stages that call a quantized vendor kernel",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results/abi3/deepseek_v41_reference_oracle_probe.json",
    )
    args = parser.parse_args()

    stages = set(ALL_STAGES) if not args.stage or "all" in args.stage else set(args.stage)

    started = time.time()
    notes: list[str] = []

    def note(message: str) -> None:
        notes.append(message)
        print(message, flush=True)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "role": "external_reference_oracle",
        "role_note": (
            "an external comparator over the vendor's own pinned code. It never "
            "produces accelerator tokens and never supplies an activation "
            "(ADR-003 section 18)"
        ),
        "model_id": MODEL_ID,
        "revision": REVISION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "argv": sys.argv[1:],
        "stages_requested": sorted(stages),
        "producer": producer_identity(),
        "environment": environment(),
    }

    try:
        report["vendor_sources"] = verify_vendor_sources(args.snapshot)
        note(
            "vendor sources verified: "
            + ", ".join(
                f"{name}={digest[:12]}"
                for name, digest in sorted(
                    report["vendor_sources"]["observed_sha256"].items()
                )
            )
        )
        report["checkpoint_lock"] = checkpoint_lock_identity(args.lock)
        lock = report["checkpoint_lock"]
        if lock.get("present"):
            note(
                f"checkpoint lock {lock['lock_id'][:16]}: "
                f"{lock['tensor_count']:,} tensors, {lock['payload_bytes']:,} bytes"
            )

        vendor = import_vendor(args.snapshot)

        #: THE WRAPS GO ON FIRST.  Before any vendor module is constructed.
        report["instrumentation"] = install_counters(vendor)
        report["instrumentation"]["verification"] = verify_wraps_installed(vendor)
        note(
            "wrapped BEFORE the first run and verified by identity: "
            + ", ".join(report["instrumentation"]["wrapped_symbols"])
        )

        model_args = released_model_args(args.snapshot, vendor, args.max_seq_len)
        report["released_geometry"] = {
            "source": "config.json:text_config at the pinned revision",
            "n_layers": model_args.n_layers,
            "dim": model_args.dim,
            "head_dim": model_args.head_dim,
            "index_head_dim": model_args.index_head_dim,
            "window_size": model_args.window_size,
            "index_topk": model_args.index_topk,
            "candidate_source_layer": model_args.candidate_source_layer,
            "candidate_topk_blocks": model_args.candidate_topk_blocks,
            "candidate_block_size": model_args.candidate_block_size,
            "kv_source_layers": list(model_args.kv_source_layers),
            "index_source_layers": list(model_args.index_source_layers),
            "engram_layer_ids": list(model_args.engram_layer_ids),
            "engram_num_embeddings": list(model_args.engram_num_embeddings),
            "note": "read at run time; nothing above is transcribed in this tool",
        }

        device = args.device
        if device == "auto":
            import torch  # noqa: PLC0415

            device = "cuda" if torch.cuda.is_available() else "cpu"

        if "widths" in stages:
            measured = measure_entry_widths(vendor, model_args)
            recipe = profile_recipe_widths()
            report["entry_widths"] = {
                "measured": measured,
                "recipe": recipe,
                "comparison": compare_widths(measured, recipe),
            }
            for row in report["entry_widths"]["comparison"]["rows"]:
                note(
                    f"{row['role']:>6} entry: measured {row['measured_entry_bytes']} B "
                    f"(grade executed) against recipe {row['recipe_entry_bytes']} B "
                    f"(ratio {row['measured_over_recipe']:.4f})"
                    if row["measured_over_recipe"]
                    else f"{row['role']:>6} entry: measured "
                    f"{row['measured_entry_bytes']} B, no recipe width"
                )

        COUNTERS.enabled = True

        if "fp4_kv" in stages:
            report["fp4_kv"] = compare_fp4_kv(
                args.snapshot, model_args, args.fp4_rows
            )
            fp4 = report["fp4_kv"]
            if fp4["grade"] == "executed":
                order = fp4["orders_tried"][fp4["element_packing_order"]] if fp4[
                    "packing_order_determined"
                ] else None
                note(
                    "fp4 main KV: reference dequantize reproduces the pinned "
                    f"kernel exactly on {order['elements_checked']:,} elements "
                    f"({fp4['element_packing_order']}), mismatches "
                    f"{order['mismatches']}"
                    if order
                    else "fp4 main KV: packing order NOT determined; see orders_tried"
                )
            else:
                note(f"fp4 main KV stage not run: {fp4.get('reason')}")

        if "index_scans" in stages:
            index_args = released_model_args(
                args.snapshot, vendor, args.index_max_seq_len
            )
            report["sparse_attn_device_limit"] = sparse_attn_device_limit(
                vendor, index_args
            )
            limit = report["sparse_attn_device_limit"]
            note(
                f"sparse_attn launch attempted at the released n_heads/head_dim: "
                f"runnable={limit['runnable']}"
                + (
                    ""
                    if limit.get("runnable")
                    else f"; {limit.get('error_type')}: "
                    f"{limit.get('error_verbatim')}; device allows "
                    f"{limit.get('shared_memory_per_block_optin_bytes')} B "
                    "of opt-in shared memory per block"
                )
            )
            report["index_scans"] = measure_index_scans(
                vendor,
                index_args,
                args.index_max_seq_len,
                args.index_decode_start_pos,
                args.index_prefill_tokens,
            )
            for row in report["index_scans"]["rows"]:
                note(
                    f"  layer {row['layer_id']:>2} {row['phase']:<7} "
                    f"{row['role']:<16} scored "
                    f"{row['index_positions_scored_total']:>9,} positions "
                    f"({row['index_positions_scored_per_query']:,.0f}/query), "
                    f"admitted {row['index_positions_admitted_total']}, "
                    f"pool bound {row['candidate_pool_position_bound']:,}, "
                    f"selected {row['selected_per_query']}/query"
                )
            note(
                "rungs where the scan exceeds the pool bound: "
                f"{report['index_scans']['rungs_where_scan_exceeds_the_pool_bound']}"
            )

        if "candidate_pool" in stages:
            report["candidate_pool"] = compare_candidate_pool(
                vendor, model_args, args.candidate_trials
            )
            pool = report["candidate_pool"]
            note(
                f"candidate pool: {pool['untied_agreements']}/"
                f"{pool['trials'] - pool['tied_rows_not_counted']} untied rows "
                f"identical, {pool['tied_rows_not_counted']} rows tied at the "
                f"threshold and not counted, "
                f"{len(pool['disagreements'])} disagreements"
            )

        if "engram_gate" in stages:
            report["engram_gate"] = compare_engram_gate(vendor, model_args, device)
            gate = report["engram_gate"]
            note(
                f"Engram.forward ran on {gate['device']} in {gate['seconds']} s; "
                f"the wrap fired {gate['engram_forward_calls_this_stage']} time(s); "
                f"measured row width {gate['measured_row_bytes']} B"
            )
            note(
                "pinned gate form against engram_gate_fp32_v1: gate codes differ = "
                f"{gate['pinned_form_against_contract_v1']['gate_codes_differ']}, "
                "outputs differ = "
                f"{gate['pinned_form_against_contract_v1']['outputs_differ']}"
            )

        if "instrumentation" in stages:
            #: What the wraps actually observed, and which of them fired.  A
            #: stage that ran vendor code and recorded zero is a failure.
            fired = {
                "Indexer.forward": COUNTERS.indexer_calls,
                "Engram.forward": COUNTERS.engram_calls,
                "Attention.forward": COUNTERS.attention_calls,
            }
            report["instrumentation"]["observed_calls"] = fired
            report["instrumentation"]["counters"] = COUNTERS.as_dict()
            unexercised = sorted(
                symbol for symbol, count in fired.items() if count == 0
            )
            report["instrumentation"]["unexercised_symbols"] = unexercised
            report["instrumentation"]["zero_is_not_a_count_note"] = (
                "a wrapped symbol with zero calls was NOT exercised by the "
                "stages that ran; it is listed rather than reported as zero, "
                "because a zero index-scan count is indistinguishable from an "
                "implementation that declined to scan (the V4 failure)"
            )
            note(
                "wrap calls observed: "
                + ", ".join(f"{name}={count}" for name, count in sorted(fired.items()))
            )
            if unexercised:
                note(
                    "NOT exercised by these stages (reported as unexercised, not "
                    "as zero): " + ", ".join(unexercised)
                )

        if "tokens" in stages:
            report["tokens"] = token_stage_prerequisites(args.snapshot, args.lock)
            blocked = report["tokens"]
            note(
                "token stage BLOCKED, missing: "
                + ", ".join(blocked["missing_prerequisites"])
            )

        report["status"] = "completed"
    except OracleError as error:
        report["status"] = "refused"
        report["refusal"] = str(error)
        note(f"REFUSED: {error}")
    except Exception as error:  # pragma: no cover - reported, never swallowed
        import traceback

        report["status"] = "failed"
        report["failure"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc().splitlines()[-12:],
        }
        note(f"FAILED: {type(error).__name__}: {error}")

    report["notes"] = notes
    report["elapsed_seconds"] = round(time.time() - started, 3)
    report["evidence_class"] = {
        "executed": [
            key
            for key in (
                "entry_widths",
                "fp4_kv",
                "index_scans",
                "candidate_pool",
                "engram_gate",
            )
            if key in report
        ],
        "not_run": ["tokens"] if "tokens" in report else [],
        "statement": (
            "nothing in this report is a TPOT, a throughput or a token. The "
            "widths and the comparisons are executed measurements of the "
            "vendor's own pinned code; the token ladder did not run"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.output}", flush=True)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
