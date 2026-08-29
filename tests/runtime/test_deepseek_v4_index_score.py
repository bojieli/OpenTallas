from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_product_add,
    decode_bf16,
    decode_binary32,
    encode_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.index_score import (
    INDEX_SCORE_COMPRESSION_RATIO,
    INDEX_SCORE_HEAD_DIM,
    INDEX_SCORE_HEADS,
    INDEX_SCORE_SCALE_BINARY32,
    INDEX_SCORE_SITE_COUNT,
    MODEL_SOURCE_SHA256,
    IndexScoreReferenceError,
    IndexScoreResult,
    index_score_bf16,
)


def _bf16(value: int | Fraction) -> int:
    return encode_bf16_rne(value).code


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def test_index_score_reference_is_bound_to_official_profile() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert INDEX_SCORE_SITE_COUNT == 21
    assert INDEX_SCORE_COMPRESSION_RATIO == 4
    assert INDEX_SCORE_HEADS == 64
    assert INDEX_SCORE_HEAD_DIM == 128
    assert INDEX_SCORE_SCALE_BINARY32 == 0x3C3504F3
    scale = decode_binary32(INDEX_SCORE_SCALE_BINARY32).value
    assert scale == Fraction(11863283, 1 << 30)


def test_index_score_orientation_relu_weighting_and_head_reduction() -> None:
    query = (
        (
            (
                (_bf16(1), _bf16(2)),
                (_bf16(1), _bf16(-1)),
            ),
        ),
    )
    kv = (
        (
            (_bf16(1), 0),
            (0, _bf16(-1)),
        ),
    )
    weights = (((_bf16(2), _bf16(3)),),)

    assert index_score_bf16(
        query,
        kv,
        weights,
        scale_binary32=_f32(1),
    ) == IndexScoreResult(
        qk_saturated_element_count=0,
        scaled_weight_saturated_element_count=0,
        weighted_score_saturated_element_count=0,
        output_saturated_element_count=0,
        values=(((_bf16(5), _bf16(3)),),),
    )


def test_index_qk_rounds_each_increasing_dimension_accumulation() -> None:
    two_to_minus_twelve = _bf16(Fraction(1, 1 << 12))
    query = ((((_bf16(1), two_to_minus_twelve, _bf16(-1)),),),)
    kv = (((_bf16(1), two_to_minus_twelve, _bf16(1)),),)
    weights = (((_bf16(1),),),)

    assert index_score_bf16(
        query,
        kv,
        weights,
        scale_binary32=_f32(1),
    ).values == (((0,),),)
    assert _f32(Fraction(1, 1 << 24)) == 0x33800000


def test_index_head_scale_is_binary32_not_prerounded_bf16() -> None:
    result = index_score_bf16(
        ((((_bf16(1),),),),),
        (((_bf16(1),),),),
        (((0x0246,),),),
    )
    assert result.values == (((0x0012,),),)
    scale_value = decode_binary32(INDEX_SCORE_SCALE_BINARY32).value
    weight_value = decode_bf16(0x0246).value
    assert scale_value is not None
    assert weight_value is not None
    assert encode_bf16_rne(weight_value * scale_value).code == 0x0012
    bf16_scale = decode_bf16(0x3C35).value
    assert bf16_scale is not None
    assert encode_bf16_rne(weight_value * bf16_scale).code == 0x0011


def test_index_head_reduction_uses_num_6_1_balanced_tree() -> None:
    query = ((((_bf16(1),),) * 4,),)
    kv = (((_bf16(1),),),)
    contribution_codes = (0x4416, 0x4547, 0xB83C, 0x3903)
    weights = ((contribution_codes,),)

    result = index_score_bf16(
        query,
        kv,
        weights,
        scale_binary32=_f32(1),
    )
    assert result.values == (((0x456C,),),)

    sequential = 0
    for code in contribution_codes:
        value = decode_bf16(code).value
        assert value is not None
        sequential = binary32_add(sequential, encode_binary32_rne(value))
    assert binary32_bits_to_bf16_rne(sequential).code == 0x456D


def test_index_score_preserves_subnormals_and_canonicalizes_relu_zero() -> None:
    result = index_score_bf16(
        (
            (
                ((0x0001,),),
                ((0x8000,),),
            ),
        ),
        (((_bf16(1),),),),
        (
            (
                (_bf16(1),),
                (_bf16(1),),
            ),
        ),
        scale_binary32=_f32(1),
    )
    assert result.values == (((0x0001,), (0,)),)


