from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict, fields, replace
import hashlib
import json
import os
from pathlib import Path
import struct

import pytest

import runtime.reference.dspark_prefill_kv as prefill
from runtime.reference.kv_window import zero_kv_window_state_bf16
from runtime.reference.matrix import dense_fp8_linear_selected_rows_bf16
from runtime.reference.normalization import rms_norm_bf16
from runtime.reference.quantization import fp8_qdq_bf16
from runtime.reference.rope import BASE_ROPE_PROFILE, apply_rotary_bf16_result
from runtime.service_engine.fp8_numeric import execute_selected_rows
from runtime.service_engine.rms_numeric import execute_weighted_rms_norm


_EVIDENCE_ROOT_ENV = "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT"
_SELECTED_ROWS = (0, 127, 128, 511)
_SYNTHETIC_RECORD_SHA256 = (
    "ac40a0164a66e9bffd2b35c96c8e4ab40da383777be2a26b90cce2ecfed2d793"
)
_OFFICIAL_EXTENT_SHA256 = (
    "b46f98c555cbf8c7c04fbf35116c66de63e77af82e75067bc48e21a58c6b4459"
)
_OFFICIAL_SELECTED_SHA256 = (
    "a6a2e504bc02a860ec744a2fe7a4756608aaf2732c697cc80b43e22113f128cb"
)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _flatten_codes(value: object):
    if type(value) is int:
        yield value
        return
    assert type(value) is tuple
    for item in value:
        yield from _flatten_codes(item)


def _code_sha256(value: object, *, width: int) -> str:
    return hashlib.sha256(
        b"".join(code.to_bytes(width, "little") for code in _flatten_codes(value))
    ).hexdigest()


def _sid(stage: int, token: int = 0) -> str:
    return f"{stage + 1:02x}{token + 1:062x}"


def _zero_state(*, capacity: int = 1):
    return zero_kv_window_state_bf16(
        batch_capacity=capacity,
        window_size=prefill.WINDOW_SIZE,
        kv_head_count=1,
        kv_value_width=prefill.KV_WIDTH,
    )


