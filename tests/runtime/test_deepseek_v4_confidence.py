from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.confidence import (
    CONFIDENCE_BLOCK_SIZE,
    CONFIDENCE_HIDDEN_WIDTH,
    CONFIDENCE_INPUT_WIDTH,
    CONFIDENCE_MARKOV_WIDTH,
    CONFIDENCE_OUTPUTS,
    MODEL_SOURCE_SHA256,
    ConfidenceReferenceError,
    confidence_score_bf16,
)
from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    binary32_product_add,
    decode_bf16,
    encode_binary32_rne,
)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def test_confidence_reference_is_bound_to_official_profile() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert CONFIDENCE_HIDDEN_WIDTH == 4096
    assert CONFIDENCE_MARKOV_WIDTH == 256
    assert CONFIDENCE_INPUT_WIDTH == 4352
    assert CONFIDENCE_OUTPUTS == 1
    assert CONFIDENCE_BLOCK_SIZE == 5


def test_confidence_concat_order_and_binary32_output() -> None:
    hidden = (((_bf16(1), _bf16(2)), (_bf16(-1), _bf16(-2))),)
    markov = (((_bf16(3),), (_bf16(-3),)),)
    weights = ((_bf16(1), _bf16(-1), _bf16(2)),)

    assert confidence_score_bf16(hidden, markov, weights) == (
        (encode_binary32_rne(5), encode_binary32_rne(-5)),
    )


def test_confidence_score_rounds_each_increasing_k_accumulation() -> None:
    two_to_minus_twelve = _bf16(Fraction(1, 1 << 12))
    assert confidence_score_bf16(
        (((_bf16(1), two_to_minus_twelve),),),
        (((_bf16(-1),),),),
        ((_bf16(1), two_to_minus_twelve, _bf16(1)),),
    ) == ((0,),)
    assert encode_binary32_rne(Fraction(1, 1 << 24)) == 0x33800000


def test_confidence_score_covers_complete_graph_profile() -> None:
    hidden_rows = tuple(
        ((_bf16(position + 1),) + (0,) * (CONFIDENCE_HIDDEN_WIDTH - 1))
        for position in range(CONFIDENCE_BLOCK_SIZE)
    )
    markov_rows = tuple(
        ((_bf16(10 * (position + 1)),) + (0,) * (CONFIDENCE_MARKOV_WIDTH - 1))
        for position in range(CONFIDENCE_BLOCK_SIZE)
    )
    weights = (
        (_bf16(2),)
        + (0,) * (CONFIDENCE_HIDDEN_WIDTH - 1)
        + (_bf16(-1),)
        + (0,) * (CONFIDENCE_MARKOV_WIDTH - 1),
    )

    assert confidence_score_bf16((hidden_rows,), (markov_rows,), weights) == (
        tuple(encode_binary32_rne(-8 * (position + 1)) for position in range(5)),
    )


def _independent_confidence_score(
    hidden: tuple[tuple[tuple[int, ...], ...], ...],
    markov: tuple[tuple[tuple[int, ...], ...], ...],
    weights: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    weight_values = []
    for code in weights[0]:
        decoded = decode_bf16(code)
        assert decoded.value is not None
        weight_values.append(decoded.value)
    output = []
    for hidden_sequence, markov_sequence in zip(hidden, markov, strict=True):
        output_sequence = []
        for hidden_row, markov_row in zip(
            hidden_sequence, markov_sequence, strict=True
        ):
            accumulator = 0
            for code, weight in zip(
                hidden_row + markov_row, weight_values, strict=True
            ):
                decoded = decode_bf16(code)
                assert decoded.value is not None
                accumulator = binary32_product_add(
                    accumulator,
                    decoded.value,
                    weight,
                )
            output_sequence.append(accumulator)
        output.append(tuple(output_sequence))
    return tuple(output)


def test_confidence_score_matches_independent_randomized_composition() -> None:
    rng = random.Random(0x434F_4E46_5343_4F52)
    palette = (
        0,
        0x0001,
        0x8001,
        _bf16(Fraction(1, 4)),
        _bf16(Fraction(-1, 4)),
        _bf16(1),
        _bf16(-1),
        _bf16(2),
        _bf16(-2),
        _bf16(8),
        _bf16(-8),
    )
    for _ in range(200):
        batch_size = rng.randint(1, 3)
        sequence_length = rng.randint(1, 5)
        hidden_width = rng.randint(1, 12)
        markov_width = rng.randint(1, 8)
        hidden = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(hidden_width))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        markov = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(markov_width))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        weights = (
            tuple(rng.choice(palette) for _ in range(hidden_width + markov_width)),
        )
        assert confidence_score_bf16(hidden, markov, weights) == (
            _independent_confidence_score(hidden, markov, weights)
        )


def test_confidence_score_poisons_binary32_accumulator_overflow() -> None:
    with pytest.raises(
        ConfidenceReferenceError, match="binary32 accumulation overflow"
    ):
        confidence_score_bf16(
            (((0x7F7F,),),),
            (((0,),),),
            ((0x7F7F, 0),),
        )


