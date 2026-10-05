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

import runtime.reference.lm_head as head
from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)
from runtime.service_engine.lm_head_numeric import (
    LMHeadServiceNumericError,
    execute_selected_vocabulary_rows,
)


_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731"
    / "snapshots"
    / head.OFFICIAL_REVISION
)
_SHARD = _SNAPSHOT / "model-00045-of-00048.safetensors"


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _value(code: int) -> Fraction:
    decoded = decode_bf16(code)
    assert decoded.finite and decoded.value is not None
    return decoded.value


def _independent_dot(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    accumulator = Fraction(0)
    accumulator_code = 0
    for lhs, rhs in zip(left, right, strict=True):
        decoded_accumulator = decode_binary32(accumulator_code)
        assert decoded_accumulator.finite and decoded_accumulator.value is not None
        accumulator = decoded_accumulator.value + _value(lhs) * _value(rhs)
        accumulator_code = encode_binary32_rne(accumulator)
    return accumulator_code


def _safetensor_entry(path: Path, name: str) -> tuple[int, dict[str, object]]:
    with path.open("rb") as stream:
        header_length = struct.unpack("<Q", stream.read(8))[0]
        header = json.loads(stream.read(header_length))
    return 8 + header_length, header[name]


def _official_rows(token_ids: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    if not _SHARD.is_file():
        pytest.skip("local pinned DeepSeek checkpoint shard is unavailable")
    data_start, entry = _safetensor_entry(_SHARD, "head.weight")
    assert entry["dtype"] == "BF16"
    assert entry["shape"] == list(head.OFFICIAL_WEIGHT_SHAPE)
    start, stop = entry["data_offsets"]
    assert stop - start == head.OFFICIAL_WEIGHT_BYTES
    row_bytes = head.OFFICIAL_HIDDEN_WIDTH * 2
    rows = []
    with _SHARD.open("rb") as stream:
        for token_id in token_ids:
            stream.seek(data_start + start + token_id * row_bytes)
            payload = stream.read(row_bytes)
            assert len(payload) == row_bytes
            rows.append(struct.unpack(f"<{head.OFFICIAL_HIDDEN_WIDTH}H", payload))
    return tuple(rows)


def test_lm_head_is_bound_to_pinned_source_config_and_checkpoint() -> None:
    assert head.OFFICIAL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert head.OFFICIAL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert head.MODEL_SOURCE_PATH == "inference/model.py"
    assert head.MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert head.CONVERT_SOURCE_PATH == "inference/convert.py"
    assert head.CONVERT_SOURCE_SHA256 == (
        "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
    )
    assert head.GENERATE_SOURCE_PATH == "inference/generate.py"
    assert head.GENERATE_SOURCE_SHA256 == (
        "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
    )
    assert head.INFERENCE_CONFIG_PATH == "inference/config.json"
    assert head.INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert head.CHECKPOINT_INDEX_PATH == "model.safetensors.index.json"
    assert head.CHECKPOINT_INDEX_SHA256 == (
        "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
    )
    assert head.CHECKPOINT_LOCK_ID == (
        "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
    )
    assert head.LM_HEAD_NUMERIC_PROFILE == (
        "opentallas.deepseek_v4_lm_head_binary32.v1"
    )

    pinned_files = (
        (head.MODEL_SOURCE_PATH, head.MODEL_SOURCE_SHA256),
        (head.CONVERT_SOURCE_PATH, head.CONVERT_SOURCE_SHA256),
        (head.GENERATE_SOURCE_PATH, head.GENERATE_SOURCE_SHA256),
        (head.INFERENCE_CONFIG_PATH, head.INFERENCE_CONFIG_SHA256),
        (head.CHECKPOINT_INDEX_PATH, head.CHECKPOINT_INDEX_SHA256),
    )
    paths = tuple(
        (_SNAPSHOT / relative, digest) for relative, digest in pinned_files
    )
    if any(not path.is_file() for path, _ in paths):
        pytest.skip("local pinned DeepSeek source snapshot is unavailable")
    for path, expected_digest in paths:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest
    source_path = _SNAPSHOT / head.MODEL_SOURCE_PATH
    config_path = _SNAPSHOT / head.INFERENCE_CONFIG_PATH
    source_payload = source_path.read_bytes()
    config_payload = config_path.read_bytes()
    source = source_payload.decode("utf-8")
    convert_source = (_SNAPSHOT / head.CONVERT_SOURCE_PATH).read_text(
        encoding="utf-8"
    )
    config = json.loads(config_payload)
    assert all(expression in source for expression in head.SOURCE_EXPRESSIONS)
    assert all(
        expression in convert_source
        for expression in head.CONVERT_SOURCE_EXPRESSIONS
    )
    assert all(config[name] == expected for name, expected in head.CONFIG_EXPECTED_FIELDS)


def test_official_shape_topology_and_payload_identities_are_frozen() -> None:
    assert head.OFFICIAL_HIDDEN_WIDTH == 4096
    assert head.OFFICIAL_VOCABULARY_SIZE == 129_280
    assert head.OFFICIAL_WEIGHT_SHAPE == (129_280, 4096)
    assert head.OFFICIAL_WEIGHT_BYTES == 1_059_061_760
    assert head.OFFICIAL_MAIN_SITE_COUNT == 1
    assert head.OFFICIAL_DSPARK_SITE_COUNT == 1
    assert head.OFFICIAL_SITE_COUNT == 2
    assert head.OFFICIAL_DSPARK_BLOCK_SIZE == 5
    assert head.OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES == (1, 2, 4, 8)
    assert head.OFFICIAL_MP4_PARTITION_ROWS == 32_320
    assert head.OFFICIAL_WEIGHT_SHA256 == (
        "029e3c5293b29cc426e21d87795e15efa4d363f27b2bc4a9e3aef7d79f047919"
    )
    assert head.OFFICIAL_MP4_WEIGHT_SHA256 == (
        "517371776bf297a7c1fba6317c04649c8080841cf0107d3395b23559b8540ee1",
        "a0e8f1115ad0ce49a7ec27af80017abe5beff4ac0fde26cfaf1ff6fbb7d217ba",
        "ea93b80dcc8940969e20c481de389f85709ea9b015a02a28540719e77c7cd494",
        "abbeab307dd4d6cf87f0d38106032743af343954a9671deec6960a0384e089c4",
    )


def test_local_official_tensor_and_mp4_partition_hashes_match() -> None:
    if not _SHARD.is_file():
        pytest.skip("local pinned DeepSeek checkpoint shard is unavailable")
    data_start, entry = _safetensor_entry(_SHARD, "head.weight")
    assert entry["dtype"] == "BF16"
    assert entry["shape"] == [129_280, 4096]
    start, stop = entry["data_offsets"]
    assert stop - start == head.OFFICIAL_WEIGHT_BYTES
    partition_bytes = head.OFFICIAL_WEIGHT_BYTES // 4
    complete = hashlib.sha256()
    partitions = [hashlib.sha256() for _ in range(4)]
    finite = True
    consumed = 0
    remaining = head.OFFICIAL_WEIGHT_BYTES
    with _SHARD.open("rb") as stream:
        stream.seek(data_start + start)
        while remaining:
            payload = stream.read(min(8 << 20, remaining))
            assert payload
            complete.update(payload)
            offset = 0
            while offset < len(payload):
                rank = min(3, consumed // partition_bytes)
                take = min(
                    len(payload) - offset,
                    (rank + 1) * partition_bytes - consumed,
                )
                partitions[rank].update(payload[offset : offset + take])
                offset += take
                consumed += take
            high_bytes = payload[1::2]
            finite &= b"\x7f" not in high_bytes and b"\xff" not in high_bytes
            remaining -= len(payload)
    assert finite
    assert complete.hexdigest() == head.OFFICIAL_WEIGHT_SHA256
    assert tuple(digest.hexdigest() for digest in partitions) == (
        head.OFFICIAL_MP4_WEIGHT_SHA256
    )


def test_main_profile_selects_only_last_position_and_gathers_rank_order() -> None:
    hidden = (
        (
            (_bf16(100), _bf16(100), _bf16(100)),
            (_bf16(1), _bf16(2), _bf16(3)),
        ),
        (
            (_bf16(-100), _bf16(-100), _bf16(-100)),
            (_bf16(-1), _bf16(-2), _bf16(-3)),
        ),
    )
    rows = tuple(
        (_bf16(token + 1), _bf16(1), _bf16(-1)) for token in range(8)
    )
    shards = tuple(tuple(rows[rank * 2 : (rank + 1) * 2]) for rank in range(4))
    result = head.lm_head_bf16(
        hidden,
        shards,
        tensor_parallel_world_size=4,
        full_logits=False,
    )

    expected_first = tuple(_independent_dot(hidden[0][-1], row) for row in rows)
    expected_second = tuple(_independent_dot(hidden[1][-1], row) for row in rows)
    assert result.logits_binary32_codes == (expected_first, expected_second)
    assert result.selected_token_ids == tuple(range(8))
    assert result.selected_partition_ranks == (0, 0, 1, 1, 2, 2, 3, 3)
    assert result.selected_local_row_indices == (0, 1, 0, 1, 0, 1, 0, 1)
    assert result.complete_output is True
    assert result.counters.source_hidden_rows_validated == 4
    assert result.counters.selected_hidden_rows_read == 2
    assert result.counters.source_rows_excluded_by_last_token_selection == 2
    assert result.counters.logical_gathered_binary32_values == 16


def test_dspark_full_logits_projects_all_five_positions_with_shared_head() -> None:
    hidden_rows = tuple(
        (_bf16(position + 1), _bf16(2 * position + 1))
        for position in range(head.OFFICIAL_DSPARK_BLOCK_SIZE)
    )
    weights = (
        (_bf16(1), _bf16(0)),
        (_bf16(0), _bf16(1)),
        (_bf16(1), _bf16(-1)),
        (_bf16(2), _bf16(3)),
    )
    result = head.lm_head_bf16(
        (hidden_rows,),
        (weights,),
        tensor_parallel_world_size=1,
        full_logits=True,
    )
    expected = tuple(
        tuple(_independent_dot(hidden_row, weight) for weight in weights)
        for hidden_row in hidden_rows
    )
    assert result.logits_binary32_codes == (expected,)
    assert result.counters.evaluated_positions_per_batch == 5
    assert result.counters.selected_hidden_rows_read == 5
    assert result.counters.source_rows_excluded_by_last_token_selection == 0
    assert result.counters.binary32_logits_written == 20


def test_increasing_hidden_index_rounding_is_frozen_without_output_conversion() -> None:
    small = _bf16(Fraction(1, 1 << 12))
    hidden = (((_bf16(1), small, _bf16(-1)),),)
    weights = ((_bf16(1), small, _bf16(1)),)
    result = head.lm_head_selected_bf16(
        hidden,
        weights,
        declared_vocabulary_size=1,
        selected_token_ids=(0,),
        tensor_parallel_world_size=1,
    )
    assert result.logits_binary32_codes == ((0,),)
    assert encode_binary32_rne(Fraction(1, 1 << 24)) == 0x33800000
    assert result.counters.exact_product_accumulates == 3
    assert result.counters.binary32_accumulation_roundings == 3


def test_selected_official_profile_maps_every_mp4_boundary() -> None:
    selected = tuple(token_id for token_id, _ in head.OFFICIAL_SELECTED_ROW_SHA256)
    zero_row = (0,) * head.OFFICIAL_HIDDEN_WIDTH
    result = head.lm_head_selected_bf16(
        (((zero_row),),),
        (zero_row,) * len(selected),
        declared_vocabulary_size=head.OFFICIAL_VOCABULARY_SIZE,
        selected_token_ids=selected,
        tensor_parallel_world_size=4,
    )
    assert result.official_shape_profile is True
    assert result.complete_output is False
    assert result.selected_partition_ranks == (0, 0, 1, 1, 2, 2, 3, 3)
    assert result.selected_local_row_indices == (
        0,
        32_319,
        0,
        32_319,
        0,
        32_319,
        0,
        32_319,
    )
    assert result.logits_binary32_codes == ((0,) * len(selected),)
    assert result.counters.partition_vocabulary_rows == 32_320
    assert result.counters.evaluated_tensor_parallel_shards == 4
    assert result.counters.declared_tensor_parallel_shards == 4


def test_real_official_rows_match_hashes_and_full_width_known_answer() -> None:
    selected_hashes = head.OFFICIAL_SELECTED_ROW_SHA256
    selected = tuple(token_id for token_id, _ in selected_hashes)
    rows = _official_rows(selected)
    for row, (_, expected_hash) in zip(rows, selected_hashes, strict=True):
        payload = struct.pack(f"<{head.OFFICIAL_HIDDEN_WIDTH}H", *row)
        assert hashlib.sha256(payload).hexdigest() == expected_hash

    palette = (
        0x0000,
        0x3F80,
        0xBF80,
        0x3F00,
        0xBF00,
        0x4000,
        0xC000,
        0x3E80,
        0xBE80,
        0x4040,
        0xC040,
    )
    hidden_row = tuple(
        palette[(index * 7 + index // 11) % len(palette)]
        for index in range(head.OFFICIAL_HIDDEN_WIDTH)
    )
    result = head.lm_head_selected_bf16(
        (((hidden_row),),),
        rows,
        declared_vocabulary_size=head.OFFICIAL_VOCABULARY_SIZE,
        selected_token_ids=selected,
        tensor_parallel_world_size=4,
    )
    service = execute_selected_vocabulary_rows(
        (hidden_row,),
        rows,
        vocabulary_row_indices=selected,
        declared_vocabulary_size=head.OFFICIAL_VOCABULARY_SIZE,
        tensor_parallel_world_size=4,
    )
    assert service.logits_binary32_codes == result.logits_binary32_codes
    assert service.owner_ranks == result.selected_partition_ranks
    assert result.logits_binary32_codes == (
        (
            0xC095_C958,
            0xC1D0_54DE,
            0x418C_15E0,
            0xC076_B7DE,
            0x41D5_6672,
            0x414F_357C,
            0x403C_3AB0,
            0x412A_990C,
        ),
    )
    assert result.logits_binary32_sha256 == (
        "39eee776802412be8ad32c2d9ac21b76c8eac8385d7112cb6caa4acc64536514"
    )
    assert result.selected_hidden_bf16_sha256 == (
        "0b188d698a9e5f29a5ce4795ef0359b6256989aff373d53b8d3932d9ab19f734"
    )
    assert result.selected_weight_bf16_sha256 == (
        "b6ccb6bb100c580f786df921c978bd43b813addb9d6bd3d837921c048dae13fa"
    )


def test_independent_service_lane_fails_closed_and_has_no_reference_dependency() -> None:
    with pytest.raises(LMHeadServiceNumericError, match="finite BF16"):
        execute_selected_vocabulary_rows(
            ((0x7F80,),),
            ((0,),),
            vocabulary_row_indices=(0,),
            declared_vocabulary_size=4,
            tensor_parallel_world_size=1,
        )
    with pytest.raises(LMHeadServiceNumericError, match="divide across ranks"):
        execute_selected_vocabulary_rows(
            ((0,),),
            ((0,),),
            vocabulary_row_indices=(0,),
            declared_vocabulary_size=5,
            tensor_parallel_world_size=2,
        )
    import runtime.service_engine.lm_head_numeric as service_module

    service_source = Path(service_module.__file__).read_text(encoding="utf-8")
    service_tree = ast.parse(service_source)
    service_import_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(service_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    service_import_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(service_tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert service_import_roots.isdisjoint({"compiler", "runtime"})


def test_randomized_reference_matches_independent_binary32_composition() -> None:
    rng = random.Random(0x4C4D_4845_4144)
    palette = (
        0,
        0x0001,
        0x8001,
        _bf16(Fraction(1, 4)),
        _bf16(Fraction(-1, 4)),
        _bf16(1),
        _bf16(-1),
        _bf16(2),
        _bf16(-2),
        _bf16(8),
        _bf16(-8),
    )
    for _ in range(100):
        batches = rng.randint(1, 3)
        positions = rng.randint(1, 5)
        width = rng.randint(1, 12)
        vocabulary = rng.choice((4, 8, 12, 16))
        world_size = rng.choice(tuple(size for size in (1, 2, 4) if vocabulary % size == 0))
        full_logits = bool(rng.getrandbits(1))
        hidden = tuple(
            tuple(
                tuple(rng.choice(palette) for _ in range(width))
                for _ in range(positions)
            )
            for _ in range(batches)
        )
        weights = tuple(
            tuple(rng.choice(palette) for _ in range(width))
            for _ in range(vocabulary)
        )
        selected = tuple(
            token_id
            for token_id in range(vocabulary)
            if rng.randrange(3) == 0
        ) or (rng.randrange(vocabulary),)
        selected = tuple(sorted(set(selected)))
        result = head.lm_head_selected_bf16(
            hidden,
            tuple(weights[token_id] for token_id in selected),
            declared_vocabulary_size=vocabulary,
            selected_token_ids=selected,
            tensor_parallel_world_size=world_size,
            full_logits=full_logits,
        )
        selected_hidden = (
            hidden if full_logits else tuple((sequence[-1],) for sequence in hidden)
        )
        expected_full = tuple(
            tuple(
                tuple(
                    _independent_dot(row, weights[token_id])
                    for token_id in selected
                )
                for row in sequence
            )
            for sequence in selected_hidden
        )
        expected = expected_full if full_logits else tuple(
            sequence[0] for sequence in expected_full
        )
        assert result.logits_binary32_codes == expected


def test_binary32_overflow_poisons_complete_transaction() -> None:
    with pytest.raises(head.LMHeadReferenceError, match="accumulation overflow"):
        head.lm_head_selected_bf16(
            (((0x7F7F,),),),
            ((0x7F7F,),),
            declared_vocabulary_size=1,
            selected_token_ids=(0,),
            tensor_parallel_world_size=1,
        )


@pytest.mark.parametrize(
    ("hidden", "weights", "options", "match"),
    [
        (object(), ((0,),), {}, "hidden_bf16_codes must be an exact"),
        ((), ((0,),), {}, "batch extent"),
        (((),), ((0,),), {}, "sequence extent"),
        ((((),),), ((0,),), {}, "hidden width"),
        (
            (((0,),), ((0,), (0,))),
            ((0,),),
            {},
            "rectangular on the sequence",
        ),
        ((((0,), (0, 0)),), ((0,),), {}, "rectangular on the hidden"),
        ((((True,),),), ((0,),), {}, "16-bit BF16"),
        ((((0x10000,),),), ((0,),), {}, "16-bit BF16"),
        ((((0x7F80,),),), ((0,),), {}, "finite BF16"),
        ((((0,),),), object(), {}, "selected_weight_bf16_codes must"),
        ((((0,),),), (), {}, "row count"),
        ((((0,),),), ((0, 0),), {}, "hidden width 1"),
        ((((0,),),), ((True,),), {}, "16-bit BF16"),
        ((((0,),),), ((0x7FC0,),), {}, "finite BF16"),
        ((((0,),),), ((0,),), {"full_logits": 1}, "exact boolean"),
        (
            (((0,),),),
            ((0,),),
            {"tensor_parallel_world_size": 3},
            "exactly 1, 2, 4, or 8",
        ),
        (
            (((0,),),),
            ((0,),),
            {"declared_vocabulary_size": 3},
            "divisible",
        ),
        (
            (((0,),),),
            ((0,),),
            {"selected_token_ids": ()},
            "must not be empty",
        ),
        (
            (((0,),),),
            ((0,), (0,)),
            {"selected_token_ids": (1, 1)},
            "strictly increasing",
        ),
    ],
)
def test_selected_reference_rejects_malformed_or_nonfinite_inputs(
    hidden: object,
    weights: object,
    options: dict[str, object],
    match: str,
) -> None:
    arguments: dict[str, object] = {
        "declared_vocabulary_size": 4,
        "selected_token_ids": (0,),
        "tensor_parallel_world_size": 4,
    }
    arguments.update(options)
    with pytest.raises(head.LMHeadReferenceError, match=match):
        head.lm_head_selected_bf16(
            hidden,
            weights,
            **arguments,  # type: ignore[arg-type]
        )


def test_complete_reference_rejects_malformed_shard_topology() -> None:
    hidden = (((0,),),)
    with pytest.raises(head.LMHeadReferenceError, match="one shard"):
        head.lm_head_bf16(hidden, (((0,),),), tensor_parallel_world_size=4)
    with pytest.raises(head.LMHeadReferenceError, match="equal row counts"):
        head.lm_head_bf16(
            hidden,
            (((0,),), ((0,), (0,)), ((0,),), ((0,),)),
            tensor_parallel_world_size=4,
        )
    with pytest.raises(head.LMHeadReferenceError, match="must contain a row"):
        head.lm_head_bf16(hidden, ((),), tensor_parallel_world_size=1)


def test_result_is_immutable_hashed_and_structurally_reconciled() -> None:
    hidden = [[[0x3F80, 0x4000]]]
    weights = [[0x3F80, 0], [0, 0x3F80]]
    result = head.lm_head_selected_bf16(
        hidden,
        weights,
        declared_vocabulary_size=2,
        selected_token_ids=[0, 1],
        tensor_parallel_world_size=1,
    )
    expected = result.logits_binary32_codes
    hidden[0][0][0] = 0
    weights[0][0] = 0
    assert result.logits_binary32_codes == expected
    assert type(result.selected_token_ids) is tuple
    with pytest.raises(FrozenInstanceError):
        result.full_logits = True  # type: ignore[misc]
    with pytest.raises(head.LMHeadReferenceError, match="logits hash"):
        replace(result, logits_binary32_codes=((0, 0),))
    with pytest.raises(head.LMHeadReferenceError, match="partition ranks"):
        replace(result, selected_partition_ranks=(0, 1))
    with pytest.raises(head.LMHeadReferenceError, match="lowercase SHA-256"):
        replace(result, selected_weight_bf16_sha256="0" * 63)
    with pytest.raises(head.LMHeadReferenceError):
        replace(result.counters, binary32_logits_written=0)


def test_counter_and_claim_boundaries_exclude_physical_performance() -> None:
    names = {field.name for field in fields(head.LMHeadCounters)}
    assert {
        "source_hidden_bf16_values_validated",
        "selected_weight_bf16_values_read",
        "exact_product_accumulates",
        "binary32_logits_written",
        "logical_gathered_binary32_values",
        "transaction_commits",
    }.issubset(names)
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
        "ppa",
    )
    assert not any(token in name for name in names for token in prohibited)
    assert set(head.EXCLUDED_CLAIMS) == {
        "final_rms_normalization",
        "checkpoint_derived_hidden_state",
        "pytorch_cuda_gemm_bit_equivalence",
        "physical_tensor_parallel_collective",
        "compiler_service_or_rtl_execution",
        "physical_rom_sram_hbm_cycles_latency_bandwidth_throughput_energy_area_routing_ppa",
        "sampling_generation_or_end_to_end_model_evidence",
    }


def test_reference_has_no_framework_host_float_or_execution_layer_dependency() -> None:
    source_path = Path(head.__file__)
    source = source_path.read_text(encoding="utf-8")
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
    assert imported_roots.isdisjoint({"decimal", "math", "mpmath", "numpy", "torch"})
    assert "compiler." not in source
    assert "service_engine" not in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )
