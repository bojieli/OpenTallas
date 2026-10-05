"""Versioned Qwen long-acceptance context expansion.

The admitted V6 graph fixes every dynamic context symbol at 8,000 positions.
That is sufficient for the retained short diagnostic but not for an 8,000-token
prompt followed by 32 generated-token decisions: the latter commits 8,031 KV
rows.  This module derives a distinct 8,192-row graph profile without mutating
or broadening the admitted graph.

Only context bounds change.  Checkpoint bindings, operation order, tensors,
numeric contracts, state effects, source anchors, and model topology remain
byte-for-byte equal after the graph identity is excluded.  The independently
implemented checker in ``qwen_full_model_context_checking`` reconstructs the
same restriction without importing this module.
"""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .common import (
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    compute_graph_id,
    parse_production_model_graph,
)


PROFILE_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_context_profile.v1"
)
MODEL_ID = "qwen3-8b"
NUMERIC_PROFILE = "qwen3_bf16_gqa_target_v1"
BASE_GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
BASE_CONTEXT_CAPACITY = 8000
ACCEPTANCE_PROMPT_TOKENS = 8000
MINIMUM_GENERATED_DECISIONS = 32
REQUIRED_COMMITTED_ROWS = (
    ACCEPTANCE_PROMPT_TOKENS + MINIMUM_GENERATED_DECISIONS - 1
)
LONG_CONTEXT_CAPACITY = 8192
MAXIMUM_POSITION_EMBEDDINGS = 40960
PROFILE_NAME = "qwen3-8b-8000-prompt-32-decision-long-v1"


