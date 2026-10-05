from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from functools import lru_cache
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import random
import struct
from typing import Any

import pytest

import runtime.reference.rope as rope_module
from runtime.reference.rope import (
    BASE_ROPE_PROFILE,
    BASE_ROPE_THETA,
    COMPRESSED_YARN_ROPE_PROFILE,
    COMPRESSED_ROPE_THETA,
    EXCLUDED_CLAIMS,
    GENERATE_SOURCE_SHA256,
    INFERENCE_CONFIG_SHA256,
    MAX_POSITION,
    MAX_SEQUENCE_LENGTH,
    MODEL_SOURCE_SHA256,
    OFFICIAL_REVISION,
    ROPE_COMPLEX_PAIRS,
    ROPE_DIMENSION,
    ROPE_NUMERIC_PROFILE,
    SUPPORTED_HEAD_WIDTHS,
    SUPPORTED_POSITION_STRIDES,
    YARN_BETA_FAST,
    YARN_BETA_SLOW,
    YARN_CORRECTION_HIGH,
    YARN_CORRECTION_LOW,
    YARN_FACTOR,
    YARN_ORIGINAL_SEQUENCE_LENGTH,
    RopeCounters,
    RopeReferenceError,
    RopeResult,
    apply_rotary_bf16,
    apply_rotary_bf16_result,
    rope_apply_bf16,
    rope_frequency_binary32_codes,
    rope_inverse_bf16,
    rope_phasor_binary32_codes,
)


class _ListSubclass(list):
    pass


_SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_SNAPSHOT"
_SNAPSHOT = Path(
    os.environ.get(
        _SNAPSHOT_ENV,
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / OFFICIAL_REVISION,
    )
)
_MODEL_SOURCE = _SNAPSHOT / "inference/model.py"
_INFERENCE_CONFIG = _SNAPSHOT / "inference/config.json"
_GENERATE_SOURCE = _SNAPSHOT / "inference/generate.py"

_BASE_FREQUENCY_SHA256 = (
    "734f9e6b629f7baccc4de81b7e8d2982035ee1b81f73f158e7d33a4dcf13fa0e"
)
_COMPRESSED_FREQUENCY_SHA256 = (
    "1f132e9c03f43671d62cb9f1a6ce7cd2941717a7be0676b93aa5a049ca0991b8"
)
_PHASOR_SHA256 = {
    (BASE_ROPE_PROFILE, 0): (
        "b6ec543f7e2f88ea31470cab35f545f125c92013ecca4dbaea43db67be86a856"
    ),
    (BASE_ROPE_PROFILE, 1): (
        "c6b5e399d5475db9335f36c09008cf21f8097c249d6e008d2b58d59e7f1b9f5c"
    ),
    (BASE_ROPE_PROFILE, 127): (
        "77663fadd6395fb40bf199cdc6fadc4a3609591a46837d671e5b63eb37bec391"
    ),
    (BASE_ROPE_PROFILE, 4095): (
        "e7cec1cd92fc33b49b843d9e9fbf4c67083730f16fd553ab8b73a9ec15f680c9"
    ),
    (BASE_ROPE_PROFILE, 65535): (
        "558cdce4f6fb37c5868178ca30cc681e68c9f3b974302fe36406a37c36fc7b4d"
    ),
    (COMPRESSED_YARN_ROPE_PROFILE, 0): (
        "b6ec543f7e2f88ea31470cab35f545f125c92013ecca4dbaea43db67be86a856"
    ),
    (COMPRESSED_YARN_ROPE_PROFILE, 1): (
        "40df0c6f80b63fb49e04cc5d65b0b32c1b5a6e72ae842b05b5bcfe7c49e0661b"
    ),
    (COMPRESSED_YARN_ROPE_PROFILE, 127): (
        "de78c7be9935f93cdde797ff3c227a91f6734341b1f9e86eafc5ae0700bc4cee"
    ),
    (COMPRESSED_YARN_ROPE_PROFILE, 4095): (
        "b1bdb187f2dc9a0dc59d7e9f982ecd75cb8a6f932f671017209df02e8ab931ed"
    ),
    (COMPRESSED_YARN_ROPE_PROFILE, 65535): (
        "086448cdd7aadc649955abf0a49bcc0783270747faf44cba16e948f691422bcf"
    ),
}


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent)
    return Fraction(1, 1 << -exponent)


