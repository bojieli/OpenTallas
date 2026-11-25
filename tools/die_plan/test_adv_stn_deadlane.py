"""tests for adv_stn_deadlane.py (PRECHECK ADV-STN-DEADLANE): python3 -m pytest tools/die_plan/test_adv_stn_deadlane.py"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_stn_deadlane as A  # noqa: E402


def _plan(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text("{}")
    return p, hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def test_not_checked_without_elab(tmp_path, monkeypatch):
    for k in ("OT_STN_DEADLANE_REPORT", "OT_STN_DEADLANE_ELAB", "OT_STN_DEADLANE_ASBUILT"):
        monkeypatch.delenv(k, raising=False)
    p, _ = _plan(tmp_path)
    out = A.findings({}, p)
    assert len(out) == 1 and out[0].startswith("WARN ADV-STN-DEADLANE not checked")


def test_report_lines_and_stale_report(tmp_path):
    p, sha = _plan(tmp_path)
    rep = dict(plan_sha=sha, findings=[dict(type="kv3_pv_v2n", bus="o_x", state="DEAD-TYPE", parts=["pv_N_2"],
                                            dead_parts=["pv_N_2"], multi_parts=[])])
    rp = tmp_path / "stn_deadlane.json"
    rp.write_text(json.dumps(rep))
    out = A.findings({}, p, stn_deadlane=str(rp))
    assert out == ["WARN ADV-STN-DEADLANE DEAD-TYPE kv3_pv_v2n o_x parts=pv_N_2 of 1 (fix: drop the row (0 bits ride it; "
                   "latency-neutral))"]
    rep["plan_sha"] = "000000000000"
    rp.write_text(json.dumps(rep))
    assert "stale report" in A.findings({}, p, stn_deadlane=str(rp))[0]


def test_registered_in_plan_advisory():
    import plan_advisory
    assert ("STN-DEADLANE", "adv_stn_deadlane") in plan_advisory.CHECKS
