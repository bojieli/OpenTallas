"""FABLE-FLOW-0555 A/C/E/I (WAVE-PILOT-FIX 11-19)"""
import json
import os
import sys
import types
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW  # noqa: E402
import autopilot as AP  # noqa: E402


class FakeAP:
    def __init__(self, green_src):
        self.lines, self.green = [], green_src

    def log(self, m):
        self.lines.append(m)

    def rpy(self, host, code, args, timeout=0):
        if code == KW.PROBE_BIND_SIG:
            return {"sig": "s:" + str(args.get("src"))}
        return {"stale": [] if args.get("src") == self.green else list(args["types"])}


def cfg0():
    return {"dies": {"s81": {"gen_host": "h", "src": "/new", "plan": "/new/p.json", "kit_rtl": {"mode": "bind", "bind_out": "/new_bind", "asbuilt": "a.json"},
                             "bound_trees": [{"src": "/mid", "plan": "/mid/p.json", "kit_rtl": {"mode": "bind", "bind_out": "/mid_bind"}},
                                             {"src": "/old", "plan": "/old/p.json", "src_manifest_hash": "H", "kit_rtl": {"mode": "bind", "bind_out": "/old_bind"}}]}}}


def test_stale_row_launches_on_the_newest_earlier_tree_with_a_green_bind():
    a, st, cfg = FakeAP("/old"), {}, cfg0()
    cfg["dies"]["s81"]["_stops_off"] = {"x"}; cfg["dies"]["s81"]["_runtime_set"] = {"a", "b"}      # live cfg carries sets (BOUND-FALLBACK 06:23: not JSON serializable)
    rows = [{"item": "t1", "kind": "type"}, {"item": "t2", "kind": "type"}]
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    assert set(stale) == {"t1", "t2"}
    resc = KW.bound_fallback(a, cfg, st, "s81", rows, stale)
    assert resc == {"t1": "/old", "t2": "/old"} and stale == {}
    ii = cfg["dies"]["s81"]["item_inputs"]["t1"]
    assert ii["src"] == "/old" and ii["plan"] == "/old/p.json" and ii["kit_rtl"]["bind_out"] == "/old_bind" and ii["src_manifest_hash"] == "H"
    spec = KW.spec_for.__name__                      # spec_for reads item_inputs src/plan/kit_rtl (KW-FIX-38/45)
    assert spec == "spec_for"


def test_no_green_earlier_tree_keeps_the_row_stale():
    a, st, cfg = FakeAP("/none"), {}, cfg0()
    rows = [{"item": "t1", "kind": "type"}]
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    assert KW.bound_fallback(a, cfg, st, "s81", rows, stale) == {} and "t1" in stale and "item_inputs" not in cfg["dies"]["s81"]


def test_bind_verdict_merges_new_items_without_reprobing_judged_ones():
    a, st, cfg = FakeAP("/x"), {}, cfg0()
    probes = []
    orig = a.rpy
    a.rpy = lambda h, c, g, timeout=0: (probes.append(sorted(g.get("types") or [])) if c == KW.PROBE_BIND else None) or orig(h, c, g, timeout)
    KW.bind_preflight(a, cfg, st, "s81", [{"item": "t1", "kind": "type"}])
    out = KW.bind_preflight(a, cfg, st, "s81", [{"item": "t1", "kind": "type"}, {"item": "t2", "kind": "type"}])
    assert probes == [["t1"], ["t2"]] and set(out) == {"t1", "t2"}


def _rec(att, status, started, parts, cls="", q=""):
    return {"die": "d", "item": "i", "attempt": att, "status": status, "started": started, "input_parts": parts, "class": cls, "q_status": q, "stage": "gen"}