def test_index_score_accepts_empty_short_prefill_candidate_axis() -> None:
    result = index_score_bf16(
        ((((_bf16(1),),),),),
        ((),),
        (((_bf16(1),),),),
        scale_binary32=_f32(1),
    )
    assert result == IndexScoreResult(0, 0, 0, 0, (((),),))


def test_index_score_covers_complete_head_profile() -> None:
    positive_query = (_bf16(1),) + (0,) * (INDEX_SCORE_HEAD_DIM - 1)
    query = (((positive_query,) * INDEX_SCORE_HEADS,),)
    kv = (
        (
            (_bf16(1),) + (0,) * (INDEX_SCORE_HEAD_DIM - 1),
            (_bf16(-1),) + (0,) * (INDEX_SCORE_HEAD_DIM - 1),
        ),
    )
    weights = ((((_bf16(1),) * INDEX_SCORE_HEADS),),)

    result = index_score_bf16(
        query,
        kv,
        weights,
        scale_binary32=_f32(1),
    )
    assert result.values == (((_bf16(INDEX_SCORE_HEADS), 0),),)


def test_index_score_reports_each_finite_bf16_saturation_boundary() -> None:
    qk = index_score_bf16(
        ((((_bf16(1), _bf16(1)),),),),
        (((0x7F7F, 0x7B00),),),
        (((_bf16(1),),),),
        scale_binary32=_f32(1),
    )
    assert qk.qk_saturated_element_count == 1
    assert qk.values == (((0x7F7F,),),)

    scaled = index_score_bf16(
        ((((_bf16(1),),),),),
        (((_bf16(1),),),),
        (((0x7F7F,),),),
        scale_binary32=_f32(2),
    )
    assert scaled.scaled_weight_saturated_element_count == 1
    assert scaled.values == (((0x7F7F,),),)

    weighted = index_score_bf16(
        ((((0x7F7F,),),),),
        (((_bf16(Fraction(1, 2)),),),),
        (((_bf16(4),),),),
        scale_binary32=_f32(1),
    )
    assert weighted.weighted_score_saturated_element_count == 1
    assert weighted.values == (((0x7F7F,),),)

    output = index_score_bf16(
        ((((_bf16(1),), (_bf16(1),)),),),
        (((_bf16(1),),),),
        (((0x7F7F, 0x7B00),),),
        scale_binary32=_f32(1),
    )
    assert output.output_saturated_element_count == 1
    assert output.values == (((0x7F7F,),),)


def test_index_score_poisons_qk_or_head_reduction_binary32_overflow() -> None:
    with pytest.raises(
        IndexScoreReferenceError,
        match="index QK arithmetic failed.*binary32 accumulation overflow",
    ):
        index_score_bf16(
            ((((0x7F7F,),),),),
            (((0x7F7F,),),),
            (((_bf16(1),),),),
            scale_binary32=_f32(1),
        )

    with pytest.raises(
        IndexScoreReferenceError,
        match="index head reduction failed.*binary32 accumulation overflow",
    ):
        index_score_bf16(
            ((((_bf16(1),), (_bf16(1),)),),),
            (((_bf16(1),),),),
            (((0x7F7F, 0x7F7F),),),
            scale_binary32=_f32(1),
        )


