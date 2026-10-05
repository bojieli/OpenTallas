from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import random

import pytest

from runtime.reference.formats import (
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
    decode_binary32,
    encode_binary32_rne,
    encode_e4m3fn_rne,
    mxfp4_fp8_block_dot,
    quantize_bf16_activation_block,
)
from runtime.reference.hyper_connection import binary32_sigmoid_rne
from runtime.reference.matrix import dense_fp8_linear_bf16
from runtime.reference.swiglu import (
    FP8_SWIGLU_NUMERIC_PROFILE,
    INFERENCE_CONFIG_SHA256,
    KERNEL_SOURCE_SHA256,
    MODEL_REVISION,
    MODEL_SOURCE_SHA256,
    MXFP4_SWIGLU_NUMERIC_PROFILE,
    OFFICIAL_ACTIVATION_BLOCK_SIZE,
    OFFICIAL_HIDDEN_SIZE,
    OFFICIAL_INTERMEDIATE_SIZE,
    OFFICIAL_LAYER0_ROUTED_EXPERT0_TENSORS,
    OFFICIAL_LAYER0_SHARED_EXPERT_TENSORS,
    OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32,
    OFFICIAL_ROUTED_WEIGHT_BLOCK_SIZE,
    OFFICIAL_SITE_COUNT,
    OFFICIAL_SWIGLU_LIMIT_BINARY32,
    SwiGLUReferenceError,
    fp8_swiglu_bf16,
    mxfp4_linear_bf16,
    mxfp4_swiglu_bf16,
)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _mxfp4_matrix(
    entries: dict[int, tuple[int, int, int]],
    *,
    output_features: int,
    input_features: int,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    weights = []
    scales = []
    for output in range(output_features):
        weight_row = [0] * (input_features // 2)
        scale_row = [0x7F] * (input_features // 32)
        if output in entries:
            column, nibble, scale = entries[output]
            weight_row[column // 2] |= nibble << (4 * (column & 1))
            scale_row[column // 32] = scale
        weights.append(tuple(weight_row))
        scales.append(tuple(scale_row))
    return tuple(weights), tuple(scales)


def _fp8_matrix(
    entries: dict[int, tuple[int, int | Fraction]],
    *,
    output_features: int,
    input_features: int,
    scale_code: int,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    weights = []
    for output in range(output_features):
        row = [0] * input_features
        if output in entries:
            column, value = entries[output]
            row[column] = encode_e4m3fn_rne(value).code
        weights.append(tuple(row))
    scales = tuple(
        (scale_code,) * (input_features // 128)
        for _ in range((output_features + 127) // 128)
    )
    return tuple(weights), scales


def _routed_fixture(
    *, route_weight: int = 0x3F000000
) -> tuple[tuple[tuple[int, ...], ...], tuple[int, ...], dict[str, object]]:
    input_features = intermediate_features = 128
    output_features = 3
    inputs = ((_bf16(1),) + (0,) * (input_features - 1),)
    w1, w1_scales = _mxfp4_matrix(
        {
            0: (0, 0x7, 0x80),  # +6 * 2 = +12
            1: (0, 0xF, 0x80),  # -6 * 2 = -12
            2: (0, 0x2, 0x7F),  # +1
        },
        output_features=intermediate_features,
        input_features=input_features,
    )
    w3, w3_scales = _mxfp4_matrix(
        {
            0: (0, 0x7, 0x80),
            1: (0, 0xF, 0x80),
            2: (0, 0x4, 0x7F),  # +2
        },
        output_features=intermediate_features,
        input_features=input_features,
    )
    w2, w2_scales = _mxfp4_matrix(
        {
            0: (0, 0x2, 0x7F),
            1: (1, 0x2, 0x7F),
            2: (2, 0x2, 0x7F),
        },
        output_features=output_features,
        input_features=intermediate_features,
    )
    return inputs, (route_weight,), {
        "w1_packed_weight_bytes": w1,
        "w1_scale_codes": w1_scales,
        "w2_packed_weight_bytes": w2,
        "w2_scale_codes": w2_scales,
        "w3_packed_weight_bytes": w3,
        "w3_scale_codes": w3_scales,
    }


def _shared_fixture() -> tuple[tuple[tuple[int, ...], ...], dict[str, object]]:
    input_features = intermediate_features = 128
    output_features = 3
    inputs = ((_bf16(1),) + (0,) * (input_features - 1),)
    # One scale covers this complete 128x128 tile. The 0.5 code in row two
    # therefore produces +1 while the +/-6 rows produce +/-12.
    w1, w1_scales = _fp8_matrix(
        {0: (0, 6), 1: (0, -6), 2: (0, Fraction(1, 2))},
        output_features=intermediate_features,
        input_features=input_features,
        scale_code=0x80,
    )
    w3, w3_scales = _fp8_matrix(
        {0: (0, 6), 1: (0, -6), 2: (0, 1)},
        output_features=intermediate_features,
        input_features=input_features,
        scale_code=0x80,
    )
    w2, w2_scales = _fp8_matrix(
        {0: (0, 1), 1: (1, 1), 2: (2, 1)},
        output_features=output_features,
        input_features=intermediate_features,
        scale_code=0x7F,
    )
    return inputs, {
        "w1_weight_codes": w1,
        "w1_scale_codes": w1_scales,
        "w2_weight_codes": w2,
        "w2_scale_codes": w2_scales,
        "w3_weight_codes": w3,
        "w3_scale_codes": w3_scales,
    }


def _independent_vector(
    gate: tuple[tuple[int, ...], ...],
    up: tuple[tuple[int, ...], ...],
    route_weights: tuple[int, ...] | None,
) -> tuple[tuple[int, ...], ...]:
    output = []
    for row_index, (gate_row, up_row) in enumerate(zip(gate, up, strict=True)):
        output_row = []
        for gate_bf16, up_bf16 in zip(gate_row, up_row, strict=True):
            gate_code = gate_bf16 << 16
            up_code = up_bf16 << 16
            gate_value = decode_binary32(gate_code).value
            up_value = decode_binary32(up_code).value
            assert gate_value is not None and up_value is not None
            if gate_value > 10:
                gate_code = OFFICIAL_SWIGLU_LIMIT_BINARY32
            if up_value < -10:
                up_code = OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32
            elif up_value > 10:
                up_code = OFFICIAL_SWIGLU_LIMIT_BINARY32
            gated = binary32_multiply(
                binary32_multiply(gate_code, binary32_sigmoid_rne(gate_code)),
                up_code,
            )
            if route_weights is not None:
                gated = binary32_multiply(gated, route_weights[row_index])
            output_row.append(binary32_bits_to_bf16_rne(gated).code)
        output.append(tuple(output_row))
    return tuple(output)


def _independent_mxfp4_linear(
    inputs: tuple[tuple[int, ...], ...],
    packed_weights: tuple[tuple[int, ...], ...],
    scales: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    output = []
    for input_row in inputs:
        activation_blocks = tuple(
            quantize_bf16_activation_block(input_row[start : start + 128])
            for start in range(0, len(input_row), 128)
        )
        output_row = []
        for weight_row, scale_row in zip(packed_weights, scales, strict=True):
            accumulator = 0
            for block_index in range(len(input_row) // 32):
                activation = activation_blocks[block_index // 4]
                activation_start = (block_index % 4) * 32
                packed_start = block_index * 16
                partial = mxfp4_fp8_block_dot(
                    weight_row[packed_start : packed_start + 16],
                    scale_row[block_index],
                    activation.value_codes[
                        activation_start : activation_start + 32
                    ],
                    activation.scale_code,
                )
                accumulator = binary32_add(accumulator, partial)
            output_row.append(binary32_bits_to_bf16_rne(accumulator).code)
        output.append(tuple(output_row))
    return tuple(output)


def test_swiglu_contract_is_bound_to_the_official_source_and_payloads() -> None:
    assert MODEL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert KERNEL_SOURCE_SHA256 == (
        "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
    )
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert OFFICIAL_SITE_COUNT == 46
    assert OFFICIAL_HIDDEN_SIZE == 4096
    assert OFFICIAL_INTERMEDIATE_SIZE == 2048
    assert OFFICIAL_ACTIVATION_BLOCK_SIZE == 128
    assert OFFICIAL_ROUTED_WEIGHT_BLOCK_SIZE == 32
    assert OFFICIAL_SWIGLU_LIMIT_BINARY32 == 0x41200000
    assert OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32 == 0xC1200000
    assert MXFP4_SWIGLU_NUMERIC_PROFILE.endswith("mxfp4_swiglu.v1")
    assert FP8_SWIGLU_NUMERIC_PROFILE.endswith("fp8_swiglu.v1")

    routed = OFFICIAL_LAYER0_ROUTED_EXPERT0_TENSORS
    shared = OFFICIAL_LAYER0_SHARED_EXPERT_TENSORS
    assert len(routed) == len(shared) == 6
    assert sum(record.size_bytes for record in routed) == 13_369_344
    assert sum(record.size_bytes for record in shared) == 25_167_360
    assert len({record.tensor_name for record in routed + shared}) == 12
    assert len({record.sha256 for record in routed + shared}) == 12
    assert [record.logical_shape for record in routed] == [
        (2048, 4096),
        (2048, 128),
        (4096, 2048),
        (4096, 64),
        (2048, 4096),
        (2048, 128),
    ]
    assert [record.logical_shape for record in shared] == [
        (2048, 4096),
        (16, 32),
        (4096, 2048),
        (32, 16),
        (2048, 4096),
        (16, 32),
    ]


def test_mxfp4_linear_uses_low_nibble_first_and_per_32_scales() -> None:
    inputs = ((
        _bf16(1),
        _bf16(1),
        *(0 for _ in range(30)),
        _bf16(1),
        *(0 for _ in range(95)),
    ),)
    weight = [0] * 64
    weight[0] = 0x42  # low logical weight +1, high logical weight +2
    weight[16] = 0x02  # logical reduction index 32 has +1
    scales = (0x7F, 0x80, 0x7F, 0x7F)  # index 32 contribution is doubled

    result = mxfp4_linear_bf16(inputs, (tuple(weight),), (scales,))

    assert result.values == ((_bf16(5),),)
    assert result.counters.activation_blocks_quantized == 1
    assert result.counters.activation_values_quantized == 128
    assert result.counters.weight_block_dot_evaluations == 4
    assert result.counters.exact_product_accumulates == 128
    assert result.counters.cross_block_binary32_adds == 4
    assert result.counters.canonical_weight_payload_bytes == 64
    assert result.counters.canonical_scale_payload_bytes == 4
    assert result.counters.logical_input_bf16_read_bytes == 256
    assert result.counters.logical_weight_data_read_bytes == 64
    assert result.counters.logical_weight_scale_read_bytes == 4
    assert result.counters.logical_output_bf16_write_bytes == 2


def test_mxfp4_linear_rounds_in_increasing_32_value_block_order() -> None:
    inputs = [0] * 128
    inputs[0] = inputs[32] = inputs[64] = _bf16(1)
    weight = [0] * 64
    weight[0] = 0x02  # +1
    weight[16] = 0x02  # +1 * 2^-24
    weight[32] = 0x0A  # -1
    scales = (0x7F, 0x67, 0x7F, 0x7F)

    result = mxfp4_linear_bf16(
        (tuple(inputs),),
        (tuple(weight),),
        (scales,),
    )

    # 1 + 2^-24 ties back to even binary32 1 before -1 is added. An exact
    # end-of-dot sum would retain 2^-24 instead.
    assert result.values == ((0,),)
    assert _bf16(Fraction(1, 1 << 24)) == 0x3380


def test_routed_mxfp4_swiglu_freezes_clamp_asymmetry_and_route_placement() -> None:
    inputs, route_weights, resources = _routed_fixture()

    result = mxfp4_swiglu_bf16(inputs, route_weights, **resources)
    diagnostics = result.diagnostics

    assert result.numeric_profile == MXFP4_SWIGLU_NUMERIC_PROFILE
    assert not result.official_shape_profile
    assert diagnostics.gate_projection_bf16_codes[0][:4] == (
        0x4140,
        0xC140,
        0x3F80,
        0,
    )
    assert diagnostics.up_projection_bf16_codes[0][:4] == (
        0x4140,
        0xC140,
        0x4000,
        0,
    )
    assert diagnostics.clamped_gate_binary32_codes[0][:4] == (
        0x41200000,
        0xC1400000,
        0x3F800000,
        0,
    )
    assert diagnostics.clamped_up_binary32_codes[0][:4] == (
        0x41200000,
        0xC1200000,
        0x40000000,
        0,
    )
    assert diagnostics.sigmoid_binary32_codes[0][:4] == (
        0x3F7FFD06,
        0x36CE2A0F,
        0x3F3B26A8,
        0x3F000000,
    )
    assert diagnostics.post_route_binary32_codes[0][:4] == tuple(
        binary32_multiply(code, route_weights[0])
        for code in diagnostics.gated_up_binary32_codes[0][:4]
    )
    assert diagnostics.intermediate_bf16_codes[0][:4] == (
        0x4248,
        0x39C1,
        0x3F3B,
        0,
    )
    assert result.output_bf16_codes == ((0x4240, 0x3A00, 0x3F40),)

    counters = result.counters
    assert counters.routed
    assert counters.gate_upper_clamps == 1
    assert counters.up_lower_clamps == 1
    assert counters.up_upper_clamps == 1
    assert counters.sigmoid_evaluations == 128
    assert counters.sigmoid_interval_evaluations == 3
    assert counters.sigmoid_max_precision_bits == 48
    assert counters.silu_gate_multiplies == 128
    assert counters.gated_up_multiplies == 128
    assert counters.route_weight_multiplies == 128
    assert counters.intermediate_bf16_conversions == 128
    assert counters.intermediate_bf16_saturations == 0
    assert counters.canonical_weight_payload_bytes == 16_576
    assert counters.canonical_scale_payload_bytes == 1_036
    assert counters.logical_external_input_bf16_read_bytes == 512
    assert counters.logical_gate_up_bf16_write_bytes == 512
    assert counters.logical_gate_up_bf16_read_bytes == 512
    assert counters.logical_route_weight_binary32_read_bytes == 4
    assert counters.logical_intermediate_bf16_write_bytes == 256
    assert counters.logical_intermediate_bf16_read_bytes == 256
    assert counters.logical_final_output_bf16_write_bytes == 6
    assert counters.total_logical_bf16_read_bytes == 1_280
    assert counters.total_logical_bf16_write_bytes == 774
    assert counters.logical_weight_data_read_bytes == 16_576
    assert counters.logical_weight_scale_read_bytes == 1_036
    assert counters.transaction_commits == 1


def test_shared_fp8_swiglu_composes_dense_linears_without_route_weight() -> None:
    inputs, resources = _shared_fixture()

    result = fp8_swiglu_bf16(inputs, **resources)
    diagnostics = result.diagnostics

    assert result.numeric_profile == FP8_SWIGLU_NUMERIC_PROFILE
    assert not result.official_shape_profile
    assert diagnostics.gate_projection_bf16_codes[0][:4] == (
        0x4140,
        0xC140,
        0x3F80,
        0,
    )
    assert diagnostics.up_projection_bf16_codes[0][:4] == (
        0x4140,
        0xC140,
        0x4000,
        0,
    )
    assert diagnostics.gated_up_binary32_codes == (
        diagnostics.post_route_binary32_codes
    )
    assert diagnostics.intermediate_bf16_codes[0][:4] == (
        0x42C8,
        0x3A41,
        0x3FBB,
        0,
    )
    assert result.output_bf16_codes == ((0x42C0, 0x3A80, 0x3FC0),)

    counters = result.counters
    assert not counters.routed
    assert counters.gate_upper_clamps == 1
    assert counters.up_lower_clamps == 1
    assert counters.up_upper_clamps == 1
    assert counters.route_weight_multiplies == 0
    assert counters.canonical_weight_payload_bytes == 33_152
    assert counters.canonical_scale_payload_bytes == 3
    assert counters.logical_external_input_bf16_read_bytes == 512
    assert counters.logical_gate_up_bf16_write_bytes == 512
    assert counters.logical_gate_up_bf16_read_bytes == 512
    assert counters.logical_route_weight_binary32_read_bytes == 0
    assert counters.logical_intermediate_bf16_write_bytes == 256
    assert counters.logical_intermediate_bf16_read_bytes == 256
    assert counters.logical_final_output_bf16_write_bytes == 6
    assert counters.total_logical_bf16_read_bytes == 1_280
    assert counters.total_logical_bf16_write_bytes == 774
    assert counters.logical_weight_data_read_bytes == 33_152
    assert counters.logical_weight_scale_read_bytes == 259
    assert counters.transaction_commits == 1


def test_complete_operators_match_separately_composed_primitives() -> None:
    routed_inputs, route_weights, routed_resources = _routed_fixture()
    routed = mxfp4_swiglu_bf16(
        routed_inputs,
        route_weights,
        **routed_resources,
    )
    routed_gate = _independent_mxfp4_linear(
        routed_inputs,
        routed_resources["w1_packed_weight_bytes"],
        routed_resources["w1_scale_codes"],
    )
    routed_up = _independent_mxfp4_linear(
        routed_inputs,
        routed_resources["w3_packed_weight_bytes"],
        routed_resources["w3_scale_codes"],
    )
    routed_intermediate = _independent_vector(
        routed_gate,
        routed_up,
        route_weights,
    )
    routed_down = _independent_mxfp4_linear(
        routed_intermediate,
        routed_resources["w2_packed_weight_bytes"],
        routed_resources["w2_scale_codes"],
    )
    assert routed.diagnostics.intermediate_bf16_codes == routed_intermediate
    assert routed.output_bf16_codes == routed_down

    shared_inputs, shared_resources = _shared_fixture()
    shared = fp8_swiglu_bf16(shared_inputs, **shared_resources)
    shared_gate = dense_fp8_linear_bf16(
        shared_inputs,
        shared_resources["w1_weight_codes"],
        shared_resources["w1_scale_codes"],
    )
    shared_up = dense_fp8_linear_bf16(
        shared_inputs,
        shared_resources["w3_weight_codes"],
        shared_resources["w3_scale_codes"],
    )
    shared_intermediate = _independent_vector(
        shared_gate.values,
        shared_up.values,
        None,
    )
    shared_down = dense_fp8_linear_bf16(
        shared_intermediate,
        shared_resources["w2_weight_codes"],
        shared_resources["w2_scale_codes"],
    )
    assert shared.diagnostics.intermediate_bf16_codes == shared_intermediate
    assert shared.output_bf16_codes == shared_down.values


def test_routed_composite_matches_seeded_sparse_independent_compositions() -> None:
    rng = random.Random(0x4D58_4650_3453_5749)
    finite_nibbles = (0x1, 0x2, 0x4, 0x9, 0xA, 0xC)
    palette = (0, _bf16(Fraction(1, 2)), _bf16(-1), _bf16(1), _bf16(2))
    for _ in range(3):
        inputs = (tuple(rng.choice(palette) for _ in range(128)),)
        w1_entries = {
            row: (
                rng.randrange(128),
                rng.choice(finite_nibbles),
                rng.randrange(0x7D, 0x81),
            )
            for row in range(8)
        }
        w3_entries = {
            row: (
                rng.randrange(128),
                rng.choice(finite_nibbles),
                rng.randrange(0x7D, 0x81),
            )
            for row in range(8)
        }
        w2_entries = {
            row: (
                rng.randrange(8),
                rng.choice(finite_nibbles),
                rng.randrange(0x7D, 0x81),
            )
            for row in range(4)
        }
        w1, s1 = _mxfp4_matrix(
            w1_entries,
            output_features=128,
            input_features=128,
        )
        w3, s3 = _mxfp4_matrix(
            w3_entries,
            output_features=128,
            input_features=128,
        )
        w2, s2 = _mxfp4_matrix(
            w2_entries,
            output_features=4,
            input_features=128,
        )
        route = (rng.choice((0x3E800000, 0x3F000000, 0x3F800000)),)
        result = mxfp4_swiglu_bf16(
            inputs,
            route,
            w1_packed_weight_bytes=w1,
            w1_scale_codes=s1,
            w2_packed_weight_bytes=w2,
            w2_scale_codes=s2,
            w3_packed_weight_bytes=w3,
            w3_scale_codes=s3,
        )
        gate = _independent_mxfp4_linear(inputs, w1, s1)
        up = _independent_mxfp4_linear(inputs, w3, s3)
        intermediate = _independent_vector(gate, up, route)
        expected = _independent_mxfp4_linear(intermediate, w2, s2)
        assert result.diagnostics.intermediate_bf16_codes == intermediate
        assert result.output_bf16_codes == expected


def test_every_resource_validates_before_any_arithmetic_result() -> None:
    inputs, route_weights, resources = _routed_fixture()
    bad_w1 = [list(row) for row in resources["w1_packed_weight_bytes"]]
    bad_w1[0][0] = 0x77
    bad_w1_scales = [list(row) for row in resources["w1_scale_codes"]]
    bad_w1_scales[0][0] = 0xFE
    bad_w2_scales = [list(row) for row in resources["w2_scale_codes"]]
    bad_w2_scales[-1][-1] = 0xFF

    # The w1 values would overflow binary32 if executed. The later invalid w2
    # scale is nevertheless diagnosed first because all resources freeze
    # before any projection result can become observable.
    with pytest.raises(SwiGLUReferenceError, match=r"w2_scale_codes.*reserved"):
        mxfp4_swiglu_bf16(
            ((0x7F7F,) * 128,),
            route_weights,
            **{
                **resources,
                "w1_packed_weight_bytes": bad_w1,
                "w1_scale_codes": bad_w1_scales,
                "w2_scale_codes": bad_w2_scales,
            },
        )


@pytest.mark.parametrize(
    ("input_codes", "weights", "scales", "match"),
    [
        (object(), ((0,) * 64,), ((0x7F,) * 4,), "exact list or tuple"),
        ((), ((0,) * 64,), ((0x7F,) * 4,), "at least one row"),
        (((0,) * 127,), ((0,) * 64,), ((0x7F,) * 4,), "divisible by 128"),
        (((0,) * 128,), (), ((0x7F,) * 4,), "at least one row"),
        (((0,) * 128,), ((0,) * 63,), ((0x7F,) * 4,), "exactly 64 bytes"),
        (((0,) * 128,), ((0,) * 64,), ((0x7F,) * 3,), "exactly 4 bytes"),
        (((0,) * 128,), ((0,) * 64,), ((0xFF,) * 4,), "reserved E8M0"),
        (((0x7F80,) * 128,), ((0,) * 64,), ((0x7F,) * 4,), "finite BF16"),
    ],
)
def test_mxfp4_linear_rejects_malformed_or_poisoned_resources(
    input_codes: object,
    weights: object,
    scales: object,
    match: str,
) -> None:
    with pytest.raises(SwiGLUReferenceError, match=match):
        mxfp4_linear_bf16(input_codes, weights, scales)


@pytest.mark.parametrize(
    ("route", "match"),
    [
        ((), "one value per input row"),
        ((True,), "must be in"),
        ((0x7F800000,), "finite binary32"),
        ((0xBF800000,), "nonnegative"),
    ],
)
def test_routed_swiglu_rejects_invalid_route_weights(
    route: object,
    match: str,
) -> None:
    inputs, _, resources = _routed_fixture()
    with pytest.raises(SwiGLUReferenceError, match=match):
        mxfp4_swiglu_bf16(inputs, route, **resources)


def test_swiglu_rejects_shape_mismatch_nan_weight_and_overflow() -> None:
    inputs, route, resources = _routed_fixture()
    shortened_w3 = resources["w3_packed_weight_bytes"][:-1]
    shortened_s3 = resources["w3_scale_codes"][:-1]
    with pytest.raises(SwiGLUReferenceError, match="w1 and w3 output"):
        mxfp4_swiglu_bf16(
            inputs,
            route,
            **{
                **resources,
                "w3_packed_weight_bytes": shortened_w3,
                "w3_scale_codes": shortened_s3,
            },
        )

    shared_inputs, shared_resources = _shared_fixture()
    bad_w1 = [list(row) for row in shared_resources["w1_weight_codes"]]
    bad_w1[0][0] = 0x7F
    with pytest.raises(SwiGLUReferenceError, match="finite E4M3FN"):
        fp8_swiglu_bf16(
            shared_inputs,
            **{**shared_resources, "w1_weight_codes": bad_w1},
        )

    with pytest.raises(SwiGLUReferenceError, match="MXFP4 arithmetic.*overflow"):
        mxfp4_linear_bf16(
            ((0x7F7F,) * 128,),
            ((0x77,) * 64,),
            ((0xFE,) * 4,),
        )

    with pytest.raises(SwiGLUReferenceError, match="vector arithmetic.*overflow"):
        overflowing_inputs, _, overflowing_resources = _routed_fixture(
            route_weight=0x7F7FFFFF
        )
        mxfp4_swiglu_bf16(
            overflowing_inputs,
            (0x7F7FFFFF,),
            **overflowing_resources,
        )


def test_results_are_deeply_immutable_after_one_transaction_commit() -> None:
    inputs, route, resources = _routed_fixture()
    result = mxfp4_swiglu_bf16(inputs, route, **resources)
    with pytest.raises(FrozenInstanceError):
        result.numeric_profile = "forged"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.output_bf16_codes[0][0] = 0  # type: ignore[index]
    assert result.counters.transaction_commits == 1


def test_cached_official_layer0_payloads_and_selected_rows_are_exact() -> None:
    root = (
        Path.home()
        / ".cache/opentallas/deepseek-v4-flash-0731/canonical-mp4"
    )
    records = (
        OFFICIAL_LAYER0_ROUTED_EXPERT0_TENSORS
        + OFFICIAL_LAYER0_SHARED_EXPERT_TENSORS
    )
    if not all((root / record.canonical_relative_path).is_file() for record in records):
        pytest.skip("optional canonical MP4 layer-0 SwiGLU payloads are unavailable")

    payloads: dict[str, bytes] = {}
    for record in records:
        payload = (root / record.canonical_relative_path).read_bytes()
        assert len(payload) == record.size_bytes
        assert sha256(payload).hexdigest() == record.sha256
        payloads[record.tensor_name] = payload

    expected_mxfp4 = {
        "w1": (0x3FA9, 0x3E8D),
        "w2": (0xBF65, 0xBFAB),
        "w3": (0xBF69, 0xBF86),
    }
    for role, input_features, output_features in (
        ("w1", 4096, 2048),
        ("w2", 2048, 4096),
        ("w3", 4096, 2048),
    ):
        inputs = (
            tuple(
                _bf16(Fraction((column % 17) - 8, 8))
                for column in range(input_features)
            ),
        )
        weight_payload = payloads[f"layers.0.ffn.experts.0.{role}.weight"]
        scale_payload = payloads[f"layers.0.ffn.experts.0.{role}.scale"]
        selected_rows = (0, output_features - 1)
        packed_width = input_features // 2
        scale_width = input_features // 32
        weights = tuple(
            tuple(
                weight_payload[row * packed_width : (row + 1) * packed_width]
            )
            for row in selected_rows
        )
        scales = tuple(
            tuple(scale_payload[row * scale_width : (row + 1) * scale_width])
            for row in selected_rows
        )
        result = mxfp4_linear_bf16(inputs, weights, scales)
        assert result.values == (expected_mxfp4[role],)
        assert result.values == _independent_mxfp4_linear(inputs, weights, scales)
        assert result.counters.input_features == input_features
        assert result.counters.output_features == 2
        assert result.counters.activation_saturated_blocks == 0
        assert result.counters.output_bf16_saturations == 0

    # The shared path composes the already-qualified dense operator. Execute
    # the same full-column selected-row audit while preserving the complete
    # declared output extent for scale-tile lookup.
    expected_fp8 = {
        "w1": (0xBF97, 0x3E64),
        "w2": (0x3EED, 0x3F42),
        "w3": (0xBF59, 0xBE1B),
    }
    from runtime.reference.matrix import dense_fp8_linear_selected_rows_bf16

    for role, input_features, output_features in (
        ("w1", 4096, 2048),
        ("w2", 2048, 4096),
        ("w3", 4096, 2048),
    ):
        inputs = (
            tuple(
                _bf16(Fraction((column % 17) - 8, 8))
                for column in range(input_features)
            ),
        )
        weight_payload = payloads[f"layers.0.ffn.shared_experts.{role}.weight"]
        scale_payload = payloads[f"layers.0.ffn.shared_experts.{role}.scale"]
        selected_rows = (0, output_features - 1)
        weights = tuple(
            tuple(
                weight_payload[
                    row * input_features : (row + 1) * input_features
                ]
            )
            for row in selected_rows
        )
        scale_width = input_features // 128
        scale_rows = (output_features + 127) // 128
        scales = tuple(
            tuple(scale_payload[row * scale_width : (row + 1) * scale_width])
            for row in range(scale_rows)
        )
        result = dense_fp8_linear_selected_rows_bf16(
            inputs,
            weights,
            scales,
            output_row_indices=selected_rows,
            declared_output_count=output_features,
        )
        assert result.values == (expected_fp8[role],)
        assert result.activation_saturated_block_count == 0
        assert result.output_saturated_element_count == 0


def test_reference_has_no_framework_or_host_float_dependency() -> None:
    source_path = Path(__file__).parents[2] / "runtime/reference/swiglu.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
        if node.level == 0
    }
    assert not imported_roots.intersection({"numpy", "torch", "jax", "tensorflow"})
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )
