"""The packed attention merge was run on the current RTL and bench sources."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_packed_attention_merge_exact_record_is_current():
    rec = json.loads((ROOT / "results/rtl/v41x_attn_row_merge.json").read_text())
    assert rec["status"] == "pass"
    assert rec["checked_rows"] == 14
    assert rec["full_beats"] == 3 and rec["partial_beats"] == 1
    assert rec["remote_rows"] == rec["tag_faults_checked"] == 1
    assert rec["range_faults_checked"] == 1
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
               for path, digest in rec["sources"].items())
