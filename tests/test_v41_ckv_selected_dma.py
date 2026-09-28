"""Regression for the HBM-selected compressed-KV row evidence."""
import json
from pathlib import Path

from tools.rtl_v41_ckv_selected_campaign import ROOT, run


def test_exact_selected_row_gate_and_source_pins():
    record = run()
    saved = json.loads((ROOT / "results/rtl/v41x_ckv_selected_dma.json").read_text())
    assert record == saved
    assert record["elements_exact_fp8_and_fp32"] == 1024
    assert record["unpublished_source_rejected"]
    assert record["window_local_row_rejected"]
    assert record["nonfinite_scale_rejected"]
