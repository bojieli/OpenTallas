import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR
import kit_wave as KW

PLAN = "p" * 64


def cfg(cancel):
    rec = {"id": "r1", "plan_sha": PLAN, "reason": "why", "release": ["result:L:tag"], "items": ["col_a", "col_b__*"], "owner": "L", "cause": "c"}
    if cancel:
        rec["cancel_running"] = True
    return {"dies": {"s": {"event": "e", "plan_sha256": PLAN, "hold_event_items": {PLAN: ["col_a", "col_b__t1"]}, "hold_records": [rec]}}}


class AP:
    DRY = True
    HUB_NAME = "hub"
    logs = []
    log = staticmethod(lambda m: AP.logs.append(m))
    sh = staticmethod(lambda *a, **k: (0, "", ""))


def test_cancel_running_marks_keys_and_removes_protection():
    c = cfg(True)
    HR.compile_holds(c)
    assert sorted(c["_hold_cancel_running"]["s"]) == ["col_a", "col_b__*"]
    row = {"die": "s", "item": "col_a", "event": "old"}
    assert KW.hold_protects_running(c, c["dies"]["s"], row, "anything") is False
    assert KW.hold_protects_running(c, c["dies"]["s"], {"die": "s", "item": "other"}, "x") is True
    c2 = cfg(False)
    HR.compile_holds(c2)
    assert c2["_hold_cancel_running"] == {} and KW.hold_protects_running(c2, c2["dies"]["s"], row, "x") is True


def test_held_running_rows_are_stopped_only_with_the_flag():
    for flag, want in ((True, "CANCELLED"), (False, "RUNNING")):
        c = cfg(flag)
        HR.compile_holds(c)
        st = {"items": {"k1": {"die": "s", "item": "col_a", "status": "RUNNING", "unit": "u1", "dir": "/nonexistent", "attempt": 2},
                        "k2": {"die": "s", "item": "free", "status": "RUNNING", "unit": "u2", "dir": "/nonexistent"}}}
        notices = {}
        KW.cancel_held_running(AP, c, st, notices)
        assert st["items"]["k1"]["status"] == want and st["items"]["k2"]["status"] == "RUNNING"
        if flag:
            assert st["items"]["k1"]["class"] == "HELD-STOP"


def test_do_yosys_stop_inside_place_is_synth():
    txt = "[INFO] x\nmake: *** [Makefile:12: do-yosys] Error 2\nERROR: TCL interpreter returned an error: child process exited abnormally\n"
    cls, why = KW.classify("place", txt)
    assert cls == "FLOW" and "synth (yosys)" in why
    assert "synth" not in KW.classify("place", "ERROR: TCL interpreter returned an error: child process exited abnormally")[1]


def test_grt_setup_repair_reroutes_on_rsz0074_and_never_fails_the_stage():
    root = Path(__file__).resolve().parents[1] / "die_plan"
    tcl = (root / "tt_setup_repair.tcl").read_text()
    assert "proc ot_tt_est_after_repair" in tcl and "RSZ-0074" in tcl
    i = tcl.index("proc ot_tt_est_after_repair")
    body = tcl[i:tcl.index("\n}\n", i)]
    assert body.index("-allow_congestion -start_incremental") < body.index("global_route -allow_congestion;")       # incremental re-route first, then a full global_route
    assert "ot_tt_est_after_repair\n" in tcl[tcl.index("lassign [ot_tt_wns before]"):]                        # the final estimate goes through it
    gen = (root / "gen_phys.py").read_text()
    assert "FAIL_TT_SETUP_REPAIR" not in gen                                            # the stage is not failed (OWNER r703)
    assert "WARNING: OT_TT_SETUP_REPAIR GRT step failed" in gen and "OT_GRT_REPORT_CORNER FF" in gen
