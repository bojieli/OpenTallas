"""FAMCAUSE-1122 (FLOW-OPS-R2, FABLE-FLOW-0230 R1): one failing path across sibling types holds the family; PLAN / STRUCTURAL stops at any
stage ignore a tools-hash change."""
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H)); sys.path.insert(0, str(H.parent))
import kit_wave as KW  # noqa: E402
import repeat_stop as RS  # noqa: E402

WHY = ("FAIL_POSTPLACE PLACE-SETUP-STOP wns -380.81 ps < -300 ps (TT, post-place; routing cannot close it) "
       "start=u_bound.u_lk_nk_u_t_0_1_n_b/q[372]$_DLATCH_N_ end=u_bound.u_t01 hop_um=3.6 path_um=3.6")


def rec(item, att, wns="-380.81", blk="b1", ev="E1"):
    return {"die": "qc", "event": ev, "item": item, "attempt": att, "status": "FAIL", "block_sha": blk,
            "q_reason": WHY.replace("-380.81", wns)}


def cfg():
    return {"dies": {"qc": {"event": "E1", "die_owner": "DIE-QC"}}}


def st(*recs):
    return {"items": {f"{r['item']}@{r['attempt']}": r for r in recs}}


def test_key_folds_instance_numbers_and_buckets_wns():
    a = KW.path_cause_key(rec("cbf_q00__cl1a2b3c", 1))
    assert a == "PLACE-SETUP-STOP|u_lk_nk_u_t_N_N_n_b/q[N]$_DLATCH_N_|u_tN|wns-400"
    assert KW.path_cause_key(rec("cbx_q10__cl4d5e6f", 2, wns="-380.5")) == a
    assert KW.path_cause_key(dict(rec("x", 1), status="SIGNED")) == ""
    assert KW.path_cause_key(dict(rec("x", 1), q_reason="ValueError: boom")) == ""


def test_two_types_hold_their_families_and_releases(monkeypatch):
    monkeypatch.setattr(KW, "family_of", lambda die, it: "fam:" + KW.family_key(it))
    monkeypatch.setattr(KW, "explicit_retry_pending", lambda c, s, d, i: False)
    s1 = st(rec("cbf_q00__cl1a2b3c", 1), rec("cbf_q00__cl7a8b9c", 2))            # one type, two variants: CAUSE-CAP's job, no family hold
    assert KW.famcause_held(cfg(), s1, "qc", "cbf_q00__cl0d0e0f") == ""
    s2 = st(rec("cbf_q00__cl1a2b3c", 1), rec("cbx_q10__cl4d5e6f", 3))
    h = KW.famcause_held(cfg(), s2, "qc", "cbf_q00__cl2b2b2b", block_sha="b9")
    assert h.startswith("FAMCAUSE hold [owner DIE-QC]") and "2 types" in h and "cbx_q10__cl4d5e6f@3" in h
    assert KW.famcause_held(cfg(), s2, "qc", "cbx_q10__cl9e9e9e") != ""
    assert KW.famcause_held(cfg(), s2, "qc", "coll_core") == ""            # another family
    assert KW.famcause_held(cfg(), s2, "qc", "cbf_q00__cl1a2b3c", block_sha="b2") == ""   # own plan block changed
    c = cfg(); c["_unblocks"] = [("fam:cbf_q00", "famcause")]
    assert KW.famcause_held(c, s2, "qc", "cbf_q00__cl2b2b2b") == ""
    c = cfg(); c["dies"]["qc"]["event"] = "E2"                           # new plan event
    assert KW.famcause_held(c, s2, "qc", "cbf_q00__cl2b2b2b") == ""
    monkeypatch.setattr(KW, "explicit_retry_pending", lambda c, s, d, i: True)
    assert KW.famcause_held(cfg(), s2, "qc", "cbf_q00__cl2b2b2b") == ""


def test_structural_place_stop_is_plan_input_tools_change_does_not_release():
    assert RS.is_plan_input("place", "STRUCTURAL", WHY) and RS.is_plan_input("route", "PLAN", "x")
    assert not RS.is_plan_input("gen", "PLAN", "ContractError: no SIGNED mean clock contract")     # gen PLAN keeps the PLAN_INPUT_RE rule
    assert RS.is_plan_input("geom", "FLOW", WHY)
    assert not RS.is_plan_input("route", "FLOW", "DRT-0255 net a")
    s = {}
    for n in (1, 2, 3):
        ev = RS.record(s, "qc", "cbf_q00", n, "place", "STRUCTURAL", WHY, inputs={"block": "b1", "tools": f"t{n}"}, t=1000.0 + n, event="E1")
    assert ev and ev["event"] == "BLOCKED-REPEAT"
    b, why, rel = RS.gate(s, "qc", "cbf_q00", {"block": "b1", "tools": "t9"}, event="E1")
    assert b and not rel
    b, why, rel = RS.gate(s, "qc", "cbf_q00", {"block": "b2", "tools": "t9"}, event="E1")
    assert not b and rel == "inputs:block"
