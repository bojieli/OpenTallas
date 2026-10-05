from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction
import hashlib
import math
import os
from pathlib import Path
import random

import pytest

from runtime.reference.formats import decode_binary32, encode_binary32_rne
from runtime.reference.sampling import (
    BINARY32_BYTES,
    BINARY32_MINIMUM_TEMPERATURE,
    BINARY32_ONE,
    DEEPSEEK_V4_MAX_BATCH_SIZE,
    DEEPSEEK_V4_VOCABULARY_SIZE,
    ENTROPY_ORDER,
    GENERATION_SOURCE_SHA256,
    GREEDY_NUMERIC_PROFILE,
    LOGIT_DTYPE_SOURCE_ANCHOR,
    MODEL_SOURCE_SHA256,
    NONCLAIMS,
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    OFFICIAL_RNG_SEED,
    PYTORCH_STOCHASTIC_EQUIVALENCE,
    REQUIREMENTS_SOURCE_ANCHOR,
    REQUIREMENTS_SOURCE_SHA256,
    RNG_SEED_SOURCE_ANCHOR,
    SAMPLE_SOURCE_ANCHOR,
    SAMPLE_SOURCE_SHA256,
    SOURCE_EQUIVALENCE_BOUNDARY,
    TARGET_STOCHASTIC_NUMERIC_PROFILE,
    TIE_POLICY,
    ExplicitExponentialEntropy,
    SamplingFunctionalCounters,
    SamplingReferenceError,
    deepseek_v4_sample_binary32,
)
from runtime.reference.transcendental import binary32_exp_general_rne


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _value(code: int) -> Fraction:
    decoded = decode_binary32(code)
    assert decoded.value is not None
    return decoded.value


def _matrix_digest(
    codes: tuple[int, ...],
    *,
    rows: int,
    columns: int,
    domain: bytes,
) -> str:
    digest = hashlib.sha256()
    digest.update(domain)
    digest.update(rows.to_bytes(8, "little"))
    digest.update(columns.to_bytes(8, "little"))
    for code in codes:
        digest.update(code.to_bytes(4, "little"))
    return digest.hexdigest()


def _independent_target_row(
    logits: tuple[int, ...],
    draws: tuple[int, ...],
    temperature: int,
) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    scaled = tuple(
        encode_binary32_rne(_value(logit) / _value(temperature)) for logit in logits
    )
    maximum = max(_value(code) for code in scaled)
    exponentials = tuple(
        binary32_exp_general_rne(encode_binary32_rne(_value(code) - maximum))
        for code in scaled
    )
    level = exponentials
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            encode_binary32_rne(_value(level[index]) + _value(level[index + 1]))
            for index in range(0, len(level), 2)
        )
    denominator = level[0]
    probabilities = tuple(
        encode_binary32_rne(_value(code) / _value(denominator)) for code in exponentials
    )
    races = tuple(
        encode_binary32_rne(_value(probability) / _value(draw))
        for probability, draw in zip(probabilities, draws, strict=True)
    )
    token = max(range(len(races)), key=lambda index: (_value(races[index]), -index))
    return token, probabilities, races


def _source_root() -> Path | None:
    configured = os.environ.get("OPENTALLAS_DEEPSEEK_V4_SNAPSHOT")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.append(
        Path.home()
        / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / OFFICIAL_REVISION
    )
    return next((candidate for candidate in candidates if candidate.is_dir()), None)


def _sample_function(source: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "sample"
    ]
    assert len(functions) == 1
    return functions[0]


