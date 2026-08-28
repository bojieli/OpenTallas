"""End-to-end guards for the committed standard analytical artifact."""

from __future__ import annotations

import json

from run import run_standard


def test_standard_report_is_complete_and_byte_reproducible(tmp_path) -> None:
    first = run_standard(tmp_path)
    first_json = (tmp_path / "analytical.json").read_bytes()
    first_csv = (tmp_path / "sweep.csv").read_bytes()
    first_report = (tmp_path / "REPORT.md").read_bytes()
    first_qwen = (tmp_path / "QWEN3_8B_ADDENDUM.md").read_bytes()

    second = run_standard(tmp_path)

    assert second == first
    assert (tmp_path / "analytical.json").read_bytes() == first_json
    assert (tmp_path / "sweep.csv").read_bytes() == first_csv
    assert (tmp_path / "REPORT.md").read_bytes() == first_report
    assert (tmp_path / "QWEN3_8B_ADDENDUM.md").read_bytes() == first_qwen

    decoded = json.loads(first_json)
    assert decoded["schema_version"] == 4
    assert "generated_at" not in decoded
    assert decoded["inputs"]["required_batches"] == [1, 8, 32, 64, 128]
    assert len(decoded["model_summaries"]) == 4
    assert decoded["inputs"]["contexts_by_model"]["Qwen3-8B"] == [8192]
    assert decoded["inputs"]["scenarios_by_model"]["Qwen3-8B"] == [
        "no_speculation"
    ]
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
    assert "## Numeric format contract" in report
    assert "mxfp4_e2m1_x_fp8_e4m3" in report
    assert "DeepSeek-V4-Flash-0731" in report
    assert "DeepSeek-V4-Pro-0813" in report
    assert "Kimi-K3" in report
    assert "Qwen3-8B" in report
    qwen_rows = [
        row for row in decoded["comparisons"] if row["model"] == "Qwen3-8B"
    ]
    assert {row["batch_size"] for row in qwen_rows} == {1, 8, 32, 64, 128}
    assert {row["scenario"] for row in qwen_rows} == {"no_speculation"}
    qwen_addendum = first_qwen.decode()
    assert "Qwen3-8B / 8K analytical addendum" in qwen_addendum
    assert "no attached draft module" in qwen_addendum
    assert "| 64 |" in qwen_addendum
