from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pytest

from runtime.reference.tensor_accelerator_elementwise import (
    ADD_NUMERIC_CONTRACT as REFERENCE_ADD_CONTRACT,
    SILU_MUL_NUMERIC_CONTRACT as REFERENCE_SILU_CONTRACT,
    ElementwiseReferenceError,
    bf16_add_rne as reference_add,
    qwen3_silu_mul_bf16 as reference_silu_mul,
)
from runtime.tensor_accelerator.elementwise import (
    ADD_NUMERIC_CONTRACT as KERNEL_ADD_CONTRACT,
    SILU_MUL_NUMERIC_CONTRACT as KERNEL_SILU_CONTRACT,
    ElementwiseKernelError,
    bf16_add_rne as kernel_add,
    qwen3_silu_mul_bf16 as kernel_silu_mul,
)


def _rows(values: np.ndarray) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(item) for item in row) for row in values.tolist())


def _assert_add_differential(left: list[list[int]], right: list[list[int]]) -> None:
    reference = reference_add(left, right)
    kernel = kernel_add(left, right)
    assert _rows(kernel.values) == reference.values
    assert (
        kernel.output_saturated_element_count
        == reference.output_saturated_element_count
    )


def _assert_silu_differential(gate: list[list[int]], up: list[list[int]]) -> None:
    reference = reference_silu_mul(gate, up)
    kernel = kernel_silu_mul(gate, up)
    assert _rows(kernel.activation_values) == reference.activation_values
    assert _rows(kernel.values) == reference.values
    assert (
        kernel.activation_saturated_element_count
        == reference.activation_saturated_element_count
    )
    assert (
        kernel.output_saturated_element_count
        == reference.output_saturated_element_count
    )


def _safe_bf16(rng: random.Random) -> int:
    value = np.float32(rng.uniform(-32.0, 32.0))
    bits = value.view(np.uint32)
    upper = int(bits >> np.uint32(16))
    discarded = int(bits & np.uint32(0xFFFF))
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    return upper & 0xFFFF


def test_contracts_and_known_answers_match_pinned_bf16_boundaries() -> None:
    assert REFERENCE_ADD_CONTRACT == KERNEL_ADD_CONTRACT == "bf16_add_rne_v1"
    assert (
        REFERENCE_SILU_CONTRACT
        == KERNEL_SILU_CONTRACT
        == "qwen3_silu_mul_bf16_v1"
    )
    left = [[0x3F80, 0x4000, 0xBF80, 0x0000]]
    right = [[0x3F00, 0xBF80, 0x3F80, 0x8000]]
    assert reference_add(left, right).values == ((0x3FC0, 0x3F80, 0x0000, 0x0000),)
    _assert_add_differential(left, right)

    gate = [[0xC1A0, 0xC120, 0xC080, 0xBF80, 0xBF00, 0x0000,
             0x3F00, 0x3F80, 0x4080, 0x4120, 0x41A0]]
    up = [[0x3FA0, 0xC000, 0x4040, 0xC080, 0x40A0, 0xC0C0,
           0x40E0, 0xC100, 0x4110, 0xC120, 0x4130]]
    result = reference_silu_mul(gate, up)
    assert result.activation_values == (
        (0xB331, 0xB9EE, 0xBD93, 0xBE8A, 0xBE41, 0x0000,
         0x3E9F, 0x3F3B, 0x407B, 0x4120, 0x41A0),
    )
    assert result.values == (
        (0xB35D, 0x3A6E, 0xBE5C, 0x3F8A, 0xBF71, 0x0000,
         0x400B, 0xC0BB, 0x420D, 0xC2C8, 0x435C),
    )
    _assert_silu_differential(gate, up)


