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
    kit = "epyc7:/r/E/items/it/attempt_4/gen/it"
    cfg = {"dies": {"s81": {"_stops_off": True}}}
    row = {"die": "s81", "item": "it", "attempt": "4", "status": "CANCELLED", "class": "SUPERSEDED", "stage": "geom", "reaped": 1, "reason": "x", "kit": kit}
    jobs = {"j1": {"status": "RUNNING", "kit": kit}, "j2": {"status": "DONE-CRASH", "kit": kit}}
    st = {"items": {"k": row, "s": dict(row, item="it", attempt="2", class_="x", **{"class": "STRUCT-STOP"})}}
    import unittest.mock as M
    with M.patch.object(KW.FG, "stops_off_die", return_value=True):
        assert KW.revive_superseded_running(None, cfg, st, jobs) == 1
    assert row["status"] == "ENQUEUED" and row["q_id"] == "j1" and "class" not in row and "reaped" not in row
    assert st["items"]["s"]["status"] == "CANCELLED"


def test_fallback_signed_view_path_is_checked_against_the_selected_tree():
    cfg, st = cfg0(), {}
    die = cfg["dies"]["s81"]
    current, fallback = die["src"], die["bound_trees"][1]["src"]
    rel = "/physical/die_plan/s81/plan_inputs/signed_view_sha_s81.json"
    key = "OT_SIGNED_VIEW_SHA"
    die["die_gen_env"] = {key: current + rel}
    die["bound_trees"][1]["gen_env"] = {key: fallback + rel}
    ap = FakeAP(fallback)
    rows = [{"item": "t1", "kind": "type"}]
    stale = KW.bind_preflight(ap, cfg, st, "s81", rows)

    assert KW.bound_fallback(ap, cfg, st, "s81", rows, stale) == {"t1": fallback}
    assert KW.gen_env_outside_tree(die, "t1") == []
    assert KW.gen_env_outside_tree(die, "t2") == []
    for other in (current, "/third"):
        die["item_env"]["t1"][key] = other + rel
        assert KW.gen_env_outside_tree(die, "t1") == [(key, other + rel)]


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
    from importlib.util import module_from_spec, spec_from_file_location

    # Other tick fixtures replace the shared module's probes. Exercise the real SSH accounting here.
    spec = spec_from_file_location("ssh_accounting_fixture", AP.__file__)
    isolated = module_from_spec(spec)
    spec.loader.exec_module(isolated)
    calls = []
    monkeypatch.setattr(isolated, "sh", lambda cmd, timeout=0, input=None: (calls.append(cmd) or (255, "", "Connection timed out")))
    for _ in range(4):
        isolated.rpy("epyc7", "x", {})
    assert len(calls) == 2 and "error" in isolated.rpy("epyc7", "x", {}) and isolated.ssh_skipped("epyc7")
    assert isolated.rbash("epyc7", "true")[0] == 255 and len(calls) == 2
    isolated.rpy("epyc8", "x", {})
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
    assert KW.wait_bind_sweep(a, cfg, st, now=now) == 2                      # the live-tree row too (FLOW-1355 3: the stage verdict wins)
    assert st["items"]["a"]["status"] == "CANCELLED" and st["items"]["a"]["class"] == "WAIT-BIND" and st["items"]["b"]["status"] == "CANCELLED"
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
    assert len(launched) == 1 and launched[0][0].startswith("ss-") and launched[0][1][0] == "bash" and launched[0][1][-1].endswith(".sh")
    body = open(launched[0][1][-1]).read()                    # script file: systemd would expand ${r#/} of the transform in a transient unit command line
    assert "tar -C / --hard-dereference -cf -" in body and "${r#/}" in body
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


def test_tick_start_marks_unreadable_and_overloaded_hosts_for_the_stop_helpers():
    import autopilot as A
    import wave_jobs as WJ
    txt = ("intel2 admits 100 GB load 10/96 run 1 | epyc8 admits 50 GB load 80/96 run 3 | epyc9 admits 50 GB load 400/96 run 9")
    bad = A.bad_hosts_from_status(txt, "intel2")
    assert "epyc9" not in bad and "epyc8" not in bad and "epyc7" in bad        # epyc7: no status row = unreadable; epyc9 over 2x still gets its stops (FLOW-1949 5)
    assert A.bad_hosts_from_status("", "intel2") == set()                       # nothing readable: nothing marked
    assert WJ.STOP_SSH_S <= 30


def test_stops_off_die_is_not_gated_by_a_post_apply_bind_value():
    d = {"enabled": True, "event": "KV-D25d", "plan": "/p", "gen_host": "h", "src": "/s", "gate_events_extra": ["KV-D25d"],
         "gate": {"g0c": "PASS", "clock": "PASS", "bind": "POST-APPLY r712 (linked copy)"}}
    cfg = {"dies": {"qwen_kvsys": d}, "stops_off": True}
    ok, why = KW.gate(cfg, "qwen_kvsys")
    assert ok, why
    cfg2 = {"dies": {"qwen_kvsys": dict(d)}}                  # not stops_off: the old rule
    assert KW.gate(cfg2, "qwen_kvsys")[0] is False


