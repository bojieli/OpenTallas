from __future__ import annotations

import random

import pytest

from runtime.reference.structural import (
    BF16_MAX_ENCODING,
    MODEL_SOURCE_SHA256,
    StructuralReferenceError,
    dspark_noise_token_block,
    hc_expand_bf16,
)


def test_structural_reference_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )


def test_hc_expand_preserves_every_bf16_payload_bit() -> None:
    hidden = (
        (
            (0x0000, 0x8000, 0x0001, 0x7F80),
            (0xFF80, 0x7FC1, 0x3F80, BF16_MAX_ENCODING),
        ),
    )
    assert hc_expand_bf16(hidden, 3) == (
        (
            (hidden[0][0], hidden[0][0], hidden[0][0]),
            (hidden[0][1], hidden[0][1], hidden[0][1]),
        ),
    )


def test_hc_expand_matches_independent_repeat_construction_randomly() -> None:
    rng = random.Random(0x4C)
    for _ in range(500):
        batch = rng.randint(1, 4)
        sequence_length = rng.randint(1, 8)
        width = rng.randint(1, 16)
        multiplier = rng.randint(1, 8)
        hidden = tuple(
            tuple(
                tuple(rng.randrange(1 << 16) for _ in range(width))
                for _ in range(sequence_length)
            )
            for _ in range(batch)
        )
        expected = tuple(
            tuple(tuple(vector for _ in range(multiplier)) for vector in sequence)
            for sequence in hidden
        )
        assert hc_expand_bf16(hidden, multiplier) == expected


def test_dspark_noise_block_preserves_current_token_only_in_column_zero() -> None:
    assert dspark_noise_token_block(
        (0, 128_804, 42),
        block_size=5,
        noise_token_id=128_799,
        vocabulary_size=129_280,
    ) == (
        (0, 128_799, 128_799, 128_799, 128_799),
        (128_804, 128_799, 128_799, 128_799, 128_799),
        (42, 128_799, 128_799, 128_799, 128_799),
    )
    assert dspark_noise_token_block(
        (7,), block_size=1, noise_token_id=9, vocabulary_size=10
    ) == ((7,),)


@pytest.mark.parametrize(
    ("hidden", "multiplier", "match"),
    [
        ((), 1, "at least one batch"),
        (((),), 1, "at least one position"),
        ((((0,),), ((0,), (1,))), 1, "rectangular"),
        ((((),),), 1, "at least one BF16"),
        ((((0,), (0, 1)),), 1, "rectangular"),
        ((((True,),),), 1, "16-bit BF16"),
        ((((BF16_MAX_ENCODING + 1,),),), 1, "16-bit BF16"),
        ((((0,),),), 0, "hc_multiplier"),
    ],
)
def test_invalid_hc_expand_fails_closed(hidden, multiplier: int, match: str) -> None:
    with pytest.raises(StructuralReferenceError, match=match):
        hc_expand_bf16(hidden, multiplier)


@pytest.mark.parametrize(
    ("tokens", "block", "noise", "vocab", "match"),
    [
        ((), 5, 1, 2, "at least one"),
        ((0,), 0, 1, 2, "block_size"),
        ((0,), 5, 1, 0, "vocabulary_size"),
        ((0,), 5, 2, 2, "noise_token_id"),
        ((True,), 5, 1, 2, "current_token_ids"),
        ((2,), 5, 1, 2, "current_token_ids"),
    ],
)
def test_invalid_dspark_noise_block_fails_closed(
    tokens, block: int, noise: int, vocab: int, match: str
) -> None:
    with pytest.raises(StructuralReferenceError, match=match):
        dspark_noise_token_block(
            tokens,
            block_size=block,
            noise_token_id=noise,
            vocabulary_size=vocab,
        )
