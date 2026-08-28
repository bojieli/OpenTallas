from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import decode_binary32, encode_binary32_rne
from runtime.reference.routing import (
    MODEL_SOURCE_SHA256,
    RoutingReferenceError,
    normalize_routed_weight_codes,
)


ROUTE_SCALE = encode_binary32_rne(Fraction(3, 2))


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def test_routing_reference_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert ROUTE_SCALE == 0x3FC00000


def test_selected_unbiased_scores_are_normalized_then_scaled_in_slot_order() -> None:
    scores = (
        tuple(_f32(value) for value in (1, 2, 3, 4)),
        tuple(_f32(value) for value in (8, 4, 2, 1)),
    )
    assert normalize_routed_weight_codes(
        scores,
        ((3, 1), (0, 3)),
        route_scale_code=ROUTE_SCALE,
    ) == (
        (_f32(1), _f32(Fraction(1, 2))),
        (_f32(Fraction(4, 3)), _f32(Fraction(1, 6))),
    )


def test_duplicate_expert_ids_remain_source_slots_in_denominator_and_output() -> None:
    scores = (tuple(_f32(value) for value in (2, 5, 7)),)
    assert normalize_routed_weight_codes(
        scores,
        ((2, 2, 0),),
        route_scale_code=ROUTE_SCALE,
    ) == (
        (
            _f32(Fraction(21, 32)),
            _f32(Fraction(21, 32)),
            _f32(Fraction(3, 16)),
        ),
    )


def test_routed_weight_normalization_matches_independent_exact_small_integer_model() -> None:
    rng = random.Random(0xA017E)
    for _ in range(2_000):
        token_count = rng.randint(1, 6)
        expert_count = rng.randint(6, 64)
        selected_count = rng.randint(1, 6)
        integer_scores = tuple(
            tuple(rng.randint(1, 10_000) for _ in range(expert_count))
            for _ in range(token_count)
        )
        scores = tuple(
            tuple(_f32(value) for value in row) for row in integer_scores
        )
        indices = tuple(
            tuple(rng.randrange(expert_count) for _ in range(selected_count))
            for _ in range(token_count)
        )
        expected = []
        for score_row, index_row in zip(integer_scores, indices, strict=True):
            selected = tuple(score_row[index] for index in index_row)
            denominator = sum(selected)
            output_row = []
            for score in selected:
                quotient_code = _f32(Fraction(score, denominator))
                quotient = decode_binary32(quotient_code).value
                assert quotient is not None
                output_row.append(_f32(quotient * Fraction(3, 2)))
            expected.append(tuple(output_row))
        assert normalize_routed_weight_codes(
            scores,
            indices,
            route_scale_code=ROUTE_SCALE,
        ) == tuple(expected)


@pytest.mark.parametrize(
    ("scores", "indices", "scale", "match"),
    [
        ((), (), ROUTE_SCALE, "at least one token"),
        (((),), ((0,),), ROUTE_SCALE, "at least one expert"),
        (((_f32(1),), (_f32(1), _f32(2))), ((0,), (0,)), ROUTE_SCALE, "rectangular"),
        (((_f32(1),),), (), ROUTE_SCALE, "token count"),
        (((_f32(1),),), ((),), ROUTE_SCALE, "at least one expert"),
        (((_f32(1),),), ((1,),), ROUTE_SCALE, "must be in"),
        (((_f32(1),),), ((True,),), ROUTE_SCALE, "must be in"),
        (((_f32(-1),),), ((0,),), ROUTE_SCALE, "nonnegative"),
        (((0x7F800000,),), ((0,),), ROUTE_SCALE, "finite binary32"),
        (((_f32(0),),), ((0,),), ROUTE_SCALE, "sum is zero"),
        (((_f32(1),),), ((0,),), _f32(0), "greater than zero"),
        (((_f32(1),),), ((0,),), 0x7FC00000, "finite binary32"),
    ],
)
def test_invalid_routing_requests_fail_closed(
    scores, indices, scale: int, match: str
) -> None:
    with pytest.raises(RoutingReferenceError, match=match):
        normalize_routed_weight_codes(
            scores,
            indices,
            route_scale_code=scale,
        )