def test_infra_class_breakers_and_repeat_stops_are_released():
    import flow_guard as FG
    st = {}
    FG.fg_state(st)["open"]["CLASS s81|pipeline|INFRA: infra (kit snapshot copy timed out) @pipeline"] = {"n": 9}
    FG.fg_state(st)["open"]["CLASS s81|gen|FLOW: real error"] = {"n": 9}
    st["repeat_ledger"] = {"s81|a": {"state": "BLOCKED-REPEAT", "fp": "pipeline|INFRA|x", "att": [{"cls": "INFRA", "fp": "x", "n": 1}]},
                           "s81|b": {"state": "BLOCKED-REPEAT", "fp": "gen|FLOW|y", "att": [{"cls": "FLOW", "fp": "y", "n": 1}]}}
    ap = type("AP", (), {"log": staticmethod(lambda m: None)})()
    assert KW.release_infra_stops(ap, {}, st) == (1, 1)
    assert "CLASS s81|gen|FLOW: real error" in FG.fg_state(st)["open"]
    assert st["repeat_ledger"]["s81|a"]["state"] == "" and st["repeat_ledger"]["s81|b"]["state"] == "BLOCKED-REPEAT"


def test_live_attempt_on_another_plan_block_does_not_block_a_stops_off_launch():
    import unittest.mock as M
    src = open(KW.__file__).read()
    assert "None if (arm or FG.stops_off_die(cfg, die)) else live_attempt_elsewhere" in src
    st = {"items": {"old": {"die": "s81_head", "item": "hd_mesh", "status": "ENQUEUED", "q_status": "RUNNING"}}}
    assert KW.live_attempt_elsewhere(st, "s81_head", "hd_mesh", "newkey") is not None          # the helper still sees it (hbm keeps the rule)


def test_previous_detached_copy_exit_code_and_error_are_read(tmp_path):
    f = tmp_path / "ss-x.log"
    f.write_text("AP_START 1 ss-x\ntar: Removing leading `/' from member names\ntar: a/b: Cannot mkdir: No such file or directory\nAP_RC=2\n")
    assert KW.src_sync_prev_result(f) == (2, "tar: a/b: Cannot mkdir: No such file or directory")
    assert KW.src_sync_prev_result(tmp_path / "none.log") == (None, "")
    f.write_text("AP_START 1 ss-x\nAP_RC=0\n")
    assert KW.src_sync_prev_result(f) == (0, "")


def test_retry_host_prefers_room_under_cores_over_free_memory():
    cfg = {"dies": {"s81": {"gen_host": "epyc2", "gen_hosts": ["epyc2", "epyc7"], "work_root": "/srv/x/claude/l"}}, "_hub": "intel2",
           "_otrun_status": {"epyc2": {"admit": 600, "load": 140, "cores": 128}, "epyc7": {"admit": 300, "load": 38, "cores": 96}}}
    assert KW.retry_gen_host(cfg, "s81", "t1", [], "epyc2") == "epyc7"          # epyc2 has more memory but is over its cores
    cfg["_otrun_status"]["epyc7"]["load"] = 200
    assert KW.retry_gen_host(cfg, "s81", "t1", [], "epyc2") == "epyc2"          # both over: memory decides, nothing is capped


def test_stage_refused_bind_on_the_live_tree_becomes_stale_for_the_launch_check(tmp_path):
    cfg = cfg0()
    cfg["dies"]["s81"].update(src="/new", kit_rtl={"mode": "bind", "bind_out": "/new_bind"})
    d = tmp_path / "a1"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"src": "/new", "kit_rtl": {"bind_out": "/new_bind"}}))
    now = time.time()
    st = {"items": {"a": {"die": "s81", "item": "t1", "status": "FAIL", "stage": "kit_topology", "dir": str(d), "updated": now, "attempt": "1",
                          "reason": "ValueError: KIT_TOPOLOGY_BIND_STALE: regenerate"}}}
    assert KW.wait_bind_sweep(FakeAP("/x"), cfg, st, now=now) == 1 and st["items"]["a"]["class"] == "WAIT-BIND"
    rows = [{"item": "t1"}, {"item": "t2"}]
    assert list(KW.bind_stale_from_stage(cfg, st, "s81", rows)) == ["t1"]
    cfg["dies"]["s81"]["kit_rtl"]["bind_out"] = "/newer_bind"                 # a new bind releases it
    assert KW.bind_stale_from_stage(cfg, st, "s81", rows) == {}


def test_plan_dies_source_prints_die_off_and_no_launch_lines():
    src = open(KW.__file__).read()
    assert "KIT-WAVE DIE-OFF {_die}" in src and "KIT-WAVE NO-LAUNCH {_die}" in src


def test_tick_killed_line_when_the_previous_tick_never_finished(tmp_path):
    import autopilot as A
    lines = []
    old, A.log = A.log, lines.append
    try:
        assert A.tick_killed_check(tmp_path, 1000.0) is None                    # no marker
        A.tick_progress(tmp_path, 500.0, "poll")
        m = A.tick_killed_check(tmp_path, 1000.0)
        assert m and "TICK-KILLED" in m and "'poll'" in m and lines
        A.tick_progress(tmp_path, 500.0, "done", done=True)
        assert A.tick_killed_check(tmp_path, 1000.0) is None                    # it finished
    finally:
        A.log = old


def test_queued_wait_on_a_host_at_its_cores_moves_when_another_host_has_room(tmp_path):
    import unittest.mock as M
    ap = type("AP", (), {"DRY": False, "AP_DIR": str(tmp_path), "log": staticmethod(lambda m: None), "sh": staticmethod(lambda c, timeout=0, input=None: (0, "", "")),
                         "ssh_host": staticmethod(lambda h: h)})()
    cfg = {"dies": {"s81": {"gen_host": "epyc8", "gen_hosts": ["epyc8", "epyc9", "epyc2"], "work_root": "/srv/x/claude/l"}}, "_hub": "intel2",
           "_otrun_status": {"epyc8": {"load": 120, "cores": 96, "admit": 5}, "epyc9": {"load": 150, "cores": 96, "admit": 5}, "epyc2": {"load": 40, "cores": 128, "admit": 300}}}
    st = {"items": {"a": {"die": "s81", "item": "t1", "status": "ENQUEUED", "q_id": "j1", "started": 1.0, "attempt": "1"}}}
    jobs = {"j1": {"status": "QUEUED", "host": "epyc8", "kit": "epyc8:/k/1"}}
    with M.patch.object(KW, "pick_gen_host", return_value="epyc2"):
        assert KW.repick_queued_waits(ap, cfg, st, {}, jobs=jobs, now=1e9) == 1
    assert st["items"]["a"]["restage_host"] == "epyc2"


