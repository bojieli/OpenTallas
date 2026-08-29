"""Frozen map from neutral kernel kinds to ABI 3.0 engine operations.

This table is the contract between three independently written components: the
model exporters that emit neutral kernels, the backends that emit ABI 3.0
operator descriptors, and the simulator engines that execute them.  Because all
three read this one table, a kernel kind cannot mean one thing in the Qwen lane
and another in the DeepSeek lane, and a backend cannot invent a private opcode.

A kind that is not in this table is a compile error.  ADR-003 section 15:
"unknown, generic-callback, unpriced, or framework-owned operations are compile
errors".
"""

from __future__ import annotations

from typing import Mapping, NamedTuple

from runtime.abi3.constants import (
    Attention,
    Dma,
    Major,
    Reduction,
    Route,
    Selection,
    State,
    Tensor as TensorOp,
    Vector,
)


class EngineOp(NamedTuple):
    """One ABI 3.0 engine operation plus its operand arity."""

    family: int
    sub: int
    inputs: int
    outputs: int


#: Neutral kernel kind -> ABI 3.0 engine operation.
KERNEL_TO_ENGINE: Mapping[str, EngineOp] = {
    # movement and lookup
    "EMBEDDING_LOOKUP": EngineOp(Major.TENSOR, TensorOp.EMBED_LOOKUP, 2, 1),
    "GATHER": EngineOp(Major.DMA, Dma.GATHER, 2, 1),
    "SCATTER": EngineOp(Major.DMA, Dma.SCATTER, 2, 1),
    "COPY": EngineOp(Major.DMA, Dma.TRANSFER, 1, 1),
    "CONCAT": EngineOp(Major.REDUCTION, Reduction.GROUPED_CONCAT, 4, 1),
    # A broadcast is not a concatenation.  ``REDUCTION.GROUPED_CONCAT`` joins
    # along axis 0, so four copies of ``[tokens, width]`` become
    # ``[4 * tokens, width]`` -- four consecutive *tokens* where four *streams*
    # belong.  What ``unsqueeze(axis).repeat(extent)`` actually is, on a machine
    # whose operands are strided views, is one source read through an axis of
    # stride zero.  That is a movement, so it lowers to ``DMA.TRANSFER`` with
    # in0 the stride-zero reading of the source and out0 the materialised
    # result; a backend that can alias the destination need not move anything
    # at all.
    "BROADCAST": EngineOp(Major.DMA, Dma.TRANSFER, 1, 1),
    # A select is a broadcast read backwards.  ``unsqueeze(axis).repeat(extent)``
    # is one source read through a stride-zero axis; ``t[..., index, ...]`` is
    # one source read through an element offset with that axis dropped.  Neither
    # needs an opcode: both are a movement whose whole content is the view, so
    # both lower to ``DMA.TRANSFER`` and a backend that can alias the
    # destination need move nothing at all.  The frozen ``VECTOR.MHC`` row is
    # what asks for it -- ``HYPER_CONNECT_PRE`` packs its pre and post
    # coefficients into one ``[tokens, 2, streams]`` output because the ABI
    # gives the second output view to the combination matrix, and the two
    # planes are then read by two different later operations.
    "SELECT": EngineOp(Major.DMA, Dma.TRANSFER, 1, 1),
    # contraction
    "MATMUL": EngineOp(Major.TENSOR, TensorOp.MATMUL, 2, 1),
    "GROUPED_MATMUL": EngineOp(Major.TENSOR, TensorOp.GROUPED_MATMUL, 3, 1),
    "ROUTED_MATMUL": EngineOp(Major.TENSOR, TensorOp.ROUTED_MATMUL, 4, 1),
    # normalisation and elementwise
    "RMS_NORM": EngineOp(Major.VECTOR, Vector.RMS_NORM, 2, 1),
    "HEAD_RMS_NORM": EngineOp(Major.VECTOR, Vector.HEAD_RMS_NORM, 2, 1),
    "ROPE": EngineOp(Major.VECTOR, Vector.ROPE, 2, 1),
    "ROPE_INVERSE": EngineOp(Major.VECTOR, Vector.ROPE, 2, 1),
    "ADD": EngineOp(Major.VECTOR, Vector.ADD, 2, 1),
    "MUL": EngineOp(Major.VECTOR, Vector.SCALE, 2, 1),
    "SCALE": EngineOp(Major.VECTOR, Vector.SCALE, 2, 1),
    "SILU_MUL": EngineOp(Major.VECTOR, Vector.SILU_MUL, 2, 1),
    "SWIGLU": EngineOp(Major.VECTOR, Vector.SILU_MUL, 2, 1),
    "CONVERT": EngineOp(Major.VECTOR, Vector.CONVERT, 1, 1),
    "QUANTIZE": EngineOp(Major.VECTOR, Vector.CONVERT, 1, 2),
    # Three inputs, because DeepSeek's FP8 QDQ is *partial*: it quantises the
    # non-rotary channels and passes the rotary channels through untouched, so
    # the third operand is the passthrough source. A two-operand dequantize
    # cannot express that without a separate concat.
    "DEQUANTIZE": EngineOp(Major.VECTOR, Vector.CONVERT, 3, 1),
    "HADAMARD": EngineOp(Major.VECTOR, Vector.HADAMARD, 1, 1),
    "SOFTMAX": EngineOp(Major.VECTOR, Vector.SOFTMAX, 1, 1),
    "SQRT_SOFTPLUS": EngineOp(Major.VECTOR, Vector.SQRT_SOFTPLUS, 1, 1),
    "SIGMOID": EngineOp(Major.VECTOR, Vector.SCALE, 1, 1),
    # attention
    "ATTENTION_DENSE": EngineOp(Major.ATTENTION, Attention.DENSE, 4, 1),
    "ATTENTION_GQA": EngineOp(Major.ATTENTION, Attention.GQA, 4, 1),
    "ATTENTION_SPARSE": EngineOp(Major.ATTENTION, Attention.SPARSE, 4, 1),
    "INDEX_SCORE": EngineOp(Major.VECTOR, Vector.INDEX_SCORE, 3, 1),
    "WINDOW_INDEX": EngineOp(Major.ROUTE, Route.WINDOW_INDEX, 1, 1),
    # compression and hyper-connections
    "COMPRESS_PROJECT": EngineOp(Major.VECTOR, Vector.COMPRESS, 3, 1),
    "COMPRESS_POOL": EngineOp(Major.VECTOR, Vector.COMPRESS, 2, 1),
    "COMPRESS_STATE_UPDATE": EngineOp(Major.VECTOR, Vector.COMPRESS, 2, 2),
    "HYPER_CONNECT_PRE": EngineOp(Major.VECTOR, Vector.MHC, 4, 2),
    "HYPER_CONNECT_POST": EngineOp(Major.VECTOR, Vector.MHC, 4, 1),
    "HYPER_CONNECT_HEAD": EngineOp(Major.VECTOR, Vector.MHC, 4, 1),
    # routing
    "ROUTER_SCORE": EngineOp(Major.TENSOR, TensorOp.MATMUL, 2, 1),
    "TOPK": EngineOp(Major.ROUTE, Route.TOPK, 1, 2),
    "BIASED_TOPK": EngineOp(Major.ROUTE, Route.BIASED_TOPK, 2, 2),
    "HASH_ROUTE": EngineOp(Major.ROUTE, Route.HASH_ROUTE, 2, 1),
    "INDEX_TOPK": EngineOp(Major.ROUTE, Route.INDEX_TOPK, 1, 1),
    "WEIGHT_NORMALIZE": EngineOp(Major.ROUTE, Route.WEIGHT_NORMALIZE, 1, 1),
    # Two outputs: the dispatched activations and the expert IDs they were
    # dispatched under. Re-emitting the IDs keeps the dataflow into
    # ROUTED_MATMUL explicit rather than implied by ordering.
    "EXPERT_DISPATCH": EngineOp(Major.ROUTE, Route.EXPERT_DISPATCH, 2, 2),
    "EXPERT_REDUCE": EngineOp(Major.REDUCTION, Reduction.EXPERT_SUM, 3, 1),
    # reduction and selection
    "ORDERED_SUM": EngineOp(Major.REDUCTION, Reduction.ORDERED_SUM, 2, 1),
    "PARTITION_SUM": EngineOp(Major.REDUCTION, Reduction.PARTITION_SUM, 2, 1),
    "LAST_TOKEN_SELECT": EngineOp(Major.DMA, Dma.GATHER, 2, 1),
    "VOCAB_PROJECT": EngineOp(Major.TENSOR, TensorOp.MATMUL, 2, 1),
    "ARGMAX": EngineOp(Major.SELECTION, Selection.ARGMAX, 1, 1),
    "TOKEN_APPEND": EngineOp(Major.SELECTION, Selection.TOKEN_APPEND, 1, 1),
    # state
    # STATE_READ names the state view it reads and the activation it produces;
    # STATE_PREPARE and STATE_COMMIT are pure transitions over the resource
    # named by the instruction's descriptor and carry no operands.
    "STATE_READ": EngineOp(Major.STATE, State.READ, 1, 1),
    "STATE_PREPARE": EngineOp(Major.STATE, State.PREPARE, 0, 0),
    "STATE_COMMIT": EngineOp(Major.STATE, State.COMMIT, 0, 0),
    # A KV append is a movement, not a conversion. Mapping it to VECTOR.CONVERT
    # made the engine read it as a dequantize and compare the wrong shapes.
    # It is a scatter: one source plane written at the positions the request
    # names. Operand row, frozen in TA-ABI3-OPCONV-1: in0 source, in1
    # destination positions. That is the reverse of DMA.SCATTER's own row, so
    # the backend permutes the two when it binds the operator -- a lowering
    # detail, not a semantic one. Both models already emit (source, index),
    # and rewriting either exporter to match the engine's slot order would put
    # a backend concern into the neutral IR.
    "KV_APPEND": EngineOp(Major.DMA, Dma.SCATTER, 2, 1),
}


def engine_for(kind: str) -> EngineOp:
    """Return the frozen engine operation for ``kind``, or raise."""
    try:
        return KERNEL_TO_ENGINE[kind]
    except KeyError:
        raise KeyError(
            f"neutral kernel kind {kind!r} has no ABI 3.0 lowering; add it to the "
            "shared table through a versioned contract change, never privately"
        ) from None


def check_table_complete() -> list[str]:
    """Every registered neutral kind must have a lowering."""
    from compiler.ir.v3.kernel_ir import OPERATION_KINDS

    return sorted(OPERATION_KINDS - set(KERNEL_TO_ENGINE))
