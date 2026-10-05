from __future__ import annotations

import inspect
import random

import pytest

from runtime.service_engine import rms_numeric
from runtime.service_engine.rms_numeric import (
    RMS_NORM_EPSILON_BINARY32,
    RMS_NORM_WIDTHS,
    RMSServiceNumericError,
    RMSServiceResult,
    execute_weighted_rms_norm,
)


def test_service_rms_contract_is_pinned_and_reference_independent() -> None:
    assert RMS_NORM_EPSILON_BINARY32 == 0x358637BD
    assert RMS_NORM_WIDTHS == frozenset({128, 512, 1024, 4096})
    assert "runtime.reference" not in inspect.getsource(rms_numeric)


@pytest.mark.parametrize(
    ("width", "one_hot_mean", "one_hot_inverse", "one_hot_output"),
    [
        (128, 0x3C000000, 0x413501FC, 0x4135),
        (512, 0x3B000000, 0x41B4F917, 0x41B5),
        (1024, 0x3A800000, 0x41FFDE79, 0x4200),
        (4096, 0x39800000, 0x427F7A31, 0x427F),
    ],
)
def test_service_rms_known_answers_cover_every_qualified_width(
    width: int,
    one_hot_mean: int,
    one_hot_inverse: int,
    one_hot_output: int,
) -> None:
    weights = (0x3F80,) * width
    zeros = (0,) * width
    ones = (0x3F80,) * width
    one_hot = (0x3F80,) + (0,) * (width - 1)

    result = execute_weighted_rms_norm((zeros, ones, one_hot), weights)

    assert isinstance(result, RMSServiceResult)
    assert result.mean_square_codes == (0, 0x3F800000, one_hot_mean)
    assert result.inverse_rms_codes == (
        0x447A0000,
        0x3F7FFFF8,
        one_hot_inverse,
    )
    assert result.output_codes == (
        zeros,
        ones,
        (one_hot_output,) + (0,) * (width - 1),
    )
    assert result.output_saturation_count == 0


