from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.vector import (
    BF16_MAX_ENCODING,
    MODEL_SOURCE_SHA256,
    VectorReferenceError,
    target_hidden_capture_bf16,
)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def test_target_hidden_capture_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )


def test_target_hidden_capture_means_hc_axis_and_preserves_tensor_order() -> None:
    hidden = (
        (
            (
                (_bf16(1), _bf16(-4), 0x8000),
                (_bf16(2), _bf16(2), 0x0000),
                (_bf16(3), _bf16(-2), 0x8000),
                (_bf16(4), _bf16(4), 0x0000),
            ),
            (
                (_bf16(8), _bf16(1), _bf16(5)),
                (_bf16(4), _bf16(1), _bf16(6)),
                (_bf16(2), _bf16(1), _bf16(7)),
                (_bf16(6), _bf16(1), _bf16(10)),
            ),
        ),
    )
    assert target_hidden_capture_bf16(hidden, hc_multiplier=4) == (
        (
            (_bf16(Fraction(5, 2)), _bf16(0), 0x0000),
            (_bf16(5), _bf16(1), _bf16(7)),
        ),
    )


def test_target_hidden_capture_uses_bf16_rne_at_output_boundary() -> None:
    one = 0x3F80
    one_plus_ulp = 0x3F81
    hidden = (
        (
            (
                (one, one),
                (one, one_plus_ulp),
                (one_plus_ulp, one_plus_ulp),
                (one_plus_ulp, one_plus_ulp),
            ),
        ),
    )
    # Column zero is exactly halfway between adjacent BF16 values and ties to
    # the even 0x3f80. Column one lies three quarters of one ULP above 1.0.
    assert target_hidden_capture_bf16(hidden, hc_multiplier=4) == (
        ((one, one_plus_ulp),),
    )


def test_target_hidden_capture_matches_exact_small_integer_means_randomly() -> None:
    rng = random.Random(0x7A267)
    for _ in range(1_000):
        batch = rng.randint(1, 3)
        sequence_length = rng.randint(1, 5)
        width = rng.randint(1, 12)
        hc_multiplier = rng.randint(1, 6)
        integer_values = tuple(
            tuple(
                tuple(
                    tuple(rng.randint(-128, 128) for _ in range(width))
                    for _ in range(hc_multiplier)
                )
                for _ in range(sequence_length)
            )
            for _ in range(batch)
        )
        hidden = tuple(
            tuple(
                tuple(tuple(_bf16(value) for value in vector) for vector in hc)
                for hc in sequence
            )
            for sequence in integer_values
        )
        expected = tuple(
            tuple(
                tuple(
                    _bf16(
                        Fraction(
                            sum(
                                hc[stream][column]
                                for stream in range(hc_multiplier)
                            ),
                            hc_multiplier,
                        )
                    )
                    for column in range(width)
                )
                for hc in sequence
            )
            for sequence in integer_values
        )
        assert target_hidden_capture_bf16(
            hidden, hc_multiplier=hc_multiplier
        ) == expected


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_target_hidden_capture_matches_explicit_pytorch_canonical_tree(
    device: str,
) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    rng = random.Random(0xC4A7)
    shape = (13, 7, 4, 19)
    flat_codes = []
    for _ in range(shape[0] * shape[1] * shape[2] * shape[3]):
        sign = rng.randrange(2) << 15
        exponent = rng.randrange(201) << 7
        fraction = rng.randrange(128)
        flat_codes.append(sign | exponent | fraction)
    hidden = tuple(
        tuple(
            tuple(
                tuple(
                    flat_codes[
                        (((batch * shape[1] + position) * shape[2] + hc) * shape[3])
                        + column
                    ]
                    for column in range(shape[3])
                )
                for hc in range(shape[2])
            )
            for position in range(shape[1])
        )
        for batch in range(shape[0])
    )
    expected = target_hidden_capture_bf16(hidden, hc_multiplier=4)

    bits = torch.tensor(flat_codes, dtype=torch.uint16, device=device).reshape(shape)
    widened = bits.view(torch.bfloat16).to(torch.float32)
    pair_01 = widened[:, :, 0, :] + widened[:, :, 1, :]
    pair_23 = widened[:, :, 2, :] + widened[:, :, 3, :]
    mean = (pair_01 + pair_23) / torch.tensor(
        4.0, dtype=torch.float32, device=device
    )
    observed = mean.to(torch.bfloat16).view(torch.uint16).reshape(-1).cpu().tolist()
    expected_flat = [
        code
        for sequence in expected
        for vector in sequence
        for code in vector
    ]
    assert observed == expected_flat

    # On this bounded finite/nonoverflow audit set, the pinned source
    # expression itself returns BF16 and agrees with the canonical target tree.
    # Extreme overflow behavior remains deliberately governed by NUM-6.5.
    source_mean = bits.view(torch.bfloat16).mean(dim=2)
    assert source_mean.dtype == torch.bfloat16
    source_codes = source_mean.view(torch.uint16).reshape(-1).cpu().tolist()
    assert source_codes == expected_flat


@pytest.mark.parametrize(
    ("hidden", "multiplier", "match"),
    [
        ((), 4, "at least one batch"),
        (((),), 4, "at least one position"),
        (((((0,),),), (((0,),), ((0,),))), 1, "rectangular rank-4"),
        ((((),),), 4, "at least one HC stream"),
        (((((0,),), ((0,), (0,))),), 1, "rectangular rank-4"),
        (((((),),),), 1, "at least one BF16"),
        (((((0,), (0, 1)),),), 2, "rectangular rank-4"),
        (((((True,),),),), 1, "16-bit BF16"),
        (((((BF16_MAX_ENCODING + 1,),),),), 1, "16-bit BF16"),
        (((((0x7F80,),),),), 1, "finite BF16"),
        (((((0x7FC1,),),),), 1, "finite BF16"),
        (((((0,), (0,)),),), 4, "HC dimension"),
        (((((0,),),),), 0, "hc_multiplier"),
    ],
)
def test_invalid_target_hidden_capture_requests_fail_closed(
    hidden, multiplier: int, match: str
) -> None:
    with pytest.raises(VectorReferenceError, match=match):
        target_hidden_capture_bf16(hidden, hc_multiplier=multiplier)


def test_target_hidden_capture_poison_on_canonical_tree_overflow() -> None:
    hidden = (
        (
            (
                (0x7F7F,),
                (0x7F7F,),
                (0xFF7F,),
                (0xFF7F,),
            ),
        ),
    )
    with pytest.raises(VectorReferenceError, match="accumulation overflow"):
        target_hidden_capture_bf16(hidden, hc_multiplier=4)
