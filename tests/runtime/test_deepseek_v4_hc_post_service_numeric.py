from __future__ import annotations

import inspect
import random
import struct
from collections.abc import Sequence
from dataclasses import FrozenInstanceError

import pytest

from runtime.reference.formats import (
    binary32_add as _oracle_binary32_add,
    binary32_balanced_sum as _oracle_binary32_balanced_sum,
    binary32_multiply as _oracle_binary32_multiply,
)
from runtime.reference.vector import hc_post_bf16 as _reference_hc_post_bf16
from runtime.service_engine import hc_post_numeric
from runtime.service_engine.hc_post_numeric import (
    HC_POST_MAX_TOKENS_PER_COMMAND,
    HC_POST_PINNED_HC_MULTIPLIER,
    HC_POST_PINNED_HIDDEN_WIDTH,
    HCPostServiceNumericError,
    HCPostServiceResult,
    execute_hc_post,
    execute_pinned_hc_post,
    rn32_add,
    rn32_balanced_sum,
    rn32_multiply,
)


def _f32(value: int | float) -> int:
    return struct.unpack(">I", struct.pack(">f", value))[0]


def _bf16(value: int | float) -> int:
    return _f32(value) >> 16


def _binary32_to_bf16_oracle(code: int) -> tuple[int, bool]:
    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    saturated = upper & 0x7F80 == 0x7F80
    if saturated:
        upper = (upper & 0x8000) | 0x7F7F
    if upper & 0x7FFF == 0:
        upper = 0
    return upper, saturated


def _inputs(
    *,
    batch: int = 1,
    sequence: int = 1,
    hc_multiplier: int = 4,
    width: int = 1,
) -> tuple[object, object, object, object]:
    branch = tuple(
        tuple(tuple(_bf16(1) for _ in range(width)) for _ in range(sequence))
        for _ in range(batch)
    )
    residual = tuple(
        tuple(
            tuple(
                tuple(_bf16(source + 1) for _ in range(width))
                for source in range(hc_multiplier)
            )
            for _ in range(sequence)
        )
        for _ in range(batch)
    )
    post = tuple(
        tuple(tuple(_f32(1) for _ in range(hc_multiplier)) for _ in range(sequence))
        for _ in range(batch)
    )
    combination = tuple(
        tuple(
            tuple(
                tuple(
                    _f32(1) if source == destination else 0
                    for destination in range(hc_multiplier)
                )
                for source in range(hc_multiplier)
            )
            for _ in range(sequence)
        )
        for _ in range(batch)
    )
    return branch, residual, post, combination


def _replace_nested(value: object, path: Sequence[int], replacement: object) -> object:
    if not path:
        return replacement
    output = list(value)  # type: ignore[arg-type]
    output[path[0]] = _replace_nested(output[path[0]], path[1:], replacement)
    return tuple(output)


def _widen_bf16(code: int) -> int:
    return 0 if code & 0x7FFF == 0 else code << 16