def test_reference_is_bound_to_the_pinned_release_and_numeric_profiles() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert GENERATION_SOURCE_SHA256 == (
        "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
    )
    assert SAMPLE_SOURCE_SHA256 == (
        "da6030c7ebf858d615fcdf6b7efb88b5a98f53849b98ffc0815b4eccd467955a"
    )
    assert REQUIREMENTS_SOURCE_SHA256 == (
        "857e0b8b58e41cabe16e55bf4ab7ff791677c53b25f0f3e104ef85227cd11eab"
    )
    assert OFFICIAL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert OFFICIAL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert SAMPLE_SOURCE_ANCHOR == "inference/model.py:939-946:sample"
    assert LOGIT_DTYPE_SOURCE_ANCHOR == "inference/model.py:719-740:ParallelHead"
    assert REQUIREMENTS_SOURCE_ANCHOR == "inference/requirements.txt:1"
    assert RNG_SEED_SOURCE_ANCHOR == "inference/generate.py:79:torch.manual_seed"
    assert OFFICIAL_RNG_SEED == 33_377_335
    assert DEEPSEEK_V4_VOCABULARY_SIZE == 129_280
    assert DEEPSEEK_V4_MAX_BATCH_SIZE == 4
    assert BINARY32_MINIMUM_TEMPERATURE == _f32(Fraction(1, 100_000))
    assert GREEDY_NUMERIC_PROFILE == "finite_binary32_first_index_argmax_v1"
    assert TARGET_STOCHASTIC_NUMERIC_PROFILE.startswith("cr32_exp_balanced_softmax")
    assert "unresolved" in PYTORCH_STOCHASTIC_EQUIVALENCE
    assert ENTROPY_ORDER == "row_major_batch_then_vocabulary"
    assert TIE_POLICY == "maximum_value_then_smallest_vocabulary_index"


