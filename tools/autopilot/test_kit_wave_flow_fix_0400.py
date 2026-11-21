"""FLOW-FIX-0400 (FABLE-FLOW-0400 b, c, e, f): live attempts are never stopped for a newer one, a structural drt-nopath is held for its owner, restage_min_wait_s has one source,
a plan-input gen repeat is released by no tools change and caps itself."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402
import repeat_stop as RS  # noqa: E402

NOW = time.time()


def row(attempt, started, event="e1", status="RUNNING", d=None, **kw):
    r = dict(die="d", item="t", attempt=attempt, status=status, event=event, started=started, updated=started, unit=f"kw-{attempt}")
    if d is not None:
        r["dir"] = str(d)
    r.update(kw)
    return r


def mkdir(tmp_path, name, age_s, stage_rc=None):
    p = tmp_path / name
    p.mkdir()
    log = p / "unit.log"
    log.write_text(f"KW_STAGE_RC {stage_rc} 0\n" if stage_rc else "x\n")
    os.utime(log, (NOW - age_s, NOW - age_s))
    return p


# --- (b) launch guard -------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_live_progressing_attempt_refuses_a_newer_launch(tmp_path):
    old = row(3, NOW - 7200, d=mkdir(tmp_path, "a3", 600))
    st = {"items": {"d|t|b1": old}}
    assert KW.live_progressing_attempt({}, st, "d", "e1", "t", "d|t|b2", NOW) is old
    assert KW.live_progressing_attempt({}, st, "d", "e2", "t", "d|t|b2", NOW) is None        # another event: parallel new-plan attempt, allowed
    assert KW.live_progressing_attempt({}, st, "d", "e1", "t", "d|t|b1", NOW) is None        # its own record


def test_a_silent_live_attempt_does_not_block(tmp_path):
    old = row(3, NOW - 20000, d=mkdir(tmp_path, "a3", 3 * 3600))
    assert KW.live_progressing_attempt({}, {"items": {"d|t|b1": old}}, "d", "e1", "t", "d|t|b2", NOW) is None


# --- (b) reap survivor -------------------------------------------------------------------------------------------------------------------------------------------------------------

class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self):
        self.logs, self.stops = [], []

    def log(self, m):
        self.logs.append(m)

    def sh(self, cmd, timeout=None, input=None):
        self.stops.append(cmd)
        return 0, "{}", ""


def reap(st, tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"jobs": {}}))
    ap = AP()
    KW.reap_stale_attempts(ap, {"dies": {}}, st, {}, tmp_path)
    return ap


def test_reap_keeps_the_attempt_with_more_progress_not_the_newest(tmp_path):
    older = row(1, NOW - 9000, d=mkdir(tmp_path, "a1", 300, stage_rc="place"), stage="place")      # placed, running
    newer = row(2, NOW - 600, d=mkdir(tmp_path, "a2", 60), stage="gen")                              # just started
    st = {"items": {"d|t|b1": older, "d|t|b2": newer}}
    ap = reap(st, tmp_path)
    assert older["status"] == "RUNNING"
    assert newer["status"] == "CANCELLED" and newer["class"] == "SUPERSEDED"
    assert any("further progress" in m for m in ap.logs)


def test_reap_with_equal_progress_keeps_the_later_start(tmp_path):
    a = row(1, NOW - 9000, d=mkdir(tmp_path, "a1", 60))
    b = row(2, NOW - 600, d=mkdir(tmp_path, "a2", 60))
    st = {"items": {"d|t|b1": a, "d|t|b2": b}}
    reap(st, tmp_path)
    assert b["status"] == "RUNNING" and a["status"] == "CANCELLED"


def test_reap_never_touches_another_event(tmp_path):
    a = row(1, NOW - 9000, event="e1", d=mkdir(tmp_path, "a1", 60))
    b = row(2, NOW - 600, event="e2", d=mkdir(tmp_path, "a2", 60))
    reap({"items": {"d|t|b1": a, "d|t|b2": b}}, tmp_path)
    assert a["status"] == "RUNNING" and b["status"] == "RUNNING"


# --- (c) drt-nopath hold and the per-cause cap -----------------------------------------------------------------------------------------------------------------------------

DRT = "[ERROR DRT-0255] Maze Route cannot find path of net net158717 in worker of routeBox ( 1 2 ) ( 3 4 )"


def failed(started, reason=DRT, **kw):
    return dict(die="d", item="coll_ftc", attempt=5, status="ENQUEUED", q_status="FAIL", q_class="ROUTING", q_reason=reason, started=started, block_sha="b" * 40, stage="route", **kw)


def test_drt_nopath_is_held_without_a_fix_key():
    cfg = {"dies": {"d": {"retry": ["coll_ftc@5"]}}}
    assert "DRT-NOPATH hold" in KW.drt_nopath_held(cfg, {}, "d", failed(NOW))
    assert KW.drt_nopath_held(cfg, {}, "d", failed(NOW, reason="no space left")) == ""
    assert KW.drt_nopath_held(cfg, {}, "d", dict(failed(NOW), status="RUNNING", q_status="RUNNING")) == ""


def test_drt_nopath_released_by_a_named_fix_and_old_rows_may_use_the_snap_fix():
    cfg = {"dies": {"d": {"retry": ["coll_ftc@5"], "_retry_fix": {"coll_ftc@5": KW.DRT_RESERVED_SNAP_FIX}}}}
    assert KW.drt_nopath_held(cfg, {}, "d", failed(NOW)) == ""
    old = KW.drt_nopath_held({"dies": {"d": {}}}, {}, "d", failed(KW.DRT_RESERVED_SNAP_EPOCH - 3600))
    assert "fix=42fa174c180 is allowed" in old
    assert "is allowed" not in KW.drt_nopath_held({"dies": {"d": {}}}, {}, "d", failed(KW.DRT_RESERVED_SNAP_EPOCH + 3600))


def test_one_automatic_retry_per_cause(tmp_path):
    cfg = {"dies": {"d": {}}}
    st = {}
    prev = failed(NOW, reason="gen exploded: ValueError: bad pin 12")
    assert KW.cause_cap_held(cfg, st, "d", prev) == ""                                     # first automatic retry: allowed, counted
    assert "CAUSE-CAP" in KW.cause_cap_held(cfg, st, "d", prev)                            # same cause again: held
    prev2 = failed(NOW, reason="gen exploded: ValueError: bad pin 99")                     # digits fold into the same cause
    assert "CAUSE-CAP" in KW.cause_cap_held(cfg, st, "d", prev2)
    other = failed(NOW, reason="RuntimeError: something else")
    assert KW.cause_cap_held(cfg, st, "d", other) == ""                                    # a different cause has its own count
    cfg["dies"]["d"].update(retry=["coll_ftc@5"], _retry_fix={"coll_ftc@5": "abc123"})
    assert KW.cause_cap_held(cfg, st, "d", prev) == ""                                     # a named fix resets it


def test_infra_failures_are_not_capped_per_cause():
    prev = dict(failed(NOW, reason="make Error 247"), q_class="INFRA", **{"class": "INFRA"})
    for _ in range(3):
        assert KW.cause_cap_held({"dies": {"d": {}}}, {}, "d", prev) == ""


# --- (e) restage_min_wait_s one source -------------------------------------------------------------------------------------------------------------------------------------------

def test_restage_min_wait_default_is_1800_and_an_expired_override_is_ignored():
    assert KW.restage_min_wait({}) == 1800
    assert KW.restage_min_wait({"restage_min_wait_s": 300}, NOW) == 300                        # no expiry: honoured (the wave logs RESTAGE-CONFIG)
    assert KW.restage_min_wait({"restage_min_wait_s": 300, "restage_min_wait_s_until": NOW - 5}, NOW) == 1800
    assert KW.restage_min_wait({"restage_min_wait_s": 300, "restage_min_wait_s_until": NOW + 3600}, NOW) == 300
    assert "restage_min_wait_s\", 1800" not in Path(KW.__file__).read_text()                  # no second literal default


# --- (f) gen repeats ---------------------------------------------------------------------------------------------------------------------------------------------------------------

GEN = "OT_MACRO_MOVES overlap: u_a and u_b (gen_phys.py)"


def test_plan_input_gen_repeat_is_not_released_by_a_tools_change():
    st = {}
    for n in (1, 2, 3):
        ev = RS.record(st, "d", "i", n, "gen", "PLAN", GEN, inputs={"block": "b1", "tools": "t1"}, t=1000 + n, event="e1")
    assert ev["event"] == "BLOCKED-REPEAT" and ev["class"] == RS.GEN_CLASS
    assert RS.gate(st, "d", "i", {"block": "b1", "tools": "t2"}, event="e1")[0] is True        # tools alone: still blocked
    assert RS.gate(st, "d", "i", {"block": "b2", "tools": "t2"}, event="e1")[2].startswith("inputs:block")


def test_plan_input_gen_repeat_caps_after_two_releases(monkeypatch):
    monkeypatch.setattr(RS, "TOTAL_CAP", 99)                  # the separate 6-attempt total cap would fire first
    st = {}
    for rel in range(RS.PLAN_RELEASE_CAP):
        for n in range(3):
            ev = RS.record(st, "d", "i", rel * 10 + n, "gen", "PLAN", GEN, inputs={"block": f"b{rel}"}, t=1000 + rel * 100 + n, event="e1")
        assert ev["event"] == "BLOCKED-REPEAT"
        assert RS.gate(st, "d", "i", {"block": f"b{rel + 1}"}, event="e1")[0] is False
    for n in range(3):
        ev = RS.record(st, "d", "i", 90 + n, "gen", "PLAN", GEN, inputs={"block": "bX"}, t=5000 + n, event="e1")
    assert ev["event"] == RS.CAP_STATE and RS.GEN_CLASS in ev["why"]
    assert RS.gate(st, "d", "i", {"block": "bY"}, event="e1")[0] is True                       # an input change does not release a cap stop
    assert RS.gate(st, "d", "i", {"block": "bY"}, event="e2")[0] is False                    # another plan event has its own ledger row


def test_other_gen_failures_still_release_on_tools():
    st = {}
    for n in (1, 2, 3):
        RS.record(st, "d", "i", n, "gen", "FLOW", "AttributeError: module gen_phys has no attribute tap_3 (gen_phys.py)", inputs={"block": "b1", "tools": "t1"}, t=n, event="e1")
    assert RS.gate(st, "d", "i", {"block": "b1", "tools": "t2"}, event="e1")[0] is False
