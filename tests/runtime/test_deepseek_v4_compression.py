from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.compression import (
    COMPRESS_INPUT_FEATURES,
    COMPRESS_OUTPUT_FEATURE_PROFILES,
    INDEX_RATIO4_OUTPUT_FEATURES,
    MAIN_RATIO4_OUTPUT_FEATURES,
    MAIN_RATIO128_OUTPUT_FEATURES,
    MODEL_SOURCE_SHA256,
    CompressProjectResult,
    CompressionReferenceError,
    compress_project_bf16,
)
from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    binary32_product_add,
    decode_bf16,
    encode_binary32_rne,
)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def test_compressor_projection_is_bound_to_official_profiles() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert COMPRESS_INPUT_FEATURES == 4096
    assert INDEX_RATIO4_OUTPUT_FEATURES == 256
    assert MAIN_RATIO128_OUTPUT_FEATURES == 512
    assert MAIN_RATIO4_OUTPUT_FEATURES == 1024
    assert COMPRESS_OUTPUT_FEATURE_PROFILES == (256, 512, 1024)


def test_compressor_projection_keeps_orientation_and_two_outputs_independent() -> None:
    hidden = (
        (
            (_bf16(1), _bf16(2), _bf16(-1), _bf16(Fraction(1, 2))),
            (_bf16(-1), _bf16(-2), _bf16(1), _bf16(Fraction(-1, 2))),
        ),
    )
    kv_weights = (
        (_bf16(1), _bf16(1), _bf16(1), _bf16(1)),
        (_bf16(1), _bf16(-1), _bf16(1), _bf16(-1)),
    )
    gate_weights = (
        (_bf16(2), 0, 0, 0),
        (0, 0, 0, _bf16(4)),
    )

    assert compress_project_bf16(hidden, kv_weights, gate_weights) == (
        CompressProjectResult(
            kv=(
                (
                    (
                        encode_binary32_rne(Fraction(5, 2)),
                        encode_binary32_rne(Fraction(-5, 2)),
                    ),
                    (
                        encode_binary32_rne(Fraction(-5, 2)),
                        encode_binary32_rne(Fraction(5, 2)),
                    ),
                ),
            ),
            scores=(
                (
                    (encode_binary32_rne(2), encode_binary32_rne(2)),
                    (encode_binary32_rne(-2), encode_binary32_rne(-2)),
                ),
            ),
        )
    )


def test_compressor_projection_rounds_each_increasing_k_accumulation() -> None:
    two_to_minus_twelve = _bf16(Fraction(1, 1 << 12))
    hidden = (((_bf16(1), two_to_minus_twelve, _bf16(-1)),),)
    weights = ((_bf16(1), two_to_minus_twelve, _bf16(1)),)

    assert compress_project_bf16(hidden, weights, weights) == CompressProjectResult(
        kv=(((0,),),),
        scores=(((0,),),),
    )
    assert encode_binary32_rne(Fraction(1, 1 << 24)) == 0x33800000


def test_compressor_projection_preserves_bf16_subnormals_in_binary32() -> None:
    result = compress_project_bf16(
        (((0x0001, 0x8001),),),
        ((_bf16(1), 0),),
        ((0, _bf16(1)),),
    )
    assert result == CompressProjectResult(
        kv=(((0x00010000,),),),
        scores=(((0x80010000,),),),
    )


def test_compressor_projection_covers_full_official_reduction_width() -> None:
    hidden_row = (
        (_bf16(1),)
        + (0,) * (COMPRESS_INPUT_FEATURES - 2)
        + (_bf16(2),)
    )
    kv_weights = (
        (_bf16(1),) + (0,) * (COMPRESS_INPUT_FEATURES - 1),
        (0,) * (COMPRESS_INPUT_FEATURES - 1) + (_bf16(1),),
        (_bf16(-1),)
        + (0,) * (COMPRESS_INPUT_FEATURES - 2)
        + (_bf16(Fraction(1, 2)),),
    )
    gate_weights = (
        (_bf16(2),) + (0,) * (COMPRESS_INPUT_FEATURES - 1),
        (0,) * (COMPRESS_INPUT_FEATURES - 1) + (_bf16(-1),),
        (0,) * COMPRESS_INPUT_FEATURES,
    )

    assert compress_project_bf16(
        ((hidden_row,),),
        kv_weights,
        gate_weights,
    ) == CompressProjectResult(
        kv=(((encode_binary32_rne(1), encode_binary32_rne(2), 0),),),
        scores=(((encode_binary32_rne(2), encode_binary32_rne(-2), 0),),),
    )


def _independent_projection(
    hidden: tuple[tuple[tuple[int, ...], ...], ...],
    weights: tuple[tuple[int, ...], ...],
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    output = []
    for sequence in hidden:
        output_sequence = []
        for input_row in sequence:
            output_row = []
            for weight_row in weights:
                accumulator = 0
                for input_code, weight_code in zip(
                    input_row, weight_row, strict=True
                ):
                    input_value = decode_bf16(input_code).value
                    weight_value = decode_bf16(weight_code).value
                    assert input_value is not None
                    assert weight_value is not None
                    accumulator = binary32_product_add(
                        accumulator,
                        input_value,
                        weight_value,
                    )
                output_row.append(accumulator)
            output_sequence.append(tuple(output_row))
        output.append(tuple(output_sequence))
    return tuple(output)


def test_compressor_projection_matches_independent_randomized_composition() -> None:
    rng = random.Random(0x434F_4D50_5052_4F4A)
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
        sequence_length = rng.randint(1, 4)
        input_width = rng.randint(1, 12)
        output_width = rng.randint(1, 5)
        hidden = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(input_width))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        kv_weights = tuple(
            tuple(rng.choice(palette) for _ in range(input_width))
            for _ in range(output_width)
        )
        gate_weights = tuple(
            tuple(rng.choice(palette) for _ in range(input_width))
            for _ in range(output_width)
        )

        assert compress_project_bf16(
            hidden,
            kv_weights,
            gate_weights,
        ) == CompressProjectResult(
            kv=_independent_projection(hidden, kv_weights),
            scores=_independent_projection(hidden, gate_weights),
        )


