from __future__ import annotations

import csv
import importlib.util
import io
import json
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_iso_node_studies.py"
CHECKED_IN = ROOT / "results" / "iso-node"
ARTIFACTS = ("REPORT.md", "analytical.json", "sweep.csv")


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_iso_node_studies", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated_studies(tmp_path_factory: pytest.TempPathFactory):
    runner = _load_runner()
    first = tmp_path_factory.mktemp("iso-node-first")
    second = tmp_path_factory.mktemp("iso-node-second")
    returned = runner.run_all(first)
    runner.run_all(second)
    return runner, returned, first, second


def test_iso_node_runner_is_byte_deterministic(generated_studies) -> None:
    runner, returned, first, second = generated_studies
    assert set(returned) == set(runner.STUDIES)
    for study_id in runner.STUDIES:
        for artifact in ARTIFACTS:
            assert (first / study_id / artifact).read_bytes() == (
                second / study_id / artifact
            ).read_bytes()


def test_checked_in_iso_node_artifacts_match_the_runner(generated_studies) -> None:
    runner, _, generated, _ = generated_studies
    for study_id in runner.STUDIES:
        for artifact in ARTIFACTS:
            assert (CHECKED_IN / study_id / artifact).read_bytes() == (
                generated / study_id / artifact
            ).read_bytes()


def test_iso_node_json_csv_and_markdown_are_mutually_consistent(
    generated_studies,
) -> None:
    runner, returned, generated, _ = generated_studies
    for study_id, in_memory in returned.items():
        destination = generated / study_id
        decoded = json.loads((destination / "analytical.json").read_text())
        assert decoded == in_memory
        assert "NaN" not in (destination / "analytical.json").read_text()
        assert "Infinity" not in (destination / "analytical.json").read_text()

        csv_rows = list(
            csv.DictReader(io.StringIO((destination / "sweep.csv").read_text()))
        )
        assert len(csv_rows) == len(decoded["points"])
        assert tuple(csv_rows[0]) == runner.CSV_FIELDS
        assert (destination / "REPORT.md").read_text() == (
            runner.render_report(decoded).rstrip() + "\n"
        )


def test_achieved_rate_report_rows_match_each_exact_comparison_tuple(
    generated_studies,
) -> None:
    runner, returned, _, _ = generated_studies
    for study_id, result in returned.items():
        central = runner._central_name(study_id)
        central_rows = [
            row
            for row in result["comparisons"]
            if row["wafer_architecture"] == central
            and row["context_tokens"] == 200_000
        ]
        report = runner.render_report(result)
        section = report.split(
            "## Central-envelope achieved byte rates at 200K", 1
        )[1].split("## ROM uncertainty bands", 1)[0]
        data_rows = [line for line in section.splitlines() if line.startswith("| DeepSeek")]
        expected_rows = sum(
            1 + (row["fastest_same_batch_gpu"] is not None) for row in central_rows
        )
        assert len(data_rows) == expected_rows
        for row in central_rows:
            prefix = f"| {row['model']} | {row['batch_per_stage']} |"
            matches = [line for line in data_rows if line.startswith(prefix)]
            assert len(matches) == 1 + (row["fastest_same_batch_gpu"] is not None)


def test_infeasible_envelopes_are_not_hidden_as_numeric_lows(
    generated_studies,
) -> None:
    runner, returned, _, _ = generated_studies
    saw_partial_feasibility = False
    for result in returned.values():
        report = runner.render_report(result)
        for band in result["uncertainty_bands"]:
            feasible = band["feasible_scenario_count"]
            total = band["scenario_count"]
            if 0 < feasible < total:
                saw_partial_feasibility = True
                assert band["rom_per_user_tokens_s_low"] is None
                assert band["same_batch_speed_ratio_low"] is None
                row_prefix = (
                    f"| {band['model']} | {band['context_tokens']:,} | "
                    f"{band['batch_per_stage']} | {feasible}/{total} | infeasible–"
                )
                assert row_prefix in report
    assert saw_partial_feasibility


def test_report_exposes_audit_and_central_aggressive_component_times(
    generated_studies,
) -> None:
    runner, returned, _, _ = generated_studies
    for study_id, result in returned.items():
        report = runner.render_report(result)
        audit = result["consistency_audit"]
        assert "## Mechanical consistency audit" in report
        assert "## Unpriced auxiliary-path break-even requirements at 200K" in report
        assert f"| {audit['status'].upper()} | {audit['checks_evaluated']:,} |" in report
        section = report.split(
            "## ROM component timing and occupancy at 200K", 1
        )[1].split("## Central-envelope achieved byte rates at 200K", 1)[0]
        component_rows = [
            line
            for line in section.splitlines()
            if line.startswith("| DeepSeek")
            and ("| central |" in line or "| aggressive |" in line)
        ]
        expected = [
            point
            for point in result["points"]
            if point["context_tokens"] == 200_000
            and point["architecture"]
            in {
                runner._central_name(study_id),
                runner._aggressive_name(study_id),
            }
        ]
        # Two envelopes x four batches for every DeepSeek model in the study;
        # Qwen3-8B has no 200K point.
        deepseek_models = sum(
            1 for summary in result["model_summaries"] if "DeepSeek" in summary["model"]
        )
        assert len(component_rows) == len(expected) == 8 * deepseek_models
        for point in expected:
            assert set(point["resource_utilization"]) == {
                "weight_or_shared_hbm",
                "kv",
                "compute",
                "cooling",
            }
            assert point["thermal_scale"] >= 1.0
            assert point["auxiliary_pricing_status"] == (
                "unpriced_break_even_requirements_only_pending_COMP-01"
            )
            assert point[
                "auxiliary_required_rates_per_s_to_fit_baseline_interval"
            ]
        if study_id == "leading_node_market":
            sensitivity = result["b300_fp32_roof_sensitivity"]
            assert len(sensitivity) == deepseek_models * 4 * 4
            assert {
                row["fp32_roof_ops_s_per_gpu"] for row in sensitivity
            } == set(runner.B300_FP32_ROOF_SWEEP_OPS_S_PER_DEVICE)
            assert "## B300 full-FP32 roof sensitivity at 200K" in report
        else:
            assert result["b300_fp32_roof_sensitivity"] == []
            assert "## B300 full-FP32 roof sensitivity at 200K" not in report
