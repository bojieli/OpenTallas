"""OWNER 12.25 die clock gate = routed pair slack (TT setup >= 0, FF hold >= +10, 0 contract violations); skew = WARN."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pair_slack_gate as PSG  # noqa: E402
import die_infra as DI  # noqa: E402
import pytest  # noqa: E402

@pytest.fixture(autouse=True)
def _legacy_signoff_profile(monkeypatch):
    """this module pins the pre-R-MINIMAL gates (OT_SIGNOFF_PROFILE=legacy); R-MINIMAL is covered by
    tools/die_plan/test_signoff_profile.py"""
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")


def _rec(skew=200.0, setup=12.0, hold=10.0, contract=0, unmeasured=0):
    def cls(c):
        d = dict(pairs=4, worst_setup_slack_ps=setup if c == "TT" else 300.0, setup_neg_pairs=0,
                 worst_hold_slack_ps=hold if c == "FF" else 200.0, hold_neg_pairs=0, skew_diag_max_ps=skew)
        if c == "FF":
            d["kit_contract_hold"] = dict(window_ps=40.0, neg_pairs=contract, worst_hold_bound_ps=5.0)
            d["hold_measured"] = dict(pairs_measured=4 - unmeasured, pairs_unmeasured=unmeasured,
                                      hold_margin_ps=hold, neg_pairs=int(hold < 0))
        return d
    return {"corners": {c: {"classes": {"intra": cls(c), "seam": cls(c), "landed": dict(pairs=0),
                                        "seam_nearest_INFO": dict(pairs=4, worst_setup_slack_ps=-50.0)}}
                        for c in ("TT", "FF")}}


def test_skew_200_with_slack_passes_with_warn():
    v = PSG.from_related(_rec(skew=200.0, setup=0.0, hold=10.0, contract=0))
    assert v["verdict"] == "PASS" and v["reasons"] == []
    assert len(v["warnings"]) == 1 and "WARN" in v["warnings"][0] and v["skew_max_ps"] == 200.0


def test_hold_below_zero_fails():
    """OWNER 11-02: no +10 ps hold margin -- FF hold slack >= 0 passes, < 0 fails (25 ps FF hold uncertainty stays)."""
    assert PSG.HOLD_MIN_PS == 0.0
    assert PSG.from_related(_rec(hold=0.0))["verdict"] == "PASS"
    assert PSG.from_related(_rec(hold=9.0))["verdict"] == "PASS"
    v = PSG.from_related(_rec(hold=-0.1))
    assert v["verdict"] == "FAIL" and any("FF hold" in r for r in v["reasons"])


def test_one_contract_violation_fails():
    v = PSG.from_related(_rec(contract=1))
    assert v["verdict"] == "FAIL" and v["contract_violations"] == 2   # one per gated class (intra + seam)
    v = PSG.verdict(5.0, 20.0, 1, 10.0)
    assert v["verdict"] == "FAIL" and v["reasons"] == ["1 block arrival-contract violation(s)"]


def _ca(lo_tt=42.8, lo_ff=27.1, guard=0):
    def c(lo):
        return dict(crossings=2, need_ps=100.0, below_need=1, unbound=0, no_taps=0, guard=dict(fail=guard),
                    slot_read=dict(fail=0), start_skew=dict(fail=0), verdict="FAIL",
                    rows=[dict(margin_lo_ps=lo, margin_hi_ps=900.0), dict(margin_lo_ps=600.0, margin_hi_ps=700.0)])
    return {"TT": c(lo_tt), "FF": c(lo_ff)}


def test_count_aligned_landed_judged_by_crossings_not_half_period():
    """COORD 13:0x (DIE-KV-56 4b/4c): count-aligned landed = crossings at 12.25 (TT >= 0, FF >= 0 since OWNER 11-02); need 100 INFO;
    the half-period plan_landing FAIL does not count."""
    r = _rec(skew=100.0)
    bad = dict(pairs=8, plan_landing=dict(verdict="FAIL", window_ps=416.5, damage_max_ps=1260.0))
    for c in ("TT", "FF"):
        r["corners"][c]["classes"]["landed"] = dict(bad)
    assert PSG.from_related(r)["verdict"] == "FAIL"                       # legacy form: half-period window gates
    r["count_aligned"] = _ca()
    v = PSG.from_related(r)
    assert v["verdict"] == "PASS" and v["contract_violations"] == 0
    assert v["count_aligned"]["FF"]["below_need_INFO"] == 1
    r["count_aligned"] = _ca(lo_ff=0.0)
    assert PSG.from_related(r)["contract_violations"] == 0                # FF crossing at 0 passes (OWNER 11-02)
    r["count_aligned"] = _ca(lo_ff=-0.1)
    assert PSG.from_related(r)["contract_violations"] == 1                # FF crossing below 0
    r["count_aligned"] = _ca(lo_tt=-0.1)
    assert PSG.from_related(r)["verdict"] == "FAIL"
    r["count_aligned"] = _ca(guard=1)
    assert PSG.from_related(r)["contract_violations"] == 2                # guard failure (TT + FF) stays a violation
    r["count_aligned"] = {"TT": dict(_ca()["TT"], rows=None)}
    assert "count_aligned TT: rows" in PSG.from_related(r)["missing"]


def test_negative_setup_fails_and_info_class_ignored():
    assert PSG.from_related(_rec(setup=-0.5))["verdict"] == "FAIL"
    assert PSG.from_related(_rec())["tt_setup_ps"] == 12.0          # seam_nearest_INFO -50 does not gate


def test_missing_numbers_not_run_and_unmeasured_blocked():
    r = _rec()
    del r["corners"]["FF"]["classes"]["seam"]["kit_contract_hold"]
    assert PSG.from_related(r)["verdict"] == "NOT RUN"
    assert PSG.from_related(_rec(unmeasured=1))["verdict"] == PSG.BLOCKED
    assert PSG.verdict(None, 20.0, 0)["verdict"] == "NOT RUN"
    assert PSG.verdict(1.0, None, 0, hold_unmeasured=3)["verdict"] == PSG.BLOCKED


def _infra(tmp_path, hold, contract=0, unc_setup=0):
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    sha = hashlib.sha256(plan.read_bytes()).hexdigest()
    pre = dict(plan=str(plan), plan_sha256=sha)
    rec = dict(plan=str(plan), plan_sha256=sha, period_ps=833, unc_setup_ps=unc_setup, unc_hold_ps=25,
               coverage={"uncovered_bits": {}}, corners={}, block_model={})
    for c in ("TT", "FF"):
        rec["corners"][c] = dict(basis="routed RC", classes={
            k: dict(pairs=2, worst_setup_slack_ps=30, worst_hold_slack_ps=hold, setup_neg_pairs=0, hold_neg_pairs=0,
                    skew_diag_max_ps=210.0, kit_contract_hold=dict(neg_pairs=contract))
            for k in ("intra", "seam")} | {"intra_cross_region": dict(pairs=0), "landed": dict(pairs=0)})
    p = tmp_path / "sta.json"
    p.write_text(json.dumps(rec))
    return DI.related_sta_state(str(p), pre)


def test_die_infra_freeze_gate_1225(tmp_path):
    ok = _infra(tmp_path, hold=10)
    assert ok["verdict"] == "PASS" and "WARN" in ok["skew_role"]          # skew 210 never fails
    assert _infra(tmp_path, hold=0)["verdict"] == "PASS"                  # OWNER 11-02: hold >= 0
    assert _infra(tmp_path, hold=-1)["verdict"] == "FAIL"
    assert _infra(tmp_path, hold=50, contract=1)["verdict"] == "FAIL"
    assert _infra(tmp_path, hold=10, unc_setup=60)["verdict"] == "PASS"   # legacy record still accepted
    assert _infra(tmp_path, hold=10, unc_setup=30)["verdict"] == "FAIL"