def test_randomized_add_and_silu_differential() -> None:
    rng = random.Random(0x51_1A_ADD)
    for _ in range(100):
        rows = rng.randrange(1, 5)
        width = rng.randrange(1, 97)
        left = [[_safe_bf16(rng) for _ in range(width)] for _ in range(rows)]
        right = [[_safe_bf16(rng) for _ in range(width)] for _ in range(rows)]
        _assert_add_differential(left, right)
        _assert_silu_differential(left, right)


def test_silu_activation_is_exhaustive_over_every_finite_bf16_encoding() -> None:
    finite = [code for code in range(1 << 16) if code & 0x7F80 != 0x7F80]
    ones = [0x3F80] * len(finite)
    reference = reference_silu_mul([finite], [ones])
    kernel = kernel_silu_mul([finite], [ones])
    assert _rows(kernel.activation_values) == reference.activation_values
    assert _rows(kernel.values) == reference.values
    assert kernel.activation_saturated_element_count == 0
    assert kernel.output_saturated_element_count == 0


def test_silu_corrects_the_binary32_libm_boundary_before_bf16_materialization() -> None:
    # Gate 0xbb80 is the sole finite BF16 input for which the supported NumPy
    # binary32 exp pipeline falls on the opposite side of the final BF16 tie.
    reference = reference_silu_mul([[0xBB80]], [[0x3F80]])
    kernel = kernel_silu_mul([[0xBB80]], [[0x3F80]])
    assert reference.activation_values == ((0xBB00,),)
    assert reference.values == ((0xBB00,),)
    assert _rows(kernel.activation_values) == reference.activation_values
    assert _rows(kernel.values) == reference.values


@pytest.mark.parametrize("bad_code", [0x7F80, 0xFF80, 0x7FC0, 0xFFFF])
def test_nonfinite_inputs_fail_closed(bad_code: int) -> None:
    with pytest.raises(ElementwiseReferenceError, match="finite BF16"):
        reference_add([[bad_code]], [[0x3F80]])
    with pytest.raises(ElementwiseKernelError, match="NaN or infinity"):
        kernel_add([[bad_code]], [[0x3F80]])
    with pytest.raises(ElementwiseReferenceError, match="finite BF16"):
        reference_silu_mul([[0x3F80]], [[bad_code]])
    with pytest.raises(ElementwiseKernelError, match="NaN or infinity"):
        kernel_silu_mul([[0x3F80]], [[bad_code]])


def test_shape_and_binary32_overflow_fail_closed() -> None:
    with pytest.raises(ElementwiseReferenceError, match="shapes differ"):
        reference_add([[0x3F80]], [[0x3F80, 0x4000]])
    with pytest.raises(ElementwiseKernelError, match="shapes differ"):
        kernel_add([[0x3F80]], [[0x3F80, 0x4000]])
    with pytest.raises(ElementwiseReferenceError, match="rectangular"):
        reference_silu_mul([[0x3F80], [0x3F80, 0x4000]], [[0x3F80], [0x4000]])
    with pytest.raises(ElementwiseKernelError, match="rank-2"):
        kernel_silu_mul([[0x3F80], [0x3F80, 0x4000]], [[0x3F80], [0x4000]])
    with pytest.raises(ElementwiseReferenceError, match="arithmetic failed"):
        reference_add([[0x7F7F]], [[0x7F7F]])
    with pytest.raises(ElementwiseKernelError, match="overflowed"):
        kernel_add([[0x7F7F]], [[0x7F7F]])
    with pytest.raises(ElementwiseReferenceError, match="arithmetic failed"):
        reference_silu_mul([[0x7F7F]], [[0x7F7F]])
    with pytest.raises(ElementwiseKernelError, match="overflowed"):
        kernel_silu_mul([[0x7F7F]], [[0x7F7F]])


def test_reference_has_no_compiler_simulator_array_or_framework_dependency() -> None:
    module = __import__(
        "runtime.reference.tensor_accelerator_elementwise",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "compiler." not in source
    assert "runtime.tensor_accelerator" not in source
    assert "import numpy" not in source.lower()
    assert "import torch" not in source.lower()
