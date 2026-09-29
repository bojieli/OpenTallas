"""Source-pinned record checks for the shared-service QE weight-stall gate (tools/v41_qe_shared_stall_gate.py)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/v41_qe_shared_stall.json"


def _rec():
    return json.loads(REC.read_text())


def test_sources_pinned():
    rec = _rec()
    for rel, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel


def test_stall_cases_exact_with_real_wq_a():
    rec = _rec()
    assert rec["status"] == "pass"
    assert rec["descriptor"]["words"] == 3840 and rec["descriptor"]["nout"] == 320
    assert rec["vectors"]["tensor"] == "layers.0.attn.wq_a" and rec["vectors"]["rows"] == [0, 320]
    stall = [c for c in rec["cases"] if c["stall"]]
    assert {c["k_period"] for c in stall} >= {0, 1}
    for c in stall:
        assert c["status"] == "pass" and c["errors"] == 0 and c["masked"] == 4 and c["rows"] == 384
        assert c["consumed"] == 3840 and c["w_sectors"] == 65280


def test_contention_is_monotone_enough():
    """Saturating K traffic can only delay the weight stream relative to no K traffic."""
    rec = _rec()
    by = {c["k_period"]: c for c in rec["cases"] if c["stall"]}
    assert by[1]["end"] >= by[0]["end"]
    assert by[0]["k_offer"] == 0 and by[1]["k_rsp"] > 0


def test_fixed_rate_no_stall_window_is_not_claimed():
    rec = _rec()
    small = [c for c in rec["cases"] if not c["stall"] and c["window_words"] == 1024]
    assert small and all(c["status"] != "pass" for c in small)