def _round_ties_even(value: Fraction) -> int:
    assert value >= 0
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (doubled == value.denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    return exponent


def _decode_binary32_fraction(code: int) -> Fraction:
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    assert exponent != 0xFF
    significand = fraction if exponent == 0 else (1 << 23) | fraction
    power = -149 if exponent == 0 else exponent - 150
    value = Fraction(significand) * _pow2(power)
    return -value if code & 0x80000000 else value


def _encode_binary32_fraction(value: Fraction) -> int:
    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < _pow2(-126):
        significand = _round_ties_even(magnitude / _pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | (1 << 23)

    exponent = _floor_log2(magnitude)
    significand = _round_ties_even(magnitude / _pow2(exponent - 23))
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise OverflowError("binary32 overflow")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def _decode_bf16_fraction(code: int) -> Fraction:
    exponent = (code >> 7) & 0xFF
    fraction = code & 0x7F
    assert exponent != 0xFF
    significand = fraction if exponent == 0 else (1 << 7) | fraction
    power = -133 if exponent == 0 else exponent - 134
    value = Fraction(significand) * _pow2(power)
    return -value if code & 0x8000 else value


def _binary32_to_bf16_rne(code: int) -> int:
    assert code & 0x7F800000 != 0x7F800000
    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    if upper & 0x7F80 == 0x7F80:
        raise OverflowError("BF16 saturation")
    return 0 if upper & 0x7FFF == 0 else upper


def _negate_binary32(code: int) -> int:
    return 0 if code & 0x7FFFFFFF == 0 else code ^ 0x80000000


def _f32_add(left: int, right: int) -> int:
    return _encode_binary32_fraction(
        _decode_binary32_fraction(left) + _decode_binary32_fraction(right)
    )


def _f32_multiply(left: int, right: int) -> int:
    return _encode_binary32_fraction(
        _decode_binary32_fraction(left) * _decode_binary32_fraction(right)
    )


def _f32_divide(left: int, right: int) -> int:
    return _encode_binary32_fraction(
        _decode_binary32_fraction(left) / _decode_binary32_fraction(right)
    )


@lru_cache(maxsize=8)
def _decimal_pi(precision: int) -> Decimal:
    with localcontext() as context:
        context.prec = precision + 24
        one = Decimal(1)
        two = Decimal(2)
        four = Decimal(4)
        a = one
        b = one / two.sqrt()
        t = one / four
        power = one
        for _ in range(12):
            next_a = (a + b) / two
            b = (a * b).sqrt()
            t -= power * (a - next_a) * (a - next_a)
            a = next_a
            power *= two
        result = (a + b) * (a + b) / (four * t)
        context.prec = precision
        return +result


def _decimal_sin_cos(
    angle: Fraction,
    precision: int,
) -> tuple[Decimal, Decimal]:
    with localcontext() as context:
        context.prec = precision + 28
        value = Decimal(angle.numerator) / Decimal(angle.denominator)
        pi = _decimal_pi(precision + 16)
        half_pi = pi / 2
        quadrant_count = int(
            (value / half_pi).to_integral_value(rounding=ROUND_HALF_EVEN)
        )
        reduced = value - Decimal(quadrant_count) * half_pi
        square = reduced * reduced
        sine_term = reduced
        cosine_term = Decimal(1)
        sine = sine_term
        cosine = cosine_term
        threshold = Decimal(1).scaleb(-(precision + 8))
        index = 1
        while True:
            sine_term *= -square / ((2 * index) * (2 * index + 1))
            cosine_term *= -square / ((2 * index - 1) * (2 * index))
            sine += sine_term
            cosine += cosine_term
            if abs(sine_term) < threshold and abs(cosine_term) < threshold:
                break
            index += 1

        quadrant = quadrant_count & 3
        if quadrant == 0:
            result = cosine, sine
        elif quadrant == 1:
            result = -sine, cosine
        elif quadrant == 2:
            result = -cosine, -sine
        else:
            result = sine, -cosine
        context.prec = precision
        return +result[0], +result[1]


def _decimal_root_power(base: int, index: int, precision: int) -> Decimal:
    if index == 0:
        return Decimal(1)
    with localcontext() as context:
        context.prec = precision + 24
        exponent = Decimal(index) / Decimal(ROPE_COMPLEX_PAIRS)
        value = (Decimal(base).ln() * exponent).exp()
        context.prec = precision
        return +value


def _oracle_yarn_correction_range(precision: int) -> tuple[int, int]:
    with localcontext() as context:
        context.prec = precision
        pi = _decimal_pi(precision)
        dimension = Decimal(ROPE_DIMENSION)
        base = Decimal(COMPRESSED_ROPE_THETA)
        original = Decimal(YARN_ORIGINAL_SEQUENCE_LENGTH)

        def correction(rotation_count: int) -> Decimal:
            numerator = (original / (Decimal(rotation_count) * 2 * pi)).ln()
            return dimension * numerator / (2 * base.ln())

        low = int(correction(YARN_BETA_FAST).to_integral_value(rounding=ROUND_FLOOR))
        high = int(correction(YARN_BETA_SLOW).to_integral_value(rounding=ROUND_CEILING))
    return max(low, 0), min(high, ROPE_DIMENSION - 1)


@lru_cache(maxsize=8)
def _oracle_frequency_codes(profile: str, precision: int) -> tuple[int, ...]:
    base = BASE_ROPE_THETA if profile == BASE_ROPE_PROFILE else COMPRESSED_ROPE_THETA
    one = 0x3F800000
    frequencies = tuple(
        _f32_divide(
            one,
            _encode_binary32_fraction(
                Fraction(_decimal_root_power(base, index, precision))
            ),
        )
        for index in range(ROPE_COMPLEX_PAIRS)
    )
    if profile == BASE_ROPE_PROFILE:
        return frequencies

    low, high = _oracle_yarn_correction_range(precision)
    factor = _encode_binary32_fraction(Fraction(YARN_FACTOR))
    output = []
    for index, frequency in enumerate(frequencies):
        ramp_value = max(
            Fraction(0),
            min(Fraction(1), Fraction(index - low, high - low)),
        )
        ramp = _encode_binary32_fraction(ramp_value)
        smooth = _f32_add(one, _negate_binary32(ramp))
        one_minus_smooth = _f32_add(one, _negate_binary32(smooth))
        output.append(
            _f32_add(
                _f32_multiply(
                    _f32_divide(frequency, factor),
                    one_minus_smooth,
                ),
                _f32_multiply(frequency, smooth),
            )
        )
    return tuple(output)


def _oracle_phasor(
    frequency: int,
    position: int,
    precision: int,
) -> tuple[int, int]:
    if position == 0:
        return 0x3F800000, 0
    position_code = _encode_binary32_fraction(Fraction(position))
    angle_code = _f32_multiply(position_code, frequency)
    cosine, sine = _decimal_sin_cos(
        _decode_binary32_fraction(angle_code),
        precision,
    )
    return (
        _encode_binary32_fraction(Fraction(cosine)),
        _encode_binary32_fraction(Fraction(sine)),
    )


def _oracle_rotate_row(
    row: tuple[int, ...],
    phasors: tuple[tuple[int, int], ...],
    *,
    inverse: bool,
) -> tuple[int, ...]:
    prefix = row[:-ROPE_DIMENSION]
    suffix = row[-ROPE_DIMENSION:]
    output = []
    for pair_index, (cosine, forward_sine) in enumerate(phasors):
        sine = _negate_binary32(forward_sine) if inverse else forward_sine
        real = suffix[2 * pair_index] << 16
        imaginary = suffix[2 * pair_index + 1] << 16
        real_output = _f32_add(
            _f32_multiply(real, cosine),
            _negate_binary32(_f32_multiply(imaginary, sine)),
        )
        imaginary_output = _f32_add(
            _f32_multiply(real, sine),
            _f32_multiply(imaginary, cosine),
        )
        output.extend(
            (
                _binary32_to_bf16_rne(real_output),
                _binary32_to_bf16_rne(imaginary_output),
            )
        )
    return prefix + tuple(output)


def _sha256_codes(codes: tuple[int, ...], bits: int) -> str:
    payload = struct.pack(
        f"<{len(codes)}{'H' if bits == 16 else 'I'}",
        *codes,
    )
    return hashlib.sha256(payload).hexdigest()


def _flatten(value: object) -> tuple[int, ...]:
    if type(value) is int:
        return (value,)
    assert type(value) is tuple
    return tuple(item for child in value for item in _flatten(child))


def _fixture(width: int = 128, *, batches: int = 1, sequence: int = 2) -> Any:
    palette = (
        0x0000,
        0x8000,
        0x0001,
        0x8001,
        0x3D80,
        0xBD80,
        0x3E80,
        0xBE80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
        0x4040,
        0xC040,
    )
    return tuple(
        tuple(
            tuple(
                palette[(batch * 5 + position * 7 + column) % len(palette)]
                for column in range(width)
            )
            for position in range(sequence)
        )
        for batch in range(batches)
    )


def _mutable(value: object) -> object:
    if isinstance(value, tuple):
        return [_mutable(element) for element in value]
    return value


def _signed_zero_equal(left: int, right: int) -> bool:
    if left & 0x7FFF == 0 and right & 0x7FFF == 0:
        return True
    return left == right


def _ordered_float32(code: int) -> int:
    return (~code & 0xFFFFFFFF) if code & 0x80000000 else code | 0x80000000


def _ulp_distance(left: int, right: int) -> int:
    return abs(_ordered_float32(left) - _ordered_float32(right))


def _official_functions(torch: Any) -> tuple[Any, Any]:
    if not _MODEL_SOURCE.is_file():
        pytest.skip(f"set {_SNAPSHOT_ENV}; missing {_MODEL_SOURCE}")
    tree = ast.parse(_MODEL_SOURCE.read_text(encoding="utf-8"))
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"precompute_freqs_cis", "apply_rotary_emb"}
    ]
    assert {node.name for node in nodes} == {
        "precompute_freqs_cis",
        "apply_rotary_emb",
    }
    namespace = {
        "torch": torch,
        "math": math,
        "lru_cache": __import__("functools").lru_cache,
    }
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), str(_MODEL_SOURCE), "exec"),
        namespace,
    )
    return namespace["precompute_freqs_cis"], namespace["apply_rotary_emb"]


