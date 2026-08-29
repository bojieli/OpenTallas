from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction

import pytest

import runtime.reference.hyper_connection as hc_reference
from runtime.reference.formats import (
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    encode_binary32_rne,
)
from runtime.reference.hyper_connection import (
    FLATTENED_WIDTH,
    HC_MULTIPLIER,
    HIDDEN_SIZE,
    KERNEL_SOURCE_SHA256,
    MIX_PARAMETER_COUNT,
    MODEL_SOURCE_SHA256,
    NORMALIZATION_EPSILON_BINARY32,
    NUMERIC_PROFILE,
    SINKHORN_EPSILON_BINARY32,
    SINKHORN_ITERATIONS,
    HCPreReferenceError,
    binary32_exp_rne,
    binary32_exp_rne_with_diagnostics,
    binary32_sigmoid_rne,
    binary32_sigmoid_rne_with_diagnostics,
    hc_pre_bf16,
    hc_split_sinkhorn_binary32,
)


ZERO_STREAM = (0,) * HIDDEN_SIZE
ZERO_TOKEN = (ZERO_STREAM,) * HC_MULTIPLIER
ZERO_PROJECTION_ROW = (0,) * FLATTENED_WIDTH
ZERO_PROJECTION = (ZERO_PROJECTION_ROW,) * MIX_PARAMETER_COUNT
ZERO_SCALE = (0, 0, 0)
ZERO_BASE = (0,) * MIX_PARAMETER_COUNT


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _token_with_flat_prefix(codes: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    assert len(codes) <= HIDDEN_SIZE
    return ((codes + (0,) * (HIDDEN_SIZE - len(codes))),) + (ZERO_STREAM,) * 3


def _projection_with_first_row_prefix(
    codes: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    first = codes + (0,) * (FLATTENED_WIDTH - len(codes))
    return (first,) + (ZERO_PROJECTION_ROW,) * (MIX_PARAMETER_COUNT - 1)


def _independent_sinkhorn_stages(
    softmax: tuple[tuple[int, ...], ...],
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    """Rebuild stage order with explicit four-term pair trees."""

    matrix = [list(row) for row in softmax]

    def sum4(values: tuple[int, int, int, int]) -> int:
        return binary32_add(
            binary32_add(values[0], values[1]),
            binary32_add(values[2], values[3]),
        )

    def rows() -> None:
        denominators = tuple(
            binary32_add(sum4(tuple(row)), SINKHORN_EPSILON_BINARY32) for row in matrix
        )
        for source in range(4):
            for destination in range(4):
                matrix[source][destination] = binary32_divide(
                    matrix[source][destination], denominators[source]
                )

    def columns() -> None:
        denominators = tuple(
            binary32_add(
                sum4(tuple(matrix[source][destination] for source in range(4))),
                SINKHORN_EPSILON_BINARY32,
            )
            for destination in range(4)
        )
        for source in range(4):
            for destination in range(4):
                matrix[source][destination] = binary32_divide(
                    matrix[source][destination], denominators[destination]
                )

    snapshots = []
    columns()
    snapshots.append(tuple(tuple(row) for row in matrix))
    for _ in range(19):
        rows()
        columns()
        snapshots.append(tuple(tuple(row) for row in matrix))
    return tuple(snapshots)


def test_hc_pre_profile_is_bound_to_pinned_sources_and_dimensions() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert KERNEL_SOURCE_SHA256 == (
        "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
    )
    assert NUMERIC_PROFILE == "opentallas.deepseek_v4_hc_pre_numeric.v1"
    assert (HC_MULTIPLIER, HIDDEN_SIZE, FLATTENED_WIDTH) == (4, 4096, 16384)
    assert MIX_PARAMETER_COUNT == 24
    assert SINKHORN_ITERATIONS == 20
    assert NORMALIZATION_EPSILON_BINARY32 == SINKHORN_EPSILON_BINARY32 == 0x358637BD


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (_f32(0), 0x3F800000),
        (_f32(-1), 0x3EBC5AB2),
        (_f32(-2), 0x3E0A9555),
        (_f32(-10), 0x383E6BCE),
        (_f32(-100), 0x0000001B),
        (_f32(-256), 0x00000000),
        (0x80000000, 0x3F800000),
    ],
)
def test_exp32_exact_interval_known_answers(code: int, expected: int) -> None:
    assert binary32_exp_rne(code) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-256, 0x00000000),
        (-100, 0x0000001B),
        (-10, 0x383E6997),
        (-2, 0x3DF420A9),
        (-1, 0x3E89B2B1),
        (0, 0x3F000000),
        (1, 0x3F3B26A8),
        (2, 0x3F617BEB),
        (10, 0x3F7FFD06),
        (100, 0x3F800000),
        (256, 0x3F800000),
    ],
)
def test_sigmoid32_is_one_direct_correctly_rounded_boundary(
    value: int, expected: int
) -> None:
    assert binary32_sigmoid_rne(_f32(value)) == expected