def _balanced_sum(codes: list[int]) -> int:
    level = list(codes)
    while len(level) > 1:
        if len(level) & 1:
            level.append(0)
        level = [
            binary32_add(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        ]
    return level[0]


def _independent_index_score(
    query: tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
    kv: tuple[tuple[tuple[int, ...], ...], ...],
    weights: tuple[tuple[tuple[int, ...], ...], ...],
    scale_code: int,
) -> IndexScoreResult:
    scale = decode_binary32(scale_code).value
    assert scale is not None
    scaled_weights = []
    scaled_saturation = 0
    for sequence in weights:
        scaled_sequence = []
        for row in sequence:
            scaled_row = []
            for code in row:
                value = decode_bf16(code).value
                assert value is not None
                item = encode_bf16_rne(value * scale)
                scaled_saturation += int(item.saturated)
                scaled_row.append(item.code)
            scaled_sequence.append(tuple(scaled_row))
        scaled_weights.append(tuple(scaled_sequence))

    qk_saturation = 0
    weighted_saturation = 0
    output_saturation = 0
    output = []
    for query_sequence, kv_candidates, weight_sequence in zip(
        query, kv, scaled_weights, strict=True
    ):
        output_sequence = []
        for query_heads, weight_row in zip(
            query_sequence, weight_sequence, strict=True
        ):
            output_row = []
            for kv_row in kv_candidates:
                contributions = []
                for query_row, weight_code in zip(
                    query_heads, weight_row, strict=True
                ):
                    accumulator = 0
                    for query_code, kv_code in zip(
                        query_row, kv_row, strict=True
                    ):
                        query_value = decode_bf16(query_code).value
                        kv_value = decode_bf16(kv_code).value
                        assert query_value is not None
                        assert kv_value is not None
                        accumulator = binary32_product_add(
                            accumulator,
                            query_value,
                            kv_value,
                        )
                    qk = binary32_bits_to_bf16_rne(accumulator)
                    qk_saturation += int(qk.saturated)
                    qk_value = decode_bf16(qk.code).value
                    weight_value = decode_bf16(weight_code).value
                    assert qk_value is not None
                    assert weight_value is not None
                    product = encode_bf16_rne(
                        (qk_value if qk_value > 0 else Fraction(0))
                        * weight_value
                    )
                    weighted_saturation += int(product.saturated)
                    product_value = decode_bf16(product.code).value
                    assert product_value is not None
                    contributions.append(encode_binary32_rne(product_value))
                summed = _balanced_sum(contributions)
                quantized = binary32_bits_to_bf16_rne(summed)
                output_saturation += int(quantized.saturated)
                output_row.append(quantized.code)
            output_sequence.append(tuple(output_row))
        output.append(tuple(output_sequence))
    return IndexScoreResult(
        qk_saturated_element_count=qk_saturation,
        scaled_weight_saturated_element_count=scaled_saturation,
        weighted_score_saturated_element_count=weighted_saturation,
        output_saturated_element_count=output_saturation,
        values=tuple(output),
    )


def test_index_score_matches_independent_randomized_composition() -> None:
    rng = random.Random(0x494E_4458_5343_4F52)
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
    scale_codes = (_f32(Fraction(1, 2)), _f32(1), INDEX_SCORE_SCALE_BINARY32)
    for _ in range(200):
        batch_size = rng.randint(1, 2)
        sequence_length = rng.randint(1, 3)
        head_count = rng.randint(1, 5)
        head_dim = rng.randint(1, 8)
        candidate_count = rng.randint(0, 5)
        query = tuple(
            tuple(
                tuple(
                    tuple(rng.choice(palette) for _ in range(head_dim))
                    for _ in range(head_count)
                )
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        kv = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(head_dim))
                for _ in range(candidate_count)
            )
            for _ in range(batch_size)
        )
        weights = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(head_count))
                for _ in range(sequence_length)
            )
            for _ in range(batch_size)
        )
        scale_code = rng.choice(scale_codes)
        assert index_score_bf16(
            query,
            kv,
            weights,
            scale_binary32=scale_code,
        ) == _independent_index_score(query, kv, weights, scale_code)


_VALID_QUERY = [[[[0]]]]
_VALID_KV = [[[0]]]
_VALID_WEIGHTS = [[[0]]]