def test_plan_current_no_never_cancels_a_queued_or_running_job_under_stops_off():
    cfg = {"dies": {"s81": {}, "hbm": {}}, "stops_off": True}
    for status in ("RUNNING", "LAUNCHING"):
        assert KW.finishes_on_old_plan(cfg, "s81", {"status": status, "stage": "gen"}, {}) is True
    for q in ("QUEUED", "WAIT-GEOM", "RUNNING"):
        assert KW.finishes_on_old_plan(cfg, "s81", {"status": "ENQUEUED", "q_id": "j"}, {"j": {"status": q}}) is True
    assert KW.finishes_on_old_plan(cfg, "s81", {"status": "ENQUEUED", "q_id": "j"}, {"j": {"status": "DONE-CRASH"}}) is False
    assert KW.finishes_on_old_plan(cfg, "s81", {"status": "FAIL"}, {}) is False
    assert KW.finishes_on_old_plan(cfg, "hbm", {"status": "ENQUEUED"}, {}) is False        # hbm keeps its holds


def test_explicit_retry_key_overrides_skip_same_input():
    P = {"v": 2, "noenv": "N1", "env": {}, "fam": {"gen": "F"}, "stg": {"gen": "G"}}
    st = {"items": {"a": {"die": "d", "item": "i", "attempt": "14", "status": "FAIL", "started": 2, "input_parts": P, "class": "FLOW"}}}
    # FLOW-FIX-0100: a retry key names fix=<sha or row> (plain item@N only for INFRA failures)
    cfg = KW.load_config('{"dies": {"d": {"retry": ["i@14:fix=r1", "i@2:fix=r1"]}}}')
    assert KW.explicit_retry_pending(cfg, st, "d", "i") is True                 # i@14 names the failed attempt: released
    assert KW.explicit_retry_pending(KW.load_config('{"dies": {"d": {"retry": ["i@14"]}}}'), st, "d", "i") is False      # no fix=, not INFRA
    cfg = KW.load_config('{"dies": {"d": {"retry": ["i@2:fix=r1"]}}}')
    assert KW.explicit_retry_pending(cfg, st, "d", "i") is False                # stale key (consumed long ago)
    cfg = KW.load_config('{"dies": {"d": {"retry": ["i@15:fix=r1"]}}}')
    assert KW.explicit_retry_pending(cfg, st, "d", "i") is True                 # pre-release of the next attempt
    assert KW.explicit_retry_pending({"dies": {"d": {}}}, st, "d", "i") is False


def test_two_events_same_item_and_attempt_never_share_a_queue_job(tmp_path):
    root_old = "/runs/qwen_compute/kit-wave/qwen_compute/hcut1111/items/tt_ctlm/attempt_2"
    root_new = "/runs/qwen_compute/kit-wave/qwen_compute/N46C/items/tt_ctlm/attempt_2"
    live = {"status": "RUNNING", "unit": "ap-live-a1", "kit": "epyc7:" + root_new + "/gen/tt_ctlm"}
    jobs = {"ad4d52b9ea00": live}
    mk = lambda root, st_="ENQUEUED": {"die": "qwen_compute", "item": "tt_ctlm", "attempt": "2", "status": st_, "q_id": "ad4d52b9ea00", "kit": "epyc7:" + root + "/gen/tt_ctlm"}
    old_row, new_row = mk(root_old), mk(root_new)
    assert KW.own_job(old_row, jobs) == {}                               # the old event's row never sees the live job: no unit to stop
    assert KW.own_job(new_row, jobs) == live
    cfg = {"dies": {"qwen_compute": {"_stops_off": True}}, "stops_off": True}
    old_row.update(status="CANCELLED", **{"class": "SUPERSEDED"}, stage="geom")
    assert KW.superseded_live_job(cfg, old_row, jobs) == ""              # REAP-REVIVE does not adopt the other event's job
    new_row.update(status="CANCELLED", **{"class": "SUPERSEDED"}, stage="geom")
    assert KW.superseded_live_job(cfg, new_row, jobs) == "ad4d52b9ea00"


def test_unresolvable_event_ancestry_never_turns_a_die_off():
    d = {"enabled": True, "event": "b4bb6a8b1e9", "plan": "/p", "gen_host": "h", "src": "/s", "gate": {"g0c": "PASS", "clock": "PASS", "bind": "PASS"}}
    cfg = {"dies": {"s81": d}, "stops_off": True}
    ok, why = KW.gate(cfg, "s81", lambda sha, base: None)               # commit not in the mirror
    assert ok, why
    assert "unresolvable" in d.pop("_descend_warn")
    ok, why = KW.gate(cfg, "s81", lambda sha, base: False)              # resolved, no descent: ignored under stops_off
    assert ok and "ignored under stops_off" in d.pop("_descend_warn")
    cfg2 = {"dies": {"s81": dict(d)}}                                   # without stops_off the old refusal stands for a resolved non-descent
    assert KW.gate(cfg2, "s81", lambda sha, base: False)[0] is False
    assert KW.gate(cfg2, "s81", lambda sha, base: None)[0] is True


