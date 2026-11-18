"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-1350): class breaker over (die, stage, class) across items, BLOCKED stays blocked across merges"""
import flow_guard as FG
import kit_wave as KW


def test_three_fails_in_an_hour_across_items_open_the_class_and_hold_fresh_launches():   # WAVE-PILOT-FIX 11-17: CLASS_N 10 -> 3
    st = {}
    for i in range(FG.CLASS_N - 1):
        FG.record_fail(st, "qc", f"it{i}", "FLOW", f"timing closure failed @place: slack -{i} ps", now=1000 + i * 300, legacy=False, stage="place")
    assert FG.held_key(st, "qc", "it0") == ""
    FG.record_fail(st, "qc", "it9", "FLOW", "timing closure failed @place: slack -9 ps", now=1000 + 2 * 300, legacy=False, stage="place")
    assert FG.held_key(st, "qc", "it0").startswith("CLASS qc|place|")
    assert FG.held_key(st, "kv", "it0") == ""                       # another die is another key
    assert len(FG.alert_lines(st, "x")) == 1 and FG.alert_lines(st, "x") == []


def test_fails_spread_over_more_than_an_hour_do_not_open():
    st = {}
    for i in range(10):
        FG.record_fail(st, "qc", f"it{i}", "FLOW", "same @place: x", now=i * 2000, legacy=False, stage="place")   # 2000 s apart: never 3 inside the 3600 s window
    assert FG.held_key(st, "qc", "it9") == ""


def test_class_cools_down_and_the_preflight_does_not_release_it():
    st = {}
    for i in range(10):
        FG.record_fail(st, "qc", f"it{i}", "FLOW", "same @place: x", now=1000 + i, legacy=False, stage="place")
    key = FG.held_key(st, "qc", "it1")
    assert FG.release_by_preflight(st, {key: [True, True]}, now=1100) == []
    assert FG.breaker_tick(st, now=1100) == []
    assert len(FG.breaker_tick(st, now=1010 + FG.BREAKER_COOLDOWN_S + 1)) == 1


def test_input_digest_ignores_tools_and_overlay_churn(monkeypatch):
    cfg = {"dies": {"d": {"plan_sha": "p", "src_sha": "s", "gen_env": {}, "kit_rtl": {}, "event": "e", "_src_overlay": "o1"}}}
    monkeypatch.setattr(KW, "rt_tools_digest", lambda: "t1")
    a = KW.input_digest(cfg, "d")
    monkeypatch.setattr(KW, "rt_tools_digest", lambda: "t2")
    cfg["dies"]["d"]["_src_overlay"] = "o2"
    assert KW.input_digest(cfg, "d") == a
    cfg["dies"]["d"]["src_sha"] = "s2"
    assert KW.input_digest(cfg, "d") != a


def test_blocked_row_stays_blocked_when_main_merges():
    st = {}
    cfg = {"dies": {"d": {"plan_sha": "p", "src_sha": "s", "gen_env": {}, "kit_rtl": {}, "event": "e"}}}
    for i in range(3):
        KW.note_fail_sig(st, {"die": "d", "item": "i", "stage": "kit_rtl", "event": "e", "attempt": i}, "FLOW", "x @kit_rtl: y")
    assert KW.blocked_why(cfg, st, "d", "i")
    cfg["dies"]["d"]["_src_overlay"] = "changed by ot-src-refresh"
    assert KW.blocked_why(cfg, st, "d", "i")