def _assert_all_intermediates_match_independent_oracle(
    service: HCPostServiceResult,
    branch: tuple,
    residual: tuple,
    post: tuple,
    combination: tuple,
    *,
    hc_multiplier: int,
) -> None:
    expected_branch_products = []
    expected_residual_products = []
    expected_residual_sums = []
    expected_outputs_binary32 = []
    for batch_index, batch in enumerate(branch):
        branch_product_sequence = []
        residual_product_sequence = []
        residual_sum_sequence = []
        output_binary32_sequence = []
        for position, vector in enumerate(batch):
            branch_product_destinations = []
            residual_products_by_source = [
                [[] for _ in range(hc_multiplier)] for _ in range(hc_multiplier)
            ]
            residual_sum_destinations = []
            output_binary32_destinations = []
            for destination in range(hc_multiplier):
                branch_product_vector = []
                residual_sum_vector = []
                output_binary32_vector = []
                for column, branch_code in enumerate(vector):
                    branch_product = _oracle_binary32_multiply(
                        post[batch_index][position][destination],
                        _widen_bf16(branch_code),
                    )
                    residual_products = tuple(
                        _oracle_binary32_multiply(
                            combination[batch_index][position][source][destination],
                            _widen_bf16(
                                residual[batch_index][position][source][column]
                            ),
                        )
                        for source in range(hc_multiplier)
                    )
                    residual_sum = _oracle_binary32_balanced_sum(residual_products)
                    output_binary32 = _oracle_binary32_add(
                        branch_product,
                        residual_sum,
                    )
                    branch_product_vector.append(branch_product)
                    residual_sum_vector.append(residual_sum)
                    output_binary32_vector.append(output_binary32)
                    for source, product in enumerate(residual_products):
                        residual_products_by_source[source][destination].append(product)
                branch_product_destinations.append(tuple(branch_product_vector))
                residual_sum_destinations.append(tuple(residual_sum_vector))
                output_binary32_destinations.append(tuple(output_binary32_vector))
            branch_product_sequence.append(tuple(branch_product_destinations))
            residual_product_sequence.append(
                tuple(
                    tuple(tuple(vector) for vector in source_destinations)
                    for source_destinations in residual_products_by_source
                )
            )
            residual_sum_sequence.append(tuple(residual_sum_destinations))
            output_binary32_sequence.append(tuple(output_binary32_destinations))
        expected_branch_products.append(tuple(branch_product_sequence))
        expected_residual_products.append(tuple(residual_product_sequence))
        expected_residual_sums.append(tuple(residual_sum_sequence))
        expected_outputs_binary32.append(tuple(output_binary32_sequence))

    assert service.branch_codes == branch
    assert service.residual_codes == residual
    assert service.branch_product_codes == tuple(expected_branch_products)
    assert service.residual_product_codes == tuple(expected_residual_products)
    assert service.residual_sum_codes == tuple(expected_residual_sums)
    assert service.output_binary32_codes == tuple(expected_outputs_binary32)


def test_hc_post_service_contract_is_pinned_and_reference_independent() -> None:
    assert HC_POST_PINNED_HC_MULTIPLIER == 4
    assert HC_POST_PINNED_HIDDEN_WIDTH == 4096
    assert HC_POST_MAX_TOKENS_PER_COMMAND == 4
    source = inspect.getsource(hc_post_numeric)
    assert "runtime.reference" not in source
    assert "hc_pre_numeric" not in source
    assert "numpy" not in source
    assert "import math" not in source


def test_pinned_h4_executes_but_reusable_primitive_preserves_num_6_7_surface() -> None:
    pinned = _inputs(hc_multiplier=HC_POST_PINNED_HC_MULTIPLIER, width=3)
    result = execute_hc_post(
        *pinned,
        hc_multiplier=HC_POST_PINNED_HC_MULTIPLIER,
    )
    assert len(result.output_codes[0][0]) == HC_POST_PINNED_HC_MULTIPLIER

    # NUM-6.7 itself permits small positive rectangular shapes for independent
    # checking. Deployment code, not this primitive, binds H=4 and D=4096.
    general = _inputs(batch=2, sequence=3, hc_multiplier=2, width=5)
    general_result = execute_hc_post(*general, hc_multiplier=2)
    assert len(general_result.output_codes) == 2
    assert len(general_result.output_codes[0]) == 3
    assert len(general_result.output_codes[0][0]) == 2
    assert len(general_result.output_codes[0][0][0]) == 5