def test_service_rms_applies_nonuniform_signed_weights_after_normalization() -> None:
    width = 128
    row = tuple(0xBF80 if index & 1 else 0x3F80 for index in range(width))
    pattern = (0x3F80, 0x4000, 0x3F00, 0xBF80)
    weights = tuple(pattern[index % len(pattern)] for index in range(width))

    result = execute_weighted_rms_norm((row,), weights)

    assert result.mean_square_codes == (0x3F800000,)
    assert result.inverse_rms_codes == (0x3F7FFFF8,)
    assert result.output_codes == (
        tuple(
            code
            for _ in range(width // len(pattern))
            for code in (0x3F80, 0xC000, 0x3F00, 0x3F80)
        ),
    )


def test_service_rms_uses_the_num_6_1_balanced_square_reduction() -> None:
    generator = random.Random(2)
    row = tuple(
        (generator.randrange(105, 133) << 7) | generator.randrange(128)
        for _ in range(128)
    )

    result = execute_weighted_rms_norm((row,), (0x3F80,) * 128)

    # For this frozen vector the canonical square sum is 0x4630e32e; a
    # left-associated reduction produces adjacent code 0x4630e32d instead.
    assert result.mean_square_codes == (0x42B0E32E,)
    assert result.inverse_rms_codes == (0x3DD9C4EB,)
    assert result.output_codes[0][0] == 0x4072


def test_service_rms_does_not_fuse_the_two_output_multiplies() -> None:
    generator = random.Random(1915)
    row = tuple(
        (generator.randrange(110, 135) << 7)
        | generator.randrange(128)
        | (generator.randrange(2) << 15)
        for _ in range(128)
    )
    weights = tuple(
        (generator.randrange(110, 135) << 7)
        | generator.randrange(128)
        | (generator.randrange(2) << 15)
        for _ in range(128)
    )

    result = execute_weighted_rms_norm((row,), weights)

    assert result.mean_square_codes == (0x458035D4,)
    assert result.inverse_rms_codes == (0x3C7FCA3D,)
    # NUM-6.8's separately rounded input*inverse then *weight path gives AE13;
    # one exact fused three-factor product would round to adjacent BF16 AE14.
    assert result.output_codes[0][40] == 0xAE13


def test_service_rms_preserves_subnormals_and_canonicalizes_signed_zero() -> None:
    width = 128
    weights = (0x3F80,) * width

    result = execute_weighted_rms_norm(
        (
            (0x8000,) * width,
            (0x0001,) * width,
            (0x8001,) * width,
        ),
        weights,
    )

    assert result.mean_square_codes == (0, 0, 0)
    assert result.inverse_rms_codes == (0x447A0000,) * 3
    assert result.output_codes == (
        (0,) * width,
        (0x01FA,) * width,
        (0x81FA,) * width,
    )

    tiny_weights = tuple(0x8001 if index & 1 else 0x0001 for index in range(width))
    weighted = execute_weighted_rms_norm(((0x3F80,) * width,), tiny_weights)
    assert weighted.output_codes == (tiny_weights,)

    underflowed = execute_weighted_rms_norm(
        ((0x8001,) * width,),
        (0x0001,) * width,
    )
    assert underflowed.output_codes == ((0,) * width,)


def test_service_rms_counts_output_saturation_and_poisons_f32_overflow() -> None:
    width = 128
    saturating_row = (0x3F81,) + (0x3F80,) * (width - 1)
    saturating_weights = (0x7F7E,) + (0x3F80,) * (width - 1)

    result = execute_weighted_rms_norm((saturating_row,), saturating_weights)

    assert result.output_codes[0][0] == 0x7F7F
    assert result.output_saturation_count == 1

    with pytest.raises(RMSServiceNumericError, match="binary32 arithmetic overflow"):
        execute_weighted_rms_norm(
            ((0x7F7F,) * width,),
            (0x3F80,) * width,
        )
    with pytest.raises(RMSServiceNumericError, match="binary32 arithmetic overflow"):
        execute_weighted_rms_norm(
            (saturating_row,),
            (0x7F7F,) + (0x3F80,) * (width - 1),
        )


@pytest.mark.parametrize(
    ("inputs", "weights", "epsilon", "match"),
    [
        ((), (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "at least one row"),
        ("bad", (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "must be a sequence"),
        (
            (0,) * 128,
            (0x3F80,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "must be a sequence",
        ),
        (
            ((0,) * 127,),
            (0x3F80,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "exactly 128",
        ),
        (
            ((0,) * 129,),
            (0x3F80,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "exactly 128",
        ),
        (
            ((False,) * 128,),
            (0x3F80,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "16-bit BF16",
        ),
        (
            (((1 << 16),) * 128,),
            (0x3F80,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "16-bit BF16",
        ),
        (
            ((0x7F80,) * 128,),
            (0x3F80,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "finite BF16",
        ),
        (((0,) * 128,), (), RMS_NORM_EPSILON_BINARY32, "at least one value"),
        (
            ((0,) * 128,),
            (0x3F80,) * 127,
            RMS_NORM_EPSILON_BINARY32,
            "outside qualified widths",
        ),
        (
            ((0,) * 128,),
            (False,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "16-bit BF16",
        ),
        (
            ((0,) * 128,),
            (0x7FC0,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "finite BF16",
        ),
        (
            ((0,) * 128,),
            (0x3F80,) * 128,
            0x358637BC,
            "must equal",
        ),
        (((0,) * 128,), (0x3F80,) * 128, True, "must equal"),
        (((0,) * 128,), (0x3F80,) * 128, 1e-6, "must equal"),
    ],
)
def test_service_rms_rejects_malformed_or_nonfinite_requests(
    inputs: object,
    weights: object,
    epsilon: object,
    match: str,
) -> None:
    with pytest.raises(RMSServiceNumericError, match=match):
        execute_weighted_rms_norm(  # type: ignore[arg-type]
            inputs,
            weights,
            epsilon_binary32=epsilon,
        )


def test_service_rms_nonfinite_later_row_poisons_the_whole_call() -> None:
    width = 128
    with pytest.raises(RMSServiceNumericError, match=r"input_codes\[1\].*finite BF16"):
        execute_weighted_rms_norm(
            (
                (0x3F80,) * width,
                (0x3F80,) * (width - 1) + (0xFF80,),
            ),
            (0x3F80,) * width,
        )