def test_official_source_and_configuration_are_content_anchored() -> None:
    if not (
        _MODEL_SOURCE.is_file()
        and _INFERENCE_CONFIG.is_file()
        and _GENERATE_SOURCE.is_file()
    ):
        pytest.skip(f"set {_SNAPSHOT_ENV}; official source cache is unavailable")
    assert hashlib.sha256(_MODEL_SOURCE.read_bytes()).hexdigest() == MODEL_SOURCE_SHA256
    assert (
        hashlib.sha256(_INFERENCE_CONFIG.read_bytes()).hexdigest()
        == INFERENCE_CONFIG_SHA256
    )
    assert (
        hashlib.sha256(_GENERATE_SOURCE.read_bytes()).hexdigest()
        == GENERATE_SOURCE_SHA256
    )
    configuration = json.loads(_INFERENCE_CONFIG.read_text(encoding="utf-8"))
    assert {
        "n_heads": configuration["n_heads"],
        "head_dim": configuration["head_dim"],
        "rope_head_dim": configuration["rope_head_dim"],
        "index_head_dim": configuration["index_head_dim"],
        "original_seq_len": configuration["original_seq_len"],
        "rope_theta": configuration["rope_theta"],
        "rope_factor": configuration["rope_factor"],
        "beta_fast": configuration["beta_fast"],
        "beta_slow": configuration["beta_slow"],
        "compress_rope_theta": configuration["compress_rope_theta"],
    } == {
        "n_heads": 64,
        "head_dim": 512,
        "rope_head_dim": ROPE_DIMENSION,
        "index_head_dim": 128,
        "original_seq_len": YARN_ORIGINAL_SEQUENCE_LENGTH,
        "rope_theta": BASE_ROPE_THETA,
        "rope_factor": YARN_FACTOR,
        "beta_fast": YARN_BETA_FAST,
        "beta_slow": YARN_BETA_SLOW,
        "compress_rope_theta": COMPRESSED_ROPE_THETA,
    }
    source = _MODEL_SOURCE.read_text(encoding="utf-8")
    generate_source = _GENERATE_SOURCE.read_text(encoding="utf-8")
    assert "base ** (torch.arange(0, dim, 2, dtype=torch.float32) / dim)" in source
    assert "freqs = freqs / factor * (1 - smooth) + freqs * smooth" in source
    assert "torch.view_as_complex(x.float().unflatten(-1, (-1, 2)))" in source
    assert "freqs_cis = freqs_cis.conj()" in source
    assert "y.copy_(x)" in source
    assert "self.freqs_cis[:cutoff:ratio]" in source
    assert "self.freqs_cis[start_pos + 1 - self.compress_ratio]" in source
    assert "args.max_seq_len = 64 * 1024" in generate_source


