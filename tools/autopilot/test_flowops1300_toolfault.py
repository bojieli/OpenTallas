"""FLOW-OPS-1300 (FABLE-FLOW-1240 a): a hub tool fault at `pipeline` (E2BIG on a pre-fix rt) neither counts in TOTAL_CAP nor holds CAUSE-CAP once the rt changed:
the relaunch runs rt/current.  The same fault twice on one rt still caps."""
import json
import kit_wave as KW
import repeat_stop as RS

E2BIG = "tool / Tcl error @pipeline: Traceback (most recent call last) OSError: [Errno 7] Argument list too long: 'ssh'"


def test_tool_fault_attempts_do_not_count_in_total_cap():
    st = {}
    for n in range(1, 9):
        ev = RS.record(st, "qwen_kvsys", "kv3_pv_v1", n, "pipeline", "FLOW", E2BIG + f" try {n}", inputs={"tools": f"rt{n}"}, t=n, event="D26")
        assert not ev or ev["event"] != RS.CAP_STATE
    assert RS.is_tool_fault("pipeline", "FLOW") and RS.is_tool_fault("pipeline", "INFRA") and not RS.is_tool_fault("route", "FLOW") and not RS.is_tool_fault("pipeline", "PLAN")


def test_a_tool_fault_cap_is_dropped_when_the_runtime_changes():
    e = {"state": RS.CAP_STATE, "fp": "cap|6 attempts", "inputs": {"tools": "4f638b4e9f8d"}, "att": [{"fp": "x"}], "tot": {"event": "D26", "n": [1, 2, 3, 4, 5, 6]},
         "why": "6 failed attempts in plan event D26 (one cause: pipeline|OSError [Errno N] Argument list too long: 'ssh'): PLAN item for the owner"}
    st = {"repeat_ledger": {RS.lkey("qwen_kvsys", "kv3_hg_v1p4", "D26"): dict(e)}}
    assert RS.gate(st, "qwen_kvsys", "kv3_hg_v1p4", {"tools": "4f638b4e9f8d"}, event="D26")[0]           # same rt: still capped
    assert RS.gate(st, "qwen_kvsys", "kv3_hg_v1p4", {"tools": "b6934d7751d6"}, event="D26")[0] is False
    st2 = {"repeat_ledger": {RS.lkey("s81", "t1", "E"): dict(e, why="6 failed attempts (one cause: route|DRT-0255 net x)", tot={"event": "E", "n": [1, 2, 3, 4, 5, 6]})}}
    assert RS.gate(st2, "s81", "t1", {"tools": "b6934d7751d6"}, event="E")[0]                          # a design cause: a runtime change does not release


def test_cause_cap_keys_a_tool_fault_by_the_attempt_runtime(tmp_path, monkeypatch):
    (tmp_path / "spec.json").write_text(json.dumps({"tools_sha": "4f638b4e9f8d0000"}))
    prev = {"item": "kv3_hg_v1p2", "attempt": 4, "dir": str(tmp_path), "stage": "pipeline", "class": "FLOW", "status": "FAIL", "reason": E2BIG, "block_sha": "abc"}
    monkeypatch.setattr(KW, "so_failed", lambda p: True)
    monkeypatch.setattr(KW, "die_owner", lambda *a, **k: ("KV-102",))
    cfg, st = {"dies": {"qwen_kvsys": {}}}, {"cause_retries": {}}
    monkeypatch.setattr(KW, "scheduler_rt", lambda root=None: ("/rt/b6934d7751d6", "b6934d7751d6aaaa"))
    for _ in range(3):                                                                 # pre-fix rt, current rt is newer: never held
        assert KW.cause_cap_held(cfg, st, "qwen_kvsys", prev) == ""
    monkeypatch.setattr(KW, "scheduler_rt", lambda root=None: ("/rt/4f638b4e9f8d", "4f638b4e9f8d0000"))
    assert KW.cause_cap_held(cfg, st, "qwen_kvsys", prev) == ""                         # same rt: one automatic relaunch
    assert KW.cause_cap_held(cfg, st, "qwen_kvsys", prev).startswith("CAUSE-CAP")      # then the cap
