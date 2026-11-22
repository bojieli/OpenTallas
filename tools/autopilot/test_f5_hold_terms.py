"""F5 (FLOW-OPS-R2 11-22, FABLE-FLOW-0000): hold owner + eta, HOLD-OVERDUE, orphan relaunch, kit_wave_edit refusal, NO-PROGRESS names the blocker."""
import sys, time
from datetime import datetime
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H)); sys.path.insert(0, str(H.parent / "fleet"))
import kit_wave as KW  # noqa: E402
import kit_wave_edit as E  # noqa: E402
import progress_watch as PW  # noqa: E402

NOW = time.mktime(time.strptime("2026-11-22 08:00", "%Y-%m-%d %H:%M"))


def cfg(holds, **kw):
    return {"dies": {"s81": dict(enabled=True, event="B6gF2s4", owner="S81-J6", hold_items=dict(holds), **kw)}}


def test_hold_term_parse_and_findings():
    assert KW.hold_term("J6 reps first owner=S81-J6 eta=2026-11-22 12:00")[0] == "S81-J6"
    assert KW.hold_term("x eta: 2026-11-21")[1] == time.mktime(time.strptime("2026-11-21", "%Y-%m-%d")) + 86399
    assert KW.hold_term("split pending (OPUS-FIX-S81-SVC-R5)") == ("", None)
    f = KW.hold_term_findings(cfg({"a*": "owner=L eta=2026-11-22 07:00", "b*": "owner=L eta=2026-11-23", "svc_*": "split pending"}), NOW)["s81"]
    assert [k for k, _o, _e in f["overdue"]] == ["a*"] and f["noterm"] == ["svc_*"] and f["n"] == 3


def test_overdue_alert_once_per_change():
    posts = []

    class AP:
        log = staticmethod(lambda m: None)
        coord_append = staticmethod(lambda path, txt: posts.append(txt))
    st = {}
    c = cfg({"a*": "owner=S81-J6 eta=2026-11-22 07:00"})
    KW.hold_term_step(AP, c, st, NOW); KW.hold_term_step(AP, c, st, NOW + 60)
    assert len(posts) == 1 and "HOLD-OVERDUE -> S81-J6, COORD" in posts[0] and "s81/a*" in posts[0]


def test_orphan_release_only_for_no_eta_keys():
    old = NOW - 3 * 3600
    st = {"items": {
        "1": dict(die="s81", item="svc_a", event="B6gF2s4", status="CANCELLED", **{"class": "SUPERSEDED"}, started=old - 100, updated=old),
        "2": dict(die="s81", item="bk_sel__t2", event="B6gF2s4", status="CANCELLED", **{"class": "SUPERSEDED"}, started=old - 100, updated=old),
        "3": dict(die="s81", item="col_x", event="B6gF2s4", status="CANCELLED", **{"class": "SUPERSEDED"}, started=old - 100, updated=old),
        "4": dict(die="s81", item="col_x", event="B6gF2s4", status="RUNNING", started=old + 10, updated=old + 10)}}   # col_x has a successor
    c = cfg({"svc_*": "split pending", "bk_sel__t2": "reps first owner=S81-J6 eta=2026-11-23 10:00", "col_*": "fix in J6"})
    out = KW.orphan_hold_release(c, st, NOW)
    assert [(d, k) for d, k, _i in out] == [("s81", "svc_*")]
    assert set(c["dies"]["s81"]["hold_items"]) == {"bk_sel__t2", "col_*"}
    c2 = cfg({"svc_*": "split pending"}, orphan_hold_release=False)
    assert KW.orphan_hold_release(c2, st, NOW) == [] and "svc_*" in c2["dies"]["s81"]["hold_items"]


def test_kit_wave_edit_new_hold_needs_term():
    old = cfg({"svc_*": "split pending"})
    new = cfg({"svc_*": "split pending", "x*": "because"})
    assert any("x*" in p for p in E.hold_term_problems(old, new))
    new["dies"]["s81"]["hold_items"]["x*"] = "because owner=FAM-X eta=2026-11-23 10:00"
    assert E.hold_term_problems(old, new) == []
    assert E.hold_term_problems(old, cfg({})) == []                            # removing holds is free


def test_noprogress_names_pending_event_and_silent_within_eta():
    now = datetime(2026, 11, 22, 8, 0)
    st = {"pending_event": {"s81_head": "r17b"}}
    assert PW.hold_blocker("s81_head", st, now).startswith("blocker: plan event r17b pending")
    st = {"holds": {"s81": ["reps first owner=L eta=2026-11-22 12:00"]}}
    assert PW.hold_blocker("s81", st, now) == ""                              # within eta: silent
    st = {"holds": {"s81": ["reps first owner=L eta=2026-11-22 07:00", "split pending"]}}
    assert "1 without eta, 1 overdue" in PW.hold_blocker("s81", st, now)
    assert PW.hold_blocker("kv", {}, now) is None
