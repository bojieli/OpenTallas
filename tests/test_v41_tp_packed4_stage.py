"""Exact packet-length gate for the proposed packed4 collective container."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_packed4_stage_record_is_exact_and_source_pinned():
    rec = json.loads((ROOT / "results/rtl/v41_tp_packed4_stage.json").read_text())
    assert rec["schema"] == "v41_tp_packed4_stage_v1"
    for path, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    assert rec["contract"] == dict(flits_B=64, CL_LANES=16, CL_DEPTH=128, QTX=2,
                                   PUSHW=1, PAIRWISE=1, GW=1, blocked_COLL_v1=True)
    assert len(rec["cases"]) == 16
    assert all(c["passed"] and c["mismatches"] == c["out_err"] == c["timeout"] == 0
               and not any(c["faults"]) for c in rec["cases"])
    for name, flits, ar, fused in (("act", 77, 464, 2004), ("y", 40, 316, 1116)):
        x = rec["summary"][name]
        assert x["local_flits_per_die"] == flits
        assert x["ar_tail_cycles"] == ar and x["mtp_fused_tail_cycles"] == fused
        assert x["ar_tail_cycles"] >= x["ar_output_port_floor"]
        assert x["mtp_fused_tail_cycles"] >= x["mtp_output_port_floor"]
        assert x["mtp_serial_six_tail_cycles"] == 6 * ar
    assert "no core packing" in rec["scope"]