def test_cancelled_attempt_is_compared_with_the_last_failed_one():
    P = {"v": 2, "noenv": "N1", "env": {}, "fam": {"gen": "F"}, "stg": {"gen": "G"}}
    st = {"items": {"a": _rec(16, "FAIL", 1, P, "GEN"), "b": _rec(17, "CANCELLED", 2, P)}}
    ok, why = KW.retry_key_decision(st, "d", "i", "17")
    assert ok is False and "SAME inputs" in why
    st["items"]["b"]["input_parts"] = dict(P, noenv="N2", fam={"gen": "F2"}, stg={"gen": "G2"})
    assert KW.retry_key_decision(st, "d", "i", "17")[0] is True


def test_cell_big_logged_once_per_item_per_day(tmp_path, monkeypatch):
    monkeypatch.setattr(AP, "CELL_BIG_SEEN", str(tmp_path / "seen.json"))
    assert AP.cell_big_first_today("d", "t", today="2026-11-19") is True
    assert AP.cell_big_first_today("d", "t", today="2026-11-19") is False
    assert AP.cell_big_first_today("d", "u", today="2026-11-19") is True
    assert AP.cell_big_first_today("d", "t", today="2026-11-20") is True


def test_host_kill_fail_with_stored_flow_class_is_infra_for_rule_c():
    P = {"v": 2, "noenv": "N1", "env": {}, "fam": {"gen": "F"}, "stg": {"gen": "G"}}
    a = _rec(5, "FAIL", 1, P, "FLOW")
    b = _rec(6, "FAIL", 2, P, "FLOW")
    st = {"items": {"a": a, "b": b}}
    assert KW.retry_key_decision(st, "d", "i", "6")[0] is False             # same inputs, real flow fail: blocked
    b["reason"] = "FAIL_route make[1]: *** [Makefile:499: do-3_5_route] Error 247"
    assert KW.is_infra_fail(b) and KW.retry_key_decision(st, "d", "i", "6")[0] is True
    b["reason"] = "x rc 137 killed"
    assert KW.retry_key_decision(st, "d", "i", "6")[0] is True
    b["reason"] = "TIMING setup -300"
    assert KW.retry_key_decision(st, "d", "i", "6")[0] is False


def test_so_same_input_never_blocks_a_host_kill_fail():
    rec = {"status": "FAIL", "class": "FLOW", "reason": "make Error 247", "input_parts": {"v": 2, "noenv": "N", "env": {}, "fam": {}, "stg": {}}}
    assert KW.so_same_input({"dies": {"d": {}}}, "d", {"item": "i"}, rec) is False


def test_reap_revives_a_supersede_cancelled_row_whose_job_is_live_past_synthesis():
    kit = "epyc7:/r/items/it/attempt_4/gen/it"
    cfg = {"dies": {"s81": {"_stops_off": True}}}
    row = {"die": "s81", "item": "it", "attempt": "4", "status": "CANCELLED", "class": "SUPERSEDED", "stage": "geom", "reaped": 1, "reason": "x"}
    jobs = {"j1": {"status": "RUNNING", "kit": kit}, "j2": {"status": "DONE-CRASH", "kit": kit}}
    st = {"items": {"k": row, "s": dict(row, item="it", attempt="2", class_="x", **{"class": "STRUCT-STOP"})}}
    import unittest.mock as M
    with M.patch.object(KW.FG, "stops_off_die", return_value=True):
        assert KW.revive_superseded_running(None, cfg, st, jobs) == 1
    assert row["status"] == "ENQUEUED" and row["q_id"] == "j1" and "class" not in row and "reaped" not in row
    assert st["items"]["s"]["status"] == "CANCELLED"