def test_reference_is_independent_of_torch_numpy_cmath_and_host_libm() -> None:
    source = inspect.getsource(rope_module)
    tree = ast.parse(source)
    for forbidden in ("import torch", "import numpy", "import cmath", "import math"):
        assert forbidden not in source
    assert "float(" not in source
    assert "runtime.service_engine" not in source
    assert "open(" not in source
    assert "Path(" not in source
    assert "expected_output" not in source
    imported_modules = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not any(
        fragment in module
        for module in imported_modules
        for fragment in (
            "torch",
            "numpy",
            "cmath",
            "math",
            "compiler",
            "service_engine",
            "checkpoint",
            "safetensors",
            "pathlib",
            "mmap",
        )
    )
    assert {
        (node.level, node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level
    } == {(1, "formats")}


def test_profile_constants_and_nonclaims_are_explicit() -> None:
    assert ROPE_NUMERIC_PROFILE == "opentallas.deepseek_v4_rope_numeric.v2"
    assert MAX_SEQUENCE_LENGTH == YARN_ORIGINAL_SEQUENCE_LENGTH == 65_536
    assert SUPPORTED_HEAD_WIDTHS == frozenset({64, 128, 512})
    assert SUPPORTED_POSITION_STRIDES == frozenset({1, 4, 128})
    assert EXCLUDED_CLAIMS == (
        "active_backend_torch_polar_bit_equivalence",
        "cuda_or_accelerator_kernel_equivalence",
        "checkpoint_execution",
        "service_engine_execution",
        "compiler_or_graph_position_binding",
        "cycles_latency_throughput_bandwidth_energy_area_density_routing_ppa",
        "end_to_end_model_execution",
    )


@pytest.mark.parametrize("bad_profile", [True, None, "yarn", "BASE", 0])
def test_frequency_and_phasor_helpers_reject_noncanonical_profiles(
    bad_profile: object,
) -> None:
    with pytest.raises(RopeReferenceError, match="profile"):
        rope_frequency_binary32_codes(profile=bad_profile)  # type: ignore[arg-type]
    with pytest.raises(RopeReferenceError, match="profile"):
        rope_phasor_binary32_codes(0, profile=bad_profile)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_position",
    [True, False, -1, MAX_POSITION + 1, 1.0, "0", None],
)
def test_phasor_helper_position_is_exact_and_bounded(bad_position: object) -> None:
    with pytest.raises(RopeReferenceError, match="position"):
        rope_phasor_binary32_codes(bad_position)  # type: ignore[arg-type]


def test_frequency_profiles_have_frozen_bit_identities() -> None:
    base = rope_frequency_binary32_codes(profile=BASE_ROPE_PROFILE)
    compressed = rope_frequency_binary32_codes(profile=COMPRESSED_YARN_ROPE_PROFILE)
    assert len(base) == len(compressed) == ROPE_COMPLEX_PAIRS
    assert _sha256_codes(base, 32) == _BASE_FREQUENCY_SHA256
    assert _sha256_codes(compressed, 32) == _COMPRESSED_FREQUENCY_SHA256
    assert base[:3] == (0x3F800000, 0x3F3FF911, 0x3F0FF59A)
    assert compressed[:3] == (0x3F800000, 0x3F300A3A, 0x3EF21C1F)
    assert base[31] == 0x390BD472
    assert compressed[15] == 0x3B6E4237
    assert compressed[25] == 0x36B443D0
    assert compressed[31] == 0x35187C4D
    assert compressed[0] == base[0]
    assert compressed != base


def test_yarn_range_is_independently_derived_from_pinned_parameters() -> None:
    low_precision = _oracle_yarn_correction_range(100)
    high_precision = _oracle_yarn_correction_range(180)
    assert (
        low_precision
        == high_precision
        == (
            YARN_CORRECTION_LOW,
            YARN_CORRECTION_HIGH,
        )
    )


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
def test_all_frequencies_match_independent_high_precision_oracle(profile: str) -> None:
    low_precision = _oracle_frequency_codes(profile, 110)
    high_precision = _oracle_frequency_codes(profile, 180)
    assert low_precision == high_precision
    assert rope_frequency_binary32_codes(profile=profile) == high_precision


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
@pytest.mark.parametrize("position", [0, 1, 127, 4095, MAX_POSITION])
def test_phasors_have_frozen_boundary_position_identities(
    profile: str,
    position: int,
) -> None:
    phasors = rope_phasor_binary32_codes(position, profile=profile)
    assert len(phasors) == ROPE_COMPLEX_PAIRS
    assert all(len(pair) == 2 for pair in phasors)
    assert _sha256_codes(_flatten(phasors), 32) == _PHASOR_SHA256[(profile, position)]
    assert phasors is rope_phasor_binary32_codes(position, profile=profile)


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
@pytest.mark.parametrize("position", [1, 127, 4095, MAX_POSITION])
def test_selected_phasors_match_independent_decimal_transcendental_oracle(
    profile: str,
    position: int,
) -> None:
    frequencies = _oracle_frequency_codes(profile, 180)
    observed = rope_phasor_binary32_codes(position, profile=profile)
    for pair_index in (0, 1, 14, 15, 16, 24, 25, 26, 31):
        low_precision = _oracle_phasor(
            frequencies[pair_index],
            position,
            110,
        )
        high_precision = _oracle_phasor(
            frequencies[pair_index],
            position,
            180,
        )
        assert low_precision == high_precision
        assert observed[pair_index] == high_precision


def test_position_zero_is_bit_identity_except_arithmetic_zero_canonicalization() -> (
    None
):
    value = _fixture(128, batches=2, sequence=1)
    output = rope_apply_bf16(value, 0)
    for source, observed in zip(_flatten(value), _flatten(output), strict=True):
        assert _signed_zero_equal(source, observed)
    prefix = 128 - ROPE_DIMENSION
    for source_batch, output_batch in zip(value, output, strict=True):
        for source, observed in zip(source_batch, output_batch, strict=True):
            assert observed[:prefix] == source[:prefix]
            assert all(code & 0x7FFF or code == 0 for code in observed[prefix:])


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
@pytest.mark.parametrize("width", [64, 128, 512])
def test_rank3_and_rank4_shapes_and_prefix_preservation(
    profile: str,
    width: int,
) -> None:
    rank3 = _fixture(width, batches=2, sequence=2)
    rank3_output = rope_apply_bf16(rank3, 126, profile=profile)
    assert len(rank3_output) == 2
    assert all(len(batch) == 2 for batch in rank3_output)
    assert all(len(row) == width for batch in rank3_output for row in batch)
    prefix = width - ROPE_DIMENSION
    for source_batch, output_batch in zip(rank3, rank3_output, strict=True):
        for source, output in zip(source_batch, output_batch, strict=True):
            assert output[:prefix] == source[:prefix]

    rank4 = tuple(
        tuple((row, tuple(reversed(row))) for row in batch) for batch in rank3
    )
    rank4_output = rope_inverse_bf16(rank4, 126, profile=profile)
    assert len(rank4_output) == 2
    assert all(len(position) == 2 for batch in rank4_output for position in batch)
    assert all(
        len(head) == width
        for batch in rank4_output
        for position in batch
        for head in position
    )
    for source_batch, output_batch in zip(rank4, rank4_output, strict=True):
        for source_position, output_position in zip(
            source_batch, output_batch, strict=True
        ):
            for source, output in zip(source_position, output_position, strict=True):
                assert output[:prefix] == source[:prefix]


