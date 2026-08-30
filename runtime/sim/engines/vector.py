"""VECTOR engine: normalisation, rotation, elementwise and activation kernels.

Ten frozen subopcodes live here.  Each names one numeric contract, and each
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
from runtime.sim.backend import (
    CONTRACT_DEEPSEEK_RMSNORM,
    CONTRACT_DEEPSEEK_ROPE,
    CONTRACT_DEEPSEEK_ROPE_INVERSE,
    CONTRACT_QWEN_RMSNORM,
    CONTRACT_QWEN_ROPE,
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
@register(Major.VECTOR, Vector.SILU_MUL)
def _vector_silu_mul(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    """SiLU the gate, materialise it in BF16, and multiply the up path.

    ``output 1``, when bound, receives the materialised BF16 activation.
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
    width = int(gate_view.dims[-1])
    gate = _read_rows(ctx, gate_view, width)
    up = _read_rows(ctx, up_view, width)
    with _numeric_guard("qwen3_silu_mul_bf16_v1"):
        result = qwen3_silu_mul_bf16(gate, up)
    ctx.write(output_view, result.values.reshape(output_view.dims))
    if operator.payload["output_view_1"] != NO_ID:
        activation_view = ctx.output_view(operator, 1)
        _same_shape(gate_view, activation_view, "SILU_MUL activation shape")
        ctx.write(
            activation_view,
            result.activation_values.reshape(activation_view.dims),
        )
    ctx.counters.add("vector.activation_elements", int(gate.size))
    ctx.counters.add("vector.elements", 2 * int(gate.size))
    # The SiLU activation and the gated product each round once.
    ctx.counters.add("vector.conversions", 2 * int(gate.size))


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
        code_view.dtype == DType.FP8_E4M3FN,
        f"QUANTIZE code view {code_view.descriptor_id} stores "
        f"{DType(code_view.dtype).name}; expected FP8_E4M3FN",
    )
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
