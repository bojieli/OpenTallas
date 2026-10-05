from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pytest

from runtime.reference.tensor_accelerator_bf16 import (
    BF16MatrixReferenceError,
    NUMERIC_CONTRACT as REFERENCE_CONTRACT,
    dense_bf16_linear_bf16 as reference_linear,
    dense_bf16_linear_selected_rows_bf16,
)
from runtime.tensor_accelerator.bf16 import (
    BF16KernelError,
    NUMERIC_CONTRACT as KERNEL_CONTRACT,
    accumulate_bf16_tile_fp32,
    dense_bf16_linear_bf16 as kernel_linear,
    finalize_bf16_accumulator,
)


REPRESENTATIVE_CODES = (
    0x0000,
    0x8000,
    0x0001,
    0x8001,
    0x007F,
    0x807F,
    0x0080,
    0x8080,
    0x3B80,
    0x3E80,
    0x3F00,
    0x3F7F,
    0x3F80,
    0x3F81,
    0x4000,
    0x4040,
    0x7E80,
    0xFE80,
    0x7F7E,
    0xFF7E,
)


def _tuples(value: np.ndarray) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(item) for item in row) for row in value.tolist())


def _assert_differential(
    inputs: list[list[int]],
    weights: list[list[int]],
    *,
    input_tile_rows: int = 8,
    output_tile_rows: int = 64,
) -> None:
    reference = reference_linear(inputs, weights)
    kernel = kernel_linear(
        inputs,
        weights,
        input_tile_rows=input_tile_rows,
        output_tile_rows=output_tile_rows,
    )
    assert _tuples(kernel.values) == reference.values
    assert (
        kernel.output_saturated_element_count
        == reference.output_saturated_element_count
    )


def _random_finite_bf16(rng: random.Random) -> int:
    while True:
        code = rng.randrange(1 << 16)
        if code & 0x7F80 != 0x7F80:
            return code


def _bf16_code(sign: int, binade: int, mantissa: int) -> int:
    """One finite BF16 encoding: 1 sign bit, 8 exponent bits, 7 mantissa bits."""
    return (sign << 15) | ((127 + binade) << 7) | mantissa


def _cancelling_codes(rng: random.Random, rows: int, reduction: int) -> list[list[int]]:
    """Inputs on which the reduction order is *observable* after BF16 rounding.

    Every row opens with ``+2**20`` and ``-2**20``.  Summed in ascending K the
    pair annihilates first and the small terms that follow decide the result;
    summed in any other order the small terms are absorbed into the large one
    and lost.  Without that cancellation a reordered reduction perturbs the
    binary32 accumulator by an ulp or two, which the final BF16 rounding then
    swallows -- so a benign operand set would let a reordered reduction pass.
    """
    codes: list[list[int]] = []
    for _ in range(rows):
        row = [_bf16_code(0, 20, 0), _bf16_code(1, 20, 0)]
        while len(row) < reduction:
            row.append(
                _bf16_code(rng.randrange(2), rng.randrange(-3, 4), rng.randrange(1 << 7))
            )
        codes.append(row[:reduction])
    return codes


def _weight_codes(rng: random.Random, rows: int, reduction: int) -> list[list[int]]:
    """Half the weight rows are one exact power of two repeated along K, which
    scales an input row's products without disturbing its cancellation; the
    rest span six binades so ordinary rows are covered too."""
    codes: list[list[int]] = []
    for index in range(rows):
        if index % 2 == 0:
            code = _bf16_code(rng.randrange(2), rng.randrange(-2, 3), 0)
            codes.append([code] * reduction)
        else:
            codes.append(
                [
                    _bf16_code(
                        rng.randrange(2), rng.randrange(-6, 7), rng.randrange(1 << 7)
                    )
                    for _ in range(reduction)
                ]
            )
    return codes


def test_known_answer_and_contract_identity() -> None:
    assert REFERENCE_CONTRACT == KERNEL_CONTRACT
    inputs = [[0x3F80, 0x4000], [0xBF80, 0x3F00]]
    weights = [[0x4040, 0x4080], [0xBF80, 0x3F00]]
    reference = reference_linear(inputs, weights)
    assert reference.values == ((0x4130, 0x0000), (0xBF80, 0x3FA0))
    _assert_differential(inputs, weights, input_tile_rows=1, output_tile_rows=1)