def test_pinned_sample_source_structure_and_unpinned_backend_boundary() -> None:
    root = _source_root()
    if root is None:
        pytest.skip("pinned official DeepSeek V4 snapshot is unavailable")
    model_path = root / "inference/model.py"
    generation_path = root / "inference/generate.py"
    requirements_path = root / "inference/requirements.txt"
    model_payload = model_path.read_bytes()
    generation_payload = generation_path.read_bytes()
    requirements_payload = requirements_path.read_bytes()
    assert hashlib.sha256(model_payload).hexdigest() == MODEL_SOURCE_SHA256
    assert hashlib.sha256(generation_payload).hexdigest() == GENERATION_SOURCE_SHA256
    assert (
        hashlib.sha256(requirements_payload).hexdigest() == REQUIREMENTS_SOURCE_SHA256
    )
    assert requirements_payload.splitlines()[0] == b"torch>=2.10.0"
    assert b"torch==" not in requirements_payload

    source = model_payload.decode("utf-8")
    model_tree = ast.parse(source)
    function = _sample_function(source)
    lines = model_payload.splitlines(keepends=True)
    function_payload = b"".join(lines[function.lineno - 1 : function.end_lineno])
    assert hashlib.sha256(function_payload).hexdigest() == SAMPLE_SOURCE_SHA256

    statements = function.body
    assert isinstance(statements[0], ast.Expr)  # docstring
    greedy = statements[1]
    assert isinstance(greedy, ast.If)
    assert isinstance(greedy.test, ast.Compare)
    assert isinstance(greedy.test.ops[0], ast.Eq)
    assert isinstance(greedy.body[0], ast.Return)
    greedy_expression = ast.unparse(greedy.body[0].value)
    assert greedy_expression == "logits.argmax(dim=-1)"

    temperature_assignment = statements[2]
    assert isinstance(temperature_assignment, ast.Assign)
    assert ast.unparse(temperature_assignment.value) == (
        "logits / max(temperature, 1e-05)"
    )
    probability_assignment = statements[3]
    assert isinstance(probability_assignment, ast.Assign)
    assert ast.unparse(probability_assignment.value) == (
        "torch.softmax(logits, dim=-1, dtype=torch.float32)"
    )
    stochastic_return = statements[4]
    assert isinstance(stochastic_return, ast.Return)
    assert ast.unparse(stochastic_return.value) == (
        "probs.div_(torch.empty_like(probs).exponential_(1)).argmax(dim=-1)"
    )

    model_args = next(
        node
        for node in model_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ModelArgs"
    )
    defaults = {
        statement.target.id: statement.value.value
        for statement in model_args.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and isinstance(statement.value, ast.Constant)
    }
    assert defaults["max_batch_size"] == DEEPSEEK_V4_MAX_BATCH_SIZE
    assert defaults["vocab_size"] == DEEPSEEK_V4_VOCABULARY_SIZE
    parallel_head = next(
        node
        for node in model_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ParallelHead"
    )
    parallel_source = ast.unparse(parallel_head)
    assert "dtype=torch.float32" in parallel_source
    assert "F.linear(x.float(), self.weight)" in parallel_source

    generation_tree = ast.parse(generation_payload.decode("utf-8"))
    seed_calls = [
        node
        for node in ast.walk(generation_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "torch"
        and node.func.attr == "manual_seed"
    ]
    assert len(seed_calls) == 1
    assert seed_calls[0].lineno == 79
    assert len(seed_calls[0].args) == 1
    assert isinstance(seed_calls[0].args[0], ast.Constant)
    assert seed_calls[0].args[0].value == OFFICIAL_RNG_SEED


def test_greedy_is_exact_first_index_argmax_and_consumes_no_entropy() -> None:
    entropy = ExplicitExponentialEntropy.from_codes((_f32(1), _f32(2)))
    result = deepseek_v4_sample_binary32(
        (
            (_f32(-2), _f32(7), _f32(7), _f32(6)),
            (0x80000000, 0, _f32(-1), _f32(-1)),
        ),
        0x80000000,
        entropy=entropy,
        vocabulary_size=4,
    )
    assert result.token_ids == (1, 0)
    assert result.batch_size == 2
    assert result.vocabulary_size == 4
    assert result.mode == "greedy_argmax"
    assert result.status == "pinned_source_greedy_exact"
    assert result.source_equivalence == "bit_exact_for_validated_finite_binary32_inputs"
    assert result.numeric_profile == GREEDY_NUMERIC_PROFILE
    assert result.effective_temperature_binary32 is None
    assert result.next_entropy is entropy
    assert result.entropy_offset_before == result.entropy_offset_after == 0
    assert result.counters == SamplingFunctionalCounters(
        rows=2,
        vocabulary_values=8,
        logit_read_bytes=8 * BINARY32_BYTES,
        temperature_zero_comparisons=1,
        temperature_floor_comparisons=0,
        temperature_divides=0,
        softmax_max_comparisons=0,
        softmax_subtracts=0,
        softmax_exp_evaluations=0,
        softmax_reduction_adds=0,
        softmax_padding_values=0,
        probability_divides=0,
        exponential_draws_consumed=0,
        entropy_read_bytes=0,
        exponential_race_divides=0,
        argmax_comparisons=6,
        token_writes=2,
    )


def test_greedy_matches_independent_exact_randomized_oracle() -> None:
    generator = random.Random(0x5341_4D50_4C45)
    palette = (
        0,
        0x80000000,
        0x00000001,
        0x80000001,
        _f32(Fraction(1, 8)),
        _f32(Fraction(-1, 8)),
        _f32(1),
        _f32(-1),
        _f32(32),
        _f32(-32),
        0x7F7FFFFF,
        0xFF7FFFFF,
    )
    for _ in range(300):
        batch_size = generator.randint(1, DEEPSEEK_V4_MAX_BATCH_SIZE)
        width = generator.randint(1, 32)
        rows = tuple(
            tuple(generator.choice(palette) for _ in range(width))
            for _ in range(batch_size)
        )
        expected = tuple(
            max(range(width), key=lambda index: (_value(row[index]), -index))
            for row in rows
        )
        assert (
            deepseek_v4_sample_binary32(
                rows,
                0,
                vocabulary_size=width,
            ).token_ids
            == expected
        )


def test_greedy_covers_the_complete_official_vocabulary_shape() -> None:
    row = (0,) * (DEEPSEEK_V4_VOCABULARY_SIZE - 1) + (_f32(1),)
    result = deepseek_v4_sample_binary32((row,), 0)
    assert result.token_ids == (DEEPSEEK_V4_VOCABULARY_SIZE - 1,)
    assert result.counters.vocabulary_values == DEEPSEEK_V4_VOCABULARY_SIZE
    assert result.counters.argmax_comparisons == DEEPSEEK_V4_VOCABULARY_SIZE - 1


def test_nonzero_source_exact_request_fails_closed_before_entropy_consumption() -> None:
    entropy = ExplicitExponentialEntropy.from_codes((_f32(1), _f32(2)))
    with pytest.raises(
        SamplingReferenceError,
        match="exact nonzero-temperature PyTorch/CUDA replay is unresolved",
    ):
        deepseek_v4_sample_binary32(
            ((0, 0),),
            BINARY32_ONE,
            entropy=entropy,
            vocabulary_size=2,
        )
    assert entropy.offset == 0
    assert entropy.remaining == 2


def test_explicit_target_race_is_row_major_deterministic_and_hash_bound() -> None:
    prefix = _f32(99)
    draws = (
        _f32(4),
        _f32(2),
        _f32(1),
        _f32(3),
        _f32(3),
        _f32(8),
    )
    stream = ExplicitExponentialEntropy((prefix, *draws, _f32(77)), offset=1)
    kwargs = {
        "entropy": stream,
        "vocabulary_size": 3,
        "require_pytorch_cuda_equivalence": False,
    }
    logits = ((0, 0, 0), (0, 0, 0))
    result = deepseek_v4_sample_binary32(logits, BINARY32_ONE, **kwargs)
    replay = deepseek_v4_sample_binary32(logits, BINARY32_ONE, **kwargs)
    assert result == replay
    assert hash(result) == hash(replay)
    assert result.token_ids == (2, 0)
    assert result.batch_size == 2
    assert result.vocabulary_size == 3
    assert result.mode == "explicit_exponential_race_target_adaptation"
    assert result.status == "deterministic_target_adaptation_executed"
    assert result.source_equivalence == PYTORCH_STOCHASTIC_EQUIVALENCE
    assert result.numeric_profile == TARGET_STOCHASTIC_NUMERIC_PROFILE
    assert result.effective_temperature_binary32 == BINARY32_ONE
    assert result.entropy_stream_sha256 == stream.stream_sha256
    assert result.entropy_offset_before == 1
    assert result.entropy_offset_after == 7
    assert result.next_entropy == ExplicitExponentialEntropy(
        stream.binary32_codes, offset=7
    )
    assert stream.offset == 1
    assert result.probabilities_sha256 is not None
    assert result.race_scores_sha256 is not None
    assert result.counters == SamplingFunctionalCounters(
        rows=2,
        vocabulary_values=6,
        logit_read_bytes=24,
        temperature_zero_comparisons=1,
        temperature_floor_comparisons=1,
        temperature_divides=6,
        softmax_max_comparisons=4,
        softmax_subtracts=6,
        softmax_exp_evaluations=6,
        softmax_reduction_adds=6,
        softmax_padding_values=2,
        probability_divides=6,
        exponential_draws_consumed=6,
        entropy_read_bytes=24,
        exponential_race_divides=6,
        argmax_comparisons=4,
        token_writes=2,
    )


def test_target_rounding_hashes_and_non_power_of_two_reduction_match_oracle() -> None:
    logits = (
        tuple(_f32(value) for value in (-2, -1, 0, 1, 2)),
        tuple(_f32(value) for value in (3, 1, -4, 0, 2)),
    )
    draws = (
        tuple(_f32(value) for value in (1, 2, 3, 4, 5)),
        tuple(_f32(value) for value in (6, 5, 4, 3, 2)),
    )
    temperature = _f32(2)
    oracle = tuple(
        _independent_target_row(row, draw_row, temperature)
        for row, draw_row in zip(logits, draws, strict=True)
    )
    result = deepseek_v4_sample_binary32(
        logits,
        temperature,
        entropy=ExplicitExponentialEntropy.from_codes(
            tuple(code for row in draws for code in row)
        ),
        vocabulary_size=5,
        require_pytorch_cuda_equivalence=False,
    )
    probabilities = tuple(code for _, row, _ in oracle for code in row)
    races = tuple(code for _, _, row in oracle for code in row)
    assert result.token_ids == tuple(token for token, _, _ in oracle)
    assert result.probabilities_sha256 == _matrix_digest(
        probabilities,
        rows=2,
        columns=5,
        domain=b"opentallas.deepseek_v4_sample_probabilities.v1\x00",
    )
    assert result.logits_sha256 == _matrix_digest(
        tuple(code for row in logits for code in row),
        rows=2,
        columns=5,
        domain=b"opentallas.deepseek_v4_sample_logits.v1\x00",
    )
    assert result.race_scores_sha256 == _matrix_digest(
        races,
        rows=2,
        columns=5,
        domain=b"opentallas.deepseek_v4_sample_race_scores.v1\x00",
    )
    # binary32_balanced_sum pads widths 5 -> 6 and 3 -> 4: two pads and
    # 3 + 2 + 1 = 6 additions per row, not a full eight-leaf tree.
    assert result.counters.softmax_padding_values == 4
    assert result.counters.softmax_reduction_adds == 12


@pytest.mark.parametrize(
    "temperature",
    [
        _f32(-100),
        _f32(Fraction(-1, 1_000_000)),
        _f32(Fraction(1, 1_000_000)),
        BINARY32_MINIMUM_TEMPERATURE,
    ],
)
def test_nonzero_temperature_preserves_source_floor_semantics(
    temperature: int,
) -> None:
    stream = ExplicitExponentialEntropy.from_codes((_f32(2), _f32(1)))
    result = deepseek_v4_sample_binary32(
        ((0, 0),),
        temperature,
        entropy=stream,
        vocabulary_size=2,
        require_pytorch_cuda_equivalence=False,
    )
    assert result.token_ids == (1,)
    assert result.effective_temperature_binary32 == BINARY32_MINIMUM_TEMPERATURE


def test_target_race_matches_independent_exponential_race_oracle_away_from_ties() -> (
    None
):
    generator = random.Random(0x4558_5052_4143_45)
    checked = 0
    while checked < 200:
        width = generator.randint(2, 10)
        logits_values = tuple(generator.randint(-5, 5) for _ in range(width))
        draw_values = tuple(generator.randint(1, 16) for _ in range(width))
        exact_scores = tuple(
            float(logit) - math.log(draw)
            for logit, draw in zip(logits_values, draw_values, strict=True)
        )
        ordered = sorted(exact_scores, reverse=True)
        if ordered[0] - ordered[1] < 0.05:
            continue
        expected = max(range(width), key=lambda index: (exact_scores[index], -index))
        result = deepseek_v4_sample_binary32(
            (tuple(_f32(value) for value in logits_values),),
            BINARY32_ONE,
            entropy=ExplicitExponentialEntropy.from_codes(
                tuple(_f32(value) for value in draw_values)
            ),
            vocabulary_size=width,
            require_pytorch_cuda_equivalence=False,
        )
        assert result.token_ids == (expected,)
        checked += 1


def test_target_race_ties_select_the_smallest_vocabulary_index() -> None:
    result = deepseek_v4_sample_binary32(
        ((0, 0, 0, 0),),
        BINARY32_ONE,
        entropy=ExplicitExponentialEntropy.from_codes((_f32(3),) * 4),
        vocabulary_size=4,
        require_pytorch_cuda_equivalence=False,
    )
    assert result.token_ids == (0,)


def test_entropy_stream_digest_and_functional_consumption_are_reproducible() -> None:
    codes = (_f32(1), _f32(2), _f32(3))
    stream = ExplicitExponentialEntropy.from_codes(codes)
    digest = hashlib.sha256()
    digest.update(b"opentallas.explicit_exponential_entropy.v1\x00")
    digest.update((1).to_bytes(8, "little"))
    digest.update((3).to_bytes(8, "little"))
    for code in codes:
        digest.update(code.to_bytes(4, "little"))
    assert stream.stream_sha256 == digest.hexdigest()
    values, continuation = stream.take(2)
    assert values == codes[:2]
    assert continuation == ExplicitExponentialEntropy(codes, offset=2)
    assert continuation.stream_sha256 == stream.stream_sha256
    assert stream.offset == 0


@pytest.mark.parametrize(
    ("codes", "offset", "match"),
    [
        ([BINARY32_ONE], 0, "immutable tuple"),
        ((True,), 0, "exact 32-bit"),
        ((-1,), 0, "exact 32-bit"),
        ((1 << 32,), 0, "exact 32-bit"),
        ((0,), 0, "positive finite"),
        ((0x80000000,), 0, "positive finite"),
        ((0xBF800000,), 0, "positive finite"),
        ((0x7F800000,), 0, "finite binary32"),
        ((0x7FC00000,), 0, "finite binary32"),
        ((BINARY32_ONE,), True, "entropy offset"),
        ((BINARY32_ONE,), -1, "entropy offset"),
        ((BINARY32_ONE,), 2, "entropy offset"),
    ],
)
def test_malformed_exponential_entropy_poisons_at_construction(
    codes: object,
    offset: object,
    match: str,
) -> None:
    with pytest.raises(SamplingReferenceError, match=match):
        ExplicitExponentialEntropy(codes, offset)  # type: ignore[arg-type]


def test_entropy_exhaustion_and_missing_stream_fail_without_partial_state() -> None:
    short = ExplicitExponentialEntropy.from_codes((BINARY32_ONE,))
    with pytest.raises(SamplingReferenceError, match="entropy exhausted"):
        deepseek_v4_sample_binary32(
            ((0, 0),),
            BINARY32_ONE,
            entropy=short,
            vocabulary_size=2,
            require_pytorch_cuda_equivalence=False,
        )
    assert short.offset == 0
    with pytest.raises(SamplingReferenceError, match="requires one exact"):
        deepseek_v4_sample_binary32(
            ((0, 0),),
            BINARY32_ONE,
            vocabulary_size=2,
            require_pytorch_cuda_equivalence=False,
        )


def test_late_row_numeric_poison_keeps_entropy_transaction_atomic() -> None:
    # Row zero completes.  Row one then overflows 0.5 / minimum-subnormal in
    # the race division.  The caller-owned stream must still remain at its
    # original offset, with no partial continuation exposed.
    codes = (
        _f32(99),
        BINARY32_ONE,
        BINARY32_ONE,
        BINARY32_ONE,
        1,
        _f32(77),
    )
    stream = ExplicitExponentialEntropy(codes, offset=1)
    before = (stream, hash(stream), stream.stream_sha256, stream.remaining)
    with pytest.raises(SamplingReferenceError, match="poisoned row 1"):
        deepseek_v4_sample_binary32(
            ((0, 0), (0, 0)),
            BINARY32_ONE,
            entropy=stream,
            vocabulary_size=2,
            require_pytorch_cuda_equivalence=False,
        )
    assert (stream, hash(stream), stream.stream_sha256, stream.remaining) == before
    assert stream.offset == 1


def test_mutable_call_inputs_are_copied_before_result_authority_is_returned() -> None:
    logits = [[0, 0]]
    entropy_codes = [_f32(2), BINARY32_ONE]
    stream = ExplicitExponentialEntropy.from_codes(entropy_codes)
    result = deepseek_v4_sample_binary32(
        logits,
        BINARY32_ONE,
        entropy=stream,
        vocabulary_size=2,
        require_pytorch_cuda_equivalence=False,
    )
    identity = (
        result.token_ids,
        result.logits_sha256,
        result.entropy_stream_sha256,
        result.next_entropy,
        hash(result),
    )
    logits[0][0] = _f32(100)
    entropy_codes[1] = _f32(100)
    assert (
        result.token_ids,
        result.logits_sha256,
        result.entropy_stream_sha256,
        result.next_entropy,
        hash(result),
    ) == identity
    assert stream.binary32_codes == (_f32(2), BINARY32_ONE)


@pytest.mark.parametrize(
    ("logits", "vocabulary_size", "match"),
    [
        (object(), 2, "must be a sequence"),
        ((), 2, "batch size"),
        (((0, 0),) * 5, 2, "batch size"),
        ((object(),), 2, "must be a sequence"),
        (((),), 2, "has width 0"),
        (((0,),), 2, "has width 1"),
        (((0, 0), (0,)), 2, "has width 1"),
        (((True, 0),), 2, "exact 32-bit"),
        (((-1, 0),), 2, "exact 32-bit"),
        ((((1 << 32), 0),), 2, "exact 32-bit"),
        (((0x7F800000, 0),), 2, "finite binary32"),
        (((0xFF800000, 0),), 2, "finite binary32"),
        (((0x7FC00000, 0),), 2, "finite binary32"),
    ],
)
def test_logits_are_exact_finite_rectangular_rank_two(
    logits: object,
    vocabulary_size: int,
    match: str,
) -> None:
    with pytest.raises(SamplingReferenceError, match=match):
        deepseek_v4_sample_binary32(  # type: ignore[arg-type]
            logits,
            0,
            vocabulary_size=vocabulary_size,
        )


@pytest.mark.parametrize(
    ("temperature", "match"),
    [
        (True, "exact 32-bit"),
        (-1, "exact 32-bit"),
        (1 << 32, "exact 32-bit"),
        (0x7F800000, "finite binary32"),
        (0xFF800000, "finite binary32"),
        (0x7FC00000, "finite binary32"),
    ],
)
def test_temperature_is_an_exact_finite_binary32_scalar(
    temperature: object,
    match: str,
) -> None:
    with pytest.raises(SamplingReferenceError, match=match):
        deepseek_v4_sample_binary32(  # type: ignore[arg-type]
            ((0, 0),),
            temperature,
            vocabulary_size=2,
        )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"vocabulary_size": True}, "vocabulary_size"),
        ({"vocabulary_size": 0}, "vocabulary_size"),
        (
            {"vocabulary_size": DEEPSEEK_V4_VOCABULARY_SIZE + 1},
            "vocabulary_size",
        ),
        (
            {"vocabulary_size": 2, "require_pytorch_cuda_equivalence": 1},
            "exact bool",
        ),
        ({"vocabulary_size": 2, "entropy": object()}, "entropy must be"),
    ],
)
def test_control_parameters_are_type_exact(
    kwargs: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(SamplingReferenceError, match=match):
        deepseek_v4_sample_binary32(((0, 0),), 0, **kwargs)  # type: ignore[arg-type]


def test_binary32_numeric_overflow_poisons_instead_of_selecting_nonfinite() -> None:
    stream = ExplicitExponentialEntropy.from_codes((BINARY32_ONE, BINARY32_ONE))
    with pytest.raises(SamplingReferenceError, match="temperature division poisoned"):
        deepseek_v4_sample_binary32(
            ((0x7F7FFFFF, 0),),
            BINARY32_MINIMUM_TEMPERATURE,
            entropy=stream,
            vocabulary_size=2,
            require_pytorch_cuda_equivalence=False,
        )
    tiny_entropy = ExplicitExponentialEntropy.from_codes((1, BINARY32_ONE))
    with pytest.raises(SamplingReferenceError, match="softmax/race poisoned"):
        deepseek_v4_sample_binary32(
            ((0, 0),),
            BINARY32_ONE,
            entropy=tiny_entropy,
            vocabulary_size=2,
            require_pytorch_cuda_equivalence=False,
        )
    assert stream.offset == tiny_entropy.offset == 0


def test_results_counters_and_entropy_continuations_are_deeply_immutable() -> None:
    stream = ExplicitExponentialEntropy.from_codes((BINARY32_ONE, BINARY32_ONE))
    result = deepseek_v4_sample_binary32(
        ((0, 0),),
        BINARY32_ONE,
        entropy=stream,
        vocabulary_size=2,
        require_pytorch_cuda_equivalence=False,
    )
    with pytest.raises(FrozenInstanceError):
        result.status = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.counters.rows = 99  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.next_entropy.offset = 0  # type: ignore[union-attr,misc]
    assert isinstance(result.token_ids, tuple)
    assert isinstance(result.nonclaims, tuple)
    assert isinstance(result.source_equivalence_boundary, tuple)
    assert hash(result)


def test_public_counter_constructor_rejects_type_and_reconciliation_mutations() -> None:
    counters = deepseek_v4_sample_binary32(
        ((0, 0),),
        0,
        vocabulary_size=2,
    ).counters
    with pytest.raises(SamplingReferenceError, match="exact nonnegative integer"):
        replace(counters, rows=True)
    with pytest.raises(SamplingReferenceError, match="do not reconcile"):
        replace(counters, logit_read_bytes=counters.logit_read_bytes + 4)
    with pytest.raises(SamplingReferenceError, match="do not reconcile"):
        replace(counters, token_writes=0)
    with pytest.raises(SamplingReferenceError, match="do not reconcile"):
        replace(counters, exponential_draws_consumed=1)


def test_public_result_constructor_rejects_mutability_and_overclaims() -> None:
    greedy = deepseek_v4_sample_binary32(
        ((0, 0),),
        0,
        vocabulary_size=2,
    )
    with pytest.raises(SamplingReferenceError, match="immutable tuple"):
        replace(greedy, token_ids=[0])
    with pytest.raises(SamplingReferenceError, match=r"token_ids\[0\]"):
        replace(greedy, token_ids=(2,))
    with pytest.raises(SamplingReferenceError, match="greedy sampling result metadata"):
        replace(greedy, status="full_model_sampling_verified")
    with pytest.raises(SamplingReferenceError, match="source-equivalence boundary"):
        replace(greedy, source_equivalence_boundary=("bit exact everywhere",))
    with pytest.raises(SamplingReferenceError, match="nonclaims differ"):
        replace(greedy, nonclaims=())

    stochastic = deepseek_v4_sample_binary32(
        ((0, 0),),
        BINARY32_ONE,
        entropy=ExplicitExponentialEntropy.from_codes((BINARY32_ONE, BINARY32_ONE)),
        vocabulary_size=2,
        require_pytorch_cuda_equivalence=False,
    )
    with pytest.raises(
        SamplingReferenceError, match="stochastic target result metadata"
    ):
        replace(
            stochastic,
            source_equivalence="bit_exact_pytorch_cuda_stochastic_replay",
        )
    with pytest.raises(SamplingReferenceError, match="lowercase SHA-256"):
        replace(stochastic, probabilities_sha256="not-a-digest")
    with pytest.raises(SamplingReferenceError, match="does not reconcile atomically"):
        replace(
            stochastic,
            entropy_offset_after=stochastic.entropy_offset_before,
        )


def test_temperature_floor_uses_the_exact_adjacent_binary32_boundary() -> None:
    for temperature, expected in (
        (BINARY32_MINIMUM_TEMPERATURE - 1, BINARY32_MINIMUM_TEMPERATURE),
        (BINARY32_MINIMUM_TEMPERATURE, BINARY32_MINIMUM_TEMPERATURE),
        (BINARY32_MINIMUM_TEMPERATURE + 1, BINARY32_MINIMUM_TEMPERATURE + 1),
    ):
        result = deepseek_v4_sample_binary32(
            ((0, 0),),
            temperature,
            entropy=ExplicitExponentialEntropy.from_codes((BINARY32_ONE, BINARY32_ONE)),
            vocabulary_size=2,
            require_pytorch_cuda_equivalence=False,
        )
        assert result.effective_temperature_binary32 == expected


def test_functional_counter_and_claim_boundary_contain_no_physical_metrics() -> None:
    counter_names = {field.name for field in fields(SamplingFunctionalCounters)}
    forbidden = {
        "cycles",
        "latency",
        "throughput",
        "bandwidth",
        "energy",
        "power",
        "area",
        "density",
        "routing",
        "ppa",
    }
    assert not any(term in name for name in counter_names for term in forbidden)
    joined_boundary = " ".join(SOURCE_EQUIVALENCE_BOUNDARY).lower()
    joined_nonclaims = " ".join(NONCLAIMS).lower()
    assert "torch>=2.10.0" in joined_boundary
    assert "does not derive" in joined_boundary
    assert "no implicit host randomness" in joined_nonclaims
    assert "not cycles" in joined_nonclaims


def test_sampling_module_imports_no_random_or_tensor_backend() -> None:
    path = Path(__file__).resolve().parents[2] / "runtime/reference/sampling.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint(
        {"random", "secrets", "time", "numpy", "torch", "tensorflow", "jax"}
    )
