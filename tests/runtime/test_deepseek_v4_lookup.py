from __future__ import annotations

import itertools

import pytest

from runtime.reference.lookup import (
    BF16_MAX_ENCODING,
    MODEL_SOURCE_SHA256,
    LookupReferenceError,
    bf16_token_embedding,
    hash_route_indices,
)


def test_lookup_reference_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )


def test_embedding_gathers_exact_bf16_encodings_without_conversion() -> None:
    weight = (
        (0x0000, 0x8000, 0x7FC1),
        (0x3F80, 0xBF80, 0x0001),
        (0x7F80, 0xFF80, 0x7F7F),
        (0x1234, 0xABCD, BF16_MAX_ENCODING),
    )
    assert bf16_token_embedding(((3, 0, 3), (1, 2, 0)), weight) == (
        (weight[3], weight[0], weight[3]),
        (weight[1], weight[2], weight[0]),
    )


def test_global_embedding_matches_vocab_shard_mask_and_combine() -> None:
    weight = tuple(
        tuple((row << 8) | column for column in range(4)) for row in range(12)
    )
    tokens = ((0, 3, 4, 7, 8, 11),)
    (observed,) = bf16_token_embedding(tokens, weight)

    # Independently express the official four-way ownership rule. Exactly one
    # shard contributes each selected row; all other partial embeddings are zero.
    combined = []
    for token_id in tokens[0]:
        contributions = []
        for shard in range(4):
            start = shard * 3
            end = start + 3
            contributions.append(weight[token_id] if start <= token_id < end else None)
        owned = tuple(value for value in contributions if value is not None)
        assert len(owned) == 1
        combined.append(owned[0])
    assert observed == tuple(combined)


def test_hash_route_is_plain_order_preserving_table_lookup() -> None:
    table = (
        (5, 1, 5),
        (0, 7, 2),
        (3, 4, 6),
        (7, 7, 7),
    )
    assert hash_route_indices((3, 0, 2, 0), table, expert_count=8) == (
        table[3],
        table[0],
        table[2],
        table[0],
    )


def test_lookup_properties_match_direct_indexing_exhaustively() -> None:
    for vocab_size, width in itertools.product(range(1, 9), range(1, 6)):
        weight = tuple(
            tuple(
                (row * width + column) & BF16_MAX_ENCODING
                for column in range(width)
            )
            for row in range(vocab_size)
        )
        ids = tuple(range(vocab_size - 1, -1, -1))
        assert bf16_token_embedding((ids,), weight) == (
            tuple(weight[token_id] for token_id in ids),
        )

        table = tuple(
            tuple((token_id + slot) % 11 for slot in range(3))
            for token_id in range(vocab_size)
        )
        assert hash_route_indices(ids, table, expert_count=11) == tuple(
            table[token_id] for token_id in ids
        )


@pytest.mark.parametrize(
    ("token_ids", "weight", "match"),
    [
        ((), ((0,),), "at least one batch"),
        (((),), ((0,),), "at least one token"),
        (((0,), (0, 1)), ((0,),), "rectangular"),
        (((True,),), ((0,),), "nonnegative integer"),
        (((1,),), ((0,),), "exceeds"),
        (((0,),), (), "at least one row"),
        (((0,),), ((),), "at least one BF16"),
        (((0,),), ((0,), (0, 1)), "rectangular"),
        (((0,),), ((BF16_MAX_ENCODING + 1,),), "exceeds"),
    ],
)
def test_invalid_embedding_requests_fail_closed(token_ids, weight, match: str) -> None:
    with pytest.raises(LookupReferenceError, match=match):
        bf16_token_embedding(token_ids, weight)


@pytest.mark.parametrize(
    ("token_ids", "table", "expert_count", "match"),
    [
        ((), ((0,),), 1, "at least one token"),
        ((0,), (), 1, "at least one row"),
        ((0,), ((),), 1, "at least one expert"),
        ((0,), ((0,), (0, 1)), 2, "rectangular"),
        ((True,), ((0,),), 1, "nonnegative integer"),
        ((1,), ((0,),), 1, "exceeds"),
        ((0,), ((1,),), 1, "exceeds"),
        ((0,), ((0,),), 0, "greater than zero"),
    ],
)
def test_invalid_hash_route_requests_fail_closed(
    token_ids, table, expert_count: int, match: str
) -> None:
    with pytest.raises(LookupReferenceError, match=match):
        hash_route_indices(token_ids, table, expert_count=expert_count)
