from __future__ import annotations

import random

import pytest

from runtime.reference.formats import (
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
    decode_bf16,
    encode_binary32_rne,
)
from runtime.reference.hadamard import (
    FHT_DEVELOPMENT_REVISION,
    HADAMARD_SCALE_BINARY32,
    HADAMARD_STRIDES,
    HADAMARD_WIDTH,
    MODEL_SOURCE_SHA256,
    REQUIREMENTS_SOURCE_SHA256,
    HadamardReferenceError,
    hadamard_rotate_128_bf16,
)


def _negate(code: int) -> int:
    return 0 if code & 0x7FFFFFFF == 0 else code ^ 0x80000000


def _independent_recursive_transform(codes: tuple[int, ...]) -> tuple[int, ...]:
    if len(codes) == 1:
        return codes
    midpoint = len(codes) // 2
    lower = _independent_recursive_transform(codes[:midpoint])
    upper = _independent_recursive_transform(codes[midpoint:])
    sums = tuple(
        binary32_add(left, right)
        for left, right in zip(lower, upper, strict=True)
    )
    differences = tuple(
        binary32_add(left, _negate(right))
        for left, right in zip(lower, upper, strict=True)
    )
    return sums + differences


def _independent_row(row: tuple[int, ...]) -> tuple[int, ...]:
    widened = []
    for code in row:
        decoded = decode_bf16(code)
        assert decoded.finite and decoded.value is not None
        widened.append(encode_binary32_rne(decoded.value))
    transformed = _independent_recursive_transform(tuple(widened))
    return tuple(
        binary32_bits_to_bf16_rne(
            binary32_multiply(code, HADAMARD_SCALE_BINARY32)
        ).code
        for code in transformed
    )


def test_hadamard_source_dependency_and_profile_are_pinned() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert REQUIREMENTS_SOURCE_SHA256 == (
        "857e0b8b58e41cabe16e55bf4ab7ff791677c53b25f0f3e104ef85227cd11eab"
    )
    assert FHT_DEVELOPMENT_REVISION == "1cc807efbd6cc001df359822d60bf6052dd66859"
    assert HADAMARD_WIDTH == 128
    assert HADAMARD_STRIDES == (1, 2, 4, 8, 16, 32, 64)
    assert HADAMARD_SCALE_BINARY32 == 0x3DB504F3


def test_hadamard_known_answers_fix_orientation_scale_and_zero_sign() -> None:
    one_hot = (0x3F80,) + (0,) * 127
    ones = (0x3F80,) * 128
    alternating = tuple(0xBF80 if index & 1 else 0x3F80 for index in range(128))
    negative_zeros = (0x8000,) * 128

    result = hadamard_rotate_128_bf16(
        (one_hot, ones, alternating, negative_zeros)
    )

    assert result[0] == (0x3DB5,) * 128
    assert result[1] == (0x4135,) + (0,) * 127
    assert result[2] == (0, 0x4135) + (0,) * 126
    assert result[3] == (0,) * 128


def test_hadamard_matches_independent_recursive_randomized_composition() -> None:
    generator = random.Random(0x4453_5634_4841_4431)
    rows = tuple(
        tuple(
            (0x8000 if generator.getrandbits(1) else 0)
            | generator.randrange(0x2000, 0x6000)
            for _ in range(128)
        )
        for _ in range(24)
    )
    assert hadamard_rotate_128_bf16(rows) == tuple(
        _independent_row(row) for row in rows
    )


def test_hadamard_preserves_governed_subnormal_path() -> None:
    result = hadamard_rotate_128_bf16(((0x0001,) * 128,))
    assert result == ((0x000B,) + (0,) * 127,)


def test_hadamard_fails_closed_on_nonfinite_and_binary32_overflow() -> None:
    with pytest.raises(HadamardReferenceError, match="must be finite BF16"):
        hadamard_rotate_128_bf16(((0x7F80,) * 128,))
    with pytest.raises(HadamardReferenceError, match="must be finite BF16"):
        hadamard_rotate_128_bf16(((0x7FC0,) * 128,))
    with pytest.raises(HadamardReferenceError, match="binary32.*overflow"):
        hadamard_rotate_128_bf16(((0x7F7F,) * 128,))


@pytest.mark.parametrize(
    ("input_codes", "width", "match"),
    [
        ((), 128, "at least one row"),
        (((0,) * 127,), 128, "exactly 128"),
        (((0,) * 129,), 128, "exactly 128"),
        (((0,) * 128,), 64, "qualified value 128"),
        (((0,) * 128,), True, "qualified value 128"),
        (((False,) * 128,), 128, "16-bit BF16"),
        (((1 << 16,) * 128,), 128, "16-bit BF16"),
        (("not-a-row",), 128, "must be a sequence"),
    ],
)
def test_hadamard_rejects_malformed_requests(
    input_codes: object, width: object, match: str
) -> None:
    with pytest.raises(HadamardReferenceError, match=match):
        hadamard_rotate_128_bf16(input_codes, width=width)  # type: ignore[arg-type]
