"""Source-pinned reduced exactness gate for the attention packed-row SRAM boundary."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_v41x_attn_macro_stage.json"


def test_macro_stage_exact_gate_is_current():
    rec = json.loads(RECORD.read_text())
    assert rec["status"] == "pass"
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest
               for p, digest in rec["sources"].items())
    a, b = rec["arms"]["0"], rec["arms"]["1"]
    assert a["bit_exact"] and b["bit_exact"]
    assert a["cycles"] == b["cycles"]
    assert a["score_errors"] == b["score_errors"] == 0
    assert a["pv_errors"] == b["pv_errors"] == 0
    assert a["scores_checked"] == b["scores_checked"] > 0
    assert a["pv_checked"] == b["pv_checked"] > 0