def test_exact_interval_refinement_is_reported_and_exceeds_initial_precision() -> None:
    exp_result = binary32_exp_rne_with_diagnostics(_f32(-100))
    sigmoid_result = binary32_sigmoid_rne_with_diagnostics(_f32(-100))
    assert exp_result.code == sigmoid_result.code == 0x0000001B
    assert exp_result.interval_evaluations == 3
    assert exp_result.final_precision_bits == 192
    assert sigmoid_result.interval_evaluations == 3
    assert sigmoid_result.final_precision_bits == 192

    exact_exp = binary32_exp_rne_with_diagnostics(_f32(0))
    exact_sigmoid = binary32_sigmoid_rne_with_diagnostics(_f32(0))
    assert (exact_exp.interval_evaluations, exact_exp.final_precision_bits) == (0, 0)
    assert (
        exact_sigmoid.interval_evaluations,
        exact_sigmoid.final_precision_bits,
    ) == (0, 0)


def test_transcendentals_match_independently_regenerated_decimal_corpus() -> None:
    # Expected codes were independently regenerated at both 180- and
    # 260-decimal-digit precision with Python libmpdec; both precisions agreed
    # before these literals were frozen. The production reference above does
    # not import or call Decimal/libm.
    corpus = {
        0x80000001: (0x3F800000, 0x3F000000),
        0x8D800000: (0x3F800000, 0x3F000000),
        0xB3800000: (0x3F7FFFFF, 0x3F000000),
        0xBDCCCCCD: (0x3F67A36D, 0x3EF335EE),
        0xBEAAAAAB: (0x3F376E98, 0x3ED5B95C),
        0xBF000000: (0x3F1B4598, 0x3EC14D03),
        0xBF800000: (0x3EBC5AB2, 0x3E89B2B1),
        0xBFC00000: (0x3E647C3C, 0x3E3ACDC2),
        0xC0400000: (0x3D4BED86, 0x3D4241A2),
        0xC0E00000: (0x3A6F0B5D, 0x3A6ED39C),
        0xC1200000: (0x383E6BCE, 0x383E6997),
        0xC1A00000: (0x310DA433, 0x310DA433),
        0xC2480000: (0x1B692BEB, 0x1B692BEB),
        0xC2A00000: (0x05BFECBA, 0x05BFECBA),
        0xC2C80000: (0x0000001B, 0x0000001B),
    }
    for code, (expected_exp, expected_sigmoid) in corpus.items():
        assert binary32_exp_rne(code) == expected_exp
        assert binary32_sigmoid_rne(code) == expected_sigmoid


