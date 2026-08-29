from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import struct

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)
import runtime.reference.markov_loop as markov
from runtime.reference.sampling import (
    BINARY32_ONE,
    GREEDY_NUMERIC_PROFILE,
    PYTORCH_STOCHASTIC_EQUIVALENCE,
    TARGET_STOCHASTIC_NUMERIC_PROFILE,
    ExplicitExponentialEntropy,
)


_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731"
    / "snapshots"
    / markov.OFFICIAL_REVISION
)
_SHARD = _SNAPSHOT / markov.CHECKPOINT_SHARD


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _bf16_value(code: int) -> Fraction:
    decoded = decode_bf16(code)
    assert decoded.finite and decoded.value is not None
    return decoded.value


def _f32_value(code: int) -> Fraction:
    decoded = decode_binary32(code)
    assert decoded.finite and decoded.value is not None
    return decoded.value


def _independent_dot(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    accumulator = 0
    for left_code, right_code in zip(left, right, strict=True):
        accumulator = encode_binary32_rne(
            _f32_value(accumulator)
            + _bf16_value(left_code) * _bf16_value(right_code)
        )
    return accumulator


def _independent_add(left: int, right: int) -> int:
    return encode_binary32_rne(_f32_value(left) + _f32_value(right))


def _first_argmax(row: tuple[int, ...]) -> int:
    return max(range(len(row)), key=lambda index: (_f32_value(row[index]), -index))


def _shards(
    rows: tuple[tuple[int, ...], ...], world_size: int
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    assert len(rows) % world_size == 0
    width = len(rows) // world_size
    return tuple(
        tuple(rows[rank * width : (rank + 1) * width])
        for rank in range(world_size)
    )


def _zero_logits(batch: int, vocabulary: int) -> tuple[tuple[tuple[int, ...], ...], ...]:
    return tuple(
        tuple((0,) * vocabulary for _ in range(markov.OFFICIAL_BLOCK_SIZE))
        for _ in range(batch)
    )


def _small_identity_fixture(
    *, batch: int = 1, world_size: int = 2
) -> tuple[
    tuple[tuple[tuple[int, ...], ...], ...],
    tuple[tuple[tuple[int, ...], ...], ...],
    tuple[tuple[tuple[int, ...], ...], ...],
]:
    embedding = tuple(
        tuple(_bf16(1 if column == row else 0) for column in range(4))
        for row in range(4)
    )
    # Output row j reads input embedding coordinate j-1, producing a causal
    # 0 -> 1 -> 2 -> 3 -> 0 cycle under greedy sampling.
    head = tuple(
        tuple(_bf16(4 if column == (row - 1) % 4 else 0) for column in range(4))
        for row in range(4)
    )
    return _zero_logits(batch, 4), _shards(embedding, world_size), _shards(
        head, world_size
    )


def _safetensor_header(path: Path) -> tuple[int, dict[str, object]]:
    with path.open("rb") as stream:
        header_length = struct.unpack("<Q", stream.read(8))[0]
        header = json.loads(stream.read(header_length))
    return 8 + header_length, header


def _tensor_payload(path: Path, name: str) -> bytes:
    data_start, header = _safetensor_header(path)
    entry = header[name]
    assert isinstance(entry, dict)
    start, stop = entry["data_offsets"]
    with path.open("rb") as stream:
        stream.seek(data_start + start)
        payload = stream.read(stop - start)
    assert len(payload) == stop - start
    return payload


def _official_row(name: str, token_id: int) -> tuple[int, ...]:
    if not _SHARD.is_file():
        pytest.skip("local pinned DeepSeek checkpoint shard is unavailable")
    data_start, header = _safetensor_header(_SHARD)
    entry = header[name]
    assert isinstance(entry, dict)
    start, _ = entry["data_offsets"]
    row_bytes = markov.OFFICIAL_MARKOV_RANK * 2
    with _SHARD.open("rb") as stream:
        stream.seek(data_start + start + token_id * row_bytes)
        payload = stream.read(row_bytes)
    assert len(payload) == row_bytes
    return struct.unpack(f"<{markov.OFFICIAL_MARKOV_RANK}H", payload)


def test_reference_is_bound_to_pinned_source_config_and_checkpoint() -> None:
    assert markov.OFFICIAL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert markov.OFFICIAL_REVISION == (
        "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    )
    assert markov.MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert markov.INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert markov.CHECKPOINT_INDEX_SHA256 == (
        "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
    )
    assert markov.CHECKPOINT_LOCK_ID == (
        "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
    )
    assert markov.MARKOV_LOOP_NUMERIC_PROFILE == (
        "opentallas.deepseek_v4_markov_loop_binary32.v1"
    )

    model_path = _SNAPSHOT / markov.MODEL_SOURCE_PATH
    config_path = _SNAPSHOT / markov.INFERENCE_CONFIG_PATH
    if not model_path.is_file() or not config_path.is_file():
        pytest.skip("local pinned DeepSeek source snapshot is unavailable")
    model_payload = model_path.read_bytes()
    config_payload = config_path.read_bytes()
    assert hashlib.sha256(model_payload).hexdigest() == markov.MODEL_SOURCE_SHA256
    assert hashlib.sha256(config_payload).hexdigest() == markov.INFERENCE_CONFIG_SHA256
    source = model_payload.decode("utf-8")
    assert all(expression in source for expression in markov.SOURCE_EXPRESSIONS)
    config = json.loads(config_payload)
    assert config["vocab_size"] == markov.OFFICIAL_VOCABULARY_SIZE
    assert config["dspark_markov_rank"] == markov.OFFICIAL_MARKOV_RANK
    assert config["dspark_block_size"] == markov.OFFICIAL_BLOCK_SIZE

    tree = ast.parse(source)
    classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    model_args = classes["ModelArgs"]
    temperature_fields = [
        node
        for node in model_args.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "temperature"
    ]
    assert len(temperature_fields) == 1
    assert isinstance(temperature_fields[0].value, ast.Constant)
    assert temperature_fields[0].value.value == 1
    markov_forward = next(
        node
        for node in classes["DSparkMarkovHead"].body
        if isinstance(node, ast.FunctionDef) and node.name == "forward"
    )
    assert ast.unparse(markov_forward.body[-1]) == "return (logits, embed)"
    block_forward = next(
        node
        for node in classes["DSparkBlock"].body
        if isinstance(node, ast.FunctionDef) and node.name == "forward_head"
    )
    loops = [node for node in ast.walk(block_forward) if isinstance(node, ast.For)]
    assert len(loops) == 1
    assert ast.unparse(loops[0].iter) == "range(self.block_size)"
    loop_expressions = tuple(ast.unparse(statement) for statement in loops[0].body)
    assert loop_expressions == (
        "(logits_bias, markov_embed) = self.markov_head(output_ids[:, i])",
        "logits[:, i].add_(logits_bias)",
        "markov_embeds.append(markov_embed)",
        "output_ids[:, i + 1] = sample(logits[:, i], self.temperature)",
    )


def test_official_topology_and_payload_identities_are_frozen() -> None:
    assert markov.OFFICIAL_VOCABULARY_SIZE == 129_280
    assert markov.OFFICIAL_MARKOV_RANK == 256
    assert markov.OFFICIAL_BLOCK_SIZE == 5
    assert markov.OFFICIAL_OUTPUT_TOKEN_COUNT == 6
    assert markov.OFFICIAL_WEIGHT_SHAPE == (129_280, 256)
    assert markov.OFFICIAL_WEIGHT_BYTES == 66_191_360
    assert markov.OFFICIAL_MP4_PARTITION_ROWS == 32_320
    assert markov.OFFICIAL_DEFAULT_TEMPERATURE_BINARY32 == BINARY32_ONE
    assert markov.OFFICIAL_W1_SHA256 == (
        "966bd0507046347754d0f4bf3addd6df6c179ff16243d63998258b3987e4b2f5"
    )
    assert markov.OFFICIAL_W2_SHA256 == (
        "40ac7e99651c5c6aab8d2555ff65d247931f318414cf94baedc6da2d3bf7c175"
    )
    assert len(markov.OFFICIAL_W1_MP4_SHA256) == 4
    assert len(markov.OFFICIAL_W2_MP4_SHA256) == 4


def test_local_official_markov_tensors_and_mp4_partitions_match() -> None:
    if not _SHARD.is_file():
        pytest.skip("local pinned DeepSeek checkpoint shard is unavailable")
    data_start, header = _safetensor_header(_SHARD)
    del data_start
    for name, whole_hash, partition_hashes in (
        (
            markov.OFFICIAL_W1_TENSOR_NAME,
            markov.OFFICIAL_W1_SHA256,
            markov.OFFICIAL_W1_MP4_SHA256,
        ),
        (
            markov.OFFICIAL_W2_TENSOR_NAME,
            markov.OFFICIAL_W2_SHA256,
            markov.OFFICIAL_W2_MP4_SHA256,
        ),
    ):
        entry = header[name]
        assert isinstance(entry, dict)
        assert entry["dtype"] == "BF16"
        assert entry["shape"] == list(markov.OFFICIAL_WEIGHT_SHAPE)
        payload = _tensor_payload(_SHARD, name)
        assert len(payload) == markov.OFFICIAL_WEIGHT_BYTES
        assert hashlib.sha256(payload).hexdigest() == whole_hash
        partition_bytes = len(payload) // 4
        assert tuple(
            hashlib.sha256(
                payload[rank * partition_bytes : (rank + 1) * partition_bytes]
            ).hexdigest()
            for rank in range(4)
        ) == partition_hashes
        assert all(high not in {0x7F, 0xFF} for high in payload[1::2])


def test_official_selected_rows_and_full_rank_known_answer_match() -> None:
    if not _SHARD.is_file():
        pytest.skip("local pinned DeepSeek checkpoint shard is unavailable")
    w1_rows = tuple(
        _official_row(markov.OFFICIAL_W1_TENSOR_NAME, token)
        for token in markov.OFFICIAL_SELECTED_TOKEN_IDS
    )
    w2_rows = tuple(
        _official_row(markov.OFFICIAL_W2_TENSOR_NAME, token)
        for token in markov.OFFICIAL_SELECTED_TOKEN_IDS
    )
    assert tuple(
        hashlib.sha256(struct.pack("<256H", *row)).hexdigest() for row in w1_rows
    ) == markov.OFFICIAL_W1_SELECTED_ROW_SHA256
    assert tuple(
        hashlib.sha256(struct.pack("<256H", *row)).hexdigest() for row in w2_rows
    ) == markov.OFFICIAL_W2_SELECTED_ROW_SHA256

    logits = tuple(_independent_dot(w1_rows[0], row) for row in w2_rows)
    assert logits == markov.OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_BINARY32
    payload = b"".join(code.to_bytes(4, "little") for code in logits)
    assert hashlib.sha256(payload).hexdigest() == (
        markov.OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_SHA256
    )


def test_five_greedy_steps_are_causal_and_return_all_source_outputs() -> None:
    base, embedding, head = _small_identity_fixture(batch=2, world_size=2)
    result = markov.markov_autoregressive_loop_bf16(
        base,
        (0, 2),
        embedding,
        head,
        temperature_binary32=0,
        tensor_parallel_world_size=2,
    )
    assert result.output_token_ids == (
        (0, 1, 2, 3, 0, 1),
        (2, 3, 0, 1, 2, 3),
    )
    flat_embedding = tuple(row for shard in embedding for row in shard)
    flat_head = tuple(row for shard in head for row in shard)
    for batch in range(2):
        for step in range(markov.OFFICIAL_BLOCK_SIZE):
            causal_token = result.output_token_ids[batch][step]
            assert result.markov_embeddings_bf16_codes[batch][step] == (
                flat_embedding[causal_token]
            )
            expected_bias = tuple(
                _independent_dot(flat_embedding[causal_token], row)
                for row in flat_head
            )
            expected_adjusted = tuple(
                _independent_add(base_code, bias_code)
                for base_code, bias_code in zip(
                    base[batch][step], expected_bias, strict=True
                )
            )
            assert result.markov_bias_binary32_codes[batch][step] == expected_bias
            assert result.adjusted_logits_binary32_codes[batch][step] == (
                expected_adjusted
            )
            assert result.output_token_ids[batch][step + 1] == _first_argmax(
                expected_adjusted
            )
    assert result.base_logits_binary32_codes == base
    assert result.sampling_mode == "greedy_argmax"
    assert result.sampling_numeric_profile == GREEDY_NUMERIC_PROFILE
    assert result.source_equivalence == (
        "bit_exact_for_validated_finite_binary32_inputs"
    )
    assert result.next_entropy is None
    assert result.entropy_offset_before is result.entropy_offset_after is None
    assert len(result.sampling_results) == 5


def test_greedy_ties_select_first_index_and_do_not_consume_entropy() -> None:
    vocabulary = 2
    rank = 1
    weights = _shards(((0,), (0,)), 1)
    entropy = ExplicitExponentialEntropy.from_codes((_f32(1), _f32(2)))
    result = markov.markov_autoregressive_loop_bf16(
        _zero_logits(1, vocabulary),
        (1,),
        weights,
        weights,
        temperature_binary32=0x80000000,
        entropy=entropy,
        tensor_parallel_world_size=1,
    )
    assert result.markov_rank == rank
    assert result.output_token_ids == ((1, 0, 0, 0, 0, 0),)
    assert result.next_entropy is entropy
    assert result.entropy_offset_before == result.entropy_offset_after == 0
    assert result.counters.sampling_entropy_draws_consumed == 0
    assert all(sample.next_entropy is entropy for sample in result.sampling_results)


def test_projection_order_and_separate_binary32_bias_addition_are_frozen() -> None:
    small = _bf16(Fraction(1, 1 << 12))
    projection_weights = (((( _bf16(1), small, _bf16(-1)),),))
    head_weights = (((( _bf16(1), small, _bf16(1)),),))
    projection = markov.markov_autoregressive_loop_bf16(
        _zero_logits(1, 1),
        (0,),
        projection_weights,
        head_weights,
        temperature_binary32=0,
        tensor_parallel_world_size=1,
    )
    # The exact dot is 2^-24, but increasing-rank RNE rounds that term away
    # between +1 and -1.  A one-round exact dot would therefore differ.
    assert projection.markov_bias_binary32_codes == (((0,),) * 5,)
    assert _f32(Fraction(1, 1 << 24)) == 0x33800000

    addend_weights = (((_bf16(1),),),)
    half_ulp_weights = (((_bf16(Fraction(1, 1 << 24)),),),)
    base = tuple(tuple((0x3F800001,) for _ in range(5)) for _ in range(1))
    addition = markov.markov_autoregressive_loop_bf16(
        base,
        (0,),
        addend_weights,
        half_ulp_weights,
        temperature_binary32=0,
        tensor_parallel_world_size=1,
    )
    assert addition.markov_bias_binary32_codes == (((0x33800000,),) * 5,)
    # 1+2^-23 has an odd significand.  Adding half an ULP ties and rounds to
    # the next even significand at the separate logit-add boundary.
    assert addition.adjusted_logits_binary32_codes == (((0x3F800002,),) * 5,)


def test_official_default_temperature_fails_closed_without_backend_contract() -> None:
    base, embedding, head = _small_identity_fixture(world_size=2)
    with pytest.raises(
        markov.MarkovLoopReferenceError,
        match="causal step 0.*exact nonzero-temperature PyTorch/CUDA replay is unresolved",
    ):
        markov.markov_autoregressive_loop_bf16(
            base,
            (0,),
            embedding,
            head,
            tensor_parallel_world_size=2,
        )


def test_explicit_stochastic_target_adaptation_threads_entropy_across_five_steps() -> None:
    weights = _shards(((0,), (0,)), 1)
    # Equal logits make each race depend only on the supplied positive draws.
    draw_pairs = (
        (_f32(2), _f32(1)),
        (_f32(1), _f32(2)),
        (_f32(3), _f32(1)),
        (_f32(1), _f32(4)),
        (_f32(5), _f32(1)),
    )
    entropy = ExplicitExponentialEntropy(
        binary32_codes=(_f32(9),)
        + tuple(code for pair in draw_pairs for code in pair),
        offset=1,
    )
    result = markov.markov_autoregressive_loop_bf16(
        _zero_logits(1, 2),
        (0,),
        weights,
        weights,
        temperature_binary32=BINARY32_ONE,
        entropy=entropy,
        tensor_parallel_world_size=1,
        require_pytorch_cuda_equivalence=False,
    )
    # Smaller exponential draw wins when probabilities tie.
    assert result.output_token_ids == ((0, 1, 0, 1, 0, 1),)
    assert result.sampling_mode == "explicit_exponential_race_target_adaptation"
    assert result.sampling_numeric_profile == TARGET_STOCHASTIC_NUMERIC_PROFILE
    assert result.source_equivalence == PYTORCH_STOCHASTIC_EQUIVALENCE
    assert entropy.offset == 1
    assert result.entropy_offset_before == 1
    assert result.entropy_offset_after == 11
    assert result.next_entropy is not entropy
    assert result.next_entropy is not None and result.next_entropy.offset == 11
    assert tuple(
        (sample.entropy_offset_before, sample.entropy_offset_after)
        for sample in result.sampling_results
    ) == ((1, 3), (3, 5), (5, 7), (7, 9), (9, 11))
    assert result.counters.sampling_entropy_draws_consumed == 10


def test_entropy_exhaustion_and_numeric_overflow_poison_without_mutation() -> None:
    base, embedding, head = _small_identity_fixture(world_size=2)
    entropy = ExplicitExponentialEntropy.from_codes((_f32(1),) * 19)
    with pytest.raises(
        markov.MarkovLoopReferenceError,
        match="causal step 4.*entropy exhausted",
    ):
        markov.markov_autoregressive_loop_bf16(
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

    overflow_weights = (((0x7F7F,),),)
    with pytest.raises(
        markov.MarkovLoopReferenceError,
        match="Markov arithmetic failed at step 0, batch 0.*overflow",
    ):
        markov.markov_autoregressive_loop_bf16(
            _zero_logits(1, 1),
            (0,),
            overflow_weights,
            overflow_weights,
            temperature_binary32=0,
            tensor_parallel_world_size=1,
        )


def test_randomized_greedy_reference_matches_independent_causal_oracle() -> None:
    rng = random.Random(0x4D41_524B_4F56)
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
    for _ in range(80):
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
                for _ in range(markov.OFFICIAL_BLOCK_SIZE)
            )
            for _ in range(batch)
        )
        inputs = tuple(rng.randrange(vocabulary) for _ in range(batch))
        result = markov.markov_autoregressive_loop_bf16(
            base,
            inputs,
            _shards(embedding_rows, world_size),
            _shards(head_rows, world_size),
            temperature_binary32=0,
            tensor_parallel_world_size=world_size,
        )
        expected_tokens = [[token] for token in inputs]
        expected_embeddings = [[] for _ in range(batch)]
        expected_biases = [[] for _ in range(batch)]
        expected_adjusted = [[] for _ in range(batch)]
        for step in range(markov.OFFICIAL_BLOCK_SIZE):
            for batch_index in range(batch):
                embedding_row = embedding_rows[expected_tokens[batch_index][step]]
                bias_row = tuple(
                    _independent_dot(embedding_row, weight_row)
                    for weight_row in head_rows
                )
                adjusted_row = tuple(
                    _independent_add(base_code, bias_code)
                    for base_code, bias_code in zip(
                        base[batch_index][step], bias_row, strict=True
                    )
                )
                expected_embeddings[batch_index].append(embedding_row)
                expected_biases[batch_index].append(bias_row)
                expected_adjusted[batch_index].append(adjusted_row)
                expected_tokens[batch_index].append(_first_argmax(adjusted_row))
        assert result.output_token_ids == tuple(
            tuple(row) for row in expected_tokens
        )
        assert result.markov_embeddings_bf16_codes == tuple(
            tuple(rows) for rows in expected_embeddings
        )
        assert result.markov_bias_binary32_codes == tuple(
            tuple(rows) for rows in expected_biases
        )
        assert result.adjusted_logits_binary32_codes == tuple(
            tuple(rows) for rows in expected_adjusted
        )


@pytest.mark.parametrize(
    ("base", "tokens", "embedding", "head", "options", "match"),
    [
        (object(), (0,), (((0,),),), (((0,),),), {}, "base_logits.*exact list"),
        ((), (), (((0,),),), (((0,),),), {}, "batch extent"),
        ((((),) * 5,), (0,), (((0,),),), (((0,),),), {}, "vocabulary width"),
        (
            _zero_logits(1, 1),
            object(),
            (((0,),),),
            (((0,),),),
            {},
            "input_token_ids must be an exact",
        ),
        (
            _zero_logits(1, 1),
            (1,),
            (((0,),),),
            (((0,),),),
            {},
            r"input_token_ids\[0\]",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            object(),
            (((0,),),),
            {},
            "embedding_weight.*exact list",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0x7F80,),),),
            (((0,),),),
            {},
            "finite BF16",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0,),),),
            (((0, 0),),),
            {},
            "rows must have equal width",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0,),),),
            (((0,),),),
            {"temperature_binary32": 0x7F800000},
            "finite binary32",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0,),),),
            (((0,),),),
            {"require_pytorch_cuda_equivalence": 1},
            "exact bool",
        ),
        (
            _zero_logits(1, 1),
            (0,),
            (((0,),),),
            (((0,),),),
            {"tensor_parallel_world_size": 3},
            "exactly 1, 2, 4, or 8",
        ),
    ],
)
def test_reference_rejects_malformed_shapes_types_and_nonfinite_values(
    base: object,
    tokens: object,
    embedding: object,
    head: object,
    options: dict[str, object],
    match: str,
) -> None:
    arguments: dict[str, object] = {
        "temperature_binary32": 0,
        "tensor_parallel_world_size": 1,
    }
    arguments.update(options)
    with pytest.raises(markov.MarkovLoopReferenceError, match=match):
        markov.markov_autoregressive_loop_bf16(
            base,
            tokens,
            embedding,
            head,
            **arguments,  # type: ignore[arg-type]
        )


