from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

import pytest

from compiler.vertical_slice.deepseek_v4_compressor_executable import (
    KNOWN_SESSION_ID,
    build_deepseek_v4_compressor_executable_deployment,
    known_answer_inputs_from_ape,
)
from runtime.reference.formats import encode_binary32_rne
from runtime.service_engine import deepseek_v4_compressor_executable as service
from runtime.service_engine.deepseek_v4_compressor_executable import (
    DeepSeekV4CompressorExecutableServiceEngine,
    DeepSeekV4CompressorExecutableServiceError,
    build_deepseek_v4_compressor_request,
    build_initial_deepseek_v4_compressor_state,
    execute_deepseek_v4_compressor_executable_deployment,
    load_deepseek_v4_compressor_executable_deployment,
    load_deepseek_v4_compressor_state,
)


def _session(label: str) -> str:
    return hashlib.sha256(f"compressor-service:{label}".encode()).hexdigest()


def _constant_tensor(batch: int, sequence: int, value: int = 0) -> tuple:
    code = encode_binary32_rne(value)
    row = (code,) * 1024
    return tuple(tuple(row for _ in range(sequence)) for _ in range(batch))


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture(scope="module")
def synthetic_deployment(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("compressor-service")
    ape = root / "ape.f32le"
    ape.write_bytes(struct.pack("<4096I", *([0] * 4096)))
    deployment = root / "deployment"
    build_deepseek_v4_compressor_executable_deployment(
        ape,
        deployment,
        source_kind="synthetic",
    )
    return deployment


def test_full_width_known_answer_executes_from_artifacts_and_reconciles_counters(
    synthetic_deployment: Path,
    tmp_path: Path,
) -> None:
    loaded = load_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment
    )
    prior_dir = tmp_path / "state-0"
    prior = build_initial_deepseek_v4_compressor_state(
        synthetic_deployment,
        prior_dir,
    )
    kv, scores = known_answer_inputs_from_ape(loaded.ape_codes)
    request_dir = tmp_path / "request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        prior_dir,
        request_dir,
        projected_kv_f32_codes=kv,
        projected_score_f32_codes=scores,
        session_ids=(KNOWN_SESSION_ID,),
        start_pos=0,
    )
    result_dir = tmp_path / "result"
    result = execute_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment,
        prior_dir,
        request_dir,
        result_dir,
    )

    known = json.loads(
        (synthetic_deployment / "evidence/known_answer.json").read_text()
    )
    assert result.should_compress
    assert result.complete_group_count == 1
    assert result.prior_state_id == prior.state_id
    assert hashlib.sha256(
        (result_dir / "outputs/pooled.f32le").read_bytes()
    ).hexdigest() == known["expected"]["pooled_f32_sha256"]
    assert hashlib.sha256(
        (result_dir / "outputs/converted.bf16le").read_bytes()
    ).hexdigest() == known["expected"]["converted_bf16_sha256"]
    assert hashlib.sha256(
        (result_dir / "outputs/valid_view.bf16le").read_bytes()
    ).hexdigest() == known["expected"]["valid_view_bf16_sha256"]
    for stage, expected in known["counters"].items():
        assert result.counters[stage] == expected
    assert result.counters["logical_only"] is True
    assert result.counters["physical_interpretation"] is None
    assert result.counters["published_transaction_commits"] == 1

    successor = load_deepseek_v4_compressor_state(
        result.state_dir,
        expected_build_id=loaded.build_id,
    )
    assert successor.state_id == result.state_id
    assert successor.prior_state_id == prior.state_id
    assert successor.transition_id == result.transition_id
    assert successor.sequence_number == 1
    assert successor.raw_state.lanes[0].session_id == KNOWN_SESSION_ID
    assert successor.raw_state.lanes[0].next_pos == 4
    assert successor.raw_state.lanes[0].version == 1
    assert successor.compressed_state.valid_prefix_lengths == (1, 0, 0, 0)
    assert successor.compressed_state.versions == (1, 0, 0, 0)

    report = json.loads((result_dir / "reports/execution.json").read_text())
    assert report["timing_claim"] is None
    assert [record["status"] for record in report["trace"]] == [
        "executed",
        "executed",
        "executed",
        "candidate_only",
        "candidate_only",
        "awaiting_publication",
    ]
    assert "RMSNorm" in report["boundary"]["post_conversion_harness"]


