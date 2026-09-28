"""Source currency and exact-output evidence for the full-shape collective depth."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/v41_collective_depth_campaign.json"


def test_selected_depth_is_exact_and_current():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "v41_collective_depth_campaign_v1"
    assert rec["contract"]["selected_full_shape_CL_DEPTH"] == 128
    assert rec["contract"]["reduced_CL_DEPTH"] == 16
    die = (ROOT / "rtl/chip/ot_chip_v41x_die.sv").read_text()
    assert "parameter integer CL_DEPTH = FULL_SHAPE ? 128 : 16" in die
    for path, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    assert len(rec["cases"]) == 4
    for case in rec["cases"]:
        assert case["passed"] and case["mismatches"] == 0
        assert case["out_err"] == case["timeout"] == 0
        assert not any(case["faults"])
    for pattern in ("act", "y"):
        row = rec["summary"][pattern]
        assert row["selected_tail_cycles"] < row["old_tail_cycles"]
        assert row["selected_first_to_last_cycles"] >= row["output_port_minimum_cycles"]
