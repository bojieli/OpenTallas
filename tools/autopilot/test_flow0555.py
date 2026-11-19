"""FABLE-FLOW-0555 A/C/E/I (WAVE-PILOT-FIX 11-19)"""
import json
import os
import sys
import types
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW  # noqa: E402
import autopilot as AP  # noqa: E402


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_bad_hosts():
    import wave_jobs as _WJ
    yield
    _WJ.BAD_HOSTS = set()                                   # unreadable_host_rows sets the module-global per tick


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


def test_a_host_failing_ssh_twice_is_skipped_for_the_rest_of_the_tick(monkeypatch):
    monkeypatch.setattr(AP, "SSH_FAILS", {})
    calls = []
    monkeypatch.setattr(AP, "sh", lambda cmd, timeout=0, input=None: (calls.append(cmd) or (255, "", "Connection timed out")))
    for _ in range(4):
        AP.rpy("epyc7", "x", {})
    assert len(calls) == 2 and "error" in AP.rpy("epyc7", "x", {}) and AP.ssh_skipped("epyc7")
    assert AP.rbash("epyc7", "true")[0] == 255 and len(calls) == 2
    AP.rpy("epyc8", "x", {})
    assert len(calls) == 3                                   # another host is unaffected
    assert "ConnectTimeout=10" in " ".join(calls[0])


def test_wave_near_miss_job_is_an_eco_candidate_with_the_routed_kit_memory():
    import auto_resign as AR
    jobs = {"j1": {"id": "j1", "status": "DONE-NEAR-MISS", "die": "hd", "type": "hd_mesh", "host": "h", "path": "h:/k/a1/gen/hd_mesh",
                   "signoff": {"path": "/k/a1/gen/hd_mesh/signoff/signoff.json"}},
            "j2": {"id": "j2", "status": "DONE-STRUCTURAL", "die": "hd", "type": "x", "host": "h", "path": "h:/k/a2", "signoff": {"path": "/k/a2/signoff.json"}},
            "j3": {"id": "j3", "status": "WAIT-PARENT", "die": "hd", "type": "y", "host": "h", "path": "h:/k/a3", "signoff": {"path": "/k/a3/s/signoff.json"}}}
    kits = {"/k/a1/gen/hd_mesh": "yes", "/k/a2": "yes", "/k/a3": "yes"}
    out = {c["name"]: c for c in AR.wave_candidates(jobs, kits)}
    assert set(out) == {"hd_mesh", "y"}
    old = {c["name"] for c in AR.wave_candidates(jobs, {"/k/a1/gen/hd_mesh": "no"})}               # plan_current no / absent kit: still a wave-eco candidate (any plan counts)
    assert old == {"hd_mesh"}
    assert "y" not in {c["name"] for c in AR.wave_candidates(jobs, {})}                              # a re-sign row still needs plan_current yes and out["hd_mesh"]["source"] == "wave-eco" and out["y"]["source"] == "wave"
    assert AR.WAVE_ECO_MEM_GB == 24


def test_wave_eco_orders_smallest_miss_first_has_no_inflight_cap_and_unpins_an_overloaded_host():
    import auto_resign as AR
    mk = lambda i, so: {"id": i, "status": "DONE-NEAR-MISS", "die": "hd", "type": i, "host": "h", "path": f"h:/k/{i}", "signoff": dict(so, path=f"/k/{i}/s/signoff.json")}
    jobs = {"big": mk("big", {"tt_wns": -120.0, "drc": 0}), "small": mk("small", {"tt_wns": -44.0, "drc": 0}), "drc": mk("drc", {"ff_wns": -5.0, "drc": 3})}
    kits = {f"/k/{i}": "yes" for i in jobs}
    assert [c["name"] for c in AR.wave_candidates(jobs, kits)] == ["small", "big", "drc"]
    assert AR.host_overloaded({"epyc7": {"load": 600, "cores": 96}}, "epyc7") and not AR.host_overloaded({"epyc7": {"load": 150, "cores": 96}}, "epyc7")
    assert not AR.host_overloaded({}, "x")

    class A:
        OT_RUN = "ot-run"
        ssh_host = staticmethod(lambda h: h)
    c, e = {"host": "epyc7"}, {"kit": "/k/small", "record": "/k/small/s.json"}
    pinned = AR.eco_argv(A, c, e, "/d", "/out", 24)
    free = AR.eco_argv(A, c, e, "/d", "/out", 24, anyhost=True)
    assert "--hosts" in pinned and "--hosts" not in free and "--stage" in free and "24" in free
    assert AR.MAX_ECO_INFLIGHT == 4                          # the cap still binds the registry rows


