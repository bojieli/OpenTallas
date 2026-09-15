"""VECTOR engine: normalisation, rotation, elementwise and activation kernels.

Eleven frozen subopcodes live here.  Each names one numeric contract, and each
contract is executed by an implementation that already exists in this
repository rather than by fresh arithmetic:

===================== ==========================================================
subopcode             numeric contract and implementation
===================== ==========================================================
``RMS_NORM``          two contracts, dispatched on the numeric descriptor's
                      contract digest: ``qwen3_rmsnorm_fp32_bf16_v1``
                      (``runtime.tensor_accelerator.rmsnorm.rms_norm_bf16``)
                      materialises the normalised value in BF16 before the gain
                      multiply, and ``deepseek_rmsnorm_binary32_v1`` stays in
                      binary32 through it.  They disagree by one ulp on roughly
                      27 % of elements, so picking one silently would corrupt
                      whichever model did not get it
``HEAD_RMS_NORM``     the same two contracts applied per head row when a head
                      weight is bound; the unweighted DeepSeek head path
                      (``runtime.reference.normalization.head_rms_norm_bf16``)
                      when input 1 is ``NO_ID``
``ROPE``              ``qwen3_rope_fp32_bf16_v1`` --
                      ``runtime.tensor_accelerator.rope.rope_bf16``
``ADD``               ``bf16_add_rne_v1`` --
                      ``runtime.tensor_accelerator.elementwise.bf16_add_rne``
``SILU_MUL``          ``qwen3_silu_mul_bf16_v1`` --
                      ``runtime.tensor_accelerator.elementwise.qwen3_silu_mul_bf16``
``CONVERT``           one rounding at the storage boundary; block-scaled
                      decode and encode follow ``runtime.reference.formats``
``SCALE``             one binary32 product and one output rounding.  ``aux0``
                      names the sub-case (amendment A8): ``0`` the profile's
                      constant ``scale_bits``, ``1`` an elementwise product
                      with ``input_view_1``, ``2`` the exact logistic sigmoid
``SOFTMAX``           row maximum, binary32 exponential, ordered denominator,
                      reciprocal multiply -- the reduction order comes from the
                      numeric profile
``SQRT_SOFTPLUS``     ``runtime.reference.sqrt_softplus`` exactly
``HADAMARD``          the 128-point normalised transform of
                      ``runtime.reference.hadamard``
``ENGRAM_GATE``       ``engram_gate_fp32_v1`` -- amendment AM-E10: the
                      normalised dot, the 1e-6 clamp, the signed square root,
                      the sigmoid and the gated residual add of
                      ``runtime.reference.engram.engram_gate`` exactly, fused so
                      the whole gate is one auditable contract
===================== ==========================================================

Every operation reduces over, or is elementwise on, the view's **last** axis;
the leading axes are rows.  That is what lets one descriptor cover
``[tokens, hidden]``, ``[tokens, heads, head_dim]`` and a single flattened row
without a private opcode per shape.

Binary32 bulk arithmetic goes through ``runtime/sim/backend.py`` rather than
straight to NumPy, so that one backend selection covers the whole device and a
comparison between two targets cannot differ by which substrate ran it.  The
frozen BF16 kernels (``ADD``, ``SILU_MUL``, ``ROPE``, ``SQRT_SOFTPLUS``,
``QUANTIZE``) stay on their own implementations: each *is* the contract it
names, and each already has a bit-exact scalar oracle.

Everything fails closed: a shape, dtype, epsilon, rounding mode, reduction
order or sub-case that contradicts the descriptor raises :class:`EngineError`
instead of being silently reinterpreted.  An RMSNorm whose contract this engine
does not recognise is refused rather than assigned to one of the two.
"""

from __future__ import annotations

import contextlib
from functools import lru_cache
from typing import Iterator, Sequence

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
from runtime.reference import formats as exact
from runtime.reference import quantization as exact_quantization
from runtime.reference.hadamard import (
    HADAMARD_SCALE_BINARY32,
    HADAMARD_STRIDES,
    HADAMARD_WIDTH,
)
from runtime.reference.normalization import (
    HEAD_RMS_NORM_EPSILON_BF16,
    HEAD_RMS_NORM_WIDTH,
    head_rms_norm_bf16,
)
from runtime.reference.sqrt_softplus import binary32_sqrt_softplus_rne
from runtime.reference.hyper_connection import binary32_sigmoid_rne
from runtime.reference.engram import (
    ENGRAM_GATE_NUMERIC_CONTRACT,
    engram_gate,
)
from runtime.reference.swiglu import (
    OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32,
    OFFICIAL_SWIGLU_LIMIT_BINARY32,
)
from runtime.sim.backend import (
    CONTRACT_DEEPSEEK_FP8_QDQ_QUANTIZE,
    CONTRACT_DEEPSEEK_FP8_SWIGLU,
    CONTRACT_DEEPSEEK_MXFP4_SWIGLU,
    CONTRACT_DEEPSEEK_RMSNORM,
    CONTRACT_DEEPSEEK_ROPE,
    CONTRACT_DEEPSEEK_ROPE_INVERSE,
    CONTRACT_QWEN_RMSNORM,
    CONTRACT_QWEN_ROPE,
    CONTRACT_QWEN_SILU_MUL,
    BackendError,
    declared_contract,
    get_backend,
    required_reduction_order,
)
from runtime.sim.engine import EngineContext, EngineError, NumericProfile, register
from runtime.sim.formats import narrow, narrow_bf16_rne, widen, widen_bf16
from runtime.sim.memory import ResolvedView
from runtime.tensor_accelerator.elementwise import bf16_add_rne, qwen3_silu_mul_bf16
from runtime.tensor_accelerator.rmsnorm import (
    # The correctly rounded binary32 reciprocal square root of the frozen Qwen
    # kernel.  The DeepSeek contract differs from the Qwen one only in where it
    # rounds to BF16, so both must take their inverse RMS from one
    # implementation or they would differ for a second, unrelated reason.
    _binary32_rsqrt_rne as binary32_rsqrt_rne,
    rms_norm_bf16,
)
from runtime.tensor_accelerator.rope import rope_bf16

#: Below this shifted argument the binary32 exponential is zero, matching
#: ``runtime.reference.formats.binary32_exp_nonpositive``.
_EXP_ZERO_CUTOFF = np.float32(-104.0)

_ONE = np.uint32(0x3F800000)


# ---------------------------------------------------------------------------
# Shared validation
# ---------------------------------------------------------------------------
def _require(
    condition: bool,
    message: str,
    trap_class: int = TrapClass.DESCRIPTOR_OR_ADDRESS,
) -> None:
    if not condition:
        raise EngineError(message, trap_class=int(trap_class))


@contextlib.contextmanager
def _numeric_guard(what: str) -> Iterator[None]:
    """Turn a frozen kernel's numeric refusal into an architectural trap."""
    try:
        yield
    except EngineError:
        raise
    except (ValueError, BackendError) as exc:
        raise EngineError(
            f"{what}: {exc}", trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE)
        ) from exc