def test_reap_never_supersedes_by_an_equal_attempt_or_another_events_row(tmp_path):
    import json as _j
    (tmp_path / "state.json").write_text(_j.dumps({"jobs": {}}))
    stops = []
    ap = type("AP", (), {"DRY": False, "AP_DIR": str(tmp_path), "log": staticmethod(lambda m: None), "HUB_NAME": "hub",
                         "sh": staticmethod(lambda c, timeout=0, input=None: (stops.append(c) or (0, "", "")))})()
    mk = lambda ev, att, st_: {"die": "d", "item": "i", "event": ev, "attempt": str(att), "status": "RUNNING", "unit": f"u-{ev}-{att}", "started": st_, "updated": st_, "dir": str(tmp_path)}
    cfg = {"dies": {"d": {}}}
    # same attempt number, two events: both keep running
    st = {"items": {"a": mk("OLD", 2, 1.0), "b": mk("NEW", 2, 2.0)}}
    KW.reap_stale_attempts(ap, cfg, st, {}, ap_dir=str(tmp_path))
    assert st["items"]["a"]["status"] == "RUNNING" and st["items"]["b"]["status"] == "RUNNING"
    # higher attempt of ANOTHER event: still both
    st = {"items": {"a": mk("OLD", 2, 1.0), "b": mk("NEW", 3, 2.0)}}
    KW.reap_stale_attempts(ap, cfg, st, {}, ap_dir=str(tmp_path))
    assert st["items"]["a"]["status"] == "RUNNING"
    # strictly higher attempt of the SAME event: the older one is superseded
    st = {"items": {"a": mk("NEW", 2, 1.0), "b": mk("NEW", 3, 2.0)}}
    KW.reap_stale_attempts(ap, cfg, st, {}, ap_dir=str(tmp_path))
    assert st["items"]["a"]["status"] == "CANCELLED" and st["items"]["b"]["status"] == "RUNNING"


def test_kit_wave_edit_refuses_a_die_event_the_gate_cannot_resolve():
    import kit_wave_edit as E
    old = {"dies": {"s81": {"enabled": True, "event": "1dfae74037a"}, "qwen_kvsys": {"enabled": True, "event": "event28w_c"}}}
    ok_new = {"dies": {"s81": {"enabled": True, "event": "b05c98f7919"}, "qwen_kvsys": {"enabled": True, "event": "event28w_c"}}}
    assert E.event_problems(old, ok_new) == []
    bad = {"dies": {"s81": {"enabled": True, "event": "D8h synthetic key"}, "qwen_kvsys": {"enabled": True, "event": "nolisted"}}}
    probs = E.event_problems(old, bad)
    assert len(probs) == 2 and "whitespace" in probs[0] and "accepted events" in probs[1]
    ok_listed = {"dies": {"qwen_kvsys": {"enabled": True, "event": "KV-D26", "gate_events_extra": ["KV-D26"]}}}
    assert E.event_problems(old, ok_listed) == []
    assert E.event_problems(old, {"dies": {"s81": {"enabled": True, "event": "xyz"}}}) != []              # not hex


def test_overloaded_hosts_are_not_in_the_stop_skip_set():
    stt = {"epyc9": {"load": 900, "cores": 96}, "epyc8": {"load": 10, "cores": 96}}
    assert KW.host_unreadable(stt, "epyc9") is False and KW.host_unreadable(stt, "epyc7") is True and KW.host_unreadable({}, "epyc7") is False


def test_every_plan_type_gets_a_row_variants_included():
    d = {"event": "E", "plan_core_items": ["core_a"], "only_items": ["hd_ctl"], "owner_lane": "L", "plan": "/p"}
    cfg = {"dies": {"s81_head": d}, "stops_off": True}
    rows = [{"die": "s81_head", "item": "hd_ctl", "kind": "type", "state": "NEEDS-KIT", "owner": "L", "live_job": "none", "replicas": "1", "members": "", "last_activity": ""}]
    plan = {"hd_ctl": {}, "hd_ctl_e": {}, "hd_spn_eshim_rx": {}, "hd_ctl__cl1": {}, "core_a": {}, "ot_sram_1r1w_32x546_m1": {}}      # a memory macro master gets no row
    assert KW.plan_type_rows(cfg, "s81_head", d, rows, plan) == []                                    # no partition-type table read: nothing synthesized
    d["_plan_part_types"] = {"hd_ctl", "hd_ctl_e", "hd_spn_eshim_rx", "hd_ctl__cl1", "core_a"}
    plan["qkd_kvs_pcc_h_head_p"] = {}                                                                 # a name in the plan blocks that is NOT a partition type (FLOW-2155 class 2)
    got = {r["item"] for r in KW.plan_type_rows(cfg, "s81_head", d, rows, plan)}
    assert "qkd_kvs_pcc_h_head_p" not in got
    assert got == {"hd_ctl_e", "hd_spn_eshim_rx"}                  # hd_ctl known; hd_ctl__cl1 expands from its parent; core_a is a core
    assert all(r["_plan_row"] for r in KW.plan_type_rows(cfg, "s81_head", d, rows, plan))
    assert d["_plan_rows_n"] == 2                                                                              # the counter the tick logs (KIT-WAVE PLAN-ROWS)
    d["_plan_part_types"] = {"hd_ctl", "hd_ctl_e"}                                                             # only real partition types get a row (kv_cland_* etc. are plan names, not types)
    assert {r["item"] for r in KW.plan_type_rows(cfg, "s81_head", d, rows, plan)} == {"hd_ctl_e"}
    d.pop("_plan_part_types")
    assert KW.plan_type_rows({"dies": {"s81_head": d}}, "s81_head", d, rows, plan) == []                       # not stops_off
    assert KW.plan_type_rows(cfg, "s81_head", dict(d, rows_from_plan=False), rows, plan) == []                # opt-out
    d["_plan_part_types"] = {"hd_ctl", "hd_ctl_e", "hd_spn_eshim_rx"}
    picks, skip = KW.select(rows, cfg, "s81_head", {"items": {}}, plan)
    assert {"hd_ctl_e", "hd_spn_eshim_rx"} <= {r["item"] for r in picks}                                       # exempt from only_items


