"""DeepSeek-V4-Flash vector engines: ``COMPRESS``, ``INDEX_SCORE`` and ``MHC``.

Three frozen VECTOR subopcodes exist only for DeepSeek-V4-Flash.  Each names a
numeric contract that already has a bit-exact scalar oracle in
``runtime/reference/``; this module is the *data-bearing* implementation of those
oracles, in the same relationship the Qwen vector kernels have to their scalar
references.  Nothing here invents arithmetic:

===================== ======================================================
subopcode             oracle
===================== ======================================================
``COMPRESS``          ``runtime.reference.compression.compress_project_bf16``,
                      ``runtime.reference.compression_state`` (the pool-operand
                      assembly), and
                      ``runtime.reference.compression_pool.compress_pool_f32``
``INDEX_SCORE``       ``runtime.reference.index_score.index_score_bf16``
``MHC``               ``runtime.reference.hyper_connection.hc_pre_bf16``,
                      ``runtime.reference.vector.hc_post_bf16`` and
                      ``runtime.reference.hc_head.hc_head_bf16``
===================== ======================================================

Sub-case encoding (backends must emit this)
===========================================
``docs/TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md`` section 3 assigns
``aux_id_0`` of the OPERATOR descriptor as the sub-case selector for ``COMPRESS``
and ``MHC``, because several neutral kernel kinds share one subopcode.  The
frozen numbering is:

======================== ======== =========================================
kernel kind              ``aux0`` operand mapping
======================== ======== =========================================
``COMPRESS_PROJECT``     ``0``    in0 hidden ``[B,S,K]`` BF16, in1 KV
                                  projection ``[N,K]`` BF16, in2 gate
                                  projection ``[N,K]`` BF16; out0
                                  ``[B,S,2,N]`` FP32 -- index 0 on the
                                  penultimate axis is KV and index 1 is the
                                  learned pooling score, which is the frozen
                                  ``projection_order: kv_then_gate``
``COMPRESS_POOL``        ``1``    in0 pool KV ``[B,G,P,D]`` FP32, in1 pool
                                  scores ``[B,G,P,D]`` FP32; out0
                                  ``[B,G,D]`` FP32
``COMPRESS_STATE_UPDATE``    ``2``    in0 projected ``[B,S,2,W]`` FP32, in2
                                  position embedding (APE) ``[ratio,W]``
                                  FP32; out0 pool KV ``[B,G,P,D]``, out1 pool
                                  scores ``[B,G,P,D]``, both FP32
======================== ======== =========================================

``COMPRESS`` also uses ``aux_id_1`` for the compression ratio (4 overlapping or
128 non-overlapping) and ``aux_id_2`` for the runtime symbol holding the start
position.  ``in1`` is ``NO_ID`` for a state update: the convention's ``in1`` slot
is the projection matrix and a state update has none, while the convention's
``in2`` slot is the position embedding, which is exactly what the APE table is.

======================== ======== =========================================
kernel kind              ``aux0`` operand mapping
======================== ======== =========================================
``HYPER_CONNECT_PRE``    ``0``    in0 hidden ``[T,M,H]`` BF16, in1 ``fn``
                                  ``[(2+M)*M, M*H]`` FP32, in2 ``base``
                                  ``[(2+M)*M]`` FP32, in3 ``scale`` ``[3]``
                                  FP32; out0 weights ``[T,2,M]`` FP32 (row 0
                                  pre, row 1 post), out1 combination
                                  ``[T,M,M]`` FP32
``HYPER_CONNECT_POST``   ``1``    in0 branch ``[B,S,H]`` BF16, in1 residual
                                  ``[B,S,M,H]`` BF16, in2 post ``[B,S,M]``
                                  FP32, in3 combination ``[B,S,M,M]`` FP32;
                                  out0 ``[B,S,M,H]`` BF16
``HYPER_CONNECT_HEAD``   ``2``    in0 hidden ``[T,M,H]`` BF16, in1 ``fn``
                                  ``[M, M*H]`` FP32, in2 ``base`` ``[M]``
                                  FP32, in3 ``scale`` ``[1]`` FP32; out0
                                  ``[T,H]`` BF16
======================== ======== =========================================

``MHC`` uses ``aux_id_1`` for the Sinkhorn iteration count (20 in the frozen
DeepSeek profile) and ``aux_id_2`` for ``hc_mult`` (4).  The normalisation and
Sinkhorn epsilon is the numeric profile's ``epsilon_bits``; the frozen contract
in ``docs/DEEPSEEK_V4_HC_PRE_EVIDENCE.md`` fixes it at ``0x358637bd`` and this
engine refuses any other value, because the reference does.

``HYPER_CONNECT_PRE`` produces the coefficients, not the branch input.  The
branch reduction ``y[t,h] = sum_m pre[t,m] * x[t,m,h]`` -- one binary32 product
per stream, a balanced four-term sum, one BF16 rounding -- is
``REDUCTION.EXPERT_SUM`` under a ``PAIRWISE_TREE`` reduction order, which is
already a frozen engine operation.  Splitting it that way is what makes the
four-input/two-output arity in ``compiler/ir/v3/lowering.py`` exact rather than
approximate, and it keeps one weighted-stream reduction in the machine instead
of two.

``INDEX_SCORE`` takes the convention's row directly: in0 query ``[B,S,Hd,D]``
BF16, in1 key ``[B,C,D]`` BF16, in2 head weights ``[B,S,Hd]`` BF16, out0 scores
``[B,S,C]`` BF16.  The learned-index scale is the numeric profile's
``scale_bits`` (``0x3c3504f3`` in the frozen profile).

Arithmetic substrate
====================
NumPy is the arithmetic substrate, never the contract.  Three rules keep it
bit-exact against the scalar oracles:

* a single IEEE binary32 operation -- add, subtract, multiply, divide -- is one
  ``np.float32`` operation, because both round once to the same format;
* the frozen ``binary32_product_add`` is a *fused* multiply-add: the product of a
  BF16 activation and a binary32 weight needs 32 significand bits, so rounding
  the product first would round twice.  The accumulation is therefore evaluated
  as ``float32(float64(acc) + float64(x) * float64(w))``.  The binary64 product
  is exact (at most 32 significand bits), and binary64 carries 53 bits, which is
  at least ``2 * 24 + 2``: double rounding through it is innocuous, so the result
  is the single correctly rounded binary32 fused product-add;
* a correctly rounded transcendental -- ``exp``, the logistic ``sigmoid``, and
  the reciprocal square root -- is *not* approximated.  Each is evaluated by the
  exact rational reference on the **distinct input encodings** of the tensor,
  which is bounded by the code space rather than by the element count and cannot
  drift from the oracle by construction.

Everything fails closed.  A shape, dtype, ratio, epsilon, iteration count or
sub-case that contradicts the descriptor raises :class:`EngineError` rather than
being reinterpreted.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from runtime.abi3.constants import (
    NO_ID,
    DType,
    Major,
    ReductionOrder,
    RoundingMode,
    TrapClass,
    Vector,
)
from runtime.abi3.descriptors import Descriptor
from runtime.reference.compression_pool import (
    F32_NEGATIVE_INFINITY,
    PINNED_COMPRESSION_RATIOS,
    PINNED_OVERLAP_RATIO,
)
from runtime.reference.formats import (
    binary32_rsqrt,
    decode_bf16,
    decode_binary32,
    encode_bf16_rne,
)
from runtime.reference.hyper_connection import (
    NORMALIZATION_EPSILON_BINARY32,
    binary32_exp_rne,
    binary32_sigmoid_rne,
)
from runtime.reference.transcendental import binary32_exp_general_rne
from runtime.sim.engine import EngineContext, EngineError, NumericProfile, register
from runtime.tensor_accelerator.sparse_attention import exp_cr32
from runtime.sim.formats import narrow_bf16_rne, widen_bf16
from runtime.sim.memory import ResolvedView

#: Sub-case selectors carried in ``aux_id_0``.
COMPRESS_PROJECT = 0
COMPRESS_POOL = 1
COMPRESS_STATE_UPDATE = 2

HC_PRE = 0
HC_POST = 1
HC_HEAD = 2

_COMPRESS_NAMES = {
    COMPRESS_PROJECT: "COMPRESS_PROJECT",
    COMPRESS_POOL: "COMPRESS_POOL",
    COMPRESS_STATE_UPDATE: "COMPRESS_STATE_UPDATE",
}
_MHC_NAMES = {
    HC_PRE: "HYPER_CONNECT_PRE",
    HC_POST: "HYPER_CONNECT_POST",
    HC_HEAD: "HYPER_CONNECT_HEAD",
}


# ---------------------------------------------------------------------------
# Shared validation
# ---------------------------------------------------------------------------
def _require(
    condition: bool,
    message: str,
    trap_class: int = int(TrapClass.DESCRIPTOR_OR_ADDRESS),
) -> None:
    if not condition:
        raise EngineError(message, trap_class=int(trap_class))


def _check_operator(descriptor: Descriptor, sub: int) -> None:
    payload = descriptor.payload
    _require(
        int(payload["engine_family"]) == int(Major.VECTOR)
        and int(payload["engine_sub"]) == int(sub),
        f"operator {descriptor.descriptor_id} does not describe "
        f"VECTOR.{Vector(sub).name}",
    )


def _aux(descriptor: Descriptor, slot: int) -> int | None:
    value = int(descriptor.payload[f"aux_id_{slot}"])
    return None if value == NO_ID else value


def _sub_case(descriptor: Descriptor, names: dict[int, str], what: str) -> int:
    selector = _aux(descriptor, 0)
    _require(
        selector is not None and selector in names,
        f"operator {descriptor.descriptor_id}: VECTOR.{what} names sub-case "
        f"{descriptor.payload['aux_id_0']} in aux_id_0; the frozen selectors are "
        + ", ".join(f"{k} ({v})" for k, v in sorted(names.items())),
    )
    assert selector is not None
    return selector


def _profile(ctx: EngineContext, descriptor: Descriptor) -> NumericProfile:
    profile = ctx.numeric(descriptor.payload["numeric_profile_id"])
    _require(
        profile.rounding_mode == int(RoundingMode.NEAREST_EVEN),
        f"numeric profile {profile.descriptor_id} selects rounding mode "
        f"{RoundingMode(profile.rounding_mode).name}; the DeepSeek vector "
        "contracts are round-to-nearest-even",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    return profile


def _dims(view: ResolvedView, rank: int, label: str) -> tuple[int, ...]:
    _require(
        len(view.dims) == rank,
        f"{label} view {view.descriptor_id} is rank {len(view.dims)}; the "
        f"operand is rank {rank}",
    )
    return tuple(int(d) for d in view.dims)


def _dtype(view: ResolvedView, expected: DType, label: str) -> None:
    _require(
        view.dtype == int(expected),
        f"{label} view {view.descriptor_id} stores {DType(view.dtype).name}, "
        f"but the contract declares {DType(expected).name}",
    )


def _bf16(ctx: EngineContext, view: ResolvedView, label: str) -> np.ndarray:
    _dtype(view, DType.BF16, label)
    codes = np.ascontiguousarray(ctx.read(view), dtype=np.uint16)
    _require(
        not bool(np.any((codes & np.uint16(0x7F80)) == np.uint16(0x7F80))),
        f"{label} view {view.descriptor_id} contains BF16 NaN or infinity",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    return codes


def _fp32(ctx: EngineContext, view: ResolvedView, label: str) -> np.ndarray:
    _dtype(view, DType.FP32, label)
    values = np.ascontiguousarray(ctx.read(view), dtype=np.float32)
    _require(
        bool(np.all(np.isfinite(values))),
        f"{label} view {view.descriptor_id} contains a NaN or infinite binary32 "
        "value",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    return values


def _finite(values: np.ndarray, label: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(values))):
        raise EngineError(
            f"{label} produced a NaN or infinite binary32 value",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    return values


# ---------------------------------------------------------------------------
# Arithmetic primitives
# ---------------------------------------------------------------------------
def _bits(values: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)


def _values(bits: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(bits, dtype=np.uint32).view(np.float32)


def _map_codes(codes: np.ndarray, scalar: Callable[[int], int]) -> np.ndarray:
    """Apply an exact scalar code-to-code map over the distinct encodings.

    A correctly rounded transcendental is defined on encodings, so evaluating it
    once per *distinct* encoding is the same function as evaluating it per
    element -- bounded by the code space instead of the tensor size.
    """
    flat = np.ascontiguousarray(codes, dtype=np.uint32).reshape(-1)
    unique, inverse = np.unique(flat, return_inverse=True)
    mapped = np.fromiter(
        (scalar(int(code)) for code in unique), dtype=np.uint32, count=unique.size
    )
    return mapped[inverse].reshape(codes.shape)


def _balanced_sum(values: np.ndarray) -> np.ndarray:
    """The NUM-6.1 balanced binary32 tree over the last axis."""
    level = np.ascontiguousarray(values, dtype=np.float32)
    while level.shape[-1] > 1:
        if level.shape[-1] & 1:
            pad = np.zeros(level.shape[:-1] + (1,), dtype=np.float32)
            level = np.concatenate((level, pad), axis=-1)
        level = np.add(level[..., 0::2], level[..., 1::2], dtype=np.float32)
    return np.ascontiguousarray(level[..., 0], dtype=np.float32)


def _ordered_product_add(rows: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """``sum_k`` of fused binary32 product-adds in increasing reduction index.

    ``rows`` is ``[R, K]`` and ``weights`` is ``[N, K]``, both as exact binary32
    values; the result is ``[R, N]``.  Each step is one correctly rounded
    ``acc + x * w`` -- see the module docstring for why binary64 delivers it.
    """
    row_count, width = rows.shape
    outputs = weights.shape[0]
    accumulator = np.zeros((row_count, outputs), dtype=np.float64)
    left = np.ascontiguousarray(rows, dtype=np.float64)
    right = np.ascontiguousarray(weights, dtype=np.float64)
    for index in range(width):
        column = left[:, index]
        if not np.any(column):
            # Adding an exact zero product cannot change a positive-zero
            # accumulator, which is what the reference's zero-skip relies on.
            continue
        accumulator = np.add(
            accumulator, np.multiply.outer(column, right[:, index]), dtype=np.float64
        ).astype(np.float32).astype(np.float64)
    return np.ascontiguousarray(accumulator, dtype=np.float32)


def _scaled_bf16(codes: np.ndarray, scale_bits: int) -> np.ndarray:
    """``encode_bf16_rne(bf16_value * binary32_scale)`` -- one rounding.

    The product of an eight-bit BF16 significand and a 24-bit binary32 scale
    needs 32 bits, so it is *not* exact in binary32 and a binary32 multiply
    followed by a BF16 rounding would round twice.  The exact scalar encoder is
    therefore applied to the distinct BF16 encodings.
    """
    decoded = decode_binary32(int(scale_bits))
    if not decoded.finite or decoded.value is None or decoded.value <= 0:
        raise EngineError(
            "the learned-index scale must be a positive finite binary32 value",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    scale_value = decoded.value

    def _scale_code(code: int) -> int:
        value = decode_bf16(int(code) & 0xFFFF).value
        if value is None:
            raise EngineError(
                "learned-index head weight is not finite BF16",
                trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
            )
        return int(encode_bf16_rne(value * scale_value).code)

    mapped = _map_codes(np.asarray(codes, dtype=np.uint32), _scale_code)
    return mapped.astype(np.uint16)


# ---------------------------------------------------------------------------
# VECTOR.COMPRESS
# ---------------------------------------------------------------------------
def _ratio(descriptor: Descriptor) -> int:
    ratio = _aux(descriptor, 1)
    _require(
        ratio is not None and ratio in PINNED_COMPRESSION_RATIOS,
        f"operator {descriptor.descriptor_id}: aux_id_1 must name a pinned "
        f"compression ratio {sorted(PINNED_COMPRESSION_RATIOS)}",
    )
    assert ratio is not None
    return int(ratio)


def _compress_project(
    ctx: EngineContext, descriptor: Descriptor, profile: NumericProfile
) -> None:
    hidden_view = ctx.input_view(descriptor, 0)
    kv_view = ctx.input_view(descriptor, 1)
    gate_view = ctx.input_view(descriptor, 2)
    out_view = ctx.output_view(descriptor, 0)
    batch, span, width = _dims(hidden_view, 3, "COMPRESS_PROJECT hidden")
    outputs, kv_width = _dims(kv_view, 2, "COMPRESS_PROJECT KV projection")
    gate_outputs, gate_width = _dims(gate_view, 2, "COMPRESS_PROJECT gate projection")
    _require(
        kv_width == width and gate_width == width,
        "COMPRESS_PROJECT projections are "
        f"{kv_width} and {gate_width} columns wide; the hidden row is {width}",
    )
    _require(
        gate_outputs == outputs,
        f"COMPRESS_PROJECT gate projection has {gate_outputs} output features "
        f"and the KV projection has {outputs}; the frozen contract projects both "
        "to the same width",
    )
    _require(
        _dims(out_view, 4, "COMPRESS_PROJECT output") == (batch, span, 2, outputs),
        f"COMPRESS_PROJECT output view {out_view.descriptor_id} is "
        f"{out_view.dims}; the packed KV-then-gate result is "
        f"{(batch, span, 2, outputs)}",
    )
    _dtype(out_view, DType.FP32, "COMPRESS_PROJECT output")
    _require(
        profile.reduction_order == int(ReductionOrder.SEQUENTIAL_ASCENDING),
        f"numeric profile {profile.descriptor_id} declares reduction order "
        f"{ReductionOrder(profile.reduction_order).name}; the compressor "
        "projection accumulates in increasing reduction index",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )

    rows = widen_bf16(_bf16(ctx, hidden_view, "COMPRESS_PROJECT hidden")).reshape(
        batch * span, width
    )
    kv_weights = widen_bf16(_bf16(ctx, kv_view, "COMPRESS_PROJECT KV projection"))
    gate_weights = widen_bf16(_bf16(ctx, gate_view, "COMPRESS_PROJECT gate projection"))

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        kv = _finite(
            _ordered_product_add(rows, kv_weights), "COMPRESS_PROJECT KV projection"
        )
        scores = _finite(
            _ordered_product_add(rows, gate_weights),
            "COMPRESS_PROJECT gate projection",
        )
    finally:
        np.seterr(**previous)

    packed = np.stack((kv, scores), axis=1).reshape(batch, span, 2, outputs)
    ctx.write(out_view, np.ascontiguousarray(packed, dtype=np.float32))
    ctx.counters.add("vector.compress_rows", batch * span)
    ctx.counters.add("vector.elements", int(packed.size))


def _exponentials(delta: np.ndarray) -> np.ndarray:
    """``CR32(exp(x))`` over a pooling delta, vectorised where that is proved.

    The contract is the correctly rounded binary32 exponential frozen by
    :func:`runtime.reference.transcendental.binary32_exp_general_rne`, and it
    does not move.  What moves is how it is reached.  Evaluating it one
    ``fractions.Fraction`` scalar at a time is what put ``ATTENTION.SPARSE`` at
    159 hours a prefill (OI-41), and the compressor pool inherits the same cost
    from the same reference: every pooled group of every layer runs one softmax
    through it.

    :func:`runtime.tensor_accelerator.sparse_attention.exp_cr32` is the
    qualified vectorised form of that same function -- it takes the host's
    binary64 exponential, *proves* the binary32 it rounds to by a two-sided
    perturbation some four thousand times the binary64 error, and refers any
    element the proof does not settle to the exact reference.  It is therefore
    the reference's value on every input, not an approximation of it, and it
    was validated by an exhaustive scan of every binary32 in ``[-104, -0.0]``:
    1,120,927,745 comparisons, zero disagreements.

    A pooling delta is ``score - max(score)``, so it is non-positive by
    construction and lands inside that domain.  A non-finite delta cannot come
    from a well-formed operand, and rather than decide what it means here it
    goes to the scalar reference, which is what raised on it before.
    """
    if not bool(np.all(np.isfinite(delta))):
        return _values(_map_codes(_bits(delta), binary32_exp_general_rne))
    return exp_cr32(delta)


def _pool(kv: np.ndarray, scores: np.ndarray) -> np.ndarray:
    """The frozen compressor-pool softmax over the pooling axis.

    ``kv`` and ``scores`` are ``[..., P]`` binary32 values with the pooling axis
    last.  Ratio-four groups carry the released overlap sentinel: a
    negative-infinity score lane contributes an exact zero exponential and takes
    no part in the maximum.
    """
    sentinel = _bits(scores) == np.uint32(F32_NEGATIVE_INFINITY)
    finite = np.where(sentinel, np.float32(-np.inf), scores)
    if not bool(np.all(np.any(~sentinel, axis=-1))):
        raise EngineError(
            "a compressor-pool score vector has no finite lane",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    maximum = np.max(finite, axis=-1, keepdims=True)
    delta = np.subtract(finite, maximum, dtype=np.float32)
    delta = np.where(sentinel, np.float32(0.0), delta)
    exponentials = _exponentials(delta)
    exponentials = np.where(sentinel, np.float32(0.0), exponentials)
    _finite(exponentials, "compressor-pool exponential")
    denominator = _balanced_sum(exponentials)
    if not bool(np.all(np.isfinite(denominator))) or bool(np.any(denominator <= 0)):
        raise EngineError(
            "compressor-pool softmax denominator must be positive finite",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    probabilities = np.divide(exponentials, denominator[..., None], dtype=np.float32)
    products = np.multiply(kv, probabilities, dtype=np.float32)
    return _finite(_balanced_sum(products), "compressor-pool weighted reduction")


def _compress_pool(ctx: EngineContext, descriptor: Descriptor) -> None:
    ratio = _ratio(descriptor)
    kv_view = ctx.input_view(descriptor, 0)
    score_view = ctx.input_view(descriptor, 1)
    out_view = ctx.output_view(descriptor, 0)
    batch, groups, axis, head_dim = _dims(kv_view, 4, "COMPRESS_POOL KV")
    _require(
        _dims(score_view, 4, "COMPRESS_POOL scores") == (batch, groups, axis, head_dim),
        f"COMPRESS_POOL score view {score_view.descriptor_id} is "
        f"{score_view.dims}; the KV operand is {kv_view.dims}",
    )
    expected_axis = (2 if ratio == PINNED_OVERLAP_RATIO else 1) * ratio
    _require(
        axis == expected_axis,
        f"COMPRESS_POOL ratio {ratio} pools {expected_axis} candidates; the "
        f"operand declares {axis}",
    )
    _require(
        _dims(out_view, 3, "COMPRESS_POOL output") == (batch, groups, head_dim),
        f"COMPRESS_POOL output view {out_view.descriptor_id} is {out_view.dims}; "
        f"the pooled result is {(batch, groups, head_dim)}",
    )
    _dtype(out_view, DType.FP32, "COMPRESS_POOL output")

    kv = _fp32(ctx, kv_view, "COMPRESS_POOL KV")
    scores = np.ascontiguousarray(ctx.read(score_view), dtype=np.float32)
    _dtype(score_view, DType.FP32, "COMPRESS_POOL scores")
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        pooled = _pool(
            np.moveaxis(kv, 2, -1),
            np.moveaxis(scores, 2, -1),
        )
    finally:
        np.seterr(**previous)
    ctx.write(out_view, np.ascontiguousarray(pooled, dtype=np.float32))
    ctx.counters.add("vector.compress_rows", batch * groups)
    ctx.counters.add("vector.elements", int(kv.size))


def _compress_state_update(ctx: EngineContext, descriptor: Descriptor) -> None:
    ratio = _ratio(descriptor)
    overlap = ratio == PINNED_OVERLAP_RATIO
    coefficient = 2 if overlap else 1
    projected_view = ctx.input_view(descriptor, 0)
    _require(
        int(descriptor.payload["input_view_1"]) == NO_ID,
        f"operator {descriptor.descriptor_id}: COMPRESS_STATE_UPDATE binds a "
        "projection matrix in input_view_1; a state update has none",
    )
    ape_view = ctx.input_view(descriptor, 2)
    kv_out = ctx.output_view(descriptor, 0)
    score_out = ctx.output_view(descriptor, 1)

    batch, span, pair, width = _dims(projected_view, 4, "COMPRESS_STATE_UPDATE input")
    _require(
        pair == 2,
        f"COMPRESS_STATE_UPDATE input view {projected_view.descriptor_id} is "
        f"{projected_view.dims}; axis 2 carries the packed KV and score rows",
    )
    _require(
        width % coefficient == 0,
        f"COMPRESS_STATE_UPDATE projected width {width} is not "
        f"{coefficient} times a head dimension",
    )
    head_dim = width // coefficient
    ape_rows, ape_width = _dims(ape_view, 2, "COMPRESS_STATE_UPDATE position embedding")
    _require(
        ape_rows == ratio and ape_width == width,
        f"COMPRESS_STATE_UPDATE position embedding is {ape_view.dims}; ratio "
        f"{ratio} declares {(ratio, width)}",
    )

    start = _aux(descriptor, 2)
    position = 0 if start is None else int(ctx.symbol(int(start)))
    _require(
        position == 0,
        "COMPRESS_STATE_UPDATE executed at start position "
        f"{position}: the decode path rolls the compressor's raw slots, which "
        "is a STATE resource this operator's arity does not bind",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )

    groups = span // ratio
    cutoff = groups * ratio
    _require(
        groups > 0,
        f"COMPRESS_STATE_UPDATE span {span} contains no complete group of "
        f"{ratio}; the should-compress predicate is false and the operation must "
        "not be issued",
    )
    pool_axis = coefficient * ratio
    expected = (batch, groups, pool_axis, head_dim)
    for view, label in ((kv_out, "KV"), (score_out, "score")):
        _require(
            _dims(view, 4, f"COMPRESS_STATE_UPDATE pool {label}") == expected,
            f"COMPRESS_STATE_UPDATE pool {label} view {view.descriptor_id} is "
            f"{view.dims}; the pool operand is {expected}",
        )
        _dtype(view, DType.FP32, f"COMPRESS_STATE_UPDATE pool {label}")

    projected = _fp32(ctx, projected_view, "COMPRESS_STATE_UPDATE input")
    ape = _fp32(ctx, ape_view, "COMPRESS_STATE_UPDATE position embedding")
    kv = projected[:, :cutoff, 0, :]
    scores = projected[:, :cutoff, 1, :]
    # The source adds the APE row to the whole complete prefix before the
    # overlap transform, including halves the transform later replaces.
    positions = np.arange(cutoff) % ratio
    biased = np.add(scores, ape[positions][None, :, :], dtype=np.float32)
    _finite(biased, "COMPRESS_STATE_UPDATE score plus position embedding")

    kv_groups = kv.reshape(batch, groups, ratio, width)
    score_groups = biased.reshape(batch, groups, ratio, width)
    if not overlap:
        pool_kv = kv_groups
        pool_scores = score_groups
    else:
        pool_kv = np.zeros(expected, dtype=np.float32)
        pool_scores = np.full(
            expected, _values(np.uint32([F32_NEGATIVE_INFINITY]))[0], dtype=np.float32
        )
        pool_kv[:, 1:, :ratio, :] = kv_groups[:, :-1, :, :head_dim]
        pool_scores[:, 1:, :ratio, :] = score_groups[:, :-1, :, :head_dim]
        pool_kv[:, :, ratio:, :] = kv_groups[:, :, :, head_dim:]
        pool_scores[:, :, ratio:, :] = score_groups[:, :, :, head_dim:]

    ctx.write(kv_out, np.ascontiguousarray(pool_kv, dtype=np.float32))
    ctx.write(score_out, np.ascontiguousarray(pool_scores, dtype=np.float32))
    ctx.counters.add("vector.compress_rows", batch * cutoff)
    ctx.counters.add("vector.elements", int(pool_kv.size))


@register(Major.VECTOR, Vector.COMPRESS)
def compress(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """DeepSeek compressor projection, state handoff and pooling."""
    _check_operator(descriptor, int(Vector.COMPRESS))
    selector = _sub_case(descriptor, _COMPRESS_NAMES, "COMPRESS")
    if selector == COMPRESS_PROJECT:
        _compress_project(ctx, descriptor, _profile(ctx, descriptor))
    elif selector == COMPRESS_POOL:
        _compress_pool(ctx, descriptor)
    else:
        _compress_state_update(ctx, descriptor)


# ---------------------------------------------------------------------------
# VECTOR.INDEX_SCORE
# ---------------------------------------------------------------------------
@register(Major.VECTOR, Vector.INDEX_SCORE)
def index_score(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """One BF16 learned-index score per KV candidate.

    Per head: an increasing-index binary32 dot product of the BF16 query row and
    the BF16 candidate, one BF16 rounding, BF16 ReLU, one BF16-rounded product
    with the scaled head weight; then the heads reduce with the NUM-6.1 balanced
    tree and the row converts once to BF16.  The scale is the numeric profile's
    ``scale_bits``.
    """
    _check_operator(descriptor, int(Vector.INDEX_SCORE))
    profile = _profile(ctx, descriptor)
    query_view = ctx.input_view(descriptor, 0)
    kv_view = ctx.input_view(descriptor, 1)
    weight_view = ctx.input_view(descriptor, 2)
    out_view = ctx.output_view(descriptor, 0)

    batch, span, heads, head_dim = _dims(query_view, 4, "INDEX_SCORE query")
    kv_batch, candidates, kv_dim = _dims(kv_view, 3, "INDEX_SCORE key")
    _require(
        kv_batch == batch and kv_dim == head_dim,
        f"INDEX_SCORE key view {kv_view.descriptor_id} is {kv_view.dims}; the "
        f"query declares batch {batch} and head dimension {head_dim}",
    )
    _require(
        _dims(weight_view, 3, "INDEX_SCORE head weights") == (batch, span, heads),
        f"INDEX_SCORE head-weight view {weight_view.descriptor_id} is "
        f"{weight_view.dims}; the query declares {(batch, span, heads)}",
    )
    _require(
        _dims(out_view, 3, "INDEX_SCORE output") == (batch, span, candidates),
        f"INDEX_SCORE output view {out_view.descriptor_id} is {out_view.dims}; "
        f"the scored shape is {(batch, span, candidates)}",
    )
    _dtype(out_view, DType.BF16, "INDEX_SCORE output")

    query = widen_bf16(_bf16(ctx, query_view, "INDEX_SCORE query"))
    keys = widen_bf16(_bf16(ctx, kv_view, "INDEX_SCORE key"))
    weight_codes = _bf16(ctx, weight_view, "INDEX_SCORE head weights")
    scaled = widen_bf16(_scaled_bf16(weight_codes.astype(np.uint32), profile.scale_bits))

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        out = np.empty((batch, span, candidates), dtype=np.uint16)
        for index in range(batch):
            # Increasing reduction index over the head dimension; the BF16
            # products are exact in binary32, so each step rounds once.
            accumulator = np.zeros((span, heads, candidates), dtype=np.float32)
            for column in range(head_dim):
                accumulator = np.add(
                    accumulator,
                    np.multiply(
                        query[index, :, :, column][:, :, None],
                        keys[index, :, column][None, None, :],
                        dtype=np.float32,
                    ),
                    dtype=np.float32,
                )
            _finite(accumulator, "INDEX_SCORE query-key product")
            rounded, _ = narrow_bf16_rne(accumulator)
            relu = np.maximum(widen_bf16(rounded), np.float32(0.0))
            weighted = np.multiply(
                relu, scaled[index][:, :, None], dtype=np.float32
            )
            _finite(weighted, "INDEX_SCORE weighted head score")
            weighted_codes, _ = narrow_bf16_rne(weighted)
            contributions = np.moveaxis(widen_bf16(weighted_codes), 1, -1)
            total = _finite(
                _balanced_sum(contributions), "INDEX_SCORE head reduction"
            )
            scores, _ = narrow_bf16_rne(total)
            out[index] = scores
    finally:
        np.seterr(**previous)

    ctx.write(out_view, np.ascontiguousarray(out, dtype=np.uint16))
    ctx.counters.add(
        "vector.elements", int(batch * span * heads * candidates * head_dim)
    )
    ctx.counters.add("vector.conversions", int(out.size))


# ---------------------------------------------------------------------------
# VECTOR.MHC
# ---------------------------------------------------------------------------
def _hc_multiplier(descriptor: Descriptor, observed: int) -> int:
    declared = _aux(descriptor, 2)
    _require(
        declared is not None and int(declared) == observed,
        f"operator {descriptor.descriptor_id}: aux_id_2 declares hc_mult "
        f"{descriptor.payload['aux_id_2']}, the operands carry {observed}",
    )
    return observed


def _hc_epsilon(profile: NumericProfile) -> np.float32:
    _require(
        int(profile.epsilon_bits) == NORMALIZATION_EPSILON_BINARY32,
        f"numeric profile {profile.descriptor_id} declares epsilon "
        f"{profile.epsilon_bits:#010x}; the frozen hyper-connection contract "
        f"fixes it at {NORMALIZATION_EPSILON_BINARY32:#010x}",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    return _values(np.uint32([NORMALIZATION_EPSILON_BINARY32]))[0]


def _hc_normalise_and_project(
    hidden_codes: np.ndarray, projection: np.ndarray, epsilon: np.float32
) -> tuple[np.ndarray, np.ndarray]:
    """Flatten, RMS-normalise and project one hyper-connection token block.

    Returns ``(flattened binary32 stream values, normalised projection rows)``.
    Arithmetic zero is canonicalised before the binary32 work, exactly as the
    reference's ``_flatten_token`` does, so a BF16 negative zero cannot leak a
    sign into a product.
    """
    tokens = hidden_codes.shape[0]
    flat = hidden_codes.reshape(tokens, -1)
    canonical = np.where(
        (flat & np.uint16(0x7FFF)) == np.uint16(0), np.uint16(0), flat
    )
    values = widen_bf16(canonical)
    width = values.shape[1]
    squares = np.multiply(values, values, dtype=np.float32)
    _finite(squares, "hyper-connection RMS square")
    totals = _balanced_sum(squares)
    means = np.divide(totals, np.float32(width), dtype=np.float32)
    arguments = np.add(means, epsilon, dtype=np.float32)
    if not bool(np.all(np.isfinite(arguments))) or bool(np.any(arguments <= 0)):
        raise EngineError(
            "hyper-connection RMS argument is not positive finite",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    inverse = _values(
        np.asarray(
            [binary32_rsqrt(int(code)) for code in _bits(arguments)], dtype=np.uint32
        )
    )
    projected = _ordered_product_add(values, projection)
    normalised = np.multiply(projected, inverse[:, None], dtype=np.float32)
    return values, _finite(normalised, "hyper-connection projection")


def _hc_split(
    mixes: np.ndarray,
    scales: np.ndarray,
    bases: np.ndarray,
    multiplier: int,
    iterations: int,
    epsilon: np.float32,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The frozen pre/post/combination split and Sinkhorn normalisation.

    ``pre`` is ``sigmoid(affine) + eps``, ``post`` is ``2 * sigmoid(affine)``, and
    the combination matrix is a stable row softmax followed by one column
    normalisation and ``iterations - 1`` further row-then-column stages -- 20 row
    and 20 column stages in the frozen DeepSeek profile.
    """
    tokens = mixes.shape[0]
    two = np.float32(2.0)

    def _affine(block: np.ndarray, scale: np.float32, base: np.ndarray) -> np.ndarray:
        return np.add(
            np.multiply(block, scale, dtype=np.float32), base, dtype=np.float32
        )

    pre_affine = _affine(mixes[:, :multiplier], scales[0], bases[:multiplier])
    post_affine = _affine(
        mixes[:, multiplier : 2 * multiplier],
        scales[1],
        bases[multiplier : 2 * multiplier],
    )
    comb_affine = _affine(
        mixes[:, 2 * multiplier :].reshape(tokens, multiplier, multiplier),
        scales[2],
        bases[2 * multiplier :].reshape(multiplier, multiplier),
    )
    _finite(comb_affine, "hyper-connection combination affine")

    pre = np.add(
        _values(_map_codes(_bits(pre_affine), binary32_sigmoid_rne)),
        epsilon,
        dtype=np.float32,
    )
    post = np.multiply(
        two, _values(_map_codes(_bits(post_affine), binary32_sigmoid_rne)),
        dtype=np.float32,
    )

    maximum = np.max(comb_affine, axis=-1, keepdims=True)
    shifted = np.subtract(comb_affine, maximum, dtype=np.float32)
    exponentials = _values(_map_codes(_bits(shifted), binary32_exp_rne))
    denominator = _balanced_sum(exponentials)
    comb = np.add(
        np.divide(exponentials, denominator[..., None], dtype=np.float32),
        epsilon,
        dtype=np.float32,
    )

    def _normalise_columns(matrix: np.ndarray) -> np.ndarray:
        sums = _balanced_sum(np.moveaxis(matrix, -2, -1))
        return np.divide(
            matrix, np.add(sums, epsilon, dtype=np.float32)[..., None, :],
            dtype=np.float32,
        )

    def _normalise_rows(matrix: np.ndarray) -> np.ndarray:
        sums = _balanced_sum(matrix)
        return np.divide(
            matrix, np.add(sums, epsilon, dtype=np.float32)[..., None],
            dtype=np.float32,
        )

    comb = _normalise_columns(comb)
    for _ in range(1, iterations):
        comb = _normalise_rows(comb)
        comb = _normalise_columns(comb)
    return pre, post, _finite(comb, "hyper-connection Sinkhorn stage")