def test_representative_subnormal_rounding_and_cancellation_differential() -> None:
    safe_codes = REPRESENTATIVE_CODES[:-4]
    inputs = [
        list(safe_codes),
        list(reversed(safe_codes)),
    ]
    weights = [
        list(safe_codes),
        [code ^ 0x8000 for code in safe_codes],
        list(reversed(safe_codes)),
    ]
    for input_tile in (1, 2, 7):
        for output_tile in (1, 2, 8):
            _assert_differential(
                inputs,
                weights,
                input_tile_rows=input_tile,
                output_tile_rows=output_tile,
            )


def test_randomized_differential_is_tile_invariant() -> None:
    rng = random.Random(0xB16F32)
    for _ in range(80):
        rows = rng.randrange(1, 5)
        outputs = rng.randrange(1, 7)
        reduction = rng.randrange(1, 25)
        inputs = [
            [_random_finite_bf16(rng) for _ in range(reduction)]
            for _ in range(rows)
        ]
        weights = [
            [_random_finite_bf16(rng) for _ in range(reduction)]
            for _ in range(outputs)
        ]
        try:
            expected = reference_linear(inputs, weights)
        except BF16MatrixReferenceError as reference_error:
            with pytest.raises(BF16KernelError):
                kernel_linear(inputs, weights)
            assert "overflow" in str(reference_error)
            continue
        for input_tile, output_tile in ((1, 1), (2, 3), (8, 64)):
            observed = kernel_linear(
                inputs,
                weights,
                input_tile_rows=input_tile,
                output_tile_rows=output_tile,
            )
            assert _tuples(observed.values) == expected.values
            assert (
                observed.output_saturated_element_count
                == expected.output_saturated_element_count
            )


def test_large_tile_schedule_matches_the_scalar_oracle() -> None:
    """The kernel picks a K-major schedule once a work tile is large enough.

    That schedule walks the reduction index on the outside and updates a whole
    ``[M,N]`` accumulator per step, instead of materialising ``[M,N,K]`` and
    reducing it.  It is a different order of *work*, not a different order of
    any element's reduction, so the scalar oracle must still answer for it, at
    tile shapes on both sides of the crossover.
    """
    rng = random.Random(0x7113)
    cases = [
        (rows, outputs, reduction, None)
        for rows, outputs, reduction in ((8, 200, 32), (40, 40, 24), (3, 512, 16))
    ]
    # The same shapes over the signed zeros and subnormals the zero
    # canonicalisation exists for, where every product underflows or vanishes.
    safe_codes = REPRESENTATIVE_CODES[:-4]
    cases.append((6, 180, len(safe_codes), safe_codes))
    for rows, outputs, reduction, pool in cases:
        if pool is None:
            inputs = _cancelling_codes(rng, rows, reduction)
            weights = _weight_codes(rng, outputs, reduction)
        else:
            inputs = [
                [pool[(index + offset) % len(pool)] for index in range(reduction)]
                for offset in range(rows)
            ]
            weights = [
                [
                    pool[(index * 3 + offset) % len(pool)] ^ (0x8000 * (offset % 2))
                    for index in range(reduction)
                ]
                for offset in range(outputs)
            ]
        expected = reference_linear(inputs, weights)
        # (1, 1) and (8, 64) stay under the crossover; the rest are over it.
        for input_tile, output_tile in (
            (1, 1),
            (8, 64),
            (rows, outputs),
            (rows, 1024),
            (256, 1024),
        ):
            observed = kernel_linear(
                inputs,
                weights,
                input_tile_rows=input_tile,
                output_tile_rows=output_tile,
            )
            assert _tuples(observed.values) == expected.values, (
                rows,
                outputs,
                reduction,
                input_tile,
                output_tile,
                pool is not None,
            )
            assert (
                observed.output_saturated_element_count
                == expected.output_saturated_element_count
            )


def test_selected_row_reference_preserves_logical_order_and_extent() -> None:
    inputs = [[0x3F80, 0x4000, 0x4040]]
    selected = [
        [0x3F80, 0x0000, 0x0000],
        [0x0000, 0x0000, 0x3F80],
    ]
    result = dense_bf16_linear_selected_rows_bf16(
        inputs,
        selected,
        output_row_indices=[2, 4095],
        declared_output_count=4096,
    )
    assert result.values == ((0x3F80, 0x4040),)
    with pytest.raises(BF16MatrixReferenceError, match="strictly increasing"):
        dense_bf16_linear_selected_rows_bf16(
            inputs,
            selected,
            output_row_indices=[4095, 2],
            declared_output_count=4096,
        )