def _profile(ctx: EngineContext, operator: Descriptor) -> NumericProfile:
    profile = ctx.numeric(operator.payload["numeric_profile_id"])
    _require(
        profile.rounding_mode == RoundingMode.NEAREST_EVEN,
        f"numeric profile {profile.descriptor_id} selects rounding mode "
        f"{RoundingMode(profile.rounding_mode).name}; the vector engine "
        "implements round-to-nearest-even only",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    return profile


def _check_dtype(view: ResolvedView, expected: int, label: str) -> None:
    _require(
        view.dtype == expected,
        f"{label} view {view.descriptor_id} stores {DType(view.dtype).name} but "
        f"its numeric profile declares {DType(expected).name}",
    )


def _same_shape(left: ResolvedView, right: ResolvedView, label: str) -> None:
    _require(
        tuple(left.dims) == tuple(right.dims),
        f"{label}: view {left.descriptor_id} is {left.dims} and view "
        f"{right.descriptor_id} is {right.dims}",
    )


def _rows(dims: Sequence[int]) -> int:
    count = 1
    for extent in dims[:-1]:
        count *= int(extent)
    return count


def _unscaled(view: ResolvedView, label: str) -> None:
    _require(
        view.scale_object_id == NO_ID,
        f"{label} view {view.descriptor_id} declares a block scale object; the "
        "vector engine takes block scales as an explicit operand view",
    )


def _read_rows(ctx: EngineContext, view: ResolvedView, width: int) -> np.ndarray:
    """Read a view and flatten its leading axes into rows of ``width``."""
    _require(
        view.dims and int(view.dims[-1]) == int(width),
        f"view {view.descriptor_id} is {view.dims}; its last axis must be {width}",
    )
    return np.ascontiguousarray(ctx.read(view)).reshape(-1, int(width))


def _write_rows(
    ctx: EngineContext, view: ResolvedView, values: np.ndarray
) -> tuple[int, int]:
    """Narrow a binary32 row block into ``view`` and write it.

    Returns ``(saturations, conversions)``.
    """
    if values.dtype == np.uint16 and view.dtype == DType.BF16:
        ctx.write(view, np.ascontiguousarray(values.reshape(view.dims)))
        return 0, int(values.size)
    with _numeric_guard(f"output view {view.descriptor_id}"):
        narrowed, saturations = narrow(view.dtype, values.reshape(view.dims))
    ctx.write(view, np.ascontiguousarray(narrowed))
    conversions = 0 if view.dtype == DType.FP32 else int(narrowed.size)
    # Vector saturation is a VECTOR_REDUCTION observation.  Counting it here
    # means every narrowing this engine performs is accounted once, whatever
    # the caller does with the returned count.
    ctx.counters.add("vector.saturations", int(saturations))
    return saturations, conversions


def _finite(ctx: EngineContext, values: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(values)
    exceptional = int(np.count_nonzero(~np.isfinite(array)))
    if exceptional:
        ctx.counters.add("vector.exceptional_values", exceptional)
        raise EngineError(
            f"{label} contains {exceptional} NaN or infinite binary32 value(s)",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    return values


# ---------------------------------------------------------------------------
# VECTOR.RMS_NORM and VECTOR.HEAD_RMS_NORM
# ---------------------------------------------------------------------------
def _weighted_rms_norm(
    ctx: EngineContext, operator: Descriptor, counter_rows: str
) -> None:
    profile = _profile(ctx, operator)
    input_view = ctx.input_view(operator, 0)
    weight_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(input_view, profile.input_dtype, "RMSNorm input")
    _check_dtype(weight_view, profile.second_input_dtype, "RMSNorm weight")
    _check_dtype(output_view, profile.output_dtype, "RMSNorm output")
    _require(
        input_view.dtype == DType.BF16 and output_view.dtype == DType.BF16,
        f"the RMSNorm contract is BF16 in and BF16 out; view "
        f"{input_view.descriptor_id} stores {DType(input_view.dtype).name}",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    _same_shape(input_view, output_view, "RMSNorm output shape")
    _require(
        len(weight_view.dims) == 1,
        f"RMSNorm weight view {weight_view.descriptor_id} has rank "
        f"{len(weight_view.dims)}; expected one gain per reduction element",
    )
    _require(
        profile.epsilon_bits != 0,
        f"numeric profile {profile.descriptor_id} declares no epsilon; the "
        "RMSNorm contract requires a positive finite binary32 epsilon",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    contract = _rms_norm_contract(ctx, profile)
    width = int(weight_view.dims[0])
    values = _read_rows(ctx, input_view, width)
    weights = np.ascontiguousarray(ctx.read(weight_view))
    with _numeric_guard(contract):
        if contract == CONTRACT_QWEN_RMSNORM:
            result = rms_norm_bf16(
                values, weights, epsilon_code=int(profile.epsilon_bits)
            )
            ctx.counters.add(
                "vector.saturations",
                int(result.normalized_saturated_element_count)
                + int(result.output_saturated_element_count),
            )
            codes = result.values
        else:
            codes, saturations = deepseek_rms_norm_binary32(
                values, weights, epsilon_bits=int(profile.epsilon_bits)
            )
            ctx.counters.add("vector.saturations", saturations)
    ctx.write(output_view, codes.reshape(output_view.dims))

    rows = values.shape[0]
    ctx.counters.add(counter_rows, rows)
    ctx.counters.add("vector.elements", int(values.size))
    # The Qwen contract crosses two architectural BF16 boundaries per element,
    # the normalised value and the weighted output; the DeepSeek contract stays
    # in binary32 and crosses one.
    ctx.counters.add(
        "vector.conversions",
        (2 if contract == CONTRACT_QWEN_RMSNORM else 1) * int(values.size),
    )


def _rms_norm_contract(ctx: EngineContext, profile: NumericProfile) -> str:
    """Which of the two RMSNorm contracts this descriptor names.

    Amendment A8: both contracts are correct and they are genuinely different
    operations -- they disagree by one ulp on roughly 27 % of elements -- so
    the engine dispatches on the digest and refuses a descriptor that names
    neither.  Guessing would corrupt whichever model did not get its own
    rounding, and would do it silently.
    """
    contract = declared_contract(ctx.table, profile.descriptor_id)
    _require(
        contract in (CONTRACT_QWEN_RMSNORM, CONTRACT_DEEPSEEK_RMSNORM),
        f"numeric profile {profile.descriptor_id} names no RMSNorm contract "
        f"this engine implements; expected {CONTRACT_QWEN_RMSNORM} (BF16 "
        f"materialised before the gain multiply) or {CONTRACT_DEEPSEEK_RMSNORM} "
        "(binary32 through it)",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    fixed = required_reduction_order(contract)
    order = int(profile.reduction_order)
    if fixed is not None and order != fixed:
        raise EngineError(
            f"numeric profile {profile.descriptor_id} declares reduction order "
            f"{ReductionOrder(order).name}; the {contract} row sum is a "
            f"balanced tree, so it must declare "
            f"{ReductionOrder(fixed).name}",
            trap_class=int(TrapClass.CAPABILITY_OR_RESOURCE),
        )
    profile.contract = contract
    return contract


def deepseek_rms_norm_binary32(
    input_codes: np.ndarray, weight_codes: np.ndarray, *, epsilon_bits: int
) -> tuple[np.ndarray, int]:
    """``deepseek_rmsnorm_binary32_v1``: one rounding, at the output.

    Square, balanced row sum, divide by the width, add epsilon, correctly
    rounded reciprocal square root, normalise and apply the gain -- all in
    binary32 -- and convert to BF16 once.  The Qwen contract is the same
    computation with an extra BF16 materialisation of the normalised value
    before the gain multiply, which is the whole of the difference between
    them.

    The row sum and the elementwise work run on the selected backend; the
    per-row reciprocal square root is the exact integer algorithm shared with
    the Qwen kernel.
    """
    backend = get_backend()
    values = backend.widen_bf16(np.ascontiguousarray(input_codes, dtype=np.uint16))
    gains = backend.widen_bf16(np.ascontiguousarray(weight_codes, dtype=np.uint16))
    width = int(np.asarray(input_codes).shape[-1])
    squares = backend.elementwise("square", values)
    if not backend.all_finite(squares):
        raise ValueError("BF16 square overflowed binary32")
    totals = np.ascontiguousarray(
        backend.fetch(
            backend.reduce_sum(squares, order=int(ReductionOrder.PAIRWISE_TREE))
        ),
        dtype=np.float32,
    )
    epsilon = np.asarray([np.uint32(epsilon_bits)], dtype=np.uint32).view(np.float32)[0]
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        means = np.divide(totals, np.float32(width), dtype=np.float32)
        arguments = np.add(means, epsilon, dtype=np.float32)
    finally:
        np.seterr(**previous)
    if not np.all(np.isfinite(arguments)) or np.any(arguments <= 0):
        raise ValueError("RMSNorm variance argument is not positive finite")
    inverse = np.asarray(
        [
            binary32_rsqrt_rne(int(code))
            for code in np.ascontiguousarray(arguments).view(np.uint32)
        ],
        dtype=np.uint32,
    ).view(np.float32)
    normalized = backend.multiply(values, backend.place(inverse[:, None]))
    weighted = backend.multiply(normalized, gains)
    narrowed = backend.narrow_rne(weighted)
    return (
        np.ascontiguousarray(backend.fetch(narrowed.codes), dtype=np.uint16),
        int(narrowed.saturations),
    )


@register(Major.VECTOR, Vector.RMS_NORM)
def _vector_rms_norm(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """Weighted RMS normalisation over the last axis."""
    _weighted_rms_norm(ctx, operator, "vector.norm_rows")


#: The 127 positive finite E4M3FN values in ascending encoding order, and the
#: midpoints between neighbours.  ``runtime.reference.formats.encode_e4m3fn_rne``
#: is a ``bisect_left`` over exactly this table followed by a nearer-neighbour
#: choice, so the rounding is a search rather than a bit trick -- and a search
#: over a sorted table of 127 entries is ``np.searchsorted``.  Every entry is a
#: small dyadic rational, so binary64 holds it and every midpoint exactly: a
#: midpoint of two adjacent encodings needs one bit more than an encoding has.
_E4M3FN_TABLE = np.array(
    [float(value) for value in exact._E4M3FN_POSITIVE], dtype=np.float64
)
_E4M3FN_MIDPOINTS = (_E4M3FN_TABLE[:-1] + _E4M3FN_TABLE[1:]) / np.float64(2.0)
_E4M3FN_MAXIMUM = np.float64(448.0)

#: The eight non-negative E2M1 magnitudes in ascending encoding order, which is
#: the table ``runtime.reference.formats.encode_e2m1_rne`` bisects: 0, 0.5, 1,
#: 1.5, 2, 3, 4, 6.  The sign is nibble bit 3 and zero is canonically positive.
_E2M1_TABLE = np.array(
    [float(value) for value in exact._E2M1_MAGNITUDES], dtype=np.float64
)
_E2M1_MIDPOINTS = (_E2M1_TABLE[:-1] + _E2M1_TABLE[1:]) / np.float64(2.0)
_E2M1_MAXIMUM = np.float32(6.0)
#: ``fast_round_scale`` multiplies the block amax by the *binary32* reciprocal
#: of six rather than dividing by six, and the two differ.  A binary32 division
#: is correctly rounded, so this is ``RN(1/6)`` exactly; writing
#: ``np.float32(1 / 6)`` would round twice, through binary64 first.
_RECIPROCAL_SIX = np.float32(1.0) / np.float32(6.0)
#: ``max(amax, 6 * 2**-126)``: the floor the pinned kernel applies before the
#: scale is derived.  ``1.5 * 2**-124`` is a normal binary32 number.
_FP4_AMAX_FLOOR = np.float32(np.ldexp(6.0, -126))
#: The compressor's FP8 kernel multiplies by these *binary32 encodings* rather
#: than evaluating either real-number constant in a wider host format first.
_RECIPROCAL_448 = np.uint32(
    exact_quantization._BINARY32_RECIPROCAL_448
).view(np.float32)
_FP8_QDQ_AMAX_FLOOR = np.uint32(
    exact_quantization._FP8_QDQ_AMAX_FLOOR_CODE
).view(np.float32)


def _quantize_fp4_qdq_blocks(
    codes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    """The pinned ``FP4_QDQ`` BF16 -> E2M1/E8M0 rule, over whole 32-value blocks.

    ``codes`` is ``[blocks, 32]`` of BF16 encodings; the result is the
    ``[blocks, 32]`` E2M1 nibbles, the ``[blocks]`` E8M0 scale codes and the
    number of elements the contract's clamp moved.  This is
    ``runtime.reference.quantization._block_qdq`` step for step, and it is a
    *different rule* from the block-scaled activation quantiser above rather
    than a variant of it -- which is the reason the engine needed a second
    quantiser and not a wider dtype check:

    * the scale is not searched for.  ``fast_round_scale`` multiplies the block
      amax by the binary32 reciprocal of six and takes ``ceil(log2)`` of the
      product, so the scale is one multiply and one exponent extraction;
    * the amax has a floor of ``6 * 2**-126``, so an all-zero block still gets
      a defined scale instead of a searched one;
    * the quotient is **clamped** to +/-6 before rounding, so a value beyond the
      format's range is committed as six rather than raising.  The official
      kernel clamps; refusing here would refuse the model.

    Exactness, for the same reasons the E4M3FN quantiser is exact: a BF16 value
    is a binary32 value exactly, the amax and the floor are binary32 values
    exactly, the multiply and the divide are each one binary32 operation that
    NumPy performs under the same round-to-nearest-even, the scale is a power of
    two so the division is exact, and the E2M1 rounding decision compares a
    binary32 magnitude against the exact midpoint between two adjacent
    encodings -- both exact in binary64, since a midpoint of two adjacent
    encodings needs one bit more than an encoding has.  Ties go to the even
    encoding, which is the retained-significand parity the reference's comment
    names.
    """
    values = widen_bf16(codes)
    if not bool(np.all(np.isfinite(values))):
        raise exact.NumericReferenceError(
            "activation BF16 element is NaN or infinity"
        )
    magnitudes = np.abs(values)
    amax = np.maximum(magnitudes.max(axis=1), _FP4_AMAX_FLOOR)
    ratio = np.multiply(amax, _RECIPROCAL_SIX, dtype=np.float32)
    if not bool(np.all(np.isfinite(ratio) & (ratio > 0))):
        raise exact.NumericReferenceError("FP4 scale ratio is nonfinite")
    # ceil(log2(x)).  ``frexp`` gives x = m * 2**e with 0.5 <= m < 1, so
    # 2**(e-1) <= x < 2**e: the ceiling is ``e`` unless x is itself the power
    # of two at the bottom of that interval, which is exactly m == 0.5.
    mantissa, exponent = np.frexp(ratio.astype(np.float64))
    scale_exponent = np.where(mantissa == 0.5, exponent - 1, exponent).astype(np.int64)
    scale_codes = scale_exponent + 127
    if not bool(np.all((scale_codes >= 1) & (scale_codes <= 253))):
        raise exact.NumericReferenceError(
            "FP4 QDQ requires an unrepresentable E8M0 scale"
        )
    scale = np.ldexp(np.float32(1.0), scale_exponent).astype(np.float32)
    quotient = np.divide(values, scale[:, None], dtype=np.float32)
    clamped = np.clip(quotient, -_E2M1_MAXIMUM, _E2M1_MAXIMUM)
    clamps = int(np.count_nonzero(clamped != quotient))

    magnitude = np.abs(clamped).astype(np.float64)
    index = np.searchsorted(_E2M1_TABLE, magnitude, side="left")
    hit = (index < _E2M1_TABLE.size) & (
        _E2M1_TABLE[np.minimum(index, _E2M1_TABLE.size - 1)] == magnitude
    )
    lower_code = np.clip(index - 1, 0, _E2M1_MIDPOINTS.size - 1)
    midpoint = _E2M1_MIDPOINTS[lower_code]
    upper_code = lower_code + 1
    rounded = np.where(
        magnitude < midpoint,
        lower_code,
        np.where(
            magnitude > midpoint,
            upper_code,
            np.where(lower_code % 2 == 0, lower_code, upper_code),
        ),
    )
    selected = np.where(
        hit, np.minimum(index, _E2M1_TABLE.size - 1), rounded
    ).astype(np.uint8)
    # A magnitude that rounds to the zero encoding is canonical positive zero,
    # exactly as the reference's ``if selected == 0: sign = 0``.
    negative = (clamped < 0) & (selected != 0)
    nibbles = np.where(negative, selected | np.uint8(0x8), selected).astype(np.uint8)
    return nibbles, scale_codes.astype(np.uint8), clamps


#: ``6 * v`` for every E4M3FN positive encoding and every midpoint between
#: neighbours.  The AM-E10 scale is ``RNE_E4M3(amax / 6)``, and dividing an exact
#: BF16 amax by six is not exact in any binary format -- but the rounding
#: DECISION is a set of comparisons ``amax / 6  <=>  t``, each of which is
#: ``amax  <=>  6 * t``, and every ``6 * t`` here IS exact in binary64: an E4M3FN
#: encoding carries four significand bits and a midpoint five, so six times one
#: needs at most seven.  Scaling the thresholds instead of the operand is what
#: makes this quantiser exact rather than merely close.
_E4M3FN_TABLE_TIMES_SIX = _E4M3FN_TABLE * np.float64(6.0)
_E4M3FN_MIDPOINTS_TIMES_SIX = _E4M3FN_MIDPOINTS * np.float64(6.0)
#: ``amax / 6 > 448``, the point at which the E4M3FN scale saturates.
_E4M3FN_MAXIMUM_TIMES_SIX = np.float64(448.0) * np.float64(6.0)


def _round_to_table_rne(
    magnitudes: np.ndarray, table: np.ndarray, midpoints: np.ndarray
) -> np.ndarray:
    """Round non-negative ``magnitudes`` to the nearest entry of ``table``.

    ``table`` is ascending in ENCODING order and ``midpoints`` holds the
    midpoint between each adjacent pair, so the returned index is the storage
    code.  Ties go to the even code, which is the significand parity the two
    reference encoders name.  Extracted because three quantisers now perform
    exactly this search and a fourth copy of it would be a fourth chance to get
    the tie wrong.
    """
    index = np.searchsorted(table, magnitudes, side="left")
    hit = (index < table.size) & (table[np.minimum(index, table.size - 1)] == magnitudes)
    lower_code = np.clip(index - 1, 0, midpoints.size - 1)
    midpoint = midpoints[lower_code]
    upper_code = lower_code + 1
    rounded = np.where(
        magnitudes < midpoint,
        lower_code,
        np.where(
            magnitudes > midpoint,
            upper_code,
            np.where(lower_code % 2 == 0, lower_code, upper_code),
        ),
    )
    return np.where(hit, np.minimum(index, table.size - 1), rounded)


def _quantize_fp4_s16_e4m3_blocks(
    codes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    """AM-E10 BF16 -> E2M1 elements with one E4M3 scale, over whole blocks.

    ``codes`` is ``[blocks, group]`` of BF16 encodings -- the group is 16 for
    DeepSeek-V4.1-Flash's main latent, and it is the caller's, not a constant
    here.  The result is the ``[blocks, group]`` E2M1 nibbles, the ``[blocks]``
    E4M3FN scale codes, and the number of elements the clamp moved.

    This is ``runtime.reference.fp4_kv.quantize_group_to_fp4`` step for step:
    ``scale = RNE_E4M3(amax / 6)``, then ``clamp(value / scale, +-6)`` rounded to
    E2M1 ties-to-even, with an all-zero group emitting scale code 0 and all-zero
    elements, and a group whose amax underflows every E4M3FN scale REFUSED
    rather than committed as zeros.

    It is a DIFFERENT RULE from ``_quantize_fp4_qdq_blocks`` above, not a block
    size of it.  That one derives an E8M0 power-of-two scale from
    ``ceil(log2(amax * RN(1/6)))``; this one rounds ``amax / 6`` to an E4M3FN
    scale with a four-bit significand, so the two disagree on the scale for
    almost every block.  Sharing a code path between them is exactly the
    confusion the separate ``DType.FP4_E2M1_S16_E4M3`` exists to prevent.

    Exact, and by the same device throughout: every rounding decision is a
    comparison against a threshold, and each threshold is multiplied into the
    operand's own scale so that both sides are exact binary64 values.  The scale
    search compares ``amax`` against ``6 * t`` (at most seven significand bits);
    the element search compares ``|value|`` against ``scale * t`` (at most seven)
    and ``scale * m`` (at most eight).  Nothing is divided, so nothing rounds
    before the one rounding each step is allowed.

    WHAT THIS DOES NOT ESTABLISH.  The reference's own docstring says it: the
    rule is the one ``docs/SOURCES.md`` records for the V4.1 compressor
    (SRC-DSV41-FLASH-MODEL, "the main latent is quantized after RoPE in groups of
    16 with E4M3 scales"), but the pinned ``model.py`` is absent from this
    checkout, so the exact scale-selection micro-path -- any floor constant, and
    whether the vendor multiplies by a rounded reciprocal of six rather than
    dividing -- is NOT confirmed against the vendor.  The forward direction is
    therefore the documented rule, not a vendor-qualified one; the INVERSE
    (``fp4_kv.dequantize_to_fp8``) is exact and is what the dual-simulator
    campaign in ``results/rtl/a3_v41_fp4kv_dequant_campaign.json`` qualified.
    """
    values = widen_bf16(codes)
    if not bool(np.all(np.isfinite(values))):
        raise exact.NumericReferenceError(
            "activation BF16 element is NaN or infinity"
        )
    magnitudes = np.abs(values).astype(np.float64)
    amax = magnitudes.max(axis=1)
    empty = amax == 0.0

    saturating = amax > _E4M3FN_MAXIMUM_TIMES_SIX
    scale_codes = _round_to_table_rne(
        np.where(saturating | empty, np.float64(0.0), amax),
        _E4M3FN_TABLE_TIMES_SIX,
        _E4M3FN_MIDPOINTS_TIMES_SIX,
    ).astype(np.int64)
    scale_codes = np.where(saturating, np.int64(0x7E), scale_codes)
    underflowed = (~empty) & (scale_codes == 0)
    if bool(np.any(underflowed)):
        raise exact.NumericReferenceError(
            "FP4 E2M1/E4M3-per-group scale underflows every E4M3FN code"
        )
    scale = np.where(
        empty, np.float64(1.0), _E4M3FN_TABLE[np.minimum(scale_codes, 0x7E)]
    )

    ceiling = scale * np.float64(6.0)
    clamped = np.minimum(magnitudes, ceiling[:, None])
    clamps = int(np.count_nonzero(clamped != magnitudes))
    # The element thresholds differ PER BLOCK, because each block has its own
    # scale, so this cannot be one ``np.searchsorted`` over a shared table.  The
    # E2M1 table has eight entries, so the insertion point is counted directly:
    # ``searchsorted(t, m, "left")`` is the number of entries strictly below
    # ``m``, and that is a sum over eight comparisons.
    element_thresholds = scale[:, None, None] * _E2M1_TABLE[None, None, :]
    element_midpoints = scale[:, None, None] * _E2M1_MIDPOINTS[None, None, :]
    target = clamped[:, :, None]
    index = np.count_nonzero(element_thresholds < target, axis=2)
    hit = np.any(element_thresholds == target, axis=2)
    lower_code = np.clip(index - 1, 0, _E2M1_MIDPOINTS.size - 1)
    midpoint = np.take_along_axis(
        element_midpoints, lower_code[:, :, None], axis=2
    )[:, :, 0]
    upper_code = lower_code + 1
    rounded = np.where(
        clamped < midpoint,
        lower_code,
        np.where(
            clamped > midpoint,
            upper_code,
            np.where(lower_code % 2 == 0, lower_code, upper_code),
        ),
    )
    selected = np.where(
        hit, np.minimum(index, _E2M1_TABLE.size - 1), rounded
    ).astype(np.uint8)
    negative = (values < 0) & (selected != 0)
    nibbles = np.where(negative, selected | np.uint8(0x8), selected).astype(np.uint8)
    nibbles = np.where(empty[:, None], np.uint8(0), nibbles).astype(np.uint8)
    scale_out = np.where(empty, np.int64(0), scale_codes).astype(np.uint8)
    return nibbles, scale_out, clamps


def _quantize_fp8_qdq_blocks(
    codes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    """The ``FP8_QDQ`` quantise half, code for code, at any qualified block.

    ``codes`` is ``[blocks, block]`` of BF16 encodings; the length is the
    operator's and every scale below comes from its own row of that array, so
    nothing here reads the block length as a constant.  The qualified lengths
    are ``FP8_QDQ_QUALIFIED_BLOCK_SIZES`` and the caller checks them.  The result is E4M3FN
    codes, one E8M0 code per block, and the number of elements the contract's
    clamp moved.  Unlike NUM-3.3's generic activation quantiser, this rule
    derives its scale with one binary32 multiply by ``RN(1 / 448)`` and
    ``ceil(log2)``, applies the released kernel's binary32 ``1e-4`` amax floor,
    and clamps before E4M3FN rounding.

    Every bulk operation below is exact with respect to the scalar reference:
    BF16 widens exactly to binary32; max and abs do not round; the ratio is one
    explicitly binary32 multiply; division by the derived power of two is the
    reference's binary32 division; and all E4M3FN values and their midpoints
    are dyadic rationals exactly representable in the binary64 search table.
    """
    values = widen_bf16(codes)
    if not bool(np.all(np.isfinite(values))):
        raise exact.NumericReferenceError(
            "activation BF16 element is NaN or infinity"
        )
    magnitudes = np.abs(values)
    amax = np.maximum(magnitudes.max(axis=1), _FP8_QDQ_AMAX_FLOOR)
    ratio = np.multiply(amax, _RECIPROCAL_448, dtype=np.float32)
    if not bool(np.all(np.isfinite(ratio) & (ratio > 0))):
        raise exact.NumericReferenceError("FP8 scale ratio is nonfinite")

    mantissa, exponent = np.frexp(ratio.astype(np.float64))
    scale_exponent = np.where(mantissa == 0.5, exponent - 1, exponent).astype(
        np.int64
    )
    scale_codes = scale_exponent + 127
    if not bool(np.all((scale_codes >= 0) & (scale_codes <= 254))):
        raise exact.NumericReferenceError(
            "FP8 QDQ requires an unrepresentable E8M0 scale"
        )
    scale = np.ldexp(np.float32(1.0), scale_exponent).astype(np.float32)
    quotient = np.divide(values, scale[:, None], dtype=np.float32)
    clamped = np.clip(
        quotient, -np.float32(_E4M3FN_MAXIMUM), np.float32(_E4M3FN_MAXIMUM)
    )
    clamps = int(np.count_nonzero(clamped != quotient))

    magnitude = np.abs(clamped).astype(np.float64)
    index = np.searchsorted(_E4M3FN_TABLE, magnitude, side="left")
    hit = (index < _E4M3FN_TABLE.size) & (
        _E4M3FN_TABLE[np.minimum(index, _E4M3FN_TABLE.size - 1)] == magnitude
    )
    lower_code = np.clip(index - 1, 0, _E4M3FN_MIDPOINTS.size - 1)
    midpoint = _E4M3FN_MIDPOINTS[lower_code]
    upper_code = lower_code + 1
    rounded = np.where(
        magnitude < midpoint,
        lower_code,
        np.where(
            magnitude > midpoint,
            upper_code,
            np.where(lower_code % 2 == 0, lower_code, upper_code),
        ),
    )
    selected = np.where(
        hit, np.minimum(index, _E4M3FN_TABLE.size - 1), rounded
    ).astype(np.uint8)
    negative = (clamped < 0) & (selected != 0)
    fp8_codes = np.where(
        negative, selected | np.uint8(0x80), selected
    ).astype(np.uint8)
    return fp8_codes, scale_codes.astype(np.uint8), clamps


def _quantize_activation_blocks(
    codes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    """The NUM-3.3 BF16 -> E4M3FN/E8M0 activation rule, over whole blocks.

    ``codes`` is ``[blocks, width]`` of BF16 encodings; the result is the
    ``[blocks, width]`` E4M3FN codes, the ``[blocks]`` E8M0 scale codes and the
    saturated-element count.  This is
    ``runtime.reference.formats.quantize_bf16_activation_block`` element for
    element, and it is exact rather than merely close for reasons that are
    worth stating, because "vectorised" is otherwise indistinguishable from
    "approximated":

    * a BF16 value is a binary64 value exactly, so decoding is exact;
    * the scale is a power of two, so ``value / scale`` is an exponent
      adjustment and binary64 performs it exactly -- the extremes are
      ``2**-133 / 2**127`` and ``2**128 / 2**-127``, both far inside binary64's
      range;
    * the rounding decision compares the scaled magnitude against the midpoint
      between two adjacent encodings, which is the same decision as the
      reference's two subtractions and is exact because both operands are;
    * ties go to the even *encoding*, which is what the reference's comment
      says the LSB means, and adjacent encodings have adjacent significands.

    ``tests/sim/test_engines_vector_exactness.py`` states the equality against
    the reference as a test rather than leaving it as this paragraph's claim.
    """
    values = widen_bf16(codes).astype(np.float64)
    if not bool(np.all(np.isfinite(values))):
        raise exact.NumericReferenceError(
            "activation BF16 element is NaN or infinity"
        )
    magnitudes = np.abs(values)
    maxima = magnitudes.max(axis=1)
    empty = maxima == 0.0

    # The reference takes the *first* code whose ``448 * 2**(code - 127)``
    # covers the block maximum.  Deriving the exponent and then confirming it
    # against its neighbours keeps the answer the search's answer: the
    # confirmation is the definition, and the derivation only says where to
    # look.
    safe = np.where(empty, np.float64(1.0), maxima)
    _, exponent = np.frexp(safe / _E4M3FN_MAXIMUM)
    scale_codes = np.clip(exponent.astype(np.int64) + 127, 0, 0xFE)
    for _ in range(3):
        covers = safe <= np.ldexp(_E4M3FN_MAXIMUM, scale_codes - 127)
        lower = np.maximum(scale_codes - 1, 0)
        smaller = safe <= np.ldexp(_E4M3FN_MAXIMUM, lower - 127)
        scale_codes = np.where(
            ~covers, np.minimum(scale_codes + 1, 0xFE), np.where(smaller, lower, scale_codes)
        )
    if not bool(
        np.all(safe <= np.ldexp(_E4M3FN_MAXIMUM, scale_codes - 127))
    ):
        raise exact.NumericReferenceError(
            "activation requires an unrepresentable E8M0 scale"
        )

    scaled = magnitudes * np.ldexp(np.float64(1.0), 127 - scale_codes)[:, None]
    index = np.searchsorted(_E4M3FN_TABLE, scaled, side="left")
    hit = (index < _E4M3FN_TABLE.size) & (
        _E4M3FN_TABLE[np.minimum(index, _E4M3FN_TABLE.size - 1)] == scaled
    )
    lower_code = np.clip(index - 1, 0, _E4M3FN_MIDPOINTS.size - 1)
    midpoint = _E4M3FN_MIDPOINTS[lower_code]
    upper_code = lower_code + 1
    rounded = np.where(
        scaled < midpoint,
        lower_code,
        np.where(
            scaled > midpoint,
            upper_code,
            np.where(lower_code % 2 == 0, lower_code, upper_code),
        ),
    )
    selected = np.where(hit, np.minimum(index, _E4M3FN_TABLE.size - 1), rounded)
    saturated = scaled > _E4M3FN_MAXIMUM
    selected = np.where(saturated, 0x7E, selected).astype(np.uint8)
    negative = (values < 0) & (selected != 0) & ~empty[:, None]
    block_codes = np.where(negative, selected | np.uint8(0x80), selected).astype(
        np.uint8
    )
    block_codes = np.where(empty[:, None], np.uint8(0), block_codes).astype(np.uint8)
    scale_out = np.where(empty, np.uint8(0x7F), scale_codes.astype(np.uint8)).astype(
        np.uint8
    )
    saturations = int(np.count_nonzero(saturated & ~empty[:, None]))
    return block_codes, scale_out, saturations


#: ``bf16_rsqrt`` and the epsilon-biased mean are a map from one BF16 encoding
#: to another, so evaluating the exact reference once per *distinct* mean code
#: is the same function bounded by the code space rather than by the tensor.
@lru_cache(maxsize=1 << 16)
def _head_rms_inverse_from_mean(mean_code: int, epsilon_bf16: int) -> int:
    epsilon = exact.decode_bf16(epsilon_bf16).value
    mean_value = exact.decode_bf16(mean_code).value
    if epsilon is None or mean_value is None:  # pragma: no cover - invariant
        raise RuntimeError("HEAD_RMS_NORM operand is not finite BF16")
    biased = exact.encode_bf16_rne(mean_value + epsilon)
    if biased.saturated:
        raise exact.NumericReferenceError("finite BF16 epsilon add overflow")
    return exact.bf16_rsqrt(biased.code)


def _head_rms_norm_rows(codes: np.ndarray, epsilon_bf16: int) -> np.ndarray:
    """The unweighted BF16 head RMSNorm, row-block at a time.

    Identical, code for code, to
    ``runtime.reference.normalization.head_rms_norm_bf16`` -- which is a
    ``fractions.Fraction`` evaluation per element and therefore not something a
    43-layer prefill can afford.  Each stage is reproduced in the domain the
    contract names, and each is exact there:

    ``x * x``       both operands are BF16, so the product needs sixteen
                    significand bits and binary32 holds it exactly whenever the
                    result is normal.  The subnormal case is not assumed away:
                    it is checked, and falls back to the reference.
    balanced sum    the contract's own domain is binary32, so a binary32
                    pairwise tree over the same pairs *is* the definition.
    mean, epsilon,  a map from one BF16 encoding to another, memoised over the
    rsqrt           distinct encodings by calling the reference itself.
    ``x * inv``     BF16 times BF16 again, under the same guard.
    """
    values = widen_bf16(codes)
    if not bool(np.all(np.isfinite(values))):
        raise exact.NumericReferenceError("head RMSNorm input is NaN or infinity")
    squares = _exact_bf16_product(values, values, "head RMSNorm square")
    square_codes, saturations = narrow_bf16_rne(squares)
    if saturations:
        raise exact.NumericReferenceError("finite BF16 square overflow")
    widened = widen_bf16(square_codes)
    total = _balanced_binary32_sum(widened)
    mean_binary32 = np.divide(
        total, np.float32(HEAD_RMS_NORM_WIDTH), dtype=np.float32
    )
    mean_codes, mean_saturations = narrow_bf16_rne(mean_binary32)
    if mean_saturations:
        raise exact.NumericReferenceError("finite BF16 mean-square overflow")
    inverse_codes = np.fromiter(
        (
            _head_rms_inverse_from_mean(int(code), int(epsilon_bf16))
            for code in mean_codes
        ),
        dtype=np.uint16,
        count=mean_codes.size,
    )
    inverse = widen_bf16(inverse_codes)[:, None]
    scaled = _exact_bf16_product(values, inverse, "head RMSNorm product")
    output, _ = narrow_bf16_rne(scaled)
    return output


def _exact_bf16_product(
    left: np.ndarray, right: np.ndarray, label: str
) -> np.ndarray:
    """``left * right`` for BF16-valued binary32 arrays, exactly.

    Two eight-bit significands make a sixteen-bit product, so binary32 carries
    it with eight bits to spare -- but only while the result is normal.  Below
    ``2**-126`` binary32 loses bits the product has, and rounding twice is not
    rounding once.  Comparing the binary32 product against the binary64 one,
    which is exact over the whole BF16 range, decides that rather than assumes
    it, and a disagreement raises instead of returning a plausible number.
    """
    product32 = np.multiply(left, right, dtype=np.float32)
    product64 = np.multiply(
        left.astype(np.float64), right.astype(np.float64), dtype=np.float64
    )
    if not np.array_equal(product32.astype(np.float64), product64):
        raise exact.NumericReferenceError(
            f"{label}: a BF16 product fell below the binary32 normal range, "
            "where rounding to binary32 and then to BF16 is not the contract's "
            "single rounding"
        )
    return product32


def _balanced_binary32_sum(values: np.ndarray) -> np.ndarray:
    """The NUM-6.1 balanced binary32 tree over the last axis."""
    level = np.ascontiguousarray(values, dtype=np.float32)
    while level.shape[-1] > 1:
        if level.shape[-1] & 1:
            pad = np.zeros(level.shape[:-1] + (1,), dtype=np.float32)
            level = np.concatenate((level, pad), axis=-1)
        level = np.add(level[..., 0::2], level[..., 1::2], dtype=np.float32)
    return np.ascontiguousarray(level[..., 0], dtype=np.float32)


@register(Major.VECTOR, Vector.HEAD_RMS_NORM)
def _vector_head_rms_norm(
    ctx: EngineContext, sub: int, operator: Descriptor
) -> None:
    """Per-head RMS normalisation.

    With a head gain bound to input 1 this is the weighted contract applied to
    each ``head_dim`` row -- the Qwen ``q_norm``/``k_norm`` path.  With input 1
    unbound it is the DeepSeek query-head path, whose square, mean, epsilon and
    reciprocal square root are all BF16-domain, and which is executed by the
    exact reference implementation.
    """
    if operator.payload["input_view_1"] != NO_ID:
        _weighted_rms_norm(ctx, operator, "vector.norm_rows")
        return
    profile = _profile(ctx, operator)
    input_view = ctx.input_view(operator, 0)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(input_view, profile.input_dtype, "head RMSNorm input")
    _check_dtype(output_view, profile.output_dtype, "head RMSNorm output")
    _require(
        input_view.dtype == DType.BF16 and output_view.dtype == DType.BF16,
        "the unweighted head RMSNorm contract is BF16 in and BF16 out",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    _same_shape(input_view, output_view, "head RMSNorm output shape")
    _require(
        profile.epsilon_bits == HEAD_RMS_NORM_EPSILON_BF16,
        f"numeric profile {profile.descriptor_id} declares epsilon "
        f"0x{profile.epsilon_bits:x}; the unweighted head RMSNorm contract "
        f"requires the BF16 encoding 0x{HEAD_RMS_NORM_EPSILON_BF16:04x}",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    width = int(input_view.dims[-1])
    _require(
        width == HEAD_RMS_NORM_WIDTH,
        f"head RMSNorm view {input_view.descriptor_id} has width {width}; the "
        f"qualified contract is {HEAD_RMS_NORM_WIDTH}-wide",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    values = _read_rows(ctx, input_view, width)
    with _numeric_guard("deepseek_v4 head RMSNorm"):
        codes = _head_rms_norm_rows(values, int(profile.epsilon_bits))
    ctx.write(output_view, codes.reshape(output_view.dims))
    ctx.counters.add("vector.norm_rows", int(values.shape[0]))
    ctx.counters.add("vector.elements", int(values.size))
    ctx.counters.add("vector.conversions", 2 * int(values.size))


# ---------------------------------------------------------------------------
# VECTOR.ROPE
# ---------------------------------------------------------------------------
@register(Major.VECTOR, Vector.ROPE)
def _vector_rope(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """Rotary position embedding over the last axis.

    ``input 0`` is ``[..., head_dim]``, ``input 1`` is the coefficient row
    ``cos[rotary_width] || sin[rotary_width]``: rank 1 to apply one position to
    every row, or ``[rows, 2 * rotary_width]`` to apply one coefficient row per
    input row.  ``output 0`` has the input's shape.  ``aux_id_0`` is the rotary
    width the frozen operand row already gives it.

    Two contracts live here and the engine dispatches on the digest, exactly as
    ``RMS_NORM`` does.  They are different operations, not two spellings of one:
    ``qwen3_rope_fp32_bf16_v1`` rotates the whole axis, pairs channel ``i`` with
    ``i + head_dim / 2``, and rounds each product to BF16 before the sum;
    ``rope_apply_bf16_v1`` rotates only the final ``rotary_width`` channels,
    pairs ``2p`` with ``2p + 1`` as a complex number, and stays in binary32
    through the product and the sum, rounding once at the output.
    """
    profile = _profile(ctx, operator)
    input_view = ctx.input_view(operator, 0)
    coefficient_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(input_view, profile.input_dtype, "RoPE input")
    _check_dtype(coefficient_view, profile.second_input_dtype, "RoPE coefficient")
    _check_dtype(output_view, profile.output_dtype, "RoPE output")
    _require(
        input_view.dtype == DType.BF16 and output_view.dtype == DType.BF16,
        "the RoPE contract is BF16 in and BF16 out",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    _same_shape(input_view, output_view, "RoPE output shape")
    contract = _rope_contract(ctx, profile)
    if contract in _DEEPSEEK_ROPE_CONTRACTS:
        _deepseek_rope(ctx, operator, profile, contract)
        return
    # ``qwen3_rope_fp32_bf16_v1`` rotates the whole last axis by definition, so
    # ``aux_id_0`` carries nothing this path needs -- and the two backends that
    # emit it do not agree about what it holds: the ROM backend writes the head
    # dimension and the HBM/SRAM backend writes the coefficient row's width,
    # which is twice that.  Reading it here would refuse deployments that are
    # correct.  The slot is load-bearing only where the rotation is partial,
    # and the partial contracts are the ones that read it.
    width = int(input_view.dims[-1])
    values = _read_rows(ctx, input_view, width)
    raw = ctx.read(coefficient_view)
    if raw.ndim == 1:
        coefficients = np.ascontiguousarray(raw)
    else:
        # The coefficient view is flattened exactly as the input is, so a table
        # holding one row per *token* reaches an input holding one row per
        # (token, head) as a broadcast: dims (tokens, heads, 2 * head_dim) with
        # a zero stride on the head axis.  Every head of a token shares the row,
        # and nothing is copied to say so.
        coefficients = _read_rows(ctx, coefficient_view, 2 * width)
    _require(
        coefficients.shape[-1] == 2 * width,
        f"RoPE coefficient view {coefficient_view.descriptor_id} has last axis "
        f"{coefficients.shape[-1]}; expected cosine then sine over {width}",
    )
    if coefficients.dtype != np.uint16:
        # ``qwen3_rope_fp32_bf16_v1``: the coefficient table is computed in
        # binary32 and applied at a BF16 boundary, which is where the frozen
        # kernel takes it.  The narrowing is part of the contract, so it happens
        # here rather than being pushed onto whoever produced the table.
        coefficients, saturations = narrow_bf16_rne(
            np.ascontiguousarray(coefficients, dtype=np.float32)
        )
        ctx.counters.add("vector.saturations", int(saturations))
    with _numeric_guard("qwen3_rope_fp32_bf16_v1"):
        if coefficients.ndim == 1:
            # The frozen kernel rotates a query and a key together; one tensor
            # is rotated by presenting it in both operand positions.
            rotated = rope_bf16(values, values, coefficients).query_values
        else:
            _require(
                coefficients.shape[0] == values.shape[0],
                f"RoPE coefficient view {coefficient_view.descriptor_id} has "
                f"{coefficients.shape[0]} rows; the input has {values.shape[0]}",
            )
            rotated = np.empty_like(values)
            for index in range(values.shape[0]):
                row = values[index : index + 1]
                rotated[index] = rope_bf16(row, row, coefficients[index]).query_values[0]
    ctx.write(output_view, rotated.reshape(output_view.dims))
    ctx.counters.add("vector.rope_pairs", int(values.shape[0]) * (width // 2))
    ctx.counters.add("vector.elements", int(values.size))
    # Direct product, rotated product and their sum each round once.
    ctx.counters.add("vector.conversions", 3 * int(values.size))


#: The two rotary contracts that rotate a *suffix* of the axis as adjacent
#: complex pairs.  They differ from each other only in the sign of the sine.
_DEEPSEEK_ROPE_CONTRACTS = (CONTRACT_DEEPSEEK_ROPE, CONTRACT_DEEPSEEK_ROPE_INVERSE)


def _rope_contract(ctx: EngineContext, profile: NumericProfile) -> str:
    """Which rotary contract this descriptor names.

    Fails closed on a digest that names none.  The rotations disagree about
    which channels move and about where the arithmetic rounds, so a descriptor
    that names neither cannot be assigned to one of them.
    """
    contract = declared_contract(ctx.table, profile.descriptor_id)
    _require(
        contract in (CONTRACT_QWEN_ROPE, *_DEEPSEEK_ROPE_CONTRACTS),
        f"numeric profile {profile.descriptor_id} names no rotary contract this "
        f"engine implements; expected {CONTRACT_QWEN_ROPE} (whole axis, "
        f"half-split pairing, BF16 products) or {CONTRACT_DEEPSEEK_ROPE} / "
        f"{CONTRACT_DEEPSEEK_ROPE_INVERSE} (suffix, adjacent complex pairs, "
        "binary32 products)",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    profile.contract = contract
    return contract


def _rotary_width(operator: Descriptor, width: int) -> int:
    """``aux_id_0``: how many trailing channels this operator rotates.

    ``TA-ABI3-OPCONV-1`` section 3 already gives ``VECTOR.ROPE``'s ``aux_id_0``
    to the rotary width; an operator that leaves it unset is declaring that the
    rotation covers the whole axis.
    """
    declared = int(operator.payload["aux_id_0"])
    rotary = width if declared == NO_ID else declared
    _require(
        0 < rotary <= width and rotary % 2 == 0,
        f"operator {operator.descriptor_id} declares rotary width {rotary} in "
        f"aux_id_0; it must be positive, even, and no wider than the {width}-"
        "wide axis it rotates",
    )
    return rotary


def _deepseek_rope(
    ctx: EngineContext,
    operator: Descriptor,
    profile: NumericProfile,
    contract: str,
) -> None:
    """``rope_apply_bf16_v1``: rotate the final ``aux_id_0`` channels.

    The released model rotates only the last ``rotary_width`` channels of each
    head and reads them as ``rotary_width / 2`` adjacent complex pairs -- pair
    ``p`` is ``(x[2p], x[2p + 1])``, not ``(x[p], x[p + half])``.  The leading
    channels are carried through unchanged; the reference counts them as
    ``prefix_bf16_values_preserved`` rather than as rotated values, and this
    engine moves exactly those bits.

    Arithmetic, from ``runtime.reference.rope``: each BF16 code widens exactly
    to binary32, the four products and the two sums are binary32 with one
    rounding each, and the pair converts to BF16 once at the end.  That single
    output rounding is the whole difference from the Qwen kernel, which rounds
    each product to BF16 before summing.

    ``input 1`` is ``cos[rotary_width] || sin[rotary_width]`` with pair ``p``'s
    coefficient repeated at ``2p`` and ``2p + 1``, so the coefficient row reads
    channel-for-channel against the block it rotates and the engine never has
    to know how the table was folded.
    """
    input_view = ctx.input_view(operator, 0)
    coefficient_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    width = int(input_view.dims[-1])
    rotary = _rotary_width(operator, width)
    _require(
        coefficient_view.dtype == DType.FP32,
        f"RoPE coefficient view {coefficient_view.descriptor_id} stores "
        f"{DType(coefficient_view.dtype).name}; {contract} applies its phasor "
        "in binary32 and takes a binary32 table",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    values = _read_rows(ctx, input_view, width)
    raw = ctx.read(coefficient_view)
    coefficients = (
        np.ascontiguousarray(raw).reshape(1, -1)
        if raw.ndim == 1
        else _read_rows(ctx, coefficient_view, 2 * rotary)
    )
    _require(
        coefficients.shape[-1] == 2 * rotary,
        f"RoPE coefficient view {coefficient_view.descriptor_id} has last axis "
        f"{coefficients.shape[-1]}; expected cosine then sine over the "
        f"{rotary} rotated channels",
    )
    _require(
        coefficients.shape[0] in (1, values.shape[0]),
        f"RoPE coefficient view {coefficient_view.descriptor_id} has "
        f"{coefficients.shape[0]} rows; the input has {values.shape[0]}",
    )
    with _numeric_guard(contract):
        rotated = deepseek_rope_binary32(
            values,
            np.ascontiguousarray(coefficients, dtype=np.float32),
            rotary_width=rotary,
            inverse=contract == CONTRACT_DEEPSEEK_ROPE_INVERSE,
        )
    ctx.write(output_view, rotated.reshape(output_view.dims))
    rows = int(values.shape[0])
    pairs = rows * (rotary // 2)
    ctx.counters.add("vector.rope_pairs", pairs)
    ctx.counters.add("vector.elements", int(values.size))
    # One conversion per rotated value, and none for the preserved prefix:
    # the reference's ``binary32_to_bf16_conversions`` is exactly this.
    ctx.counters.add("vector.conversions", rows * rotary)


def deepseek_rope_binary32(
    values: np.ndarray,
    coefficients: np.ndarray,
    *,
    rotary_width: int,
    inverse: bool,
) -> np.ndarray:
    """The data-bearing form of ``runtime.reference.rope``'s suffix rotation.

    ``values`` are BF16 codes ``[rows, width]``; ``coefficients`` are binary32
    ``[rows or 1, 2 * rotary_width]``.  Returns BF16 codes of the input's shape.
    """
    rows, width = values.shape
    prefix = width - rotary_width
    suffix = values[:, prefix:]
    real = widen_bf16(np.ascontiguousarray(suffix[:, 0::2]))
    imaginary = widen_bf16(np.ascontiguousarray(suffix[:, 1::2]))
    cosine = np.ascontiguousarray(coefficients[:, 0:rotary_width:2], dtype=np.float32)
    sine = np.ascontiguousarray(coefficients[:, rotary_width::2], dtype=np.float32)
    if inverse:
        # The conjugate phasor.  Negating the stored sine is exact, and it is
        # what ``freqs_cis.conj()`` does.  Zero negates to *positive* zero,
        # which is the reference's canonical arithmetic zero rather than a
        # sign flip -- a negated zero would carry its sign into the product.
        sine = np.where(sine == 0, np.float32(0.0), -sine).astype(np.float32)
    real_output = np.subtract(
        np.multiply(real, cosine, dtype=np.float32),
        np.multiply(imaginary, sine, dtype=np.float32),
        dtype=np.float32,
    )
    imaginary_output = np.add(
        np.multiply(real, sine, dtype=np.float32),
        np.multiply(imaginary, cosine, dtype=np.float32),
        dtype=np.float32,
    )
    if not np.all(np.isfinite(real_output)) or not np.all(
        np.isfinite(imaginary_output)
    ):
        raise ValueError("rotary binary32 arithmetic produced NaN or infinity")
    real_codes, real_saturated = narrow_bf16_rne(real_output)
    imaginary_codes, imaginary_saturated = narrow_bf16_rne(imaginary_output)
    if real_saturated or imaginary_saturated:
        raise ValueError("rotary BF16 conversion overflowed")
    rotated = np.empty((rows, width), dtype=np.uint16)
    rotated[:, :prefix] = values[:, :prefix]
    rotated[:, prefix::2] = real_codes
    rotated[:, prefix + 1 :: 2] = imaginary_codes
    return rotated


# ---------------------------------------------------------------------------
# VECTOR.ADD
# ---------------------------------------------------------------------------
@register(Major.VECTOR, Vector.ADD)
def _vector_add(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """Residual add of two equal-shape BF16 tensors through one rounding."""
    profile = _profile(ctx, operator)
    left_view = ctx.input_view(operator, 0)
    right_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(left_view, profile.input_dtype, "ADD left")
    _check_dtype(right_view, profile.second_input_dtype, "ADD right")
    _check_dtype(output_view, profile.output_dtype, "ADD output")
    _require(
        left_view.dtype == DType.BF16 and output_view.dtype == DType.BF16,
        "the residual add contract is BF16 in and BF16 out",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    _same_shape(left_view, right_view, "ADD operand shape")
    _same_shape(left_view, output_view, "ADD output shape")
    width = int(left_view.dims[-1])
    left = _read_rows(ctx, left_view, width)
    right = _read_rows(ctx, right_view, width)
    with _numeric_guard("bf16_add_rne_v1"):
        result = bf16_add_rne(left, right)
    ctx.counters.add(
        "vector.saturations", int(result.output_saturated_element_count)
    )
    ctx.write(output_view, result.values.reshape(output_view.dims))
    ctx.counters.add("vector.elements", int(left.size))
    ctx.counters.add("vector.conversions", int(left.size))


# ---------------------------------------------------------------------------
# VECTOR.SILU_MUL
# ---------------------------------------------------------------------------
#: The released DeepSeek ``swiglu_limit``, as the binary32 codes the reference
#: substitutes for a clamped operand.
_SWIGLU_LIMIT_BINARY32 = np.uint32(OFFICIAL_SWIGLU_LIMIT_BINARY32)
_NEGATIVE_SWIGLU_LIMIT_BINARY32 = np.uint32(OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32)
_SWIGLU_LIMIT = np.uint32(OFFICIAL_SWIGLU_LIMIT_BINARY32).view(np.float32)

#: The two SwiGLU sites of the released DeepSeek MoE -- the FP8 shared expert
#: and the MXFP4 routed one -- whose vector stage is one function.
_DEEPSEEK_SWIGLU_CONTRACTS = (
    CONTRACT_DEEPSEEK_FP8_SWIGLU,
    CONTRACT_DEEPSEEK_MXFP4_SWIGLU,
)


def deepseek_clamped_silu_product_bf16(
    gate_codes: np.ndarray, up_codes: np.ndarray
) -> tuple[np.ndarray, int, int, int]:
    """``*_swiglu_bf16_clamped_silu_product_v1``: one rounding, at the output.

    The arithmetic is ``runtime.reference.swiglu``'s vector stage with no
    routing weight, which the graph carries as its own ``MUL``: widen both BF16
    projections exactly to binary32; substitute the limit code for a gate above
    ``+10`` and for an up projection outside ``+/-10``; take the correctly
    rounded binary32 logistic of the *clamped* gate; multiply it by the clamped
    gate and then by the clamped up projection, each a single binary32
    rounding; and convert once to BF16.

    Returns ``(codes, saturations, gate_clamps, up_clamps)``.
    """
    gate = np.ascontiguousarray(widen_bf16(np.ascontiguousarray(gate_codes, dtype=np.uint16)))
    up = np.ascontiguousarray(widen_bf16(np.ascontiguousarray(up_codes, dtype=np.uint16)))
    if not (bool(np.all(np.isfinite(gate))) and bool(np.all(np.isfinite(up)))):
        raise EngineError(
            "the clamped SwiGLU contract is defined on finite BF16 projections",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    gate_bits = gate.view(np.uint32).copy()
    up_bits = up.view(np.uint32).copy()
    gate_high = gate > _SWIGLU_LIMIT
    up_low = up < -_SWIGLU_LIMIT
    up_high = up > _SWIGLU_LIMIT
    gate_bits[gate_high] = _SWIGLU_LIMIT_BINARY32
    up_bits[up_low] = _NEGATIVE_SWIGLU_LIMIT_BINARY32
    up_bits[up_high] = _SWIGLU_LIMIT_BINARY32
    clamped_gate = gate_bits.view(np.float32)
    clamped_up = up_bits.view(np.float32)
    sigmoid = _map_codes(gate_bits, binary32_sigmoid_rne).view(np.float32)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        silu = np.multiply(clamped_gate, sigmoid, dtype=np.float32)
        gated = np.multiply(silu, clamped_up, dtype=np.float32)
    finally:
        np.seterr(**previous)
    if not bool(np.all(np.isfinite(gated))):
        raise EngineError(
            "the clamped SwiGLU product left the binary32 range",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    codes, saturations = narrow_bf16_rne(gated)
    return (
        np.ascontiguousarray(codes, dtype=np.uint16),
        int(saturations),
        int(np.count_nonzero(gate_high)),
        int(np.count_nonzero(up_low) + np.count_nonzero(up_high)),
    )


def _silu_mul_contract(ctx: EngineContext, profile: NumericProfile) -> str:
    """Which of the two SwiGLU contracts this descriptor names.

    Fails closed on a digest that names neither.  They are different
    operations: Qwen's clamps nothing and materialises the SiLU activation in
    BF16 before it gates the up projection, while the released DeepSeek MoE
    clamps at ``swiglu_limit`` and stays in binary32 through the gating.  This
    engine executed Qwen's for both until amendment A22, which is why the
    DeepSeek graph declared ``*_clamped_silu_product_v1`` at 86 sites a prefill
    and got the unclamped arithmetic at every one of them.
    """
    contract = declared_contract(ctx.table, profile.descriptor_id)
    _require(
        contract in (CONTRACT_QWEN_SILU_MUL, *_DEEPSEEK_SWIGLU_CONTRACTS),
        f"numeric profile {profile.descriptor_id} names no SwiGLU contract this "
        f"engine implements; expected {CONTRACT_QWEN_SILU_MUL} (no clamp, BF16 "
        f"activation boundary) or {CONTRACT_DEEPSEEK_FP8_SWIGLU} / "
        f"{CONTRACT_DEEPSEEK_MXFP4_SWIGLU} (clamped at the released "
        "swiglu_limit, binary32 through the gating)",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    profile.contract = contract
    return contract


@register(Major.VECTOR, Vector.SILU_MUL)
def _vector_silu_mul(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """SiLU the gate and multiply the up path, under the declared contract.

    ``output 1``, when bound, receives the materialised BF16 activation.  Only
    the Qwen contract has one: the DeepSeek clamped product never leaves
    binary32 between the SiLU and the gating, so there is no such value to
    write and a bound slot is refused rather than filled with a number the
    contract does not define.
    """
    profile = _profile(ctx, operator)
    _require(
        operator.payload["input_view_2"] == NO_ID,
        "the three-operand SwiGLU form has no frozen numeric contract; bind the "
        "gate and up projections only",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    gate_view = ctx.input_view(operator, 0)
    up_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(gate_view, profile.input_dtype, "SILU_MUL gate")
    _check_dtype(up_view, profile.second_input_dtype, "SILU_MUL up")
    _check_dtype(output_view, profile.output_dtype, "SILU_MUL output")
    _require(
        gate_view.dtype == DType.BF16 and output_view.dtype == DType.BF16,
        "the SiLU-multiply contract is BF16 in and BF16 out",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    _same_shape(gate_view, up_view, "SILU_MUL operand shape")
    _same_shape(gate_view, output_view, "SILU_MUL output shape")
    contract = _silu_mul_contract(ctx, profile)
    width = int(gate_view.dims[-1])
    gate = _read_rows(ctx, gate_view, width)
    up = _read_rows(ctx, up_view, width)
    if contract == CONTRACT_QWEN_SILU_MUL:
        with _numeric_guard(CONTRACT_QWEN_SILU_MUL):
            result = qwen3_silu_mul_bf16(gate, up)
        ctx.write(output_view, result.values.reshape(output_view.dims))
        if operator.payload["output_view_1"] != NO_ID:
            activation_view = ctx.output_view(operator, 1)
            _same_shape(gate_view, activation_view, "SILU_MUL activation shape")
            ctx.write(
                activation_view,
                result.activation_values.reshape(activation_view.dims),
            )
    else:
        _require(
            operator.payload["output_view_1"] == NO_ID,
            f"{contract} keeps the SiLU activation in binary32, so it "
            "materialises no BF16 activation for output 1",
            TrapClass.CAPABILITY_OR_RESOURCE,
        )
        with _numeric_guard(contract):
            codes, saturations, gate_clamps, up_clamps = (
                deepseek_clamped_silu_product_bf16(gate, up)
            )
        ctx.write(output_view, codes.reshape(output_view.dims))
        ctx.counters.add("vector.saturations", saturations)
        # ``gate_clamps`` and ``up_clamps`` are returned for callers and tests
        # but deliberately not counted: the frozen registry has no clamp event,
        # and a clamp is a value the *contract* replaced, not an exceptional
        # value or a saturation.  Filing it under either would put a routine,
        # expected substitution into a counter whose whole meaning is that
        # something went wrong.
        del gate_clamps, up_clamps
    ctx.counters.add("vector.activation_elements", int(gate.size))
    ctx.counters.add("vector.elements", 2 * int(gate.size))
    # The SiLU activation and the gated product each round once under the Qwen
    # contract; the clamped one rounds only at the output.
    ctx.counters.add(
        "vector.conversions",
        (2 if contract == CONTRACT_QWEN_SILU_MUL else 1) * int(gate.size),
    )


# ---------------------------------------------------------------------------
# VECTOR.CONVERT
# ---------------------------------------------------------------------------
@register(Major.VECTOR, Vector.CONVERT)
def _vector_convert(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """Storage-format conversion, block dequantisation and block quantisation.

    Three descriptor shapes select the three lowered kernel kinds:

    * one input and one output -- ``CONVERT``/``KV_APPEND``: widen the source
      to binary32 and round once into the destination format, or move the
      elements unchanged when both formats agree;
    * two inputs and one output -- ``DEQUANTIZE``: input 1 supplies one block
      scale per ``block`` elements of input 0's last axis;
    * one input and two outputs -- ``QUANTIZE``: output 0 receives E4M3FN
      codes and output 1 the E8M0 block scale, exactly as
      ``runtime.reference.formats.quantize_bf16_activation_block`` specifies.
    """
    has_second_input = operator.payload["input_view_1"] != NO_ID
    has_second_output = operator.payload["output_view_1"] != NO_ID
    _require(
        not (has_second_input and has_second_output),
        "CONVERT takes either a scale input or a scale output, never both",
    )
    if has_second_output:
        _convert_quantize(ctx, operator)
        return
    if has_second_input:
        _convert_dequantize(ctx, operator)
        return

    source_view = ctx.input_view(operator, 0)
    output_view = ctx.output_view(operator, 0)
    _unscaled(source_view, "CONVERT source")
    _unscaled(output_view, "CONVERT destination")
    _same_shape(source_view, output_view, "CONVERT output shape")
    source = ctx.read(source_view)
    if source_view.dtype == output_view.dtype:
        ctx.write(output_view, np.ascontiguousarray(source).reshape(output_view.dims))
        ctx.counters.add("vector.elements", int(source.size))
        return
    with _numeric_guard(f"CONVERT source view {source_view.descriptor_id}"):
        values = widen(source_view.dtype, source)
    _finite(ctx, values, f"CONVERT source view {source_view.descriptor_id}")
    _, conversions = _write_rows(ctx, output_view, values)
    ctx.counters.add("vector.elements", int(values.size))
    ctx.counters.add("vector.conversions", conversions)


def _convert_dequantize(ctx: EngineContext, operator: Descriptor) -> None:
    code_view = ctx.input_view(operator, 0)
    scale_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    carried_view = (
        ctx.input_view(operator, 2)
        if operator.payload["input_view_2"] != NO_ID
        else None
    )
    if carried_view is None:
        _same_shape(code_view, output_view, "DEQUANTIZE output shape")
    else:
        # A *partial* dequantisation.  DeepSeek quantises the 448 non-rotary
        # channels of a 512-wide KV vector and keeps the 64 rotary ones in
        # BF16, because the rotary channels carry position and cannot afford
        # E4M3FN.  Reconstructing the vector therefore reads two sources, which
        # is why the shared lowering table gives ``DEQUANTIZE`` three inputs:
        # the codes, their scales, and the plane the untouched channels come
        # from.  Expressing it as a two-operand dequantize plus a concatenation
        # would need an axis ``REDUCTION.GROUPED_CONCAT`` does not have -- it
        # joins on axis 0, and this joins on the last one.
        _same_shape(carried_view, output_view, "DEQUANTIZE carried plane shape")
        _require(
            carried_view.dtype == output_view.dtype,
            f"DEQUANTIZE carried view {carried_view.descriptor_id} stores "
            f"{DType(carried_view.dtype).name} and the destination stores "
            f"{DType(output_view.dtype).name}; the carried channels are moved, "
            "not converted",
            TrapClass.CAPABILITY_OR_RESOURCE,
        )
        _require(
            output_view.dtype == DType.BF16,
            "the partial dequantisation contract reconstructs into BF16",
            TrapClass.CAPABILITY_OR_RESOURCE,
        )
        _require(
            len(code_view.dims) == len(output_view.dims)
            and tuple(code_view.dims[:-1]) == tuple(output_view.dims[:-1])
            and 0 < int(code_view.dims[-1]) < int(output_view.dims[-1]),
            f"DEQUANTIZE code view {code_view.descriptor_id} is {code_view.dims} "
            f"and the destination is {output_view.dims}; a partial "
            "dequantisation reconstructs a prefix of each row and carries the "
            "rest",
        )
    width = int(code_view.dims[-1])
    rows = _rows(code_view.dims)
    scale_rows = _rows(scale_view.dims)
    blocks = int(scale_view.dims[-1])
    _require(
        scale_rows == rows and blocks > 0 and width % blocks == 0,
        f"DEQUANTIZE scale view {scale_view.descriptor_id} is {scale_view.dims}; "
        f"expected {rows} rows of block scales dividing {width}",
    )
    block = width // blocks
    codes = np.ascontiguousarray(ctx.read(code_view)).reshape(rows, blocks, block)
    with _numeric_guard(f"DEQUANTIZE codes view {code_view.descriptor_id}"):
        values = widen(code_view.dtype, codes)
    scale_codes = np.ascontiguousarray(ctx.read(scale_view)).reshape(rows, blocks)
    with _numeric_guard(f"DEQUANTIZE scale view {scale_view.descriptor_id}"):
        scales = widen(
            DType.E8M0_SCALE if scale_view.dtype == DType.U8 else scale_view.dtype,
            scale_codes,
        )
    _finite(ctx, values, f"DEQUANTIZE codes view {code_view.descriptor_id}")
    _finite(ctx, scales, f"DEQUANTIZE scale view {scale_view.descriptor_id}")
    scaled = np.multiply(values, scales[:, :, None], dtype=np.float32)
    _finite(ctx, scaled, "DEQUANTIZE product")
    if carried_view is None:
        _, conversions = _write_rows(ctx, output_view, scaled.reshape(code_view.dims))
        ctx.counters.add("vector.elements", int(values.size))
        ctx.counters.add("vector.conversions", conversions)
        return
    full = int(output_view.dims[-1])
    with _numeric_guard(f"output view {output_view.descriptor_id}"):
        reconstructed, saturations = narrow_bf16_rne(scaled.reshape(rows, width))
    ctx.counters.add("vector.saturations", int(saturations))
    carried = _read_rows(ctx, carried_view, full)
    output = np.empty((rows, full), dtype=np.uint16)
    output[:, :width] = reconstructed
    # The carried channels are copied, not converted: the reference preserves
    # their codes exactly, and a round trip through binary32 would count a
    # conversion the architecture never performs.
    output[:, width:] = carried[:, width:]
    ctx.write(output_view, output.reshape(output_view.dims))
    ctx.counters.add("vector.elements", int(values.size))
    ctx.counters.add("vector.conversions", int(reconstructed.size))


def _convert_quantize(ctx: EngineContext, operator: Descriptor) -> None:
    source_view = ctx.input_view(operator, 0)
    code_view = ctx.output_view(operator, 0)
    scale_view = ctx.output_view(operator, 1)
    _require(
        source_view.dtype == DType.BF16,
        f"QUANTIZE source view {source_view.descriptor_id} stores "
        f"{DType(source_view.dtype).name}; the block activation quantiser is "
        "specified from BF16",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    _require(
        code_view.dtype
        in (DType.FP8_E4M3FN, DType.MXFP4_E2M1, DType.FP4_E2M1_S16_E4M3),
        f"QUANTIZE code view {code_view.descriptor_id} stores "
        f"{DType(code_view.dtype).name}; expected FP8_E4M3FN, MXFP4_E2M1 or "
        "FP4_E2M1_S16_E4M3",
    )
    # AM-E10's format carries an E4M3FN scale, and the other two carry an E8M0
    # one.  The scale view's dtype is checked against the CODE view's format
    # rather than against a single permitted set, because a group of E2M1
    # elements beside an E8M0 scale is ``MXFP4_E2M1`` and the same elements
    # beside an E4M3FN scale are ``FP4_E2M1_S16_E4M3``: the scale is what tells
    # the two apart, so accepting either scale for either format would make the
    # storage codes decorative.
    if code_view.dtype == DType.FP4_E2M1_S16_E4M3:
        _require(
            scale_view.dtype == DType.FP8_E4M3FN,
            f"QUANTIZE scale view {scale_view.descriptor_id} stores "
            f"{DType(scale_view.dtype).name}; FP4_E2M1_S16_E4M3 is defined with "
            "an E4M3FN scale",
        )
    else:
        _require(
            scale_view.dtype in (DType.E8M0_SCALE, DType.U8),
            f"QUANTIZE scale view {scale_view.descriptor_id} stores "
            f"{DType(scale_view.dtype).name}; expected an E8M0 scale",
        )
    _same_shape(source_view, code_view, "QUANTIZE code shape")
    width = int(source_view.dims[-1])
    rows = _rows(source_view.dims)
    blocks = int(scale_view.dims[-1])
    _require(
        _rows(scale_view.dims) == rows and blocks > 0 and width % blocks == 0,
        f"QUANTIZE scale view {scale_view.descriptor_id} is {scale_view.dims}; "
        f"expected {rows} rows of block scales dividing {width}",
    )
    block = width // blocks
    source = _read_rows(ctx, source_view, width).reshape(rows * blocks, block)
    # The generic E4M3FN quantiser searches for the block scale and refuses to
    # saturate.  Both pinned QDQ contracts instead derive a scale and clamp;
    # FP8 therefore needs its declared contract as well as its output dtype to
    # distinguish two different rules over the same storage formats.
    fp4 = code_view.dtype == DType.MXFP4_E2M1
    contract = declared_contract(ctx.table, operator.payload["numeric_profile_id"])
    if code_view.dtype == DType.FP4_E2M1_S16_E4M3:
        # The group is the operator's, taken from the scale view, not a constant:
        # the format's name says 16 because that is DeepSeek-V4.1-Flash's main
        # latent group, and a different deployment of the same format would state
        # a different one in its own descriptors.
        with _numeric_guard("fp4_e2m1_s16_e4m3_to_fp8_quantize_v1"):
            flat_codes, flat_scales, saturations = _quantize_fp4_s16_e4m3_blocks(
                source
            )
    elif fp4:
        _require(
            block == exact_quantization.FP4_QDQ_BLOCK_SIZE,
            f"QUANTIZE code view {code_view.descriptor_id} is MXFP4_E2M1 with a "
            f"{block}-element block; the qualified FP4 block is "
            f"{exact_quantization.FP4_QDQ_BLOCK_SIZE}",
        )
        with _numeric_guard("quantization_fp4_qdq_bf16_quantize_v1"):
            flat_codes, flat_scales, saturations = _quantize_fp4_qdq_blocks(source)
    elif contract == CONTRACT_DEEPSEEK_FP8_QDQ_QUANTIZE:
        # The block is the operator's, and it is checked against the lengths the
        # reference is QUALIFIED at rather than against one constant.  Comparing
        # to a single value refused DeepSeek-V4.1-Flash at PC 64 of its own
        # program for declaring the 32-element block its
        # quantization_config.weight_block_size states, while the arithmetic --
        # a per-block amax with a binary32 1e-4 floor, one multiply by
        # RN(1/448) and a ceil(log2) -- never depended on the length.  The set
        # is a qualification, not a permission: each entry is established in
        # tests/runtime/test_deepseek_v4_fp8_qdq.py against an independent
        # scalar recomputation, and the two lengths are shown to disagree on the
        # same row so neither is checking the other's arithmetic.  The sibling
        # FP4_E2M1_S16_E4M3 branch above already takes its group from the
        # operator's own scale view for the same reason.
        _require(
            block in exact_quantization.FP8_QDQ_QUALIFIED_BLOCK_SIZES,
            f"QUANTIZE code view {code_view.descriptor_id} names {contract} with "
            f"a {block}-element block; the qualified FP8 blocks are "
            f"{exact_quantization.FP8_QDQ_QUALIFIED_BLOCK_SIZES}",
        )
        with _numeric_guard(contract):
            flat_codes, flat_scales, saturations = _quantize_fp8_qdq_blocks(source)
    else:
        with _numeric_guard("block activation quantisation"):
            flat_codes, flat_scales, saturations = _quantize_activation_blocks(source)
    codes = flat_codes.reshape(rows, blocks, block)
    scales = flat_scales.reshape(rows, blocks)
    ctx.write(code_view, codes.reshape(code_view.dims))
    ctx.write(scale_view, scales.reshape(scale_view.dims))
    ctx.counters.add("vector.elements", int(source.size))
    ctx.counters.add("vector.conversions", int(codes.size) + int(scales.size))
    if saturations:
        ctx.counters.add("vector.saturations", int(saturations))
        if not fp4 and contract != CONTRACT_DEEPSEEK_FP8_QDQ_QUANTIZE:
            raise EngineError(
                f"QUANTIZE saturated {saturations} E4M3FN block(s)",
                trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
            )


# ---------------------------------------------------------------------------
# VECTOR.SCALE
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1 << 16)
def _sigmoid_binary32_from_bf16(code: int) -> int:
    """The exact logistic sigmoid of one BF16 code, as a binary32 encoding.

    Composed from the exact scalar primitives in
    ``runtime.reference.formats``: one correctly rounded binary32 exponential
    of a non-positive argument, one binary32 denominator addition and one
    binary32 division, sign-selected for stability.  This is the same subgraph
    the frozen SiLU contract uses.
    """
    value = code << 16
    if code & 0x8000:
        exponential = exact.binary32_exp_nonpositive(value)
        denominator = exact.binary32_add(int(_ONE), exponential)
        return exact.binary32_divide(exponential, denominator)
    negated = 0 if value & 0x7FFFFFFF == 0 else value ^ 0x80000000
    exponential = exact.binary32_exp_nonpositive(negated)
    denominator = exact.binary32_add(int(_ONE), exponential)
    return exact.binary32_divide(int(_ONE), denominator)


def _map_codes(codes: np.ndarray, function) -> np.ndarray:
    """Apply an exact scalar code-to-code map over the distinct codes only."""
    flat = np.ascontiguousarray(codes).reshape(-1)
    unique, inverse = np.unique(flat, return_inverse=True)
    mapped = np.fromiter(
        (function(int(code)) for code in unique), dtype=np.uint32, count=unique.size
    )
    return mapped[inverse].reshape(codes.shape)


#: ``VECTOR.SCALE`` sub-cases, named by ``aux_id_0`` (amendment A8).
SCALE_CONSTANT = 0
SCALE_ELEMENTWISE = 1
SCALE_SIGMOID = 2

_SCALE_SUBCASE_NAMES = {
    SCALE_CONSTANT: "0 (multiply by the profile's scale_bits)",
    SCALE_ELEMENTWISE: "1 (elementwise multiply by input_view_1)",
    SCALE_SIGMOID: "2 (logistic sigmoid)",
}


def _scale_subcase(operator: Descriptor) -> int:
    """Resolve the ``VECTOR.SCALE`` sub-case from ``aux_id_0``.

    Amendment A8 moved this out of the numeric profile.  The first
    implementation read it from ``scale_bits != 0``, which makes a legitimate
    scale of zero unrepresentable -- a descriptor asking for "multiply by
    zero" was silently executed as the logistic sigmoid.  ``aux_id_0`` now
    names the sub-case outright, matching the ``COMPRESS``/``MHC`` pattern.

    An unnamed ``aux_id_0`` is accepted only where the operand map already
    settles the question: ``input_view_1`` bound can only be the elementwise
    product.  With one operand and no sub-case there is nothing left to read
    it from, so it fails closed rather than guessing.
    """
    aux = int(operator.payload["aux_id_0"])
    if aux in _SCALE_SUBCASE_NAMES:
        return aux
    if aux == NO_ID:
        if operator.payload["input_view_1"] != NO_ID:
            return SCALE_ELEMENTWISE
        raise EngineError(
            "VECTOR.SCALE names no sub-case in aux_id_0 and binds one operand; "
            "the constant scale and the logistic sigmoid are then "
            "indistinguishable.  Amendment A8 requires aux_id_0: "
            + ", ".join(_SCALE_SUBCASE_NAMES[k] for k in sorted(_SCALE_SUBCASE_NAMES)),
            trap_class=int(TrapClass.DESCRIPTOR_OR_ADDRESS),
        )
    raise EngineError(
        f"VECTOR.SCALE sub-case {aux} is not defined; aux_id_0 is "
        + ", ".join(_SCALE_SUBCASE_NAMES[k] for k in sorted(_SCALE_SUBCASE_NAMES)),
        trap_class=int(TrapClass.DESCRIPTOR_OR_ADDRESS),
    )


@register(Major.VECTOR, Vector.SCALE)
def _vector_scale(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """Elementwise product, constant scale, or logistic sigmoid.

    ``aux_id_0`` names which: ``0`` multiplies by the numeric profile's
    ``scale_bits``, ``1`` multiplies elementwise by ``input_view_1``, and ``2``
    is the exact logistic sigmoid.  Under sub-case ``1`` the second operand may
    cover only the trailing axes, which is how a per-channel gain is applied to
    ``[tokens, channels]`` without a broadcast copy.
    """
    profile = _profile(ctx, operator)
    subcase = _scale_subcase(operator)
    source_view = ctx.input_view(operator, 0)
    second_view = ctx.optional_input(operator, 1)
    output_view = ctx.output_view(operator, 0)
    _unscaled(source_view, "SCALE source")
    _same_shape(source_view, output_view, "SCALE output shape")
    _check_dtype(source_view, profile.input_dtype, "SCALE source")
    _check_dtype(output_view, profile.output_dtype, "SCALE output")
    source = ctx.read(source_view)

    _require(
        (second_view is not None) == (subcase == SCALE_ELEMENTWISE),
        f"VECTOR.SCALE sub-case {_SCALE_SUBCASE_NAMES[subcase]} "
        + (
            "does not read input_view_1, but one is bound"
            if second_view is not None
            else "requires input_view_1, which is unbound"
        ),
    )

    if subcase == SCALE_ELEMENTWISE:
        assert second_view is not None  # settled by the check above
        _check_dtype(second_view, profile.second_input_dtype, "SCALE factor")
        _unscaled(second_view, "SCALE factor")
        trailing = tuple(source_view.dims[len(source_view.dims) - len(second_view.dims) :])
        _require(
            tuple(second_view.dims) == trailing,
            f"SCALE factor view {second_view.descriptor_id} is "
            f"{second_view.dims}; expected {trailing} to broadcast over "
            f"{source_view.dims}",
        )
        backend = get_backend()
        with _numeric_guard("SCALE operands"):
            left = widen(source_view.dtype, source)
            right = widen(second_view.dtype, ctx.read(second_view))
        _finite(ctx, left, f"SCALE source view {source_view.descriptor_id}")
        _finite(ctx, right, f"SCALE factor view {second_view.descriptor_id}")
        with _numeric_guard("SCALE product"):
            values = backend.fetch(backend.multiply(left, right))
        _finite(ctx, values, "SCALE product")
        _, conversions = _write_rows(ctx, output_view, values)
        ctx.counters.add("vector.elements", int(left.size))
        ctx.counters.add("vector.conversions", conversions)
        return

    if subcase == SCALE_CONSTANT:
        with _numeric_guard(f"SCALE source view {source_view.descriptor_id}"):
            left = widen(source_view.dtype, source)
        _finite(ctx, left, f"SCALE source view {source_view.descriptor_id}")
        constant = np.float32(profile.scale)
        _require(
            np.isfinite(constant),
            f"numeric profile {profile.descriptor_id} declares a non-finite "
            "constant scale",
            TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
        )
        backend = get_backend()
        with _numeric_guard("SCALE product"):
            values = backend.fetch(
                backend.multiply(left, np.full((1,), constant, dtype=np.float32))
            )
        _finite(ctx, values, "SCALE product")
        _, conversions = _write_rows(ctx, output_view, values)
        ctx.counters.add("vector.elements", int(left.size))
        ctx.counters.add("vector.conversions", conversions)
        return

    _require(
        source_view.dtype == DType.BF16,
        f"the sigmoid form of SCALE takes BF16 input; view "
        f"{source_view.descriptor_id} stores {DType(source_view.dtype).name}",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    codes = np.ascontiguousarray(source, dtype=np.uint16)
    with _numeric_guard("logistic sigmoid"):
        binary32 = _map_codes(codes, _sigmoid_binary32_from_bf16)
    values = binary32.view(np.float32)
    _, conversions = _write_rows(ctx, output_view, values)
    ctx.counters.add("vector.activation_elements", int(codes.size))
    ctx.counters.add("vector.elements", int(codes.size))
    ctx.counters.add("vector.conversions", conversions)


# ---------------------------------------------------------------------------
# VECTOR.SOFTMAX
# ---------------------------------------------------------------------------
def _ordered_row_sum(values: np.ndarray, order: int) -> np.ndarray:
    """Reduce each row under the declared binary32 reduction order.

    The three orders are the frozen enumeration: strictly ascending,
    a balanced pairwise tree, and the eight-lane blocked accumulation that
    matches ``binary32_lanes8_sum``.  The backend owns all three so that one
    substrate selection covers the engine's reductions as well as its
    contractions.
    """
    return np.ascontiguousarray(
        get_backend().fetch(get_backend().reduce_sum(values, order=int(order))),
        dtype=np.float32,
    )


@register(Major.VECTOR, Vector.SOFTMAX)
def _vector_softmax(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """Row softmax over the last axis.

    The row maximum is subtracted before the binary32 exponential, so the
    exponential's argument is non-positive and its correctly rounded result is
    defined by ``runtime.reference.formats.binary32_exp_nonpositive``.  The
    denominator uses the numeric profile's reduction order, and the row is
    scaled by one binary32 reciprocal rather than divided element by element.
    """
    profile = _profile(ctx, operator)
    source_view = ctx.input_view(operator, 0)
    output_view = ctx.output_view(operator, 0)
    _unscaled(source_view, "SOFTMAX source")
    _same_shape(source_view, output_view, "SOFTMAX output shape")
    _check_dtype(source_view, profile.input_dtype, "SOFTMAX source")
    _check_dtype(output_view, profile.output_dtype, "SOFTMAX output")
    width = int(source_view.dims[-1])
    _require(width > 0, "SOFTMAX row is empty")
    codes = _read_rows(ctx, source_view, width)
    with _numeric_guard(f"SOFTMAX source view {source_view.descriptor_id}"):
        values = widen(source_view.dtype, codes)
    _finite(ctx, values, f"SOFTMAX source view {source_view.descriptor_id}")

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        maximum = np.max(values, axis=1, keepdims=True)
        shifted = np.subtract(values, maximum, dtype=np.float32)
        # Evaluate with binary64 guard precision and round once to binary32:
        # NumPy's float32 exponential is an approximation, not the correctly
        # rounded binary32 operation the contract names.
        exponentials = np.ascontiguousarray(
            np.exp(shifted.astype(np.float64)).astype(np.float32), dtype=np.float32
        )
        exponentials = np.where(
            shifted <= _EXP_ZERO_CUTOFF, np.float32(0.0), exponentials
        ).astype(np.float32, copy=False)
        _finite(ctx, exponentials, "SOFTMAX exponential")
        denominator = _ordered_row_sum(exponentials, int(profile.reduction_order))
        if not np.all(np.isfinite(denominator)) or np.any(denominator <= 0):
            raise EngineError(
                "SOFTMAX denominator is not positive finite",
                trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
            )
        inverse = np.divide(np.float32(1.0), denominator, dtype=np.float32)
        probabilities = np.multiply(
            exponentials, inverse[:, None], dtype=np.float32
        )
    finally:
        np.seterr(**previous)

    rows = int(codes.shape[0])
    _, conversions = _write_rows(
        ctx, output_view, probabilities.reshape(source_view.dims)
    )
    ctx.counters.add("vector.softmax_rows", rows)
    ctx.counters.add("vector.elements", int(values.size))
    ctx.counters.add("vector.conversions", conversions)


# ---------------------------------------------------------------------------
# VECTOR.SQRT_SOFTPLUS
# ---------------------------------------------------------------------------
@register(Major.VECTOR, Vector.SQRT_SOFTPLUS)
def _vector_sqrt_softplus(
    ctx: EngineContext, sub: int, operator: Descriptor
) -> None:
    """``sqrt(softplus(x))`` with both stages rounded once in binary32.

    The scalar semantics are the exact, host-``libm``-independent rounding in
    ``runtime.reference.sqrt_softplus``; this engine applies it to the distinct
    input encodings of the tensor rather than to every element.
    """
    profile = _profile(ctx, operator)
    source_view = ctx.input_view(operator, 0)
    output_view = ctx.output_view(operator, 0)
    _unscaled(source_view, "SQRT_SOFTPLUS source")
    _same_shape(source_view, output_view, "SQRT_SOFTPLUS output shape")
    _check_dtype(source_view, profile.input_dtype, "SQRT_SOFTPLUS source")
    _check_dtype(output_view, profile.output_dtype, "SQRT_SOFTPLUS output")
    _require(
        source_view.dtype in (DType.FP32, DType.BF16),
        f"SQRT_SOFTPLUS source view {source_view.descriptor_id} stores "
        f"{DType(source_view.dtype).name}; the operator is defined on binary32 "
        "scores",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    source = np.ascontiguousarray(ctx.read(source_view))
    if source_view.dtype == DType.BF16:
        codes = source.astype(np.uint32) << np.uint32(16)
    else:
        codes = source.view(np.uint32)
    with _numeric_guard("deepseek_v4 SQRT_SOFTPLUS"):
        mapped = _map_codes(codes, binary32_sqrt_softplus_rne)
    values = np.ascontiguousarray(mapped).view(np.float32)
    _, conversions = _write_rows(ctx, output_view, values)
    ctx.counters.add("vector.activation_elements", int(values.size))
    ctx.counters.add("vector.elements", int(values.size))
    ctx.counters.add("vector.conversions", conversions)


# ---------------------------------------------------------------------------
# VECTOR.HADAMARD
# ---------------------------------------------------------------------------
@register(Major.VECTOR, Vector.HADAMARD)
def _vector_hadamard(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """The normalised 128-point Hadamard rotation.

    Seven ascending-stride binary32 butterfly stages, one binary32
    normalisation product and one BF16 conversion, exactly as
    ``runtime.reference.hadamard`` freezes them.  Signed zero is canonicalised
    to positive zero at every stage, which is what makes the vectorised
    butterfly identical to the scalar one.
    """
    profile = _profile(ctx, operator)
    source_view = ctx.input_view(operator, 0)
    output_view = ctx.output_view(operator, 0)
    _unscaled(source_view, "HADAMARD source")
    _same_shape(source_view, output_view, "HADAMARD output shape")
    _check_dtype(source_view, profile.input_dtype, "HADAMARD source")
    _check_dtype(output_view, profile.output_dtype, "HADAMARD output")
    _require(
        source_view.dtype == DType.BF16 and output_view.dtype == DType.BF16,
        "the Hadamard rotation contract is BF16 in and BF16 out",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    width = int(source_view.dims[-1])
    _require(
        width == HADAMARD_WIDTH,
        f"HADAMARD view {source_view.descriptor_id} has width {width}; the "
        f"qualified transform is {HADAMARD_WIDTH}-point",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    codes = _read_rows(ctx, source_view, width)
    with _numeric_guard("deepseek_v4 Hadamard rotation"):
        values = widen_bf16(codes).copy()
    _finite(ctx, values, f"HADAMARD source view {source_view.descriptor_id}")
    values[values == 0] = np.float32(0.0)
    rows = values.shape[0]
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        for stride in HADAMARD_STRIDES:
            blocks = values.reshape(rows, -1, 2, stride)
            lower = blocks[:, :, 0, :]
            upper = blocks[:, :, 1, :]
            summed = np.add(lower, upper, dtype=np.float32)
            differed = np.subtract(lower, upper, dtype=np.float32)
            blocks[:, :, 0, :] = summed
            blocks[:, :, 1, :] = differed
            values = blocks.reshape(rows, width)
            values[values == 0] = np.float32(0.0)
            _finite(ctx, values, "HADAMARD butterfly stage")
        scale = np.asarray([HADAMARD_SCALE_BINARY32], dtype=np.uint32).view(np.float32)[0]
        scaled = np.multiply(values, scale, dtype=np.float32)
    finally:
        np.seterr(**previous)
    _finite(ctx, scaled, "HADAMARD normalisation")
    with _numeric_guard("HADAMARD BF16 conversion"):
        narrowed, saturations = narrow_bf16_rne(scaled)
    if saturations:
        ctx.counters.add("vector.saturations", int(saturations))
        raise EngineError(
            "HADAMARD output saturated the BF16 range",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    ctx.write(output_view, narrowed.reshape(output_view.dims))
    ctx.counters.add("vector.elements", int(codes.size))
    ctx.counters.add("vector.conversions", int(codes.size))
# ---------------------------------------------------------------------------
# VECTOR.ENGRAM_GATE
# ---------------------------------------------------------------------------
#: The numeric contract this sub-op executes, and the module that *is* that
#: contract.  ``runtime.reference.engram.engram_gate`` states every step of the
#: gate as an exact rational computation with one named rounding, so this engine
#: calls it rather than restating the arithmetic: a second statement of a
#: contract is a second thing to get wrong.
ENGRAM_GATE_CONTRACT = ENGRAM_GATE_NUMERIC_CONTRACT

#: ``EngramGateResult.refusal_stage`` values, by name, so a trap message can
#: attribute a refusal to one line of the contract rather than to "the gate
#: failed".  The reference's numbering is the RTL's ``refusal_stage`` port.
_ENGRAM_GATE_REFUSALS: dict[int, str] = {
    1: "operand shape",
    2: "a nonfinite q or k",
    3: "a product outside the reduction's exactness window",
    4: "rounding the exact dot",
    5: "rounding an exact squared norm",
    6: "the norm square root",
    7: "the clamped denominator",
    8: "the normalising division",
    9: "the signed square root",
    10: "the sigmoid",
    11: "a nonfinite h, key or value in the combine",
    12: "the combine's range",
}


def _engram_gate_codes(
    ctx: EngineContext, view: ResolvedView, width: int, label: str
) -> np.ndarray:
    """Read a binary32 operand of the gate as ``[rows, width]`` of codes."""
    _unscaled(view, f"ENGRAM_GATE {label}")
    _require(
        view.dtype == DType.FP32,
        f"ENGRAM_GATE {label} view {view.descriptor_id} stores "
        f"{DType(view.dtype).name}; the {ENGRAM_GATE_CONTRACT} contract is "
        "binary32 throughout",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    values = _read_rows(ctx, view, width)
    return np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)


@register(Major.VECTOR, Vector.ENGRAM_GATE)
def _vector_engram_gate(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """The Engram gated residual: ``engram_gate_fp32_v1``.

    ``in0`` is the residual stream ``h``, ``[rows, width]``.  ``in1`` is the
    Engram key/value projection: the plan's operand row names ``key`` and
    ``value`` separately and they are the two halves of one projection output,
    so they arrive as one ``[2, width]`` view -- or ``[rows, 2, width]`` when
    each row has its own -- with plane 0 the key and plane 1 the value.  ``in2``
    and ``in3`` are the gate's query and key rows ``q`` and ``k``.  ``out0`` is
    ``h'``.  Five operands into four input views is the ABI's ceiling, and the
    pair that shares a view is the pair the model already computes together.

    Per row, exactly :func:`runtime.reference.engram.engram_gate`::

        dot   = rne(exact sum of q_i k_i)          nq2, nk2 likewise
        denom = max(rne(sqrt(nq2) * sqrt(nk2)), epsilon)
        gate  = sigmoid(sign(dot/denom) * sqrt(|dot/denom|))
        h'_i  = rne(h_i + rne(gate * rne(key_i * value_i)))

    The reduction is *exact* before its single rounding, so the result does not
    depend on a reduction order and this operator does not read one from its
    profile -- a registered tree and a serial accumulator give the same code.
    The clamp floor is the profile's epsilon, which the released model sets to
    ``1e-6``; a profile that declares none is refused rather than given the
    reference's default, because a silently supplied clamp is a numeric contract
    nobody wrote down.  Nothing about the model's shape appears here: rows, the
    width, and whether the key/value pair is shared all come from the views.

    A refusal the contract defines -- a nonfinite operand, a product outside the
    exactness window, a transcendental the reference will not certify -- becomes
    a trap naming the site, so a campaign can predict which line fired.
    """
    profile = _profile(ctx, operator)
    state_view = ctx.input_view(operator, 0)
    kv_view = ctx.input_view(operator, 1)
    query_view = ctx.input_view(operator, 2)
    gate_key_view = ctx.input_view(operator, 3)
    out_view = ctx.output_view(operator, 0)
    _check_dtype(state_view, profile.input_dtype, "ENGRAM_GATE state")
    _check_dtype(kv_view, profile.second_input_dtype, "ENGRAM_GATE key/value")
    _check_dtype(out_view, profile.output_dtype, "ENGRAM_GATE output")
    _same_shape(state_view, out_view, "ENGRAM_GATE output shape")
    _same_shape(state_view, query_view, "ENGRAM_GATE query shape")
    _same_shape(state_view, gate_key_view, "ENGRAM_GATE gate-key shape")
    _require(
        profile.epsilon_bits != 0,
        f"numeric profile {profile.descriptor_id} declares no epsilon; the "
        f"{ENGRAM_GATE_CONTRACT} clamp floor is a declared value, not one this "
        "engine may supply",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    width = int(state_view.dims[-1])
    _require(width > 0, "ENGRAM_GATE state row is empty")
    rows = _rows(state_view.dims)

    state = _engram_gate_codes(ctx, state_view, width, "state")
    query = _engram_gate_codes(ctx, query_view, width, "query")
    gate_key = _engram_gate_codes(ctx, gate_key_view, width, "gate key")
    _require(
        len(kv_view.dims) >= 2 and int(kv_view.dims[-2]) == 2,
        f"ENGRAM_GATE key/value view {kv_view.descriptor_id} is {kv_view.dims}; "
        f"the key and the value are the two planes of a [2, {width}] view, or "
        f"of a [rows, 2, {width}] one",
    )
    pairs = _engram_gate_codes(ctx, kv_view, width, "key/value").reshape(-1, 2, width)
    _require(
        pairs.shape[0] in (1, rows),
        f"ENGRAM_GATE key/value view {kv_view.descriptor_id} holds "
        f"{pairs.shape[0]} pair(s) for {rows} state row(s); a retrieved pair is "
        "shared by every row or given one each",
    )

    epsilon_code = int(profile.epsilon_bits)
    results = np.empty((rows, width), dtype=np.uint32)
    gates: list[int] = []
    for row in range(rows):
        pair = pairs[0] if pairs.shape[0] == 1 else pairs[row]
        with _numeric_guard(ENGRAM_GATE_CONTRACT):
            outcome = engram_gate(
                [int(code) for code in state[row]],
                [int(code) for code in pair[0]],
                [int(code) for code in pair[1]],
                [int(code) for code in query[row]],
                [int(code) for code in gate_key[row]],
                epsilon_code=epsilon_code,
                # The admitted width is the operand's own, so no model geometry
                # bounds this operator from inside the engine.
                max_width=width,
            )
        if outcome.refusal_stage != 0:
            site = _ENGRAM_GATE_REFUSALS.get(
                int(outcome.refusal_stage), "an unnumbered site"
            )
            ctx.counters.add("vector.exceptional_values", 1)
            raise EngineError(
                f"ENGRAM_GATE row {row} refused at site "
                f"{int(outcome.refusal_stage)} ({site}), engine error code "
                f"{int(outcome.error_code)}, after "
                f"{int(outcome.written_words)} of {width} output word(s)",
                trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
            )
        results[row] = np.asarray(outcome.output_codes, dtype=np.uint32)
        gates.append(int(outcome.gate_code))

    ctx.write(out_view, results.view(np.float32).reshape(out_view.dims))
    # Two normalisations and one sigmoid per row, as the V4.1 operator
    # accounting charges an Engram module.
    ctx.counters.add("vector.norm_rows", 2 * rows)
    ctx.counters.add("vector.activation_elements", rows)
    ctx.counters.add("vector.elements", int(results.size))
    notes = ctx.notes.setdefault("engram_gate", {})
    notes["gate_codes"] = tuple(gates)