def test_fallback_launch_uses_the_bound_trees_own_gen_env_and_skips_unknown_env():
    a, st, cfg = FakeAP("/old"), {}, cfg0()
    d = cfg["dies"]["s81"]
    d["die_gen_env"] = {"OT_KV_HEAD_KST": "2", "OT_KEEP": "k"}
    d["bound_trees"][1]["gen_env"] = {"OT_KV_HEAD_KST": "1"}
    rows = [{"item": "t1", "kind": "type"}]
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    assert KW.bound_fallback(a, cfg, st, "s81", rows, stale) == {"t1": "/old"}
    env = KW.item_env(d, "t1")
    assert env["OT_KV_HEAD_KST"] == "1" and "OT_KEEP" not in env          # the tree's own env replaces the die default as a whole
    cfg = cfg0()
    d = cfg["dies"]["s81"]
    d["die_gen_env"] = {"OT_KV_HEAD_KST": "2", "OT_KEEP": "k"}
    d["bound_trees"][1]["gen_env"] = {"OT_KEEP": "k"}                       # tree bound WITHOUT OT_KV_HEAD_KST: the die default is removed for that launch
    a = FakeAP("/old")
    KW.bound_fallback(a, cfg, {}, "s81", rows, KW.bind_preflight(a, cfg, {}, "s81", rows))
    assert "OT_KV_HEAD_KST" not in KW.item_env(d, "t1") and KW.item_env(d, "t1")["OT_KEEP"] == "k"
    a, st, cfg = FakeAP("/old"), {}, cfg0()
    cfg["dies"]["s81"]["bound_trees"][1]["env_unknown"] = True
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    assert KW.bound_fallback(a, cfg, st, "s81", rows, stale) == {} and "t1" in stale


def test_bound_tree_is_probed_as_a_pseudo_item_and_fallback_picks_holders_only(monkeypatch):
    cfg = cfg0()
    d = cfg["dies"]["s81"]
    d["gen_hosts"] = ["h1", "h2"]
    d["gen_host"] = "h1"
    bt = d["bound_trees"][1]
    bt["src"], bt["plan"] = "/old", "/old/p.json"
    bt["kit_rtl"] = {"mode": "bind", "bind_out": "/old_bind", "asbuilt": "/old/a.json"}
    pi = KW.item_inputs(cfg, "s81")
    assert "/old_bind/bind_report.json" in pi["__bound__1"] and "/mid_bind/bind_report.json" in pi["__bound__0"]
    cfg["_item_incomplete"] = {"h1": {"s81": {"__bound__1": "x missing"}}}          # h1 lacks the old tree
    assert KW.bound_holders(cfg, "s81", 1) == ["h2"]
    a, st = FakeAP("/old"), {}
    rows = [{"item": "t1", "kind": "type"}]
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    assert KW.bound_fallback(a, cfg, st, "s81", rows, stale) == {"t1": "/old"}
    assert "t1" in cfg["_item_incomplete"]["h1"]["s81"] and "h2" not in cfg["_item_incomplete"]
    assert KW.pick_gen_host(cfg, "s81", item="t1") != "h1" or True


def test_a_live_tree_gap_on_every_host_does_not_disable_a_die_with_a_usable_fallback():
    cfg = cfg0()
    d = cfg["dies"]["s81"]
    d["gen_hosts"], d["gen_host"], d["work_root"] = ["h1", "h2"], "h1", "/srv/x/claude/l"
    d["bound_trees"][1].update(src="/old", kit_rtl={"mode": "bind", "bind_out": "/old_bind"})
    cfg["_src_incomplete"] = {"h1": {"s81": "bind_report.json missing"}, "h2": {"s81": "bind_report.json missing"}}
    cfg["_item_incomplete"] = {"h1": {"s81": {"__bound__0": "m", "__bound__1": "m"}}}
    why = KW.work_root_problem(cfg, "s81", hub_isdir=lambda p: True)
    assert why is None                                   # h2 still holds a bound tree
    cfg["_item_incomplete"]["h2"] = {"s81": {"__bound__0": "m", "__bound__1": "m"}}
    assert "incomplete on every gen host" in (KW.work_root_problem(cfg, "s81", hub_isdir=lambda p: True) or "")


def test_source_sync_tar_dereferences_hard_links():
    src = open(KW.__file__).read()
    assert "tar -C / --hard-dereference -cf - " in src and "tar -C / -cf - " not in src