@pytest.mark.parametrize("bad_code", [0x7F80, 0xFF80, 0x7FC0, 0xFFFF])
def test_nonfinite_inputs_fail_closed(bad_code: int) -> None:
    with pytest.raises(BF16MatrixReferenceError, match="finite BF16"):
        reference_linear([[bad_code]], [[0x3F80]])
    with pytest.raises(BF16KernelError, match="NaN or infinity"):
        kernel_linear([[bad_code]], [[0x3F80]])


def test_binary32_overflow_and_invalid_shapes_fail_closed() -> None:
    with pytest.raises(BF16MatrixReferenceError, match="overflow"):
        reference_linear([[0x7F7F]], [[0x7F7F]])
    with pytest.raises(BF16KernelError, match="overflowed binary32"):
        kernel_linear([[0x7F7F]], [[0x7F7F]])

    with pytest.raises(BF16MatrixReferenceError, match="rectangular"):
        reference_linear([[0x3F80], [0x3F80, 0x4000]], [[0x3F80]])
    with pytest.raises(BF16KernelError, match="rank-2"):
        kernel_linear([[0x3F80], [0x3F80, 0x4000]], [[0x3F80]])
    with pytest.raises(BF16KernelError, match="reduction widths differ"):
        kernel_linear([[0x3F80]], [[0x3F80, 0x4000]])
    with pytest.raises(BF16KernelError, match="positive integers"):
        kernel_linear([[0x3F80]], [[0x3F80]], input_tile_rows=0)


def test_finite_bf16_output_overflow_saturates_and_counts() -> None:
    reference = reference_linear([[0x7F01]], [[0x3FFE]])
    kernel = kernel_linear([[0x7F01]], [[0x3FFE]])
    assert reference.values == ((0x7F7F,),)
    assert reference.output_saturated_element_count == 1
    assert _tuples(kernel.values) == reference.values
    assert kernel.output_saturated_element_count == 1


def test_segmented_accumulation_is_bit_exact_for_every_k_partition() -> None:
    rng = random.Random(0xACC0)
    inputs = np.asarray(
        [[_random_finite_bf16(rng) for _ in range(31)] for _ in range(3)],
        dtype=np.uint16,
    )
    weights = np.asarray(
        [[_random_finite_bf16(rng) for _ in range(31)] for _ in range(7)],
        dtype=np.uint16,
    )
    try:
        expected = kernel_linear(inputs, weights)
    except BF16KernelError:
        # Keep this test deterministic if the unrestricted random encodings
        # happen to overflow on a future numeric implementation.
        inputs &= np.uint16(0xBFFF)
        weights &= np.uint16(0xBFFF)
        expected = kernel_linear(inputs, weights)
    for boundaries in ((0, 31), (0, 1, 31), (0, 7, 19, 31)):
        accumulator = None
        for start, end in zip(boundaries[:-1], boundaries[1:], strict=True):
            accumulator = accumulate_bf16_tile_fp32(
                inputs[:, start:end],
                weights[:, start:end],
                None if accumulator is None else accumulator.values,
            )
        assert accumulator is not None
        observed = finalize_bf16_accumulator(accumulator.values)
        assert np.array_equal(observed.values, expected.values)
        assert (
            observed.output_saturated_element_count
            == expected.output_saturated_element_count
        )


def test_segmented_accumulator_rejects_shape_range_and_nonfinite_state() -> None:
    inputs = np.asarray([[0x3F80, 0x4000]], dtype=np.uint16)
    weights = np.asarray([[0x4040, 0x4080]], dtype=np.uint16)
    with pytest.raises(BF16KernelError, match=r"integer \[M,N\]"):
        accumulate_bf16_tile_fp32(inputs, weights, np.zeros((2, 1), dtype=np.uint32))
    with pytest.raises(BF16KernelError, match="NaN or infinity"):
        accumulate_bf16_tile_fp32(
            inputs,
            weights,
            np.asarray([[0x7F800000]], dtype=np.uint32),
        )
    with pytest.raises(BF16KernelError, match="nonempty integer"):
        finalize_bf16_accumulator(np.asarray([], dtype=np.uint32))


def test_reference_has_no_compiler_simulator_or_array_dependency() -> None:
    module = __import__(
        "runtime.reference.tensor_accelerator_bf16",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "compiler." not in source
    assert "runtime.tensor_accelerator" not in source
    assert "import numpy" not in source.lower()
    assert "import torch" not in source.lower()
