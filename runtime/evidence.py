"""Evidence classes, provenance and the governed comparison gate.

Three failure modes have to be structurally impossible in this program's
reports, because each has already happened once in its history:

1. *Boundary confusion* -- quoting a functional-simulator result as if it were a
   timing or silicon result.  Every record carries an explicit
   :class:`EvidenceClass`, and a comparison refuses to mix them.
2. *Provenance laundering* -- a performance number whose inputs were assumed
   rather than measured, reported without that qualification.  Every
   quantitative input carries a :class:`Provenance`, and a report that depends
   on any assumed value is labelled at the top level.
3. *Incomparable pairs* -- comparing two runs that did not share a prompt, a
   numeric profile, a generation policy or a technology view.  A comparison is
   admitted only after the shared-identity gate passes.

The rule the gate enforces is the one from the master plan section 12: only
same-model pairs are compared, everything except topology must be identical, and
topology cost stays explicit rather than being forced equal.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping, Sequence

from runtime.abi3.capability import canonical_json, digest_of


class EvidenceClass(enum.Enum):
    """What a number actually came from.  Never inferred, always declared."""

    FUNCTIONAL = "functional_artifact_only"
    """Complete numerical execution driven only by compiled artifacts.

    This is full model execution at the functional-simulator boundary.  It is
    not a timing, RTL, post-layout or silicon claim.
    """

    CYCLE = "cycle_model"
    """Event-driven timing over an executed operation trace."""

    RTL = "rtl_simulation"
    """Behaviour observed in RTL simulation."""

    SYNTHESIS = "synthesis_and_static_timing"
    """Gate-level area and timing from a real synthesis and STA run."""

    PLACE_AND_ROUTE = "place_and_route"
    """Post-route area, timing and routing from a real P&R run."""

    SPICE = "spice_circuit"
    """Extracted-circuit simulation."""

    EXTERNAL_REFERENCE = "external_reference_comparator"
    """A vendor or framework result used only to check ours."""

    ASSUMED = "assumed_boundary_component"
    """A sourced or assumed external component such as an HBM stack or PHY."""


class Provenance(enum.Enum):
    """Where one quantitative input came from."""

    CHARACTERIZED = "characterized"
    """Measured by a run in this repository, with an artifact path."""

    DATASHEET = "datasheet"
    """A sourced external component specification, with a citation."""

    ASSUMED = "assumed"
    """A stated assumption.  Any report depending on one says so."""


@dataclass(frozen=True, slots=True)
class Quantity:
    """One number with its unit and provenance."""

    name: str
    value: float
    unit: str
    provenance: Provenance
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.value,
            "source": self.source,
        }


@dataclass
class WorkloadIdentity:
    """Everything that must match for two runs to be comparable."""

    model_id: str
    workload_id: str
    workload_digest: str
    prompt_token_count: int
    max_new_tokens: int
    generation_policy_digest: str
    numeric_profile: str
    graph_id: str
    tokenizer_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "workload_id": self.workload_id,
            "workload_digest": self.workload_digest,
            "prompt_token_count": self.prompt_token_count,
            "max_new_tokens": self.max_new_tokens,
            "generation_policy_digest": self.generation_policy_digest,
            "numeric_profile": self.numeric_profile,
            "graph_id": self.graph_id,
            "tokenizer_sha256": self.tokenizer_sha256,
        }

    @property
    def digest(self) -> str:
        return digest_of(self.to_dict())


@dataclass
class TargetIdentity:
    """What ran the workload.  This is what a comparison is allowed to differ in."""

    target_id: str
    backend: str
    topology_class: int
    node_count: int
    capability_digest: str
    deployment_digest: str
    technology_view: str = "uncharacterized"

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "backend": self.backend,
            "topology_class": self.topology_class,
            "node_count": self.node_count,
            "capability_digest": self.capability_digest,
            "deployment_digest": self.deployment_digest,
            "technology_view": self.technology_view,
        }


@dataclass
class ExecutionRecord:
    """One target's result for one workload at one evidence boundary."""

    evidence_class: EvidenceClass
    workload: WorkloadIdentity
    target: TargetIdentity
    generated_token_ids: tuple[int, ...]
    stop_reason: str
    counters: Mapping[str, int]
    quantities: tuple[Quantity, ...] = ()
    notes: Mapping[str, Any] = dc_field(default_factory=dict)
    failure: str | None = None

    @property
    def depends_on_assumption(self) -> bool:
        return any(q.provenance is Provenance.ASSUMED for q in self.quantities)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_class": self.evidence_class.value,
            "workload": self.workload.to_dict(),
            "target": self.target.to_dict(),
            "generated_token_ids": list(self.generated_token_ids),
            "generated_token_count": len(self.generated_token_ids),
            "stop_reason": self.stop_reason,
            "counters": dict(sorted(self.counters.items())),
            "quantities": [q.to_dict() for q in self.quantities],
            "depends_on_assumption": self.depends_on_assumption,
            "notes": dict(self.notes),
            "failure": self.failure,
        }


class ComparisonError(Exception):
    """Raised when two records may not be compared."""


#: The fields of :class:`WorkloadIdentity` that must be equal for a legal pair.
SHARED_IDENTITY_FIELDS = (
    "model_id",
    "workload_id",
    "workload_digest",
    "prompt_token_count",
    "max_new_tokens",
    "generation_policy_digest",
    "numeric_profile",
    "graph_id",
    "tokenizer_sha256",
)