def test_pinned_hc_post_profile_executes_only_bounded_h4_d4096_commands() -> None:
    zero_vector = (0,) * HC_POST_PINNED_HIDDEN_WIDTH
    branch = ((zero_vector,),)
    residual = (((zero_vector,) * HC_POST_PINNED_HC_MULTIPLIER,),)
    post = (((0,) * HC_POST_PINNED_HC_MULTIPLIER,),)
    combination = (
        (((0,) * HC_POST_PINNED_HC_MULTIPLIER,) * HC_POST_PINNED_HC_MULTIPLIER,),
    )
    result = execute_pinned_hc_post(branch, residual, post, combination)
    assert result.output_codes == ((((zero_vector,) * HC_POST_PINNED_HC_MULTIPLIER),),)

    with pytest.raises(HCPostServiceNumericError, match="pinned value 4096"):
        execute_pinned_hc_post(*_inputs(width=1))

    oversized_branch = ((zero_vector,) * (HC_POST_MAX_TOKENS_PER_COMMAND + 1),)
    with pytest.raises(HCPostServiceNumericError, match="token bound"):
        execute_pinned_hc_post(
            oversized_branch,
            residual,
            post,
            combination,
        )


def test_pinned_hc_post_profile_accepts_legal_maximum_token_extent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zero_vector = (0,) * HC_POST_PINNED_HIDDEN_WIDTH
    branch = ((zero_vector,) * HC_POST_MAX_TOKENS_PER_COMMAND,)
    marker = object()
    observed: list[tuple[object, object, object, object, int]] = []

    def fake_execute(
        raw_branch: object,
        raw_residual: object,
        raw_post: object,
        raw_combination: object,
        *,
        hc_multiplier: int,
    ) -> object:
        observed.append(
            (
                raw_branch,
                raw_residual,
                raw_post,
                raw_combination,
                hc_multiplier,
            )
        )
        return marker

    monkeypatch.setattr(hc_post_numeric, "execute_hc_post", fake_execute)
    result = execute_pinned_hc_post(  # type: ignore[arg-type]
        branch,
        (),
        (),
        (),
    )
    assert result is marker
    assert observed == [
        (
            branch,
            (),
            (),
            (),
            HC_POST_PINNED_HC_MULTIPLIER,
        )
    ]


def test_hc_post_source_destination_orientation_and_diagnostics() -> None:
    branch = (((_bf16(1), _bf16(2)),),)
    residual = (
        (
            (
                (_bf16(10), _bf16(20)),
                (_bf16(30), _bf16(40)),
                (_bf16(50), _bf16(60)),
                (_bf16(70), _bf16(80)),
            ),
        ),
    )
    post = (((_f32(1), _f32(2), _f32(3), _f32(4)),),)
    combination = (
        (
            (
                (_f32(1), _f32(2), 0, 0),
                (0, 0, _f32(3), 0),
                (_f32(4), 0, 0, 0),
                (0, 0, 0, _f32(5)),
            ),
        ),
    )

    result = execute_hc_post(
        branch,
        residual,
        post,
        combination,
        hc_multiplier=4,
    )

    assert isinstance(result, HCPostServiceResult)
    assert result.output_codes == (
        (
            (
                (_bf16(211), _bf16(262)),
                (_bf16(22), _bf16(44)),
                (_bf16(93), _bf16(126)),
                (_bf16(354), _bf16(408)),
            ),
        ),
    )
    assert result.branch_product_codes[0][0][2] == (_f32(3), _f32(6))
    assert result.residual_product_codes[0][0][2][0] == (
        _f32(200),
        _f32(240),
    )
    assert result.residual_sum_codes[0][0][0] == (_f32(210), _f32(260))
    assert result.output_binary32_codes[0][0][0] == (_f32(211), _f32(262))
    assert result.branch_codes == branch
    assert result.residual_codes == residual