def test_start_position_advances_across_sequence_axis_only() -> None:
    row = _fixture(64, sequence=1)[0][0]
    tensor = ((row, row, row), (row, row, row))
    output = rope_apply_bf16(tensor, 17)
    expected = tuple(
        rope_apply_bf16(((row,),), position)[0][0] for position in (17, 18, 19)
    )
    assert output == (expected, expected)


@pytest.mark.parametrize("ratio", [4, 128])
def test_compressor_prefill_stride_selects_exact_official_table_rows(
    ratio: int,
) -> None:
    row = _fixture(64, sequence=1)[0][0]
    value = ((row, row, row),)
    observed = rope_apply_bf16(
        value,
        0,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
        position_stride=ratio,
    )
    expected = tuple(
        rope_apply_bf16(
            ((row,),),
            position,
            profile=COMPRESSED_YARN_ROPE_PROFILE,
        )[0][0]
        for position in (0, ratio, 2 * ratio)
    )
    assert observed == (expected,)


@pytest.mark.parametrize(
    ("profile", "inverse"),
    [
        (BASE_ROPE_PROFILE, False),
        (BASE_ROPE_PROFILE, True),
        (COMPRESSED_YARN_ROPE_PROFILE, True),
    ],
)
def test_nonunit_stride_is_restricted_to_official_compressor_prefill(
    profile: str,
    inverse: bool,
) -> None:
    row = (0,) * ROPE_DIMENSION
    with pytest.raises(RopeReferenceError, match="compressor-prefill"):
        apply_rotary_bf16(
            ((row,),),
            0,
            profile=profile,
            inverse=inverse,
            position_stride=4,
        )


@pytest.mark.parametrize("ratio", [4, 128])
def test_compressor_decode_consumes_caller_adjusted_absolute_position(
    ratio: int,
) -> None:
    request_start = ratio + 9
    adjusted_position = request_start + 1 - ratio
    row = _fixture(64, sequence=1)[0][0]
    result = apply_rotary_bf16_result(
        ((row,),),
        adjusted_position,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
    )
    assert result.start_position == result.last_position == adjusted_position
    assert result.output_bf16_codes == rope_apply_bf16(
        ((row,),),
        adjusted_position,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
    )


def test_detailed_result_and_logical_counters_reconcile_rank4_inverse() -> None:
    row = _fixture(128, sequence=1)[0][0]
    value = tuple(
        tuple(tuple(row for _ in range(4)) for _ in range(3)) for _ in range(2)
    )
    result = apply_rotary_bf16_result(
        value,
        5,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
        inverse=True,
    )
    assert result.numeric_profile == ROPE_NUMERIC_PROFILE
    assert result.profile == COMPRESSED_YARN_ROPE_PROFILE
    assert result.inverse is True
    assert result.start_position == 5
    assert result.last_position == 7
    assert result.position_stride == 1
    assert result.output_bf16_codes == apply_rotary_bf16(
        value,
        5,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
        inverse=True,
    )
    assert result.counters == RopeCounters(
        tensor_rank=4,
        batch_count=2,
        sequence_length=3,
        head_count=4,
        head_width=128,
        rope_dimension=64,
        complex_pairs_per_vector=32,
        position_stride=1,
        rotated_vector_count=24,
        input_bf16_values=3072,
        prefix_bf16_values_preserved=1536,
        rotated_input_bf16_values=1536,
        logical_phasor_binary32_values_read=1536,
        bf16_to_binary32_exact_widenings=1536,
        binary32_multiplications=3072,
        binary32_additions_or_subtractions=1536,
        conjugated_sine_binary32_values=96,
        binary32_to_bf16_conversions=1536,
        output_bf16_values=3072,
        transaction_commits=1,
    )

    counter_names = {field.name for field in fields(RopeCounters)}
    prohibited_physical_claims = (
        "cycle",
        "latency",
        "throughput",
        "bandwidth",
        "energy",
        "area",
        "density",
        "routing",
        "ppa",
    )
    assert not any(
        token in name for name in counter_names for token in prohibited_physical_claims
    )
    assert {field.name for field in fields(RopeResult)} == {
        "numeric_profile",
        "profile",
        "inverse",
        "start_position",
        "last_position",
        "position_stride",
        "output_bf16_codes",
        "counters",
    }
    with pytest.raises(FrozenInstanceError):
        result.inverse = False  # type: ignore[misc]


def test_public_counter_constructor_rejects_bool_aliases_for_every_field() -> None:
    counters = apply_rotary_bf16_result(_fixture(64), 0).counters
    for field in fields(RopeCounters):
        with pytest.raises(RopeReferenceError, match="exact integer"):
            replace(counters, **{field.name: True})


def test_public_counter_direct_constructor_rejects_forged_completion() -> None:
    counters = apply_rotary_bf16_result(_fixture(64), 0).counters
    values = {field.name: getattr(counters, field.name) for field in fields(counters)}
    values["transaction_commits"] = 0
    with pytest.raises(RopeReferenceError, match="transaction_commits"):
        RopeCounters(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "rotated_vector_count",
        "input_bf16_values",
        "prefix_bf16_values_preserved",
        "rotated_input_bf16_values",
        "logical_phasor_binary32_values_read",
        "bf16_to_binary32_exact_widenings",
        "binary32_multiplications",
        "binary32_additions_or_subtractions",
        "binary32_to_bf16_conversions",
        "output_bf16_values",
        "transaction_commits",
    ],
)
def test_public_counter_constructor_rejects_every_forged_formula(
    field_name: str,
) -> None:
    counters = apply_rotary_bf16_result(_fixture(128), 0).counters
    with pytest.raises(RopeReferenceError, match=field_name):
        replace(counters, **{field_name: getattr(counters, field_name) + 1})