@pytest.mark.parametrize("value", [Fraction(-100), Fraction(-10), Fraction(-1, 3)])
def test_exp_exact_enclosures_are_nested_and_strictly_convergent(
    value: Fraction,
) -> None:
    previous: tuple[Fraction, Fraction] | None = None
    for precision in (48, 96, 192):
        lower, upper = hc_reference._exp_negative_fixed_interval(value, precision)
        scale = 1 << precision
        current = (Fraction(lower, scale), Fraction(upper, scale))
        assert current[0] <= current[1]
        if previous is not None:
            assert previous[0] <= current[0] <= current[1] <= previous[1]
            assert current[1] - current[0] < previous[1] - previous[0]
        previous = current


@pytest.mark.parametrize(
    ("function", "code", "match"),
    [
        (binary32_exp_rne, _f32(1), "must be nonpositive"),
        (binary32_exp_rne, 0x7F800000, "finite binary32"),
        (binary32_exp_rne, 0x7FC00001, "finite binary32"),
        (binary32_exp_rne, True, "32-bit binary32"),
        (binary32_exp_rne, [], "32-bit binary32"),
        (binary32_sigmoid_rne, 0xFF800000, "finite binary32"),
        (binary32_sigmoid_rne, -1, "32-bit binary32"),
        (binary32_sigmoid_rne, 0.0, "32-bit binary32"),
    ],
)
def test_transcendentals_reject_out_of_profile_or_nonfinite_values(
    function, code: object, match: str
) -> None:
    with pytest.raises(HCPreReferenceError, match=match):
        function(code)  # type: ignore[arg-type]


def test_all_zero_hc_pre_known_answer_and_exact_counters() -> None:
    result = hc_pre_bf16(
        (ZERO_TOKEN,),
        ZERO_PROJECTION,
        ZERO_SCALE,
        ZERO_BASE,
    )

    assert result.diagnostics.mean_square_codes == (0x00000000,)
    assert result.diagnostics.inverse_rms_codes == (0x447A0000,)
    assert result.diagnostics.projection_codes == ((0,) * 24,)
    assert result.diagnostics.normalized_projection_codes == ((0,) * 24,)
    assert result.pre_binary32_codes == ((0x3F000011,) * 4,)
    assert result.post_binary32_codes == ((0x3F800000,) * 4,)
    assert result.diagnostics.split.softmax_codes == (((0x3E800022,) * 4,) * 4,)
    assert result.comb_binary32_codes == (((0x3E7FFFF0,) * 4,) * 4,)
    assert result.branch_bf16_codes == ((0,) * HIDDEN_SIZE,)
    assert result.residual_bf16_codes == (ZERO_TOKEN,)
    assert result.branch_output_saturation_count == 0

    assert asdict(result.counters) == {
        "hc_pre_token_count": 1,
        "hc_pre_input_bf16_values": 16_384,
        "hc_pre_rms_square_multiplies": 16_384,
        "hc_pre_rms_reduction_adds": 16_383,
        "hc_pre_rms_divides": 1,
        "hc_pre_rms_epsilon_adds": 1,
        "hc_pre_rsqrt_evaluations": 1,
        "hc_pre_projection_product_accumulates": 393_216,
        "hc_pre_projection_rms_multiplies": 24,
        "hc_pre_field_affine_multiplies": 24,
        "hc_pre_field_affine_adds": 24,
        "hc_pre_sigmoid_evaluations": 8,
        "hc_pre_coefficient_epsilon_adds": 4,
        "hc_pre_post_factor_multiplies": 4,
        "hc_pre_softmax_max_comparisons": 12,
        "hc_pre_softmax_subtracts": 16,
        "hc_pre_exp_evaluations": 16,
        "hc_pre_sinkhorn_row_stages": 20,
        "hc_pre_sinkhorn_column_stages": 20,
        "hc_pre_sinkhorn_row_reduction_adds": 240,
        "hc_pre_sinkhorn_column_reduction_adds": 240,
        "hc_pre_sinkhorn_divides": 640,
        "hc_pre_sinkhorn_epsilon_adds": 172,
        "hc_pre_branch_coefficient_multiplies": 16_384,
        "hc_pre_branch_reduction_adds": 12_288,
        "hc_pre_branch_bf16_conversions": 4_096,
        "hc_pre_branch_bf16_saturations": 0,
        "hc_pre_residual_bf16_values_preserved": 16_384,
    }