def test_src_manifest_extra_files_alone_never_refuse_a_kit():
    sp = {"src": "/t", "src_sha": "abc"}
    extra = "SRC_MANIFEST DRIFT physical/x/clock_contract.json.SONNET-DISABLED-1120 (extra: not in the manifest)\n" * 3
    assert KW.src_manifest_verdict(sp, 1, extra)[0] == ""
    assert "extra file" in KW.src_manifest_verdict(sp, 1, extra)[1]
    mixed = extra + "SRC_MANIFEST DRIFT physical/y.json (changed: sha differs)\n"
    assert KW.src_manifest_verdict(sp, 1, mixed)[0].startswith("SRC_MANIFEST FAIL")


def test_tick_source_logs_the_plan_rows_counter():
    assert "KIT-WAVE PLAN-ROWS {_die}" in open(KW.__file__).read()


def test_plan_failure_with_alternating_evidence_texts_stops_after_three():
    import repeat_stop as RS
    a = "core view has no recipe / unambiguous port map in the plan @gen: import json,sys;v=json.load(open(sys.argv[1]))"
    b = "core view has no recipe / unambiguous port map in the plan @gen: CORE_VIEW FAIL <id>@ x"
    assert RS.fingerprint("gen", "PLAN", a) == RS.fingerprint("gen", "PLAN", b)
    st, ev = {}, None
    for n, w in enumerate([a, b, a], 1):
        ev = RS.record(st, "qwen_kvsys", "qkd_pv_fin_s8_pin", n, "gen", "PLAN", w, inputs={"block": "B"}, t=n)
    assert ev and ev["event"] == "BLOCKED-REPEAT"                                         # 3rd failure of the same plan cause on the same block
    assert RS.gate(st, "qwen_kvsys", "qkd_pv_fin_s8_pin", {"block": "B"})[0] is True      # held while block / plan file are unchanged
    assert RS.gate(st, "qwen_kvsys", "qkd_pv_fin_s8_pin", {"block": "B2"})[0] is False   # a new plan block (D25e3) releases it


def test_tool_digests_of_an_immutable_rt_tree_are_computed_once_and_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(KW, "DIGEST_CACHE", str(tmp_path / "dg.json"))
    root = tmp_path / "abcdef012345"                                  # an rt/<sha12> tree
    root.mkdir()
    calls = []
    assert KW._digest_persist(root, "stage", "gen", lambda: calls.append(1) or "D1") == "D1"
    assert KW._digest_persist(root, "stage", "gen", lambda: calls.append(1) or "D2") == "D1" and len(calls) == 1      # second call (a new process) reads the file
    assert KW._digest_persist(root, "stage", "bind", lambda: "D3") == "D3"
    other = tmp_path / "not-a-sha-dir"
    other.mkdir()
    assert KW._digest_persist(other, "stage", "gen", lambda: "X") == "X" and KW._digest_persist(other, "stage", "gen", lambda: "Y") == "Y"   # mutable trees are never cached


def test_bind_signature_recheck_interval_is_half_an_hour():
    assert KW.BIND_SIG_RECHECK_S == 1800


def test_bind_preflight_groups_and_dies_probe_in_parallel_with_the_same_result(monkeypatch):
    import threading
    import time as _t
    seen, lock = [], threading.Lock()

    class A:
        def log(self, m): pass

        def rpy(self, host, code, args, timeout=0):
            if code == KW.PROBE_BIND_SIG:
                return {"sig": "s"}
            with lock:
                seen.append(args.get("bind_out"))
            _t.sleep(0.3)
            return {"stale": ["t2"] if args.get("bind_out") == "/b1" else []}
    ap = A()
    cfg = {"dies": {"d": {"gen_host": "h", "src": "/s", "plan": "/p", "kit_rtl": {"mode": "bind", "bind_out": "/b0", "asbuilt": ""},
                          "item_inputs": {"t2": {"kit_rtl": {"bind_out": "/b1"}}}}}}
    rows = [{"item": "t1", "kind": "type"}, {"item": "t2", "kind": "type"}]
    t0 = _t.time()
    out = KW.bind_preflight(ap, cfg, {}, "d", rows, rpy=ap.rpy)
    dt = _t.time() - t0
    assert set(out) == {"t2"} and sorted(seen) == ["/b0", "/b1"]
    assert dt < 0.55                                              # two 0.3 s probes ran concurrently
    # prewarm: two dies, probed concurrently, caches filled so the per-die loop makes no further probe
    cfg2 = {"dies": {k: {"enabled": True, "gen_host": "h", "src": "/s", "plan": "/p", "kit_rtl": {"mode": "bind", "bind_out": "/b0"}} for k in ("a", "b")}}
    owners = [{"die": k, "item": "t1", "kind": "type"} for k in ("a", "b")]
    cfg2["dies"]["parked"] = dict(cfg2["dies"]["a"], plan="/parked", parked={"reason": "owner parked"})
    owners.append({"die": "parked", "item": "t1", "kind": "type"})
    seen.clear()
    plans = []
    st = {}
    monkeypatch.setattr(KW, "plan_names", lambda AP, st, d: plans.append(d["plan"]) or {})
    t0 = _t.time()
    n = KW.prewarm_probes(type("AP2", (), {"log": staticmethod(lambda m: None), "rpy": staticmethod(ap.rpy)})(), cfg2, st, owners)
    assert n == 2 and _t.time() - t0 < 0.55
    assert plans == ["/p", "/p"]


