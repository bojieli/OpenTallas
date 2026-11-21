"""OWNER 11-20 23:2x: an unstarted old-event row is skipped (LAUNCH-SKIP SUPERSEDED) while the same type has a queued or running row on the current event."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave as KW

CFG = {"dies": {"s81": {"event": "J5"}}}


def row(event, status, **k):
    r = {"die": "s81", "item": "t1", "event": event, "status": status}
    r.update(k)
    return r


def test_skips_unstarted_old_row_when_current_row_is_live():
    for live in ("RUNNING", "LAUNCHING", "ENQUEUED"):
        st = {"items": {"a": row("D8i", "RETRY-INFRA"), "b": row("J5", live)}}
        assert KW.superseded_unstarted(CFG, st, st["items"]["a"]) == "b"


def test_not_skipped_without_live_current_row_or_when_started_or_current():
    st = {"items": {"a": row("D8i", "RETRY-INFRA"), "b": row("J5", "FAIL")}}
    assert KW.superseded_unstarted(CFG, st, st["items"]["a"]) == ""
    st = {"items": {"a": row("D8i", "RETRY-INFRA", started=1.0), "b": row("J5", "RUNNING")}}
    assert KW.superseded_unstarted(CFG, st, st["items"]["a"]) == ""
    st = {"items": {"a": row("J5", "RETRY-INFRA"), "b": row("J5", "RUNNING")}}
    assert KW.superseded_unstarted(CFG, st, st["items"]["a"]) == ""
    st = {"items": {"a": row("D8i", "RUNNING"), "b": row("J5", "RUNNING")}}
    assert KW.superseded_unstarted(CFG, st, st["items"]["a"]) == ""        # a running old-plan kit keeps running


def test_other_type_or_die_does_not_block(tmp_path):
    st = {"items": {"a": row("D8i", "RETRY-INFRA"), "b": row("J5", "RUNNING", item="t2"), "c": row("J5", "RUNNING", die="qc")}}
    assert KW.superseded_unstarted(CFG, st, st["items"]["a"]) == ""
    (tmp_path / "gen").mkdir()
    st = {"items": {"a": row("D8i", "RETRY-INFRA", work=str(tmp_path)), "b": row("J5", "RUNNING")}}
    assert KW.superseded_unstarted(CFG, st, st["items"]["a"]) == ""        # a gen dir exists: it has begun
