"""Check the source-pinned logical Qwen activation handoff stress gate."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/qwen_two_reticle_handoff.json"


def test_qwen_two_reticle_handoff_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-two-reticle-logical-handoff.v1"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    assert rec["build_returncode"] == rec["returncode"] == 0
    cfg = rec["configuration"]
    assert cfg == {
        "data_bits": 256, "transaction_bits": 12, "user_bits": 3,
        "position_bits": 16, "topology_bits": 5,
        "exchange_bits": 8, "fifo_depth": 4,
        "users": 2, "transactions": 4, "exchanges_at_one_position": 4,
        "payload_beats": 536, "full_vector_bytes": 16384,
        "aborted_transactions": 1, "seed": "71ace55d",
    }
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    exe = Path(rec["workdir"]) / "obj/Vtb_qwen_activation_handoff"
    if exe.exists():
        assert hashlib.sha256(exe.read_bytes()).hexdigest() == rec["binary_sha256"]
    assert rec["metrics"] == {
        "beats": 536, "completions": 4, "aborts": 1, "users": 2,
        "cycles": 2199, "max_level": 4, "source_stalls": 1068,
        "sink_stalls": 1618, "status_stalls": 60, "terminal_wait": 35,
        "fault": 0, "seed": "71ace55d",
    }
    assert rec["stdout"].count("PASS") == 1
    assert "FAIL" not in rec["stdout"] and "FATAL" not in rec["stdout"]