def _zero_conditioning(
    token_count: int,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    row = (0,) * prefill.INPUT_WIDTH
    return ((row,) * token_count,)


def _synthetic_fixture():
    first = [0] * prefill.INPUT_WIDTH
    second = [0] * prefill.INPUT_WIDTH
    first[0:3] = (0x3F80, 0x4000, 0x4040)
    second[0:3] = (0xBF80, 0x3F00, 0xC000)
    conditioning = ((tuple(first), tuple(second)),)

    weights = bytearray(prefill.WEIGHT_BYTES)
    # One non-RoPE output and one adjacent RoPE pair make every downstream
    # boundary data-bearing while retaining the complete declared shape.
    for output_row, input_column, code in (
        (0, 0, 0x38),
        (448, 1, 0x38),
        (449, 2, 0xB8),
    ):
        weights[output_row * prefill.INPUT_WIDTH + input_column] = code
    scales = bytearray(prefill.SCALE_BYTES)
    scales[0] = 0x7F
    scales[3 * prefill.REDUCTION_BLOCKS] = 0x7F
    norm = [0x3F80] * prefill.KV_WIDTH
    norm[0] = 0x3F00
    norm[448] = 0x3FC0
    norm[449] = 0xBF80
    return conditioning, bytes(weights), bytes(scales), tuple(norm)


@pytest.fixture(scope="module")
def synthetic_fixture():
    return _synthetic_fixture()


def _official_resources() -> tuple[
    tuple[bytes, bytes, tuple[int, ...]], ...
]:
    configured = os.environ.get(_EVIDENCE_ROOT_ENV)
    if configured is None:
        pytest.skip(f"set {_EVIDENCE_ROOT_ENV} to run official-payload evidence")
    rank = Path(configured) / "canonical-mp4/ranks/rank-000"
    result = []
    for stage in range(prefill.STAGE_COUNT):
        weight_path = rank / f"mtp.{stage}.attn.wkv.weight.bin"
        scale_path = rank / f"mtp.{stage}.attn.wkv.scale.bin"
        norm_path = rank / f"mtp.{stage}.attn.kv_norm.weight.bin"
        if not all(path.is_file() for path in (weight_path, scale_path, norm_path)):
            pytest.skip(f"official DSpark stage resources are unavailable below {rank}")
        weights = weight_path.read_bytes()
        scales = scale_path.read_bytes()
        norm_payload = norm_path.read_bytes()
        assert hashlib.sha256(weights).hexdigest() == (
            prefill.OFFICIAL_WEIGHT_SHA256[stage]
        )
        assert hashlib.sha256(scales).hexdigest() == (
            prefill.OFFICIAL_SCALE_SHA256[stage]
        )
        assert hashlib.sha256(norm_payload).hexdigest() == (
            prefill.OFFICIAL_NORM_WEIGHT_SHA256[stage]
        )
        norm = struct.unpack(f"<{prefill.KV_WIDTH}H", norm_payload)
        result.append((weights, scales, norm))
    return tuple(result)


def _result_record(result: prefill.DSparkPrefillKVResult) -> dict[str, object]:
    return {
        "activation_saturations": result.activation_saturated_block_count,
        "committed_kv_sha256": _code_sha256(
            result.committed_kv_bf16_codes,
            width=2,
        ),
        "counter_sha256": hashlib.sha256(
            _canonical_bytes(asdict(result.counters))
        ).hexdigest(),
        "mean_sha256": _code_sha256(
            result.mean_square_binary32_codes,
            width=4,
        ),
        "normalized_sha256": _code_sha256(
            result.normalized_bf16_codes,
            width=2,
        ),
        "projection_saturations": result.projection_saturated_output_count,
        "projection_sha256": _code_sha256(
            result.projection_bf16_codes,
            width=2,
        ),
        "qdq_code_sha256": _code_sha256(result.qdq_e4m3fn_codes, width=1),
        "qdq_scale_sha256": _code_sha256(
            result.qdq_scale_e8m0_codes,
            width=1,
        ),
        "rms_saturations": result.normalization_saturated_output_count,
        "rope_sha256": _code_sha256(result.rotated_bf16_codes, width=2),
        "stage": result.stage_id,
        "state_sha256": _code_sha256(
            result.window_write.state.bf16_codes,
            width=2,
        ),
        "token_count": result.counters.token_count,
    }


def test_identity_shapes_precision_and_source_sequence_are_frozen() -> None:
    assert prefill.OFFICIAL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert prefill.OFFICIAL_REVISION == (
        "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    )
    assert prefill.INPUT_WIDTH == 4096
    assert prefill.KV_WIDTH == 512
    assert prefill.ROPE_WIDTH == 64
    assert prefill.QDQ_WIDTH == 448
    assert prefill.REDUCTION_BLOCKS == 32
    assert prefill.FP8_QDQ_BLOCKS == 7
    assert prefill.WEIGHT_BYTES == 2_097_152
    assert prefill.SCALE_BYTES == 128
    assert prefill.NORM_WEIGHT_BYTES == 1_024
    assert prefill.WINDOW_SIZE == 128
    assert prefill.STAGE_COUNT == 3
    assert prefill.MAX_PREFILL_SEQUENCE == 65_536
    assert prefill.NUMERIC_PROFILE == (
        "opentallas.deepseek_v4_dspark_prefill_kv_bf16.v1"
    )
    assert prefill.SOURCE_EXPRESSIONS[-4:] == (
        "main_kv = self.kv_norm(self.wkv(main_x))",
        "apply_rotary_emb(main_kv[..., -rd:], main_freqs_cis)",
        "act_quant(main_kv[..., :-rd], 64, scale_fmt, scale_dtype, True)",
        "self.kv_cache[:bsz, :seqlen] = main_kv",
    )


def test_pinned_source_contains_prefill_only_control_and_operation_order() -> None:
    snapshot = (
        Path.home()
        / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / prefill.OFFICIAL_REVISION
    )
    source_path = snapshot / prefill.MODEL_SOURCE_PATH
    config_path = snapshot / prefill.INFERENCE_CONFIG_PATH
    if not source_path.is_file() or not config_path.is_file():
        pytest.skip("pinned official source snapshot is unavailable")
    source_payload = source_path.read_bytes()
    config_payload = config_path.read_bytes()
    assert hashlib.sha256(source_payload).hexdigest() == prefill.MODEL_SOURCE_SHA256
    assert hashlib.sha256(config_payload).hexdigest() == (
        prefill.INFERENCE_CONFIG_SHA256
    )
    source = source_payload.decode("utf-8")
    assert all(expression in source for expression in prefill.SOURCE_EXPRESSIONS)
    config = json.loads(config_payload)
    assert config["dtype"] == "fp8"
    assert config["scale_fmt"] == "ue8m0"
    assert config["n_mtp_layers"] == 3
    assert config["window_size"] == 128
    assert config["rope_head_dim"] == 64


def test_reference_imports_only_qualified_semantic_components() -> None:
    source = Path(prefill.__file__).read_text(encoding="utf-8")
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
        {"compiler", "decimal", "math", "mpmath", "numpy", "torch"}
    )
    assert "runtime.service_engine" not in source
    assert "from .matrix import" in source
    assert "from .normalization import" in source
    assert "from .rope import" in source
    assert "from .quantization import" in source
    assert "from .kv_window import" in source


def test_nonclaims_and_counter_names_do_not_promote_physical_performance() -> None:
    assert "physical_rom_sram_hbm_cycles_latency_bandwidth_throughput_energy_area_ppa" in (
        prefill.EXCLUDED_CLAIMS
    )
    names = {field.name for field in fields(prefill.DSparkPrefillKVCounters)}
    prohibited = ("cycle", "latency", "bandwidth", "throughput", "energy", "ppa")
    assert not any(token in name for name in names for token in prohibited)
    assert "window_state_write_logical_bytes" in names


def test_nonzero_full_shape_composition_retains_every_boundary(
    synthetic_fixture,
) -> None:
    conditioning, weights, scales, norm = synthetic_fixture
    state = _zero_state()
    result = prefill.dspark_prefill_kv_bf16(
        conditioning,
        weights,
        scales,
        norm,
        state,
        stage_id=1,
        active_session_ids=(_sid(1),),
        expected_window_state_versions=state.versions,
    )
    assert any(result.projection_bf16_codes[0][0])
    assert any(result.normalized_bf16_codes[0][0])
    assert any(result.rotated_bf16_codes[0][0])
    assert any(result.committed_kv_bf16_codes[0][0])
    assert result.window_write.input_bf16_codes == tuple(
        tuple((row,) for row in sequence)
        for sequence in result.committed_kv_bf16_codes
    )
    assert result.window_write.state.next_positions == (2,)
    assert result.window_write.state.session_ids == (_sid(1),)
    assert result.counters.projection_exact_product_accumulates == (
        2 * 512 * 4096
    )
    assert result.counters.projection_cross_block_reduction_adds == (
        2 * 512 * 31
    )
    assert result.counters.qdq_blocks_quantized == 2 * 7
    assert hashlib.sha256(_canonical_bytes(_result_record(result))).hexdigest() == (
        _SYNTHETIC_RECORD_SHA256
    )


def test_direct_qualified_component_composition_matches_wrapper(
    synthetic_fixture,
) -> None:
    conditioning, weights, scales, norm = synthetic_fixture
    state = _zero_state()
    result = prefill.dspark_prefill_kv_bf16(
        conditioning,
        weights,
        scales,
        norm,
        state,
        stage_id=2,
        active_session_ids=(_sid(2),),
        expected_window_state_versions=state.versions,
    )
    projection_rows = tuple(row for sequence in result.projection_bf16_codes for row in sequence)
    direct_norm = rms_norm_bf16(projection_rows, norm)
    direct_service_norm = execute_weighted_rms_norm(projection_rows, norm)
    assert direct_norm.output_codes == direct_service_norm.output_codes
    assert direct_norm.mean_square_codes == direct_service_norm.mean_square_codes
    assert direct_norm.inverse_rms_codes == direct_service_norm.inverse_rms_codes
    direct_norm_batch = (direct_norm.output_codes,)
    direct_rope = apply_rotary_bf16_result(
        direct_norm_batch,
        0,
        profile=BASE_ROPE_PROFILE,
    )
    assert direct_rope.output_bf16_codes == result.rotated_bf16_codes
    prefixes = tuple(row[: prefill.QDQ_WIDTH] for row in direct_rope.output_bf16_codes[0])
    direct_qdq = fp8_qdq_bf16(prefixes)
    assert direct_qdq.e4m3fn_codes == result.qdq_e4m3fn_codes[0]
    assert direct_qdq.scale_codes == result.qdq_scale_e8m0_codes[0]


def test_malformed_nonfinite_resource_and_mode_inputs_fail_closed(
    synthetic_fixture,
) -> None:
    conditioning, weights, scales, norm = synthetic_fixture
    state = _zero_state()
    bad_conditioning = (
        ((0x7F80,) + (0,) * (prefill.INPUT_WIDTH - 1),),
    )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="finite BF16"):
        prefill.dspark_prefill_kv_bf16(
            bad_conditioning,
            weights,
            scales,
            norm,
            state,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=state.versions,
        )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="immutable bytes"):
        prefill.dspark_prefill_kv_bf16(
            conditioning,
            bytearray(weights),
            scales,
            norm,
            state,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=state.versions,
        )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="start_pos"):
        prefill.dspark_prefill_kv_bf16(
            conditioning,
            weights,
            scales,
            norm,
            state,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=state.versions,
            start_pos=1,
        )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="stage_id"):
        prefill.dspark_prefill_kv_bf16(
            conditioning,
            weights,
            scales,
            norm,
            state,
            stage_id=3,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=state.versions,
        )