@pytest.mark.parametrize(
    ("field_name", "forged"),
    [
        ("tensor_rank", 2),
        ("tensor_rank", 5),
        ("batch_count", 0),
        ("batch_count", 5),
        ("sequence_length", 0),
        ("sequence_length", MAX_SEQUENCE_LENGTH + 1),
        ("head_count", 0),
        ("head_count", 65),
        ("head_width", 256),
        ("rope_dimension", 32),
        ("complex_pairs_per_vector", 16),
        ("position_stride", 2),
        ("conjugated_sine_binary32_values", 1),
    ],
)
def test_public_counter_constructor_rejects_forged_dimensions_and_completion(
    field_name: str,
    forged: int,
) -> None:
    counters = apply_rotary_bf16_result(_fixture(64), 0).counters
    with pytest.raises(RopeReferenceError, match=field_name):
        replace(counters, **{field_name: forged})


def test_public_result_constructor_rejects_mutable_and_sequence_aliases() -> None:
    result = apply_rotary_bf16_result(_fixture(64), 0)
    output = result.output_bf16_codes
    mutable_nested = (list(output[0]),)
    aliases: tuple[object, ...] = (
        _mutable(output),
        mutable_nested,
        _ListSubclass(output),
        {"output": output},
    )
    for alias in aliases:
        with pytest.raises(RopeReferenceError, match="immutable|BF16"):
            replace(result, output_bf16_codes=alias)  # type: ignore[arg-type]

    mutable = _mutable(output)
    with pytest.raises(RopeReferenceError, match="immutable"):
        RopeResult(
            numeric_profile=result.numeric_profile,
            profile=result.profile,
            inverse=result.inverse,
            start_position=result.start_position,
            last_position=result.last_position,
            position_stride=result.position_stride,
            output_bf16_codes=mutable,  # type: ignore[arg-type]
            counters=result.counters,
        )
    mutable[0][0][0] = 0x3F80  # type: ignore[index]
    assert result.output_bf16_codes == output

    with pytest.raises(RopeReferenceError, match="profile"):
        RopeResult(
            numeric_profile=result.numeric_profile,
            profile="yarn",  # type: ignore[arg-type]
            inverse=result.inverse,
            start_position=result.start_position,
            last_position=result.last_position,
            position_stride=result.position_stride,
            output_bf16_codes=result.output_bf16_codes,
            counters=result.counters,
        )


@pytest.mark.parametrize(
    ("field_name", "forged", "match"),
    [
        (
            "numeric_profile",
            "opentallas.deepseek_v4_rope_numeric.v1",
            "numeric_profile",
        ),
        ("numeric_profile", True, "numeric_profile"),
        ("profile", "yarn", "profile"),
        ("profile", True, "profile"),
        ("inverse", 0, "inverse"),
        ("start_position", True, "start_position"),
        ("start_position", -1, "start_position"),
        ("last_position", True, "last_position"),
        ("last_position", MAX_POSITION + 1, "last_position"),
        ("position_stride", True, "position_stride"),
        ("position_stride", 2, "position_stride"),
    ],
)
def test_public_result_constructor_rejects_forged_scalar_authority(
    field_name: str,
    forged: object,
    match: str,
) -> None:
    result = apply_rotary_bf16_result(_fixture(64), 0)
    with pytest.raises(RopeReferenceError, match=match):
        replace(result, **{field_name: forged})


def test_public_result_constructor_reconciles_position_direction_shape_and_counters() -> (
    None
):
    result = apply_rotary_bf16_result(
        _fixture(128, sequence=2),
        7,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
    )
    with pytest.raises(RopeReferenceError, match="last_position"):
        replace(result, last_position=result.last_position + 1)
    with pytest.raises(RopeReferenceError, match="nonunit"):
        replace(
            result,
            profile=BASE_ROPE_PROFILE,
            position_stride=4,
            last_position=11,
        )

    inverse = apply_rotary_bf16_result(
        _fixture(64),
        0,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
        inverse=True,
    )
    with pytest.raises(RopeReferenceError, match="conjugation"):
        replace(inverse, inverse=False)
    forward = apply_rotary_bf16_result(_fixture(64), 0)
    with pytest.raises(RopeReferenceError, match="conjugation"):
        replace(forward, counters=inverse.counters)

    with pytest.raises(RopeReferenceError, match="rank-3 or rank-4"):
        replace(result, output_bf16_codes=result.output_bf16_codes[0])
    ragged = ((result.output_bf16_codes[0][0], result.output_bf16_codes[0][1][:-1]),)
    with pytest.raises(RopeReferenceError, match="rectangular"):
        replace(result, output_bf16_codes=ragged)
    with pytest.raises(RopeReferenceError, match="dimensions"):
        replace(result, counters=forward.counters)
    for alias in (result.counters.__dict__, [result.counters]):
        with pytest.raises(RopeReferenceError, match="exact RopeCounters"):
            replace(result, counters=alias)  # type: ignore[arg-type]


def test_public_result_constructor_rejects_invalid_output_codes() -> None:
    result = apply_rotary_bf16_result(_fixture(64), 0)
    row = result.output_bf16_codes[0][0]
    for code in (True, -1, 1 << 16, 0x7F80, 0x7FC1):
        forged = (((code,) + row[1:],),)
        with pytest.raises(RopeReferenceError, match="BF16"):
            replace(result, output_bf16_codes=forged)