def test_optional_pool_payload_is_absent_until_exact_ratio_boundary(
    synthetic_deployment: Path,
    tmp_path: Path,
) -> None:
    loaded = load_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment
    )
    session_id = _session("boundary")
    initial_dir = tmp_path / "state-0"
    build_initial_deepseek_v4_compressor_state(synthetic_deployment, initial_dir)
    request0 = tmp_path / "request-0"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        initial_dir,
        request0,
        projected_kv_f32_codes=_constant_tensor(1, 3, 1),
        projected_score_f32_codes=_constant_tensor(1, 3, 0),
        session_ids=(session_id,),
        start_pos=0,
    )
    result0_dir = tmp_path / "result-0"
    result0 = execute_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment,
        initial_dir,
        request0,
        result0_dir,
    )
    assert not result0.should_compress
    assert result0.complete_group_count == 0
    assert not (result0_dir / "outputs/pooled.f32le").exists()
    assert not (result0_dir / "outputs/converted.bf16le").exists()
    assert (result0_dir / "outputs/valid_view.bf16le").stat().st_size == 0
    assert result0.counters["pool"] is None
    assert result0.counters["conversion"] is None
    state0 = load_deepseek_v4_compressor_state(
        result0.state_dir,
        expected_build_id=loaded.build_id,
    )
    assert state0.raw_state.lanes[0].next_pos == 3
    assert state0.compressed_state.next_positions[0] == 3
    assert state0.compressed_state.valid_prefix_lengths[0] == 0

    request1 = tmp_path / "request-1"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        result0.state_dir,
        request1,
        projected_kv_f32_codes=_constant_tensor(1, 1, 1),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_id,),
        start_pos=3,
    )
    result1_dir = tmp_path / "result-1"
    result1 = execute_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment,
        result0.state_dir,
        request1,
        result1_dir,
    )
    assert result1.should_compress
    assert result1.complete_group_count == 1
    assert (result1_dir / "outputs/pooled.f32le").stat().st_size == 512 * 4
    assert (result1_dir / "outputs/converted.bf16le").stat().st_size == 512 * 2
    assert (result1_dir / "outputs/valid_view.bf16le").stat().st_size == 512 * 2
    state1 = load_deepseek_v4_compressor_state(
        result1.state_dir,
        expected_build_id=loaded.build_id,
    )
    assert state1.raw_state.lanes[0].next_pos == 4
    assert state1.compressed_state.valid_prefix_lengths[0] == 1


def test_downstream_abort_discards_candidate_and_leaves_prior_unchanged(
    synthetic_deployment: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = load_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment
    )
    prior_dir = tmp_path / "state"
    build_initial_deepseek_v4_compressor_state(synthetic_deployment, prior_dir)
    before = _tree_hashes(prior_dir)
    kv, scores = known_answer_inputs_from_ape(loaded.ape_codes)
    request_dir = tmp_path / "request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        prior_dir,
        request_dir,
        projected_kv_f32_codes=kv,
        projected_score_f32_codes=scores,
        session_ids=(KNOWN_SESSION_ID,),
        start_pos=0,
    )

    def poison(_: object) -> object:
        raise RuntimeError("injected conversion poison")

    monkeypatch.setattr(service, "binary32_tensor_to_bf16_rne", poison)
    result_dir = tmp_path / "aborted-result"
    with pytest.raises(
        DeepSeekV4CompressorExecutableServiceError,
        match="candidate execution poisoned",
    ):
        execute_deepseek_v4_compressor_executable_deployment(
            synthetic_deployment,
            prior_dir,
            request_dir,
            result_dir,
        )
    assert not result_dir.exists()
    assert _tree_hashes(prior_dir) == before
    reloaded = load_deepseek_v4_compressor_state(
        prior_dir,
        expected_build_id=loaded.build_id,
    )
    assert reloaded.sequence_number == 0


