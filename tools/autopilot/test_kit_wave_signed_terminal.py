"""SIGNED-TERMINAL-1115 (FABLE-FLOW-1350 class 2): an archived R-MINIMAL sign-off ends the item with or without a flow tag"""
import kit_wave as K


def test_unversioned_signoff_is_signed_not_fail():
    j = {"status": "SIGNED-UNVERSIONED", "archive": "h:/a", "prov_error": "no flow release tag carries this commit's flow"}
    stage, status, cls, why = K.queue_class(j)
    assert (status, cls) == ("SIGNED", "") and "terminal" in why and "h:/a" in why


def test_signed_attempt_never_releases_a_retry_key():
    rec = {"die": "s81", "item": "t1", "attempt": 3, "started": 5, "status": "ENQUEUED", "q_status": "SIGNED"}
    ok, why = K.retry_key_decision({"items": {"k": rec}}, "s81", "t1", "3")
    assert ok is False and "signed" in why


def test_ended_fail_still_releases():
    rec = {"die": "s81", "item": "t1", "attempt": 3, "started": 5, "status": "ENQUEUED", "q_status": "FAIL"}
    assert K.retry_key_decision({"items": {"k": rec}}, "s81", "t1", "3")[0] is True


def _pick(q_status, retry):
    cfg = {"dies": {"d": {"event": "e", "retry": retry}}}
    rows = [dict(die="d", item="t1", kind="type", state="NEEDS-KIT", owner="KIT-WAVE", live_job="none", last_activity="",
                 next_step="", evidence="", default_owner="", replicas="1", members="")]
    st = {"items": {K.item_key("d", "e", "t1", "b" * 12): dict(die="d", item="t1", attempt=3, status="ENQUEUED",
                                                                 q_status=q_status, event="e")}}
    picks, skip = K.select(rows, cfg, "d", st, {"t1": "b" * 12})
    return [p["item"] for p in picks], skip


def test_signed_record_is_terminal_even_with_a_retry_key():
    picks, skip = _pick("SIGNED", ["t1@3"])
    assert picks == [] and any("signed off on this plan block" in k for k in skip)


def test_queue_fail_with_retry_key_still_relaunches():
    assert _pick("FAIL", ["t1@3"])[0] == ["t1"]


def test_minimal_auto_retry_skips_a_signed_unversioned_row():
    # the 11-15 relaunch path: queue_class gave FAIL FLOW -> R-MINIMAL one automatic retry -> LAUNCH
    st = {"items": {}}
    for q in ("FAIL", None):
        stage, status, cls, why = K.queue_class({"status": "SIGNED-UNVERSIONED", "archive": "h:/a"}) if q is None else ("", "FAIL", "FLOW", "")
        st["items"][f"k{q}"] = {"die": "d", "item": "t" + str(q), "attempt": 1, "status": "ENQUEUED", "q_status": status, "q_class": cls}
    out = K.minimal_auto_retry(st, "d", "e", {"event": "e"}, [], log=lambda m: None)
    assert "tFAIL@1" in out and "tNone@1" not in out
