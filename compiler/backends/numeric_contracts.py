"""Execution-contract substitutions shared by every ABI 3.0 backend.

The neutral IR retains the numeric contract that owns qualification.  A
deployment may select another contract only when that substitution is explicit
and digest-bound in its manifest.  Keeping the substitution table here is part
of that contract: ROM and HBM must not give the same neutral operation two
different accumulation associations merely because they use different storage
classes.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Final, Mapping

from runtime.abi3.constants import ReductionOrder


BLOCKED_CONTRACTION_CONTRACT: Final = "bf16_bf16_fp32_blocked_rne_v1"

# TA-ABI3-OPCONV-1 amendment A7 admits both the strictly ascending scalar
# qualification contract and the blocked lane-array execution contract.  A key
# belongs here only when it names a plain contraction: a sum of products with
# no nonlinearity, gating, or operation-specific accumulation order folded into
# it.  Provenance-bearing names are listed rather than inferred so an unknown
# contract never acquires a library association accidentally.
EXECUTION_CONTRACT: Final[Mapping[str, str]] = MappingProxyType(
    {
        "bf16_bf16_fp32_sequential_rne_v1": BLOCKED_CONTRACTION_CONTRACT,
        "matrix_bf16_linear_bf16_v1": BLOCKED_CONTRACTION_CONTRACT,
        "grouped_output_project_bf16_v1": BLOCKED_CONTRACTION_CONTRACT,
        "lm_head_bf16_vocabulary_projection_v1": BLOCKED_CONTRACTION_CONTRACT,
        "matrix_dense_fp8_linear_bf16_block_scaled_contraction_v1": (
            BLOCKED_CONTRACTION_CONTRACT
        ),
        "routing_router_score_bf16_v1": BLOCKED_CONTRACTION_CONTRACT,
        # The SwiGLU nonlinearity is a separate kernel.  These names describe
        # only the dense or routed contractions that feed it.
        "fp8_swiglu_bf16_gate_contraction_v1": BLOCKED_CONTRACTION_CONTRACT,
        "fp8_swiglu_bf16_up_contraction_v1": BLOCKED_CONTRACTION_CONTRACT,
        "fp8_swiglu_bf16_down_contraction_v1": BLOCKED_CONTRACTION_CONTRACT,
        "mxfp4_swiglu_bf16_gate_contraction_v1": BLOCKED_CONTRACTION_CONTRACT,
        "mxfp4_swiglu_bf16_up_contraction_v1": BLOCKED_CONTRACTION_CONTRACT,
        "mxfp4_swiglu_bf16_down_contraction_v1": BLOCKED_CONTRACTION_CONTRACT,
    }
)

REDUCTION_KINDS: Final = frozenset(
    {"EXPERT_REDUCE", "ORDERED_SUM", "PARTITION_SUM"}
)

# Spellings emitted by the two released front ends.  The first three all name
# the same frozen NUM-6.1 balanced binary32 tree.
DECLARED_REDUCTION_ORDER: Final[Mapping[str, ReductionOrder]] = MappingProxyType(
    {
        "balanced_tree": ReductionOrder.PAIRWISE_TREE,
        "canonical_balanced_binary32_tree": ReductionOrder.PAIRWISE_TREE,
        "pairwise_tree": ReductionOrder.PAIRWISE_TREE,
        "blocked_ascending": ReductionOrder.BLOCKED_ASCENDING,
        "sequential_ascending": ReductionOrder.SEQUENTIAL_ASCENDING,
    }
)


def reduction_order_for(
    contract: str,
    kind: str,
    attributes: Mapping[str, Any] | None = None,
) -> ReductionOrder:
    """Return the execution association declared by one neutral operation.

    A reduction kernel states its association directly because the association
    is the operation's content.  Other kernels derive it from their execution
    contract.  In particular, the hyper-connection prelude's normalisation and
    Sinkhorn sums are balanced, RMSNorm is balanced, and the A7 lane-array
    contraction is blocked.
    """

    attributes = attributes or {}
    if kind in REDUCTION_KINDS:
        declared = DECLARED_REDUCTION_ORDER.get(
            str(attributes.get("reduction_order", ""))
        )
        if declared is not None:
            return declared
    lowered = contract.lower()
    if kind in {"RMS_NORM", "HEAD_RMS_NORM"} or "rmsnorm" in lowered:
        return ReductionOrder.PAIRWISE_TREE
    if "hc_pre" in lowered:
        return ReductionOrder.PAIRWISE_TREE
    if "blocked" in lowered:
        return ReductionOrder.BLOCKED_ASCENDING
    return ReductionOrder.SEQUENTIAL_ASCENDING


__all__ = [
    "BLOCKED_CONTRACTION_CONTRACT",
    "DECLARED_REDUCTION_ORDER",
    "EXECUTION_CONTRACT",
    "REDUCTION_KINDS",
    "reduction_order_for",
]
