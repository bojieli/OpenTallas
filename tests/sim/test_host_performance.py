"""Host-performance evidence stays separate, bounded, and reproducible."""

from __future__ import annotations

import hashlib
import json

from runtime.sim.performance import HostPerformanceObservations, sample_process


def test_device_epoch_recorder_keeps_zero_configuration_and_ordered_runs() -> None:
    recorder = HostPerformanceObservations()
    recorder.add("routed_operator_issues", 2)
    recorder.add("decoded_weight_materializations", 3)
    recorder.add_duration_ns("decoded_weight_materialization", 1_500_000_000)
    for shape in ((3, 7), (3, 7), (1, 7)):
        recorder.record_association(
            contract="bf16_bf16_fp32_blocked_rne_v1",
            activation_shape=shape,
            weight_shape=(5, 7),
            output_shape=(shape[0], 5),
        )

    snapshot = recorder.snapshot()
    assert snapshot["architectural_counter_registry_unchanged"] is True
    assert snapshot["totals"]["decoded_weight_cache_budget_bytes"] == 0
    assert snapshot["totals"]["decoded_weight_cache_hits"] == 0
    assert snapshot["durations"]["decoded_weight_materialization_seconds"] == 1.5
    ordered = snapshot["ordered_executed_associations"]
    assert ordered["blocked_call_count"] == 3
    assert ordered["run_count"] == 2
    assert [run["call_count"] for run in ordered["runs"]] == [2, 1]
    unsigned = dict(ordered)
    digest = unsigned.pop("manifest_sha256")
    encoded = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    assert digest == hashlib.sha256(encoded).hexdigest()


def test_transaction_delta_does_not_enter_architectural_counters() -> None:
    recorder = HostPerformanceObservations()
    before = recorder.checkpoint()
    process_before = sample_process()
    recorder.add("route_organization_passes", 4)
    recorder.add("route_unique_scans", 24)
    recorder.add_duration_ns("route_organization", 1234)
    recorder.record_association(
        contract="bf16_bf16_fp32_blocked_rne_v1",
        activation_shape=(1, 8),
        weight_shape=(2, 8),
        output_shape=(1, 2),
    )
    delta = recorder.transaction_delta(before, process_before, sample_process())
    assert delta["totals"]["route_organization_passes"] == 4
    assert delta["totals"]["route_unique_scans"] == 24
    assert delta["durations"]["route_organization_seconds"] == 0.000001234
    assert delta["blocked_association_calls"] == 1
    assert delta["process"]["minor_page_faults"] >= 0
    assert delta["process"]["major_page_faults"] >= 0
