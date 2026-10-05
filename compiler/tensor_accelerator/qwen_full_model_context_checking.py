"""Independent reconstruction of the Qwen long-context graph profile."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any, Mapping

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)
from .production_model import (
    ProductionModelGraphError,
    compute_graph_id,
    parse_production_model_graph,
)


PROFILE_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_context_profile.v1"
)
CHECK_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_context_profile_check.v1"
)
MODEL_ID = "qwen3-8b"
NUMERIC_PROFILE = "qwen3_bf16_gqa_target_v1"
BASE_GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
BASE_CONTEXT = 8000
PROMPT_TOKENS = 8000
GENERATED_DECISIONS = 32
REQUIRED_ROWS = PROMPT_TOKENS + GENERATED_DECISIONS - 1
EXPANDED_CONTEXT = 8192
MAXIMUM_POSITIONS = 40960
PROFILE_NAME = "qwen3-8b-8000-prompt-32-decision-long-v1"


class QwenFullModelContextCheckError(ArtifactError):
    """Raised when independent context-profile reconstruction fails."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise QwenFullModelContextCheckError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QwenFullModelContextCheckError(f"{label} is not canonical JSON")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise QwenFullModelContextCheckError(f"{label} identity differs")


def _symbol(raw: Mapping[str, Any], symbol_id: str) -> dict[str, Any]:
    symbols = raw.get("symbols")
    if not isinstance(symbols, list):
        raise QwenFullModelContextCheckError("graph symbols are malformed")
    found = [item for item in symbols if isinstance(item, dict) and item.get("id") == symbol_id]
    if len(found) != 1:
        raise QwenFullModelContextCheckError(
            f"graph symbol {symbol_id!r} is missing or duplicated"
        )
    return found[0]


def _validate_base(raw: Mapping[str, Any]) -> None:
    try:
        model = parse_production_model_graph(raw)
    except ProductionModelGraphError as exc:
        raise QwenFullModelContextCheckError(
            f"base graph admission failed: {exc}"
        ) from exc
    if (
        model.graph_id != BASE_GRAPH_ID
        or model.model_id != MODEL_ID
        or model.numeric_profile != NUMERIC_PROFILE
        or len(model.operations) != 617
        or len(model.tensors) != 1053
        or len(model.state_resources) != 36
        or model.source
        != {
            "repository": "Qwen/Qwen3-8B",
            "revision": "b968826d9c46dd6066d109eabc6255188de91218",
            "source_lock_id": "2720b27e49fc6d10422ae70a332e514a8db89a6e7dccfdaa8117f43b4116c670",
        }
    ):
        raise QwenFullModelContextCheckError("base graph identity differs")
    expected = {
        "context_capacity": (BASE_CONTEXT, BASE_CONTEXT, BASE_CONTEXT, BASE_CONTEXT),
        "position_end": (1, BASE_CONTEXT, 1, 1),
        "position_start": (0, BASE_CONTEXT - 1, 0, 1),
        "span_tokens": (1, BASE_CONTEXT, 1, 1),
    }
    for symbol_id, (default, maximum, minimum, multiple) in expected.items():
        item = _symbol(raw, symbol_id)
        if (
            item.get("default"),
            item.get("maximum"),
            item.get("minimum"),
            item.get("multiple_of"),
        ) != (default, maximum, minimum, multiple):
            raise QwenFullModelContextCheckError(
                f"base symbol {symbol_id!r} differs"
            )


def _independent_expansion(base: Mapping[str, Any]) -> dict[str, Any]:
    expected = copy.deepcopy(dict(base))
    _symbol(expected, "context_capacity").update(
        {
            "default": EXPANDED_CONTEXT,
            "maximum": EXPANDED_CONTEXT,
            "minimum": EXPANDED_CONTEXT,
            "multiple_of": EXPANDED_CONTEXT,
        }
    )
    _symbol(expected, "position_end")["maximum"] = EXPANDED_CONTEXT
    _symbol(expected, "position_start")["maximum"] = EXPANDED_CONTEXT - 1
    _symbol(expected, "span_tokens")["maximum"] = EXPANDED_CONTEXT
    entrypoints = expected.get("entrypoints")
    if not isinstance(entrypoints, list) or len(entrypoints) != 2:
        raise QwenFullModelContextCheckError("base entrypoint count differs")
    for index, entrypoint in enumerate(entrypoints):
        try:
            terms = entrypoint["predicate"]["terms"]
        except (KeyError, TypeError) as exc:
            raise QwenFullModelContextCheckError(
                f"base entrypoint {index} predicate is malformed"
            ) from exc
        if (
            not isinstance(terms, list)
            or len(terms) != 2 + index
            or terms[1]
            != {
                "kind": "compare",
                "operator": "le",
                "symbol": "position_end",
                "value": BASE_CONTEXT,
            }
        ):
            raise QwenFullModelContextCheckError(
                f"base entrypoint {index} predicate differs"
            )
        terms[1]["value"] = EXPANDED_CONTEXT
    expected["graph_id"] = compute_graph_id(expected)
    return expected


