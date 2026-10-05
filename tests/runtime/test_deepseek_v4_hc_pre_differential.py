from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction
import hashlib
import inspect
import json
import os
from pathlib import Path
import random

import pytest

import runtime.reference.hyper_connection as hc_reference
import runtime.service_engine.hc_pre_numeric as hc_service
from runtime.reference.formats import encode_binary32_rne


_HIDDEN = hc_reference.HIDDEN_SIZE
_FLAT = hc_reference.FLATTENED_WIDTH
_ZERO_STREAM = (0,) * _HIDDEN
_ZERO_PROJECTION_ROW = (0,) * _FLAT
_OFFICIAL_EVIDENCE_ENV = "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT"
_OFFICIAL_EVIDENCE_SHA256 = (
    "6582fb14ce5ed2657bab39211bd33787ce40b4b3c815f67a0413fbf87bbd9b55"
)
_OFFICIAL_RECORD_SHA256 = (
    "0eff4d087d2ad25518ddcd0a5d3592bf5a0237586d7e425eb64ba1ffe68b41b3",
    "0e681964b79cc613bcf482b66a7812223223e95e29e5f99a7437e5f5cfe4e1d3",
    "490ae6c24ee98ac9e56ac7fcdacd96bfda191a6537207efdf39b258bc45f11fa",
    "60448b7b4c080dc9ab13ec68c74986eb7a91132ef207babb7495d499ade76835",
)
_OFFICIAL_SOURCE_SHA256 = {
    "base_sha256": "edaa695cf5de59f919415f6e71dcb35be5ad817a06fa7222ee3021d9f388adda",
    "input_sha256": "f0ea58b5da876ba4fd41b5a72b2721d7d300c1bd6377db558eac08f57e7dc9e6",
    "projection_sha256": "f5c1ffdfb92df2c04ac17e9a31e38701f2b7a5cac0cd427a2df2aa3e239987fc",
    "scale_sha256": "0b0e327d2f4d1a104c53d6e0a9172cf532028383e82cdf6d70537cb83092c63f",
}


def _finite_binary32_codes(seed: int, count: int) -> tuple[int, ...]:
    generator = random.Random(seed)
    result: list[int] = []
    while len(result) < count:
        code = generator.randrange(1 << 32)
        if code & 0x7F800000 != 0x7F800000:
            result.append(code)
    return tuple(result)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _read_codes(path: Path, bits: int) -> tuple[int, ...]:
    payload = path.read_bytes()
    width = bits // 8
    assert len(payload) % width == 0
    return tuple(
        int.from_bytes(payload[offset : offset + width], "little")
        for offset in range(0, len(payload), width)
    )


def _reshape_codes(
    values: tuple[int, ...], shape: tuple[int, ...]
) -> tuple[object, ...]:
    if len(shape) == 1:
        assert len(values) == shape[0]
        return tuple(values)
    stride = 1
    for extent in shape[1:]:
        stride *= extent
    assert len(values) == shape[0] * stride
    return tuple(
        _reshape_codes(values[index * stride : (index + 1) * stride], shape[1:])
        for index in range(shape[0])
    )


def _flatten_codes(value: object):
    if type(value) is int:
        yield value
        return
    assert type(value) is tuple
    for item in value:
        yield from _flatten_codes(item)


def _code_sha256(value: object, bits: int) -> str:
    width = bits // 8
    payload = b"".join(
        code.to_bytes(width, "little") for code in _flatten_codes(value)
    )
    return hashlib.sha256(payload).hexdigest()


