import json
"""FLOW-HEALTH-1 11-16 (FABLE-FLOW-0513 class 3, COORD): REPEAT-STOP.  Replays: coll_n (6x DRT-0255 same net + routeBox), hd_serdes (5x post-CTS), kv3_pc_v1 (OOM at --mem 48)."""
import repeat_stop as RS
import kit_wave as KW

DRT = "[ERROR DRT-0255] Maze Route cannot find path of net %s in worker of routeBox ( %d %d ) ( %d %d )."
CTS = ("FAIL_POSTCTS FAIL_POSTCTS SETUP_TRIAGE pre-route setup estimate below the stop (PLAN-TRIAGE, not routed): OT_POSTCTS_GATE TT (global_routing) "
       "pinreg n 1125 mean 458.77 bound 450.00 dev 8.77 tol 20.0 setup_est -%s hold_est -117.72")
OOM = "post-CTS gate lost (postcts_gate_tt.json missing); infra-oom: earlyoom killed the place unit"
D, I = "qwen_compute", "coll_n"


def test_fingerprint_keeps_the_identifying_object():
    a = RS.fingerprint("route", "CRASH", DRT % ("net25397", 62700, 653220, 66690, 657210))
    assert a == "route|CRASH|DRT-0255 net net25397 box 62700 653220 66690 657210"
    assert a != RS.fingerprint("route", "CRASH", DRT % ("net99", 62700, 653220, 66690, 657210))        # another net
    assert a != RS.fingerprint("route", "CRASH", DRT % ("net25397", 1, 2, 3, 4))                      # another routeBox
    assert RS.fingerprint("cts", "STRUCTURAL", CTS % "261.37") == RS.fingerprint("cts", "STRUCTURAL", CTS % "259.00")     # numbers do not split it
    assert RS.fingerprint("gen", "INFRA", "AttributeError: module gen_phys has no attribute tap_3 (gen_phys.py)") == \
        RS.fingerprint("gen", "INFRA", "AttributeError: module gen_phys has no attribute tap_9 (gen_phys.py)")


def test_coll_n_is_blocked_at_the_third_identical_drt_0255_and_not_relaunched():
    st = {}
    evs = [RS.record(st, D, I, n, "route", "CRASH", DRT % ("net25397", 62700, 653220, 66690, 657210), inputs={"block": "b1"}, t=1000 + n * 3600)
           for n in range(1, 7)]
    assert [bool(e) for e in evs] == [False, False, True, False, False, False]
    assert evs[2]["event"] == "BLOCKED-REPEAT" and "net25397" in evs[2]["fp"]
    # the die overlay / tools changed 6 times: nothing of the item's own changed -> still blocked
    for _ in range(3):
        assert RS.gate(st, D, I, {"block": "b1"})[0] is True
    # a change of the item's own block releases it, once
    assert RS.gate(st, D, I, {"block": "b2"}) == (False, "", "inputs:block")
    assert RS.gate(st, D, I, {"block": "b2"})[0] is False and RS.state_of(st, D, I) == ("", "")


def test_a_different_net_breaks_the_streak():
    st = {}
    for n, net in enumerate(["net1", "net1", "net2", "net2", "net1"], 1):
        assert RS.record(st, D, I, n, "route", "CRASH", DRT % (net, 1, 2, 3, 4), t=n) is None


def test_hd_serdes_post_cts_five_times_is_blocked_at_the_third():
    st = {}
    r = [RS.record(st, "s81_head", "hd_serdes", n, "cts", "STRUCTURAL", CTS % str(250 + n), inputs={"block": "b"}, t=n * 7200) for n in range(1, 6)]
    assert r[2] and r[2]["event"] == "BLOCKED-REPEAT" and r[3] is None and r[4] is None


