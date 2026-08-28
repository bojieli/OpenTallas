from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pytest

from runtime.reference.formats import decode_binary32, encode_binary32_rne
from runtime.reference.tensor_accelerator_rmsnorm import (
    EPSILON_CODE as REFERENCE_EPSILON,
    NUMERIC_CONTRACT as REFERENCE_CONTRACT,
    RMSNormReferenceError,
    binary32_rsqrt_rne,
    rms_norm_bf16 as reference_rmsnorm,
)
from runtime.tensor_accelerator.rmsnorm import (
    EPSILON_CODE as KERNEL_EPSILON,
    NUMERIC_CONTRACT as KERNEL_CONTRACT,
    RMSNormKernelError,
    rms_norm_bf16 as kernel_rmsnorm,
)


def _rows(value: np.ndarray) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(item) for item in row) for row in value.tolist())


def _codes(value: np.ndarray) -> tuple[int, ...]:
    return tuple(int(item) for item in value.tolist())


def _assert_differential(inputs: list[list[int]], weights: list[int]) -> None:
    reference = reference_rmsnorm(inputs, weights)
    kernel = kernel_rmsnorm(inputs, weights)
    assert _rows(kernel.values) == reference.values
    assert _rows(kernel.normalized_values) == reference.normalized_values
    assert _codes(kernel.mean_square_codes) == reference.mean_square_codes
    assert _codes(kernel.inverse_rms_codes) == reference.inverse_rms_codes
    assert (
        kernel.normalized_saturated_element_count
        == reference.normalized_saturated_element_count
    )
    assert (
        kernel.output_saturated_element_count
        == reference.output_saturated_element_count
    )


def _random_safe_bf16(rng: random.Random) -> int:
    value = np.float32(rng.uniform(-8.0, 8.0))
    bits = value.view(np.uint32)
    upper = int(bits >> np.uint32(16))
    discarded = int(bits & np.uint32(0xFFFF))
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    return upper & 0xFFFF


def test_known_answer_contract_and_explicit_bf16_boundary() -> None:
    assert REFERENCE_CONTRACT == KERNEL_CONTRACT
    assert REFERENCE_EPSILON == KERNEL_EPSILON == 0x358637BD
    inputs = [
        [0x3F80, 0x4000, 0x4040, 0x4080],
        [0xBF80, 0x3F00, 0xC000, 0x0000],
    ]
    weights = [0x3F80, 0x3F00, 0x4000, 0xBF80]
    result = reference_rmsnorm(inputs, weights)
    assert result.mean_square_codes == (0x40F00000, 0x3FA80000)
    assert result.inverse_rms_codes == (0x3EBAF4B9, 0x3F5F747D)
    assert result.normalized_values == (
        (0x3EBB, 0x3F3B, 0x3F8C, 0x3FBB),
        (0xBF5F, 0x3EDF, 0xBFDF, 0x0000),
    )
    assert result.values == (
        (0x3EBB, 0x3EBB, 0x400C, 0xBFBB),
        (0xBF5F, 0x3E5F, 0xC05F, 0x0000),
    )
    _assert_differential(inputs, weights)


def test_rsqrt_is_correctly_rounded_around_boundaries() -> None:
    codes = (
        encode_binary32_rne(1),
        encode_binary32_rne(2),
        encode_binary32_rne(3),
        encode_binary32_rne(4096),
        0x00000001,
        0x007FFFFF,
        0x00800000,
        0x3A5C35E6,
        0x7F7FFFFF,
    )
    for code in codes:
        result = binary32_rsqrt_rne(code)
        argument = decode_binary32(code).value
        observed = decode_binary32(result).value
        assert argument is not None and observed is not None
        if result > 0:
            lower = decode_binary32(result - 1).value
            assert lower is not None
            lower_midpoint = (lower + observed) / 2
            assert lower_midpoint * lower_midpoint * argument <= 1
        if result < 0x7F7FFFFF:
            upper = decode_binary32(result + 1).value
            assert upper is not None
            upper_midpoint = (observed + upper) / 2
            assert upper_midpoint * upper_midpoint * argument >= 1


def test_randomized_scalar_and_kernel_differential() -> None:
    rng = random.Random(0x524D534E)
    for _ in range(60):
        rows = rng.randrange(1, 5)
        width = rng.randrange(1, 65)
        inputs = [
            [_random_safe_bf16(rng) for _ in range(width)] for _ in range(rows)
        ]
        weights = [_random_safe_bf16(rng) for _ in range(width)]
        _assert_differential(inputs, weights)


@pytest.mark.parametrize("bad_code", [0x7F80, 0xFF80, 0x7FC0, 0xFFFF])
def test_nonfinite_input_and_weight_fail_closed(bad_code: int) -> None:
    with pytest.raises(RMSNormReferenceError, match="finite BF16"):
        reference_rmsnorm([[bad_code]], [0x3F80])
    with pytest.raises(RMSNormKernelError, match="NaN or infinity"):
        kernel_rmsnorm([[bad_code]], [0x3F80])
    with pytest.raises(RMSNormReferenceError, match="finite BF16"):
        reference_rmsnorm([[0x3F80]], [bad_code])
    with pytest.raises(RMSNormKernelError, match="NaN or infinity"):
        kernel_rmsnorm([[0x3F80]], [bad_code])


def test_shapes_epsilon_and_overflow_fail_closed() -> None:
    with pytest.raises(RMSNormReferenceError, match="rectangular"):
        reference_rmsnorm([[0x3F80], [0x3F80, 0x4000]], [0x3F80])
    with pytest.raises(RMSNormKernelError, match="rank-2"):
        kernel_rmsnorm([[0x3F80], [0x3F80, 0x4000]], [0x3F80])
    with pytest.raises(RMSNormReferenceError, match="exactly 2"):
        reference_rmsnorm([[0x3F80, 0x4000]], [0x3F80])
    with pytest.raises(RMSNormKernelError, match="width 2"):
        kernel_rmsnorm([[0x3F80, 0x4000]], [0x3F80])
    with pytest.raises(RMSNormReferenceError, match="positive finite"):
        reference_rmsnorm([[0x3F80]], [0x3F80], epsilon_code=0)
    with pytest.raises(RMSNormKernelError, match="positive finite"):
        kernel_rmsnorm([[0x3F80]], [0x3F80], epsilon_code=0)
    with pytest.raises(RMSNormReferenceError, match="arithmetic failed"):
        reference_rmsnorm([[0x7F7F]], [0x3F80])
    with pytest.raises(RMSNormKernelError, match="overflowed"):
        kernel_rmsnorm([[0x7F7F]], [0x3F80])


def test_reference_has_no_compiler_simulator_array_or_framework_dependency() -> None:
    module = __import__(
        "runtime.reference.tensor_accelerator_rmsnorm",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "compiler." not in source
    assert "runtime.tensor_accelerator" not in source
    assert "import numpy" not in source.lower()
    assert "import torch" not in source.lower()
