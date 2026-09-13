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


@register("floor_div_indices_v1")
def floor_div_indices_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """``position // divisor`` for every position in ``range(count)``.

    The table turns an absolute-position index into its completed-group ordinal.
    Both parameters are deliberately strict: generated-object parameters come
    from authenticated JSON, so accepting booleans, strings, fractional values,
    or ignored fields would give the same generated bytes multiple declarations.
    ``count`` may cover the complete U32 position domain, while ``divisor`` is a
    positive U32 value.  The output is always a contiguous rank-one U32 array,
    which makes :func:`digest_of` bind the same bytes as every other generator.
    """
    expected = {"count", "divisor"}
    unexpected = sorted(str(name) for name in parameters if name not in expected)
    if unexpected:
        raise GeneratorError(
            "floor_div_indices_v1 has unexpected parameter(s): "
            + ", ".join(repr(name) for name in unexpected)
        )

    count = _require(parameters, "count")
    divisor = _require(parameters, "divisor")
    if type(count) is not int or not 1 <= count <= (1 << 32):
        raise GeneratorError(
            "count must be an integer in the U32 position-domain range "
            "1..4294967296"
        )
    if type(divisor) is not int or not 1 <= divisor <= 0xFFFFFFFF:
        raise GeneratorError(
            "divisor must be an integer in the unsigned 32-bit range "
            "1..4294967295"
        )

    positions = np.arange(count, dtype=np.uint32)
    return np.ascontiguousarray(positions // np.uint32(divisor), dtype=np.uint32)


@register("arange_u32_v1")
def arange_u32_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """A plain ascending index vector, used for enumerations."""
    count = int(_require(parameters, "count"))
    if count <= 0:
        raise GeneratorError("count must be positive")
    return np.arange(count, dtype=np.uint32)


@register("constant_u32_v1")
def constant_u32_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """``count`` copies of one unsigned parameter.

    Amendment A19 gives ``ROUTE.INDEX_TOPK`` a compression ratio, and an
    operator can only be handed one through an input view.  The ratio is a
    pinned property of the layer, not of the request, so the view reads a
    mask-programmed constant -- declared here rather than smuggled in as the
    extent of some operand that happens to be that long.
    """
    value = int(_require(parameters, "value"))
    count = int(parameters.get("count", 1))
    if count <= 0:
        raise GeneratorError("count must be positive")
    if not 0 <= value <= 0xFFFFFFFF:
        raise GeneratorError("value must be an unsigned 32-bit integer")
    return np.full(count, value, dtype=np.uint32)


@register("constant_binary32_v1")
def constant_binary32_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """``count`` copies of one binary32 value, stated as its bit pattern.

    The companion to :func:`constant_u32_v1` for a *floating-point* deployment
    constant.  The parameter is a bit pattern rather than a decimal literal so
    that the declared constant and the bytes the device materialises are the
    same object: a decimal round-trip through JSON is exact for the values in
    use, but "the binary32 whose encoding is ``0x3f800000``" is what a frozen
    generation configuration actually states, and it cannot drift.

    DeepSeek's sampling temperature is the first user.  ABI 3.0's submission
    record has no temperature field, so a temperature read out of a *request*
    input is read out of an object no request can write -- it stays zero, and
    the logits are multiplied by zero.  It is a deployment constant.
    """
    bits = int(_require(parameters, "bits"))
    count = int(parameters.get("count", 1))
    if count <= 0:
        raise GeneratorError("count must be positive")
    if not 0 <= bits <= 0xFFFFFFFF:
        raise GeneratorError("bits must be an unsigned 32-bit pattern")
    value = np.array([bits], dtype=np.uint32).view(np.float32)[0]
    if not np.isfinite(value):
        raise GeneratorError(
            f"bit pattern {bits:#010x} is not a finite binary32 value"
        )
    return np.full(count, value, dtype=np.float32)


# ---------------------------------------------------------------------------
# Engram tables (AM-E10)
# ---------------------------------------------------------------------------
#: Deterministic primality for the Engram bucket search.
#:
#: ``inference/engram.py`` draws its bucket moduli with ``sympy.isprime``.  A
#: device-side generator may not depend on a symbolic-algebra package, and it
#: must not depend on a probabilistic answer either, so the test below is the
#: Miller-Rabin witness set that is *proved* deterministic for every integer
#: under 3.3e24 -- far above the released bucket base -- and the two published
#: row counts are what check it: the 24 moduli a layer draws sum to exactly the
#: released ``engram_num_embeddings`` entry for that layer, so a wrong answer
#: anywhere in the search changes a number this repository did not choose.
_MILLER_RABIN_WITNESSES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def _is_prime(candidate: int) -> bool:
    if candidate < 2:
        return False
    for witness in _MILLER_RABIN_WITNESSES:
        if candidate % witness == 0:
            return candidate == witness
    exponent, remainder = 0, candidate - 1
    while remainder % 2 == 0:
        remainder //= 2
        exponent += 1
    for witness in _MILLER_RABIN_WITNESSES:
        value = pow(witness, remainder, candidate)
        if value in (1, candidate - 1):
            continue
        for _ in range(exponent - 1):
            value = value * value % candidate
            if value == candidate - 1:
                break
        else:
            return False
    return True


def _next_prime(start: int, seen: set[int]) -> int:
    candidate = start + 1
    while not _is_prime(candidate) or candidate in seen:
        candidate += 1
    return candidate


@register("engram_hash_multipliers_v1")
def engram_hash_multipliers_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """One n-gram hash multiplier per lookback, for one Engram layer.

    ``compute_hash_multipliers`` draws them from a per-layer generator seeded
    ``10007 * layer_id``, keeps them odd, and bounds them so that
    ``token_id * multiplier`` cannot reach the int64 window -- which is why the
    compressed vocabulary is a parameter and not a decoration: the bound is
    derived from it, so a table hashed under the wrong vocabulary is a different
    table.  The values are an operand of ``DMA.NGRAM_HASH``, never a constant of
    the machine.
    """
    layer_id = int(_require(parameters, "layer_id"))
    count = int(_require(parameters, "count"))
    vocabulary = int(_require(parameters, "compressed_vocabulary"))
    if layer_id < 0:
        raise GeneratorError("layer_id must be non-negative")
    if count < 2:
        raise GeneratorError("count is the maximum n-gram size and is at least 2")
    if vocabulary < 1:
        raise GeneratorError("compressed_vocabulary must be positive")
    bound = max(1, (int(np.iinfo(np.int64).max) // vocabulary) // 2)
    generator = np.random.default_rng(10007 * layer_id)
    values = generator.integers(low=0, high=bound, size=(count,), dtype=np.int64)
    return np.ascontiguousarray(values * 2 + 1, dtype=np.uint64)


@register("engram_hash_columns_v1")
def engram_hash_columns_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """One Engram layer's column table: ``[2, orders, heads]`` unsigned 64-bit.

    Plane 0 is the prime bucket modulus of each (n-gram order, hash head) pair
    and plane 1 is that pair's base row, the prefix sum of the earlier columns'
    moduli.  ``EngramLayout.from_args`` draws the primes in layer order from one
    shared set, so a layer's table depends on every layer drawn before it:
    ``layer_ids`` is therefore the whole released list and ``layer_id`` says
    which of them this table belongs to.  Nothing here is a model constant --
    the base, the order count and the head count are all parameters -- and the
    result is checkable against a released number, because the moduli of one
    layer sum to its ``engram_num_embeddings`` row count.
    """
    layer_ids = [int(value) for value in _require(parameters, "layer_ids")]
    layer_id = int(_require(parameters, "layer_id"))
    orders = int(_require(parameters, "orders"))
    heads = int(_require(parameters, "heads"))
    base = int(_require(parameters, "bucket_base"))
    if layer_id not in layer_ids:
        raise GeneratorError(f"layer {layer_id} is not one of {layer_ids}")
    if orders < 1 or heads < 1:
        raise GeneratorError("orders and heads must be positive")
    if base < 2:
        raise GeneratorError("bucket_base must be at least two")
    seen: set[int] = set()
    table: np.ndarray | None = None
    for drawn in layer_ids:
        primes: list[int] = []
        for _ in range(orders):
            current = base - 1
            for _ in range(heads):
                current = _next_prime(current, seen)
                seen.add(current)
                primes.append(current)
        if drawn != layer_id:
            continue
        offsets = np.cumsum([0, *primes[:-1]], dtype=np.uint64)
        table = np.stack(
            (
                np.asarray(primes, dtype=np.uint64).reshape(orders, heads),
                offsets.reshape(orders, heads),
            )
        )
    assert table is not None  # layer_id is in layer_ids, checked above
    return np.ascontiguousarray(table, dtype=np.uint64)


@register("engram_compressed_token_map_v1")
def engram_compressed_token_map_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """The compressed token id of every token id, per ``build_compressed_token_map``.

    N-grams are hashed over compressed ids, so tokens that normalise alike share
    a row.  The map is a function of the released tokenizer and of nothing else,
    and it is not in the checkpoint: ``NgramHashState`` builds it at load and
    asserts its size against ``engram_compressed_vocab_size``.  This derives it
    the same way and makes the same assertion, which is what lets a graph
    *declare* the table rather than carry an unbound one -- the released
    tokenizer is pinned by digest in the checkpoint source contract, and this
    refuses a tokenizer whose bytes differ from the digest it is given.
    """
    repository = str(_require(parameters, "repository"))
    revision = str(_require(parameters, "revision"))
    digest = str(_require(parameters, "tokenizer_sha256"))
    filename = str(parameters.get("tokenizer_file", "tokenizer.json"))
    vocabulary = int(_require(parameters, "vocabulary"))
    compressed = int(_require(parameters, "compressed_vocabulary"))
    try:
        from huggingface_hub import try_to_load_from_cache
        from tokenizers import Regex, Tokenizer, normalizers
    except ImportError as exc:  # pragma: no cover - environment without them
        raise GeneratorError(
            f"the compressed token map is derived from the released {filename}, "
            f"which needs huggingface_hub and tokenizers: {exc}"
        ) from exc
    path = try_to_load_from_cache(repository, filename, revision=revision)
    if not isinstance(path, str):
        raise GeneratorError(
            f"{repository} {filename} at revision {revision} is not in the local "
            "cache; the compressed token map is derived from the released "
            "tokenizer and may not be guessed"
        )
    payload = open(path, "rb").read()
    observed = sha256_hex(payload)
    if observed != digest:
        raise GeneratorError(
            f"{filename} has sha256 {observed} against the declared {digest}"
        )
    backend = Tokenizer.from_file(path)
    if backend.get_vocab_size(with_added_tokens=True) != vocabulary:
        raise GeneratorError(
            f"{filename} holds {backend.get_vocab_size(with_added_tokens=True)} "
            f"tokens against the declared {vocabulary}"
        )
    # A private-use character, so a token that is exactly one space survives
    # Strip() instead of collapsing to the empty string, exactly as the released
    # build_compressed_token_map does.
    sentinel = "\ue000"
    normalizer = normalizers.Sequence(
        [
            normalizers.NFKC(),
            normalizers.NFD(),
            normalizers.StripAccents(),
            normalizers.Lowercase(),
            normalizers.Replace(Regex(r"[ \t\r\n]+"), " "),
            normalizers.Replace(Regex(r"^ $"), sentinel),
            normalizers.Strip(),
            normalizers.Replace(sentinel, " "),
        ]
    )
    key_to_new: dict[str, int] = {}
    lookup = np.zeros(vocabulary, dtype=np.uint32)
    for token_id in range(vocabulary):
        text = backend.decode([token_id], skip_special_tokens=False)
        if "\ufffd" in text:
            # A partial UTF-8 byte token: nothing to normalise, so it is keyed by
            # its raw form.
            key = backend.id_to_token(token_id)
        else:
            normalized = normalizer.normalize_str(text)
            key = normalized if normalized else text
        new_id = key_to_new.get(key)
        if new_id is None:
            new_id = len(key_to_new)
            key_to_new[key] = new_id
        lookup[token_id] = new_id
    if len(key_to_new) != compressed:
        raise GeneratorError(
            f"the released tokenizer compresses to {len(key_to_new)} ids against "
            f"the declared {compressed}; every hash multiplier is derived from "
            "that size, so a disagreement rehashes the whole table"
        )
    return lookup


@register("one_hot_binary32_v1")
def one_hot_binary32_v1(parameters: Mapping[str, Any]) -> np.ndarray:
    """``count`` binary32 values, one at ``index`` and zero elsewhere.

    DeepSeek-V4.1's first block collapses its hyper-connection copies with
    ``make_identity_pre_mix``, a one-hot weighting of the first copy.  Every
    later collapse reads coefficients a previous sublayer computed, so this is
    the one coefficient vector that is a deployment constant rather than an
    activation -- and a ``constant_binary32_v1`` fill cannot state it, because
    the whole content of the vector is that its entries differ.
    """
    count = int(_require(parameters, "count"))
    index = int(_require(parameters, "index"))
    if count <= 0:
        raise GeneratorError("count must be positive")
    if not 0 <= index < count:
        raise GeneratorError(f"index {index} is outside 0..{count - 1}")
    out = np.zeros(count, dtype=np.float32)
    out[index] = 1.0
    return out


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