def test_inputs_are_copied_and_result_is_immutable_hashed_and_reconciled() -> None:
    base = [
        [[0, 0] for _ in range(markov.OFFICIAL_BLOCK_SIZE)]
    ]
    embedding = [[[_bf16(1)], [_bf16(-1)]]]
    head = [[[_bf16(1)], [_bf16(-1)]]]
    result = markov.markov_autoregressive_loop_bf16(
        base,
        [0],
        embedding,
        head,
        temperature_binary32=0,
        tensor_parallel_world_size=1,
    )
    expected = result.adjusted_logits_binary32_codes
    base[0][0][0] = _f32(100)
    embedding[0][0][0] = 0
    head[0][0][0] = 0
    assert result.adjusted_logits_binary32_codes == expected
    with pytest.raises(FrozenInstanceError):
        result.temperature_binary32 = BINARY32_ONE  # type: ignore[misc]
    with pytest.raises(markov.MarkovLoopReferenceError, match="adjusted-logit hash"):
        replace(result, adjusted_logits_binary32_sha256="0" * 64)
    with pytest.raises(markov.MarkovLoopReferenceError, match="base plus bias"):
        tampered = list(result.adjusted_logits_binary32_codes[0])
        tampered[0] = (0,) * result.vocabulary_size
        replace(result, adjusted_logits_binary32_codes=(tuple(tampered),))
    with pytest.raises(markov.MarkovLoopReferenceError, match="output-token hash"):
        replace(result, output_token_ids_sha256="0" * 64)
    with pytest.raises(markov.MarkovLoopReferenceError, match="does not reconcile"):
        replace(result.counters, binary32_bias_additions=0)


