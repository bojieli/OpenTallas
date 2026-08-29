from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.conversion import (
    BF16_BYTES,
    BINARY32_BYTES,
    BINARY32_TO_BF16_PROFILE,
    MODEL_SOURCE_SHA256,
    Binary32ToBF16Counters,
    Binary32ToBF16Result,
    ConversionReferenceError,
    binary32_tensor_to_bf16_rne,
)
from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
)


class _ListSubclass(list):
    pass


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def test_conversion_is_bound_to_num_4_2_and_compressor_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert BINARY32_TO_BF16_PROFILE == (
        "opentallas.binary32_tensor_to_bf16_rne_sat.v1"
    )
    assert BINARY32_BYTES == 4
    assert BF16_BYTES == 2


def test_conversion_preserves_shape_rounds_and_counts_traffic() -> None:
    value = (
        (
            (_f32(1), _f32(Fraction(257, 256)), _f32(-2)),
            (_f32(Fraction(1, 1 << 133)), 0x80000000, _f32(4)),
        ),
        (
            (_f32(8), _f32(-8), _f32(Fraction(3, 2))),
            (_f32(16), _f32(-16), _f32(Fraction(-3, 2))),
        ),
    )
    expected = tuple(
        tuple(
            tuple(binary32_bits_to_bf16_rne(code).code for code in row)
            for row in sequence
        )
        for sequence in value
    )
    assert binary32_tensor_to_bf16_rne(value) == Binary32ToBF16Result(
        bf16_codes=expected,
        counters=Binary32ToBF16Counters(
            batch_count=2,
            sequence_length=2,
            width=3,
            input_binary32_values=12,
            logical_input_read_bytes=48,
            output_bf16_values=12,
            logical_output_write_bytes=24,
            finite_saturation_count=0,
            transaction_commits=1,
        ),
    )
    assert expected[0][1][1] == 0


def test_conversion_reports_finite_bf16_saturation() -> None:
    result = binary32_tensor_to_bf16_rne((((0x7F7FFFFF, 0xFF7FFFFF),),))
    assert result.bf16_codes == (((0x7F7F, 0xFF7F),),)
    assert result.counters.finite_saturation_count == 2


def test_conversion_matches_scalar_reference_on_random_finite_codes() -> None:
    rng = random.Random(0x4233_3254_4F42_4631)

    def finite_code() -> int:
        while True:
            code = rng.getrandbits(32)
            if code & 0x7F800000 != 0x7F800000:
                return code

    for _ in range(200):
        batch_count = rng.randint(1, 3)
        sequence_length = rng.randint(1, 5)
        width = rng.randint(1, 12)
        value = tuple(
            tuple(
                tuple(finite_code() for _ in range(width))
                for _ in range(sequence_length)
            )
            for _ in range(batch_count)
        )
        result = binary32_tensor_to_bf16_rne(value)
        assert result.bf16_codes == tuple(
            tuple(
                tuple(binary32_bits_to_bf16_rne(code).code for code in row)
                for row in sequence
            )
            for sequence in value
        )


@pytest.mark.parametrize(
    ("value", "match"),
    [
        (object(), "exact list or tuple"),
        (_ListSubclass(), "exact list or tuple"),
        ((), "at least one batch"),
        (((),), "at least one row"),
        ((((),),), "at least one value"),
        ((((0,),), ((0,), (0,))), "rectangular on the sequence axis"),
        ((((0,), (0, 0)),), "rectangular on the value axis"),
        ((((True,),),), "32-bit binary32"),
        ((((-1,),),), "32-bit binary32"),
        ((((1 << 32,),),), "32-bit binary32"),
        ((((0x7F800000,),),), "finite binary32"),
        ((((0x7FC00000,),),), "finite binary32"),
    ],
)
def test_conversion_rejects_malformed_or_nonfinite_inputs(
    value: object,
    match: str,
) -> None:
    with pytest.raises(ConversionReferenceError, match=match):
        binary32_tensor_to_bf16_rne(value)
