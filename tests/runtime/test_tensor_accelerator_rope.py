from __future__ import annotations

import hashlib
import random
from pathlib import Path

import numpy as np
import pytest

from runtime.reference.tensor_accelerator_rope import (
    INV_FREQ_BINARY32_CODES as REFERENCE_INV_FREQ,
    NUMERIC_CONTRACT as REFERENCE_CONTRACT,
    RoPEReferenceError,
    rope_bf16 as reference_rope,
)
from runtime.tensor_accelerator.rope import (
    INV_FREQ_BINARY32_CODES as KERNEL_INV_FREQ,
    MAX_POSITIONS,
    NUMERIC_CONTRACT as KERNEL_CONTRACT,
    RoPEKernelError,
    coefficient_table_bf16,
    rope_bf16 as kernel_rope,
)


def _rows(value: np.ndarray) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(item) for item in row) for row in value.tolist())


def _assert_differential(
    query: list[list[int]],
    key: list[list[int]],
    coefficients: np.ndarray,
) -> None:
    width = len(query[0])
    cosine = [int(item) for item in coefficients[:width].tolist()]
    sine = [int(item) for item in coefficients[width:].tolist()]
    reference = reference_rope(query, key, cosine, sine)
    kernel = kernel_rope(query, key, coefficients)
    assert _rows(kernel.query_values) == reference.query_values
    assert _rows(kernel.key_values) == reference.key_values
    assert (
        kernel.multiplication_saturated_element_count
        == reference.multiplication_saturated_element_count
    )
    assert (
        kernel.addition_saturated_element_count
        == reference.addition_saturated_element_count
    )


def test_contract_constants_and_complete_8256_coefficient_table_are_frozen() -> None:
    assert REFERENCE_CONTRACT == KERNEL_CONTRACT == "qwen3_rope_fp32_bf16_v1"
    assert REFERENCE_INV_FREQ == KERNEL_INV_FREQ
    table = coefficient_table_bf16(MAX_POSITIONS)
    assert table.shape == (8256, 256)
    assert hashlib.sha256(table.astype("<u2", copy=False).tobytes()).hexdigest() == (
        "c4a38c505ed56202240983c7f4cb992d30966448bb651b54d93bdfd434bb4d77"
    )
    legacy_8192 = table[:8192]
    assert hashlib.sha256(
        legacy_8192.astype("<u2", copy=False).tobytes()
    ).hexdigest() == (
        "aeaab0b9af138b2f7464ed38c925ca4ab2faa6de294a49d3e579003e70f7051b"
    )
    extension = table[8192:]
    assert hashlib.sha256(
        extension.astype("<u2", copy=False).tobytes()
    ).hexdigest() == (
        "02f66262eee5999f64c02d5d307a52b70564abffffbc4ed53ec0f9db2de35e74"
    )
    legacy_8000 = table[:8000]
    assert hashlib.sha256(
        legacy_8000.astype("<u2", copy=False).tobytes()
    ).hexdigest() == (
        "82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9"
    )
    assert [int(table[7999, index]) for index in (0, 3, 10, 16, 128, 142)] == [
        16224,
        16024,
        16255,
        48471,
        16120,
        48388,
    ]
    assert [int(table[8255, index]) for index in (0, 3, 10, 16, 128, 142)] == [
        16102,
        49021,
        48716,
        49013,
        48997,
        48647,
    ]


def test_position_zero_is_identity_and_unit_sine_is_exact_half_rotation() -> None:
    query = [[0x3F80, 0x4000, 0x4040, 0x4080]]
    key = [[0xBF80, 0x3F00, 0xC000, 0x0000]]
    position_zero = np.asarray([0x3F80] * 4 + [0] * 4)
    identity = kernel_rope(query, key, position_zero)
    assert _rows(identity.query_values) == tuple(tuple(row) for row in query)
    assert _rows(identity.key_values) == tuple(tuple(row) for row in key)

    unit_sine = np.asarray([0, 0, 0, 0, 0x3F80, 0x3F80, 0x3F80, 0x3F80])
    rotated = reference_rope(
        query,
        key,
        unit_sine[:4].tolist(),
        unit_sine[4:].tolist(),
    )
    assert rotated.query_values == ((0xC040, 0xC080, 0x3F80, 0x4000),)
    assert rotated.key_values == ((0x4000, 0x0000, 0xBF80, 0x3F00),)
    _assert_differential(query, key, unit_sine)


def test_randomized_scalar_and_optimized_differential() -> None:
    rng = random.Random(0x524F5045)
    table = coefficient_table_bf16(MAX_POSITIONS)
    for _ in range(40):
        query_heads = rng.randrange(1, 6)
        key_heads = rng.randrange(1, 4)
        width = 2 * rng.randrange(1, 17)

        def code() -> int:
            magnitude = rng.randrange(0, 0x7F80)
            return magnitude | (0x8000 if rng.randrange(2) and magnitude else 0)

        query = [[code() for _ in range(width)] for _ in range(query_heads)]
        key = [[code() for _ in range(width)] for _ in range(key_heads)]
        full = table[rng.randrange(MAX_POSITIONS)]
        coefficients = np.concatenate(
            (
                full[: width // 2],
                full[64 : 64 + width // 2],
                full[128 : 128 + width // 2],
                full[192 : 192 + width // 2],
            )
        )
        _assert_differential(query, key, coefficients)


@pytest.mark.parametrize("bad_code", [0x7F80, 0xFF80, 0x7FC0, 0xFFFF])
def test_nonfinite_operands_fail_closed(bad_code: int) -> None:
    with pytest.raises(RoPEReferenceError, match="finite BF16"):
        reference_rope([[bad_code, 0]], [[0, 0]], [0x3F80, 0x3F80], [0, 0])
    with pytest.raises(RoPEKernelError, match="NaN or infinity"):
        kernel_rope([[bad_code, 0]], [[0, 0]], [0x3F80, 0x3F80, 0, 0])


def test_shapes_and_unqualified_coefficient_domain_fail_closed() -> None:
    with pytest.raises(RoPEReferenceError, match="positive even"):
        reference_rope([[0]], [[0]], [0], [0])
    with pytest.raises(RoPEKernelError, match="must match"):
        kernel_rope([[0, 0]], [[0, 0, 0, 0]], [0, 0, 0, 0])
    with pytest.raises(RoPEKernelError, match="qualified bound"):
        coefficient_table_bf16(MAX_POSITIONS + 1)


def test_reference_has_no_compiler_simulator_array_or_framework_dependency() -> None:
    module = __import__(
        "runtime.reference.tensor_accelerator_rope",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "compiler." not in source
    assert "runtime.tensor_accelerator" not in source
    assert "import numpy" not in source.lower()
    assert "import torch" not in source.lower()