def test_compressor_projection_poisons_either_accumulator_overflow() -> None:
    with pytest.raises(
        CompressionReferenceError,
        match="compressor KV arithmetic.*binary32 accumulation overflow",
    ):
        compress_project_bf16(
            (((0x7F7F,),),),
            ((0x7F7F,),),
            ((0,),),
        )
    with pytest.raises(
        CompressionReferenceError,
        match="compressor gate arithmetic.*binary32 accumulation overflow",
    ):
        compress_project_bf16(
            (((0x7F7F,),),),
            ((0,),),
            ((0x7F7F,),),
        )


@pytest.mark.parametrize(
    ("hidden", "kv_weights", "gate_weights", "match"),
    [
        (object(), ((0,),), ((0,),), "hidden_bf16_codes must be a sequence"),
        ((), ((0,),), ((0,),), "at least one batch"),
        (((),), ((0,),), ((0,),), "at least one position"),
        ((((),),), ((0,),), ((0,),), "at least one BF16"),
        (
            (((0,),), ((0,), (0,))),
            ((0,),),
            ((0,),),
            "rectangular rank-3",
        ),
        (
            (((0,), (0, 0)),),
            ((0,),),
            ((0,),),
            "rectangular rank-3",
        ),
        ((((True,),),), ((0,),), ((0,),), "16-bit BF16"),
        ((((0x10000,),),), ((0,),), ((0,),), "16-bit BF16"),
        ((((0x7F80,),),), ((0,),), ((0,),), "finite BF16"),
        ((((0,),),), object(), ((0,),), "kv_weight_bf16_codes must be a sequence"),
        ((((0,),),), (), ((0,),), "at least one output row"),
        ((((0,),),), (object(),), ((0,),), r"kv_weight_bf16_codes\[0\]"),
        ((((0, 0),),), ((0,),), ((0, 0),), "input width 2"),
        ((((0,),),), ((True,),), ((0,),), "16-bit BF16"),
        ((((0,),),), ((0x7FC0,),), ((0,),), "finite BF16"),
        ((((0,),),), ((0,),), object(), "gate_weight_bf16_codes must be a sequence"),
        ((((0,),),), ((0,),), (), "at least one output row"),
        ((((0,),),), ((0,),), (object(),), r"gate_weight_bf16_codes\[0\]"),
        ((((0, 0),),), ((0, 0),), ((0,),), "input width 2"),
        ((((0,),),), ((0,),), ((False,),), "16-bit BF16"),
        ((((0,),),), ((0,),), ((0xFF80,),), "finite BF16"),
        ((((0,),),), ((0,), (0,)), ((0,),), "output count must match"),
    ],
)
def test_compressor_projection_rejects_malformed_or_nonfinite_inputs(
    hidden: object,
    kv_weights: object,
    gate_weights: object,
    match: str,
) -> None:
    with pytest.raises(CompressionReferenceError, match=match):
        compress_project_bf16(  # type: ignore[arg-type]
            hidden,
            kv_weights,
            gate_weights,
        )


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
def test_compressor_projection_matches_bounded_native_pytorch_differential(
    device: str,
) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    _require_governed_development_stack(torch, device)
    rng = random.Random(0x434F_4D50_4E41_5449)
    batch_size = 2
    sequence_length = 3
    output_width = 4

    def random_bf16() -> int:
        return (
            (rng.randrange(2) << 15)
            | (rng.randrange(117, 135) << 7)
            | rng.randrange(128)
        )

    hidden = tuple(
        tuple(
            tuple(random_bf16() for _ in range(COMPRESS_INPUT_FEATURES))
            for _ in range(sequence_length)
        )
        for _ in range(batch_size)
    )
    kv_weights = tuple(
        tuple(random_bf16() for _ in range(COMPRESS_INPUT_FEATURES))
        for _ in range(output_width)
    )
    gate_weights = tuple(
        tuple(random_bf16() for _ in range(COMPRESS_INPUT_FEATURES))
        for _ in range(output_width)
    )
    expected = compress_project_bf16(hidden, kv_weights, gate_weights)

    hidden_bits = torch.tensor(hidden, dtype=torch.uint16)
    hidden_float = hidden_bits.view(torch.bfloat16).to(device).float()

    def native_projection(weights):
        weight_bits = torch.tensor(weights, dtype=torch.uint16)
        observed = torch.nn.functional.linear(
            hidden_float,
            weight_bits.view(torch.bfloat16).to(device).float(),
        )
        assert observed.dtype == torch.float32
        return tuple(
            int(code) & 0xFFFFFFFF
            for code in observed.view(torch.int32).reshape(-1).cpu().tolist()
        )

    for observed_codes, expected_tensor in (
        (native_projection(kv_weights), expected.kv),
        (native_projection(gate_weights), expected.scores),
    ):
        expected_codes = tuple(
            code
            for sequence in expected_tensor
            for row in sequence
            for code in row
        )
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
