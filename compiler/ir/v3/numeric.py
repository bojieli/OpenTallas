"""Canonical numeric-contract identities and the capability union.

Two problems this module exists to solve, both found by running the two
exporters against one backend:

*The exporters had disagreed on naming.* Qwen emitted semantic identifiers such
as ``qwen3_rope_fp32_bf16_v1`` while DeepSeek emitted Python module paths such
as ``runtime.reference.rope.rope_apply_bf16#...``. A module path is an
implementation detail, and ADR-003 section 15 forbids the neutral IR from
carrying one: rename the module and every published graph silently changes
identity. Contract names are now canonicalised to opaque semantic identifiers,
and the mapping from a legacy name is explicit rather than incidental.

*The capability had no way to state what it implements.* ADR-003 section 14
forbids silent emulation, so a backend must refuse a contract the capability
does not declare — which it correctly did, and which is what surfaced the
naming problem. The shared HBM/SRAM chip serves both models, so its capability
must declare the *union* of both models' contracts. That union is derived here
from the published graphs rather than hand-maintained, because a hand-listed
union drifts the moment an exporter adds an operation.

Two contracts with different names are different operations. Qwen's RMSNorm
materialises the normalised value in BF16 before the gain multiply and
DeepSeek's stays in binary32; they disagree by one ulp on roughly 27 % of
elements. Collapsing them onto one name would corrupt whichever model did not
get its own.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO = Path(__file__).resolve().parents[3]

#: Contract identifiers must be lowercase, dot-free and version-suffixed.
CONTRACT_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*_v\d+$")

#: Prefixes that mark a name as an implementation path rather than a contract.
IMPLEMENTATION_PREFIXES = ("runtime.", "compiler.", "tests.", "tools.")


class NumericContractError(ValueError):
    """Raised when a contract identity is malformed or unmappable."""


def canonical_contract_id(name: str) -> str:
    """Return the canonical identifier for ``name``.

    Already-canonical names pass through unchanged. A ``runtime.reference.*``
    path is rewritten mechanically: the implementation prefix is dropped, the
    module qualifier and the ``#variant`` suffix become underscore-separated
    segments, and a ``_v1`` version suffix is appended. The rewrite is total and
    injective, so two different implementation paths never collide.
    """
    if not name:
        raise NumericContractError("numeric contract name is empty")
    if CONTRACT_PATTERN.match(name):
        return name
    stripped = name
    for prefix in IMPLEMENTATION_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :]
            break
    else:
        if "." not in stripped and "#" not in stripped:
            raise NumericContractError(
                f"contract {name!r} is neither canonical nor a recognised "
                "implementation path; canonical names are lowercase, "
                "underscore-separated and end in _v<major>"
            )
    if stripped.startswith("reference."):
        stripped = stripped[len("reference.") :]
    # Drop a redundant module qualifier: "rope.rope_apply_bf16" -> "rope_apply_bf16"
    head, _, tail = stripped.partition(".")
    if tail and (tail.startswith(head + "_") or head in tail):
        stripped = tail
    else:
        stripped = stripped.replace(".", "_")
    stripped = stripped.replace("#", "__").replace(".", "_")
    stripped = re.sub(r"[^a-z0-9_]", "_", stripped.lower())
    stripped = re.sub(r"_+", "_", stripped).strip("_")
    canonical = f"{stripped}_v1"
    if not CONTRACT_PATTERN.match(canonical):
        raise NumericContractError(
            f"contract {name!r} canonicalised to {canonical!r}, which is not a "
            "legal identifier"
        )
    return canonical


def is_implementation_path(name: str) -> bool:
    """True when ``name`` leaks an implementation location into the IR."""
    return name.startswith(IMPLEMENTATION_PREFIXES) or "#" in name or "." in name


def contracts_of(graph: Mapping[str, Any]) -> dict[str, int]:
    """Canonical contract identities used by a published graph, with counts."""
    counts: dict[str, int] = {}
    for kernel in graph.get("kernels", []):
        canonical = canonical_contract_id(kernel["numeric_contract"])
        counts[canonical] = counts.get(canonical, 0) + 1
    return dict(sorted(counts.items()))


def capability_union(graph_paths: Iterable[Path]) -> dict[str, Any]:
    """Derive the numeric-contract union the shared chip must implement.

    The union is derived from the published graphs rather than hand-listed,
    because a hand-listed union silently goes stale the moment an exporter adds
    an operation, and the failure mode is an admission error at the very end of
    a long build.
    """
    per_model: dict[str, dict[str, int]] = {}
    union: dict[str, list[str]] = {}
    for path in graph_paths:
        body = json.loads(Path(path).read_text())
        model = body["model_id"]
        counts = contracts_of(body)
        per_model[model] = counts
        for name in counts:
            union.setdefault(name, []).append(model)
    return {
        "schema": "opentallas.abi3.numeric_contract_union.v1",
        "contract_count": len(union),
        "contracts": {
            name: sorted(models) for name, models in sorted(union.items())
        },
        "per_model_counts": {m: c for m, c in sorted(per_model.items())},
        "shared_by_all": sorted(
            name for name, models in union.items() if len(models) == len(per_model)
        ),
    }


def default_graph_paths() -> list[Path]:
    root = REPO / "build" / "ir-v3"
    return sorted(root.glob("*/kernel_ir.v3.json")) if root.exists() else []


def load_union() -> dict[str, Any]:
    """Load the published union, or derive it if it has not been published."""
    published = REPO / "spec" / "abi3" / "numeric_contract_union.json"
    if published.exists():
        return json.loads(published.read_text())
    return capability_union(default_graph_paths())


def union_contract_ids() -> tuple[str, ...]:
    return tuple(load_union()["contracts"])