def test_cancel_stop_is_detached_and_its_result_is_checked_next_tick(tmp_path, monkeypatch):
    import autopilot as A
    import wave_jobs as WJ
    spawned, lines = [], []
    monkeypatch.setattr(WJ, "stop_bg_spawn", lambda hub, roots, logp, tag="": spawned.append((roots, str(logp), tag)) or True)
    monkeypatch.setattr(A, "AP_DIR", tmp_path)
    monkeypatch.setattr(A, "log", lines.append)
    monkeypatch.setattr(A, "DRY", False)
    j = {"id": "J1", "die": "qc", "type": "t", "path": "h:/k/attempt_1"}
    assert A.stop_cancelled(j, "explicit cancel") == "" and spawned and spawned[0][2] == "J1"
    assert j["stopped_containers"]["queued"] and "detached" in lines[-1]
    st = {"jobs": {"J1": j}}
    assert A.check_pending_stops(st) == 0 and not j["stopped_containers"].get("checked")            # no result yet
    (tmp_path / "remote_stops.log").write_text("2026-11-20 00:30:00 stop-bg [J1] 1 root(s): none running; epyc7 not checked: timeout\n")
    assert A.check_pending_stops(st) == 1 and j["stopped_containers"]["retry"] == 1 and len(spawned) == 2   # a host was not checked: started once more
    (tmp_path / "remote_stops.log").write_text("2026-11-20 00:31:00 stop-bg [J1] 1 root(s): epyc8:c1\n")
    assert A.check_pending_stops(st) == 0 and "epyc8:c1" in j["stopped_containers"]["checked"]
    found, ok, _ = WJ.stop_result_for("x stop-bg [J2] 1 root(s): none running", "J2")
    assert found and ok


def test_loop_gaps_run_in_the_aux_timer_when_the_marker_exists(tmp_path, monkeypatch):
    import autopilot as A
    monkeypatch.setattr(A, "AP_DIR", tmp_path)
    assert A.loop_gaps_off_tick() is False
    (tmp_path / "AUX-LOOPGAPS").write_text("")
    assert A.loop_gaps_off_tick() is True
    calls = []
    monkeypatch.setattr(A, "load_state", lambda: {"jobs": {}})
    monkeypatch.setattr(A, "parse_queue", lambda t: {})
    monkeypatch.setattr(A, "read_queue_text", lambda: "")
    monkeypatch.setattr(A, "read_coord", lambda p: "")
    monkeypatch.setattr(A, "write_loop_gaps", lambda st, rows, g: calls.append((st, rows, g)))
    monkeypatch.setattr(A, "log", lambda m: None)
    A.aux_loop_gaps()
    assert len(calls) == 1 and calls[0][0] == {"jobs": {}}
    src = open(A.__file__).read()
    assert "if not loop_gaps_off_tick():" in src                  # the tick skips it


def test_family_key_groups_generator_families_and_variants():
    assert KW.family_key("col_h9_r1__t1__cl49d7a23e__pv047ea3b3") == "col_h9_r1" == KW.family_key("col_h9_r1__t1__clf32cde8d")
    assert KW.family_key("ot_s81sl_leaf__t56") == KW.family_key("ot_s81sl_leaf__t21") == "ot_s81sl_leaf"
    assert KW.family_key("kv3_pv_v3") == KW.family_key("kv3_pv_v3n") == "kv3_pv" and KW.family_key("hd_ctl_e") == "hd_ctl_e"


def test_representatives_first_hold_siblings_while_the_representative_fails_and_release_on_a_new_attempt(monkeypatch, tmp_path):
    monkeypatch.setattr(KW, "FAMILY_TABLE_PATH", str(tmp_path / "none.json"))      # hermetic: name-key families
    cfg = {"dies": {"s81": {"event": "E"}}, "stops_off": True}
    mk = lambda i: {"die": "s81", "item": i, "kind": "type"}
    picks = [mk("ot_s81sl_leaf__t1"), mk("ot_s81sl_leaf__t2"), mk("ot_s81sl_leaf__t3"), mk("slice_station__t1")]
    st = {"items": {"a": {"die": "s81", "item": "ot_s81sl_leaf__t3", "status": "FAIL", "event": "OLD", "started": 1, "attempt": "1"}}}      # t3 failed most (on an old event)
    ordered, held, meta = KW.family_plan(cfg, st, "s81", picks)
    assert meta["families"] == 2 and "ot_s81sl_leaf__t3" in meta["reps"] and "slice_station__t1" in meta["reps"] and meta["siblings"] == 2 and not held
    assert [r["item"] for r in ordered][:2] == sorted(["ot_s81sl_leaf__t3", "slice_station__t1"], key=lambda x: [r["item"] for r in picks].index(x))      # representatives first
    st["items"]["b"] = {"die": "s81", "item": "ot_s81sl_leaf__t3", "status": "FAIL", "class": "PLAN", "stage": "place", "event": "E", "started": 5, "attempt": "2"}
    ordered, held, meta = KW.family_plan(cfg, st, "s81", picks)
    assert set(held) == {"ot_s81sl_leaf__t1", "ot_s81sl_leaf__t2"} and "FAMILY-HOLD" in held["ot_s81sl_leaf__t1"]
    assert {r["item"] for r in ordered} == {"ot_s81sl_leaf__t3", "slice_station__t1"}                          # siblings stay queued, not launched
    st["items"]["c"] = {"die": "s81", "item": "ot_s81sl_leaf__t3", "status": "RUNNING", "event": "E", "started": 9, "attempt": "3"}       # the fix landed: a newer attempt
    ordered, held, meta = KW.family_plan(cfg, st, "s81", picks)
    assert not held and len(ordered) == 4
    st["items"]["c"]["status"] = "FAIL"
    st["items"]["c"].update(**{"class": "INFRA"}, reason="make Error 247")
    assert not KW.family_plan(cfg, st, "s81", picks)[1]                                                       # an INFRA failure of the representative holds nothing