@pytest.mark.parametrize(
    ("hidden", "markov", "weights", "match"),
    [
        (object(), (((0,),),), ((0, 0),), "hidden_bf16_codes must be a sequence"),
        ((), (((0,),),), ((0, 0),), "at least one batch"),
        (((),), (((0,),),), ((0, 0),), "at least one position"),
        ((((),),), (((0,),),), ((0,),), "at least one BF16"),
        (
            (((0,),), ((0,), (0,))),
            (((0,),), ((0,), (0,))),
            ((0, 0),),
            "rectangular rank-3",
        ),
        (
            (((0,), (0, 0)),),
            (((0,), (0,)),),
            ((0, 0),),
            "rectangular rank-3",
        ),
        ((((True,),),), (((0,),),), ((0, 0),), "16-bit BF16"),
        ((((0x10000,),),), (((0,),),), ((0, 0),), "16-bit BF16"),
        ((((0x7F80,),),), (((0,),),), ((0, 0),), "finite BF16"),
        ((((0,),),), object(), ((0, 0),), "markov_bf16_codes must be a sequence"),
        ((((0,),),), (), ((0, 0),), "at least one batch"),
        ((((0,),),), ((),), ((0,),), "at least one position"),
        ((((0,),),), (((),),), ((0,),), "at least one BF16"),
        ((((0,),),), (((True,),),), ((0, 0),), "16-bit BF16"),
        ((((0,),),), (((0x7FC0,),),), ((0, 0),), "finite BF16"),
        (
            (((0,),),),
            (((0,),), ((0,),)),
            ((0, 0),),
            "batch and sequence shape",
        ),
        (
            (((0,), (0,)),),
            (((0,),),),
            ((0, 0),),
            "batch and sequence shape",
        ),
        ((((0,),),), (((0,),),), object(), "weight_bf16_codes must be a sequence"),
        ((((0,),),), (((0,),),), (), "exactly one"),
        ((((0,),),), (((0,),),), ((0, 0), (0, 0)), "exactly one"),
        ((((0,),),), (((0,),),), (object(),), r"weight_bf16_codes\[0\]"),
        ((((0,),),), (((0,),),), ((0,),), "concatenated width 2"),
        ((((0,),),), (((0,),),), ((True, 0),), "16-bit BF16"),
        ((((0,),),), (((0,),),), ((0x7F80, 0),), "finite BF16"),
    ],
)
def test_confidence_score_rejects_malformed_or_nonfinite_inputs(
    hidden: object,
    markov: object,
    weights: object,
    match: str,
) -> None:
    with pytest.raises(ConfidenceReferenceError, match=match):
        confidence_score_bf16(hidden, markov, weights)  # type: ignore[arg-type]


def _require_governed_development_stack(torch, device: str) -> None:
    if str(torch.__version__) != "2.10.0+cu128":
        pytest.skip("development observation is pinned to PyTorch 2.10.0+cu128")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    if device == "cuda" and (
        torch.version.cuda != "12.8" or torch.cuda.get_device_capability() != (12, 0)
    ):
        pytest.skip("CUDA development observation is pinned to CUDA 12.8 and SM120")


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_confidence_score_matches_bounded_native_pytorch_differential(
    device: str,
) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    _require_governed_development_stack(torch, device)
    rng = random.Random(0x434F_4E46_5343_4F52)
    batch_size = 4

    def random_bf16() -> int:
        return (
            (rng.randrange(2) << 15)
            | (rng.randrange(117, 135) << 7)
            | rng.randrange(128)
        )

    hidden = tuple(
        tuple(
            tuple(random_bf16() for _ in range(CONFIDENCE_HIDDEN_WIDTH))
            for _ in range(CONFIDENCE_BLOCK_SIZE)
        )
        for _ in range(batch_size)
    )
    markov = tuple(
        tuple(
            tuple(random_bf16() for _ in range(CONFIDENCE_MARKOV_WIDTH))
            for _ in range(CONFIDENCE_BLOCK_SIZE)
        )
        for _ in range(batch_size)
    )
    weights = (tuple(random_bf16() for _ in range(CONFIDENCE_INPUT_WIDTH)),)
    expected = confidence_score_bf16(hidden, markov, weights)

    hidden_bits = torch.tensor(hidden, dtype=torch.uint16)
    markov_bits = torch.tensor(markov, dtype=torch.uint16)
    weight_bits = torch.tensor(weights, dtype=torch.uint16)
    concatenated = torch.cat(
        (
            hidden_bits.view(torch.bfloat16).to(device),
            markov_bits.view(torch.bfloat16).to(device),
        ),
        dim=-1,
    )
    assert concatenated.dtype == torch.bfloat16
    observed = torch.nn.functional.linear(
        concatenated.float(),
        weight_bits.view(torch.bfloat16).to(device).float(),
    ).squeeze(-1)
    assert observed.dtype == torch.float32
    observed_codes = tuple(
        int(code) & 0xFFFFFFFF
        for code in observed.view(torch.int32).reshape(-1).cpu().tolist()
    )
    expected_codes = tuple(code for sequence in expected for code in sequence)

    assert all(
        observed_code == expected_code
        or (
            observed_code >> 31 == expected_code >> 31
            and abs(observed_code - expected_code) <= 512
        )
        for observed_code, expected_code in zip(
            observed_codes,
            expected_codes,
            strict=True,
        )
    )