class QwenFullModelContextError(ArtifactError):
    """Raised when the Qwen context expansion is not exact and source-bound."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise QwenFullModelContextError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QwenFullModelContextError(f"{label} is not canonical JSON")
    return value


def _context_symbol(raw: Mapping[str, Any], symbol_id: str) -> dict[str, Any]:
    symbols = raw.get("symbols")
    if not isinstance(symbols, list):
        raise QwenFullModelContextError("base graph symbols are malformed")
    matches = [item for item in symbols if isinstance(item, dict) and item.get("id") == symbol_id]
    if len(matches) != 1:
        raise QwenFullModelContextError(
            f"base graph symbol {symbol_id!r} is missing or duplicated"
        )
    return matches[0]


def _validate_base_graph(raw: Mapping[str, Any]) -> None:
    try:
        model = parse_production_model_graph(raw)
    except ProductionModelGraphError as exc:
        raise QwenFullModelContextError(f"base graph admission failed: {exc}") from exc
    if (
        model.graph_id != BASE_GRAPH_ID
        or model.model_id != MODEL_ID
        or model.numeric_profile != NUMERIC_PROFILE
        or len(model.operations) != 617
        or len(model.tensors) != 1053
        or len(model.state_resources) != 36
        or model.source.get("repository") != "Qwen/Qwen3-8B"
        or model.source.get("revision")
        != "b968826d9c46dd6066d109eabc6255188de91218"
    ):
        raise QwenFullModelContextError("base graph is not the admitted Qwen V6 graph")
    expected_symbols = {
        "context_capacity": {
            "binding": {"kind": "compile_time"},
            "default": BASE_CONTEXT_CAPACITY,
            "id": "context_capacity",
            "maximum": BASE_CONTEXT_CAPACITY,
            "minimum": BASE_CONTEXT_CAPACITY,
            "multiple_of": BASE_CONTEXT_CAPACITY,
        },
        "position_end": {
            "binding": {"field": "position_end", "kind": "request"},
            "default": 1,
            "id": "position_end",
            "maximum": BASE_CONTEXT_CAPACITY,
            "minimum": 1,
            "multiple_of": 1,
        },
        "position_start": {
            "binding": {"field": "position_start", "kind": "request"},
            "default": 0,
            "id": "position_start",
            "maximum": BASE_CONTEXT_CAPACITY - 1,
            "minimum": 0,
            "multiple_of": 1,
        },
        "span_tokens": {
            "binding": {"field": "span_tokens", "kind": "request"},
            "default": 1,
            "id": "span_tokens",
            "maximum": BASE_CONTEXT_CAPACITY,
            "minimum": 1,
            "multiple_of": 1,
        },
    }
    for symbol_id, expected in expected_symbols.items():
        if _context_symbol(raw, symbol_id) != expected:
            raise QwenFullModelContextError(
                f"base graph symbol {symbol_id!r} is not the admitted V6 contract"
            )
    entrypoints = raw.get("entrypoints")
    if not isinstance(entrypoints, list) or len(entrypoints) != 2:
        raise QwenFullModelContextError("base graph entrypoints are malformed")
    for index, entrypoint in enumerate(entrypoints):
        if not isinstance(entrypoint, dict):
            raise QwenFullModelContextError(f"base entrypoint {index} is malformed")
        predicate = entrypoint.get("predicate")
        terms = predicate.get("terms") if isinstance(predicate, dict) else None
        if (
            not isinstance(terms, list)
            or len(terms) not in {2, 3}
            or terms[1]
            != {
                "kind": "compare",
                "operator": "le",
                "symbol": "position_end",
                "value": BASE_CONTEXT_CAPACITY,
            }
        ):
            raise QwenFullModelContextError(
                f"base entrypoint {index} context predicate differs"
            )


def _expand_raw(base: Mapping[str, Any]) -> dict[str, Any]:
    expanded = copy.deepcopy(dict(base))
    context = _context_symbol(expanded, "context_capacity")
    context.update(
        {
            "default": LONG_CONTEXT_CAPACITY,
            "maximum": LONG_CONTEXT_CAPACITY,
            "minimum": LONG_CONTEXT_CAPACITY,
            "multiple_of": LONG_CONTEXT_CAPACITY,
        }
    )
    _context_symbol(expanded, "position_end")["maximum"] = LONG_CONTEXT_CAPACITY
    _context_symbol(expanded, "position_start")["maximum"] = (
        LONG_CONTEXT_CAPACITY - 1
    )
    _context_symbol(expanded, "span_tokens")["maximum"] = LONG_CONTEXT_CAPACITY
    for entrypoint in expanded["entrypoints"]:
        entrypoint["predicate"]["terms"][1]["value"] = LONG_CONTEXT_CAPACITY
    expanded["graph_id"] = compute_graph_id(expanded)
    return expanded


def build_qwen_long_context_profile(
    base_graph_path: Path,
) -> tuple[ProductionModelGraph, dict[str, Any]]:
    """Derive the immutable 8,192-row graph and its scoped profile record."""

    if REQUIRED_COMMITTED_ROWS > LONG_CONTEXT_CAPACITY:
        raise QwenFullModelContextError("long context does not cover acceptance rows")
    if LONG_CONTEXT_CAPACITY > MAXIMUM_POSITION_EMBEDDINGS:
        raise QwenFullModelContextError("long context exceeds pinned model positions")
    base = _load_canonical(Path(base_graph_path), "admitted Qwen V6 graph")
    _validate_base_graph(base)
    expanded_raw = _expand_raw(base)
    try:
        expanded = parse_production_model_graph(expanded_raw)
    except ProductionModelGraphError as exc:
        raise QwenFullModelContextError(
            f"expanded graph admission failed: {exc}"
        ) from exc
    base_payload = canonical_json_bytes(base)
    expanded_payload = canonical_json_bytes(expanded.to_dict())
    checkpoint_ids = {
        tensor.binding.checkpoint_lock_id
        for tensor in expanded.tensors
        if tensor.binding is not None
    }
    if len(checkpoint_ids) != 1:
        raise QwenFullModelContextError(
            "expanded graph checkpoint binding is not singular"
        )
    body = {
        "acceptance_workload": {
            "generated_decisions_minimum": MINIMUM_GENERATED_DECISIONS,
            "prompt_tokens_exact": ACCEPTANCE_PROMPT_TOKENS,
            "required_committed_rows": REQUIRED_COMMITTED_ROWS,
        },
        "base_context_capacity_tokens": BASE_CONTEXT_CAPACITY,
        "base_graph_id": BASE_GRAPH_ID,
        "base_graph_payload_sha256": hashlib.sha256(base_payload).hexdigest(),
        "checkpoint_lock_id": checkpoint_ids.pop(),
        "claim_boundary": {
            "allocation_capacity_only": True,
            "exact_8000_token_acceptance_executed": False,
            "qwen_8192_boundary_executed": False,
            "timing_or_performance": False,
        },
        "expanded_graph_id": expanded.graph_id,
        "expanded_graph_payload_sha256": hashlib.sha256(expanded_payload).hexdigest(),
        "long_context_capacity_tokens": LONG_CONTEXT_CAPACITY,
        "maximum_position_embeddings": MAXIMUM_POSITION_EMBEDDINGS,
        "model_id": MODEL_ID,
        "profile_name": PROFILE_NAME,
        "schema": PROFILE_SCHEMA,
        "transformation": {
            "entrypoint_context_predicates_changed": 2,
            "numeric_contracts_changed": 0,
            "operation_records_changed": 0,
            "source_records_changed": 0,
            "state_resource_records_changed": 0,
            "symbol_records_changed": 4,
            "tensor_records_changed": 0,
        },
    }
    return expanded, _identified(body, "profile_id")


def publish_qwen_long_context_profile(
    base_graph_path: Path,
    graph_output_path: Path,
    profile_output_path: Path,
) -> tuple[ProductionModelGraph, dict[str, Any]]:
    """Publish a graph/profile pair atomically and without overwriting evidence."""

    graph, profile = build_qwen_long_context_profile(base_graph_path)
    outputs = (
        (Path(graph_output_path), canonical_json_bytes(graph.to_dict())),
        (Path(profile_output_path), canonical_json_bytes(profile)),
    )
    if outputs[0][0].parent != outputs[1][0].parent:
        raise QwenFullModelContextError("context outputs must share one directory")
    parent = outputs[0][0].parent
    parent.mkdir(parents=True, exist_ok=True)
    if any(path.exists() for path, _ in outputs):
        raise QwenFullModelContextError("context profile output already exists")
    temporaries: list[Path] = []
    published: list[Path] = []
    try:
        for output, payload in outputs:
            descriptor, temporary_name = tempfile.mkstemp(
                dir=parent, prefix=f".{output.name}.", suffix=".tmp"
            )
            temporary = Path(temporary_name)
            temporaries.append(temporary)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        for (output, _), temporary in zip(outputs, temporaries, strict=True):
            os.link(temporary, output)
            published.append(output)
    except OSError as exc:
        for output in published:
            output.unlink(missing_ok=True)
        raise QwenFullModelContextError(
            f"cannot publish context profile atomically: {exc}"
        ) from exc
    finally:
        for temporary in temporaries:
            temporary.unlink(missing_ok=True)
    return graph, profile


__all__ = [
    "ACCEPTANCE_PROMPT_TOKENS",
    "BASE_CONTEXT_CAPACITY",
    "BASE_GRAPH_ID",
    "LONG_CONTEXT_CAPACITY",
    "MAXIMUM_POSITION_EMBEDDINGS",
    "MINIMUM_GENERATED_DECISIONS",
    "PROFILE_NAME",
    "PROFILE_SCHEMA",
    "QwenFullModelContextError",
    "REQUIRED_COMMITTED_ROWS",
    "build_qwen_long_context_profile",
    "publish_qwen_long_context_profile",
]