def test_forbidden_resource_codes_validate_before_zero_acceleration() -> None:
    state = _zero_state()
    weights = bytes(prefill.WEIGHT_BYTES)
    scales = bytes(prefill.SCALE_BYTES)
    norm = (0x3F80,) * prefill.KV_WIDTH
    for bad_weight in (weights[:-1] + b"\x7f", weights[:-1] + b"\xff"):
        with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="forbidden"):
            prefill.dspark_prefill_kv_bf16(
                _zero_conditioning(1),
                bad_weight,
                scales,
                norm,
                state,
                stage_id=0,
                active_session_ids=(_sid(0),),
                expected_window_state_versions=state.versions,
            )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="forbidden"):
        prefill.dspark_prefill_kv_bf16(
            _zero_conditioning(1),
            weights,
            scales[:-1] + b"\xff",
            norm,
            state,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=state.versions,
        )


def test_projection_overflow_poisons_before_window_commit() -> None:
    conditioning = (
        ((0x7F7F,) + (0,) * (prefill.INPUT_WIDTH - 1),),
    )
    weights = bytearray(prefill.WEIGHT_BYTES)
    weights[0] = 0x7E
    scales = bytearray(prefill.SCALE_BYTES)
    scales[0] = 0xFE
    state = _zero_state()
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="overflow"):
        prefill.dspark_prefill_kv_bf16(
            conditioning,
            bytes(weights),
            bytes(scales),
            (0x3F80,) * prefill.KV_WIDTH,
            state,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=state.versions,
        )
    assert state.versions == (0,)
    assert state.next_positions == (0,)


