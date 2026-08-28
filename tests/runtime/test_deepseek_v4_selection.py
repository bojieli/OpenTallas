from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.selection import (
    INT64_MAX,
    MODEL_SOURCE_SHA256,
    NEGATIVE_INFINITY_BF16,
    NEGATIVE_INFINITY_BINARY32,
    REQUIREMENTS_SOURCE_SHA256,
    TIE_POLICY,
    SelectionReferenceError,
    biased_topk_route_indices,
    index_topk_indices,
    stable_topk_bf16,
    stable_topk_binary32,
)


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(_f32(value)).code


def test_selection_reference_pins_source_and_declares_tie_policy() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert REQUIREMENTS_SOURCE_SHA256 == (
        "857e0b8b58e41cabe16e55bf4ab7ff791677c53b25f0f3e104ef85227cd11eab"
    )
    assert TIE_POLICY == "score_descending_then_logical_index_ascending"


def test_stable_topk_orders_values_infinities_and_exact_ties() -> None:
    scores = (
        _f32(3),
        _f32(5),
        _f32(5),
        0x7F800000,
        NEGATIVE_INFINITY_BINARY32,
        0x80000000,
        0,
    )
    assert stable_topk_binary32(scores, len(scores)) == (3, 1, 2, 0, 5, 6, 4)
    assert stable_topk_binary32(scores, 3) == (3, 1, 2)
    assert stable_topk_binary32((), 0) == ()


def test_stable_bf16_topk_orders_values_infinities_and_exact_ties() -> None:
    scores = (
        _bf16(3),
        _bf16(5),
        _bf16(5),
        0x7F80,
        NEGATIVE_INFINITY_BF16,
        0x8000,
        0,
    )
    assert stable_topk_bf16(scores, len(scores)) == (3, 1, 2, 0, 5, 6, 4)


def test_stable_topk_matches_independent_exact_integer_order_randomly() -> None:
    rng = random.Random(0x70C)
    for _ in range(2_000):
        count = rng.randint(1, 64)
        values = [rng.randint(-100_000, 100_000) for _ in range(count)]
        codes = tuple(_f32(value) for value in values)
        k = rng.randint(0, count)
        expected = tuple(
            sorted(range(count), key=lambda index: (-values[index], index))[:k]
        )
        assert stable_topk_binary32(codes, k) == expected


def test_biased_router_uses_selection_bias_and_stable_ties_only() -> None:
    scores = (
        tuple(_f32(value) for value in (1, 4, 3, 2)),
        tuple(_f32(value) for value in (9, 0, 1, 8)),
    )
    bias = tuple(_f32(value) for value in (5, 0, 1, 2))
    # Row zero becomes (6,4,4,4), so tied indices are 1 then 2. Row one
    # becomes (14,0,2,10).
    assert biased_topk_route_indices(scores, bias, top_k=3) == (
        (0, 1, 2),
        (0, 3, 2),
    )


def test_router_bias_add_rounds_once_to_binary32_before_selection() -> None:
    one = _f32(1)
    half_ulp = _f32(Fraction(1, 1 << 24))
    one_ulp = _f32(Fraction(1, 1 << 23))
    scores = ((one, one),)
    # 1 + half-ULP ties back to even 1.0, while 1 + one ULP advances.
    assert biased_topk_route_indices(
        scores, (half_ulp, one_ulp), top_k=2
    ) == ((1, 0),)


def test_index_topk_prefill_masks_incomplete_groups_before_selection() -> None:
    rows = []
    for query in range(10):
        # The incomplete group deliberately has the larger score. It must never
        # beat a complete group; once both groups are complete, index 1 wins.
        rows.append((_bf16(query), _bf16(100 + query)))
    observed = index_topk_indices(
        (tuple(rows),),
        top_k=2,
        compression_ratio=4,
        start_position=0,
        offset=128,
    )
    assert observed == (
        (
            (-1, -1),
            (-1, -1),
            (-1, -1),
            (128, -1),
            (128, -1),
            (128, -1),
            (128, -1),
            (129, 128),
            (129, 128),
            (129, 128),
        ),
    )


def test_index_topk_decode_selects_all_cached_candidates_and_offsets() -> None:
    assert index_topk_indices(
        (((_bf16(3), _bf16(7)),),),
        top_k=512,
        compression_ratio=4,
        start_position=7,
        offset=128,
    ) == (((129, 128),),)


def test_index_topk_handles_zero_complete_candidates() -> None:
    assert index_topk_indices(
        (((), (), ()),),
        top_k=512,
        compression_ratio=4,
        start_position=0,
        offset=128,
    ) == (((), (), ()),)


@pytest.mark.parametrize("nan_code", [0x7FC00000, 0xFFC00001])
def test_binary32_topk_rejects_nan(nan_code: int) -> None:
    with pytest.raises(SelectionReferenceError, match="NaN"):
        stable_topk_binary32((_f32(1), nan_code), 1)


@pytest.mark.parametrize("nan_code", [0x7F81, 0xFFFF])
def test_bf16_topk_rejects_nan(nan_code: int) -> None:
    with pytest.raises(SelectionReferenceError, match="NaN"):
        stable_topk_bf16((_bf16(1), nan_code), 1)


@pytest.mark.parametrize(
    ("scores", "k", "match"),
    [
        ((_f32(1),), -1, "k"),
        ((_f32(1),), 2, "exceeds"),
        ((True,), 1, "binary32"),
        ((1 << 32,), 1, "binary32"),
    ],
)
def test_invalid_stable_topk_fails_closed(scores, k: int, match: str) -> None:
    with pytest.raises(SelectionReferenceError, match=match):
        stable_topk_binary32(scores, k)


@pytest.mark.parametrize(
    ("scores", "k", "match"),
    [
        ((_bf16(1),), -1, "k"),
        ((_bf16(1),), 2, "exceeds"),
        ((True,), 1, "BF16"),
        ((1 << 16,), 1, "BF16"),
    ],
)
def test_invalid_stable_bf16_topk_fails_closed(scores, k: int, match: str) -> None:
    with pytest.raises(SelectionReferenceError, match=match):
        stable_topk_bf16(scores, k)


def test_invalid_router_requests_fail_closed() -> None:
    with pytest.raises(SelectionReferenceError, match="at least one token"):
        biased_topk_route_indices((), (_f32(0),), top_k=1)
    with pytest.raises(SelectionReferenceError, match="at least one expert"):
        biased_topk_route_indices(((),), (), top_k=1)
    with pytest.raises(SelectionReferenceError, match="match"):
        biased_topk_route_indices(
            ((_f32(1),),), (_f32(0), _f32(0)), top_k=1
        )
    with pytest.raises(SelectionReferenceError, match="finite"):
        biased_topk_route_indices(
            ((0x7F800000,),), (_f32(0),), top_k=1
        )


def test_invalid_index_requests_fail_closed() -> None:
    with pytest.raises(SelectionReferenceError, match="at least one batch"):
        index_topk_indices(
            (), top_k=1, compression_ratio=4, start_position=0, offset=0
        )
    with pytest.raises(SelectionReferenceError, match="rectangular"):
        index_topk_indices(
            (((_bf16(1),), (_bf16(1), _bf16(2))),),
            top_k=1,
            compression_ratio=1,
            start_position=0,
            offset=0,
        )
    with pytest.raises(SelectionReferenceError, match="expected"):
        index_topk_indices(
            (((_bf16(1),),),),
            top_k=1,
            compression_ratio=4,
            start_position=0,
            offset=0,
        )
    with pytest.raises(SelectionReferenceError, match="finite BF16"):
        index_topk_indices(
            (((0x7F80,),),),
            top_k=1,
            compression_ratio=1,
            start_position=0,
            offset=0,
        )
    with pytest.raises(SelectionReferenceError, match="signed int64"):
        index_topk_indices(
            (((_bf16(1),),),),
            top_k=1,
            compression_ratio=1,
            start_position=0,
            offset=INT64_MAX + 1,
        )