def test_signed_zero_residual_is_preserved_but_arithmetic_zero_is_positive() -> None:
    negative_zero_stream = (0x8000,) * HIDDEN_SIZE
    token = (negative_zero_stream,) * HC_MULTIPLIER
    result = hc_pre_bf16((token,), ZERO_PROJECTION, ZERO_SCALE, ZERO_BASE)
    assert result.residual_bf16_codes == (token,)
    assert result.diagnostics.mean_square_codes == (0,)
    assert result.diagnostics.projection_codes == ((0,) * MIX_PARAMETER_COUNT,)
    assert result.branch_bf16_codes == ((0,) * HIDDEN_SIZE,)


def test_bf16_subnormals_survive_branch_arithmetic_when_result_is_representable() -> (
    None
):
    minimum_subnormal_stream = (0x0001,) + (0,) * (HIDDEN_SIZE - 1)
    token = (
        minimum_subnormal_stream,
        minimum_subnormal_stream,
        ZERO_STREAM,
        ZERO_STREAM,
    )
    result = hc_pre_bf16((token,), ZERO_PROJECTION, ZERO_SCALE, ZERO_BASE)
    # Each product rounds to the exact BF16 half-ULP as a binary32 subnormal;
    # the balanced pair sum is one minimum BF16 subnormal.
    assert result.branch_bf16_codes[0][0] == 0x0001
    assert result.branch_bf16_codes[0][1:] == (0,) * (HIDDEN_SIZE - 1)
    assert result.residual_bf16_codes == (token,)


@pytest.mark.parametrize("token_count", [1, 2, 3, 4])
def test_hc_pre_accepts_every_qualified_token_extent(token_count: int) -> None:
    result = hc_pre_bf16(
        (ZERO_TOKEN,) * token_count,
        ZERO_PROJECTION,
        ZERO_SCALE,
        ZERO_BASE,
    )
    assert len(result.branch_bf16_codes) == token_count
    assert all(len(row) == HIDDEN_SIZE for row in result.branch_bf16_codes)
    assert len(result.pre_binary32_codes) == token_count
    assert len(result.comb_binary32_codes) == token_count
    assert len(result.residual_bf16_codes) == token_count
    counters = asdict(result.counters)
    assert counters["hc_pre_token_count"] == token_count
    assert counters["hc_pre_input_bf16_values"] == 16_384 * token_count
    assert counters["hc_pre_projection_product_accumulates"] == (393_216 * token_count)
    assert counters["hc_pre_sinkhorn_divides"] == 640 * token_count
    assert counters["hc_pre_branch_bf16_conversions"] == 4_096 * token_count


def test_projection_uses_increasing_k_exact_product_rounding() -> None:
    # 1 + 2^-24 is a midpoint that ties back to even 1.0 before -1 arrives.
    token = _token_with_flat_prefix((0x3F80, 0x3980, 0xBF80))
    projection = _projection_with_first_row_prefix(
        (_f32(1), _f32(Fraction(1, 1 << 12)), _f32(1))
    )
    result = hc_pre_bf16((token,), projection, ZERO_SCALE, ZERO_BASE)
    assert result.diagnostics.projection_codes[0][0] == 0x00000000
    assert result.diagnostics.projection_codes[0][1:] == (0,) * 23
    assert _f32(Fraction(1, 1 << 24)) == 0x33800000


