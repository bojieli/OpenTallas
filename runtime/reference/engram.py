"""Independent exact semantics for the DeepSeek-V4.1-Flash Engram mechanisms.

This module is the reference authority named by
[`docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`](../../docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md)
section 7 for the Engram additions of section 5.  It is written from the stated
mechanism semantics and the exact IEEE binary32 primitives already qualified in
`runtime/reference/formats.py`; it does not transcribe, call, or read any RTL,
compiler, simulator engine, or cost table.

Each function documents the numeric contract it implements and the boundary of
what that contract does *not* establish.  Every arithmetic step is an exact
rational computation followed by one explicitly named rounding, so the result
is independent of any host floating-point mode, ``libm`` build, or reduction
order chosen by a datapath.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import isqrt

from .formats import (
    NumericReferenceError,
    binary32_divide,
    binary32_multiply,
    binary32_rsqrt,
    decode_binary32,
    encode_binary32_rne,
)
from .hyper_connection import binary32_sigmoid_rne


# --------------------------------------------------------------------------
# VECTOR.ENGRAM_GATE -- numeric contract engram_gate_fp32_v1
# --------------------------------------------------------------------------

#: Binary32 encoding of the pinned 1e-6 clamp floor.  The same code the V4
#: RMS-norm epsilon uses, and the value the plan's section 5 row 6 names.
ENGRAM_GATE_EPSILON_BINARY32 = 0x358637BD

#: Numeric contract identifier published by the capability record.
ENGRAM_GATE_NUMERIC_CONTRACT = "engram_gate_fp32_v1"

#: V4.1-Flash Engram row width, from SRC-DSV41-FLASH-INDEX: the two FP8 tables
#: are [384,006,168, 256] and [384,016,682, 256].  It is a DEFAULT here, never a
#: frozen bound: every entry point takes the width from its operands.
ENGRAM_GATE_DEFAULT_WIDTH = 256

#: Default exactness window of the fused reduction, as exponents of two.  A
#: product whose exact value is nonzero and whose least significant bit falls
#: below 2**ACC_EXP_MIN, or whose magnitude reaches 2**ACC_EXP_MAX, is refused
#: rather than rounded: the contract's reduction is exact or it does not run.
#: ACC_EXP_MIN defaults to -126 so that every representable nonzero exact sum
#: is at least the smallest binary32 normal and no subnormal rounding path
#: exists in the reduction.
ENGRAM_GATE_DEFAULT_ACC_EXP_MIN = -126
ENGRAM_GATE_DEFAULT_ACC_EXP_MAX = 64

#: Refusal sites, numbered so a trap can be attributed to one line of the
#: contract instead of to "the block failed".  The RTL reports the same
#: numbering on its ``refusal_stage`` port.
REFUSAL_NONE = 0
REFUSAL_SHAPE = 1
REFUSAL_REDUCE_OPERAND = 2
REFUSAL_REDUCE_WINDOW = 3
REFUSAL_DOT_ROUND = 4
REFUSAL_NORM_ROUND = 5
REFUSAL_NORM_SQRT = 6
REFUSAL_DENOMINATOR = 7
REFUSAL_DIVIDE = 8
REFUSAL_SIGNED_SQRT = 9
REFUSAL_SIGMOID = 10
REFUSAL_COMBINE_OPERAND = 11
REFUSAL_COMBINE_RANGE = 12

#: Engine error codes of ``rtl/abi3/ot_a3_engine_pkg.sv``, mirrored so the
#: reference predicts the architectural code as well as the site.
ERR_NONE = 0
ERR_OPERAND_NONFINITE = 1
ERR_PRODUCT_RANGE = 2
ERR_ACCUMULATE_RANGE = 3
ERR_SHAPE = 7

_REFUSAL_ERROR_CODE = {
    REFUSAL_NONE: ERR_NONE,
    REFUSAL_SHAPE: ERR_SHAPE,
    REFUSAL_REDUCE_OPERAND: ERR_OPERAND_NONFINITE,
    REFUSAL_REDUCE_WINDOW: ERR_ACCUMULATE_RANGE,
    REFUSAL_DOT_ROUND: ERR_ACCUMULATE_RANGE,
    REFUSAL_NORM_ROUND: ERR_ACCUMULATE_RANGE,
    REFUSAL_NORM_SQRT: ERR_PRODUCT_RANGE,
    REFUSAL_DENOMINATOR: ERR_PRODUCT_RANGE,
    REFUSAL_DIVIDE: ERR_PRODUCT_RANGE,
    REFUSAL_SIGNED_SQRT: ERR_PRODUCT_RANGE,
    REFUSAL_SIGMOID: ERR_PRODUCT_RANGE,
    REFUSAL_COMBINE_OPERAND: ERR_OPERAND_NONFINITE,
    REFUSAL_COMBINE_RANGE: ERR_PRODUCT_RANGE,
}

_BINARY32_MAX_FINITE = 0x7F7FFFFF


class EngramReferenceError(ValueError):
    """Raised when a request is malformed rather than architecturally refused.

    A refusal the contract defines -- a nonfinite operand, a product outside the
    exactness window, a transcendental the engine will not certify -- is
    *returned* as a refusal site, because the target fails closed and the
    campaign has to predict which site fired.  Only a request that could never
    be issued at all (a negative width, mismatched operand lengths) raises.
    """


@dataclass(frozen=True)
class EngramGateResult:
    """Every architecturally visible word of one ENGRAM_GATE transaction.

    On a refused transaction the scalar fields hold exactly what the contract
    had already produced when the refusal fired, and zero for everything after
    it.  That is what a fail-closed target leaves in its diagnostic registers,
    so predicting it is part of predicting the refusal.
    """

    #: Refusal site, 0 when the transaction retires.
    refusal_stage: int
    #: ``ot_a3_engine_pkg`` error code implied by ``refusal_stage``.
    error_code: int
    #: Element count the transaction was issued with.
    width: int
    #: Elements the reduction consumed: the full row unless the request was
    #: refused before the reduction ran at all.
    reduced_words: int
    #: Output words the target is permitted to write.  Equal to ``width`` on a
    #: retiring transaction, and to the number of elements that precede the
    #: first refused *group* when the refusal is raised in the combine phase.
    written_words: int
    #: Rounded exact dot product of q and k.
    dot_code: int
    #: Rounded exact squared norms of q and of k.
    norm_q_square_code: int
    norm_k_square_code: int
    #: Correctly rounded square roots of those squared norms.
    norm_q_code: int
    norm_k_code: int
    #: The rounded norm product before and after the 1e-6 clamp.
    denominator_raw_code: int
    denominator_code: int
    #: True when the clamp replaced the rounded norm product.
    clamped: bool
    #: The normalised dot, the signed square root of it, and the gate.
    cosine_code: int
    signed_sqrt_code: int
    gate_code: int
    #: Output elements the target writes: ``written_words`` long, which on a
    #: refused transaction is the elements of the groups that precede the
    #: refused one and nothing after them.
    output_codes: tuple[int, ...]


def binary32_sqrt_rne(value_code: int) -> int:
    """Correctly round the square root of a nonnegative finite binary32 code.

    An integer square root locates the truncated candidate, and the rounding
    decision is then an exact integer comparison of the candidate midpoint's
    SQUARE against the argument, so no floating-point square root, ``libm``
    call, decimal approximation or enclosure width participates.  Locating the
    candidate by ``math.isqrt`` rather than by bisecting the code space makes
    this a different algorithm from ``runtime/reference/sqrt_softplus.py`` and
    from the RTL's digit recurrence; all three are correctly rounded, so they
    agree by definition, which is why the agreement is evidence about the RTL
    and not about a shared implementation.
    """

    decoded = decode_binary32(value_code)
    if not decoded.finite or decoded.value is None:
        raise NumericReferenceError("binary32 square-root argument is NaN or infinity")
    value = decoded.value
    if value < 0:
        raise NumericReferenceError("binary32 square-root argument is negative")
    if value == 0:
        return 0

    # Locate a candidate within one ulp: isqrt of the argument scaled by an even
    # power of two carries far more bits than binary32 needs.
    scale_bits = 32
    while (value.numerator << (2 * scale_bits)) // value.denominator < (1 << 64):
        scale_bits += 32
    scaled = (value.numerator << (2 * scale_bits)) // value.denominator
    approximate = Fraction(isqrt(scaled), 1 << scale_bits)
    candidate_code = _truncate_to_binary32(approximate)

    # Walk to the exact truncation: the largest finite code whose square does
    # not exceed the argument.  Both comparisons are exact rational ones.
    while candidate_code > 0 and _square(candidate_code) > value:
        candidate_code -= 1
    while (
        candidate_code < _BINARY32_MAX_FINITE
        and _square(candidate_code + 1) <= value
    ):
        candidate_code += 1

    if _square(candidate_code) == value:
        return candidate_code
    if candidate_code >= _BINARY32_MAX_FINITE:  # pragma: no cover - sqrt shrinks
        raise NumericReferenceError("binary32 square root left finite range")

    lower = _require(decode_binary32(candidate_code).value)
    upper = _require(decode_binary32(candidate_code + 1).value)
    midpoint = (lower + upper) / 2
    midpoint_square = midpoint * midpoint
    if value < midpoint_square:
        return candidate_code
    if value > midpoint_square:
        return candidate_code + 1
    return candidate_code if candidate_code % 2 == 0 else candidate_code + 1


def _square(code: int) -> Fraction:
    magnitude = decode_binary32(code).value
    if magnitude is None:  # pragma: no cover - positive finite code space
        raise EngramReferenceError("square requested for a nonfinite code")
    return magnitude * magnitude


def _truncate_to_binary32(value: Fraction) -> int:
    """Encode the largest binary32 code whose value does not exceed ``value``.

    The exponent is found by exact comparison against powers of two and the
    significand by exact integer division, so the truncation never depends on a
    host rounding mode.  ``value`` is strictly positive.
    """

    exponent = 0
    while Fraction(2) ** (exponent + 1) <= value:
        exponent += 1
    while Fraction(2) ** exponent > value:
        exponent -= 1
    if exponent < -126:
        # A binary32 square root is at least 2**-75, so a subnormal truncation
        # cannot arise from this function's only caller.
        raise EngramReferenceError("binary32 truncation reached the subnormal range")
    scaled = value / Fraction(2) ** (exponent - 23)
    significand = scaled.numerator // scaled.denominator
    if significand >= 1 << 24:  # pragma: no cover - exponent search invariant
        raise EngramReferenceError("binary32 truncation significand overflowed")
    if exponent > 127:
        raise NumericReferenceError("binary32 truncation left finite range")
    return ((exponent + 127) << 23) | (significand - (1 << 23))


def _exact_finite(code: int, label: str) -> Fraction | None:
    decoded = decode_binary32(code)
    if not decoded.finite or decoded.value is None:
        return None
    return decoded.value


def _significand_and_exponent(code: int) -> tuple[int, int, int]:
    """Return ``(sign, significand, exponent)`` with ``value = s * m * 2**e``.

    ``significand`` is the 24-bit integer significand and ``exponent`` its
    power of two, both exact, which is how the exactness window is checked.
    """

    sign = -1 if code & 0x80000000 else 1
    biased = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if biased == 0:
        return sign, fraction, -149
    return sign, (1 << 23) | fraction, biased - 150


def _product_in_window(
    left_code: int, right_code: int, acc_exp_min: int, acc_exp_max: int
) -> bool:
    """Is the exact product representable in the reduction window?

    Zero always is.  A nonzero product ``m * 2**e`` with ``m`` at most 48 bits
    needs ``e >= acc_exp_min`` for its least significant bit to land on the
    accumulator grid, and ``e + 48 <= acc_exp_max`` for its magnitude to stay
    inside the window.  Both bounds are derived from the window parameters, not
    from a model dimension.
    """

    _, left_significand, left_exponent = _significand_and_exponent(left_code)
    _, right_significand, right_exponent = _significand_and_exponent(right_code)
    if left_significand == 0 or right_significand == 0:
        return True
    exponent = left_exponent + right_exponent
    return exponent >= acc_exp_min and exponent + 48 <= acc_exp_max


def engram_gate(
    hidden_codes: Sequence[int],
    key_codes: Sequence[int],
    value_codes: Sequence[int],
    query_codes: Sequence[int],
    gate_key_codes: Sequence[int],
    *,
    epsilon_code: int = ENGRAM_GATE_EPSILON_BINARY32,
    max_width: int = ENGRAM_GATE_DEFAULT_WIDTH,
    acc_exp_min: int = ENGRAM_GATE_DEFAULT_ACC_EXP_MIN,
    acc_exp_max: int = ENGRAM_GATE_DEFAULT_ACC_EXP_MAX,
    combine_group: int = 1,
) -> EngramGateResult:
    """Execute one ``ENGRAM_GATE(h, key, value, q, k) -> h'`` transaction.

    NUMERIC CONTRACT ``engram_gate_fp32_v1``, in this order, every operand and
    every result a finite IEEE binary32 encoding:

      1. ``dot``  = one RNE rounding of the EXACT sum of ``q_i * k_i``;
         ``nq2``, ``nk2`` likewise for ``q_i * q_i`` and ``k_i * k_i``.  The
         reduction is exact, so it is order independent: a registered tree, a
         serial accumulator and any lane partitioning give the same code, and
         reduction order is therefore not part of the claim.  A product that
         does not fit the exactness window is refused, not rounded.
      2. ``nq = sqrt(nq2)``, ``nk = sqrt(nk2)``, each correctly rounded once.
      3. ``denominator = max(rne(nq * nk), epsilon)`` -- the pinned ``1e-6``
         clamp, applied to the rounded norm product.
      4. ``cosine = rne(dot / denominator)``, the normalised dot.
      5. ``signed_sqrt = sign(cosine) * sqrt(|cosine|)``, correctly rounded,
         with ``+0`` for a zero cosine.  This is the SIGNED square root: the
         gate argument keeps the sign of the normalised dot, which a plain
         square root of a negative value could not.
      6. ``gate = sigmoid(signed_sqrt)``, correctly rounded once.
      7. ``h'_i = rne(h_i + rne(gate * rne(key_i * value_i)))`` -- the residual
         add, three named roundings per element.

    OPERAND ROLES.  ``q`` and ``k`` are the gate's query and key rows; their
    normalised dot is the single scalar gate for the whole row.  ``key`` and
    ``value`` are the two halves of the Engram key/value projection of the 24
    gathered rows, combined elementwise as a gate/value pair.  ``h`` is the
    residual stream the gated term is added to.

    NOT ESTABLISHED.  The pinned ``inference/engram.py`` of revision
    ``dba1be0a40aa45a94ad051997016db3960a90277`` is NOT present in this
    checkout, so this module cannot and does not claim bit equivalence with the
    vendor's ``Engram.forward``.  It implements the mechanism the plan states
    -- normalised dot, signed square root, sigmoid, residual add, in FP32, with
    the ``1e-6`` clamp -- as an explicit deterministic target contract, in the
    same sense as every other numeric contract in this directory.  Confirming
    the operand-role mapping and the reduction convention against the vendor
    source is WP-H work and remains open.

    ``combine_group`` describes the lane grouping of the target that will
    execute the combine phase.  It changes NO output VALUE: ``h'_i`` depends only
    on element ``i``.  What it changes is HOW MANY output words a refused
    transaction is credited with, because a target that writes ``combine_group``
    elements at a time cannot have written a partial group -- so on a refusal
    ``written_words`` and the length of ``output_codes`` are rounded down to the
    group that contains the refused element, and the row one grouping writes is a
    prefix of the row a smaller grouping writes.  A retiring transaction is
    unaffected in every field.
    """

    width = len(hidden_codes)
    if not (
        len(key_codes) == len(value_codes) == len(query_codes)
        == len(gate_key_codes) == width
    ):
        raise EngramReferenceError("ENGRAM_GATE operands differ in length")
    if combine_group < 1:
        raise EngramReferenceError("combine group must be positive")

    partial: dict[str, object] = {
        "width": width,
        "reduced_words": 0,
        "written_words": 0,
        "dot_code": 0,
        "norm_q_square_code": 0,
        "norm_k_square_code": 0,
        "norm_q_code": 0,
        "norm_k_code": 0,
        "denominator_raw_code": 0,
        "denominator_code": 0,
        "clamped": False,
        "cosine_code": 0,
        "signed_sqrt_code": 0,
        "gate_code": 0,
        "output_codes": (),
    }
    if width < 1 or width > max_width:
        return _refused(REFUSAL_SHAPE, partial)

    # ---- 1. the exact reductions -----------------------------------------
    #: The reduction is exact, so the loop order below is a convenience and not
    #: a contract: the same three sums come out of any partitioning.
    partial["reduced_words"] = width
    dot_exact = Fraction(0)
    norm_q_exact = Fraction(0)
    norm_k_exact = Fraction(0)
    for index in range(width):
        query = _exact_finite(query_codes[index], "q")
        gate_key = _exact_finite(gate_key_codes[index], "k")
        if query is None or gate_key is None:
            return _refused(REFUSAL_REDUCE_OPERAND, partial)
        for left, right in (
            (query_codes[index], gate_key_codes[index]),
            (query_codes[index], query_codes[index]),
            (gate_key_codes[index], gate_key_codes[index]),
        ):
            if not _product_in_window(left, right, acc_exp_min, acc_exp_max):
                return _refused(REFUSAL_REDUCE_WINDOW, partial)
        dot_exact += query * gate_key
        norm_q_exact += query * query
        norm_k_exact += gate_key * gate_key

    try:
        partial["dot_code"] = encode_binary32_rne(dot_exact)
    except NumericReferenceError:
        return _refused(REFUSAL_DOT_ROUND, partial)
    try:
        partial["norm_q_square_code"] = encode_binary32_rne(norm_q_exact)
    except NumericReferenceError:
        return _refused(REFUSAL_NORM_ROUND, partial)
    try:
        partial["norm_k_square_code"] = encode_binary32_rne(norm_k_exact)
    except NumericReferenceError:
        return _refused(REFUSAL_NORM_ROUND, partial)

    # ---- 2. the two correctly rounded norms ------------------------------
    try:
        partial["norm_q_code"] = binary32_sqrt_rne(
            int(partial["norm_q_square_code"])
        )
        partial["norm_k_code"] = binary32_sqrt_rne(
            int(partial["norm_k_square_code"])
        )
    except NumericReferenceError:
        return _refused(REFUSAL_NORM_SQRT, partial)

    # ---- 3. the clamped denominator --------------------------------------
    try:
        raw_code = binary32_multiply(
            int(partial["norm_q_code"]), int(partial["norm_k_code"])
        )
    except NumericReferenceError:
        return _refused(REFUSAL_DENOMINATOR, partial)
    epsilon_value = _exact_finite(epsilon_code, "epsilon")
    raw_value = _exact_finite(raw_code, "denominator")
    if epsilon_value is None or raw_value is None or epsilon_value <= 0:
        raise EngramReferenceError("ENGRAM_GATE clamp floor must be finite positive")
    clamped = raw_value < epsilon_value
    partial["denominator_raw_code"] = raw_code
    partial["denominator_code"] = epsilon_code if clamped else raw_code
    partial["clamped"] = clamped

    # ---- 4. the normalised dot -------------------------------------------
    try:
        partial["cosine_code"] = binary32_divide(
            int(partial["dot_code"]), int(partial["denominator_code"])
        )
    except NumericReferenceError:
        return _refused(REFUSAL_DIVIDE, partial)

    # ---- 5. the signed square root ---------------------------------------
    cosine_code = int(partial["cosine_code"])
    try:
        root_code = binary32_sqrt_rne(cosine_code & 0x7FFFFFFF)
    except NumericReferenceError:
        return _refused(REFUSAL_SIGNED_SQRT, partial)
    partial["signed_sqrt_code"] = (
        0 if root_code == 0 else root_code | (cosine_code & 0x80000000)
    )

    # ---- 6. the gate ------------------------------------------------------
    try:
        partial["gate_code"] = binary32_sigmoid_rne(
            int(partial["signed_sqrt_code"])
        )
    except NumericReferenceError:
        return _refused(REFUSAL_SIGMOID, partial)

    # ---- 7. the gated residual add ---------------------------------------
    gate_code = int(partial["gate_code"])
    outputs: list[int] = []
    for index in range(width):
        group_start = (index // combine_group) * combine_group
        for code in (hidden_codes[index], key_codes[index], value_codes[index]):
            if _exact_finite(code, "combine operand") is None:
                partial["written_words"] = group_start
                #: The groups that precede the refused one have already been
                #: written, so their codes are part of the refused result.
                partial["output_codes"] = tuple(outputs[:group_start])
                return _refused(REFUSAL_COMBINE_OPERAND, partial)
        try:
            product = binary32_multiply(key_codes[index], value_codes[index])
            gated = binary32_multiply(gate_code, product)
            total = encode_binary32_rne(
                _require(_exact_finite(hidden_codes[index], "h"))
                + _require(_exact_finite(gated, "gated"))
            )
        except NumericReferenceError:
            partial["written_words"] = group_start
            partial["output_codes"] = tuple(outputs[:group_start])
            return _refused(REFUSAL_COMBINE_RANGE, partial)
        outputs.append(total)

    partial["written_words"] = width
    partial["output_codes"] = tuple(outputs)
    return EngramGateResult(
        refusal_stage=REFUSAL_NONE, error_code=ERR_NONE, **partial  # type: ignore[arg-type]
    )


def _require(value: Fraction | None) -> Fraction:
    if value is None:  # pragma: no cover - guarded by the caller
        raise EngramReferenceError("finite operand expected")
    return value


def _refused(stage: int, partial: dict) -> EngramGateResult:
    """Build the refused result, keeping everything the contract had produced."""

    return EngramGateResult(
        refusal_stage=stage,
        error_code=_REFUSAL_ERROR_CODE[stage],
        **partial,
    )


__all__ = [
    "ENGRAM_GATE_DEFAULT_ACC_EXP_MAX",
    "ENGRAM_GATE_DEFAULT_ACC_EXP_MIN",
    "ENGRAM_GATE_DEFAULT_WIDTH",
    "ENGRAM_GATE_EPSILON_BINARY32",
    "ENGRAM_GATE_NUMERIC_CONTRACT",
    "EngramGateResult",
    "EngramReferenceError",
    "NGRAM_HASH_NUMERIC_CONTRACT",
    "REFUSAL_COMBINE_OPERAND",
    "REFUSAL_COMBINE_RANGE",
    "REFUSAL_DENOMINATOR",
    "REFUSAL_DIVIDE",
    "REFUSAL_DOT_ROUND",
    "REFUSAL_NONE",
    "REFUSAL_NORM_ROUND",
    "REFUSAL_NORM_SQRT",
    "REFUSAL_REDUCE_OPERAND",
    "REFUSAL_REDUCE_WINDOW",
    "REFUSAL_SHAPE",
    "REFUSAL_SIGMOID",
    "REFUSAL_SIGNED_SQRT",
    "binary32_sqrt_rne",
    "engram_gate",
    "ngram_row_ids",
]


# --------------------------------------------------------------------------
# DMA.NGRAM_HASH -- numeric contract ngram_hash_u32_v1
#
# Appended by the DMA.NGRAM_HASH unit.  Every name this mechanism needs is
# local to `ngram_row_ids`, so the two Engram units share this module without
# sharing anything but the docstring above: nothing below is referenced by the
# gate, and nothing above is referenced here.
# --------------------------------------------------------------------------


#: The numeric contract `ngram_row_ids` is the reference for, declared as a
#: module constant for the same reason `ENGRAM_GATE_NUMERIC_CONTRACT` is:
#: `compiler.ir.v3.numeric.require_implemented` will not let a capability
#: declare a contract nothing in the tree implements, and it finds an
#: implementation either by the contract's spelling matching a reference's
#: module path or by a constant naming it.  `ngram_hash_u32_v1` matches neither
#: the module nor the function name, so until this constant existed the name
#: plan section 6.4 publishes could not be declared by any capability -- the
#: arithmetic below was implemented and unreachable from a declaration.  A
#: comment is not a declaration.
NGRAM_HASH_NUMERIC_CONTRACT = "ngram_hash_u32_v1"


def ngram_row_ids(
    token_ids: Sequence[int],
    *,
    order: int,
    head: int,
    multipliers: Sequence[int],
    primes: Sequence[Sequence[int]],
    offsets: Sequence[int],
    pad_id: int,
    compressed_vocab_size: int,
    dead_positions: Sequence[int] = (),
    n_heads: int | None = None,
    order_min: int = 2,
    dividend_bits: int = 63,
    table_rows: int | None = None,
) -> tuple[dict[str, object], ...]:
    """Engram n-gram hash row ids, one record per position of `token_ids`.

    IDENTITY, exactly as the pinned `inference/engram.py` computes it
    (SRC-DSV41-FLASH-MODEL, revision
    `dba1be0a40aa45a94ad051997016db3960a90277`, SHA-256
    `11f35ecbead8150c35aa002b3d180ef290b05a25afe883a11884f94d476d3897`,
    `NgramHashState.forward`).  For a position `p`, an n-gram order `n` and a
    hash head `h`:

        t_j     = pad_id if blocked_j else compressed[p - j]      j = 0..N-1
        blocked_j = OR over i <= j of (p < i or position p-i is DEAD)
        X_n     = t_0*m_0  XOR  t_1*m_1  XOR  ...  XOR  t_{n-1}*m_{n-1}
        row     = (X_n mod P[n][h]) + offset[(n - n_min)*H + h]

    where `N` = `len(multipliers)` = `engram_max_ngram_size`, `m_j` is the
    per-lookback multiplier of the Engram layer, `P[n][h]` is that layer's
    prime bucket size for this (order, head) column, and `offset[...]` is the
    prefix sum of the earlier columns' primes.  The fold is XOR, not addition:
    `rolling = torch.bitwise_xor(rolling, products[..., i])` in the pinned
    source, so the running value after step `i` is exactly the hash of the
    `(i+1)`-gram and each order lands in its own prime-sized bucket range.

    Three properties of the pinned source that this function relies on, and
    that a caller can check independently:

    * the columns are ngram-major and head-minor -- the layout flattens
      `[p for per_ngram in layer for p in per_ngram]` -- and `offsets` is
      `cumsum([0, *sizes[:-1]])` over that flattening, so the sum of a layer's
      primes is exactly its released row count.  For V4.1-Flash that is
      384,006,168 rows for layer 1 and 384,016,682 for layer 14
      (SRC-DSV41-FLASH-CONFIG `engram_num_embeddings`), which is how a caller
      can prove its `primes`/`offsets` are the released ones;
    * look-back is STICKY: once a lookback is blocked by the start of the
      sequence or by a DEAD token (an image span), every deeper lookback of
      that position is blocked too and substitutes `pad_id`;
    * every product is formed in signed 64-bit arithmetic and the released
      multipliers are chosen so `token_id * multiplier` cannot overflow it, so
      `dividend_bits` (63, the positive int64 range) is a CONTRACT and not an
      implementation limit.  A product that reaches it is refused here rather
      than silently wrapped as a fixed-width machine would.

    Modulus and multipliers are OPERANDS, never constants: the two released
    tables differ in every one of their 24 column primes, and the multipliers
    differ per Engram layer, so nothing about the V4.1 geometry is frozen into
    this function.  `order_min` defaults to 2 because the pinned layout's first
    prime row is the 2-gram; the row index used is `order - order_min`.

    NOT ESTABLISHED by this function: the compressed token map itself
    (`build_compressed_token_map` normalizes with the vendor's tokenizer, which
    is not reproduced here -- `token_ids` are already compressed ids), the
    choice of prime and multiplier values (they are arguments), the row read
    that follows, and the gate that consumes it.

    Raises `ValueError` for any input outside the contract, which is how a
    caller derives the fail-closed cases of a hardware implementation.
    """

    def _int(value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} must be an integer, not {type(value)!r}")
        return int(value)

    size = len(multipliers)
    if size < 2:
        raise ValueError("multipliers must hold at least two lookbacks")
    order_min = _int(order_min, "order_min")
    if order_min < 2:
        raise ValueError("order_min must be at least 2: the first fold is a 2-gram")
    if len(primes) != size - order_min + 1:
        raise ValueError(
            f"primes must hold one row per order in [{order_min}, {size}], "
            f"got {len(primes)} rows for {size - order_min + 1} orders"
        )
    heads = len(primes[0]) if n_heads is None else _int(n_heads, "n_heads")
    if heads < 1 or any(len(row) != heads for row in primes):
        raise ValueError("every prime row must hold exactly n_heads entries")
    if len(offsets) != len(primes) * heads:
        raise ValueError(
            f"offsets must hold {len(primes) * heads} columns, got {len(offsets)}"
        )
    vocab = _int(compressed_vocab_size, "compressed_vocab_size")
    if vocab < 1:
        raise ValueError("compressed_vocab_size must be positive")
    dividend_bits = _int(dividend_bits, "dividend_bits")
    if dividend_bits < 1:
        raise ValueError("dividend_bits must be positive")
    order = _int(order, "order")
    head = _int(head, "head")
    if not order_min <= order <= size:
        raise ValueError(f"order {order} is outside [{order_min}, {size}]")
    if not 0 <= head < heads:
        raise ValueError(f"head {head} is outside [0, {heads})")
    pad = _int(pad_id, "pad_id")
    if not 0 <= pad < vocab:
        raise ValueError(f"pad_id {pad} is outside the compressed vocabulary")
    for index, value in enumerate(multipliers):
        if _int(value, f"multipliers[{index}]") < 1:
            raise ValueError(f"multipliers[{index}] must be positive")
    for row_index, row in enumerate(primes):
        for column_index, value in enumerate(row):
            if _int(value, f"primes[{row_index}][{column_index}]") < 2:
                raise ValueError("every prime bucket size must be at least 2")
    for index, value in enumerate(offsets):
        if _int(value, f"offsets[{index}]") < 0:
            raise ValueError("offsets must be non-negative")
    if table_rows is not None:
        rows = _int(table_rows, "table_rows")
        for row_index, row in enumerate(primes):
            for column_index, value in enumerate(row):
                column = row_index * heads + column_index
                if offsets[column] + value > rows:
                    raise ValueError(
                        f"column {column} ends at {offsets[column] + value} "
                        f"beyond the {rows}-row table"
                    )
    dead = {_int(position, "dead_positions") for position in dead_positions}
    prime = int(primes[order - order_min][head])
    column = (order - order_min) * heads + head
    offset = int(offsets[column])
    limit = 1 << dividend_bits

    records: list[dict[str, object]] = []
    for position in range(len(token_ids)):
        blocked = False
        window: list[int] = []
        flags: list[bool] = []
        for shift in range(size):
            source_position = position - shift if position - shift > 0 else 0
            source = _int(token_ids[source_position], f"token_ids[{source_position}]")
            if not 0 <= source < vocab:
                raise ValueError(
                    f"token id {source} at position {source_position} is outside "
                    f"the {vocab}-entry compressed vocabulary"
                )
            flag = position < shift or source_position in dead
            blocked = blocked or flag
            flags.append(flag)
            window.append(pad if blocked else source)
        products = [window[index] * int(multipliers[index]) for index in range(size)]
        for index in range(order):
            if products[index] >= limit:
                raise ValueError(
                    f"product {products[index]} of lookback {index} reaches "
                    f"2**{dividend_bits}: the multiplier and the compressed "
                    f"vocabulary are not compatible"
                )
        dividend = products[0]
        for index in range(1, order):
            dividend ^= products[index]
        remainder = dividend % prime
        records.append(
            {
                "position": position,
                "order": order,
                "head": head,
                "column": column,
                "blocked": tuple(flags),
                "tokens": tuple(window),
                "products": tuple(products),
                "dividend": dividend,
                "prime": prime,
                "remainder": remainder,
                "offset": offset,
                "row_id": remainder + offset,
            }
        )
    return tuple(records)


# ---------------------------------------------------------------------------
# The PINNED form of the Engram gate, and how it differs from
# `engram_gate_fp32_v1` above.
#
# `engram_gate` was written before the pinned `inference/engram.py` and
# `inference/model.py` were available in this checkout; its own docstring says
# so, and says that "confirming the operand-role mapping and the reduction
# convention against the vendor source is WP-H work and remains open".  This is
# that work.  The pinned `model.py::Engram.forward` (SRC-DSV41-FLASH-MODEL,
# SHA-256 4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65) is
#
#     kv          = wkv(embed(hash_ids).flatten(-2))
#     key, value  = kv.split([hc_mult * dim, dim], dim=-1)
#     key         = key.float().unflatten(-1, (hc_mult, dim))
#     weight      = q_weight.float() * k_weight.float()
#     h, eps      = x.float(), self.eps
#     rstd        = rsqrt(h.square().mean(-1) + eps) * rsqrt(key.square().mean(-1) + eps)
#     dot         = (h * weight * key).sum(-1) * rstd * dim ** -0.5
#     gate        = sigmoid(copysign(dot.abs().clamp_min(self.clamp_value).sqrt(), dot))
#     return        (h + gate.unsqueeze(-1) * value.float().unsqueeze(-2)).to(x.dtype)
#
# and it diverges from `engram_gate_fp32_v1` in FOUR ways, none of them a
# rounding detail.  Each was read off the pinned source and then confirmed by
# constructing the released-geometry module and reading the attribute:
# `clamp_value` is 1e-6 and `eps` is `norm_eps` = 1e-20, not one value used
# twice.
#
#   D1  WHAT THE 1e-6 CLAMPS.  The pinned clamp is `dot.abs().clamp_min(1e-6)`
#       -- a floor on the MAGNITUDE OF THE NORMALISED DOT, immediately before
#       the square root, whose only effect is to keep the root off zero.  In
#       `engram_gate_fp32_v1` the 1e-6 floors the NORM PRODUCT, i.e. the
#       DENOMINATOR.  The epsilon inside the pinned normalisation is
#       `norm_eps` = 1e-20, which `engram_gate_fp32_v1` has no term for at all.
#   D2  MEAN, NOT SUM.  The pinned normaliser is `rsqrt(mean(h^2) + eps)`, and
#       the whole dot is then scaled by `dim ** -0.5`.  Over `dim` elements
#       that is `sqrt(dim) / sqrt(sum(h^2) + dim * eps)` and one further
#       `dim ** -0.5`, so the composed scale is NOT the cosine denominator
#       `sqrt(sum q^2) * sqrt(sum k^2)` of `engram_gate_fp32_v1`; it differs by
#       a factor of `dim ** -0.5` as well as by where eps enters.
#   D3  OPERAND ROLES.  The pinned dot is between the RESIDUAL STREAM `h` and
#       the gathered `key`, weighted elementwise by `q_weight * k_weight` --
#       one learned row, not a query row.  `engram_gate_fp32_v1` takes `q` and
#       `k` as two separate operand rows and normalises each of them, so its
#       `hidden_codes` play no part in its gate.  In the pinned form `h` is
#       both the gate's query and the residual.
#   D4  WHAT THE GATE MULTIPLIES.  The pinned residual term is
#       `gate * value`, with `value` shared across the `hc_mult` copies.
#       `engram_gate_fp32_v1` adds `gate * (key_i * value_i)`.
#
# D1, D3 and D4 change the VALUE for ordinary finite inputs, not just the
# rounding; `prove_pinned_form_differs` exhibits one input where they do.
# Nothing here edits `engram_gate` or the vectors built from it: which of the
# two the machine must implement is a contract decision, and this module's job
# is to make the difference impossible to miss.
# ---------------------------------------------------------------------------


#: Binary32 encoding of the pinned `Engram.clamp_value`, the floor on |dot|.
PINNED_GATE_CLAMP_BINARY32 = encode_binary32_rne(Fraction(1, 1_000_000))
#: Binary32 encoding of the pinned `norm_eps`, the term inside both rsqrts.
PINNED_NORM_EPS_BINARY32 = encode_binary32_rne(Fraction(1, 10**20))
#: The name this module gives the pinned expression DAG.  DELIBERATELY NOT
#: `engram_gate_fp32_v1`: it is a different function, and giving it the same
#: contract name is how a deployment would come to hand one to an engine
#: expecting the other.
PINNED_GATE_FORM = "engram_gate_pinned_dsv41_form"


def engram_gate_pinned_divergences() -> tuple[dict[str, str], ...]:
    """The four divergences D1-D4 above, as records an audit can enumerate."""
    return (
        {
            "id": "D1_clamp_target",
            "pinned": "clamp_min(1e-6) applied to |dot|, the normalised dot, before sqrt",
            "contract_v1": "1e-6 applied to the norm product, i.e. the denominator",
            "changes_value": "yes",
        },
        {
            "id": "D2_mean_not_sum",
            "pinned": "rsqrt(mean(h^2) + norm_eps) * rsqrt(mean(key^2) + norm_eps), then * dim**-0.5; norm_eps = 1e-20",
            "contract_v1": "dot / max(sqrt(sum q^2) * sqrt(sum k^2), 1e-6); no eps term",
            "changes_value": "yes",
        },
        {
            "id": "D3_operand_roles",
            "pinned": "dot is h . (q_weight * k_weight * key); h is both gate query and residual",
            "contract_v1": "dot is q . k; hidden_codes take no part in the gate",
            "changes_value": "yes",
        },
        {
            "id": "D4_gated_term",
            "pinned": "h + gate * value, value shared across the hc_mult copies",
            "contract_v1": "h + gate * (key * value), elementwise",
            "changes_value": "yes",
        },
    )


def engram_gate_pinned_form(
    hidden_codes: Sequence[int],
    key_codes: Sequence[int],
    value_codes: Sequence[int],
    weight_codes: Sequence[int],
    *,
    clamp_code: int = PINNED_GATE_CLAMP_BINARY32,
    norm_eps_code: int = PINNED_NORM_EPS_BINARY32,
) -> dict[str, int]:
    """The pinned `Engram.forward` gate for ONE (token, hc copy) row.

    Operands are binary32 encodings: ``hidden_codes`` is `h`, ``key_codes`` the
    gathered key for this copy, ``value_codes`` the shared value, and
    ``weight_codes`` the elementwise product ``q_weight * k_weight`` for this
    copy.  ``dim`` is ``len(hidden_codes)``, DERIVED -- no width is frozen here,
    and the ``dim ** -0.5`` factor is computed from that length.

    Roundings are named and each applied once, in the pinned order.  This is a
    STATEMENT of the pinned expression DAG in exact arithmetic, not a claim of
    bit equality with any particular GPU kernel: torch evaluates
    ``h * weight * key`` and its ``.sum(-1)`` in an order it does not specify,
    so a per-element comparison against the vendor is a measurement to report,
    which is what the oracle does with it, and a difference within the
    reduction's own freedom is not a divergence.

    Returns the named intermediates plus ``output_codes``.
    """
    width = len(hidden_codes)
    if not (len(key_codes) == len(value_codes) == len(weight_codes) == width):
        raise EngramReferenceError(
            "h, key, value and weight rows must all have the same length"
        )
    if width == 0:
        raise EngramReferenceError("the gate needs at least one element")

    def exact(code: int, label: str) -> Fraction:
        value = _exact_finite(code, label)
        if value is None:
            raise EngramReferenceError(f"{label} is not a finite binary32 value")
        return value

    h = [exact(code, "h") for code in hidden_codes]
    key = [exact(code, "key") for code in key_codes]
    weight = [exact(code, "weight") for code in weight_codes]
    eps = exact(norm_eps_code, "norm_eps")

    #: mean of squares + eps, one rounding each, then the pinned rsqrt.
    mean_h = encode_binary32_rne(sum(value * value for value in h) / width + eps)
    mean_k = encode_binary32_rne(sum(value * value for value in key) / width + eps)
    rstd = binary32_multiply(binary32_rsqrt(mean_h), binary32_rsqrt(mean_k))

    #: the weighted dot, then the pinned two scalings.
    raw = encode_binary32_rne(
        sum(h[i] * weight[i] * key[i] for i in range(width))
    )
    #: `dim ** -0.5` is not rational, so it is taken as the binary32 rsqrt of
    #: the width: exactly the value `dim ** -0.5` produces for a power-of-two
    #: width, and the correctly rounded one otherwise.
    scale = binary32_rsqrt(encode_binary32_rne(Fraction(width)))
    dot = binary32_multiply(binary32_multiply(raw, rstd), scale)

    #: |dot| floored at the clamp, square-rooted, then given dot's sign back.
    magnitude = dot & 0x7FFFFFFF
    clamp_value = exact(clamp_code, "clamp")
    if exact(magnitude, "dot magnitude") < clamp_value:
        magnitude = clamp_code
    root = binary32_sqrt_rne(magnitude)
    signed_root = 0 if root == 0 else root | (dot & 0x80000000)
    gate = binary32_sigmoid_rne(signed_root)

    outputs = tuple(
        encode_binary32_rne(
            h[i] + exact(binary32_multiply(gate, value_codes[i]), "gated")
        )
        for i in range(width)
    )
    return {
        "form": PINNED_GATE_FORM,
        "width": width,
        "mean_square_h_code": mean_h,
        "mean_square_key_code": mean_k,
        "rstd_code": rstd,
        "raw_dot_code": raw,
        "dim_rsqrt_code": scale,
        "dot_code": dot,
        "clamped": magnitude == clamp_code and (dot & 0x7FFFFFFF) != clamp_code,
        "signed_sqrt_code": signed_root,
        "gate_code": gate,
        "output_codes": outputs,
    }


def prove_pinned_form_differs() -> dict[str, object]:
    """Exhibit one finite input on which the pinned form and v1 disagree.

    Returns both gates and both first output elements.  This is the executable
    half of D1-D4: it does not argue that the two contracts differ, it runs
    them on the same operands and reports the two answers.
    """
    width = 8
    one = encode_binary32_rne(Fraction(1))
    h = tuple(encode_binary32_rne(Fraction(i + 1, 4)) for i in range(width))
    key = tuple(encode_binary32_rne(Fraction(width - i, 8)) for i in range(width))
    value = tuple(encode_binary32_rne(Fraction(i + 1, 16)) for i in range(width))
    weight = tuple(one for _ in range(width))

    pinned = engram_gate_pinned_form(h, key, value, weight)
    #: v1's q and k are the operands its own gate normalises.  Feeding it the
    #: pinned operands in the roles it names -- q = h * weight, k = key -- is
    #: the most favourable reading available to it.
    v1 = engram_gate(h, key, value, h, key)
    return {
        "width": width,
        "pinned_form": PINNED_GATE_FORM,
        "pinned_gate_code": pinned["gate_code"],
        "pinned_gate_value": float(decode_binary32(pinned["gate_code"]).value or 0),
        "pinned_first_output_code": pinned["output_codes"][0],
        "contract_v1": ENGRAM_GATE_NUMERIC_CONTRACT,
        "v1_gate_code": v1.gate_code,
        "v1_gate_value": float(decode_binary32(v1.gate_code).value or 0),
        "v1_first_output_code": v1.output_codes[0],
        "gate_codes_differ": pinned["gate_code"] != v1.gate_code,
        "outputs_differ": pinned["output_codes"][0] != v1.output_codes[0],
        "divergences": engram_gate_pinned_divergences(),
    }
