from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_ordered_dot,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)
from runtime.reference.routing import (
    MODEL_SOURCE_SHA256,
    ROUTER_SCORE_EXPERTS,
    ROUTER_SCORE_INPUT_FEATURES,
    RoutingReferenceError,
    normalize_routed_weight_codes,
    router_score_bf16,
)


ROUTE_SCALE = encode_binary32_rne(Fraction(3, 2))


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def test_routing_reference_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert ROUTE_SCALE == 0x3FC00000
    assert ROUTER_SCORE_INPUT_FEATURES == 4096
    assert ROUTER_SCORE_EXPERTS == 256


def _independent_router_score(
    inputs: tuple[tuple[int, ...], ...],
    weights: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    input_values = []
    for row in inputs:
        decoded_row = []
        for code in row:
            decoded = decode_bf16(code)
            assert decoded.value is not None
            decoded_row.append(decoded.value)
        input_values.append(tuple(decoded_row))
    weight_values = []
    for row in weights:
        decoded_row = []
        for code in row:
            decoded = decode_bf16(code)
            assert decoded.value is not None
            decoded_row.append(decoded.value)
        weight_values.append(tuple(decoded_row))
    return tuple(
        tuple(binary32_ordered_dot(input_row, weight_row) for weight_row in weight_values)
        for input_row in input_values
    )


def test_router_score_known_answers_retain_binary32_output() -> None:
    inputs = (
        (0x3F80, 0x4000, 0xBF80, 0x3F00),
        (0xBF80, 0xC000, 0x3F80, 0xBF00),
    )
    weights = (
        (0x3F80, 0x3F80, 0x3F80, 0x3F80),
        (0x3F80, 0xBF80, 0x3F80, 0xBF80),
        (0, 0, 0, 0),
    )
    assert router_score_bf16(inputs, weights) == (
        (0x40200000, 0xC0200000, 0),
        (0xC0200000, 0x40200000, 0),
    )


def test_router_score_rounds_each_increasing_k_accumulation() -> None:
    two_to_minus_twelve = 0x3980
    assert router_score_bf16(
        ((0x3F80, two_to_minus_twelve, 0xBF80),),
        ((0x3F80, two_to_minus_twelve, 0x3F80),),
    ) == ((0,),)
    assert _f32(Fraction(1, 1 << 24)) == 0x33800000


def test_router_score_covers_complete_graph_profile() -> None:
    inputs = ((0x3F80,) + (0,) * (ROUTER_SCORE_INPUT_FEATURES - 1),)
    palette = (0, 0x3E80, 0xBE80, 0x3F00, 0xBF00, 0x3F80, 0xBF80, 0x4000)
    weights = tuple(
        (palette[expert % len(palette)],)
        + (0,) * (ROUTER_SCORE_INPUT_FEATURES - 1)
        for expert in range(ROUTER_SCORE_EXPERTS)
    )
    expected = tuple(
        encode_binary32_rne(decode_bf16(palette[expert % len(palette)]).value)
        for expert in range(ROUTER_SCORE_EXPERTS)
    )
    assert router_score_bf16(inputs, weights) == (expected,)


def test_router_score_matches_independent_randomized_composition() -> None:
    generator = random.Random(0x524F_5554_4552_5343)
    palette = (
        0,
        0x0001,
        0x8001,
        0x3D80,
        0xBD80,
        0x3E80,
        0xBE80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
    )
    for _ in range(12):
        reduction = generator.randint(1, 48)
        inputs = tuple(
            tuple(generator.choice(palette) for _ in range(reduction))
            for _ in range(generator.randint(1, 3))
        )
        weights = tuple(
            tuple(generator.choice(palette) for _ in range(reduction))
            for _ in range(generator.randint(1, 5))
        )
        assert router_score_bf16(inputs, weights) == _independent_router_score(
            inputs,
            weights,
        )


def test_router_score_poisons_binary32_accumulator_overflow() -> None:
    with pytest.raises(RoutingReferenceError, match="binary32 accumulation overflow"):
        router_score_bf16(((0x7F7F,),), ((0x7F7F,),))


@pytest.mark.parametrize(
    ("inputs", "weights", "match"),
    [
        ((), ((0,),), "at least one row"),
        ("bad", ((0,),), "must be a sequence"),
        (((),), ((0,),), "at least one value"),
        (((0,), (0, 0)), ((0,),), "rectangular"),
        (((0,),), (), "at least one row"),
        (((0, 0),), ((0,),), "rectangular with width 2"),
        (((True,),), ((0,),), "16-bit BF16"),
        (((0,),), ((False,),), "16-bit BF16"),
        (((0x7F80,),), ((0,),), "finite BF16"),
        (((0,),), ((0x7FC0,),), "finite BF16"),
    ],
)
def test_router_score_rejects_malformed_or_nonfinite_inputs(
    inputs: object,
    weights: object,
    match: str,
) -> None:
    with pytest.raises(RoutingReferenceError, match=match):
        router_score_bf16(inputs, weights)  # type: ignore[arg-type]


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_router_score_matches_bounded_native_pytorch_differential(device: str) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    generator = random.Random(0x524F_5554_4552_5343)
    reduction = ROUTER_SCORE_INPUT_FEATURES
    input_rows = 16
    expert_rows = 4

    def random_bf16() -> int:
        return (
            (generator.randrange(2) << 15)
            | (generator.randrange(117, 135) << 7)
            | generator.randrange(128)
        )

    inputs = tuple(
        tuple(random_bf16() for _ in range(reduction))
        for _ in range(input_rows)
    )
    weights = tuple(
        tuple(random_bf16() for _ in range(reduction))
        for _ in range(expert_rows)
    )
    expected = router_score_bf16(inputs, weights)

    input_bits = torch.tensor(
        [code for row in inputs for code in row], dtype=torch.uint16
    ).reshape(input_rows, reduction)
    weight_bits = torch.tensor(
        [code for row in weights for code in row], dtype=torch.uint16
    ).reshape(expert_rows, reduction)
    observed = torch.nn.functional.linear(
        input_bits.view(torch.bfloat16).to(device).float(),
        weight_bits.view(torch.bfloat16).to(device).float(),
    )
    assert observed.dtype == torch.float32
    observed_codes = tuple(
        int(code) & 0xFFFFFFFF
        for code in observed.view(torch.int32).reshape(-1).cpu().tolist()
    )
    expected_codes = tuple(code for row in expected for code in row)

    # Native GEMM tiling is a bounded cross-check, not the target reduction
    # order. NUM-6 records exact CPU/SM120 counts for this governed corpus.
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


def test_selected_unbiased_scores_are_normalized_then_scaled_in_slot_order() -> None:
    scores = (
        tuple(_f32(value) for value in (1, 2, 3, 4)),
        tuple(_f32(value) for value in (8, 4, 2, 1)),
    )
    assert normalize_routed_weight_codes(
        scores,
        ((3, 1), (0, 3)),
        route_scale_code=ROUTE_SCALE,
    ) == (
        (_f32(1), _f32(Fraction(1, 2))),
        (_f32(Fraction(4, 3)), _f32(Fraction(1, 6))),
    )


def test_duplicate_expert_ids_remain_source_slots_in_denominator_and_output() -> None:
    scores = (tuple(_f32(value) for value in (2, 5, 7)),)
    assert normalize_routed_weight_codes(
        scores,
        ((2, 2, 0),),
        route_scale_code=ROUTE_SCALE,
    ) == (
        (
            _f32(Fraction(21, 32)),
            _f32(Fraction(21, 32)),
            _f32(Fraction(3, 16)),
        ),
    )


def test_routed_weight_normalization_matches_independent_exact_small_integer_model() -> None:
    rng = random.Random(0xA017E)
    for _ in range(2_000):
        token_count = rng.randint(1, 6)
        expert_count = rng.randint(6, 64)
        selected_count = rng.randint(1, 6)
        integer_scores = tuple(
            tuple(rng.randint(1, 10_000) for _ in range(expert_count))
            for _ in range(token_count)
        )
        scores = tuple(
            tuple(_f32(value) for value in row) for row in integer_scores
        )
        indices = tuple(
            tuple(rng.randrange(expert_count) for _ in range(selected_count))
            for _ in range(token_count)
        )
        expected = []
        for score_row, index_row in zip(integer_scores, indices, strict=True):
            selected = tuple(score_row[index] for index in index_row)
            denominator = sum(selected)
            output_row = []
            for score in selected:
                quotient_code = _f32(Fraction(score, denominator))
                quotient = decode_binary32(quotient_code).value
                assert quotient is not None
                output_row.append(_f32(quotient * Fraction(3, 2)))
            expected.append(tuple(output_row))
        assert normalize_routed_weight_codes(
            scores,
            indices,
            route_scale_code=ROUTE_SCALE,
        ) == tuple(expected)


@pytest.mark.parametrize(
    ("scores", "indices", "scale", "match"),
    [
        ((), (), ROUTE_SCALE, "at least one token"),
        (((),), ((0,),), ROUTE_SCALE, "at least one expert"),
        (((_f32(1),), (_f32(1), _f32(2))), ((0,), (0,)), ROUTE_SCALE, "rectangular"),
        (((_f32(1),),), (), ROUTE_SCALE, "token count"),
        (((_f32(1),),), ((),), ROUTE_SCALE, "at least one expert"),
        (((_f32(1),),), ((1,),), ROUTE_SCALE, "must be in"),
        (((_f32(1),),), ((True,),), ROUTE_SCALE, "must be in"),
        (((_f32(-1),),), ((0,),), ROUTE_SCALE, "nonnegative"),
        (((0x7F800000,),), ((0,),), ROUTE_SCALE, "finite binary32"),
        (((_f32(0),),), ((0,),), ROUTE_SCALE, "sum is zero"),
        (((_f32(1),),), ((0,),), _f32(0), "greater than zero"),
        (((_f32(1),),), ((0,),), 0x7FC00000, "finite binary32"),
    ],
)
def test_invalid_routing_requests_fail_closed(
    scores, indices, scale: int, match: str
) -> None:
    with pytest.raises(RoutingReferenceError, match=match):
        normalize_routed_weight_codes(
            scores,
            indices,
            route_scale_code=scale,
        )