def test_hc_post_balanced_source_tree_differs_after_bf16_conversion() -> None:
    branch = (((0x436A,),),)
    residual = ((((0x436A,), (0xBE04,), (0xBE5D,), (0xBFCC,)),),)
    post = (((0, 0xBF1002EA, 0, 0),),)
    comb_values = (0x3F1002E2, 0xBEB4BA08, 0xBF3689A2, 0x3E042C08)
    combination = (
        (
            (
                (0, comb_values[0], 0, 0),
                (0, comb_values[1], 0, 0),
                (0, comb_values[2], 0, 0),
                (0, comb_values[3], 0, 0),
            ),
        ),
    )

    result = execute_hc_post(
        branch,
        residual,
        post,
        combination,
        hc_multiplier=4,
    )
    assert result.output_codes[0][0][1][0] == 0xBBD2

    products = tuple(
        rn32_multiply(comb_values[source], residual[0][0][source][0] << 16)
        for source in range(4)
    )
    assert rn32_balanced_sum(products) == result.residual_sum_codes[0][0][1][0]
    sequential = 0
    for product in products:
        sequential = rn32_add(sequential, product)
    sequential_output = rn32_add(
        rn32_multiply(post[0][0][1], branch[0][0][0] << 16),
        sequential,
    )
    assert _binary32_to_bf16_oracle(sequential_output) == (0xBBD3, False)


def test_hc_post_adds_branch_only_after_the_residual_tree() -> None:
    branch_term = 0xC32DD060
    residual_terms = (0xC31BA2EC, 0x44F0A7A8, 0xC209FCB2, 0xC30D4AC8)
    branch = (((_bf16(1),),),)
    residual = ((((_bf16(1),),) * 4,),)
    post = (((branch_term, 0, 0, 0),),)
    combination = (
        (
            (
                (residual_terms[0], 0, 0, 0),
                (residual_terms[1], 0, 0, 0),
                (residual_terms[2], 0, 0, 0),
                (residual_terms[3], 0, 0, 0),
            ),
        ),
    )

    result = execute_hc_post(
        branch,
        residual,
        post,
        combination,
        hc_multiplier=4,
    )
    assert result.output_binary32_codes[0][0][0][0] == 0x44B18000
    assert result.output_codes[0][0][0][0] == 0x44B2

    # Treating the branch as a fifth tree leaf gives an adjacent binary32 code
    # that crosses the BF16 midpoint and therefore produces 0x44b1 instead.
    wrong_tree = rn32_balanced_sum((branch_term, *residual_terms))
    assert wrong_tree == 0x44B17FFF
    assert _binary32_to_bf16_oracle(wrong_tree) == (0x44B1, False)


def test_hc_post_preserves_signed_zero_and_subnormal_payloads() -> None:
    vector = (0x8000, 0x0001, 0x8001, 0)
    branch = ((vector,),)
    residual = (((vector, (0,) * 4, (0,) * 4, (0,) * 4),),)
    post = (((_f32(1), 0, 0x80000000, 0),),)
    combination = (
        (
            (
                (0, _f32(1), 0, 0),
                (0, 0, 0x80000000, 0),
                (0, 0, 0, 0),
                (0, 0, 0, 0),
            ),
        ),
    )

    result = execute_hc_post(
        branch,
        residual,
        post,
        combination,
        hc_multiplier=4,
    )

    expected = (0, 0x0001, 0x8001, 0)
    assert result.output_codes[0][0][0] == expected
    assert result.output_codes[0][0][1] == expected
    assert result.output_codes[0][0][2:] == ((0,) * 4, (0,) * 4)
    assert result.branch_codes == branch
    assert result.residual_codes == residual
    assert result.branch_product_codes[0][0][0][0] == 0
    assert result.residual_product_codes[0][0][0][1][0] == 0
    assert result.branch_product_codes[0][0][2] == (0,) * 4
    assert result.residual_product_codes[0][0][1][2] == (0,) * 4

    # Both formats' least subnormals multiply to a result far below binary32.
    underflow = execute_hc_post(
        (((0x0001,),),),
        (((((0,), (0,), (0,), (0,)),),)),
        (((0x00000001, 0, 0, 0),),),
        (((((0, 0, 0, 0),) * 4),),),
        hc_multiplier=4,
    )
    assert underflow.branch_product_codes[0][0][0][0] == 0
    assert underflow.output_codes[0][0][0][0] == 0

    # A degenerate one-leaf service reduction still consumes its input at a
    # checked arithmetic boundary, where NUM-6.7 canonicalizes signed zero.
    assert rn32_balanced_sum((0x80000000,)) == 0


