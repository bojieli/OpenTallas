from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.measured_gpu_break_even import (
    MeasuredBreakEvenError,
    build_result,
    render_report,
    strict_json,
    validate_measurement,
)
from tools.profile_local_qwen3_vl import validate_lock


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/benchmarks/local_gpu_measured_break_even_v2.json"
MODEL_LOCK = ROOT / "configs/benchmarks/local_qwen3_vl_30b_fp8_lock.json"
MEASUREMENT = (
    ROOT
    / "results/gpu/local_rtx_pro_6000_measured_break_even"
    / "20260828T114437Z/measurement.json"
)
RESULT = ROOT / "results/gpu/measured_break_even/measured_break_even.json"
REPORT = ROOT / "results/gpu/measured_break_even/REPORT.md"


def test_model_accounting_lock_closes_internal_identities() -> None:
    lock = strict_json(MODEL_LOCK)
    validate_lock(lock)
    assert lock["model"]["revision"] == "d9748a51ae66354c4dad665aab2c71f26cf2c8cd"
    assert lock["checkpoint"]["tensor_count"] == 1170
    assert lock["checkpoint"]["full_checkpoint_payload_bytes"] == 32_251_808_224
    binding = lock["runtime_binding"]
    assert binding["endpoint_api_revision_attested"] is False
    assert binding["accounting_snapshot_revision"] == lock["model"]["revision"]
    assert binding["local_cache_snapshot_revisions"] == [lock["model"]["revision"]]


def test_measured_break_even_is_byte_reproducible_from_archived_inputs() -> None:
    first = build_result(CONFIG, MEASUREMENT)
    second = build_result(CONFIG, MEASUREMENT)
    assert first == second
    assert strict_json(RESULT) == first
    assert REPORT.read_text(encoding="utf-8") == render_report(first)
    assert first["source_measurement_generated_at"] == "2026-08-28T11:44:55.122+00:00"
    assert first["comparison_contract"]["endpoint_runtime"]["version"] == "0.19.0"
    assert all(first["measurement_environment"]["endpoint_version_stability"].values())
    assert (
        first["measurement_environment"]["gpu_before"]["driver_version"] == "595.71.05"
    )
    assert (
        "not API-attested" in first["comparison_contract"]["runtime_revision_binding"]
    )
    assert first["reference_threshold"]["energy_requirement"] is None
    assert first["comparison_contract"]["contamination_label"] == "shared_contended"
    reference = first["reference_threshold"]
    assert reference["required_aggregate_tokens_s"] == pytest.approx(134.77854528322558)
    assert reference["maximum_aggregate_token_interval_s"] == pytest.approx(
        0.007419578523411019
    )
    assert reference["required_full_checkpoint_capacity_bytes"] == 32_251_808_224
    assert reference["required_effective_active_weight_bandwidth_bytes_s"] == (
        pytest.approx(453_730_640_005.72314)
    )


def test_measurement_usage_tamper_fails_closed() -> None:
    config = strict_json(CONFIG)
    lock = strict_json(MODEL_LOCK)
    measurement = copy.deepcopy(strict_json(MEASUREMENT))
    measurement["waves"][0]["requests"][0]["completion_tokens"] -= 1
    with pytest.raises(MeasuredBreakEvenError, match="completion usage differs"):
        validate_measurement(measurement, config, CONFIG, lock)


def test_runtime_version_instability_fails_closed() -> None:
    config = strict_json(CONFIG)
    lock = strict_json(MODEL_LOCK)
    measurement = copy.deepcopy(strict_json(MEASUREMENT))
    measurement["endpoint_version_stability"]["http://127.0.0.1:8000"] = False
    with pytest.raises(MeasuredBreakEvenError, match="runtime versions changed"):
        validate_measurement(measurement, config, CONFIG, lock)