def test_window_shape_stale_authority_and_session_reuse_fail_closed(
    synthetic_fixture,
) -> None:
    conditioning, weights, scales, norm = synthetic_fixture
    wrong_window = zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=4,
        kv_head_count=1,
        kv_value_width=prefill.KV_WIDTH,
    )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="128 slots"):
        prefill.dspark_prefill_kv_bf16(
            conditioning,
            weights,
            scales,
            norm,
            wrong_window,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=wrong_window.versions,
        )
    state = _zero_state()
    first = prefill.dspark_prefill_kv_bf16(
        conditioning,
        weights,
        scales,
        norm,
        state,
        stage_id=0,
        active_session_ids=(_sid(0),),
        expected_window_state_versions=state.versions,
    )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="fresh prefill"):
        prefill.dspark_prefill_kv_bf16(
            conditioning,
            weights,
            scales,
            norm,
            first.window_write.state,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=first.window_write.state.versions,
        )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="versions"):
        prefill.dspark_prefill_kv_bf16(
            conditioning,
            weights,
            scales,
            norm,
            state,
            stage_id=0,
            active_session_ids=(_sid(0),),
            expected_window_state_versions=(1,),
        )


def test_result_is_deeply_immutable_and_reconstructs_downstream_boundaries(
    synthetic_fixture,
) -> None:
    state = _zero_state()
    result = prefill.dspark_prefill_kv_bf16(
        *synthetic_fixture,
        state,
        stage_id=0,
        active_session_ids=(_sid(0),),
        expected_window_state_versions=state.versions,
    )
    with pytest.raises(FrozenInstanceError):
        result.stage_id = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.committed_kv_bf16_codes[0][0][0] = 0  # type: ignore[index]
    forged = (
        (
            (0,) + result.normalized_bf16_codes[0][0][1:],
            result.normalized_bf16_codes[0][1],
        ),
    )
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="does not reconcile"):
        replace(result, normalized_bf16_codes=forged)
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="counters"):
        replace(result.counters, transaction_commits=0)
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="counters"):
        replace(
            result.counters,
            window_state_rows_preserved=(
                result.counters.window_state_rows_preserved + 1
            ),
        )


