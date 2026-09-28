"""Checks the scale boundary of Qwen O4's two-die INT8 column split."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hdc_golden as G
import qwen3_deployment_quality as Q
import qwen_o4_tp2_numeric as N


def test_fold_before_row_scale_is_the_reference_order():
    # Signed INT8 codes, BF16-exact inputs and BF16 scale.  This fixture has a
    # one-ULP difference when the two dies scale their partial sums locally.
    codes = np.array([[89, 53, -103, 61, -32, 121, 70, -60,
                       -77, -62, 21, -20, -13, -53, 95, 38]], dtype=np.float32)
    x = np.array([89, -51, 28.125, -28, 39.5, -82.5, -6, 17.75,
                  25.25, 38.5, 78.5, -51.75, -69.5, -21.875, 13.75, 92],
                 dtype=np.float32)
    scale = np.array([0.09521484375], dtype=np.float32)
    correct, local = N.scaled_tp2(codes, x, scale, split=1)
    expected = G.mul(G.matvec(codes, x, split=1), scale)
    np.testing.assert_array_equal(G.bits(correct), G.bits(expected))
    assert int(G.bits(correct)[0]) == 3290711288
    assert int(G.bits(local)[0]) == 3290711287


def test_real_row_record_is_source_pinned_and_exposes_wrong_fold_order():
    record = json.loads((ROOT / "results/quality/qwen_o4_tp2_numeric.json").read_text())
    for path, digest in record["source_sha256"].items():
        assert N.source_sha(ROOT / path) == digest
    assert record["snapshot_revision"] == "b968826d9c46dd6066d109eabc6255188de91218"
    assert record["splits"] == {"q_quality": 512, "q_tp2": 256,
                                 "o_quality": 256, "o_tp2_per_die": 2048}
    assert [p["o_fold_then_scale_vs_scale_then_fold_mismatches"]
            for p in record["probes"]] == [49, 39, 50, 54, 34, 43, 43]
    assert all(p["q_global_vs_tp2_mismatches"] == 0 for p in record["probes"])
    assert all(p["o_global_vs_tp2_fold_then_scale_mismatches"] == 0
               for p in record["probes"])


def test_real_row_record_rederives_when_checkpoint_is_present():
    try:
        snapshot = Q.find_snapshot()
    except FileNotFoundError:
        pytest.skip("Qwen3-8B snapshot is not present")
    got = N.evaluate(snapshot)
    pinned = json.loads((ROOT / "results/quality/qwen_o4_tp2_numeric.json").read_text())
    assert got == pinned
