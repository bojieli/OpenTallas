from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction
import inspect
import random

import runtime.reference.hyper_connection as hc_reference
import runtime.service_engine.hc_pre_numeric as hc_service
from runtime.reference.formats import encode_binary32_rne


_HIDDEN = hc_reference.HIDDEN_SIZE
_FLAT = hc_reference.FLATTENED_WIDTH
_ZERO_STREAM = (0,) * _HIDDEN
_ZERO_PROJECTION_ROW = (0,) * _FLAT


def _finite_binary32_codes(seed: int, count: int) -> tuple[int, ...]:
    generator = random.Random(seed)
    result: list[int] = []
    while len(result) < count:
        code = generator.randrange(1 << 32)
        if code & 0x7F800000 != 0x7F800000:
            result.append(code)
    return tuple(result)


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