def _sparse_fixture(
    *, seed: int, token_count: int
) -> tuple[
    tuple[tuple[tuple[int, ...], ...], ...],
    tuple[tuple[int, ...], ...],
    tuple[int, ...],
    tuple[int, ...],
]:
    generator = random.Random(seed)
    bf16_palette = (
        0x0000,
        0x8000,
        0x0001,
        0x8001,
        0x3E00,
        0xBE00,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
    )
    weight_palette = (
        0,
        0x39800000,
        0xB9800000,
        0x3E800000,
        0xBE800000,
        0x3F000000,
        0xBF000000,
        0x3F800000,
        0xBF800000,
    )
    tokens: list[tuple[tuple[int, ...], ...]] = []
    for _ in range(token_count):
        flattened = [0] * _FLAT
        for index in generator.sample(range(_FLAT), 48):
            flattened[index] = generator.choice(bf16_palette)
        tokens.append(
            tuple(
                tuple(flattened[stream * _HIDDEN : (stream + 1) * _HIDDEN])
                for stream in range(hc_reference.HC_MULTIPLIER)
            )
        )

    projection: list[tuple[int, ...]] = []
    for _ in range(hc_reference.MIX_PARAMETER_COUNT):
        row = [0] * _FLAT
        for index in generator.sample(range(_FLAT), 64):
            row[index] = generator.choice(weight_palette)
        projection.append(tuple(row))

    scales = (0x3F800000, 0x3F000000, 0x3F800000)
    base_palette = (0, 0x3E800000, 0xBE800000, 0x3F000000, 0xBF000000)
    bases = tuple(
        generator.choice(base_palette) for _ in range(hc_reference.MIX_PARAMETER_COUNT)
    )
    return tuple(tokens), tuple(projection), scales, bases


def _assert_complete_result_equal(
    reference: hc_reference.HCPreResult,
    service: hc_service.HCPreServiceResult,
) -> None:
    assert service.branch_codes == (reference.branch_bf16_codes,)
    assert service.post_codes == (reference.post_binary32_codes,)
    assert service.combination_codes == (reference.comb_binary32_codes,)
    assert service.residual_codes == (reference.residual_bf16_codes,)
    assert service.rms_mean_codes == (reference.diagnostics.mean_square_codes,)
    assert service.rms_inverse_codes == (reference.diagnostics.inverse_rms_codes,)
    assert service.projection_codes == (reference.diagnostics.projection_codes,)
    assert service.mix_codes == (reference.diagnostics.normalized_projection_codes,)
    assert service.pre_codes == (reference.pre_binary32_codes,)
    assert service.stable_softmax_codes == (reference.diagnostics.split.softmax_codes,)
    assert service.branch_saturation_count == reference.branch_output_saturation_count
    reference_counters = asdict(reference.counters)
    assert reference_counters.pop("hc_pre_token_count") == len(
        reference.branch_bf16_codes
    )
    assert dict(service.logical_counters) == reference_counters


def test_hc_pre_reference_and_service_do_not_import_each_other() -> None:
    reference_source = inspect.getsource(hc_reference)
    service_source = inspect.getsource(hc_service)
    assert "runtime.service_engine" not in reference_source
    assert "runtime.reference" not in service_source
    assert "from .formats" in reference_source
    assert "from decimal import" in service_source


def test_hc_pre_transcendentals_match_on_deterministic_binary32_corpus() -> None:
    corpus = _finite_binary32_codes(0x48504352, 4096)
    for code in corpus:
        assert hc_reference.binary32_sigmoid_rne(code) == hc_service.cr32_sigmoid(code)
        if code & 0x80000000 or code & 0x7FFFFFFF == 0:
            assert hc_reference.binary32_exp_rne(code) == hc_service.cr32_exp(code)


def test_hc_pre_sinkhorn_matches_on_asymmetric_deterministic_corpus() -> None:
    generator = random.Random(0x53494E4B)
    for _ in range(64):
        fields = tuple(
            encode_binary32_rne(Fraction(generator.randrange(-640, 641), 32))
            for _ in range(16)
        )
        matrix = tuple(tuple(fields[row * 4 : row * 4 + 4]) for row in range(4))
        reference = hc_reference.hc_split_sinkhorn_binary32(
            ((0,) * hc_reference.MIX_PARAMETER_COUNT,),
            (0, 0, 0),
            (0,) * 8 + fields,
        )
        service_softmax, service_final = hc_service.sinkhorn20(matrix)
        assert reference.diagnostics.softmax_codes[0] == service_softmax
        assert reference.comb_binary32_codes[0] == service_final


