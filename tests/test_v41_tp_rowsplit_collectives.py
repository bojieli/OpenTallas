"""Keep V4.1 row-split stage timing bound to the exercised RTL sources."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _check_pins(record):
    for path, digest in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def test_base_engine_width_matched_gather_record():
    rec = json.loads((ROOT / "results/rtl/v41_tp_rowsplit_collectives.json").read_text())
    assert rec["schema"] == "v41_tp_rowsplit_collectives_v1"
    _check_pins(rec)
    assert rec["patterns"]["act"]["words"] == 266
    assert rec["patterns"]["y"]["words"] == 80
    assert len(rec["cases"]) == 9
    assert all(case["passed"] and case["mismatches"] == 0 and not any(case["faults"])
               for case in rec["cases"])
    assert rec["summary"]["act"]["measured_tail_cycles"] > rec["patterns"]["act"]["model_exposed"]
    assert rec["summary"]["y"]["measured_tail_cycles"] > rec["patterns"]["y"]["model_exposed"]
    wide_queue = next(case for case in rec["cases"] if case["case"] == "rowsplit_act_d64_q512")
    assert wide_queue["producer_stall_cycles"] == 0