def test_width_16384_rms_uses_balanced_tree_not_a_left_fold() -> None:
    values = (0xB8C2, 0x29E0, 0xBA4A, 0x3ECD)
    result = hc_pre_bf16(
        (_token_with_flat_prefix(values),),
        ZERO_PROJECTION,
        ZERO_SCALE,
        ZERO_BASE,
    )
    assert result.diagnostics.mean_square_codes == (0x37242929,)

    squares = tuple(binary32_multiply(code << 16, code << 16) for code in values)
    linear = squares[0]
    for square in squares[1:]:
        linear = binary32_add(linear, square)
    assert binary32_divide(linear, _f32(FLATTENED_WIDTH)) == 0x37242928
    assert binary32_balanced_sum(squares) == 0x3E242929


def test_branch_reduction_uses_balanced_four_stream_association() -> None:
    stream_values = (0xC863, 0xCB8A, 0xD1C0, 0x5508)
    token = tuple(((value,) + (0,) * (HIDDEN_SIZE - 1)) for value in stream_values)
    result = hc_pre_bf16(
        (token,),
        ZERO_PROJECTION,
        ZERO_SCALE,
        ZERO_BASE,
    )
    assert result.branch_bf16_codes[0][0] == 0x5487

    pre = 0x3F000011
    products = tuple(binary32_multiply(pre, value << 16) for value in stream_values)
    linear = products[0]
    for product in products[1:]:
        linear = binary32_add(linear, product)
    assert binary32_bits_to_bf16_rne(linear).code == 0x5486
    assert binary32_bits_to_bf16_rne(binary32_balanced_sum(products)).code == 0x5487


def test_asymmetric_sinkhorn_sentinel_fixes_pass_count_and_orientation() -> None:
    asymmetric = (
        -3,
        1,
        2,
        -1,
        4,
        -2,
        Fraction(1, 2),
        3,
        Fraction(-1, 2),
        5,
        -4,
        2,
        1,
        -3,
        Fraction(3, 2),
        0,
    )
    base = (0,) * 8 + tuple(_f32(value) for value in asymmetric)
    result = hc_split_sinkhorn_binary32(
        ((0,) * MIX_PARAMETER_COUNT,),
        ZERO_SCALE,
        base,
    )
    stages = result.diagnostics.sinkhorn_stage_codes
    assert len(stages) == SINKHORN_ITERATIONS
    assert all(len(stage) == 1 for stage in stages)
    assert stages[18][0][0] == (
        0x3C157563,
        0x3E48BC3A,
        0x3F2AEF00,
        0x3E022E87,
    )
    assert stages[19][0][0] == (
        0x3C157693,
        0x3E48BAB1,
        0x3F2AEF65,
        0x3E022F04,
    )
    assert stages[18] != stages[19]
    assert result.comb_binary32_codes[0] == stages[19][0]
    assert tuple(stage[0] for stage in stages) == _independent_sinkhorn_stages(
        result.diagnostics.softmax_codes[0]
    )
    # [source][destination] orientation is deliberately asymmetric.
    assert result.comb_binary32_codes[0][0][1] == 0x3E48BAB1
    assert result.comb_binary32_codes[0][1][0] == 0x3F15B95E

    # The fourth initial exponential row is an association sentinel: the
    # required pair tree differs by one binary32 code from a left fold.
    affine_row = result.diagnostics.comb_affine_codes[0][3]
    maximum = affine_row[2]
    exponentials = tuple(
        binary32_exp_rne(binary32_add(code, maximum ^ 0x80000000))
        for code in affine_row
    )
    balanced = binary32_balanced_sum(exponentials)
    left_fold = exponentials[0]
    for code in exponentials[1:]:
        left_fold = binary32_add(left_fold, code)
    assert balanced == 0x3FEB9E59
    assert left_fold == 0x3FEB9E58

    mutated = list(base)
    mutated[8], mutated[9] = mutated[9], mutated[8]
    changed = hc_split_sinkhorn_binary32(
        ((0,) * MIX_PARAMETER_COUNT,),
        ZERO_SCALE,
        tuple(mutated),
    )
    assert changed.comb_binary32_codes != result.comb_binary32_codes