def test_oom_resubmits_with_more_memory_once_then_blocks():
    st = {}
    e1 = RS.record(st, "qwen_kvsys", "kv3_pc_v1", 1, "place", "INFRA", OOM, t=1)
    assert e1 == {"event": "OOM-RESUBMIT", "fp": e1["fp"], "mem_x": 1.5} and RS.mem_x(st, "qwen_kvsys", "kv3_pc_v1") == 1.5
    assert RS.gate(st, "qwen_kvsys", "kv3_pc_v1", {})[0] is False                      # the resubmit is allowed
    cfg = {"dies": {"qwen_kvsys": {"place_mem_gb": 48}}, "_mem_x": {"qwen_kvsys|kv3_pc_v1": 1.5}}
    assert KW.place_mem_gb(cfg, "qwen_kvsys", "kv3_pc_v1") == 72 and KW.place_mem_gb(cfg, "qwen_kvsys", "other") == 48
    e2 = RS.record(st, "qwen_kvsys", "kv3_pc_v1", 2, "place", "INFRA", OOM, t=2)
    assert e2["event"] == "OOM-RESUBMIT" and e2["mem_x"] == 2.25                      # FLOW-1803 (4): a second OOM raises the memory again, never blocks the row
    assert RS.gate(st, "qwen_kvsys", "kv3_pc_v1", {})[0] is False


def test_stalled_after_six_attempts_in_24h_with_no_later_stage_whatever_the_cause():
    st = {}
    causes = ["AttributeError: a in x.py", "ValueError: b in y.py", "KeyError: c in z.py", "TypeError: d in w.py", "OSError: e in v.py", "IndexError: f in u.py"]
    out = [RS.record(st, "qwen_kvsys", "kv3_pc", n, "gen", "INFRA", c, inputs={"block": "b"}, t=1000 + n * 600) for n, c in enumerate(causes, 1)]
    assert [bool(x) for x in out] == [False] * 5 + [True] and out[5]["event"] == "STALLED"
    st2 = {}
    mixed = [("gen", c) for c in causes[:3]] + [("place", "FlowError: g in t.py")] + [("gen", c) for c in causes[3:]]
    out2 = [RS.record(st2, "d", "i", n, s, "FLOW", c, t=1000 + n * 600) for n, (s, c) in enumerate(mixed, 1)]
    assert not any(out2[:5]) and not out2[-1] or out2[-1] is None                       # reaching place inside the window is progress
    st3 = {}
    old = [RS.record(st3, "d", "i", n, "gen", "FLOW", c, t=n) for n, c in enumerate(causes, 1)]    # six attempts spread over many days: no stall
    assert not any(old[:5])
    spread = {}
    for n, c in enumerate(causes, 1):
        assert RS.record(spread, "d", "i", n, "gen", "FLOW", c, t=n * 30 * 3600) is None


def test_a_pass_resets_the_streak():
    st = {}
    RS.record(st, D, I, 1, "route", "CRASH", DRT % ("n", 1, 2, 3, 4), t=1)
    RS.record(st, D, I, 2, "route", "CRASH", DRT % ("n", 1, 2, 3, 4), t=2)
    RS.record(st, D, I, 3, "place", "", "", ok=True, t=3)
    assert RS.record(st, D, I, 4, "route", "CRASH", DRT % ("n", 1, 2, 3, 4), t=4) is None


def test_unblock_line_releases_by_name_and_prefix():
    st = {}
    for n in range(1, 4):
        RS.record(st, D, I, n, "route", "CRASH", DRT % ("n", 1, 2, 3, 4), inputs={"block": "b"}, t=n)
    un = RS.parse_unblocks("- 2026-11-16 05:00 PST RULING [COORD -> X] unblock coll_n route today\n- other line")
    assert un == [("coll_n", "route")]
    assert RS.gate(st, D, I, {"block": "b"}, [("other_item", "route")])[0] is True
    assert RS.gate(st, D, I, {"block": "b"}, un) == (False, "", "unblock")


def test_launch_gate_refuses_and_posts_one_needs_action(monkeypatch):
    class AP:
        logs, q = [], []
        log = staticmethod(lambda m: AP.logs.append(m))
        coord_append = staticmethod(lambda rel, line: AP.q.append(line))
    cfg = {"dies": {D: {"enabled": True, "event": "e", "owner_lane": "DIE-QC-103"}}}
    st, rec = {}, {"die": D, "item": I, "block_sha": "b1", "dir": "/nonexistent"}
    monkeypatch.setattr(KW, "file_sha", lambda *a, **k: "")
    for n in range(1, 5):
        rec["attempt"] = n
        ev = RS.record(st, D, I, n, "route", "CRASH", DRT % ("net25397", 1, 2, 3, 4), inputs=KW.repeat_inputs(cfg, rec, "x"), t=n)
        if ev:
            KW.repeat_event(AP, cfg, st, rec, ev)
    assert len(AP.q) == 1 and "NEEDS-ACTION" in AP.q[0] and "net25397" in AP.q[0] and "unblock coll_n" in AP.q[0]
    monkeypatch.setattr(KW, "scheduler_current", lambda a: True)
    monkeypatch.setattr(KW, "tool_skew_refuse", lambda *a, **k: False, raising=False)
    assert KW.launch(AP, cfg, {"items": {}, **st}, D, {"item": I, "block_sha": "b1"}, "hub") is None
    assert any("LAUNCH-HELD" in m and "BLOCKED-REPEAT" in m for m in AP.logs)