def test_exact_result_type_rejects_subclass_authority(synthetic_fixture) -> None:
    state = _zero_state()
    result = prefill.dspark_prefill_kv_bf16(
        *synthetic_fixture,
        state,
        stage_id=0,
        active_session_ids=(_sid(0),),
        expected_window_state_versions=state.versions,
    )

    class Derived(prefill.DSparkPrefillKVResult):
        pass

    kwargs = {field.name: getattr(result, field.name) for field in fields(result)}
    with pytest.raises(prefill.DSparkPrefillKVReferenceError, match="exact"):
        Derived(**kwargs)


def test_official_resources_zero_input_match_all_stages_and_extents() -> None:
    resources = _official_resources()
    records = []
    authority = []
    for stage, (weights, scales, norm) in enumerate(resources):
        identities = prefill.official_resource_hashes(weights, scales, norm)
        assert identities == {
            "norm_weight_sha256": prefill.OFFICIAL_NORM_WEIGHT_SHA256[stage],
            "scale_sha256": prefill.OFFICIAL_SCALE_SHA256[stage],
            "weight_sha256": prefill.OFFICIAL_WEIGHT_SHA256[stage],
        }
        authority.append(identities)
        for token_count in range(1, 5):
            state = _zero_state()
            result = prefill.dspark_prefill_kv_bf16(
                _zero_conditioning(token_count),
                weights,
                scales,
                norm,
                state,
                stage_id=stage,
                active_session_ids=(_sid(stage, token_count),),
                expected_window_state_versions=state.versions,
            )
            zero = ((0,) * prefill.KV_WIDTH,) * token_count
            assert result.projection_bf16_codes == (zero,)
            assert result.normalized_bf16_codes == (zero,)
            assert result.rotated_bf16_codes == (zero,)
            assert result.committed_kv_bf16_codes == (zero,)
            assert result.window_write.state.next_positions == (token_count,)
            records.append(_result_record(result))
    aggregate = {"authority": authority, "records": records}
    assert hashlib.sha256(_canonical_bytes(aggregate)).hexdigest() == (
        _OFFICIAL_EXTENT_SHA256
    )


def test_selected_official_projection_rows_match_independent_fp8_lane() -> None:
    resources = _official_resources()
    input_row = [0] * prefill.INPUT_WIDTH
    palette = (0x3F80, 0xBF00, 0x4000, 0xBE80, 0x4040, 0xC000)
    for block in range(prefill.REDUCTION_BLOCKS):
        input_row[block * 128 + block] = palette[block % len(palette)]
    input_rows = (tuple(input_row),)
    records = []
    for stage, (weights, scales, _) in enumerate(resources):
        weight_view = memoryview(weights)
        scale_view = memoryview(scales)
        selected_weights = tuple(
            weight_view[row * prefill.INPUT_WIDTH : (row + 1) * prefill.INPUT_WIDTH]
            for row in _SELECTED_ROWS
        )
        scale_rows = tuple(
            scale_view[
                tile
                * prefill.REDUCTION_BLOCKS : (tile + 1)
                * prefill.REDUCTION_BLOCKS
            ]
            for tile in range(prefill.KV_WIDTH // 128)
        )
        reference = dense_fp8_linear_selected_rows_bf16(
            input_rows,
            selected_weights,
            scale_rows,
            output_row_indices=_SELECTED_ROWS,
            declared_output_count=prefill.KV_WIDTH,
        )

        def weight_row(logical_row: int) -> bytes:
            start = logical_row * prefill.INPUT_WIDTH
            return weights[start : start + prefill.INPUT_WIDTH]

        def scale_code(logical_row: int, block: int) -> int:
            return scales[(logical_row // 128) * prefill.REDUCTION_BLOCKS + block]

        service, activation_saturations, output_saturations = execute_selected_rows(
            input_rows,
            selected_rows=_SELECTED_ROWS,
            input_features=prefill.INPUT_WIDTH,
            weight_row=weight_row,
            scale_code=scale_code,
        )
        assert reference.values == service
        assert reference.activation_saturated_block_count == activation_saturations
        assert reference.output_saturated_element_count == output_saturations
        records.append(
            {
                "activation_saturations": activation_saturations,
                "output_saturations": output_saturations,
                "output_sha256": _code_sha256(service, width=2),
                "selected_weight_sha256": hashlib.sha256(
                    b"".join(selected_weights)
                ).hexdigest(),
                "stage": stage,
            }
        )
    aggregate = {
        "activation_sha256": _code_sha256(input_rows, width=2),
        "records": records,
        "selected_rows": list(_SELECTED_ROWS),
    }
    assert hashlib.sha256(_canonical_bytes(aggregate)).hexdigest() == (
        _OFFICIAL_SELECTED_SHA256
    )