def test_apply_and_inverse_use_opposite_conjugate_angles() -> None:
    row = (0x3F80, 0) + (0,) * 62
    forward = rope_apply_bf16(((row,),), 1)[0][0]
    inverse = rope_inverse_bf16(((row,),), 1)[0][0]
    phasors = rope_phasor_binary32_codes(1)
    assert forward == _oracle_rotate_row(row, phasors, inverse=False)
    assert inverse == _oracle_rotate_row(row, phasors, inverse=True)
    assert forward[0] == inverse[0]
    assert forward[1] == (inverse[1] ^ 0x8000)
    assert forward[2:] == inverse[2:]


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
@pytest.mark.parametrize("inverse", [False, True])
@pytest.mark.parametrize("width", [64, 128, 512])
def test_randomized_application_matches_independent_exact_pair_oracle(
    profile: str,
    inverse: bool,
    width: int,
) -> None:
    generator = random.Random(
        0x524F_5045
        + width
        + int(inverse)
        + int(profile == COMPRESSED_YARN_ROPE_PROFILE)
    )
    finite_codes = tuple(
        code for code in range(0, 1 << 16, 257) if code & 0x7F80 != 0x7F80
    )
    for position in (0, 1, 127, 4095, MAX_POSITION):
        row = tuple(generator.choice(finite_codes) for _ in range(width))
        phasors = rope_phasor_binary32_codes(position, profile=profile)
        try:
            expected = _oracle_rotate_row(row, phasors, inverse=inverse)
        except (OverflowError, AssertionError):
            with pytest.raises(RopeReferenceError):
                apply_rotary_bf16(
                    ((row,),),
                    position,
                    profile=profile,
                    inverse=inverse,
                )
        else:
            observed = apply_rotary_bf16(
                ((row,),),
                position,
                profile=profile,
                inverse=inverse,
            )
            assert observed == ((expected,),)


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
@pytest.mark.parametrize("position", [0, 1, 127, 4095, MAX_POSITION])
def test_apply_inverse_composition_is_bf16_accurate(
    profile: str,
    position: int,
) -> None:
    source = _fixture(64, sequence=1)
    restored = rope_inverse_bf16(
        rope_apply_bf16(source, position, profile=profile),
        position,
        profile=profile,
    )
    for expected_code, observed_code in zip(
        _flatten(source), _flatten(restored), strict=True
    ):
        expected = _decode_bf16_fraction(expected_code)
        observed = _decode_bf16_fraction(observed_code)
        # Two BF16 conversions make exact bit inversion impossible in general.
        # Bound the composition by two source BF16 ULPs at each magnitude.
        neighbors = [expected_code]
        if 0 < (expected_code & 0x7FFF) < 0x7F7F:
            neighbors.extend((expected_code - 1, expected_code + 1))
        ulp = max(
            abs(_decode_bf16_fraction(code) - expected)
            for code in neighbors
            if code & 0x7F80 != 0x7F80
        )
        if ulp == 0:
            assert observed == expected
        else:
            assert abs(observed - expected) <= 2 * ulp


def test_public_wrappers_match_explicit_direction() -> None:
    value = _fixture(128)
    assert rope_apply_bf16(value, 127, profile=BASE_ROPE_PROFILE) == apply_rotary_bf16(
        value,
        127,
        profile=BASE_ROPE_PROFILE,
        inverse=False,
    )
    assert rope_inverse_bf16(
        value, 127, profile=COMPRESSED_YARN_ROPE_PROFILE
    ) == apply_rotary_bf16(
        value,
        127,
        profile=COMPRESSED_YARN_ROPE_PROFILE,
        inverse=True,
    )


def test_output_is_deterministic_and_input_is_not_mutated() -> None:
    value = _mutable(_fixture(128))
    before = deepcopy(value)
    first = rope_apply_bf16(value, 127, profile=COMPRESSED_YARN_ROPE_PROFILE)
    second = rope_apply_bf16(value, 127, profile=COMPRESSED_YARN_ROPE_PROFILE)
    assert first == second
    assert value == before
    value[0][0][0] = 0x3F80  # type: ignore[index]
    assert first == second
    assert type(first) is tuple
    assert type(first[0]) is tuple
    assert type(first[0][0]) is tuple


@pytest.mark.parametrize(
    ("value", "start", "kwargs", "match"),
    [
        ((), 0, {}, "rank-3 or rank-4|must not be empty"),
        (((0,) * 64,), 0, {}, "rank-3 or rank-4"),
        ((((0,) * 64,),), -1, {}, "start_position"),
        ((((0,) * 64,),), True, {}, "start_position"),
        ((((0,) * 64,),), MAX_SEQUENCE_LENGTH, {}, "start_position"),
        ((((0,) * 63,),), 0, {}, "head width"),
        ((((0,) * 66,),), 0, {}, "head width"),
        ((((0,) * 256,),), 0, {}, "head width"),
        ((((0,) * 64,),), 0, {"profile": "yarn"}, "profile"),
        ((((0,) * 64,),), 0, {"profile": True}, "profile"),
        ((((0,) * 64,),), 0, {"rope_dimension": 32}, "rope_dimension"),
        ((((0,) * 64,),), 0, {"rope_dimension": True}, "rope_dimension"),
        ((((0,) * 64,),), 0, {"inverse": 1}, "inverse"),
        ((((0,) * 64,),), 0, {"position_stride": 2}, "position_stride"),
        ((((0,) * 64,),), 0, {"position_stride": True}, "position_stride"),
    ],
)
def test_malformed_scalar_shape_and_type_aliases_fail_closed(
    value: object,
    start: object,
    kwargs: dict[str, Any],
    match: str,
) -> None:
    with pytest.raises(RopeReferenceError, match=match):
        apply_rotary_bf16(value, start, **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [None, "x", b"x", bytearray(b"x"), 1.0, object()])
def test_nonsequence_tensor_inputs_fail_closed(bad: object) -> None:
    with pytest.raises(RopeReferenceError, match="sequence|rank-3"):
        rope_apply_bf16(bad, 0)


def test_every_tensor_axis_requires_an_exact_list_or_tuple() -> None:
    row = (0,) * 64
    invalid_values = (
        _ListSubclass([((row,),)]),
        (_ListSubclass([(row,)]),),
        ((_ListSubclass([row]),),),
        (((_ListSubclass(row),),),),
        ((range(64),),),
    )
    for invalid in invalid_values:
        with pytest.raises(RopeReferenceError, match="exact list or tuple"):
            rope_apply_bf16(invalid, 0)


