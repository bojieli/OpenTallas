"""R-MINIMAL + R-PERIOD sign-off profile (OWNER 2026-11-13, PROFILE-1): the only blocking type gates are DRC 0, TT setup
WNS >= -(P_die - 833) - 42 ps (P_die 1000 by default), internal FF hold >= 0; everything else is advisory.
OT_SIGNOFF_PROFILE=legacy keeps the previous verdicts."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import signoff_profile as SP  # noqa: E402
import pair_slack_gate as PSG  # noqa: E402


@pytest.fixture(autouse=True)
def _minimal(monkeypatch):
    for k in ("OT_SIGNOFF_PROFILE", "OT_DIE_PERIOD_PS", "OT_DIE_PERIOD_PS_S81", "OT_DIE_PERIOD_PS_QWEN_KVSYS"):
        monkeypatch.delenv(k, raising=False)


def rec(drc=0, tt=10.0, ff=1.0, port_only=False, extra=None, verdict="NOT SIGNED"):
    ch = dict(drc=dict(verdict="PASS" if drc == 0 else "FAIL", count=drc),
              setup_tt=dict(verdict="PASS" if tt >= 0 else "FAIL", wns_ps=tt),
              hold_ff=dict(verdict="PASS" if ff >= 0 or port_only else "FAIL", wns_ps=ff, port_only_needs_parent=port_only),
              antenna=dict(verdict="FAIL", count=3), drv=dict(verdict="FAIL"), pg=dict(verdict="NOT RUN"),
              io_hold_parent=dict(verdict="NOT RUN"))
    ch.update(extra or {})
    return dict(verdict=verdict, checks=ch, reasons=["antenna: FAIL 3"],
                inputs=dict(kit="/x/kit-wave/s81/ev/items/t1/attempt_1/gen/t1"))


def test_default_profile_is_minimal_and_legacy_flag(monkeypatch):
    assert SP.profile() == "minimal"
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")
    assert SP.profile() == "legacy" and SP.setup_tolerance_ps("s81") == 42.0
    r = rec(tt=-100.0)
    SP.apply(r)
    assert r["verdict"] == "NOT SIGNED" and r["profile"] == "legacy"
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "bogus")
    with pytest.raises(ValueError):
        SP.profile()


def test_only_three_gates_block_everything_else_advisory():
    j = SP.judge(rec())
    assert j["verdict"] == "SIGNED" and j["reasons"] == []
    assert any(a.startswith("antenna") for a in j["advisories"]) and any(a.startswith("drv") for a in j["advisories"])
    assert any(a.startswith("io_hold_parent") for a in j["advisories"])


def test_default_gate_is_minus_42_r_period_held():
    """COORD 11-13: R-PERIOD is a held proposal -- the default gate stays TT WNS >= -42 ps at 833 ps"""
    assert SP.die_period_ps("s81") == 833.0 and SP.setup_tolerance_ps("s81") == 42.0
    assert SP.judge(rec(tt=-42.0))["verdict"] == "SIGNED" and SP.judge(rec(tt=-42.5))["verdict"] == "NOT SIGNED"


def test_r_period_setup_tolerance_and_achieved_period(monkeypatch):
    monkeypatch.setenv("OT_DIE_PERIOD_PS", "1000")
    assert SP.die_period_ps("s81") == 1000.0 and SP.setup_tolerance_ps("s81") == pytest.approx(209.0)
    j = SP.judge(rec(tt=-209.0))
    assert j["verdict"] == "SIGNED" and j["achieved_period_ps"] == pytest.approx(1042.0) and j["die"] == "s81"
    assert SP.judge(rec(tt=-209.5))["verdict"] == "NOT SIGNED"
    assert SP.judge(rec(tt=25.0))["achieved_period_ps"] == 833.0
    monkeypatch.setenv("OT_DIE_PERIOD_PS_S81", "1250")
    assert SP.judge(rec(tt=-450.0))["verdict"] == "SIGNED"
    assert SP.setup_tolerance_ps("qwen_kvsys") == pytest.approx(209.0)
    monkeypatch.setenv("OT_DIE_PERIOD_PS", "833")
    assert SP.setup_tolerance_ps("qwen_kvsys") == 42.0 and SP.judge(dict(drc=0, tt_wns=-43, ff_wns=0, die="kv"))["verdict"] == "NOT SIGNED"


def test_hold_has_no_tolerance_but_port_start_only_is_advisory():
    j = SP.judge(rec(ff=-1.28))                    # e.g. hd_st_n3_transit: internal hold miss, not signed
    assert j["verdict"] == "NOT SIGNED" and j["reasons"][0].startswith("hold_ff: FAIL")
    j = SP.judge(rec(ff=-14.41, port_only=True))   # every violator starts at an input port -> io_hold_parent advisory
    assert j["verdict"] == "SIGNED" and j["hold_port_only"] and any("port-start hold" in a for a in j["advisories"])


def test_drc_and_missing_numbers_block():
    assert SP.judge(rec(drc=1))["reasons"] == ["drc: FAIL 1"]
    r = rec()
    del r["checks"]["setup_tt"]
    assert SP.judge(r)["gates"]["setup_tt"] == "NOT RUN" and SP.judge(r)["verdict"] == "NOT SIGNED"


def test_autopilot_summary_records():
    s = dict(drc=0, tt_wns=147.75, ff_wns=-14.41, local_verdict="SIGNED", verdict="LOCAL_PASS_NEEDS_PARENT", fails=[],
             reasons=["io_hold_parent: NEEDS_PARENT; matching real-parent PASS receipt missing"], die="s81")
    assert SP.judge(s)["verdict"] == "SIGNED"
    s = dict(drc=3, tt_wns=84.87, ff_wns=-15.39, fails=["drc", "drv", "hold_ff"], die="s81_head")
    assert SP.judge(s)["verdict"] == "NOT SIGNED"


def test_apply_keeps_legacy_verdict():
    r = rec(tt=-30.0)
    SP.apply(r)
    assert r["verdict"] == "SIGNED" and r["legacy_verdict"] == "NOT SIGNED" and r["achieved_period_ps"] == 863.0
    assert r["profile"] == "minimal" and r["reasons"] == [] and r["advisories"]


def _related(setup, hold, contract):
    def cls(c):
        d = dict(pairs=4, worst_setup_slack_ps=setup if c == "TT" else 300.0, setup_neg_pairs=int(setup < 0),
                 worst_hold_slack_ps=hold if c == "FF" else 200.0, hold_neg_pairs=0, skew_diag_max_ps=50.0)
        if c == "FF":
            d["kit_contract_hold"] = dict(window_ps=40.0, neg_pairs=contract, worst_hold_bound_ps=5.0)
        return d
    return {"die": "s81", "corners": {c: {"classes": {"intra": cls(c)}} for c in ("TT", "FF")}}


def test_die_clock_gate_minimal(monkeypatch):
    assert PSG.from_related(_related(setup=-1.0, hold=0.0, contract=2))["verdict"] == "FAIL"   # 833 ps default
    monkeypatch.setenv("OT_DIE_PERIOD_PS", "1000")
    v = PSG.from_related(_related(setup=-100.0, hold=0.0, contract=2))   # judged at P_die 1000: -100 + 167 >= 0
    assert v["verdict"] == "PASS" and v["profile"] == "minimal" and any("advisory" in w for w in v["warnings"])
    assert PSG.from_related(_related(setup=-200.0, hold=0.0, contract=0))["verdict"] == "FAIL"
    assert PSG.from_related(_related(setup=10.0, hold=-0.1, contract=0))["verdict"] == "FAIL"
    assert PSG.from_related(_related(setup=10.0, hold=0.0, contract=2))["verdict"] == "PASS"
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")
    assert PSG.from_related(_related(setup=-100.0, hold=0.0, contract=0))["verdict"] == "FAIL"
    assert PSG.from_related(_related(setup=10.0, hold=0.0, contract=2))["verdict"] == "FAIL"


def test_signoff_chain_rejudges_old_records(tmp_path, monkeypatch):
    import signoff_chain as SC
    r = rec(tt=-30.0, verdict="NOT SIGNED")
    assert SC.signed(r) and SC.signoff_gates(r) == dict(drc="PASS", setup_tt="PASS", hold_ff="PASS")
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")
    assert not SC.signed(r)


def test_rejudge_type_of_path():
    import rejudge_minimal as RJ
    assert RJ.type_of_path("/a/kit-wave/s81_head/l48rf/items/hd_turn_a/attempt_5/gen/hd_turn_a/signoff/signoff.json") \
        == ("s81_head", "hd_turn_a", 5)
    out = RJ.compact(dict(rec(), name="x"))
    assert out["checks"]["hold_ff"]["port_only_needs_parent"] is False and json.dumps(out)


def test_inf_slack_is_not_a_measurement():
    """kv3_pv_pair re-judge 11-13: TT 1e42 'slack' (no constrained path) must never sign off"""
    assert SP.judge(dict(drc=0, tt_wns=1.0000000190432691e+42, ff_wns=1.0000000190432691e+42, die="kv"))["verdict"] == "NOT SIGNED"