def _mhc_pre(ctx: EngineContext, descriptor: Descriptor, profile: NumericProfile) -> None:
    hidden_view = ctx.input_view(descriptor, 0)
    fn_view = ctx.input_view(descriptor, 1)
    base_view = ctx.input_view(descriptor, 2)
    scale_view = ctx.input_view(descriptor, 3)
    weight_out = ctx.output_view(descriptor, 0)
    comb_out = ctx.output_view(descriptor, 1)

    tokens, multiplier, hidden = _dims(hidden_view, 3, "HYPER_CONNECT_PRE hidden")
    multiplier = _hc_multiplier(descriptor, multiplier)
    parameters = (2 + multiplier) * multiplier
    _require(
        _dims(fn_view, 2, "HYPER_CONNECT_PRE fn") == (parameters, multiplier * hidden),
        f"HYPER_CONNECT_PRE fn view {fn_view.descriptor_id} is {fn_view.dims}; "
        f"hc_mult {multiplier} declares {(parameters, multiplier * hidden)}",
    )
    _require(
        _dims(base_view, 1, "HYPER_CONNECT_PRE base") == (parameters,),
        f"HYPER_CONNECT_PRE base view {base_view.descriptor_id} is "
        f"{base_view.dims}; hc_mult {multiplier} declares {(parameters,)}",
    )
    _require(
        _dims(scale_view, 1, "HYPER_CONNECT_PRE scale") == (3,),
        f"HYPER_CONNECT_PRE scale view {scale_view.descriptor_id} is "
        f"{scale_view.dims}; the split declares three scales",
    )
    _require(
        _dims(weight_out, 3, "HYPER_CONNECT_PRE weights")
        == (tokens, 2, multiplier),
        f"HYPER_CONNECT_PRE weight view {weight_out.descriptor_id} is "
        f"{weight_out.dims}; the pre/post block is {(tokens, 2, multiplier)}",
    )
    _require(
        _dims(comb_out, 3, "HYPER_CONNECT_PRE combination")
        == (tokens, multiplier, multiplier),
        f"HYPER_CONNECT_PRE combination view {comb_out.descriptor_id} is "
        f"{comb_out.dims}; the matrix is "
        f"{(tokens, multiplier, multiplier)}",
    )
    _dtype(weight_out, DType.FP32, "HYPER_CONNECT_PRE weights")
    _dtype(comb_out, DType.FP32, "HYPER_CONNECT_PRE combination")

    iterations = _aux(descriptor, 1)
    _require(
        iterations is not None and int(iterations) >= 1,
        f"operator {descriptor.descriptor_id}: aux_id_1 must declare the Sinkhorn "
        "iteration count",
    )
    epsilon = _hc_epsilon(profile)

    hidden_codes = _bf16(ctx, hidden_view, "HYPER_CONNECT_PRE hidden")
    projection = _fp32(ctx, fn_view, "HYPER_CONNECT_PRE fn")
    bases = _fp32(ctx, base_view, "HYPER_CONNECT_PRE base")
    scales = _fp32(ctx, scale_view, "HYPER_CONNECT_PRE scale")

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        _, mixes = _hc_normalise_and_project(hidden_codes, projection, epsilon)
        pre, post, comb = _hc_split(
            mixes, scales, bases, multiplier, int(iterations), epsilon
        )
    finally:
        np.seterr(**previous)

    ctx.write(
        weight_out,
        np.ascontiguousarray(np.stack((pre, post), axis=1), dtype=np.float32),
    )
    ctx.write(comb_out, np.ascontiguousarray(comb, dtype=np.float32))
    ctx.counters.add("vector.mhc_sites", tokens)
    ctx.counters.add("vector.elements", int(hidden_codes.size))


