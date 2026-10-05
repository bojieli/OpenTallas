from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path

import pytest

from opentallas.world_model import linear_row_storage_roofline


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_world_model_landscape_study.py"
CHECKED_IN = ROOT / "results" / "world-model-landscape"


def _runner_module():
    spec = importlib.util.spec_from_file_location(
        "run_world_model_landscape_study", RUNNER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated():
    return _runner_module().build()


def test_checked_in_outputs_are_byte_deterministic(generated) -> None:
    result, report, sweep = generated
    expected_json = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    assert (CHECKED_IN / "analytical.json").read_text() == expected_json
    assert (CHECKED_IN / "REPORT.md").read_text() == report
    assert (CHECKED_IN / "row_sweep.csv").read_text() == sweep


def test_csv_covers_both_configured_formats(generated) -> None:
    result, _, sweep = generated
    rows = list(csv.DictReader(io.StringIO(sweep)))
    assert len(rows) == 2 * len(result["row_sweep"])
    assert {row["format_label"] for row in rows} == {"BF16", "FP8"}
    assert {row["compute_format"] for row in rows} == {
        "bf16_x_bf16",
        "fp8_e4m3_x_fp8_e4m3",
    }
    expected_rows = [item["rows_per_call"] for item in result["row_sweep"]]
    for label in ("BF16", "FP8"):
        assert [
            int(row["rows_per_call"]) for row in rows if row["format_label"] == label
        ] == expected_rows


def test_parameter_count_and_call_count_cancel() -> None:
    common = {
        "rows_per_call": 144,
        "weight_bytes_per_parameter": 2.0,
        "compute_ops_s": 8.3835e15,
        "hbm_weight_bytes_s": 22.4595e12,
        "rom_weight_bytes_s": 2.149484688e15,
    }
    small = linear_row_storage_roofline(active_matrix_parameters=1e9, calls=1, **common)
    large = linear_row_storage_roofline(
        active_matrix_parameters=33e9, calls=49, **common
    )
    for key in (
        "arithmetic_intensity_ops_per_weight_byte",
        "roofline_storage_attribution",
        "additive_storage_attribution",
        "zero_cost_rom_additive_upper_bound",
    ):
        assert large[key] == pytest.approx(small[key])


def test_central_ridge_and_known_row_screens(generated) -> None:
    result, _, _ = generated
    bf16 = next(item for item in result["hardware_formats"] if item["label"] == "BF16")
    fp8 = next(item for item in result["hardware_formats"] if item["label"] == "FP8")
    assert bf16["same_compute_hbm_ridge_rows"] == pytest.approx(373.2718894009217)
    assert bf16["same_compute_hbm_ridge_rows"] == pytest.approx(
        fp8["same_compute_hbm_ridge_rows"]
    )
    assert bf16["gpu_hbm_ridge_rows"] == pytest.approx(174.19354838709677)
    assert bf16["rom_ridge_rows"] == pytest.approx(3.9002371344177726)
    assert bf16["rom_phase_compute_ops_s"] == pytest.approx(8.3835e15)
    assert fp8["rom_phase_compute_ops_s"] == pytest.approx(1.6767e16)
    assert bf16["same_compute_hbm_weight_bytes_s"] == pytest.approx(2.24595e13)
    assert bf16["rom_weight_bytes_s"] == pytest.approx(2.149484688e15)
    assert bf16["gpu_phase_compute_ops_s"] == pytest.approx(9.234e14)
    assert fp8["gpu_phase_compute_ops_s"] == pytest.approx(1.8468e15)
    assert bf16["gpu_hbm_weight_bytes_s"] == pytest.approx(5.301e12)

    screens = {item["model"]: item for item in result["model_screens"]}
    assert screens["Oasis causal-cache candidate"][
        "roofline_storage_attribution"
    ] == pytest.approx(2.592165898617511)
    assert (
        screens["LingBot-World-Infinity 14B causal-fast"][
            "roofline_storage_attribution"
        ]
        == 1.0
    )
    assert screens["LingBot-World-Infinity 14B causal-fast"][
        "zero_cost_rom_additive_upper_bound"
    ] == pytest.approx(1.0797589507266927)
    assert (
        screens["MiniMax-H3 dense 5.17-second control"][
            "zero_cost_rom_additive_upper_bound"
        ]
        < 1.01
    )


def test_format_invariance_and_absolute_time_scaling(generated) -> None:
    result, _, _ = generated
    bf16 = {row["rows_per_call"]: row for row in result["row_sweep"]}
    fp8 = {row["rows_per_call"]: row for row in result["fp8_row_sweep"]}
    assert bf16.keys() == fp8.keys()
    ratio_fields = (
        "roofline_storage_attribution",
        "additive_storage_attribution",
        "zero_cost_rom_additive_upper_bound",
        "actual_architecture_ratio_not_storage_attribution",
    )
    time_fields = (
        "compute_service_s",
        "hbm_weight_service_s",
        "rom_weight_service_s",
        "hbm_roofline_s",
        "rom_roofline_s",
    )
    for rows in bf16:
        for field in ratio_fields:
            assert fp8[rows][field] == pytest.approx(bf16[rows][field])
        for field in time_fields:
            assert fp8[rows][field] == pytest.approx(bf16[rows][field] / 2.0)
        assert fp8[rows]["arithmetic_intensity_ops_per_weight_byte"] == pytest.approx(
            2.0 * bf16[rows]["arithmetic_intensity_ops_per_weight_byte"]
        )


def test_governed_crossover_neighbors_and_thresholds(generated) -> None:
    result, report, _ = generated
    rows = {row["rows_per_call"]: row for row in result["row_sweep"]}
    assert rows[3]["rom_binding_term"] == "immutable_weight"
    assert rows[4]["rom_binding_term"] == "compute"
    assert rows[186]["roofline_storage_attribution"] >= 2.0
    assert rows[187]["roofline_storage_attribution"] < 2.0
    assert rows[339]["roofline_storage_attribution"] >= 1.1
    assert rows[340]["roofline_storage_attribution"] < 1.1
    assert rows[373]["hbm_binding_term"] == "immutable_weight"
    assert rows[373]["roofline_storage_attribution"] > 1.0
    assert rows[374]["hbm_binding_term"] == "compute"
    assert rows[374]["roofline_storage_attribution"] == 1.0
    assert (
        result["thresholds"]["1.1"]["largest_integer_row_meeting_roofline_target"]
        == 339
    )
    assert (
        result["thresholds"]["2.0"]["largest_integer_row_meeting_roofline_target"]
        == 186
    )
    assert (
        result["atlas_conditions"]["largest_integer_row_with_any_roofline_benefit"]
        == 373
    )
    assert "Largest qualifying integer row" in report


def test_actual_architecture_comparison_is_separate(generated) -> None:
    result, report, _ = generated
    rows = {row["rows_per_call"]: row for row in result["row_sweep"]}
    expected = {
        1: 405.4866417657045,
        4: 395.3735144312393,
        174: 9.089046308764123,
        187: 9.078947368421053,
    }
    for row, ratio in expected.items():
        assert rows[row][
            "actual_architecture_ratio_not_storage_attribution"
        ] == pytest.approx(ratio)
    assert (
        result["comparison_contract"][
            "actual_architecture_ratio_is_storage_attribution"
        ]
        is False
    )
    assert "actual ratio (not attribution)" in report


def test_recent_model_inventory_keeps_unknowns_unknown(generated) -> None:
    result, report, _ = generated
    models = {item["model"]: item for item in result["inventory_models"]}
    assert models["World Labs Atlas"]["current_rows_per_call"] is None
    assert models["World Labs RTFM"]["current_rows_per_call"] is None
    assert (
        models["LingBot-World-Infinity 14B causal-fast"]["current_rows_per_call"]
        == 4680
    )
    assert (
        models["HY-World 1.5 WorldPlay 8B distilled"]["current_rows_per_call"] == 1560
    )
    assert models["Alaya-EVOKE"]["current_rows_per_call"] == 8640
    assert "any Atlas number today would be fabricated" in " ".join(report.split())
    assert "correct KV cache does not imply a weight-bound decoder" in report

    surveyed = [
        model for model in models.values() if model["record_role"] == "surveyed_release"
    ]
    controls = [
        model for model in models.values() if model["record_role"] == "existing_control"
    ]
    assert len(surveyed) == 8
    assert len(controls) == 2
    assert sum(model["current_rows_per_call"] is not None for model in surveyed) == 5
    assert models["Alaya-EVOKE"]["row_evidence"]["grade"] == "assumed"
    assert (
        models["MiniMax-H3 dense 5.17-second control"]["row_evidence"]["grade"]
        == "assumed"
    )


def test_retained_current_row_factors_close_exactly(generated) -> None:
    result, _, _ = generated
    for model in result["inventory_models"]:
        factors = model.get("current_rows_factors")
        if factors is None:
            continue
        expected = 1
        for factor in factors:
            expected *= factor
        expected += sum(model.get("current_rows_addends", []))
        assert model["current_rows_per_call"] == expected


def test_every_load_bearing_source_is_locked(generated) -> None:
    result, _, _ = generated
    assert set(result["producer"]) == {
        "runner",
        "analytical_module",
        "schema_module",
    }
    identities = [
        *result["producer"].values(),
        *result["input_identity"].values(),
    ]
    for identity in identities:
        path = ROOT / identity["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == identity["sha256"]


def test_pinned_input_hash_mismatch_fails_closed() -> None:
    runner = _runner_module()
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        runner._load_pinned_json(
            {
                "path": "data/world-model/recent-world-models-2026-09.json",
                "sha256": "0" * 64,
            },
            label="test inventory",
        )


def test_unpinned_and_escaping_inputs_fail_closed() -> None:
    runner = _runner_module()
    with pytest.raises(RuntimeError, match="pinned path/SHA-256"):
        runner._load_pinned_json(
            "data/world-model/recent-world-models-2026-09.json",
            label="test inventory",
        )
    with pytest.raises(RuntimeError, match="inside the repository"):
        runner._load_pinned_json(
            {"path": "../outside.json", "sha256": "0" * 64},
            label="test inventory",
        )


def test_config_mutations_fail_closed() -> None:
    runner = _runner_module()
    config, _ = runner._load_config()

    mutations = []
    bad = copy.deepcopy(config)
    bad["threshold_metric"] = "additive_storage_attribution"
    mutations.append(bad)
    bad = copy.deepcopy(config)
    bad["row_sweep"].append(bad["row_sweep"][-1])
    mutations.append(bad)
    bad = copy.deepcopy(config)
    bad["numeric_format_sweeps"][1]["compute_format"] = "unknown"
    mutations.append(bad)
    bad = copy.deepcopy(config)
    bad["calls_normalizer"] = True
    mutations.append(bad)
    bad = copy.deepcopy(config)
    bad["inventory"] = bad["inventory"]["path"]
    mutations.append(bad)

    for mutation in mutations:
        with pytest.raises(RuntimeError):
            runner._validate_config(mutation)


def test_inventory_evidence_mutations_fail_closed() -> None:
    runner = _runner_module()
    config, _ = runner._load_config()
    _, inventory, _ = runner._load_pinned_json(config["inventory"], label="inventory")
    validation = {
        "expected_date": config["as_of_date"],
        "expected_rows": set(config["row_sweep"]),
    }

    missing_row_evidence = copy.deepcopy(inventory)
    quantified = next(
        model
        for model in missing_row_evidence["models"]
        if model["current_rows_per_call"] is not None
    )
    del quantified["row_evidence"]
    with pytest.raises(RuntimeError, match="graded evidence"):
        runner._validate_inventory(missing_row_evidence, **validation)

    corrupt_local_pin = copy.deepcopy(inventory)
    control = next(
        model
        for model in corrupt_local_pin["models"]
        if model["record_role"] == "existing_control"
    )
    local_source = next(
        source for source in control["sources"] if source["grade"] == "derived"
    )
    local_source["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="local source SHA-256 mismatch"):
        runner._validate_inventory(corrupt_local_pin, **validation)


def test_architecture_kind_mismatch_fails_closed() -> None:
    runner = _runner_module()
    config, _ = runner._load_config()
    _, hardware, _ = runner._load_pinned_json(
        config["hardware_config"], label="hardware config"
    )
    with pytest.raises(RuntimeError, match="expected 'rom'"):
        runner._find_architecture(
            hardware,
            config["comparison_architectures"]["gpu"],
            expected_kind="rom",
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"rows_per_call": 0},
        {"rows_per_call": -1},
        {"rows_per_call": False},
        {"rows_per_call": 1.5},
        {"rows_per_call": 10**400},
        {"active_matrix_parameters": 0},
        {"active_matrix_parameters": -1},
        {"active_matrix_parameters": math.nan},
        {"active_matrix_parameters": math.inf},
        {"active_matrix_parameters": True},
        {"active_matrix_parameters": "1"},
        {"calls": 0},
        {"calls": -1},
        {"calls": False},
        {"calls": 1.5},
        {"weight_bytes_per_parameter": 0},
        {"weight_bytes_per_parameter": math.nan},
        {"weight_bytes_per_parameter": math.inf},
        {"compute_ops_s": 0},
        {"compute_ops_s": math.nan},
        {"compute_ops_s": math.inf},
        {"hbm_weight_bytes_s": 0},
        {"hbm_weight_bytes_s": math.nan},
        {"hbm_weight_bytes_s": math.inf},
        {"rom_weight_bytes_s": 0},
        {"rom_weight_bytes_s": math.nan},
        {"rom_weight_bytes_s": math.inf},
        {
            "active_matrix_parameters": 8e307,
            "weight_bytes_per_parameter": 1.0,
            "compute_ops_s": 1.0,
            "hbm_weight_bytes_s": 1.0,
            "rom_weight_bytes_s": 10.0,
        },
        {
            "active_matrix_parameters": 5e-324,
            "compute_ops_s": 1e308,
        },
    ],
)
def test_linear_row_screen_rejects_invalid_or_unrepresentable_inputs(overrides) -> None:
    inputs = {
        "rows_per_call": 1,
        "active_matrix_parameters": 1.0,
        "calls": 1,
        "weight_bytes_per_parameter": 2.0,
        "compute_ops_s": 1.0,
        "hbm_weight_bytes_s": 1.0,
        "rom_weight_bytes_s": 1.0,
    }
    inputs.update(overrides)
    with pytest.raises(ValueError):
        linear_row_storage_roofline(**inputs)