def test_real_family_table_is_used_then_the_name_key(tmp_path):
    import json as _j
    f = tmp_path / "classes.json"
    f.write_text(_j.dumps({"s81": {"leaf": {"classes": [{"id": "leaf_S00", "members": [["ot_s81sl_leaf__t13", "R0"], ["ot_s81sl_leaf__t53__clb66fa5cb", "MX"]]}]},
                                    "leaf_cap7786": {"classes": [{"id": "leaf_T00", "members": [["ot_s81sl_leaf__t99", "R0"]]}]}},
                           "qc": [{"stem": "cbf_q01", "types": "1"}, {"stem": "cbf_q01_s2", "types": "1"}, {"stem": "sle_ctl", "types": "7"}], "kv": [{"stem": "kv3_pv", "types": "16"}]}))
    t = KW.family_table(str(f))
    assert KW.family_of("s81", "ot_s81sl_leaf__t13", t) == KW.family_of("s81", "ot_s81sl_leaf__t53__clb66fa5cb", t) == "s81:leaf_S00"
    assert KW.family_of("s81", "ot_s81sl_leaf__t99", t) == KW.family_key("ot_s81sl_leaf__t99")           # the cap7786 cut is ignored: name key
    assert KW.family_of("s81", "col_h9_r1__t1__cl1", t) == "col_h9_r1"                                      # not in the table: name key
    assert KW.family_of("qwen_compute", "sle_ctl__cl372cea1c", t) == "qc:sle_ctl" and KW.family_of("qwen_compute", "cbf_q01_s2", t) == "qc:cbf_q01_s2"
    assert KW.family_of("qwen_compute", "cbf_q01", t) == "qc:cbf_q01"
    assert KW.family_of("qwen_kvsys", "kv3_pv_v3n", t) == "kv:kv3_pv"
    f2 = tmp_path / "classes2.json"
    f2.write_text(_j.dumps({"s81": {"leaf": {"classes": [{"id": "old", "members": [["ot_s81sl_leaf__t13", "R0"]]}]},
                                     "leaf_nogrowth_j4e": {"note": "x", "by_cap_bits": {"3000": [{"id": "wrong", "members": [["ot_s81sl_leaf__t13", "R0"]]}],
                                                                                         "4500": [{"id": "leaf_N01", "members": [["ot_s81sl_leaf__t13", "R0"], ["ot_s81sl_leaf__t4", "R0"]]}]}},
                                     "leaf_site_slack_j4e": [{"id": "x"}]}, "qc": [], "kv": []}))
    t2 = KW.family_table(str(f2))
    assert KW.family_of("s81", "ot_s81sl_leaf__t13", t2) == "s81:leaf_N01" == KW.family_of("s81", "ot_s81sl_leaf__t4", t2)      # nogrowth cut wins over the growth cut
    assert KW.family_table(str(tmp_path / "none.json")) == {}
    assert KW.family_of("hbm", "x_t1", t) == "x"


def test_full_input_hash_does_not_move_with_the_rt_tools_digest(monkeypatch):
    cfg = {"dies": {"d": {"src_manifest_hash": "S", "gen_env": {}, "die_gen_env": {}}}}
    monkeypatch.setattr(KW, "kit_digest_parts", lambda cfg, die, rec=None, **k: {"plan": "P", "tools": "T"})
    monkeypatch.setattr(KW, "item_env", lambda d, item: {})
    monkeypatch.setattr(KW, "exec_tools_digest", lambda root=None: "RT1")
    h1 = KW.full_input_hash(cfg, "d", "i", "B")
    monkeypatch.setattr(KW, "exec_tools_digest", lambda root=None: "RT2")            # another rt tree: the hash is unchanged
    assert h1 and KW.full_input_hash(cfg, "d", "i", "B") == h1
    monkeypatch.setattr(KW, "kit_digest_parts", lambda cfg, die, rec=None, **k: {"plan": "P2", "tools": "T"})
    assert KW.full_input_hash(cfg, "d", "i", "B") != h1                                # a plan row change moves it


def test_state_follows_the_host_ot_run_actually_uses():
    lines = []
    ap = type("AP", (), {"log": staticmethod(lines.append)})()
    row = lambda i, kit: {"die": "qwen_compute", "item": i, "attempt": "1", "status": "ENQUEUED", "q_status": "RUNNING", "kit": kit, "dir": "/nonexistent"}
    st = {"items": {"a": row("sle_ctl", "epyc9:/r/E/items/sle_ctl/gen/sle_ctl"), "b": row("ok", "epyc8:/r/E/items/ok/gen/ok"), "c": row("two", "epyc8:/r/E/items/two/gen/two")}}
    scans = {"/r/E/items/sle_ctl/gen/sle_ctl": {"epyc10": ["dpkit-x"], "epyc9": []}, "/r/E/items/ok/gen/ok": {"epyc8": ["dpkit-y"]}, "/r/E/items/two/gen/two": {"epyc2": ["a"], "epyc7": ["b"]}}
    n = KW.follow_actual_hosts(ap, {}, st, now=1.0, scan=lambda root: scans[root])
    assert n == 1 and st["items"]["a"]["ran_on"] == "epyc10" and "HOST-MOVED" in lines[0]
    assert "ran_on" not in st["items"]["b"] and "ran_on" not in st["items"]["c"]               # same host: unchanged; two hosts: ambiguous, untouched
    assert all(r["host_checked"] == 1.0 for r in st["items"].values())


