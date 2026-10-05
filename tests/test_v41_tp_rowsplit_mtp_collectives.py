"""Source-pinned six-position V4.1 gather timing evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_six_position_gather_record_is_exact_and_bounded():
    rec = json.loads((ROOT / "results/rtl/v41_tp_rowsplit_mtp_collectives.json").read_text())
    assert rec["schema"] == "v41_tp_rowsplit_mtp_collectives_v1"
    for path, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    assert rec["contract"] == dict(CL_LANES=16, flit_bytes=64, CL_DEPTH=128,
                                   DMA_VM_words_per_cycle=1, PAIRWISE=1, PUSHW=1, QTX=2, m=6)
    assert len(rec["cases"]) == 14
    assert all(case["passed"] and case["mismatches"] == case["out_err"] == case["timeout"] == 0
               and not any(case["faults"]) for case in rec["cases"])
    for pattern, local in (("act", 266), ("y", 80)):
        row = rec["summary"][pattern]
        assert row["local_flits_per_die"] == local
        assert row["fused_local_flits_per_die"] == 6 * local
        assert row["fused_exposed_tail_cycles"] >= row["one_vm_write_per_cycle_floor"]
        assert row["serial_six_exposed_tail_cycles"] >= row["one_vm_write_per_cycle_floor"]