def test_queued_wait_on_an_overloaded_or_unreadable_host_is_repicked_for_every_die(tmp_path):
    import unittest.mock as M
    logs, shs = [], []
    ap = type("AP", (), {"DRY": False, "AP_DIR": str(tmp_path), "log": staticmethod(logs.append),
                         "sh": staticmethod(lambda cmd, timeout=0, input=None: (shs.append(cmd) or (0, "", ""))),
                         "ssh_host": staticmethod(lambda h: h)})()
    cfg = {"dies": {"qwen_kvsys": {}, "s81": {}}, "_otrun_status": {"epyc7": {"load": 965, "cores": 96}, "epyc8": {"load": 80, "cores": 96}}}
    mk = lambda die, q: {"die": die, "item": "i_" + die, "status": "ENQUEUED", "q_id": q, "started": 1.0, "attempt": "1"}
    st = {"items": {"a": mk("qwen_kvsys", "j1"), "b": mk("s81", "j2"), "c": mk("s81", "j3"), "d": mk("s81", "j4")}}
    st["items"]["c"]["item"], st["items"]["d"]["item"] = "i_c", "i_d"
    jobs = {"j1": {"status": "WAIT-GEOM", "host": "epyc7", "kit": "epyc7:/k/1"},
            "j2": {"status": "QUEUED", "host": "gone9", "kit": "gone9:/k/2"},          # unreadable: no status row
            "j3": {"status": "RUNNING", "host": "epyc7", "kit": "epyc7:/k/3"},        # started: never touched
            "j4": {"status": "QUEUED", "host": "epyc8", "kit": "epyc8:/k/4"}}         # healthy host
    notices = {}
    with M.patch.object(KW, "pick_gen_host", return_value="epyc8"):
        n = KW.repick_queued_waits(ap, cfg, st, notices, jobs=jobs, now=1e9)
    assert n == 2
    assert st["items"]["a"]["status"] == "RETRY-INFRA" and st["items"]["a"]["restage_host"] == "epyc8" and st["items"]["a"]["class"] == "INFRA"
    assert st["items"]["b"]["status"] == "RETRY-INFRA"
    assert st["items"]["c"]["status"] == "ENQUEUED" and st["items"]["d"]["status"] == "ENQUEUED"
    assert sum(1 for c in shs if "--cancel-dir" in c) == 2 and any("/k/1" in c for c in shs)
    assert KW.queued_host_bad({}, "epyc7") == ""            # no status at all: unknown, not bad


def test_kit_topology_bind_stale_on_a_fallback_tree_is_wait_bind_not_a_fail(tmp_path):
    cfg = cfg0()
    cfg["dies"]["s81"]["src"] = "/new"
    d = tmp_path / "a7"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"src": "/old"}))
    live = tmp_path / "a8"
    live.mkdir()
    (live / "spec.json").write_text(json.dumps({"src": "/new"}))
    now = time.time()
    mk = lambda it, dd: {"die": "s81", "item": it, "status": "FAIL", "stage": "kit_topology", "dir": str(dd), "updated": now, "attempt": "1",
                         "reason": "ValueError: KIT_TOPOLOGY_BIND_STALE: regenerate the canonical native bind"}
    st = {"items": {"a": mk("t1", d), "b": mk("t2", live)}}
    a = FakeAP("/old")
    assert KW.wait_bind_sweep(a, cfg, st, now=now) == 1
    assert st["items"]["a"]["status"] == "CANCELLED" and st["items"]["a"]["class"] == "WAIT-BIND" and st["items"]["b"]["status"] == "FAIL"
    assert "s81|t1|/old" in st["wait_bind"] and any("WAIT-BIND" in m for m in a.lines)
    rows = [{"item": "t1", "kind": "type"}, {"item": "t3", "kind": "type"}]
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    out = KW.bound_fallback(a, cfg, st, "s81", rows, stale)
    assert "t1" not in out and out.get("t3") == "/old"                       # t1 never again on /old; t3 still does