def test_queue_route_outcomes_reach_the_ledger(monkeypatch):
    class AP:
        logs, q = [], []
        log = staticmethod(lambda m: AP.logs.append(m))
        coord_append = staticmethod(lambda rel, line: AP.q.append(line))
    cfg = {"dies": {D: {"enabled": True}}}
    st = {}
    monkeypatch.setattr(KW, "file_sha", lambda *a, **k: "")
    for n in range(1, 4):
        KW.QUEUE_OUTCOMES.append(({"die": D, "item": I, "attempt": n, "block_sha": "b", "dir": "/x"}, "FAIL", "route", "CRASH", DRT % ("net25397", 1, 2, 3, 4)))
    KW.repeat_queue_outcomes(AP, cfg, st)
    assert RS.state_of(st, D, I)[0] == "BLOCKED-REPEAT" and len(AP.q) == 1 and KW.QUEUE_OUTCOMES == []


def test_class_relabel_keeps_the_streak_and_the_fail_key():
    # FLOW-NOADV-R2 11-20 (FABLE-FLOW-1200 class 7): UNCLASSIFIED -> PLAN -> INFRA on the same text is ONE cause: same retry key, same streak
    why = "AttributeError: module gen_phys has no attribute tap_3 (gen_phys.py)"
    assert KW.fail_key({"a": 1}, "UNCLASSIFIED", why) == KW.fail_key({"a": 1}, "PLAN", why)
    assert KW.fail_key({"a": 1}, "PLAN", why) != KW.fail_key({"a": 2}, "PLAN", why)                  # other inputs: another key
    assert KW.fail_key({"a": 1}, "PLAN", why) != KW.fail_key({"a": 1}, "PLAN", "KeyError: 'x' (gen_phys.py)")
    st = {}
    ev = [RS.record(st, D, "t1", n, "gen", cls, why) for n, cls in enumerate(["UNCLASSIFIED", "PLAN", "CRASH"], 1)]
    assert ev[-1] and ev[-1]["event"] == "BLOCKED-REPEAT"
    assert RS.ident("gen|PLAN|ValueError x") == RS.ident("gen|CRASH|ValueError x") != RS.ident("gen|PLAN|ValueError y")


