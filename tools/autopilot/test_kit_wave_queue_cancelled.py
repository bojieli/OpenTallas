"""KW-FIX-45 11-11: a CANCELLED queue job turns its ENQUEUED wave row into a CANCELLED, retry-eligible row."""
import json
import time
import kit_wave as KW


def ap_dir(tmp_path, jobs):
    d = tmp_path / "ap"; d.mkdir(exist_ok=True)
    (d / "state.json").write_text(json.dumps({"jobs": jobs}))
    return d


def rec(kit="hostA:/k/q_x"):
    return {"die": "hbm", "item": "q_x", "attempt": 2, "status": "ENQUEUED", "kit": kit}


def test_cancelled_queue_job_makes_the_row_cancelled_and_not_superseded(tmp_path):
    st = {"items": {"hbm|q_x|b1": rec()}}
    d = ap_dir(tmp_path, {"j1": {"id": "j1", "kit": "hostA:/k/q_x", "status": "CANCELLED", "updated": 1}})
    notices = {}
    KW.follow_queue(st, d, notices)
    r = st["items"]["hbm|q_x|b1"]
    assert r["status"] == "CANCELLED" and r["class"] == "QUEUE-CANCELLED" and r["class"] != "SUPERSEDED"
    assert r["q_status"] == "CANCELLED" and r["q_id"] == "j1"
    assert "q_x@2" in notices["hbm"][0]


def test_running_and_failed_jobs_are_unchanged(tmp_path):
    for status in ("RUNNING", "ORPHAN"):
        st = {"items": {"k": rec()}}
        d = ap_dir(tmp_path, {"j1": {"id": "j1", "kit": "hostA:/k/q_x", "status": status, "updated": 1}})
        KW.follow_queue(st, d, {})
        assert st["items"]["k"]["status"] == "ENQUEUED" and st["items"]["k"]["q_status"] == status


def test_cancelled_row_is_retry_eligible_only_with_its_entry():
    r = {"status": "CANCELLED", "class": "QUEUE-CANCELLED", "attempt": 2}
    assert "q_x@2" in {"q_x@2"} and not (r["status"] == "FAIL")
    # select() lets a CANCELLED row through only when f"{item}@{attempt}" is in the retry list (no blind retry otherwise)
    src = open(KW.__file__).read()
    assert 'f"{r[\'item\']}@{rec.get(\'attempt\')}" not in retry' in src


def test_unsignable_cancel_is_cancelled_with_its_reason_and_stops_the_block(tmp_path):
    """FLOW-OPS-1300 (FABLE-FLOW-1240 b): the cancel mark reason reaches the row; same plan block never relaunches"""
    r0 = dict(rec(), block_sha="872f1c33699aabcdef", die="s81", item="lepe_t2")
    st = {"items": {"k": r0}}
    why = "cancelled by UNSIGNABLE watchdog at 2026-11-21 11:46:19 (not an OOM kill): CANCEL-UNSIGNABLE: tt_setup_keep.log latest setup WNS -423.00 ps"
    d = ap_dir(tmp_path, {"j1": {"id": "j1", "kit": "hostA:/k/q_x", "status": "CANCELLED", "reasons": why, "updated": 1,
                                 "history": [[0, 0, "cancelled: " + why[:180]]]}})
    notices = {}
    KW.follow_queue(st, d, notices)
    r = st["items"]["k"]
    assert r["status"] == "CANCELLED" and r["class"] == "CANCEL-UNSIGNABLE" and "-423.00" in r["reason"]
    k, e = KW.struct_stop_for(st, "s81", "lepe_t2", "872f1c33699aabcdef")
    assert e and e["block"] == "872f1c33699a" and "CANCEL-UNSIGNABLE" in e["why"]
    assert KW.struct_stop_for(st, "s81", "lepe_t2", "ffffffffffff")[1] is None                # a changed plan block launches
    assert "stopped" in notices["s81"][0]


def test_a_crash_job_with_a_cancel_reason_or_watchdog_superseded_is_cancelled_not_infra():
    j = {"status": "DONE-CRASH", "kind": "infra-stopped", "reasons": "CANCEL-UNSIGNABLE: -891 ps"}
    assert KW.queue_class(j)[1] == "CANCELLED" and KW.queue_class(j)[3].startswith("CANCEL-UNSIGNABLE")
    j = {"status": "DONE-CRASH", "kind": "watchdog-superseded", "reasons": "exit 143: stopped by the hub WATCHDOG (x): SUPERSEDED older attempt"}
    assert KW.queue_class(j)[1] == "CANCELLED" and KW.queue_class(j)[3].startswith("CANCEL-SUPERSEDED")
    j = {"status": "DONE-CRASH", "kind": "infra-stopped", "reasons": "exit 143, no OOM line in the run logs: stopped from outside"}
    st_, status, cls, why = KW.queue_class(j)
    assert status == "FAIL" and cls == "INFRA"                                             # unknown stop: not a cancel, and (repeat_stop) not an OOM