def _mhc_post(ctx: EngineContext, descriptor: Descriptor) -> None:
    branch_view = ctx.input_view(descriptor, 0)
    residual_view = ctx.input_view(descriptor, 1)
    post_view = ctx.input_view(descriptor, 2)
    comb_view = ctx.input_view(descriptor, 3)
    out_view = ctx.output_view(descriptor, 0)

    batch, span, hidden = _dims(branch_view, 3, "HYPER_CONNECT_POST branch")
    residual_dims = _dims(residual_view, 4, "HYPER_CONNECT_POST residual")
    multiplier = _hc_multiplier(descriptor, int(residual_dims[2]))
    _require(
        residual_dims == (batch, span, multiplier, hidden),
        f"HYPER_CONNECT_POST residual view {residual_view.descriptor_id} is "
        f"{residual_view.dims}; the branch declares "
        f"{(batch, span, multiplier, hidden)}",
    )
    _require(
        _dims(post_view, 3, "HYPER_CONNECT_POST post") == (batch, span, multiplier),
        f"HYPER_CONNECT_POST post view {post_view.descriptor_id} is "
        f"{post_view.dims}; the coefficients are {(batch, span, multiplier)}",
    )
    _require(
        _dims(comb_view, 4, "HYPER_CONNECT_POST combination")
        == (batch, span, multiplier, multiplier),
        f"HYPER_CONNECT_POST combination view {comb_view.descriptor_id} is "
        f"{comb_view.dims}; the matrix is "
        f"{(batch, span, multiplier, multiplier)}",
    )
    _require(
        _dims(out_view, 4, "HYPER_CONNECT_POST output") == residual_dims,
        f"HYPER_CONNECT_POST output view {out_view.descriptor_id} is "
        f"{out_view.dims}; the mixed streams are {residual_dims}",
    )
    _dtype(out_view, DType.BF16, "HYPER_CONNECT_POST output")

    branch = widen_bf16(_bf16(ctx, branch_view, "HYPER_CONNECT_POST branch"))
    residual = widen_bf16(_bf16(ctx, residual_view, "HYPER_CONNECT_POST residual"))
    post = _fp32(ctx, post_view, "HYPER_CONNECT_POST post")
    comb = _fp32(ctx, comb_view, "HYPER_CONNECT_POST combination")

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        # comb[source][destination]: the broadcast and reduction axes of
        # ``Block.hc_post``.
        branch_product = np.multiply(
            post[..., None], branch[:, :, None, :], dtype=np.float32
        )
        residual_products = np.multiply(
            np.moveaxis(comb, -1, 2)[..., None],
            residual[:, :, None, :, :],
            dtype=np.float32,
        )
        residual_sum = _balanced_sum(np.moveaxis(residual_products, 3, -1))
        combined = _finite(
            np.add(branch_product, residual_sum, dtype=np.float32),
            "HYPER_CONNECT_POST mix",
        )
        codes, _ = narrow_bf16_rne(combined)
    finally:
        np.seterr(**previous)

    ctx.write(out_view, np.ascontiguousarray(codes, dtype=np.uint16))
    ctx.counters.add("vector.mhc_sites", batch * span)
    ctx.counters.add("vector.elements", int(residual.size))


