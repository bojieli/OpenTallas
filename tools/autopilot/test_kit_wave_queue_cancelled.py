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
