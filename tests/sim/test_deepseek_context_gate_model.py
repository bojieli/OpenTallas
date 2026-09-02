"""The sparse-KV traffic model must keep reproducing evidence it never fitted.

``tools/check_deepseek_v4_context_gate.py`` refuses a DeepSeek accelerator run
whose attention counters differ from the traffic the pinned profile implies.
That is only a gate while the model is right.  Its independent anchor is a raw
single-node prefill captured before the governed multi-token records; it must
reproduce all four counters exactly without being fitted to that capture.

This test holds that evidence in place.  If the profile, the model, or the
committed record moves, the checker stops being a checker and this fails.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
RECORD = (
    REPO / "results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32_raw.json"
)
PROFILE = REPO / "configs/models/deepseek-v4-flash-0731.json"
TOKEN_RECORD = (
    REPO / "results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json"
)
GATE_REPORT = REPO / "results/abi3/deepseek_v4_context_gate.json"


def _checker():
    spec = importlib.util.spec_from_file_location(
        "deepseek_context_gate",
        REPO / "tools" / "check_deepseek_v4_context_gate.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_model_reproduces_the_independent_raw_deepseek_prefill():
    module = _checker()
    recorded = json.loads(RECORD.read_text())["counters"]
    predicted = module.predict(
        int(json.loads(RECORD.read_text())["prompt_tokens"]), 0, PROFILE
    )
    for name, value in predicted.items():
        assert recorded[name] == value, (
            f"{name}: the profile says {value:,}, the committed run recorded "
            f"{recorded[name]:,}"
        )


def test_the_window_and_the_ranking_both_bind():
    """The model is not a dense count wearing a sparse name."""
    module = _checker()
    window, _heads, layers = module.layer_table(PROFILE)
    # A query far past the window sees the window, not its whole history.
    assert module.gathered_rows_for_query(10_000, window, 0, 0) == window
    # A ranked layer stops at top_k once the candidates exceed it.
    ratio, top_k = next((r, k) for r, k in layers if k)
    assert module.gathered_rows_for_query(
        ratio * (top_k + 1) - 1, window, ratio, top_k
    ) == window + top_k
    # An unranked compressing layer never stops.
    ratio_dense = next(r for r, k in layers if r and not k)
    assert module.gathered_rows_for_query(
        ratio_dense * 4096 - 1, window, ratio_dense, 0
    ) == window + 4096


def _cluster_record(expected: dict[str, int]) -> dict:
    return {
        "target": {"node_count": 2},
        "counter_scope": {
            "aggregate": "cluster_total",
            "per_node": "engine_work_by_node_id",
            "node_count": 2,
            "node_counters_index": "NODE_ID",
        },
        "counters": {name: value * 2 for name, value in expected.items()},
        "node_counters": [dict(expected), dict(expected)],
    }


def test_cluster_counters_are_checked_per_node_and_as_a_total():
    module = _checker()
    expected = {
        "attention.context_positions": 7,
        "attention.sparse_indices": 7,
        "attention.kv_bytes_read": 7168,
        "attention.heads": 64,
    }
    checked = module.check_counter_evidence(
        _cluster_record(expected), expected, compared=True
    )
    assert checked["problems"] == []
    assert checked["counter_comparison_scope"] == (
        "measured_per_node_and_cluster_total"
    )
    assert checked["expected_aggregate_counters"][
        "attention.context_positions"
    ] == 14
    assert checked["per_node_counter_summary"][
        "attention.context_positions"
    ]["mismatched_node_count"] == 0


def test_compensating_node_errors_cannot_hide_in_a_correct_cluster_total():
    module = _checker()
    expected = {"attention.context_positions": 7}
    record = _cluster_record(expected)
    record["node_counters"] = [
        {"attention.context_positions": 6},
        {"attention.context_positions": 8},
    ]
    checked = module.check_counter_evidence(record, expected, compared=True)
    assert checked["observed_aggregate_counters"] == {
        "attention.context_positions": 14
    }
    assert checked["per_node_counter_summary"][
        "attention.context_positions"
    ]["mismatched_node_count"] == 2
    assert any("2 of 2 nodes" in problem for problem in checked["problems"])


def test_an_aggregate_only_cluster_record_is_refused_not_divided():
    module = _checker()
    expected = {"attention.context_positions": 7}
    record = _cluster_record(expected)
    del record["node_counters"]
    checked = module.check_counter_evidence(record, expected, compared=True)
    assert checked["counter_comparison_scope"] == "invalid_or_missing"
    assert any(
        "aggregate division is not accepted" in problem
        for problem in checked["problems"]
    )


def test_source_gate_checks_every_recorded_source_not_only_the_required_subset():
    module = _checker()
    source_map = {
        relative: hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
        for relative in module.REQUIRED_FUNCTIONAL_SOURCES
    }
    extra = "runtime/sim/engines/deepseek_vector.py"
    source_map[extra] = "0" * 64

    problems = module._source_lock_problems(source_map)

    assert problems == [
        f"record source {extra} does not match the current implementation"
    ]


def test_source_gate_requires_the_non_removable_minimum_and_safe_paths():
    module = _checker()
    problems = module._source_lock_problems(
        {"../outside.py": "0" * 64}
    )
    assert "record source path escapes the repository: ../outside.py" in problems
    assert any(
        problem == "record does not bind required source runtime/abi3/verifier.py"
        for problem in problems
    )


def test_missing_explicit_pin_is_reported_and_fails_closed(tmp_path):
    missing_pin = tmp_path / "missing-pin.json"
    output = tmp_path / "gate.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/check_deepseek_v4_context_gate.py"),
            str(TOKEN_RECORD),
            "--pin",
            str(missing_pin),
            "--output",
            str(output),
        ],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    report = json.loads(output.read_text())
    assert report["pins_missing"] == [str(missing_pin)]
    assert report["claim_boundary"]["all_required_pins_present"] is False
    assert report["all_pass"] is False


def test_malformed_counter_values_fail_closed_instead_of_raising():
    module = _checker()
    expected = {"attention.context_positions": 7}
    record = _cluster_record(expected)
    record["counters"]["attention.context_positions"] = "14"
    record["node_counters"][1]["attention.context_positions"] = None
    checked = module.check_counter_evidence(record, expected, compared=True)
    assert checked["observed_aggregate_counters"] == {
        "attention.context_positions": -1
    }
    summary = checked["per_node_counter_summary"][
        "attention.context_positions"
    ]
    assert summary["nodes_with_valid_counter"] == 1
    assert summary["mismatched_node_count"] == 1
    assert any("non-negative integer" in problem for problem in checked["problems"])
    assert any("missing or invalid" in problem for problem in checked["problems"])


def test_malformed_counter_scope_objects_fail_closed_instead_of_raising():
    module = _checker()
    checked = module.check_counter_evidence(
        {
            "target": ["not", "an", "object"],
            "counter_scope": "cluster_total",
            "counters": {"attention.context_positions": 14},
        },
        {"attention.context_positions": 7},
        compared=True,
    )
    assert checked["node_count"] is None
    assert checked["expected_aggregate_counters"] == {
        "attention.context_positions": None
    }
    assert checked["aggregate_excess_over_model"] == {
        "attention.context_positions": None
    }
    assert "target is not an object" in checked["problems"]
    assert "counter_scope is not an object" in checked["problems"]
    assert any("node_count" in problem for problem in checked["problems"])


def test_make_target_checks_the_governed_hbm_record():
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    recipe = makefile.split("abi3-context-gate:", 1)[1].split("\n\n", 1)[0]
    assert "tools/check_deepseek_v4_context_gate.py" in recipe
    assert "deepseek_v4_flash_hbm_p32.json" in recipe
    assert "--output results/abi3/deepseek_v4_context_gate.json" in recipe


def test_governed_hbm_record_retains_every_measured_node_counter_set():
    module = _checker()
    record = json.loads(TOKEN_RECORD.read_text(encoding="utf-8"))
    expected = module.predict(
        record["workload"]["prompt_token_count"],
        record["generated_token_count"] - 1,
        PROFILE,
    )
    assert record["status"] == "pass"
    assert record["target"]["node_count"] == 32
    assert record["counter_scope"] == {
        "aggregate": "cluster_total",
        "node_count": 32,
        "node_counters_index": "NODE_ID",
        "per_node": "engine_work_by_node_id",
        "reconciliation": (
            "cluster total equals the sum of per-node engine work plus "
            "cluster-only LINK, STATE, control, and host bookkeeping"
        ),
    }
    assert len(record["node_counters"]) == 32
    for node, counters in enumerate(record["node_counters"]):
        assert {name: counters[name] for name in expected} == expected, node
    assert {name: record["counters"][name] for name in expected} == {
        name: value * 32 for name, value in expected.items()
    }


def test_governed_v2_report_binds_sources_and_stays_below_the_thresholds():
    report = json.loads(GATE_REPORT.read_text(encoding="utf-8"))
    assert report["schema"] == "opentallas.deepseek_v4_context_gate.v2"
    assert report["all_pass"] is True
    assert report["records_checked"] == 1
    assert report["records_missing"] == []

    result = report["results"][0]
    assert result["passes"] is True
    assert result["problems"] == []
    assert result["node_count"] == 32
    assert result["counter_comparison_scope"] == (
        "measured_per_node_and_cluster_total"
    )
    assert result["expected_counters_per_node"] == {
        "attention.context_positions": 30_114,
        "attention.heads": 96_320,
        "attention.kv_bytes_read": 30_836_736,
        "attention.sparse_indices": 30_114,
    }
    assert result["observed_aggregate_counters"] == {
        name: value * 32
        for name, value in result["expected_counters_per_node"].items()
    }
    assert result["expected_aggregate_counters"] == result[
        "observed_aggregate_counters"
    ]
    assert set(result["aggregate_excess_over_model"].values()) == {0}
    for name, expected in result["expected_counters_per_node"].items():
        summary = result["per_node_counter_summary"][name]
        assert summary["expected_each_node"] == expected
        assert summary["minimum_observed"] == expected
        assert summary["maximum_observed"] == expected
        assert summary["nodes_observed"] == 32
        assert summary["nodes_with_valid_counter"] == 32
        assert summary["mismatched_node_count"] == 0

    boundary = report["claim_boundary"]
    assert boundary["maximum_accelerator_context_tokens_checked"] == 35
    assert boundary["first_window_clipping_context_tokens"] == 129
    assert boundary["first_index_pruning_context_tokens"] == 2_052
    assert boundary["accelerator_window_clipping_executed"] is False
    assert boundary["accelerator_index_pruning_executed"] is False
    assert boundary["all_declared_sparsity_thresholds_executed"] is False
    assert boundary["functional_simulator_only"] is True
    assert boundary["rtl"] is False
    assert boundary["cycles_or_performance"] is False

    required_sources = {
        "tools/run_accelerator_tokens.py",
        "runtime/sim/device.py",
        "runtime/sim/engine.py",
        "runtime/sim/memory.py",
        "runtime/sim/counters.py",
        "runtime/sim/engines/route.py",
        "runtime/sim/engines/attention.py",
    }
    assert required_sources <= set(report["source_sha256"])

    record_path = REPO / result["record"]
    assert result["record_sha256"] == hashlib.sha256(
        record_path.read_bytes()
    ).hexdigest()
    for relative, expected in report["source_sha256"].items():
        assert hashlib.sha256((REPO / relative).read_bytes()).hexdigest() == expected
