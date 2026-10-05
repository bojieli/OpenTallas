from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
    encode_binary32_rne,
)
from runtime.reference.vector import (
    BF16_MAX_ENCODING,
    HCPostResult,
    MODEL_SOURCE_SHA256,
    VectorReferenceError,
    hc_post_bf16,
    target_hidden_capture_bf16,
)


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(_f32(value)).code


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


def test_hc_post_uses_source_then_destination_comb_axes() -> None:
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
    comb = (
        (
            (
                (_f32(1), _f32(2), _f32(0), _f32(0)),
                (_f32(0), _f32(0), _f32(3), _f32(0)),
                (_f32(4), _f32(0), _f32(0), _f32(0)),
                (_f32(0), _f32(0), _f32(0), _f32(5)),
            ),
        ),
    )
    assert hc_post_bf16(
        branch, residual, post, comb, hc_multiplier=4
    ) == HCPostResult(
        output_codes=(
            (
                (
                    (_bf16(211), _bf16(262)),
                    (_bf16(22), _bf16(44)),
                    (_bf16(93), _bf16(126)),
                    (_bf16(354), _bf16(408)),
                ),
            ),
        ),
        output_saturation_count=0,
    )


def test_hc_post_matches_independent_exact_small_integer_model_randomly() -> None:
    rng = random.Random(0x4C7057)
    for _ in range(500):
        batch_size = rng.randint(1, 2)
        sequence_length = rng.randint(1, 3)
        hidden_width = rng.randint(1, 6)
        hc_multiplier = rng.randint(1, 6)
        branch_values = tuple(
            tuple(
                tuple(rng.randint(-8, 8) for _ in range(hidden_width))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        residual_values = tuple(
            tuple(
                tuple(
                    tuple(rng.randint(-8, 8) for _ in range(hidden_width))
                    for _ in range(hc_multiplier)
                )
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        post_values = tuple(
            tuple(
                tuple(rng.randint(-2, 2) for _ in range(hc_multiplier))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        comb_values = tuple(
            tuple(
                tuple(
                    tuple(rng.randint(-2, 2) for _ in range(hc_multiplier))
                    for _ in range(hc_multiplier)
                )
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        branch = tuple(
            tuple(tuple(_bf16(value) for value in row) for row in sequence)
            for sequence in branch_values
        )
        residual = tuple(
            tuple(
                tuple(tuple(_bf16(value) for value in row) for row in matrix)
                for matrix in sequence
            )
            for sequence in residual_values
        )
        post = tuple(
            tuple(tuple(_f32(value) for value in row) for row in sequence)
            for sequence in post_values
        )
        comb = tuple(
            tuple(
                tuple(tuple(_f32(value) for value in row) for row in matrix)
                for matrix in sequence
            )
            for sequence in comb_values
        )
        expected = tuple(
            tuple(
                tuple(
                    tuple(
                        _bf16(
                            post_values[batch][position][destination]
                            * branch_values[batch][position][column]
                            + sum(
                                comb_values[batch][position][source][destination]
                                * residual_values[batch][position][source][column]
                                for source in range(hc_multiplier)
                            )
                        )
                        for column in range(hidden_width)
                    )
                    for destination in range(hc_multiplier)
                )
                for position in range(sequence_length)
            )
            for batch in range(batch_size)
        )
        assert hc_post_bf16(
            branch,
            residual,
            post,
            comb,
            hc_multiplier=hc_multiplier,
        ) == HCPostResult(expected, 0)


def test_hc_post_canonical_tree_resolves_source_reduction_difference() -> None:
    branch = (((0x436A,),),)
    residual = (((((0x436A,), (0xBE04,), (0xBE5D,), (0xBFCC,)),),))
    post = (((0, 0xBF1002EA, 0, 0),),)
    comb_values = (0x3F1002E2, 0xBEB4BA08, 0xBF3689A2, 0x3E042C08)
    comb = (
        (
            (
                (0, comb_values[0], 0, 0),
                (0, comb_values[1], 0, 0),
                (0, comb_values[2], 0, 0),
                (0, comb_values[3], 0, 0),
            ),
        ),
    )
    observed = hc_post_bf16(
        branch, residual, post, comb, hc_multiplier=4
    ).output_codes[0][0][1][0]
    assert observed == 0xBBD2

    products = tuple(
        binary32_multiply(comb_values[source], residual[0][0][source][0] << 16)
        for source in range(4)
    )
    sequential = binary32_add(
        binary32_add(binary32_add(products[0], products[1]), products[2]),
        products[3],
    )
    sequential = binary32_add(
        binary32_multiply(post[0][0][1], branch[0][0][0] << 16),
        sequential,
    )
    assert binary32_bits_to_bf16_rne(sequential).code == 0xBBD3


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_hc_post_matches_explicit_pytorch_canonical_tree(device: str) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    rng = random.Random(0xC057)
    batch_size, sequence_length, hc_multiplier, hidden_width = (5, 4, 4, 9)
    branch_flat = [
        (rng.randrange(2) << 15) | (rng.randrange(120, 135) << 7) | rng.randrange(128)
        for _ in range(batch_size * sequence_length * hidden_width)
    ]
    residual_flat = [
        (rng.randrange(2) << 15) | (rng.randrange(120, 135) << 7) | rng.randrange(128)
        for _ in range(
            batch_size * sequence_length * hc_multiplier * hidden_width
        )
    ]
    generator = torch.Generator(device="cpu").manual_seed(0xC05)
    post_values = (
        torch.rand(
            (batch_size, sequence_length, hc_multiplier),
            generator=generator,
            dtype=torch.float32,
        )
        * 2
        - 1
    )
    comb_values = (
        torch.rand(
            (batch_size, sequence_length, hc_multiplier, hc_multiplier),
            generator=generator,
            dtype=torch.float32,
        )
        * 2
        - 1
    )
    branch = (
        torch.tensor(branch_flat, dtype=torch.uint16)
        .reshape(batch_size, sequence_length, hidden_width)
        .tolist()
    )
    residual = (
        torch.tensor(residual_flat, dtype=torch.uint16)
        .reshape(batch_size, sequence_length, hc_multiplier, hidden_width)
        .tolist()
    )
    post_codes = post_values.view(torch.uint32).tolist()
    comb_codes = comb_values.view(torch.uint32).tolist()
    expected = hc_post_bf16(
        branch,
        residual,
        post_codes,
        comb_codes,
        hc_multiplier=hc_multiplier,
    )
    assert expected.output_saturation_count == 0

    branch_tensor = (
        torch.tensor(branch_flat, dtype=torch.uint16, device=device)
        .view(torch.bfloat16)
        .reshape(batch_size, sequence_length, hidden_width)
    )
    residual_tensor = (
        torch.tensor(residual_flat, dtype=torch.uint16, device=device)
        .view(torch.bfloat16)
        .reshape(batch_size, sequence_length, hc_multiplier, hidden_width)
    )
    post_tensor = post_values.to(device)
    comb_tensor = comb_values.to(device)
    products = comb_tensor.unsqueeze(-1) * residual_tensor.unsqueeze(-2)
    residual_sum = (products[:, :, 0] + products[:, :, 1]) + (
        products[:, :, 2] + products[:, :, 3]
    )
    output = post_tensor.unsqueeze(-1) * branch_tensor.unsqueeze(-2) + residual_sum
    observed = output.to(torch.bfloat16).view(torch.uint16).reshape(-1).cpu().tolist()
    expected_flat = [
        code
        for sequence in expected.output_codes
        for destinations in sequence
        for vector in destinations
        for code in vector
    ]
    assert observed == expected_flat


def test_hc_post_reports_finite_bf16_saturation() -> None:
    result = hc_post_bf16(
        (((0x7F7F,),),),
        (((((0,), (0,), (0,), (0,)),),)),
        (((0x3F808000, 0, 0, 0),),),
        (((((0, 0, 0, 0),) * 4),),),
        hc_multiplier=4,
    )
    assert result.output_codes[0][0][0][0] == 0x7F7F
    assert result.output_saturation_count == 1


def test_invalid_hc_post_requests_fail_closed() -> None:
    branch = (((_bf16(1),),),)
    residual = (((((_bf16(1),),) * 4,),))
    post = (((_f32(1),) * 4,),)
    comb = (((((_f32(0),) * 4,) * 4,),))

    with pytest.raises(VectorReferenceError, match="at least one batch"):
        hc_post_bf16((), residual, post, comb, hc_multiplier=4)
    with pytest.raises(VectorReferenceError, match="HC dimension"):
        hc_post_bf16(
            branch,
            (((((_bf16(1),),) * 3,),)),
            post,
            comb,
            hc_multiplier=4,
        )
    with pytest.raises(VectorReferenceError, match="hidden width"):
        hc_post_bf16(
            branch,
            (((((_bf16(1), _bf16(2)),) * 4,),)),
            post,
            comb,
            hc_multiplier=4,
        )
    with pytest.raises(VectorReferenceError, match="post_binary32_codes HC"):
        hc_post_bf16(
            branch,
            residual,
            (((_f32(1),) * 3,),),
            comb,
            hc_multiplier=4,
        )
    with pytest.raises(VectorReferenceError, match="destination HC"):
        hc_post_bf16(
            branch,
            residual,
            post,
            (((((_f32(0),) * 3,) * 4,),)),
            hc_multiplier=4,
        )
    with pytest.raises(VectorReferenceError, match="finite BF16"):
        hc_post_bf16((((0x7F80,),),), residual, post, comb, hc_multiplier=4)
    with pytest.raises(VectorReferenceError, match="finite binary32"):
        hc_post_bf16(
            branch,
            residual,
            (((0x7F800000, 0, 0, 0),),),
            comb,
            hc_multiplier=4,
        )
    with pytest.raises(VectorReferenceError, match="hc_multiplier"):
        hc_post_bf16(branch, residual, post, comb, hc_multiplier=0)


def test_hc_post_poison_on_binary32_intermediate_overflow() -> None:
    with pytest.raises(VectorReferenceError, match="accumulation overflow"):
        hc_post_bf16(
            (((0x7F7F,),),),
            (((((0,), (0,), (0,), (0,)),),)),
            (((_f32(2), 0, 0, 0),),),
            (((((0, 0, 0, 0),) * 4),),),
            hc_multiplier=4,
        )