def _mhc_head(ctx: EngineContext, descriptor: Descriptor, profile: NumericProfile) -> None:
    hidden_view = ctx.input_view(descriptor, 0)
    fn_view = ctx.input_view(descriptor, 1)
    base_view = ctx.input_view(descriptor, 2)
    scale_view = ctx.input_view(descriptor, 3)
    out_view = ctx.output_view(descriptor, 0)

    tokens, multiplier, hidden = _dims(hidden_view, 3, "HYPER_CONNECT_HEAD hidden")
    multiplier = _hc_multiplier(descriptor, multiplier)
    _require(
        _dims(fn_view, 2, "HYPER_CONNECT_HEAD fn") == (multiplier, multiplier * hidden),
        f"HYPER_CONNECT_HEAD fn view {fn_view.descriptor_id} is {fn_view.dims}; "
        f"hc_mult {multiplier} declares {(multiplier, multiplier * hidden)}",
    )
    _require(
        _dims(base_view, 1, "HYPER_CONNECT_HEAD base") == (multiplier,),
        f"HYPER_CONNECT_HEAD base view {base_view.descriptor_id} is "
        f"{base_view.dims}; hc_mult {multiplier} declares {(multiplier,)}",
    )
    _require(
        _dims(scale_view, 1, "HYPER_CONNECT_HEAD scale") == (1,),
        f"HYPER_CONNECT_HEAD scale view {scale_view.descriptor_id} is "
        f"{scale_view.dims}; the head declares one scale",
    )
    _require(
        _dims(out_view, 2, "HYPER_CONNECT_HEAD output") == (tokens, hidden),
        f"HYPER_CONNECT_HEAD output view {out_view.descriptor_id} is "
        f"{out_view.dims}; the reduced hidden is {(tokens, hidden)}",
    )
    _dtype(out_view, DType.BF16, "HYPER_CONNECT_HEAD output")
    epsilon = _hc_epsilon(profile)

    hidden_codes = _bf16(ctx, hidden_view, "HYPER_CONNECT_HEAD hidden")
    projection = _fp32(ctx, fn_view, "HYPER_CONNECT_HEAD fn")
    bases = _fp32(ctx, base_view, "HYPER_CONNECT_HEAD base")
    scales = _fp32(ctx, scale_view, "HYPER_CONNECT_HEAD scale")

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        streams, normalised = _hc_normalise_and_project(
            hidden_codes, projection, epsilon
        )
        affine = np.add(
            np.multiply(normalised, scales[0], dtype=np.float32),
            bases,
            dtype=np.float32,
        )
        coefficients = np.add(
            _values(_map_codes(_bits(affine), binary32_sigmoid_rne)),
            epsilon,
            dtype=np.float32,
        )
        products = np.multiply(
            coefficients[:, :, None],
            streams.reshape(tokens, multiplier, hidden),
            dtype=np.float32,
        )
        total = _finite(
            _balanced_sum(np.moveaxis(products, 1, -1)),
            "HYPER_CONNECT_HEAD stream reduction",
        )
        codes, _ = narrow_bf16_rne(total)
    finally:
        np.seterr(**previous)

    ctx.write(out_view, np.ascontiguousarray(codes, dtype=np.uint16))
    ctx.counters.add("vector.mhc_sites", tokens)
    ctx.counters.add("vector.elements", int(hidden_codes.size))


@register(Major.VECTOR, Vector.MHC)
def mhc(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """DeepSeek mHC hyper-connection: pre-split, post-mix and head reduction."""
    _check_operator(descriptor, int(Vector.MHC))
    selector = _sub_case(descriptor, _MHC_NAMES, "MHC")
    if selector == HC_PRE:
        _mhc_pre(ctx, descriptor, _profile(ctx, descriptor))
    elif selector == HC_POST:
        _mhc_post(ctx, descriptor)
    else:
        _mhc_head(ctx, descriptor, _profile(ctx, descriptor))


__all__ = [
    "COMPRESS_POOL",
    "COMPRESS_PROJECT",
    "COMPRESS_STATE_UPDATE",
    "HC_HEAD",
    "HC_POST",
    "HC_PRE",
    "compress",
    "index_score",
    "mhc",
]