def test_hc_post_saturates_only_at_final_bf16_conversion() -> None:
    result = execute_hc_post(
        (((0x7F7F,),),),
        (((((0,), (0,), (0,), (0,)),),)),
        (((0x3F808000, 0, 0, 0),),),
        (((((0, 0, 0, 0),) * 4),),),
        hc_multiplier=4,
    )

    assert result.output_codes[0][0][0][0] == 0x7F7F
    assert result.output_saturation_count == 1
    assert result.logical_counters["hc_post_output_bf16_saturations"] == 1


def test_hc_post_exact_semantic_counters_are_shape_derived_and_immutable() -> None:
    inputs = _inputs(batch=2, sequence=2, hc_multiplier=4, width=3)
    result = execute_hc_post(*inputs, hc_multiplier=4)

    assert dict(result.logical_counters) == {
        "hc_post_branch_bf16_values": 12,
        "hc_post_residual_bf16_values_preserved": 48,
        "hc_post_post_binary32_values": 16,
        "hc_post_comb_binary32_values": 64,
        "hc_post_branch_coefficient_multiplies": 48,
        "hc_post_residual_coefficient_multiplies": 192,
        "hc_post_residual_reduction_adds": 144,
        "hc_post_branch_residual_adds": 48,
        "hc_post_output_bf16_conversions": 48,
        "hc_post_output_bf16_saturations": 0,
    }
    assert result.semantic_counters is result.logical_counters
    with pytest.raises(TypeError):
        result.logical_counters["hc_post_output_bf16_conversions"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    ("hc_multiplier", "expected_adds_per_output"),
    [(3, 3), (5, 6)],
)
def test_hc_post_counters_include_padded_zero_tree_additions(
    hc_multiplier: int,
    expected_adds_per_output: int,
) -> None:
    result = execute_hc_post(
        *_inputs(hc_multiplier=hc_multiplier, width=2),
        hc_multiplier=hc_multiplier,
    )
    output_count = hc_multiplier * 2
    assert result.logical_counters["hc_post_residual_reduction_adds"] == (
        output_count * expected_adds_per_output
    )


def test_hc_post_matches_reference_only_as_a_test_oracle() -> None:
    generator = random.Random(0x4843504F53545356)
    for _ in range(120):
        batch = generator.randint(1, 2)
        sequence = generator.randint(1, 3)
        hc_multiplier = generator.randint(1, 6)
        width = generator.randint(1, 7)

        branch = tuple(
            tuple(
                tuple(
                    (generator.randrange(2) << 15)
                    | (generator.randrange(118, 136) << 7)
                    | generator.randrange(128)
                    for _ in range(width)
                )
                for _ in range(sequence)
            )
            for _ in range(batch)
        )
        residual = tuple(
            tuple(
                tuple(
                    tuple(
                        (generator.randrange(2) << 15)
                        | (generator.randrange(118, 136) << 7)
                        | generator.randrange(128)
                        for _ in range(width)
                    )
                    for _ in range(hc_multiplier)
                )
                for _ in range(sequence)
            )
            for _ in range(batch)
        )
        post = tuple(
            tuple(
                tuple(
                    (generator.randrange(2) << 31)
                    | (generator.randrange(118, 136) << 23)
                    | generator.randrange(1 << 23)
                    for _ in range(hc_multiplier)
                )
                for _ in range(sequence)
            )
            for _ in range(batch)
        )
        combination = tuple(
            tuple(
                tuple(
                    tuple(
                        (generator.randrange(2) << 31)
                        | (generator.randrange(118, 136) << 23)
                        | generator.randrange(1 << 23)
                        for _ in range(hc_multiplier)
                    )
                    for _ in range(hc_multiplier)
                )
                for _ in range(sequence)
            )
            for _ in range(batch)
        )

        service = execute_hc_post(
            branch,
            residual,
            post,
            combination,
            hc_multiplier=hc_multiplier,
        )
        reference = _reference_hc_post_bf16(
            branch,
            residual,
            post,
            combination,
            hc_multiplier=hc_multiplier,
        )
        assert service.output_codes == reference.output_codes
        assert service.output_saturation_count == reference.output_saturation_count
        _assert_all_intermediates_match_independent_oracle(
            service,
            branch,
            residual,
            post,
            combination,
            hc_multiplier=hc_multiplier,
        )


