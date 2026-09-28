"""Source-pinned exact evidence for the adopted-width four-bank prototype."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _current(record):
    for path, digest in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def test_stage_engine_tail_is_exact_and_current():
    record = json.loads((ROOT / "results/rtl/v41_collective_gw4_campaign.json").read_text())
    assert record["schema"] == "v41_collective_gw4_campaign_v1"
    assert record["contract"]["GW"] == 4
    assert record["contract"]["CL_DEPTH"] == 256
    assert record["contract"]["PAIRWISE"] == 1
    _current(record)
    assert len(record["cases"]) == 2
    for case in record["cases"]:
        assert case["passed"] and case["mismatches"] == 0
        assert case["out_err"] == case["timeout"] == 0
        assert not any(case["faults"])
    for pattern, expected in (("act", (266, 463)), ("y", (80, 236))):
        row = record["summary"][pattern]
        assert (row["words_per_die"], row["gw4_depth256_tail_cycles"]) == expected
        assert row["gw4_depth256_tail_cycles"] < row["gw1_depth128_tail_cycles"]


def test_dma_transpose_boundary_is_exact_and_current():
    record = json.loads((ROOT / "results/rtl/v41x_coll_gw4_gate.json").read_text())
    assert record["schema"] == "v41x_coll_gw4_gate_v1"
    assert record["contract"]["VM_write_words_per_cycle"] == 4
    assert record["contract"]["bank_commit_pipeline_cycles"] == 2
    _current(record)
    assert len(record["cases"]) == 8
    for case in record["cases"]:
        assert case["passed"]
        assert case["metrics"]["writes"] == 4 * case["words"]
    stress = [c for c in record["cases"] if c["words"] == 266]
    assert len(stress) == 3
    assert all(c["metrics"].get("held", c["metrics"].get("holds", c["metrics"].get("out_hold", 0))) > 0
               for c in stress)


def test_adopted_link_engine_and_banked_drain_are_exact_and_current():
    record = json.loads((ROOT / "results/rtl/v41_collective_gw4_banked.json").read_text())
    assert record["schema"] == "v41_collective_gw4_banked_v1"
    assert record["contract"]["GW"] == 4
    assert record["contract"]["OUT_BP"] == 1
    assert record["contract"]["CL_DEPTH"] == 256
    _current(record)
    assert len(record["cases"]) == 2
    for case in record["cases"]:
        assert case["passed"] and case["mismatches"] == 0
        assert case["out_err"] == case["timeout"] == 0
        assert not any(case["faults"])
    assert record["summary"]["act"]["banked_tail_cycles"] == 469
    assert record["summary"]["y"]["banked_tail_cycles"] == 240