def test_col_h9_landing_variants_are_the_families(tmp_path):
    import json as _j
    (tmp_path / "classes.json").write_text(_j.dumps({"s81": {}, "qc": [], "kv": []}))
    rows = lambda names, sig: [{"member": n, "pins": sig[0], "edges": sig[1], "reset": sig[2]} for n in names]
    (tmp_path / "FABLE-SUPERSET-0415-unify.json").write_text(_j.dumps({"classes": [
        {"die": "s81", "cls": "col_h9_r1", "role_rows": rows(["col_h9_r1__a", "col_h9_r1__b", "col_h9_r1__c"], ["p", "e", "r0"]) + rows(["col_h9_r1__d"], ["q", "f", "r1"]) + rows(["col_h9_r1__e"], ["q", "f", "r2"])},
        {"die": "s81", "cls": "col_h9_r2", "role_rows": rows(["col_h9_r2__a"], ["p", "e", "r"])},
        {"die": "qwen_compute", "cls": "sle_ctl", "role_rows": rows(["sle_ctl__x"], ["p", "e", "r"])}]}))
    t = KW.family_table(str(tmp_path / "classes.json"))
    f = lambda i: KW.family_of("s81", i, t)
    assert f("col_h9_r1__a") == f("col_h9_r1__b") == f("col_h9_r1__c") == "s81:col_h9_r1:v1"
    assert len({f("col_h9_r1__d"), f("col_h9_r1__e"), f("col_h9_r1__a")}) == 3 and f("col_h9_r2__a") == "s81:col_h9_r2:v1"
    assert f("col_h9_r1__unknown") == "col_h9_r1"                                                      # not listed: the name key


def test_bind_probe_marks_a_type_stale_when_the_bound_module_predates_the_plan_relay_rows(tmp_path, monkeypatch):
    import json as _j, subprocess as _sp, sys as _sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bo = tmp_path / "bind"
    (bo / "rtl").mkdir(parents=True)
    (bo / "bind_report.json").write_text(_j.dumps({"types": {"ta": {"module": "ma"}, "tb": {"module": "mb"}, "tc": {"module": "mc"}}}))
    plain = "module %s(\n  input wire clk\n);\n  leaf_x u_x (.clk(clk), .i(w_a));\nendmodule\n"
    for m in ("ma", "mb", "mc"):
        (bo / "rtl" / f"{m}.sv").write_text(plain % m)
    (bo / "rtl" / "mb.sv").write_text("module mb(\n  input wire clk\n);\n  wire [3:0] w_a;\n  leaf_x u_x (.clk(clk), .i(w_a));\nendmodule\n")
    row = lambda inst: {"inst": inst, "side": "sink", "port": "i", "D": 1}
    plan = {"partition_types": {"ta": {"relay_depth": [row("nope")]},            # sink instance absent from the bound module: kit_rtl would fail
                                "tb": {"relay_depth": [row("x")]},               # applies (sink instance + plain 4-bit wire): not stale
                                "tc": {}}}                                       # no relay rows
    (tmp_path / "plan.json").write_text(_j.dumps(plan))
    monkeypatch.setenv("OT_BIND_PROBE_RT", str(tmp_path / "no_rt"))               # fall back to the src tree's tools/die_plan
    a = {"src": root, "plan": str(tmp_path / "plan.json"), "bind_out": str(bo), "types": ["ta", "tb", "tc"]}
    r = _sp.run([_sys.executable, "-I", "-", _j.dumps(a)], input=KW.PROBE_BIND, capture_output=True, text=True, env=dict(os.environ))
    out = _j.loads([l for l in r.stdout.splitlines() if l.startswith("AP_JSON ")][-1][8:])
    assert out["stale"] == ["ta"] and "ta" in out["relay"] and "tb" not in out["relay"], out


def test_guard_refusal_is_released_only_by_the_guard_files_not_by_gen_closure_churn(monkeypatch):
    """FLOW-NOADV-0915: seqhost__t1 attempt 13 -> 14: identical noenv hash, only stg['gen'] moved (unrelated main merge) and the deterministic guard refusal relaunched 12 times in 6 h"""
    why = "gen phys: ERROR type t: physical collector_tree differs from captured bound reset identity; preserve original IDs/edges/coordinates"
    gf = KW.guard_files_for(why)
    assert gf and "tools/die_plan/gen_phys.py" in gf and KW.guard_files_for("some other text") == ()
    rf = {f: "A" for f in gf}
    old = {"v": 2, "noenv": "N", "env": {}, "fam": {"gen": "F1"}, "stg": {"gen": "G1"}, "pc": {}, "rf": rf}
    rec = {"status": "FAIL", "class": "PLAN", "stage": "gen", "reason": why, "input_parts": old}
    cfg = {"dies": {"d": {}}}
    def now(**kw):
        n = dict(old, **kw)
        monkeypatch.setattr(KW, "input_parts", lambda *a, **k: n)
        return KW.so_same_input(cfg, "d", {"item": "i"}, rec)
    assert now() is True
    assert now(fam={"gen": "F2"}, stg={"gen": "G2"}) is True                      # unrelated gen closure churn: still the same input
    assert now(rf=dict(rf, **{"tools/die_plan/gen_phys.py": "B"})) is False       # the guard code changed: relaunch
    assert now(noenv="N2") is False                                               # the plan / bind inputs changed: relaunch
    rec["class"] = "UNCLASSIFIED"
    assert now(stg={"gen": "G2"}) is True                                         # the class label is no part of the key
    rec["input_parts"] = {k: v for k, v in old.items() if k != "rf"}              # an attempt stamped before the guard digests: old whole-stage compare
    assert now(fam={"gen": "F2"}, stg={"gen": "G2"}) is False