def test_hc_post_one_bit_coefficient_mutation_is_visible() -> None:
    branch, residual, post, combination = _inputs(width=2)
    baseline = execute_hc_post(
        branch,
        residual,
        post,
        combination,
        hc_multiplier=4,
    )
    # Flip exactly the low exponent bit of binary32 1.0, producing 0.5.
    mutated_post = _replace_nested(post, (0, 0, 0), _f32(1) ^ 0x00800000)
    mutated = execute_hc_post(
        branch,
        residual,
        mutated_post,  # type: ignore[arg-type]
        combination,
        hc_multiplier=4,
    )

    assert mutated_post[0][0][0] == _f32(0.5)  # type: ignore[index]
    assert baseline.branch_product_codes[0][0][0] == (_f32(1), _f32(1))
    assert mutated.branch_product_codes[0][0][0] == (_f32(0.5), _f32(0.5))
    assert baseline.output_codes[0][0][0] == (_bf16(2), _bf16(2))
    assert mutated.output_codes[0][0][0] == (_bf16(1.5), _bf16(1.5))


@pytest.mark.parametrize(
    ("operand", "path", "replacement", "match"),
    [
        ("branch", (0, 0, 0), 0x7F80, "finite BF16"),
        ("branch", (0, 0, 0), False, "16-bit"),
        ("residual", (0, 0, 3, 0), 0xFF80, "finite BF16"),
        ("post", (0, 0, 2), 0x7F800000, "finite binary32"),
        ("post", (0, 0, 2), 1 << 32, "32-bit"),
        ("combination", (0, 0, 3, 2), 0x7FC00000, "finite binary32"),
    ],
)
def test_hc_post_nonfinite_or_malformed_elements_poison_the_command(
    operand: str,
    path: tuple[int, ...],
    replacement: object,
    match: str,
) -> None:
    branch, residual, post, combination = _inputs(width=2)
    values = {
        "branch": branch,
        "residual": residual,
        "post": post,
        "combination": combination,
    }
    values[operand] = _replace_nested(values[operand], path, replacement)

    with pytest.raises(HCPostServiceNumericError, match=match):
        execute_hc_post(
            values["branch"],  # type: ignore[arg-type]
            values["residual"],  # type: ignore[arg-type]
            values["post"],  # type: ignore[arg-type]
            values["combination"],  # type: ignore[arg-type]
            hc_multiplier=4,
        )


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda values: ((), *values[1:]), "at least one batch"),
        (
            lambda values: (((),), *values[1:]),
            "at least one position",
        ),
        (
            lambda values: (_replace_nested(values[0], (0, 0), ()), *values[1:]),
            "at least one BF16",
        ),
        (
            lambda values: (
                values[0],
                _replace_nested(values[1], (0, 0), values[1][0][0][:3]),
                values[2],
                values[3],
            ),
            "source HC dimension",
        ),
        (
            lambda values: (
                values[0],
                _replace_nested(values[1], (0, 0, 0), (0,)),
                values[2],
                values[3],
            ),
            "hidden width",
        ),
        (
            lambda values: (
                values[0],
                values[1],
                _replace_nested(values[2], (0, 0), values[2][0][0][:3]),
                values[3],
            ),
            "destination HC dimension",
        ),
        (
            lambda values: (
                values[0],
                values[1],
                values[2],
                _replace_nested(values[3], (0, 0), values[3][0][0][:3]),
            ),
            "source HC dimension",
        ),
        (
            lambda values: (
                values[0],
                values[1],
                values[2],
                _replace_nested(values[3], (0, 0, 0), values[3][0][0][0][:3]),
            ),
            "destination HC dimension",
        ),
    ],
)
def test_hc_post_rejects_malformed_or_mismatched_shapes(
    mutator: object,
    match: str,
) -> None:
    values = _inputs(width=2)
    malformed = mutator(values)  # type: ignore[operator]
    with pytest.raises(HCPostServiceNumericError, match=match):
        execute_hc_post(*malformed, hc_multiplier=4)