def test_functional_counters_reconcile_exactly_without_physical_claims() -> None:
    base, embedding, head = _small_identity_fixture(batch=2, world_size=2)
    result = markov.markov_autoregressive_loop_bf16(
        base,
        (0, 1),
        embedding,
        head,
        temperature_binary32=0,
        tensor_parallel_world_size=2,
    )
    assert result.counters == markov.MarkovLoopCounters(
        batch_count=2,
        block_size=5,
        vocabulary_size=4,
        markov_rank=4,
        tensor_parallel_world_size=2,
        partition_vocabulary_rows=2,
        loop_iterations=5,
        initial_token_values_read=2,
        initial_token_values_written=2,
        causal_token_values_read=10,
        base_logit_binary32_values_validated=40,
        base_logit_binary32_values_read=40,
        embedding_weight_bf16_values_validated=16,
        head_weight_bf16_values_validated=16,
        embedding_row_lookups=10,
        embedding_bf16_values_read=40,
        embedding_bf16_values_written=40,
        embedding_binary32_widens=40,
        head_weight_binary32_widens=16,
        exact_product_accumulates=160,
        binary32_accumulation_roundings=160,
        markov_bias_binary32_values_written=40,
        binary32_bias_additions=40,
        adjusted_logit_binary32_values_written=40,
        sampling_calls=5,
        sampling_logit_binary32_values_read=40,
        sampling_argmax_comparisons=30,
        sampling_entropy_draws_consumed=0,
        sampled_token_values_written=10,
        output_token_values_written=12,
        transaction_commits=1,
    )
    names = {field.name for field in fields(markov.MarkovLoopCounters)}
    prohibited = (
        "hbm",
        "sram",
        "burst",
        "cycle",
        "latency",
        "bandwidth",
        "throughput",
        "energy",
        "area",
        "routing",
        "ppa",
    )
    assert not any(token in name for name in names for token in prohibited)
    assert "physical_rom_sram_hbm_cycles_latency_bandwidth_throughput_energy_area_routing_ppa" in (
        markov.EXCLUDED_CLAIMS
    )


def test_reference_has_no_framework_host_float_or_execution_layer_dependency() -> None:
    source = Path(markov.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert imported_roots.isdisjoint(
        {"decimal", "math", "mpmath", "numpy", "torch", "compiler"}
    )
    assert "service_engine" not in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )
