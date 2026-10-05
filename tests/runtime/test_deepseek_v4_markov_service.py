from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import struct

import pytest

from compiler.microcode.deepseek_v4_markov import (
    HEADER,
    PROGRAM_SHA256,
    RECORD,
    assemble,
    encode,
)
from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
)
import runtime.reference.markov_loop as reference
from runtime.reference.sampling import ExplicitExponentialEntropy
import runtime.service_engine.deepseek_v4_markov as service_module
from runtime.service_engine.deepseek_v4_markov import (
    BINARY32_ONE,
    DeepSeekV4MarkovServiceError,
    MarkovServiceEntropy,
    execute_deepseek_v4_markov_program,
)


_PROGRAM = encode(assemble())
_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731"
    / "snapshots"
    / reference.OFFICIAL_REVISION
)
_SHARD = _SNAPSHOT / reference.CHECKPOINT_SHARD


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _shards(
    rows: tuple[tuple[int, ...], ...], world_size: int
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    assert len(rows) % world_size == 0
    width = len(rows) // world_size
    return tuple(
        tuple(rows[rank * width : (rank + 1) * width])
        for rank in range(world_size)
    )


def _zero_logits(batch: int, vocabulary: int) -> tuple:
    return tuple(
        tuple((0,) * vocabulary for _ in range(reference.OFFICIAL_BLOCK_SIZE))
        for _ in range(batch)
    )


def _token_hash(value: tuple[tuple[int, ...], ...]) -> str:
    digest = hashlib.sha256()
    digest.update(b"opentallas.deepseek_v4_markov_output_tokens.v1\x00")
    digest.update(len(value).to_bytes(8, "little"))
    digest.update((len(value[0]) if value else 0).to_bytes(8, "little"))
    for row in value:
        for token in row:
            digest.update(token.to_bytes(4, "little"))
    return digest.hexdigest()


def _small_identity_fixture(
    *, batch: int = 1, world_size: int = 2
) -> tuple[tuple, tuple, tuple]:
    embedding = tuple(
        tuple(_bf16(1 if column == row else 0) for column in range(4))
        for row in range(4)
    )
    head = tuple(
        tuple(_bf16(4 if column == (row - 1) % 4 else 0) for column in range(4))
        for row in range(4)
    )
    return (
        _zero_logits(batch, 4),
        _shards(embedding, world_size),
        _shards(head, world_size),
    )


def _reference_entropy(value: MarkovServiceEntropy) -> ExplicitExponentialEntropy:
    return ExplicitExponentialEntropy(value.binary32_codes, value.offset)


def _assert_service_matches_reference(service: object, expected: object) -> None:
    assert service.output_token_ids == expected.output_token_ids
    assert service.base_logits_binary32_codes == expected.base_logits_binary32_codes
    assert service.markov_embeddings_bf16_codes == (
        expected.markov_embeddings_bf16_codes
    )
    assert service.markov_bias_binary32_codes == (
        expected.markov_bias_binary32_codes
    )
    assert service.adjusted_logits_binary32_codes == (
        expected.adjusted_logits_binary32_codes
    )
    assert service.embedding_weight_bf16_sha256 == (
        expected.embedding_weight_bf16_sha256
    )
    assert service.head_weight_bf16_sha256 == expected.head_weight_bf16_sha256
    assert service.base_logits_binary32_sha256 == (
        expected.base_logits_binary32_sha256
    )
    assert service.markov_bias_binary32_sha256 == (
        expected.markov_bias_binary32_sha256
    )
    assert service.adjusted_logits_binary32_sha256 == (
        expected.adjusted_logits_binary32_sha256
    )
    assert service.markov_embeddings_bf16_sha256 == (
        expected.markov_embeddings_bf16_sha256
    )
    assert service.output_token_ids_sha256 == expected.output_token_ids_sha256
    assert service.sampling_mode == expected.sampling_mode
    assert service.sampling_numeric_profile == expected.sampling_numeric_profile
    assert service.source_equivalence == expected.source_equivalence
    assert service.entropy_stream_sha256 == expected.entropy_stream_sha256
    assert service.entropy_offset_before == expected.entropy_offset_before
    assert service.entropy_offset_after == expected.entropy_offset_after
    service_counters = dict(service.logical_counters)
    for name in expected.counters.__dataclass_fields__:
        assert service_counters[name] == getattr(expected.counters, name)


def _rewrite_record(payload: bytes, index: int, field: int, value: int) -> bytes:
    body = bytearray(payload[HEADER.size :])
    record = list(RECORD.unpack_from(body, index * RECORD.size))
    record[field] = value
    RECORD.pack_into(body, index * RECORD.size, *record)
    header = list(HEADER.unpack_from(payload))
    header[-1] = hashlib.sha256(body).digest()
    return HEADER.pack(*header) + bytes(body)


def _safetensor_header(path: Path) -> tuple[int, dict[str, object]]:
    with path.open("rb") as stream:
        header_length = struct.unpack("<Q", stream.read(8))[0]
        header = json.loads(stream.read(header_length))
    return 8 + header_length, header


def _official_row(name: str, token_id: int) -> tuple[int, ...]:
    if not _SHARD.is_file():
        pytest.skip("local pinned DeepSeek checkpoint shard is unavailable")
    data_start, header = _safetensor_header(_SHARD)
    entry = header[name]
    start, stop = entry["data_offsets"]
    assert stop > start
    row_bytes = reference.OFFICIAL_MARKOV_RANK * 2
    with _SHARD.open("rb") as stream:
        stream.seek(data_start + start + token_id * row_bytes)
        payload = stream.read(row_bytes)
    assert len(payload) == row_bytes
    return struct.unpack(f"<{reference.OFFICIAL_MARKOV_RANK}H", payload)


def test_greedy_microprogram_executes_all_five_causal_steps() -> None:
    base, embedding, head = _small_identity_fixture(batch=2, world_size=2)
    actual = execute_deepseek_v4_markov_program(
        _PROGRAM,
        base,
        (0, 2),
        embedding,
        head,
        temperature_binary32=0,
        tensor_parallel_world_size=2,
    )
    expected = reference.markov_autoregressive_loop_bf16(
        base,
        (0, 2),
        embedding,
        head,
        temperature_binary32=0,
        tensor_parallel_world_size=2,
    )
    _assert_service_matches_reference(actual, expected)
    assert actual.program_sha256 == PROGRAM_SHA256
    assert actual.output_token_ids == (
        (0, 1, 2, 3, 0, 1),
        (2, 3, 0, 1, 2, 3),
    )
    assert actual.output_token_ids_sha256 == (
        "cc0f413587e898b8508fc9ede8925ec37a0fca07c03dd22eb859fc2efb6f67d5"
    )
    assert dict(actual.logical_counters) | {} == dict(actual.semantic_counters)
    assert actual.logical_counters["micro_ops_executed"] == 21
    assert actual.logical_counters["lookup_micro_ops"] == 5
    assert actual.logical_counters["projection_micro_ops"] == 5
    assert actual.logical_counters["bias_add_micro_ops"] == 5
    assert actual.logical_counters["sampling_micro_ops"] == 5
    assert actual.logical_counters["complete_micro_ops"] == 1


def test_greedy_ties_preserve_supplied_entropy_without_consumption() -> None:
    weights = _shards(((0,), (0,)), 1)
    entropy = MarkovServiceEntropy.from_codes((_f32(1), _f32(2)))
    actual = execute_deepseek_v4_markov_program(
        _PROGRAM,
        _zero_logits(1, 2),
        (1,),
        weights,
        weights,
        temperature_binary32=0x80000000,
        entropy=entropy,
        tensor_parallel_world_size=1,
    )
    expected = reference.markov_autoregressive_loop_bf16(
        _zero_logits(1, 2),
        (1,),
        weights,
        weights,
        temperature_binary32=0x80000000,
        entropy=_reference_entropy(entropy),
        tensor_parallel_world_size=1,
    )
    _assert_service_matches_reference(actual, expected)
    assert actual.output_token_ids == ((1, 0, 0, 0, 0, 0),)
    assert actual.next_entropy is entropy
    assert entropy.offset == 0


def test_signed_zero_is_value_equal_for_argmax_and_preserved_in_base_record() -> None:
    weights = _shards(((0,), (0,)), 1)
    base = tuple(
        tuple((0x80000000, 0) for _ in range(reference.OFFICIAL_BLOCK_SIZE))
        for _ in range(1)
    )
    actual = execute_deepseek_v4_markov_program(
        _PROGRAM,
        base,
        (1,),
        weights,
        weights,
        temperature_binary32=0x80000000,
        tensor_parallel_world_size=1,
    )
    expected = reference.markov_autoregressive_loop_bf16(
        base,
        (1,),
        weights,
        weights,
        temperature_binary32=0x80000000,
        tensor_parallel_world_size=1,
    )
    _assert_service_matches_reference(actual, expected)
    assert actual.temperature_binary32 == 0x80000000
    assert actual.base_logits_binary32_codes == base
    assert actual.output_token_ids == ((1, 0, 0, 0, 0, 0),)


def test_projection_and_later_bias_add_rounding_match_independently() -> None:
    small = _bf16(Fraction(1, 1 << 12))
    embedding = (((_bf16(1), small, _bf16(-1)),),)
    head = (((_bf16(1), small, _bf16(1)),),)
    result = execute_deepseek_v4_markov_program(
        _PROGRAM,
        _zero_logits(1, 1),
        (0,),
        embedding,
        head,
        temperature_binary32=0,
        tensor_parallel_world_size=1,
    )
    assert result.markov_bias_binary32_codes == (((0,),) * 5,)

    half_ulp = (((_bf16(Fraction(1, 1 << 24)),),),)
    base = (((0x3F800001,),) * 5,)
    result = execute_deepseek_v4_markov_program(
        _PROGRAM,
        base,
        (0,),
        (((_bf16(1),),),),
        half_ulp,
        temperature_binary32=0,
        tensor_parallel_world_size=1,
    )
    assert result.markov_bias_binary32_codes == (((0x33800000,),) * 5,)
    assert result.adjusted_logits_binary32_codes == (((0x3F800002,),) * 5,)


def test_explicit_stochastic_entropy_threads_through_every_sample_slot() -> None:
    weights = _shards(((0,), (0,)), 1)
    draw_pairs = (
        (_f32(2), _f32(1)),
        (_f32(1), _f32(2)),
        (_f32(3), _f32(1)),
        (_f32(1), _f32(4)),
        (_f32(5), _f32(1)),
    )
    entropy = MarkovServiceEntropy(
        (_f32(9),) + tuple(code for pair in draw_pairs for code in pair),
        offset=1,
    )
    actual = execute_deepseek_v4_markov_program(
        _PROGRAM,
        _zero_logits(1, 2),
        (0,),
        weights,
        weights,
        temperature_binary32=BINARY32_ONE,
        entropy=entropy,
        tensor_parallel_world_size=1,
        require_pytorch_cuda_equivalence=False,
    )
    expected = reference.markov_autoregressive_loop_bf16(
        _zero_logits(1, 2),
        (0,),
        weights,
        weights,
        temperature_binary32=BINARY32_ONE,
        entropy=_reference_entropy(entropy),
        tensor_parallel_world_size=1,
        require_pytorch_cuda_equivalence=False,
    )
    _assert_service_matches_reference(actual, expected)
    assert actual.output_token_ids == ((0, 1, 0, 1, 0, 1),)
    assert entropy.offset == 1
    assert actual.next_entropy is not entropy
    assert actual.next_entropy is not None and actual.next_entropy.offset == 11
    assert actual.logical_counters["sampling_entropy_draws_consumed"] == 10


def test_default_nonzero_source_replay_and_late_entropy_exhaustion_poison() -> None:
    base, embedding, head = _small_identity_fixture(world_size=2)
    with pytest.raises(
        DeepSeekV4MarkovServiceError,
        match="nonzero-temperature PyTorch/CUDA replay is unresolved",
    ):
        execute_deepseek_v4_markov_program(
            _PROGRAM,
            base,
            (0,),
            embedding,
            head,
            tensor_parallel_world_size=2,
        )

    entropy = MarkovServiceEntropy.from_codes((_f32(1),) * 19)
    with pytest.raises(DeepSeekV4MarkovServiceError, match="entropy exhausted"):
        execute_deepseek_v4_markov_program(
            _PROGRAM,
            base,
            (0,),
            embedding,
            head,
            temperature_binary32=BINARY32_ONE,
            entropy=entropy,
            tensor_parallel_world_size=2,
            require_pytorch_cuda_equivalence=False,
        )
    assert entropy.offset == 0


def test_program_integrity_is_checked_before_any_numeric_execution() -> None:
    base, embedding, head = _small_identity_fixture(world_size=2)
    corrupted = bytearray(_PROGRAM)
    corrupted[-1] ^= 1
    with pytest.raises(DeepSeekV4MarkovServiceError, match="body digest"):
        execute_deepseek_v4_markov_program(
            bytes(corrupted), base, (0,), embedding, head, temperature_binary32=0
        )
    rehashed = _rewrite_record(_PROGRAM, 4, 3, 1)
    with pytest.raises(DeepSeekV4MarkovServiceError, match="instruction 4"):
        execute_deepseek_v4_markov_program(
            rehashed, base, (0,), embedding, head, temperature_binary32=0
        )


def test_randomized_service_matches_reference_for_greedy_and_target_modes() -> None:
    rng = random.Random(0x5345_5256_4D41_524B)
    bf16_palette = (
        0,
        0x8000,
        _bf16(Fraction(1, 4)),
        _bf16(Fraction(-1, 4)),
        _bf16(1),
        _bf16(-1),
        _bf16(2),
        _bf16(-2),
    )
    f32_palette = tuple(_f32(value) for value in (-3, -1, 0, 1, 3))
    for case in range(50):
        batch = rng.randint(1, 3)
        vocabulary = rng.choice((2, 4, 8))
        world_size = rng.choice(
            tuple(size for size in (1, 2, 4) if vocabulary % size == 0)
        )
        rank = rng.randint(1, 8)
        embedding_rows = tuple(
            tuple(rng.choice(bf16_palette) for _ in range(rank))
            for _ in range(vocabulary)
        )
        head_rows = tuple(
            tuple(rng.choice(bf16_palette) for _ in range(rank))
            for _ in range(vocabulary)
        )
        base = tuple(
            tuple(
                tuple(rng.choice(f32_palette) for _ in range(vocabulary))
                for _ in range(5)
            )
            for _ in range(batch)
        )
        tokens = tuple(rng.randrange(vocabulary) for _ in range(batch))
        stochastic = case % 5 == 0
        service_entropy = None
        reference_entropy = None
        temperature = 0
        require_source = True
        if stochastic:
            draws = tuple(
                _f32(rng.choice((1, 2, 3, 4)))
                for _ in range(batch * vocabulary * 5)
            )
            service_entropy = MarkovServiceEntropy(draws)
            reference_entropy = ExplicitExponentialEntropy(draws)
            temperature = BINARY32_ONE
            require_source = False
        embedding = _shards(embedding_rows, world_size)
        head = _shards(head_rows, world_size)
        actual = execute_deepseek_v4_markov_program(
            _PROGRAM,
            base,
            tokens,
            embedding,
            head,
            temperature_binary32=temperature,
            entropy=service_entropy,
            tensor_parallel_world_size=world_size,
            require_pytorch_cuda_equivalence=require_source,
        )
        expected = reference.markov_autoregressive_loop_bf16(
            base,
            tokens,
            embedding,
            head,
            temperature_binary32=temperature,
            entropy=reference_entropy,
            tensor_parallel_world_size=world_size,
            require_pytorch_cuda_equivalence=require_source,
        )
        _assert_service_matches_reference(actual, expected)


def test_selected_official_rows_execute_through_the_microprogram() -> None:
    token_ids = reference.OFFICIAL_SELECTED_TOKEN_IDS
    embedding_rows = tuple(
        _official_row(reference.OFFICIAL_W1_TENSOR_NAME, token) for token in token_ids
    )
    head_rows = tuple(
        _official_row(reference.OFFICIAL_W2_TENSOR_NAME, token) for token in token_ids
    )
    result = execute_deepseek_v4_markov_program(
        _PROGRAM,
        _zero_logits(1, len(token_ids)),
        (0,),
        _shards(embedding_rows, 4),
        _shards(head_rows, 4),
        temperature_binary32=0,
        tensor_parallel_world_size=4,
    )
    assert result.markov_bias_binary32_codes[0][0] == (
        reference.OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_BINARY32
    )
    payload = b"".join(
        struct.pack("<I", code)
        for code in result.markov_bias_binary32_codes[0][0]
    )
    assert hashlib.sha256(payload).hexdigest() == (
        reference.OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_SHA256
    )


def test_result_is_deeply_immutable_and_rejects_forged_relationships() -> None:
    base, embedding, head = _small_identity_fixture(world_size=2)
    result = execute_deepseek_v4_markov_program(
        _PROGRAM,
        base,
        (0,),
        embedding,
        head,
        temperature_binary32=0,
        tensor_parallel_world_size=2,
    )
    with pytest.raises(TypeError):
        result.logical_counters["micro_ops_executed"] = 0
    forged_adjusted = tuple(
        tuple(
            tuple((code ^ 1) if (batch == step == column == 0) else code for column, code in enumerate(row))
            for step, row in enumerate(sequence)
        )
        for batch, sequence in enumerate(result.adjusted_logits_binary32_codes)
    )
    with pytest.raises(DeepSeekV4MarkovServiceError, match="base plus bias"):
        replace(result, adjusted_logits_binary32_codes=forged_adjusted)
    with pytest.raises(DeepSeekV4MarkovServiceError, match="output_token_ids_sha256"):
        replace(result, output_token_ids_sha256="0" * 64)
    forged_tokens = (
        result.output_token_ids[0][:1]
        + (2,)
        + result.output_token_ids[0][2:],
    )
    with pytest.raises(DeepSeekV4MarkovServiceError, match="causal sampling"):
        replace(
            result,
            output_token_ids=forged_tokens,
            output_token_ids_sha256=_token_hash(forged_tokens),
        )


@pytest.mark.parametrize(
    ("base", "tokens", "embedding", "head", "options", "match"),
    [
        (
            object(),
            (0,),
            (((0,),),),
            (((0,),),),
            {"tensor_parallel_world_size": 1},
            "base_logits.*exact list",
        ),
        (
            (),
            (),
            (((0,),),),
            (((0,),),),
            {"tensor_parallel_world_size": 1},
            "batch extent",
        ),
        (
            _zero_logits(1, 1),
            object(),
            (((0,),),),
            (((0,),),),
            {"tensor_parallel_world_size": 1},
            "input_token",
        ),
        (
            _zero_logits(1, 1),
            (1,),
            (((0,),),),
            (((0,),),),
            {"tensor_parallel_world_size": 1},
            "integer",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0x7F80,),),),
            (((0,),),),
            {"tensor_parallel_world_size": 1},
            "finite BF16",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0,),),),
            (((0x7F80,),),),
            {"tensor_parallel_world_size": 1},
            "finite BF16",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0,),),),
            (((0,),),),
            {
                "temperature_binary32": 0x7F800000,
                "tensor_parallel_world_size": 1,
            },
            "finite binary32",
        ),
        (
            _zero_logits(1, 2),
            (0,),
            (((0,),), ((0,),)),
            (((0,),), ((0,),)),
            {"tensor_parallel_world_size": 3},
            "exactly 1, 2, 4, or 8",
        ),
    ],
)
def test_malformed_commands_fail_closed(
    base: object,
    tokens: object,
    embedding: object,
    head: object,
    options: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(DeepSeekV4MarkovServiceError, match=match):
        execute_deepseek_v4_markov_program(
            _PROGRAM, base, tokens, embedding, head, **options
        )


def test_service_has_no_compiler_reference_rng_or_expected_output_dependency() -> None:
    source = Path(service_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    absolute_import_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    absolute_import_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert absolute_import_roots.isdisjoint({"compiler", "runtime", "random", "torch"})
    assert "known_answer" not in source
    assert service_module.EXCLUDED_CLAIMS == (
        "checkpoint_or_artifact_authentication",
        "checkpoint_derived_base_logits",
        "complete_official_vocabulary_execution",
        "exact_nonzero_temperature_pytorch_cuda_replay",
        "confidence_target_verification_or_speculative_acceptance",
        "physical_collective_or_memory_traffic",
        "physical_schedule_cycles_latency_bandwidth_throughput_energy_area_routing_ppa",
        "rtl_or_full_model_execution",
    )