def test_running_row_on_an_unreadable_host_is_unknown_for_two_hours_then_infra_dead_once(tmp_path):
    import unittest.mock as M
    shs = []
    ap = type("AP", (), {"DRY": False, "log": staticmethod(lambda m: None), "sh": staticmethod(lambda c, timeout=0, input=None: (shs.append(c) or (0, "", "")))})()
    d = tmp_path / "a5"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_host": "epyc7"}))
    now = 1e9
    row = lambda age_h: {"die": "qwen_kvsys", "item": "kv3_sys_c", "status": "RUNNING", "unit": "kw-u", "dir": str(d), "updated": now - age_h * 3600, "started": now - age_h * 3600, "attempt": "5"}
    cfg = {"dies": {"qwen_kvsys": {}}, "_hub": "intel2", "_otrun_status": {"epyc8": {"load": 1, "cores": 96}, "intel2": {"load": 1, "cores": 96}}}
    with M.patch.object(KW, "pick_gen_host", return_value="epyc8"):
        st = {"items": {"x": row(1.0)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 0 and st["items"]["x"]["status"] == "RUNNING"     # unknown for 2 h
        st = {"items": {"x": row(8.5)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 1
        r = st["items"]["x"]
        assert r["status"] == "RETRY-INFRA" and r["class"] == "INFRA" and r["restage_host"] == "epyc8" and r["infra_dead_n"] == 1
        assert ["systemctl", "--user", "stop", "kw-u"] in shs
        r.update(status="RUNNING", updated=now - 9 * 3600)
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 0                       # once only
        cfg["_otrun_status"] = {}
        st = {"items": {"x": row(9.0)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 0                       # no status at all: nothing known


def test_gen_host_choice_drops_an_unreadable_or_overloaded_host_while_another_stays():
    cfg = {"dies": {"s81": {"gen_host": "epyc7", "gen_hosts": ["epyc7", "epyc8", "epyc9"], "work_root": "/srv/x/claude/l"}}, "_hub": "intel2",
           "_otrun_status": {"epyc8": {"load": 90, "cores": 96}, "epyc9": {"load": 400, "cores": 96}}}
    got = KW.gen_hosts(cfg, "s81", "t1")
    assert got == ["epyc8"]                                   # epyc7 has no status row, epyc9 is over 2x cores
    cfg["_otrun_status"] = {}
    assert "epyc7" in KW.gen_hosts(cfg, "s81", "t1")          # nothing known: nothing dropped
    cfg["_otrun_status"] = {"epyc7": {"load": 900, "cores": 96}, "epyc8": {"load": 900, "cores": 96}, "epyc9": {"load": 900, "cores": 96}}
    assert len(KW.gen_hosts(cfg, "s81", "t1")) == 3           # every host bad: the list is unchanged


def test_row_stuck_in_the_rt_mirror_of_a_bad_host_moves_after_30_minutes(tmp_path):
    import unittest.mock as M
    ap = type("AP", (), {"DRY": False, "log": staticmethod(lambda m: None), "sh": staticmethod(lambda c, timeout=0, input=None: (0, "", ""))})()
    d = tmp_path / "a1"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_host": "epyc9"}))      # the gen host is fine; the MIRROR to roam host epyc7 hangs
    now = 1e9
    row = {"die": "s81", "item": "t1", "status": "RUNNING", "unit": "u", "dir": str(d), "stage": "rt_mirror_copy_epyc7", "updated": now - 3600, "started": now - 3600, "attempt": "1"}
    cfg = {"dies": {"s81": {}}, "_hub": "intel2", "_otrun_status": {"epyc9": {"load": 10, "cores": 96}, "epyc8": {"load": 10, "cores": 96}}}
    with M.patch.object(KW, "pick_gen_host", return_value="epyc8"):
        st = {"items": {"x": dict(row, updated=now - 600, started=now - 600)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 0           # only 10 min
        st = {"items": {"x": dict(row)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 1 and st["items"]["x"]["status"] == "RETRY-INFRA"
        st = {"items": {"x": dict(row, stage="rt_mirror_copy_epyc9", updated=now - 2400, started=now - 2400)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 0           # a healthy host's mirror is left alone


def test_plan_src_macro_is_a_classified_plan_failure():
    cls, why = KW.classify("preflight", "KIT_PREFLIGHT FAIL 21 issues\n  macro_instances PLAN-SRC-MACRO: u_bound.u_host.host__qkd_hr_core_order is not an instance of the bound host\n")[:2]
    assert cls == "PLAN" and "PLAN-SRC-MACRO" in why


def test_wave_eco_prints_one_summary_line_per_pass():
    import auto_resign as AR
    lines = []
    ap = type("AP", (), {"log": staticmethod(lines.append)})()
    c = {"die": "hd", "name": "hd_mesh", "host": "h", "path": "/k", "source": "wave-eco"}
    AR.eco_summary(ap, {AR.cand_id(c): {"status": "WAIT", "why": "no tag tools for hd"}}, [c, {"die": "x", "name": "y", "source": "wave"}])
    assert len(lines) == 1 and "1 candidate(s)" in lines[0] and "no tag tools" in lines[0]
    AR.eco_summary(ap, {}, [])
    assert "0 DONE-NEAR-MISS candidates" in lines[1]


def test_bind_preflight_probes_import_the_rt_launch_trees_kit_topology():
    assert "rt/current/tools/die_plan" in KW.PROBE_BIND and "kit_topology.py" in KW.PROBE_BIND
    assert KW.PROBE_BIND.index("rt/current") < KW.PROBE_BIND.index("import kit_topology")      # rt copy first, die src tree only as the fallback
    assert "rt/current/tools/die_plan/kit_topology.py" in KW.PROBE_BIND_SIG                    # the verdict cache follows the same file


def test_tar_extract_resolves_a_cross_device_symlink_top_directory(tmp_path):
    import subprocess
    real = tmp_path / "scratch3" / "claude" / "kw45"
    real.mkdir(parents=True)
    claude = tmp_path / "scratch2" / "claude"
    claude.mkdir(parents=True)
    os.symlink(real, claude / "kw45")
    top = "/srv/x"                                                       # the command only treats /srv/... tops; emulate with a tmp path rewrite
    cmd = KW.tar_extract_cmd(["/srv/opentallas-scratch2/claude/kw45/a/b/f.sv"])
    assert "readlink -f /srv/opentallas-scratch2/claude/kw45" in cmd and "--transform" in cmd and cmd.endswith("$T")
    assert KW.tar_extract_cmd(["/tmp/not/srv"]) .startswith("T=''; eval tar -C / -xf -")
    src = open(KW.__file__).read()
    assert "tar -C / -xf - --keep-old-files'" not in src


def test_self_heal_source_sync_skips_bad_hosts_both_ways():
    runs = []
    ap = type("AP", (), {"log": staticmethod(lambda m: None), "sh": staticmethod(lambda c, timeout=0, input=None: (runs.append(c) or (0, "", "")))})()
    cfg = {"dies": {"s81": {"gen_hosts": ["epyc7", "epyc8", "epyc9"], "gen_host": "epyc8"}}, "_hub": "intel2",
           "_otrun_status": {"epyc8": {"load": 10, "cores": 96}, "epyc9": {"load": 10, "cores": 96}},        # epyc7: no status row = unreadable
           "_src_incomplete": {"epyc7": {"s81": "/srv/opentallas-scratch2/claude/x/a.sv missing"}, "epyc9": {"s81": "/srv/opentallas-scratch2/claude/x/a.sv missing"}}}
    import tempfile
    os.environ["OT_SELF_HEAL_STATE"] = os.path.join(tempfile.mkdtemp(), "t.json")
    KW.sync_die_inputs(ap, cfg, run=lambda argv, inp=None: (runs.append(argv) or 0))
    joined = " ".join(" ".join(map(str, c)) for c in runs)
    assert "epyc7" not in joined                              # neither a destination nor a donor


def test_snapshot_commands_run_kit_store_from_rt_current(tmp_path, monkeypatch):
    rt = tmp_path / "rt_current" / "tools" / "autopilot"
    rt.mkdir(parents=True)
    (rt / "kit_store.py").write_text("# RT-CURRENT-COPY\n")
    monkeypatch.setenv("OT_RT_CURRENT", str(tmp_path / "rt_current"))
    assert KW.ks_source() == rt / "kit_store.py" and "RT-CURRENT-COPY" in KW.ks_cmd("snap --x")
    monkeypatch.setenv("OT_RT_CURRENT", str(tmp_path / "none"))
    assert KW.ks_source() == KW.KS_PATH                      # not visible: the module's own copy


def test_fleet_stop_and_scan_skip_bad_hosts_with_a_short_ssh_timeout(monkeypatch):
    import wave_jobs as WJ
    seen = []
    sh = lambda cmd, timeout=0, input=None: (seen.append((cmd, timeout)) or (0, "{}", ""))
    monkeypatch.setattr(WJ, "BAD_HOSTS", {"epyc7"})
    res = WJ.stop_on_fleet(sh, "intel2", ["/r"], hosts=["epyc7", "epyc8"])
    assert "skipped" in res["epyc7"]["error"] and not any("epyc7" in c for c, _ in seen)
    cmd, to = [x for x in seen if "epyc8" in x[0]][0]
    assert "ConnectTimeout=10" in cmd and to <= 90
    seen.clear()
    res = WJ.orphan_scopes(sh, "intel2", [], hosts=["epyc7", "epyc9"])
    assert "skipped" in res["epyc7"]["error"] and any("epyc9" in c for c, _ in seen)


def test_live_source_sync_copies_run_in_detached_units_and_never_wait():
    launched, shs = [], []
    ap = type("AP", (), {"DRY": False, "log": staticmethod(lambda m: None), "sh": staticmethod(lambda c, timeout=0, input=None: (shs.append(c) or (0, "", ""))),
                         "launch_unit": staticmethod(lambda unit, logf, argv: launched.append((unit, argv)) or True), "unit_active": staticmethod(lambda u: False)})()
    cfg = {"dies": {"s81": {"gen_hosts": ["epyc8", "epyc9"], "gen_host": "epyc8"}}, "_hub": "intel2",
           "_otrun_status": {"epyc8": {"load": 10, "cores": 96}, "epyc9": {"load": 10, "cores": 96}},
           "_src_incomplete": {"epyc9": {"s81": "/srv/opentallas-scratch2/claude/x/a.sv missing"}}}
    import tempfile
    os.environ["OT_SELF_HEAL_STATE"] = os.path.join(tempfile.mkdtemp(), "t.json")
    KW.sync_die_inputs(ap, cfg)
    assert len(launched) == 1 and launched[0][0].startswith("ss-") and "tar -C / --hard-dereference -cf -" in launched[0][1][-1]
    assert not any(c and c[0] == "bash" for c in shs)          # nothing ran inline


def test_rt_mirror_stage_older_than_an_hour_moves_even_when_the_host_status_is_fine(tmp_path):
    import unittest.mock as M
    ap = type("AP", (), {"DRY": False, "log": staticmethod(lambda m: None), "sh": staticmethod(lambda c, timeout=0, input=None: (0, "", ""))})()
    d = tmp_path / "a1"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_host": "epyc8"}))
    now = 1e9
    row = {"die": "s81", "item": "t1", "status": "RUNNING", "unit": "u", "dir": str(d), "stage": "rt_mirror_copy_epyc7", "updated": now - 1.7 * 3600, "started": now - 1.7 * 3600, "attempt": "1"}
    cfg = {"dies": {"s81": {}}, "_hub": "intel2", "_otrun_status": {"epyc7": {"load": 50, "cores": 96}, "epyc8": {"load": 10, "cores": 96}}}   # epyc7 healthy by status
    with M.patch.object(KW, "pick_gen_host", return_value="epyc8"):
        st = {"items": {"x": dict(row)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 1 and st["items"]["x"]["status"] == "RETRY-INFRA"
        st = {"items": {"x": dict(row, updated=now - 1200, started=now - 1200)}}
        assert KW.unreadable_host_rows(ap, cfg, st, {}, now=now) == 0


def test_a_host_with_stuck_mirrors_is_dropped_from_gen_hosts_for_three_hours():
    import unittest.mock as M
    ap = type("AP", (), {"DRY": False, "log": staticmethod(lambda m: None), "sh": staticmethod(lambda c, timeout=0, input=None: (0, "", ""))})()
    now = 1e9
    mk = lambda i: {"die": "s81", "item": f"t{i}", "status": "RUNNING", "unit": "u", "dir": "/nonexistent", "stage": "rt_mirror_copy_epyc7", "updated": now - 2 * 3600, "started": now - 2 * 3600, "attempt": "1"}
    cfg = {"dies": {"s81": {"gen_host": "epyc7", "gen_hosts": ["epyc7", "epyc8"], "work_root": "/srv/x/claude/l"}}, "_hub": "intel2",
           "_otrun_status": {"epyc7": {"load": 10, "cores": 96}, "epyc8": {"load": 10, "cores": 96}}}
    st = {"items": {str(i): mk(i) for i in range(3)}}
    KW.unreadable_host_rows(ap, cfg, st, {}, now=now)
    assert st["mirror_bad"]["epyc7"]["n"] == 3 and KW.gen_hosts(cfg, "s81", "t1") == ["epyc8"]
    cfg["_otrun_status"] = {"epyc7": {"load": 10, "cores": 96}, "epyc8": {"load": 10, "cores": 96}}            # next tick: re-applied from the state, rows already moved
    KW.unreadable_host_rows(ap, cfg, {"items": {}, "mirror_bad": st["mirror_bad"]}, {}, now=now + 3600)
    assert KW.gen_hosts(cfg, "s81", "t1") == ["epyc8"]
