"""The packed stage record must remain tied to the tested RTL and real bits."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/v41_w2_packed_collective.json"


def test_real_payload_and_rtl_are_current():
    r = json.loads(REC.read_text())
    for path, digest in r["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    assert "PASS" in r["standalone"]["pack4"]
    assert "PASS" in r["standalone"]["y_pack2"]
    assert "PASS" in r["standalone"]["direct_scratchpad"]
    assert all(x["passed"] and x["mismatches"] == 0 for x in r["stage"]["cases"])


def test_packed_write_floor_and_timing_are_accounted_once():
    r = json.loads(REC.read_text())
    assert r["contract"]["act_link_bytes_per_rank"] == 77 * 64
    assert r["contract"]["act_payload_bytes_per_rank"] == 7 * (576 + 18)
    s = r["stage"]["summary"]
    assert s["act"]["baseline_output_writes"] == 4 * 266
    assert s["act"]["packed_output_writes"] == 4 * 77
    assert s["y"]["baseline_output_writes"] == 4 * 80
    assert s["y"]["packed_output_writes"] == 4 * 40
    for pattern in ("act", "y"):
        row = s[pattern]
        assert row["packed_comparable_tail_cycles"] == row["packed_engine_tail_cycles"] + row["source_pack_input_words"]
        assert row["exposed_tail_delta_cycles"] == row["packed_comparable_tail_cycles"] - row["baseline_tail_cycles"]