@pytest.mark.parametrize("code", [True, False, -1, 1 << 16, 1.0, "0", None])
def test_invalid_bf16_encodings_and_bool_aliases_fail_closed(code: object) -> None:
    value = (((code,) + (0,) * 63,),)
    with pytest.raises(RopeReferenceError, match="BF16 encoding"):
        rope_apply_bf16(value, 0)


@pytest.mark.parametrize("code", [0x7F80, 0xFF80, 0x7FC1, 0xFFC1])
def test_nonfinite_bf16_input_poisons_the_whole_transaction(code: int) -> None:
    value = ((((0,) * 64), ((0,) * 63 + (code,))),)
    with pytest.raises(RopeReferenceError, match="finite BF16"):
        rope_apply_bf16(value, 1)


def test_all_input_validation_completes_before_pair_arithmetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def forbidden_rotate(*_args: object, **_kwargs: object) -> tuple[int, ...]:
        nonlocal calls
        calls += 1
        raise AssertionError("pair arithmetic ran before validation completed")

    monkeypatch.setattr(rope_module, "_rotate_vector", forbidden_rotate)
    value = ((((0,) * 64), ((0,) * 63 + (0x7FC1,))),)
    with pytest.raises(RopeReferenceError, match="finite BF16"):
        rope_apply_bf16(value, 1)
    assert calls == 0


def test_finite_complex_overflow_poisons_without_partial_output() -> None:
    overflowing_pair = (0x7F7F, 0x7F7F)
    safe_row = (0,) * ROPE_DIMENSION
    value = (((safe_row, overflowing_pair + (0,) * 62)),)
    before = deepcopy(value)
    with pytest.raises(RopeReferenceError, match="overflow"):
        rope_apply_bf16(value, 1)
    assert value == before


def test_ragged_tensors_fail_closed() -> None:
    with pytest.raises(RopeReferenceError, match="rectangular"):
        rope_apply_bf16((((0,) * 64, (0,) * 128),), 0)
    with pytest.raises(RopeReferenceError, match="rectangular"):
        rope_apply_bf16(((((0,) * 64,),), (((0,) * 64,) * 2)), 0)


def test_batch_head_and_position_bounds_are_enforced() -> None:
    row = (0,) * 64
    with pytest.raises(RopeReferenceError, match="batch size"):
        rope_apply_bf16(tuple(((row,),) for _ in range(5)), 0)
    with pytest.raises(RopeReferenceError, match="head count"):
        rope_apply_bf16((((row,) * 65,),), 0)
    with pytest.raises(RopeReferenceError, match="pinned.*table"):
        rope_apply_bf16(((row, row),), MAX_POSITION)
    with pytest.raises(RopeReferenceError, match="pinned.*table"):
        rope_apply_bf16(
            ((row, row),),
            MAX_POSITION - 3,
            profile=COMPRESSED_YARN_ROPE_PROFILE,
            position_stride=4,
        )
    assert len(rope_apply_bf16(((row,),), MAX_POSITION)[0][0]) == 64


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
@pytest.mark.parametrize("inverse", [False, True])
def test_unmodified_official_cpu_source_diagnostic_matches_selected_bf16_cases(
    profile: str,
    inverse: bool,
) -> None:
    # This diagnostic executes the pinned Python functions on the installed
    # CPU Torch backend.  It is not the exact target oracle above and makes no
    # statement about CUDA, another backend, or checkpoint execution.
    torch = pytest.importorskip("torch")
    precompute, official_apply = _official_functions(torch)
    if profile == BASE_ROPE_PROFILE:
        arguments = (0, 10_000, 16, 32, 1)
    else:
        arguments = (65_536, 160_000, 16, 32, 1)
    official_freqs = precompute(64, 65_536, *arguments)

    generator = random.Random(0x524F5045)
    palette = (
        0x0000,
        0x8000,
        0x0001,
        0x8001,
        0x3E80,
        0xBE80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
    )
    value = tuple(
        tuple(tuple(generator.choice(palette) for _ in range(128)) for _ in range(3))
        for _ in range(2)
    )
    for start in (0, 127, 4095, MAX_POSITION - 2):
        official_input = (
            torch.tensor(_flatten(value), dtype=torch.uint16)
            .view(torch.bfloat16)
            .reshape(2, 3, 128)
        )
        expected = official_apply(
            official_input[..., -ROPE_DIMENSION:].clone(),
            official_freqs[start : start + 3],
            inverse,
        ).view(torch.uint16)
        rotated = (
            rope_inverse_bf16(value, start, profile=profile)
            if inverse
            else rope_apply_bf16(value, start, profile=profile)
        )
        observed = tuple(
            tuple(row[-ROPE_DIMENSION:] for row in batch) for batch in rotated
        )
        for left, right in zip(
            _flatten(observed), expected.reshape(-1).tolist(), strict=True
        ):
            # These selected finite cases land on the same BF16 codes modulo
            # the development backend's signed-zero retention.
            assert _signed_zero_equal(left, right)


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
def test_installed_cpu_source_phasors_are_within_one_binary32_ulp_diagnostic(
    profile: str,
) -> None:
    # Diagnostic only; active-backend torch.polar bits are explicitly not part
    # of ROPE_NUMERIC_PROFILE.
    torch = pytest.importorskip("torch")
    precompute, _ = _official_functions(torch)
    arguments = (
        (0, 10_000, 16, 32, 1)
        if profile == BASE_ROPE_PROFILE
        else (65_536, 160_000, 16, 32, 1)
    )
    official = precompute(64, 65_536, *arguments)
    for position in (0, 1, 127, 4095, MAX_POSITION):
        expected_real = official[position].real.contiguous().view(torch.int32).tolist()
        expected_imag = official[position].imag.contiguous().view(torch.int32).tolist()
        observed = rope_phasor_binary32_codes(position, profile=profile)
        for (cosine, sine), expected_cosine, expected_sine in zip(
            observed,
            expected_real,
            expected_imag,
            strict=True,
        ):
            assert _ulp_distance(cosine, expected_cosine & 0xFFFFFFFF) <= 1
            assert _ulp_distance(sine, expected_sine & 0xFFFFFFFF) <= 1
