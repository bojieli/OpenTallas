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


def test_hold_9_fails():
    v = PSG.from_related(_rec(hold=9.0))
    assert v["verdict"] == "FAIL" and any("FF hold" in r for r in v["reasons"])


def test_one_contract_violation_fails():
    v = PSG.from_related(_rec(contract=1))
    assert v["verdict"] == "FAIL" and v["contract_violations"] == 2   # one per gated class (intra + seam)
    v = PSG.verdict(5.0, 20.0, 1, 10.0)
    assert v["verdict"] == "FAIL" and v["reasons"] == ["1 block arrival-contract violation(s)"]


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
    assert _infra(tmp_path, hold=9)["verdict"] == "FAIL"
    assert _infra(tmp_path, hold=50, contract=1)["verdict"] == "FAIL"
    assert _infra(tmp_path, hold=10, unc_setup=60)["verdict"] == "PASS"   # legacy record still accepted
    assert _infra(tmp_path, hold=10, unc_setup=30)["verdict"] == "FAIL"
