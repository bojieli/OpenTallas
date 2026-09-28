"""The full-shape activation-load sensitivity must stay tied to its evidence."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_fullshape_load_floor as F  # noqa: E402


def test_current_record_and_source_pins():
    saved = json.loads(F.OUT.read_text())
    assert F.build() == saved
    for path, digest in saved["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_floor_changes_batch_one_token_path():
    rec = F.build()
    assert rec["contract"]["proposed_wo_a_load_cycles_per_layer"] == 2048
    assert rec["contract"]["current_wo_a_descriptor"].startswith("invalid")
    for rows in rec["points"].values():
        row = rows["gw1_depth128_exact_stage"]
        assert row["proposed_wo_load_ar_tok_s"] < row["before_wo_load_ar_tok_s"]
        assert row["status"].startswith("conditional")
    assert "MTP has no corrected" in " ".join(rec["limits"])