def check_comparable(left: ExecutionRecord, right: ExecutionRecord) -> list[str]:
    """Return every reason ``left`` and ``right`` may not be compared."""
    problems: list[str] = []
    if left.evidence_class is not right.evidence_class:
        problems.append(
            f"evidence classes differ: {left.evidence_class.value} vs "
            f"{right.evidence_class.value}; boundaries are never mixed"
        )
    for field in SHARED_IDENTITY_FIELDS:
        a = getattr(left.workload, field)
        b = getattr(right.workload, field)
        if a != b:
            problems.append(f"workload identity differs on {field}: {a!r} vs {b!r}")
    if left.target.technology_view != right.target.technology_view:
        problems.append(
            f"technology views differ: {left.target.technology_view} vs "
            f"{right.target.technology_view}; no number crosses views"
        )
    if left.target.deployment_digest == right.target.deployment_digest:
        problems.append(
            "both records name the same deployment; a comparison needs two targets"
        )
    if left.failure or right.failure:
        problems.append("a failed execution is never promoted into a comparison")
    return problems


def compare_tokens(
    left: ExecutionRecord, right: ExecutionRecord
) -> dict[str, Any]:
    """Token-level agreement between two targets on the same workload."""
    a, b = left.generated_token_ids, right.generated_token_ids
    first_divergence = None
    for index, (x, y) in enumerate(zip(a, b)):
        if x != y:
            first_divergence = index
            break
    if first_divergence is None and len(a) != len(b):
        first_divergence = min(len(a), len(b))
    return {
        "identical": a == b,
        "left_count": len(a),
        "right_count": len(b),
        "first_divergence_index": first_divergence,
        "common_prefix_length": (
            len(a) if first_divergence is None else first_divergence
        ),
    }


def build_comparison(
    left: ExecutionRecord,
    right: ExecutionRecord,
    *,
    comparison_id: str,
    require_identical_tokens: bool = True,
) -> dict[str, Any]:
    """Build a governed same-model comparison, or raise.

    Topology cost is reported explicitly on both sides and never normalised
    away: a 32-node cluster and a wafer are different physical objects, and the
    comparison's job is to make that visible, not to hide it.
    """
    problems = check_comparable(left, right)
    if problems:
        raise ComparisonError(
            "comparison refused:\n  " + "\n  ".join(problems)
        )
    tokens = compare_tokens(left, right)
    if require_identical_tokens and not tokens["identical"]:
        raise ComparisonError(
            "the two targets produced different token sequences; a performance "
            "comparison may not precede correct end-to-end execution "
            f"(first divergence at index {tokens['first_divergence_index']})"
        )
    assumed = left.depends_on_assumption or right.depends_on_assumption
    body = {
        "schema": "opentallas.abi3.comparison.v1",
        "comparison_id": comparison_id,
        "evidence_class": left.evidence_class.value,
        "workload": left.workload.to_dict(),
        "targets": {
            "left": left.target.to_dict(),
            "right": right.target.to_dict(),
        },
        "token_agreement": tokens,
        "topology_cost": {
            "left": {
                "topology_class": left.target.topology_class,
                "node_count": left.target.node_count,
            },
            "right": {
                "topology_class": right.target.topology_class,
                "node_count": right.target.node_count,
            },
            "note": (
                "Topology cost is reported, never equalised. The two sides are "
                "different physical objects."
            ),
        },
        "quantities": {
            "left": [q.to_dict() for q in left.quantities],
            "right": [q.to_dict() for q in right.quantities],
        },
        "counter_deltas": _counter_deltas(left.counters, right.counters),
        "depends_on_assumption": assumed,
        "claim_boundary": {
            "functional_execution": left.evidence_class is EvidenceClass.FUNCTIONAL,
            "timing_or_performance": left.evidence_class
            in (EvidenceClass.CYCLE, EvidenceClass.RTL),
            "silicon": False,
            "note": (
                "Artifact-only functional execution is full numerical model "
                "execution at the functional-simulator boundary. It is not an "
                "RTL, timing, post-layout or silicon claim."
            ),
        },
    }
    return body


def _counter_deltas(
    left: Mapping[str, int], right: Mapping[str, int]
) -> dict[str, dict[str, int]]:
    names = sorted(set(left) | set(right))
    out: dict[str, dict[str, int]] = {}
    for name in names:
        a = int(left.get(name, 0))
        b = int(right.get(name, 0))
        if a != b:
            out[name] = {"left": a, "right": b, "delta": b - a}
    return out


def check_token_legitimacy(
    token_ids: Sequence[int],
    *,
    vocabulary_size: int,
    eos_token_ids: Iterable[int],
    stop_reason: str,
) -> list[str]:
    """Assert the acceptance contract on a produced token sequence.

    Every produced ID must be legal, the first official EOS must terminate the
    sequence when the stop reason says so, and no token may follow it.
    """
    problems: list[str] = []
    eos = set(int(t) for t in eos_token_ids)
    for index, token in enumerate(token_ids):
        if not 0 <= int(token) < vocabulary_size:
            problems.append(
                f"token {index} = {token} is outside vocabulary {vocabulary_size}"
            )
    interior_eos = [i for i, t in enumerate(token_ids[:-1]) if int(t) in eos]
    if interior_eos:
        problems.append(
            f"EOS appears at interior positions {interior_eos}; no model "
            "transaction may execute after the first official EOS"
        )
    if stop_reason == "eos":
        if not token_ids:
            problems.append("stop reason is EOS but no token was produced")
        elif int(token_ids[-1]) not in eos:
            problems.append(
                f"stop reason is EOS but the final token {token_ids[-1]} is not "
                "in the authenticated EOS set"
            )
    return problems
