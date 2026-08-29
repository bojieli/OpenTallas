"""Deterministic generators for derived constants.

Some constants a model needs exist in no checkpoint: a rotary coefficient
table, a causal window index table, a compressed-group enumeration. They are
computed from declared parameters. ADR-003 section 15 forbids a *backend* from
computing model numerics, and the neutral IR previously could not declare such a
tensor at all, which left `VECTOR.ROPE`'s coefficient-rows operand slot
unfillable by either exporter.

The resolution keeps the artifacts-only property intact. A derived constant is
declared in the neutral IR by naming a generator and its parameters; the
deployment binds the SHA-256 of the *result*; and the device materialises it
here and checks that digest before use. So the table is derived from declared
parameters rather than injected, the compiler still does not invent numerics,
and a generator that drifts is caught at load rather than silently changing a
model's outputs.

Every generator must be a pure function of its declared parameters, must be
bit-reproducible across machines, and must be versioned in its name.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping

import numpy as np

from runtime.abi3.crc import sha256_hex


class GeneratorError(Exception):
    """Raised when a generator is unknown, misparameterised, or drifts."""


_REGISTRY: dict[str, Callable[[Mapping[str, Any]], np.ndarray]] = {}


def register(name: str):
    def _wrap(function):
        if name in _REGISTRY:
            raise RuntimeError(f"generator {name!r} is already registered")
        _REGISTRY[name] = function
        return function

    return _wrap


def _require(parameters: Mapping[str, Any], name: str) -> Any:
    if name not in parameters:
        raise GeneratorError(f"generator parameter {name!r} is missing")
    return parameters[name]


@register("rope_coefficients_v1")
def rope_coefficients_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """Rotary coefficient rows: ``[maximum_position, 2 * head_dim]`` binary32.

    Each row holds the cosine block for one position followed by the sine block,
    each ``head_dim`` wide, so the pair for channel ``i`` is ``row[i]`` and
    ``row[head_dim + i]``. Angles are computed in binary64 and rounded once to
    binary32, which is what makes the table reproducible across machines: the
    intermediate ``position / theta ** (2i / head_dim)`` is otherwise sensitive
    to the order the power is evaluated in.
    """
    head_dim = int(_require(parameters, "head_dim"))
    maximum_position = int(_require(parameters, "maximum_position"))
    theta = float(_require(parameters, "theta"))
    if head_dim <= 0 or head_dim % 2:
        raise GeneratorError(f"head_dim {head_dim} must be positive and even")
    if maximum_position <= 0:
        raise GeneratorError("maximum_position must be positive")
    half = head_dim // 2
    inverse = np.array(
        [1.0 / (theta ** ((2.0 * i) / head_dim)) for i in range(half)],
        dtype=np.float64,
    )
    positions = np.arange(maximum_position, dtype=np.float64)
    angles = positions[:, None] * inverse[None, :]
    cos = np.cos(angles)
    sin = np.sin(angles)
    # Qwen3 duplicates each half-rotation across the two channel halves.
    table = np.empty((maximum_position, 2 * head_dim), dtype=np.float64)
    table[:, :half] = cos
    table[:, half:head_dim] = cos
    table[:, head_dim : head_dim + half] = sin
    table[:, head_dim + half :] = sin
    return np.ascontiguousarray(table, dtype=np.float32)


@register("causal_window_indices_v1")
def causal_window_indices_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """Sliding-window index rows, ascending, tail-padded with ``0xffffffff``."""
    window = int(_require(parameters, "window"))
    maximum_position = int(_require(parameters, "maximum_position"))
    if window <= 0:
        raise GeneratorError("window must be positive")
    table = np.full((maximum_position, window), 0xFFFFFFFF, dtype=np.uint32)
    for position in range(maximum_position):
        low = max(0, position - window + 1)
        span = position - low + 1
        table[position, :span] = np.arange(low, position + 1, dtype=np.uint32)
    return table


@register("arange_u32_v1")
def arange_u32_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """A plain ascending index vector, used for enumerations."""
    count = int(_require(parameters, "count"))
    if count <= 0:
        raise GeneratorError("count must be positive")
    return np.arange(count, dtype=np.uint32)


def generate(name: str, parameters: Mapping[str, Any]) -> np.ndarray:
    try:
        function = _REGISTRY[name]
    except KeyError:
        raise GeneratorError(
            f"unknown generator {name!r}; a deployment may not name a generator "
            "the device does not implement, and no fallback may stand in for one"
        ) from None
    return function(parameters)


def generate_bytes(name: str, parameters: Mapping[str, Any]) -> bytes:
    return generate(name, parameters).tobytes()


def digest_of(name: str, parameters: Mapping[str, Any]) -> str:
    """The digest a deployment must bind for this generator and parameters."""
    return sha256_hex(generate_bytes(name, parameters))


def registered() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