@pytest.mark.parametrize("hc_multiplier", [0, -1, True, 1.0])
def test_hc_post_requires_an_explicit_positive_integer_hc_multiplier(
    hc_multiplier: object,
) -> None:
    with pytest.raises(HCPostServiceNumericError, match="integer >= 1"):
        execute_hc_post(
            *_inputs(),
            hc_multiplier=hc_multiplier,  # type: ignore[arg-type]
        )


def test_hc_post_rejects_hc_axis_mismatch_against_explicit_multiplier() -> None:
    h4 = _inputs(hc_multiplier=4)
    with pytest.raises(HCPostServiceNumericError, match="source HC dimension"):
        execute_hc_post(*h4, hc_multiplier=3)

    h3 = _inputs(hc_multiplier=3)
    with pytest.raises(HCPostServiceNumericError, match="source HC dimension"):
        execute_hc_post(*h3, hc_multiplier=4)


def test_hc_post_binary32_overflow_poison_is_atomic_across_later_rows() -> None:
    zero_residual = ((0,), (0,), (0,), (0,))
    branch = (((_bf16(1),), (0x7F7F,)),)
    residual = ((zero_residual, zero_residual),)
    post = (((_f32(1), 0, 0, 0), (_f32(2), 0, 0, 0)),)
    zero_matrix = ((0, 0, 0, 0),) * 4
    combination = ((zero_matrix, zero_matrix),)

    with pytest.raises(
        HCPostServiceNumericError,
        match=r"\[0\]\[1\]\[0\]\[0\].*arithmetic overflow",
    ):
        execute_hc_post(
            branch,
            residual,
            post,
            combination,
            hc_multiplier=4,
        )


def test_hc_post_poison_on_residual_tree_overflow_before_cancellation() -> None:
    result_shape = (((0,),),)
    residual = ((((0x7F7F,), (0x7F7F,), (0xFF7F,), (0xFF7F,)),),)
    post = (((0, 0, 0, 0),),)
    combination = (((((_f32(1), 0, 0, 0),) * 4),),)

    with pytest.raises(HCPostServiceNumericError, match="arithmetic overflow"):
        execute_hc_post(
            result_shape,
            residual,
            post,
            combination,
            hc_multiplier=4,
        )


def test_hc_post_snapshots_mutable_inputs_and_returns_immutable_diagnostics() -> None:
    branch = [[[_bf16(1)]]]
    residual = [[[[_bf16(2)], [_bf16(3)], [_bf16(4)], [_bf16(5)]]]]
    post = [[[_f32(1), _f32(1), _f32(1), _f32(1)]]]
    combination = [
        [
            [
                [_f32(1), 0, 0, 0],
                [0, _f32(1), 0, 0],
                [0, 0, _f32(1), 0],
                [0, 0, 0, _f32(1)],
            ]
        ]
    ]
    result = execute_hc_post(
        branch,
        residual,
        post,
        combination,
        hc_multiplier=4,
    )

    branch[0][0][0] = _bf16(100)
    residual[0][0][0][0] = _bf16(100)
    post[0][0][0] = _f32(100)
    combination[0][0][0][0] = _f32(100)

    assert result.branch_codes == (((_bf16(1),),),)
    assert result.residual_codes[0][0][0][0] == _bf16(2)
    assert result.output_codes[0][0] == (
        (_bf16(3),),
        (_bf16(4),),
        (_bf16(5),),
        (_bf16(6),),
    )
    with pytest.raises(TypeError):
        result.logical_counters["hc_post_branch_bf16_values"] = 99  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        result.output_codes = ()  # type: ignore[misc]