@pytest.mark.parametrize(
    ("inputs", "projection", "scale", "base", "kwargs", "match"),
    [
        ((), ZERO_PROJECTION, ZERO_SCALE, ZERO_BASE, {}, "token dimension"),
        (
            (ZERO_TOKEN,) * 5,
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {},
            "token dimension",
        ),
        (
            ((ZERO_STREAM,) * 3,),
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {},
            "exactly 4 HC streams",
        ),
        (
            (((0,) * (HIDDEN_SIZE - 1),) + (ZERO_STREAM,) * 3,),
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {},
            "exactly 4096 values",
        ),
        (
            (((0x7F80,) + (0,) * (HIDDEN_SIZE - 1),) + (ZERO_STREAM,) * 3,),
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {},
            "finite BF16",
        ),
        (
            (ZERO_TOKEN,),
            ZERO_PROJECTION[:-1],
            ZERO_SCALE,
            ZERO_BASE,
            {},
            "exactly 24 rows",
        ),
        (
            (ZERO_TOKEN,),
            ZERO_PROJECTION,
            (0x7F800000, 0, 0),
            ZERO_BASE,
            {},
            "finite binary32",
        ),
        (
            (ZERO_TOKEN,),
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {"normalization_epsilon_binary32": 0x358637BC},
            "must equal",
        ),
        (
            (ZERO_TOKEN,),
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {"sinkhorn_epsilon_binary32": 0x358637BC},
            "must equal",
        ),
        (
            (ZERO_TOKEN,),
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {"sinkhorn_iterations": 21},
            "must equal 20",
        ),
        (
            (ZERO_TOKEN,),
            ZERO_PROJECTION,
            ZERO_SCALE,
            ZERO_BASE,
            {"sinkhorn_iterations": 20.0},
            "must equal 20",
        ),
    ],
)
def test_hc_pre_rejects_malformed_nonfinite_or_profile_drift(
    inputs, projection, scale, base, kwargs: dict[str, int], match: str
) -> None:
    with pytest.raises(HCPreReferenceError, match=match):
        hc_pre_bf16(inputs, projection, scale, base, **kwargs)


def test_arithmetic_poison_is_atomic_and_does_not_mutate_input() -> None:
    mutable_input = [
        [list((0x3F80, 0x3F80) + (0,) * (HIDDEN_SIZE - 2))]
        + [list(ZERO_STREAM) for _ in range(3)]
    ]
    before = deepcopy(mutable_input)
    overflow_row = (0x7F7FFFFF, 0x7F7FFFFF) + (0,) * (FLATTENED_WIDTH - 2)
    projection = (overflow_row,) + (ZERO_PROJECTION_ROW,) * 23

    with pytest.raises(HCPreReferenceError, match="normalization/projection"):
        hc_pre_bf16(mutable_input, projection, ZERO_SCALE, ZERO_BASE)
    assert mutable_input == before


def test_rms_square_overflow_poisons_complete_transaction() -> None:
    extreme_stream = (0x7F7F,) + (0,) * (HIDDEN_SIZE - 1)
    token = (extreme_stream,) + (ZERO_STREAM,) * 3
    with pytest.raises(HCPreReferenceError, match="normalization/projection"):
        hc_pre_bf16((token,), ZERO_PROJECTION, ZERO_SCALE, ZERO_BASE)


def test_late_parameter_poison_does_not_expose_partial_result() -> None:
    bad_last_row = ZERO_PROJECTION_ROW[:-1] + (0x7FC00000,)
    projection = ZERO_PROJECTION[:-1] + (bad_last_row,)
    mutable_input = [[list(stream) for stream in ZERO_TOKEN]]
    before = deepcopy(mutable_input)

    with pytest.raises(HCPreReferenceError, match="finite binary32"):
        hc_pre_bf16(mutable_input, projection, ZERO_SCALE, ZERO_BASE)
    assert mutable_input == before