def test_decode_replay_and_stale_session_fail_without_successor(
    synthetic_deployment: Path,
    tmp_path: Path,
) -> None:
    session_a = _session("causal-a")
    session_b = _session("causal-b")
    initial_dir = tmp_path / "state-0"
    build_initial_deepseek_v4_compressor_state(synthetic_deployment, initial_dir)
    prefill_request = tmp_path / "prefill-request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        initial_dir,
        prefill_request,
        projected_kv_f32_codes=_constant_tensor(1, 1, 3),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_a,),
        start_pos=0,
    )
    prefill_result_dir = tmp_path / "prefill-result"
    prefill = execute_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment,
        initial_dir,
        prefill_request,
        prefill_result_dir,
    )
    decode_request = tmp_path / "decode-request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        prefill.state_dir,
        decode_request,
        projected_kv_f32_codes=_constant_tensor(1, 1, 4),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_a,),
        start_pos=1,
    )
    decode_result_dir = tmp_path / "decode-result"
    decoded = execute_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment,
        prefill.state_dir,
        decode_request,
        decode_result_dir,
    )
    successor_before = _tree_hashes(decoded.state_dir)

    replay_request = tmp_path / "replay-request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        decoded.state_dir,
        replay_request,
        projected_kv_f32_codes=_constant_tensor(1, 1, 5),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_a,),
        start_pos=1,
    )
    with pytest.raises(
        DeepSeekV4CompressorExecutableServiceError,
        match="expected start_pos 2",
    ):
        execute_deepseek_v4_compressor_executable_deployment(
            synthetic_deployment,
            decoded.state_dir,
            replay_request,
            tmp_path / "replay-result",
        )
    assert not (tmp_path / "replay-result").exists()

    stale_request = tmp_path / "stale-request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        decoded.state_dir,
        stale_request,
        projected_kv_f32_codes=_constant_tensor(1, 1, 5),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_b,),
        start_pos=2,
    )
    with pytest.raises(
        DeepSeekV4CompressorExecutableServiceError,
        match="session ID does not match",
    ):
        execute_deepseek_v4_compressor_executable_deployment(
            synthetic_deployment,
            decoded.state_dir,
            stale_request,
            tmp_path / "stale-result",
        )
    assert not (tmp_path / "stale-result").exists()
    assert _tree_hashes(decoded.state_dir) == successor_before


def test_lane_retirement_hides_retired_capacity_and_prevents_reactivation(
    synthetic_deployment: Path,
    tmp_path: Path,
) -> None:
    loaded = load_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment
    )
    session_a = _session("retire-a")
    session_b = _session("retire-b")
    initial_dir = tmp_path / "state-0"
    build_initial_deepseek_v4_compressor_state(synthetic_deployment, initial_dir)
    request0 = tmp_path / "request-0"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        initial_dir,
        request0,
        projected_kv_f32_codes=_constant_tensor(2, 4, 2),
        projected_score_f32_codes=_constant_tensor(2, 4, 0),
        session_ids=(session_a, session_b),
        start_pos=0,
    )
    result0 = execute_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment,
        initial_dir,
        request0,
        tmp_path / "result-0",
    )
    request1 = tmp_path / "request-1"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        result0.state_dir,
        request1,
        projected_kv_f32_codes=_constant_tensor(1, 1, 3),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_a,),
        start_pos=4,
    )
    result1_dir = tmp_path / "result-1"
    result1 = execute_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment,
        result0.state_dir,
        request1,
        result1_dir,
    )
    state = load_deepseek_v4_compressor_state(
        result1.state_dir,
        expected_build_id=loaded.build_id,
    )
    assert state.compressed_state.session_ids[:2] == (session_a, session_b)
    assert state.compressed_state.lane_active[:2] == (True, False)
    assert state.compressed_state.next_positions[:2] == (5, 0)
    assert state.compressed_state.valid_prefix_lengths[:2] == (1, 0)
    assert state.compressed_state.versions[:2] == (2, 2)
    assert (result1_dir / "outputs/valid_view.bf16le").stat().st_size == 512 * 2
    assert result1.counters["valid_prefix_view"]["valid_rows_returned"] == 1
    assert result1.counters["valid_prefix_view"]["total_state_rows_not_exposed"] == 31

    reactivate = tmp_path / "reactivate-request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        result1.state_dir,
        reactivate,
        projected_kv_f32_codes=_constant_tensor(2, 1, 4),
        projected_score_f32_codes=_constant_tensor(2, 1, 0),
        session_ids=(session_a, session_b),
        start_pos=5,
    )
    with pytest.raises(DeepSeekV4CompressorExecutableServiceError):
        execute_deepseek_v4_compressor_executable_deployment(
            synthetic_deployment,
            result1.state_dir,
            reactivate,
            tmp_path / "reactivate-result",
        )
    assert not (tmp_path / "reactivate-result").exists()


