from __future__ import annotations

import ast
import hashlib
import inspect
import math
import os
from pathlib import Path
import random
import struct
from typing import Any

import pytest

from runtime.reference.formats import decode_bf16
import runtime.reference.rope as rope_module
from runtime.reference.rope import (
    BASE_ROPE_PROFILE,
    COMPRESSED_YARN_ROPE_PROFILE,
    INFERENCE_CONFIG_SHA256,
    MAX_POSITION,
    MAX_SEQUENCE_LENGTH,
    MODEL_SOURCE_SHA256,
    OFFICIAL_REVISION,
    ROPE_COMPLEX_PAIRS,
    ROPE_DIMENSION,
    RopeReferenceError,
    apply_rotary_bf16,
    rope_apply_bf16,
    rope_frequency_binary32_codes,
    rope_inverse_bf16,
    rope_phasor_binary32_codes,
)


_SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_SNAPSHOT"
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
    if not (_MODEL_SOURCE.is_file() and _INFERENCE_CONFIG.is_file()):
        pytest.skip(f"set {_SNAPSHOT_ENV}; official source cache is unavailable")
    assert hashlib.sha256(_MODEL_SOURCE.read_bytes()).hexdigest() == MODEL_SOURCE_SHA256
    assert (
        hashlib.sha256(_INFERENCE_CONFIG.read_bytes()).hexdigest()
        == INFERENCE_CONFIG_SHA256
    )
    source = _MODEL_SOURCE.read_text(encoding="utf-8")
    assert "torch.view_as_complex(x.float().unflatten(-1, (-1, 2)))" in source
    assert "freqs_cis = freqs_cis.conj()" in source
    assert "y.copy_(x)" in source


def test_reference_is_independent_of_torch_numpy_cmath_and_host_libm() -> None:
    source = inspect.getsource(rope_module)
    for forbidden in ("import torch", "import numpy", "import cmath", "import math"):
        assert forbidden not in source
    assert "float(" not in source
    assert "runtime.service_engine" not in source


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


def test_apply_and_inverse_use_opposite_conjugate_angles() -> None:
    row = (0x3F80, 0) + (0,) * 62
    forward = rope_apply_bf16(((row,),), 1)[0][0]
    inverse = rope_inverse_bf16(((row,),), 1)[0][0]
    assert forward[:2] == (0x3F0A, 0x3F57)
    assert inverse[:2] == (0x3F0A, 0xBF57)
    assert forward[2:] == inverse[2:]


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
        expected = decode_bf16(expected_code)
        observed = decode_bf16(observed_code)
        assert expected.value is not None and observed.value is not None
        # Two BF16 conversions make exact bit inversion impossible in general.
        # Bound the composition by two source BF16 ULPs at each magnitude.
        neighbors = [expected_code]
        if 0 < (expected_code & 0x7FFF) < 0x7F7F:
            neighbors.extend((expected_code - 1, expected_code + 1))
        ulp = max(
            abs(decode_bf16(code).value - expected.value)  # type: ignore[operator]
            for code in neighbors
            if decode_bf16(code).value is not None
        )
        if ulp == 0:
            assert observed.value == expected.value
        else:
            assert abs(observed.value - expected.value) <= 2 * ulp


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
    value = _fixture(128)
    before = _flatten(value)
    first = rope_apply_bf16(value, 127, profile=COMPRESSED_YARN_ROPE_PROFILE)
    second = rope_apply_bf16(value, 127, profile=COMPRESSED_YARN_ROPE_PROFILE)
    assert first == second
    assert _flatten(value) == before
    assert _sha256_codes(_flatten(first), 16) == (
        "3314bfcff2395d351c74f4fe4b1ed0b64b5f81d292de3413c9f5ad4026d68b53"
    )


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


def test_finite_complex_overflow_poisons_without_partial_output() -> None:
    overflowing_pair = (0x7F7F, 0x7F7F)
    safe_row = (0,) * ROPE_DIMENSION
    value = (((safe_row, overflowing_pair + (0,) * 62)),)
    with pytest.raises(RopeReferenceError, match="overflow"):
        rope_apply_bf16(value, 1)
    assert value[0][0] == safe_row


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
    with pytest.raises(RopeReferenceError, match="official window"):
        rope_apply_bf16(((row, row),), MAX_POSITION)
    assert len(rope_apply_bf16(((row,),), MAX_POSITION)[0][0]) == 64


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
@pytest.mark.parametrize("inverse", [False, True])
def test_independent_official_source_differential(
    profile: str,
    inverse: bool,
) -> None:
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
            # The independent profile differs from backend libm/pow by at most
            # one binary32 ULP before BF16 conversion.  Outputs are therefore
            # bit-equal modulo the development backend's signed-zero retention.
            assert _signed_zero_equal(left, right)


@pytest.mark.parametrize("profile", [BASE_ROPE_PROFILE, COMPRESSED_YARN_ROPE_PROFILE])
def test_official_phasors_are_within_one_binary32_ulp(profile: str) -> None:
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
