"""Focused coverage for the authenticated floor-div index generator."""

from __future__ import annotations

import numpy as np
import pytest

from runtime.abi3.crc import sha256_hex
from runtime.sim.generators import (
    GeneratorError,
    digest_of,
    generate,
    generate_bytes,
    registered,
)


GENERATOR = "floor_div_indices_v1"


@pytest.mark.parametrize("divisor", [4, 128])
def test_floor_div_indices_cover_each_group_boundary(divisor: int) -> None:
    count = 2 * divisor + 1
    table = generate(GENERATOR, {"count": count, "divisor": divisor})

    expected = np.arange(count, dtype=np.uint32) // np.uint32(divisor)
    np.testing.assert_array_equal(table, expected)
    assert table.dtype == np.dtype(np.uint32)
    assert table.shape == (count,)
    assert table.flags.c_contiguous
    assert table[divisor - 1] == 0
    assert table[divisor] == 1
    assert table[2 * divisor] == 2


def test_floor_div_indices_accept_the_strict_minimum_and_divisor_maximum() -> None:
    table = generate(GENERATOR, {"count": 1, "divisor": 0xFFFFFFFF})

    np.testing.assert_array_equal(table, np.array([0], dtype=np.uint32))
    assert GENERATOR in registered()


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"count": 4},
        {"divisor": 4},
        {"count": 0, "divisor": 4},
        {"count": -1, "divisor": 4},
        {"count": (1 << 32) + 1, "divisor": 4},
        {"count": True, "divisor": 4},
        {"count": 4.0, "divisor": 4},
        {"count": "4", "divisor": 4},
        {"count": 4, "divisor": 0},
        {"count": 4, "divisor": -1},
        {"count": 4, "divisor": 1 << 32},
        {"count": 4, "divisor": True},
        {"count": 4, "divisor": 4.0},
        {"count": 4, "divisor": "4"},
        {"count": 4, "divisor": 4, "offset": 0},
    ],
)
def test_floor_div_indices_reject_invalid_parameters(parameters: dict) -> None:
    with pytest.raises(GeneratorError):
        generate(GENERATOR, parameters)


def test_floor_div_indices_bytes_and_digest_are_deterministic() -> None:
    parameters = {"count": 257, "divisor": 128}
    expected = np.repeat(np.arange(3, dtype=np.uint32), [128, 128, 1])

    first = generate(GENERATOR, parameters)
    second = generate(GENERATOR, dict(reversed(tuple(parameters.items()))))
    expected_bytes = expected.tobytes()

    assert first is not second
    assert first.tobytes() == second.tobytes() == expected_bytes
    assert generate_bytes(GENERATOR, parameters) == expected_bytes
    assert digest_of(GENERATOR, parameters) == sha256_hex(expected_bytes)
    assert digest_of(GENERATOR, parameters) == digest_of(
        GENERATOR, dict(parameters)
    )