def test_state_payload_tamper_and_create_once_result_fail_closed(
    synthetic_deployment: Path,
    tmp_path: Path,
) -> None:
    loaded = load_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment
    )
    state_dir = tmp_path / "state"
    build_initial_deepseek_v4_compressor_state(synthetic_deployment, state_dir)
    payload_path = state_dir / "raw_kv.f32le"
    payload = bytearray(payload_path.read_bytes())
    payload[0] ^= 1
    payload_path.write_bytes(payload)
    with pytest.raises(
        DeepSeekV4CompressorExecutableServiceError,
        match="digest",
    ):
        load_deepseek_v4_compressor_state(
            state_dir,
            expected_build_id=loaded.build_id,
        )

    clean_state = tmp_path / "clean-state"
    build_initial_deepseek_v4_compressor_state(synthetic_deployment, clean_state)
    session_id = _session("collision")
    request = tmp_path / "request"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        clean_state,
        request,
        projected_kv_f32_codes=_constant_tensor(1, 1, 1),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_id,),
        start_pos=0,
    )
    result = tmp_path / "result"
    result.mkdir()
    marker = result / "marker"
    marker.write_bytes(b"preserve")
    with pytest.raises(
        DeepSeekV4CompressorExecutableServiceError,
        match="already exists",
    ):
        execute_deepseek_v4_compressor_executable_deployment(
            synthetic_deployment,
            clean_state,
            request,
            result,
        )
    assert marker.read_bytes() == b"preserve"


def test_fresh_engine_can_continue_only_from_published_state_artifact(
    synthetic_deployment: Path,
    tmp_path: Path,
) -> None:
    session_id = _session("restart")
    state0 = tmp_path / "state-0"
    build_initial_deepseek_v4_compressor_state(synthetic_deployment, state0)
    request0 = tmp_path / "request-0"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        state0,
        request0,
        projected_kv_f32_codes=_constant_tensor(1, 1, 1),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_id,),
        start_pos=0,
    )
    engine0 = DeepSeekV4CompressorExecutableServiceEngine.load(
        synthetic_deployment
    )
    result0 = engine0.execute(state0, request0, tmp_path / "result-0")

    # A new engine object has no process-local session state.  It can continue
    # solely because the published successor package carries the complete
    # causal raw/compressed state and hash chain.
    request1 = tmp_path / "request-1"
    build_deepseek_v4_compressor_request(
        synthetic_deployment,
        result0.state_dir,
        request1,
        projected_kv_f32_codes=_constant_tensor(1, 1, 2),
        projected_score_f32_codes=_constant_tensor(1, 1, 0),
        session_ids=(session_id,),
        start_pos=1,
    )
    engine1 = DeepSeekV4CompressorExecutableServiceEngine.load(
        synthetic_deployment
    )
    result1 = engine1.execute(
        result0.state_dir,
        request1,
        tmp_path / "result-1",
    )
    assert result1.prior_state_id == result0.state_id
    assert result1.state_id != result0.state_id
    assert result1.transition_id != result0.transition_id
