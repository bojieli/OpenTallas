"""The reduced RTL record stays bound to its exact sources."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_qwen_kv_write_adapter_record_is_current_and_passes():
    rec = json.loads((ROOT / "results/rtl/qwen_kv_write_adapter_prototype.json").read_text())
    assert rec["status"] == "pass"
    assert set(rec["runs"]) == {"8", "16"}
    assert all(set(run) == {"write", "read", "streamer_tail_port"} and
               all(part["status"] == "pass" for part in run.values())
               for run in rec["runs"].values())
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