def test_hc_pre_complete_sparse_operator_matches_every_observable() -> None:
    tokens, projection, scales, bases = _sparse_fixture(
        seed=0x48434655,
        token_count=2,
    )
    reference = hc_reference.hc_pre_bf16(
        tokens,
        projection,
        scales,
        bases,
    )
    service = hc_service.execute_hc_pre(
        (tokens,),
        projection,
        scales,
        bases,
    )
    _assert_complete_result_equal(reference, service)


def test_hc_pre_one_bit_parameter_mutation_is_visible_in_both_lanes() -> None:
    token = ((_ZERO_STREAM,) * hc_reference.HC_MULTIPLIER,)
    projection = (_ZERO_PROJECTION_ROW,) * hc_reference.MIX_PARAMETER_COUNT
    scales = (0, 0, 0)
    baseline_bases = (0,) * hc_reference.MIX_PARAMETER_COUNT
    mutated_bases = list(baseline_bases)
    # ``0x40000000`` has exactly one set bit and encodes binary32 2.0.  A
    # least-significant subnormal bit flip is retained by the affine evidence
    # but intentionally disappears at correctly rounded sigmoid, so use a
    # single-bit mutation that must remain visible at the architectural output.
    mutated_bases[0] = 0x40000000

    reference_baseline = hc_reference.hc_pre_bf16(
        token,
        projection,
        scales,
        baseline_bases,
    )
    reference_mutated = hc_reference.hc_pre_bf16(
        token,
        projection,
        scales,
        tuple(mutated_bases),
    )
    service_baseline = hc_service.execute_hc_pre(
        (token,),
        projection,
        scales,
        baseline_bases,
    )
    service_mutated = hc_service.execute_hc_pre(
        (token,),
        projection,
        scales,
        tuple(mutated_bases),
    )

    _assert_complete_result_equal(reference_baseline, service_baseline)
    _assert_complete_result_equal(reference_mutated, service_mutated)
    assert (
        reference_baseline.diagnostics.split.pre_affine_codes
        != reference_mutated.diagnostics.split.pre_affine_codes
    )
    assert service_baseline.pre_codes != service_mutated.pre_codes


