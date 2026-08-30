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


@register("deepseek_rope_coefficients_v1")
def deepseek_rope_coefficients_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """Partial rotary coefficient rows: ``[maximum_position, 2 * rotary_width]``.

    Two things separate this table from ``rope_coefficients_v1``.

    *The rotation is partial and its pairing is adjacent.*  DeepSeek rotates only
    the final ``rotary_width`` channels of a head, and it pairs them as
    ``(2p, 2p + 1)`` complex components rather than as ``(i, i + half)``.  The
    row therefore spans the *rotary* width, not the head width, and pair ``p``'s
    cosine appears at both ``2p`` and ``2p + 1`` so that the row reads
    channel-for-channel against the block it rotates.  The layout is still the
    frozen one ``TA-ABI3-OPCONV-1`` section 3 names: cosine block then sine
    block.

    *The frequencies may be YaRN-interpolated.*  ``position_scaling`` is
    ``"none"`` or ``"yarn"``; the YaRN branch needs ``factor``, ``beta_fast``,
    ``beta_slow`` and ``original_max_position``, and reproduces the released
    interpolation with binary32 operations in the released order -- one
    division, one ramp, two products and one sum -- because the interpolation is
    part of the model's numerics rather than a convenience.

    Reproducibility.  The 32 angular frequencies are built from correctly
    rounded binary32 roots and binary32 arithmetic, so they are bit-identical on
    any machine.  The angle is one binary32 product of an exactly representable
    position with a frozen frequency.  Only the sine and cosine are evaluated in
    binary64 and rounded once to binary32, the same boundary
    ``rope_coefficients_v1`` uses; ``tests/sim/test_deepseek_rope_coefficients.py``
    checks that boundary against the correctly rounded scalar reference over
    both profiles and finds no disagreement.
    """
    rotary_width = int(_require(parameters, "rotary_width"))
    maximum_position = int(_require(parameters, "maximum_position"))
    theta = float(_require(parameters, "theta"))
    scaling = str(_require(parameters, "position_scaling"))
    if rotary_width <= 0 or rotary_width % 2:
        raise GeneratorError(
            f"rotary_width {rotary_width} must be positive and even"
        )
    if maximum_position <= 0:
        raise GeneratorError("maximum_position must be positive")
    if theta <= 1.0:
        raise GeneratorError(f"theta {theta} must exceed one")
    if scaling not in {"none", "yarn"}:
        raise GeneratorError(
            f"position_scaling {scaling!r} is neither 'none' nor 'yarn'"
        )
    pairs = rotary_width // 2
    frequencies = _rope_frequencies_binary32(
        parameters, rotary_width=rotary_width, theta=theta, scaling=scaling
    )
    positions = np.arange(maximum_position, dtype=np.float32)
    if maximum_position > (1 << 24):
        # Beyond 2**24 a position is no longer exactly representable in
        # binary32, so the angle would depend on which rounding of the position
        # a host chose.  Refuse rather than emit a table that is reproducible
        # only by accident.
        raise GeneratorError(
            "maximum_position exceeds the exactly representable binary32 range"
        )
    angles = positions[:, None] * frequencies[None, :]
    wide = np.asarray(angles, dtype=np.float64)
    cos = np.asarray(np.cos(wide), dtype=np.float32)
    sin = np.asarray(np.sin(wide), dtype=np.float32)
    table = np.empty((maximum_position, 2 * rotary_width), dtype=np.float32)
    table[:, 0:rotary_width:2] = cos
    table[:, 1:rotary_width:2] = cos
    table[:, rotary_width::2] = sin
    table[:, rotary_width + 1 :: 2] = sin
    assert table.shape[1] == 2 * rotary_width and pairs == cos.shape[1]
    return np.ascontiguousarray(table, dtype=np.float32)


def _rope_frequencies_binary32(
    parameters: Mapping[str, Any],
    *,
    rotary_width: int,
    theta: float,
    scaling: str,
) -> np.ndarray:
    """The ``rotary_width // 2`` angular frequencies, in binary32.

    ``1 / theta ** (2 i / rotary_width)`` is evaluated as a correctly rounded
    binary32 root followed by one binary32 division, which is what makes the
    frequency independent of the host's ``pow``.  The YaRN branch then follows
    the released operation order exactly.
    """
    from runtime.reference.formats import binary32_divide
    from runtime.reference.rope import _correctly_rounded_root_power

    pairs = rotary_width // 2
    base = int(theta)
    if float(base) != theta:
        raise GeneratorError(f"theta {theta} is not an exact integer base")
    codes = [
        binary32_divide(0x3F800000, _correctly_rounded_root_power(base, index))
        for index in range(pairs)
    ]
    frequencies = np.asarray(codes, dtype=np.uint32).view(np.float32).copy()
    if scaling == "none":
        return frequencies
    factor = np.float32(float(_require(parameters, "factor")))
    beta_fast = float(_require(parameters, "beta_fast"))
    beta_slow = float(_require(parameters, "beta_slow"))
    original = int(_require(parameters, "original_max_position"))
    if factor <= 0 or original <= 0:
        raise GeneratorError("YaRN factor and original_max_position must be positive")

    def correction_dim(rotations: float) -> float:
        return (
            rotary_width
            * math.log(original / (rotations * 2.0 * math.pi))
            / (2.0 * math.log(base))
        )

    low = max(int(math.floor(correction_dim(beta_fast))), 0)
    high = min(int(math.ceil(correction_dim(beta_slow))), rotary_width - 1)
    if low >= high:
        raise GeneratorError(
            f"YaRN correction range [{low}, {high}] is empty for these parameters"
        )
    index = np.arange(pairs, dtype=np.float32)
    ramp = np.clip(
        (index - np.float32(low)) / np.float32(high - low), np.float32(0), np.float32(1)
    ).astype(np.float32)
    smooth = (np.float32(1) - ramp).astype(np.float32)
    one_minus_smooth = (np.float32(1) - smooth).astype(np.float32)
    interpolated = ((frequencies / factor).astype(np.float32) * one_minus_smooth).astype(
        np.float32
    )
    original_term = (frequencies * smooth).astype(np.float32)
    return (interpolated + original_term).astype(np.float32)


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


@register("ring_indices_v1")
def ring_indices_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """``position mod modulus``: the row a sliding-window cache writes.

    A sliding-window KV cache holds the last ``modulus`` positions in a ring, so
    absolute position ``p`` lives at row ``p % modulus`` -- which is what the
    released model does in both directions, writing ``start_pos % window`` on a
    decode step and rotating the prefill's final window into the same alignment.
    A tensor view can offset an index vector by a runtime symbol but cannot
    reduce one, so the reduction is in the table: reading this table at
    ``POSITION_START + i`` yields ``(POSITION_START + i) % modulus`` with no
    arithmetic in the descriptor.
    """
    count = int(_require(parameters, "count"))
    modulus = int(_require(parameters, "modulus"))
    if count <= 0:
        raise GeneratorError("count must be positive")
    if modulus <= 0:
        raise GeneratorError("modulus must be positive")
    return (np.arange(count, dtype=np.uint32) % np.uint32(modulus)).astype(np.uint32)


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
