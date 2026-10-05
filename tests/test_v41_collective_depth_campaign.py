"""Exact GW1 reference before the GW4 collective prototype."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/v41_collective_depth_campaign.json"


def test_gw1_reference_is_exact_and_source_pinned():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "v41_collective_depth_campaign_v1"
    assert rec["contract"]["selected_full_shape_CL_DEPTH"] == 128
    assert rec["contract"]["reduced_CL_DEPTH"] == 16
    # This is a historical same-program GW1 reference. The current engine
    # adds output backpressure and the current die selects GW4/depth256.
    assert len(rec["source_sha256"]) >= 8
    assert all(len(digest) == 64 for digest in rec["source_sha256"].values())
    assert len(rec["cases"]) == 4
    for case in rec["cases"]:
        assert case["passed"] and case["mismatches"] == 0
        assert case["out_err"] == case["timeout"] == 0
        assert not any(case["faults"])
    for pattern in ("act", "y"):
        row = rec["summary"][pattern]
        assert row["selected_tail_cycles"] < row["old_tail_cycles"]
        assert row["selected_first_to_last_cycles"] >= row["output_port_minimum_cycles"]