@pytest.mark.parametrize(
    ("query", "kv", "weights", "scale", "match"),
    [
        (object(), _VALID_KV, _VALID_WEIGHTS, _f32(1), "must be a sequence"),
        ([], _VALID_KV, _VALID_WEIGHTS, _f32(1), "at least one batch"),
        ([[]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "at least one position"),
        ([[[]]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "at least one head"),
        ([[[[]]]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "at least one value"),
        (
            [[[[0]]], [[[0]], [[0]]]],
            [[[0]], [[0]]],
            [[[0]], [[0], [0]]],
            _f32(1),
            "rectangular rank-4",
        ),
        ([[[[0]], [[0], [0]]]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "rank-4"),
        ([[[[0, 0], [0]]]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "rank-4"),
        ([[[[True]]]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "16-bit BF16"),
        ([[[[0x10000]]]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "16-bit BF16"),
        ([[[[0x7F80]]]], _VALID_KV, _VALID_WEIGHTS, _f32(1), "finite BF16"),
        (_VALID_QUERY, object(), _VALID_WEIGHTS, _f32(1), "must be a sequence"),
        (_VALID_QUERY, [], _VALID_WEIGHTS, _f32(1), "batch count"),
        (
            [[[[0]]], [[[0]]]],
            [[[0]], []],
            [[[0]], [[0]]],
            _f32(1),
            "candidate axis",
        ),
        ([[[[0, 0]]]], [[[0]]], _VALID_WEIGHTS, _f32(1), "head dimension 2"),
        (_VALID_QUERY, [[[False]]], _VALID_WEIGHTS, _f32(1), "16-bit BF16"),
        (_VALID_QUERY, [[[0x7FC0]]], _VALID_WEIGHTS, _f32(1), "finite BF16"),
        (_VALID_QUERY, _VALID_KV, object(), _f32(1), "must be a sequence"),
        (_VALID_QUERY, _VALID_KV, [], _f32(1), "batch count"),
        ([[[[0], [0]]]], _VALID_KV, [[[0]]], _f32(1), "contain 2 heads"),
        (
            [[[[0]]], [[[0]]]],
            [[[0]], [[0]]],
            [[[0]], []],
            _f32(1),
            "sequence length",
        ),
        (_VALID_QUERY, _VALID_KV, [[[True]]], _f32(1), "16-bit BF16"),
        (_VALID_QUERY, _VALID_KV, [[[0xFF80]]], _f32(1), "finite BF16"),
        (_VALID_QUERY, _VALID_KV, _VALID_WEIGHTS, True, "binary32 encoding"),
        (_VALID_QUERY, _VALID_KV, _VALID_WEIGHTS, 1 << 32, "binary32 encoding"),
        (_VALID_QUERY, _VALID_KV, _VALID_WEIGHTS, 0, "greater than zero"),
        (_VALID_QUERY, _VALID_KV, _VALID_WEIGHTS, 0xBF800000, "greater than zero"),
        (_VALID_QUERY, _VALID_KV, _VALID_WEIGHTS, 0x7F800000, "finite binary32"),
    ],
)
def test_index_score_rejects_malformed_or_nonfinite_inputs(
    query: object,
    kv: object,
    weights: object,
    scale: object,
    match: str,
) -> None:
    with pytest.raises(IndexScoreReferenceError, match=match):
        index_score_bf16(  # type: ignore[arg-type]
            query,
            kv,
            weights,
            scale_binary32=scale,
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
def test_index_score_matches_bounded_native_pytorch_differential(device: str) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    _require_governed_development_stack(torch, device)
    rng = random.Random(0x494E_4458_4E41_5449)
    batch_size = 2
    sequence_length = 2
    candidate_count = 7

    def random_bf16() -> int:
        return (
            (rng.randrange(2) << 15)
            | (rng.randrange(117, 130) << 7)
            | rng.randrange(128)
        )

    query = tuple(
        tuple(
            tuple(
                tuple(random_bf16() for _ in range(INDEX_SCORE_HEAD_DIM))
                for _ in range(INDEX_SCORE_HEADS)
            )
            for _ in range(sequence_length)
        )
        for _ in range(batch_size)
    )
    kv = tuple(
        tuple(
            tuple(random_bf16() for _ in range(INDEX_SCORE_HEAD_DIM))
            for _ in range(candidate_count)
        )
        for _ in range(batch_size)
    )
    weights = tuple(
        tuple(
            tuple(random_bf16() for _ in range(INDEX_SCORE_HEADS))
            for _ in range(sequence_length)
        )
        for _ in range(batch_size)
    )
    expected = index_score_bf16(query, kv, weights).values

    query_bits = torch.tensor(query, dtype=torch.uint16)
    kv_bits = torch.tensor(kv, dtype=torch.uint16)
    weight_bits = torch.tensor(weights, dtype=torch.uint16)
    query_native = query_bits.view(torch.bfloat16).to(device)
    kv_native = kv_bits.view(torch.bfloat16).to(device)
    weight_native = weight_bits.view(torch.bfloat16).to(device)
    scale = 128**-0.5 * 64**-0.5
    observed = torch.einsum(
        "bshd,btd->bsht",
        query_native,
        kv_native,
    )
    observed = (
        observed.relu_() * (weight_native * scale).unsqueeze(-1)
    ).sum(dim=2)
    assert observed.dtype == torch.bfloat16
    observed_codes = tuple(
        int(code) & 0xFFFF
        for code in observed.view(torch.int16).reshape(-1).cpu().tolist()
    )
    expected_codes = tuple(
        code for sequence in expected for row in sequence for code in row
    )

    differences = [
        abs((0 if observed_code & 0x7FFF == 0 else observed_code) - expected_code)
        for observed_code, expected_code in zip(
            observed_codes,
            expected_codes,
            strict=True,
        )
        if (0 if observed_code & 0x7FFF == 0 else observed_code) != expected_code
    ]
    assert len(expected_codes) == 28
    assert len(differences) == 0
    assert max(differences, default=0) == 0