def _check_profile(
    *,
    base: Mapping[str, Any],
    expanded: Mapping[str, Any],
    profile: dict[str, Any],
) -> None:
    required = {
        "acceptance_workload",
        "base_context_capacity_tokens",
        "base_graph_id",
        "base_graph_payload_sha256",
        "checkpoint_lock_id",
        "claim_boundary",
        "expanded_graph_id",
        "expanded_graph_payload_sha256",
        "long_context_capacity_tokens",
        "maximum_position_embeddings",
        "model_id",
        "profile_id",
        "profile_name",
        "schema",
        "transformation",
    }
    try:
        exact_keys(profile, required, set(), "context profile")
    except ArtifactError as exc:
        raise QwenFullModelContextCheckError(str(exc)) from exc
    _identity(profile, "profile_id", "context profile")
    if (
        profile.get("schema") != PROFILE_SCHEMA
        or profile.get("model_id") != MODEL_ID
        or profile.get("profile_name") != PROFILE_NAME
        or profile.get("base_graph_id") != BASE_GRAPH_ID
        or profile.get("expanded_graph_id") != expanded.get("graph_id")
        or profile.get("base_context_capacity_tokens") != BASE_CONTEXT
        or profile.get("long_context_capacity_tokens") != EXPANDED_CONTEXT
        or profile.get("maximum_position_embeddings") != MAXIMUM_POSITIONS
        or profile.get("base_graph_payload_sha256")
        != hashlib.sha256(canonical_json_bytes(base)).hexdigest()
        or profile.get("expanded_graph_payload_sha256")
        != hashlib.sha256(canonical_json_bytes(expanded)).hexdigest()
    ):
        raise QwenFullModelContextCheckError("context profile binding differs")
    if profile.get("acceptance_workload") != {
        "generated_decisions_minimum": GENERATED_DECISIONS,
        "prompt_tokens_exact": PROMPT_TOKENS,
        "required_committed_rows": REQUIRED_ROWS,
    }:
        raise QwenFullModelContextCheckError("acceptance row arithmetic differs")
    if profile.get("claim_boundary") != {
        "allocation_capacity_only": True,
        "exact_8000_token_acceptance_executed": False,
        "qwen_8192_boundary_executed": False,
        "timing_or_performance": False,
    }:
        raise QwenFullModelContextCheckError("context profile claim differs")
    if profile.get("transformation") != {
        "entrypoint_context_predicates_changed": 2,
        "numeric_contracts_changed": 0,
        "operation_records_changed": 0,
        "source_records_changed": 0,
        "state_resource_records_changed": 0,
        "symbol_records_changed": 4,
        "tensor_records_changed": 0,
    }:
        raise QwenFullModelContextCheckError("context transformation scope differs")
    checkpoint_ids = {
        tensor.get("binding", {}).get("checkpoint_lock_id")
        for tensor in expanded.get("tensors", [])
        if isinstance(tensor, dict) and "binding" in tensor
    }
    if checkpoint_ids != {profile.get("checkpoint_lock_id")}:
        raise QwenFullModelContextCheckError("context checkpoint binding differs")


def check_qwen_long_context_profile(
    *,
    base_graph_path: Path,
    expanded_graph_path: Path,
    profile_path: Path,
) -> dict[str, Any]:
    """Independently reconstruct and authenticate the long-context profile."""

    base = _load_canonical(Path(base_graph_path), "base Qwen graph")
    expanded = _load_canonical(Path(expanded_graph_path), "expanded Qwen graph")
    profile = _load_canonical(Path(profile_path), "Qwen context profile")
    _validate_base(base)
    expected = _independent_expansion(base)
    if expanded != expected:
        raise QwenFullModelContextCheckError(
            "expanded graph differs from independent context reconstruction"
        )
    try:
        model = parse_production_model_graph(expanded)
    except ProductionModelGraphError as exc:
        raise QwenFullModelContextCheckError(
            f"expanded graph admission failed: {exc}"
        ) from exc
    _check_profile(base=base, expanded=expanded, profile=profile)
    context = model.symbol_by_id["context_capacity"]
    if (
        require_int(context.default, "context default", minimum=REQUIRED_ROWS)
        != EXPANDED_CONTEXT
        or REQUIRED_ROWS > context.maximum
        or context.maximum > MAXIMUM_POSITIONS
    ):
        raise QwenFullModelContextCheckError("expanded context capacity is illegal")
    body = {
        "base_graph_id": BASE_GRAPH_ID,
        "check_schema_version": 1,
        "checks": {
            "acceptance_row_arithmetic": True,
            "base_graph_identity": True,
            "checkpoint_bindings_unchanged": True,
            "context_capacity_within_model_positions": True,
            "entrypoint_bounds_expanded_exactly": True,
            "graph_identity_recomputed": True,
            "numeric_and_state_semantics_unchanged": True,
            "profile_identity_and_claim_boundary": True,
        },
        "expanded_graph_id": model.graph_id,
        "profile_id": profile["profile_id"],
        "required_committed_rows": REQUIRED_ROWS,
        "schema": CHECK_SCHEMA,
        "status": "pass",
    }
    result = dict(body)
    result["check_id"] = sha256_bytes(canonical_json_bytes(body))
    return result


__all__ = [
    "CHECK_SCHEMA",
    "QwenFullModelContextCheckError",
    "check_qwen_long_context_profile",
]