def test_repeat_stop_refuses_with_stops_off_and_releases_on_a_new_input(monkeypatch, tmp_path):
    # FLOW-NOADV-R2 11-20 (COORD): sle_su_l0 relaunched unchanged 8 times because stops_off made REPEAT-STOP advisory
    class AP:
        logs, q = [], []
        log = staticmethod(lambda m: AP.logs.append(m))
        coord_append = staticmethod(lambda rel, line: AP.q.append(line))
        launched = []
    cfg = {"stops_off": True, "dies": {D: {"enabled": True, "event": "e", "owner_lane": "DIE-QC-103"}}}
    (tmp_path / "spec.json").write_text('{"src_sha": "s1", "tools_sha": "rt1"}')
    rec = {"die": D, "item": I, "block_sha": "b1", "dir": str(tmp_path)}
    monkeypatch.setattr(KW, "file_sha", lambda *a, **k: "")
    why = "plan contract metadata missing for this type @gen: ContractError: x.lib: no SIGNED mean clock contract"
    st = {}
    for n in range(1, 4):
        rec["attempt"] = n
        ev = RS.record(st, D, I, n, "gen", "PLAN", why, inputs=KW.repeat_inputs(cfg, rec, why), t=n)
        if ev:
            KW.repeat_event(AP, cfg, st, rec, ev)
    assert RS.state_of(st, D, I)[0] == "BLOCKED-REPEAT"
    monkeypatch.setattr(KW, "scheduler_current", lambda a: True)
    monkeypatch.setattr(KW, "tool_skew_refuse", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(KW, "rt_tools_fields", lambda c, d, root=None: {"tools_sha": "rt1"})
    same = {"items": {}, **st}
    assert KW.launch(AP, cfg, same, D, {"item": I, "block_sha": "b1"}, "hub") is None
    assert any("LAUNCH-HELD" in m and "BLOCKED-REPEAT" in m for m in AP.logs)
    # a new plan block, a new runtime each release it automatically (gate level: same inputs held, changed inputs released)
    cur = KW.repeat_inputs_now(cfg, st, D, I, "b1")
    assert RS.gate(st, D, I, cur)[0] is True
    st2 = json.loads(json.dumps(st))
    st3 = json.loads(json.dumps(st))
    assert RS.gate(st3, D, I, dict(cur, block="b2"))[2].startswith("inputs:block")
    monkeypatch.setattr(KW, "rt_tools_fields", lambda c, d, root=None: {"tools_sha": "rt2"})
    cur2 = KW.repeat_inputs_now(cfg, st2, D, I, "b1")
    assert cur2["tools"] == "rt2" and RS.gate(st2, D, I, cur2)[2].startswith("inputs:tools")


def test_station_row_overlap_plan_class_is_blocked_at_the_third():
    """FLOW-NOADV-R3 11-20: kit_istations cross-row site overlap (QC A4 st_a) is PLAN[design:station_overlap]; REPEAT-STOP holds it at the third"""
    line = ("kit_istations: sle_st_a_v1__cl989804f6__cled3c1d7b: station rows bus:rs_s0 and bus:rs_s1 claim overlapping sites "
            "(233.28, 522.72) / (233.28, 522.72) (%d overlaps); one site per flop across rows")
    st, evs = {}, []
    for n in range(1, 5):
        cls, why = KW.classify("kit_topology", line % (20 + n))                  # the overlap count changes: still one cause
        assert cls == "PLAN" and KW.typed_class(cls, "kit_topology", line % 20) == "design:station_overlap"
        full = f"{why} @kit_topology: {line % (20 + n)}"
        evs.append(RS.record(st, "qwen_compute", "sle_st_a_v1__cl989804f6__cled3c1d7b", n, "kit_topology", cls, full,
                             inputs={"block": "b1"}, t=1000 + n * 3600))
    assert [bool(e) for e in evs] == [False, False, True, False]
    assert evs[2]["event"] == "BLOCKED-REPEAT"
    assert RS.gate(st, "qwen_compute", "sle_st_a_v1__cl989804f6__cled3c1d7b", {"block": "b1"})[0] is True


def test_total_attempt_cap_stops_mixed_error_retries_per_event():
    """FLOW-NOADV-R4: S81-DIE-R5 saw a D8i svc row reach 22 attempts of mixed errors (no 3 identical in a row): the 6th failed attempt of one plan event blocks."""
    st = {}
    whys = ["KeyError: a%d (gen_phys.py)", "infra-oom: earlyoom killed the place unit", "ValueError: b%d (kit_wave.py)"]
    evs = [RS.record(st, D, I, n, "gen", "FLOW", whys[n % 3].replace("%d", str(n)), inputs={"block": "b1"}, t=n * 7200, event="E1") for n in range(1, 8)]
    capped = [e for e in evs if e and e["event"] == RS.CAP_STATE]
    assert len(capped) == 1 and evs[5] is capped[0] and "PLAN" in capped[0]["why"]
    # an input change does not release a cap stop
    assert RS.gate(st, D, I, {"block": "b2"}, event="E1")[0] is True
    # a new plan event does, and the count starts again
    assert RS.gate(st, D, I, {"block": "b2"}, event="E2") == (False, "", "")          # the ledger is keyed item@event: E2 starts clean
    assert RS.state_of(st, D, I, "E2") == ("", "") and RS.state_of(st, D, I, "E1")[0] == RS.CAP_STATE
    for n in range(8, 13):
        assert RS.record(st, D, I, n, "gen", "FLOW", "%s: z (x.py)" % ("KeyError", "ValueError", "OSError", "TypeError", "IndexError")[n - 8], t=n * 7200, event="E2") is None
    # an unblock line releases it too
    st2 = {}
    for n in range(1, 7):
        RS.record(st2, D, I, n, "gen", "FLOW", "%s: k (x.py)" % ("KeyError", "ValueError", "OSError", "TypeError", "IndexError", "EOFError")[n - 1], t=n, event="E1")
    assert RS.gate(st2, D, I, {}, unblocks=[(I, "*")], event="E1")[2] == "unblock"
    # the same attempt number counts once
    st3 = {}
    for _ in range(9):
        assert RS.record(st3, D, I, 1, "gen", "FLOW", "KeyError: q (x.py)", t=1, event="E1") is None


def test_tool_mix_infra_error_identical_on_two_attempts_stops_and_survives_the_infra_release():
    """FLOW-NOADV-R4 (COORD, leaf t28: 5 relaunches in 40 min of INFRA[tool_mix] ResetError at kit_rtl)"""
    st = {}
    why = "ResetError: reset identity differs (kit_rtl.py) tool skew"
    a = RS.record(st, D, I, 1, "kit_rtl", "INFRA", why, inputs={"block": "b1"}, t=1, event="E1", ident_n=RS.TOOL_MIX_IDENT_N)
    b = RS.record(st, D, I, 2, "kit_rtl", "INFRA", why, inputs={"block": "b1"}, t=2, event="E1", ident_n=RS.TOOL_MIX_IDENT_N)
    assert a is None and b and b["event"] == "BLOCKED-REPEAT"
    assert st["repeat_ledger"][RS.lkey(D, I, "E1")]["tool_mix"] is True
    assert RS.gate(st, D, I, {"block": "b1"}, event="E1")[0] is True
    assert RS.gate(st, D, I, {"block": "b2"}, event="E1")[0] is False           # an own-input change releases it
    assert "tool_mix" not in st["repeat_ledger"][RS.lkey(D, I, "E1")]
    # a different message does not stop at 2
    st2 = {}
    assert RS.record(st2, D, I, 1, "kit_rtl", "INFRA", "ResetError: a (x.py)", t=1, event="E1", ident_n=2) is None
    assert RS.record(st2, D, I, 2, "kit_rtl", "INFRA", "KeyError: b (y.py)", t=2, event="E1", ident_n=2) is None


def test_stops_and_counters_key_on_item_at_event():
    """FABLE-FLOW-2000 (a): 69 live item names exist on more than one event; a stop on D8i must not hit J5, and the reverse"""
    st = {}
    for n in range(1, 4):
        RS.record(st, D, I, n, "route", "CRASH", DRT % ("net1", 1, 2, 3, 4), inputs={"block": "b"}, t=n, event="D8i")
    assert RS.gate(st, D, I, {"block": "b"}, event="D8i")[0] is True
    assert RS.gate(st, D, I, {"block": "b"}, event="J5")[0] is False
    assert RS.state_of(st, D, I, "J5") == ("", "") and RS.state_of(st, D, I, "D8i")[0] == "BLOCKED-REPEAT"
    for n in range(1, 4):                                   # J5 counts its own attempts from zero
        assert RS.record(st, D, I, n, "route", "CRASH", ("KeyError: a (a.py)", "OSError: b (b.py)", "ValueError: c (c.py)")[n - 1], t=n, event="J5") is None
    # a legacy (die|item) stop recorded before the key carried the event still holds
    st2 = {"repeat_ledger": {D + "|" + I: {"att": [], "state": "BLOCKED-REPEAT", "fp": "x|y|z", "inputs": {"block": "b"}, "why": "old"}}}
    assert RS.gate(st2, D, I, {"block": "b"}, event="D8i")[0] is True


def test_cap_applies_to_rows_that_already_ran_many_attempts():
    """FABLE-FLOW-2000 (c): 78 live rows are at 10+ attempts (max 46): the next failure of such a row goes to its owner as PLAN, no ledger history needed"""
    st = {}
    ev = RS.record(st, D, I, 17, "gen", "FLOW", "KeyError: q (q.py)", t=1, event="E1", attempts_hint=17)
    assert ev and ev["event"] == RS.CAP_STATE and "17 failed attempts" in ev["why"]
    assert RS.record({}, D, I, 3, "gen", "FLOW", "KeyError: q (q.py)", t=1, event="E1", attempts_hint=3) is None
