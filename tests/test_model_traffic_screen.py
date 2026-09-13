from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/run_model_traffic_screen.py"
CHECKED_IN = ROOT / "results/model-traffic"
ARTIFACTS = ("REPORT.md", "analytical.json", "sweep.csv")


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_model_traffic_screen", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory):
    runner = _load_runner()
    first = tmp_path_factory.mktemp("traffic-first")
    second = tmp_path_factory.mktemp("traffic-second")
    result = runner.run(first)
    runner.run(second)
    return runner, result, first, second


def test_traffic_screen_is_deterministic_and_checked_in(generated) -> None:
    _, _, first, second = generated
    for artifact in ARTIFACTS:
        assert (first / artifact).read_bytes() == (second / artifact).read_bytes()
        assert (first / artifact).read_bytes() == (CHECKED_IN / artifact).read_bytes()


def test_traffic_screen_matrix_and_identities(generated) -> None:
    runner, result, _, _ = generated
    assert len(result["rows"]) == 4 * 4 * 4
    assert {row["model"] for row in result["rows"]} == {
        "DeepSeek-V4-Flash-0731",
        "DeepSeek-V4-Pro-0813",
        "Kimi-K3",
        "DeepSeek-V4.1-Flash",
    }
    for row in result["rows"]:
        assert row["weight_to_kv_read_ratio"] == pytest.approx(
            row["active_weight_read_bytes_per_step"]
            / row["kv_read_bytes_per_step"]
        )
        assert row["weight_to_kv_read_write_ratio"] == pytest.approx(
            row["active_weight_read_bytes_per_step"]
            / row["kv_total_bytes_per_step"]
        )
    decoded = json.loads((CHECKED_IN / "analytical.json").read_text())
    assert decoded == result
    report = runner.render_report(result)
    assert "## Weight / KV-read ratio" in report
    assert "## Weight / (KV-read + write) ratio" in report