def test_official_lookup_derived_token_matches_at_every_bounded_extent() -> None:
    """Replay one independently verified checkpoint row at ``T=1..4``.

    Repeating the same authentic token deliberately isolates transaction extent
    from token-value variation.  The sparse development corpus above supplies
    heterogeneous values; this test supplies the locked-checkpoint provenance.
    """

    default_root = Path.home() / ".cache/opentallas/deepseek-v4-flash-0731"
    root = Path(os.environ.get(_OFFICIAL_EVIDENCE_ENV, default_root))
    application_root = root / "hc-pre-canonical"
    request_root = root / "hc-pre-request"
    required = (
        root / "hc-pre-composition-v1.json",
        application_root / "canonical_application.json",
        application_root / "canonical_verification.json",
        request_root / "request_manifest.json",
        request_root / "input/hc_hidden.bf16le",
        application_root / "ranks/rank-000/layers.0.hc_attn_base.bin",
        application_root / "ranks/rank-000/layers.0.hc_attn_fn.bin",
        application_root / "ranks/rank-000/layers.0.hc_attn_scale.bin",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        pytest.skip(
            f"set {_OFFICIAL_EVIDENCE_ENV} for the HC_PRE official corpus; "
            f"missing {missing}"
        )

    composition = json.loads(required[0].read_bytes())
    application = json.loads(required[1].read_bytes())
    verification = json.loads(required[2].read_bytes())
    request = json.loads(required[3].read_bytes())
    assert composition["status"] == (
        "official_tokenizer_lookup_differential_composition_verified"
    )
    assert composition["tokenizer"]["token_ids"] == [[19923]]
    assert application["application_id"] == (
        "195f060eafeefbe414eb30525618a42e765c882c39abdcd8885be644882734a1"
    )
    assert verification["verification_id"] == (
        "82c453a978017140b2c15fe2b782a7e04698ce55034376d169bfbb54a85dbbb4"
    )
    assert verification["status"] == "full_assignment_match"
    assert request["input"]["sha256"] == _OFFICIAL_SOURCE_SHA256["input_sha256"]
    assert request["input"]["shape"] == [1, 1, 4, 4096]

    base_path = required[5]
    projection_path = required[6]
    scale_path = required[7]
    input_path = required[4]
    source = {
        "base_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "projection_sha256": hashlib.sha256(
            projection_path.read_bytes()
        ).hexdigest(),
        "scale_sha256": hashlib.sha256(scale_path.read_bytes()).hexdigest(),
    }
    assert source == _OFFICIAL_SOURCE_SHA256
    base = _read_codes(base_path, 32)
    projection = _reshape_codes(
        _read_codes(projection_path, 32),
        (24, 16_384),
    )
    scale = _read_codes(scale_path, 32)
    token = _reshape_codes(_read_codes(input_path, 16), (4, 4096))

    records = []
    for token_count in range(1, 5):
        tokens = (token,) * token_count
        reference = hc_reference.hc_pre_bf16(
            tokens, projection, scale, base  # type: ignore[arg-type]
        )
        service = hc_service.execute_hc_pre(
            (tokens,), projection, scale, base  # type: ignore[arg-type]
        )
        comparisons = {
            "branch": (reference.branch_bf16_codes, service.branch_codes[0], 16),
            "combination": (
                reference.comb_binary32_codes,
                service.combination_codes[0],
                32,
            ),
            "mix": (
                reference.diagnostics.normalized_projection_codes,
                service.mix_codes[0],
                32,
            ),
            "post": (reference.post_binary32_codes, service.post_codes[0], 32),
            "pre": (reference.pre_binary32_codes, service.pre_codes[0], 32),
            "projection": (
                reference.diagnostics.projection_codes,
                service.projection_codes[0],
                32,
            ),
            "residual": (
                reference.residual_bf16_codes,
                service.residual_codes[0],
                16,
            ),
            "rms_inverse": (
                reference.diagnostics.inverse_rms_codes,
                service.rms_inverse_codes[0],
                32,
            ),
            "rms_mean": (
                reference.diagnostics.mean_square_codes,
                service.rms_mean_codes[0],
                32,
            ),
            "stable_softmax": (
                reference.diagnostics.split.softmax_codes,
                service.stable_softmax_codes[0],
                32,
            ),
        }
        payload_hashes = {}
        for name, (expected, observed, bits) in comparisons.items():
            assert expected == observed, name
            payload_hashes[name] = _code_sha256(expected, bits)
        counters = asdict(reference.counters)
        assert counters.pop("hc_pre_token_count") == token_count
        assert counters == dict(service.logical_counters)
        record = {
            "branch_saturation_count": reference.branch_output_saturation_count,
            "logical_counters_sha256": hashlib.sha256(
                _canonical_bytes(counters)
            ).hexdigest(),
            "payload_sha256": payload_hashes,
            "status": "exact_reference_service_match",
            "token_count": token_count,
        }
        record["record_sha256"] = hashlib.sha256(
            _canonical_bytes(record)
        ).hexdigest()
        records.append(record)

    assert tuple(record["record_sha256"] for record in records) == (
        _OFFICIAL_RECORD_SHA256
    )
    body = {"records": records, "source": source}
    assert hashlib.sha256(_canonical_bytes(body)).hexdigest() == (
        _OFFICIAL_EVIDENCE_SHA256
    )
