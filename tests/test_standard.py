"""End-to-end guards for the committed standard analytical artifact."""

from __future__ import annotations

import json

from run import run_standard


def test_standard_report_is_complete_and_byte_reproducible(tmp_path) -> None:
    first = run_standard(tmp_path)
    first_json = (tmp_path / "analytical.json").read_bytes()
    first_csv = (tmp_path / "sweep.csv").read_bytes()
    first_report = (tmp_path / "REPORT.md").read_bytes()

    second = run_standard(tmp_path)

    assert second == first
    assert (tmp_path / "analytical.json").read_bytes() == first_json
    assert (tmp_path / "sweep.csv").read_bytes() == first_csv
    assert (tmp_path / "REPORT.md").read_bytes() == first_report

    decoded = json.loads(first_json)
    assert decoded["schema_version"] == 2
    assert "generated_at" not in decoded
    assert decoded["inputs"]["required_batches"] == [1, 8, 32, 64, 128]
    assert len(decoded["model_summaries"]) == 3
    assert all(
        summary["dense_active_parameters"] >= 0
        and summary["routed_active_parameters"] >= 0
        and summary["dense_active_parameters"]
        + summary["routed_active_parameters"]
        == summary["active_parameters"]
        for summary in decoded["model_summaries"]
    )
    report = first_report.decode()
    assert "## Assumed speculative-decoding midpoint" in report
    assert "DeepSeek-V4-Flash-0731" in report
    assert "DeepSeek-V4-Pro-0813" in report
    assert "Kimi-K3" in report
