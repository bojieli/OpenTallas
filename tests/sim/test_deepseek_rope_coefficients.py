"""The DeepSeek rotary table and the partial rotation that reads it.

Two things need proving and they are different things.

*The generator is reproducible.*  A generated object's authentication is the
SHA-256 of its own output, so a generator that drifts by one bit relocks the
whole deployment.  ``deepseek_rope_coefficients_v1`` builds its 32 angular
frequencies from correctly rounded binary32 roots and binary32 arithmetic and
takes only the sine and cosine through binary64, so the frequencies are checked
against the qualified scalar reference exactly and the transcendental boundary
is checked against it over a sample of positions spanning the pinned table.

*The rotation is the released one.*  ``runtime/reference/rope.py`` is the
bit-exact scalar oracle for ``ROPE_APPLY`` and ``ROPE_INVERSE``: it rotates the
final 64 channels as adjacent complex pairs, keeps the four products and two
sums in binary32, and converts to BF16 once.  The engine's data-bearing form is
compared against it at every official call-site width, in both directions, on
both profiles, and on hostile inputs -- signed zeros, subnormals and the BF16
values either side of one.

Neither check reads the engine's own arithmetic to decide what the answer is.
"""

from __future__ import annotations

import numpy as np
import pytest

from runtime.reference.rope import (
    BASE_ROPE_PROFILE,
    COMPRESSED_YARN_ROPE_PROFILE,
    ROPE_DIMENSION,
    rope_apply_bf16,
    rope_frequency_binary32_codes,
    rope_inverse_bf16,
    rope_phasor_binary32_codes,
)
from runtime.sim.engines.vector import deepseek_rope_binary32
from runtime.sim.formats import widen_bf16
from runtime.sim.generators import (
    GeneratorError,
    _rope_frequencies_binary32,
    digest_of,
    generate,
    generate_bytes,
    registered,
)

#: The two rotary profiles the released model uses, as this graph declares them.
BASE = {
    "rotary_width": ROPE_DIMENSION,
    "maximum_position": 512,
    "theta": 10_000.0,
    "position_scaling": "none",
}
YARN = {
    "rotary_width": ROPE_DIMENSION,
    "maximum_position": 512,
    "theta": 160_000.0,
    "position_scaling": "yarn",
    "factor": 16.0,
    "beta_fast": 32,
    "beta_slow": 1,
    "original_max_position": 65_536,
}
PROFILES = ((BASE, BASE_ROPE_PROFILE), (YARN, COMPRESSED_YARN_ROPE_PROFILE))


def test_the_generator_is_registered() -> None:
    assert "deepseek_rope_coefficients_v1" in registered()


@pytest.mark.parametrize("parameters,profile", PROFILES)
def test_frequencies_match_the_scalar_reference_exactly(parameters, profile) -> None:
    """The 32 angular frequencies, YaRN interpolation included, are exact.

    Nothing here is approximate: the root is correctly rounded by an integer
    binary search and every subsequent operation is one binary32 step, so a
    disagreement with the reference would be a disagreement about the model,
    not about floating point.
    """
    produced = _rope_frequencies_binary32(
        parameters,
        rotary_width=int(parameters["rotary_width"]),
        theta=float(parameters["theta"]),
        scaling=str(parameters["position_scaling"]),
    ).view(np.uint32)
    expected = np.asarray(rope_frequency_binary32_codes(profile=profile), np.uint32)
    np.testing.assert_array_equal(produced, expected)


@pytest.mark.parametrize("parameters,profile", PROFILES)
def test_table_rows_match_the_correctly_rounded_phasors(parameters, profile) -> None:
    """The binary64 sine and cosine round to the correctly rounded binary32.

    The reference evaluates both from exact rational intervals and refuses to
    answer until the interval rounds to a single binary32 code, so it is the
    correctly rounded value by construction.  A sample rather than the whole
    table, because the reference costs milliseconds per angle -- but a sample
    that spans the pinned range rather than its first few rows.
    """
    table = generate("deepseek_rope_coefficients_v1", parameters)
    width = int(parameters["rotary_width"])
    assert table.shape == (int(parameters["maximum_position"]), 2 * width)
    assert table.dtype == np.float32
    codes = table.view(np.uint32)
    positions = [0, 1, 2, 3, 17, 104, 255, 256, 511]
    for position in positions:
        expected = rope_phasor_binary32_codes(position, profile=profile)
        for pair, (cosine, sine) in enumerate(expected):
            # Pair ``p``'s coefficient sits at both channels it multiplies.
            assert int(codes[position, 2 * pair]) == cosine
            assert int(codes[position, 2 * pair + 1]) == cosine
            assert int(codes[position, width + 2 * pair]) == sine
            assert int(codes[position, width + 2 * pair + 1]) == sine


def test_the_generator_is_a_pure_function_of_its_parameters() -> None:
    """Same parameters, same bytes, same digest -- twice, in one process."""
    first = generate_bytes("deepseek_rope_coefficients_v1", BASE)
    second = generate_bytes("deepseek_rope_coefficients_v1", dict(BASE))
    assert first == second
    assert digest_of("deepseek_rope_coefficients_v1", BASE) == digest_of(
        "deepseek_rope_coefficients_v1", dict(BASE)
    )
    # And a different profile is a different table, not the same one renamed.
    assert digest_of("deepseek_rope_coefficients_v1", BASE) != digest_of(
        "deepseek_rope_coefficients_v1", YARN
    )


@pytest.mark.parametrize(
    "override,message",
    (
        ({"rotary_width": 63}, "positive and even"),
        ({"maximum_position": 0}, "must be positive"),
        ({"theta": 1.0}, "must exceed one"),
        ({"position_scaling": "linear"}, "neither"),
    ),
)
def test_the_generator_refuses_a_parameter_it_cannot_honour(override, message) -> None:
    parameters = {**BASE, **override}
    with pytest.raises(GeneratorError) as raised:
        generate("deepseek_rope_coefficients_v1", parameters)
    assert message in str(raised.value)


def test_yarn_requires_its_own_parameters() -> None:
    parameters = {k: v for k, v in YARN.items() if k != "beta_fast"}
    with pytest.raises(GeneratorError):
        generate("deepseek_rope_coefficients_v1", parameters)


def _random_bf16(rng: np.random.Generator, shape) -> np.ndarray:
    exponent = rng.integers(110, 140, size=shape).astype(np.uint32)
    mantissa = rng.integers(0, 128, size=shape).astype(np.uint32)
    sign = rng.integers(0, 2, size=shape).astype(np.uint32)
    return ((sign << 15) | (exponent << 7) | mantissa).astype(np.uint16)


def _reference_rows(
    values: np.ndarray, start: int, *, profile: str, inverse: bool
) -> np.ndarray:
    rows = tuple(tuple(int(code) for code in row) for row in values)
    apply = rope_inverse_bf16 if inverse else rope_apply_bf16
    return np.asarray(apply((rows,), start, profile=profile)[0], dtype=np.uint16)


@pytest.mark.parametrize("parameters,profile", PROFILES)
@pytest.mark.parametrize("width", (64, 128, 512))
@pytest.mark.parametrize("inverse", (False, True))
def test_the_partial_rotation_matches_the_scalar_reference(
    parameters, profile, width, inverse
) -> None:
    """Every official call-site width, both directions, both profiles.

    The reference rotates the final 64 channels and preserves the rest; this
    checks the preserved prefix as well as the rotated suffix, because carrying
    the prefix through the same operator -- rather than by a separate movement
    -- is the whole reason the rotation can be partial at all.
    """
    rng = np.random.default_rng(4093)
    start, rows = 13, 9
    values = _random_bf16(rng, (rows, width))
    table = generate("deepseek_rope_coefficients_v1", parameters)
    produced = deepseek_rope_binary32(
        values,
        table[start : start + rows],
        rotary_width=ROPE_DIMENSION,
        inverse=inverse,
    )
    expected = _reference_rows(values, start, profile=profile, inverse=inverse)
    np.testing.assert_array_equal(produced, expected)
    # The prefix is moved, not recomputed.
    np.testing.assert_array_equal(
        produced[:, : width - ROPE_DIMENSION], values[:, : width - ROPE_DIMENSION]
    )


@pytest.mark.parametrize("inverse", (False, True))
def test_the_partial_rotation_handles_zeros_and_subnormals(inverse) -> None:
    """Signed zero, subnormals and the codes either side of one.

    The reference canonicalises arithmetic zero to positive and preserves
    subnormals; a rotation that lost either would disagree here and nowhere in
    a random sample.
    """
    hostile = np.array(
        [0x0000, 0x8000, 0x0001, 0x8001, 0x007F, 0x3F80, 0xBF80, 0x0080, 0x4780, 0xC780],
        dtype=np.uint16,
    )
    rows, width = len(hostile), 512
    values = np.stack(
        [hostile[(np.arange(width) + index) % len(hostile)] for index in range(rows)]
    ).astype(np.uint16)
    table = generate("deepseek_rope_coefficients_v1", YARN)
    produced = deepseek_rope_binary32(
        values, table[:rows], rotary_width=ROPE_DIMENSION, inverse=inverse
    )
    expected = _reference_rows(
        values, 0, profile=COMPRESSED_YARN_ROPE_PROFILE, inverse=inverse
    )
    np.testing.assert_array_equal(produced, expected)


def test_the_inverse_rotation_undoes_the_forward_one() -> None:
    """A property the reference cannot state: the two directions are inverse.

    Not bit-exact, and the tolerance says why rather than being tuned until it
    passed.  A pair is rotated in binary32 and rounded to BF16 twice, and the
    rotation mixes the two components, so each component comes back to within a
    couple of BF16 ulps *of the pair's magnitude* -- not of its own, which
    cancellation can make arbitrarily small.
    """
    rng = np.random.default_rng(77)
    values = _random_bf16(rng, (6, 512))
    table = generate("deepseek_rope_coefficients_v1", BASE)
    rows = table[3:9]
    forward = deepseek_rope_binary32(
        values, rows, rotary_width=ROPE_DIMENSION, inverse=False
    )
    restored = deepseek_rope_binary32(
        forward, rows, rotary_width=ROPE_DIMENSION, inverse=True
    )
    original = widen_bf16(values)
    returned = widen_bf16(restored)
    suffix = slice(512 - ROPE_DIMENSION, 512)
    pairs = np.abs(original[:, suffix]).reshape(6, ROPE_DIMENSION // 2, 2)
    magnitude = np.repeat(pairs.max(axis=2), 2, axis=1)
    difference = np.abs(returned[:, suffix] - original[:, suffix])
    assert np.all(difference <= magnitude / 64.0)
    # The preserved prefix comes back untouched, not merely close.
    np.testing.assert_array_equal(restored[:, :suffix.start], values[:, :suffix.start])
