"""WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 A): automatic tools-only refresh; bind unchanged -> applied, bind changed -> NEEDS-LANE."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import tools_refresh as TR

OLD = "/srv/s/kw45/src_kv_pin_abc_d16"
SHA = "f" * 40


def die(**kw):
    d = {"src": OLD, "gen_host": "epyc10", "gen_hosts": ["epyc10", "epyc8"], "tools_refresh": True, "owner_lane": "KV-R3",
         "src_manifest_hash": "old", "plan": OLD + "/physical/plan.json",
         "kit_rtl": {"mode": "bind", "asbuilt": OLD + "/physical/native_bind/asbuilt.json", "bind_out": OLD + "/physical/native_bind/out"},
         "event": "e"}
    d.update(kw)
    return d


LAG = {"pin": "abc", "n_commits": 12, "missing": ["r535", "r554"]}


class FakeOps:
    def __init__(self, compose=True, guard=True, bind=(True, True, "ok")):
        self.calls, self._c, self._g, self._b = [], compose, guard, bind

    def compose(self, old, new):
        self.calls.append(("compose", old, new))
        return (self._c, "composed" if self._c else "delta-make failed", "newhash")

    def guard(self, new, h):
        self.calls.append(("guard", new, h))
        return self._g, "g"

    def bind(self, new):
        self.calls.append(("bind", new))
        return self._b


def run(d=None, ops=None, lag=LAG, state=None, dry=False):
    posts, edits = [], []
    state = {} if state is None else state
    rec = TR.refresh("kv", d or die(), lag, SHA, ops or FakeOps(), state, posts.append, lambda die_, ops_, msg: edits.append((ops_, msg)), dry=dry)
    return rec, posts, edits, state


def test_off_and_nothing_missing_do_nothing():
    assert run(die(tools_refresh=False))[0]["status"] == "SKIP"
    assert run(lag={"pin": "a", "n_commits": 3, "missing": []})[0]["status"] == "SKIP"
    assert run(lag={"pin": "a", "n_commits": None, "missing": []})[0]["status"] == "SKIP"


def test_bind_unchanged_applies_the_tools_only_tree():
    ops = FakeOps()
    rec, posts, edits, state = run(ops=ops)
    assert rec["status"] == "APPLIED" and [c[0] for c in ops.calls] == ["compose", "guard", "bind"]
    new = TR.new_tree_path(OLD, SHA)
    patch, msg = edits[0]
    byp = {o["path"]: o for o in patch}
    assert byp["/dies/kv/src"]["value"] == new and byp["/dies/kv/src_manifest_hash"]["value"] == "newhash"
    assert byp["/dies/kv/kit_rtl"]["value"]["bind_out"] == new + "/physical/native_bind/out"     # paths into the old tree follow the new tree
    assert byp["/dies/kv/plan"]["value"].startswith(new)
    assert byp["/dies/kv/superseded_trees"]["value"] == [OLD]
    assert "r535" in msg and posts and posts[0].startswith("TOOLS-REFRESH kv: switched")
    # the same (pin, main, rulings) is never composed twice
    assert run(state=state)[0]["status"] == "SKIP"


def test_bind_changed_posts_needs_lane_and_applies_nothing():
    rec, posts, edits, _ = run(ops=FakeOps(bind=(True, False, "bind native_topology CHANGED")))
    assert rec["status"] == "BIND-CHANGED" and not edits
    assert posts[0].startswith("NEEDS-LANE [TOOLS-REFRESH -> KV-R3]") and "change the bind of record" in posts[0]


def test_failures_never_apply():
    for kw, st in ((dict(compose=False), "COMPOSE-FAIL"), (dict(guard=False), "GUARD-FAIL"), (dict(bind=(False, False, "boom")), "BIND-FAIL")):
        rec, posts, edits, _ = run(ops=FakeOps(**kw))
        assert rec["status"] == st and not edits
    assert len(run(ops=FakeOps(compose=False))[1]) == 1                   # FABLE-FLOW-1900 B: a compose failure is structural: one NEEDS-LANE, no retry loop


def test_dry_mode_reports_only():
    rec, posts, edits, _ = run(d=die(tools_refresh="dry"))
    assert rec["status"] == "DRY-OK" and not edits and not posts
    assert run(dry=True)[0]["status"] == "DRY-OK"


def test_real_command_text():
    o = TR.Ops(die(), "/repo.git", SHA)
    new = TR.new_tree_path(OLD, SHA)
    pc = o.pack_cmd(OLD, new)                                            # built on the hub: the gen host has no git store of main
    assert "delta-make" in pc and "--paths tools physical/common_flow" in pc and "cat " + OLD + "/.src-manifest.json" in pc
    assert "rsync" in pc and "epyc10:" in pc and new + ".pack" in pc and "--repo /repo.git" in pc
    cmds = o.compose_cmds(OLD, new)
    assert "delta-apply" in cmds[0] and "--link" in cmds[0] and "verify" in cmds[1] and "publish" in cmds[2]
    assert "replicate" in cmds[3] and "--hosts epyc8" in cmds[3] and "--link-from src_kv_pin_abc_d16" in cmds[3]
    ob = TR.Ops(die(tools_refresh_bind_cmd="python3 tools/die_plan/bind.py bind {plan} --out {out} --strict"), "/repo.git", SHA)   # the recipe is per die: no default any more
    assert "bind.py bind" in ob.bind_cmd(new, "/o") and "--strict" in ob.bind_cmd("/n", "/o") and ob.bind_cmd("/n", "/o").startswith("cd /n && ")


def test_ops_compose_stops_at_the_first_failing_step(monkeypatch):
    import overlay_classify as OC
    monkeypatch.setattr(OC, "classify_die", lambda repo, d, main, prefixes=None: {})
    seen = []

    def run_(host, cmd, timeout=0):
        seen.append((host, cmd))
        return (1, "boom") if "delta-apply" in cmd else (0, "hash")
    ok, detail, h = TR.Ops(die(), "/r", SHA, run=run_).compose(OLD, "/n")
    assert not ok and len(seen) == 2 and "rc 1" in detail and seen[0][0] is None and seen[1][0] == "epyc10"
    seen.clear()
    ok, detail, h = TR.Ops(die(), "/r", SHA, run=lambda host, cmd, timeout=0: (3, "no sha")).compose(OLD, "/n")
    assert not ok and "delta-make (hub)" in detail


def test_wave_tick_starts_one_refresh_per_key(monkeypatch):
    import kit_wave as KW
    launched, logs = [], []

    class AP:
        DRY = False
        AP_DIR = "/tmp/apdir"
        log = staticmethod(logs.append)
        launch_unit = staticmethod(lambda unit, logf, argv: launched.append((unit, argv)))
    KW.TOOLS_LAG_CACHE["raw"] = {"kv": dict(LAG), "s81": {"pin": "p", "n_commits": 5, "missing": ["r400"]}, "hbm": {"pin": "q", "n_commits": 9, "missing": []}}
    cfg = {"dies": {"kv": {"enabled": True, "tools_refresh": True}, "s81": {"enabled": True, "tools_refresh": False},
                    "hbm": {"enabled": True, "tools_refresh": "dry"}}}
    st = {}
    KW.tools_refresh_tick(AP, cfg, st)
    KW.tools_refresh_tick(AP, cfg, st)                                   # same key: not started again
    assert [u.split("-")[2] for u, _ in launched] == ["kv"]              # s81 off, hbm has nothing missing
    assert "--die" in launched[0][1] and "--dry" not in launched[0][1]
    KW.TOOLS_LAG_CACHE["raw"]["kv"] = {"pin": "abc", "n_commits": 20, "missing": ["r535", "r554", "r600"]}
    KW.tools_refresh_tick(AP, cfg, st)                                   # a new ruling = a new key
    assert len(launched) == 2


def test_a_private_overlay_patch_stops_the_refresh_with_its_diff():
    ops = FakeOps(compose=False)
    ops.overlay_report = {"tools/a.py": "a", "tools/b.py": "b", "tools/c.py": "c"}
    ops.compose = lambda old, new: (False, "OVERLAY-PRIVATE: tools/c.py: private patch: the change is not in main\n--- base/tools/c.py\n+++ overlay/tools/c.py\n+X=1", "")
    rec, posts, edits, _ = run(ops=ops)
    assert rec["status"] == "OVERLAY-PRIVATE" and not edits and rec["overlay_main_wins"] == ["tools/a.py", "tools/b.py"]
    assert posts[0].startswith("NEEDS-LANE [TOOLS-REFRESH -> KV-R3]") and "tools/c.py" in posts[0] and "+X=1" in posts[0] and "main wins on 2" in posts[0]


def test_main_wins_overlays_are_dropped_and_logged(monkeypatch):
    seen = []
    import overlay_classify as OC
    monkeypatch.setattr(OC, "classify_die", lambda repo, d, main, prefixes=None: {"tools/a.py": {"cls": "a", "why": "x"}, "tools/b.py": {"cls": "b", "why": "y"}})
    o = TR.Ops(die(), "/r", SHA, run=lambda host, cmd, timeout=0: (seen.append(cmd) or (0, "h")))
    ok, detail, h = o.compose(OLD, "/n")
    assert ok and o.overlay_report == {"tools/a.py": "a", "tools/b.py": "b"}
    assert "--drop-overlay tools/a.py tools/b.py" in seen[0]                      # the pack drops exactly the main-wins overlays
    monkeypatch.setattr(OC, "classify_die", lambda repo, d, main, prefixes=None: {"tools/c.py": {"cls": "c", "why": "private patch", "diff": "+X"}})
    ok, detail, h = TR.Ops(die(), "/r", SHA, run=lambda *a, **k: (0, "")).compose(OLD, "/n")
    assert not ok and detail.startswith("OVERLAY-PRIVATE") and "+X" in detail


def test_a_crash_before_compose_is_not_an_attempt_and_three_crashes_stop():
    posts, state = [], {}
    for n in (1, 2, 3):
        # the pass dies before its first step (e.g. an import error): nothing was recorded as attempted, the key is still open
        key = TR.refresh_key("kv", LAG, SHA)
        assert "done" not in state and "attempts" not in state                               # a pre-compose crash leaves no attempt record
        assert TR.should_refresh(dict(die(), _die="kv"), LAG, state, key) == (True, "")      # ... so the key is still open for the next pass (n < 3)
        TR.record_crash(state, "kv", die(), LAG, SHA, ModuleNotFoundError("overlay_classify"), posts.append)
        assert state["crashes"]["kv|abc|r535,r554"] == n and "done" not in state and "attempts" not in state
        if n < 3:
            assert not posts
    assert len(posts) == 1 and "crashed 3 times" in posts[0] and posts[0].startswith("NEEDS-LANE [TOOLS-REFRESH -> KV-R3]")
    ok, why = TR.should_refresh(dict(die(), _die="kv"), LAG, state, TR.refresh_key("kv", LAG, SHA))
    assert not ok and "crash stop" in why


def test_compose_start_is_the_attempt_and_a_compose_crash_may_be_retried():
    class Boom(FakeOps):
        def compose(self, old, new):
            raise RuntimeError("ssh died")
    state = {}
    try:
        run(ops=Boom(), state=state)
        raise AssertionError("must propagate")
    except RuntimeError:
        pass
    assert state["attempts"]["kv|abc|r535,r554"]["status"] == "STARTED"            # compose had started: recorded
    TR.record_crash(state, "kv", die(), LAG, SHA, RuntimeError("ssh died"), lambda t: None)
    assert state["attempts"]["kv|abc|r535,r554"]["status"] == "CRASH"
    rec, posts, edits, _ = run(state=state)                                        # CRASH below 3: the same key runs again
    assert rec["status"] == "APPLIED"
    assert run(state=state)[0]["status"] == "SKIP"                                 # a finished pass is final


def test_wave_decide_retries_a_pre_compose_crash_and_stops_at_three():
    import kit_wave as KW
    now = 10_000
    assert KW.tools_refresh_decide(None, None, 0, now, False)[0] == "spawn"
    act, why, ent = KW.tools_refresh_decide({"t": now - 60, "unit": "u"}, None, 0, now, True)
    assert act == "skip" and why == "in flight"
    act, why, ent = KW.tools_refresh_decide({"t": now - 3000, "unit": "u"}, None, 0, now, False)       # unit ended, no attempt record: a crash
    assert act == "spawn" and ent["crashes"] == 1
    act, why, ent = KW.tools_refresh_decide({"t": now - 3000, "unit": "u", "crashes": 2}, None, 0, now, False)
    assert act == "stop" and "3 crashed" in why
    assert KW.tools_refresh_decide({"t": now - 3000}, {"status": "BIND-CHANGED"}, 0, now, False)[0] == "skip"    # attempted and finished: final
    assert KW.tools_refresh_decide({"t": now - 3000}, {"status": "CRASH"}, 1, now, False)[0] == "spawn"            # a compose crash below 3 is retried
    assert KW.tools_refresh_decide({"t": now - 3000}, {"status": "CRASH"}, 3, now, False)[0] == "stop"
    assert KW.tools_refresh_decide(5000, None, 0, now, False)[0] == "spawn"                                       # a legacy int entry (old wave state)


def test_wave_and_unit_use_the_same_key():
    import kit_wave as KW
    seen = {}

    class AP:
        DRY = False
        AP_DIR = "/tmp/no_such_apdir"
        log = staticmethod(lambda m: None)
        coord_append = staticmethod(lambda *a: None)
        launch_unit = staticmethod(lambda unit, logf, argv: seen.setdefault("n", 0) or seen.update(n=seen["n"] + 1))
    KW.TOOLS_LAG_CACHE["raw"] = {"kv": dict(LAG)}
    st = {}
    KW.tools_refresh_tick(AP, {"dies": {"kv": {"enabled": True, "tools_refresh": True}}}, st)
    assert list(st["tools_refresh_started"]) == [TR.wave_key("kv", LAG)] and seen["n"] == 1


def test_cli_starts_under_isolated_mode():
    """the wave starts it as `python3 -I tools_refresh.py`: the first dry run died with ModuleNotFoundError: overlay_classify"""
    import subprocess
    r = subprocess.run([sys.executable, "-I", str(HERE / "tools_refresh.py"), "--help"], capture_output=True, text=True, cwd="/")
    assert r.returncode == 0 and "--die" in r.stdout, r.stderr


def test_bind_gate_without_a_recipe_uses_the_bind_closure(monkeypatch):
    """KV dry run 15:30: the guessed `bind.py bind --asbuilt` command was wrong for KV (needs per-die env / packaged elaboration). Without dies.<die>.tools_refresh_bind_cmd
    the bind of record is unchanged only when the tools delta touches nothing bind.py imports; otherwise the owner supplies the recipe"""
    import flow_guard as FG
    monkeypatch.setattr(FG, "closure_files", lambda read, entry=(): ["tools/die_plan/bind.py", "tools/die_plan/bind_helper.py"])
    o = TR.Ops(die(), "/r", SHA, run=lambda *a, **k: (0, ""))
    o.delta_paths = ["tools/die_plan/gen_phys.py", "tools/autopilot/kit_wave.py"]
    assert o.bind("/n") == (True, True, "bind closure untouched: none of the 2 delta files is in bind.py's import closure")
    o.delta_paths = ["tools/die_plan/bind_helper.py", "tools/die_plan/gen_phys.py"]
    ran, unchanged, why = o.bind("/n")
    assert not ran and not unchanged and "bind_helper.py" in why and "tools_refresh_bind_cmd" in why
    o.delta_paths = None
    assert not o.bind("/n")[0]
    d = die(tools_refresh_bind_cmd="python3 tools/die_plan/bind.py bind {plan} --out {out} --strict")
    seen = []
    o2 = TR.Ops(d, "/r", SHA, run=lambda host, cmd, timeout=0: (seen.append(cmd) or (0, "aa\naa")))
    assert o2.bind("/n")[:2] == (True, True) and "bind.py bind" in seen[0] and "--strict" in seen[0]


def test_compose_reads_the_delta_paths():
    import overlay_classify as OC
    calls = []

    def run_(host, cmd, timeout=0):
        calls.append(cmd)
        if "delta.json" in cmd and cmd.startswith("cat"):
            return 0, json.dumps({"add": {"tools/die_plan/a.py": {}}, "delete": ["tools/die_plan/b.py"]})
        return 0, "hash"
    o = TR.Ops(die(), "/r", SHA, run=run_)
    OC.classify_die = lambda repo, d, main, prefixes=None: {}
    ok, detail, h = o.compose(OLD, "/n")
    assert ok and o.delta_paths == ["tools/die_plan/a.py", "tools/die_plan/b.py"]


def test_bind_recipes_kv_style_subdir_and_head_style_pass_line():
    """KV: native_topology.json lands in {out}/bind (tools_refresh_bind_sub); HEAD: head_die_portbind prints a PASS line and has no comparable output (tools_refresh_bind_pass)"""
    seen = []

    def run_kv(host, cmd, timeout=0):
        seen.append(cmd)
        return (0, "same\nsame") if "sha256sum" in cmd else (0, "")
    kv = die(tools_refresh_bind_cmd="mkdir -p {out}/bind && echo run {tree}", tools_refresh_bind_sub="bind")
    o = TR.Ops(kv, "/r", SHA, run=run_kv)
    assert o.bind("/n")[:2] == (True, True)
    sha = next(c for c in seen if "sha256sum" in c)
    assert "/n.bindcheck/bind/native_topology.json" in sha and "/physical/native_bind/out/native_topology.json" in sha
    seen.clear()
    head = die(tools_refresh_bind_cmd="python3 -I tools/s81_head/head_die_portbind.py p.json --out {out_rel}", tools_refresh_bind_pass=r"HEAD_DIE_PORTBIND PASS module_missing=0")
    ok = TR.Ops(head, "/r", SHA, run=lambda host, cmd, timeout=0: (seen.append(cmd) or (0, "HEAD_DIE_PORTBIND PASS module_missing=0 port_bind_rc=0")))
    assert ok.bind("/tree/n") == (True, True, "strict bind PASS (no bind output to compare; PASS line matched)")
    assert "--out ../n.bindcheck" in seen[0] and any("rm -rf /tree/n.bindcheck" in c for c in seen)
    bad = TR.Ops(head, "/r", SHA, run=lambda host, cmd, timeout=0: (0, "HEAD_DIE_PORTBIND FAIL"))
    assert not bad.bind("/tree/n")[0]


def test_a_structural_exit_stops_the_die_until_the_tree_or_recipe_changes():
    """FABLE-FLOW-1900 B: KV ran 9 passes, 7 exited 1 (the same compose / bind failures every time a ruling merged)"""
    d = die()
    state = {}
    rec, posts, edits, _ = run(d=d, ops=FakeOps(bind=(False, False, "no recipe")), state=state)
    assert rec["status"] == "BIND-FAIL" and state["stopped"]["kv"]["status"] == "BIND-FAIL" and len(posts) == 1
    for new_lag in (LAG, dict(LAG, missing=["r535", "r554", "r637"])):                  # a new main / new ruling does not retry
        rec2, posts2, _, _ = run(d=d, ops=FakeOps(), lag=new_lag, state=state)
        assert rec2["status"] == "SKIP" and "stopped on BIND-FAIL" in rec2["why"] and not posts2
    d2 = dict(d, tools_refresh_bind_cmd="x")                                              # the owner gave a recipe: resumes
    assert run(d=d2, ops=FakeOps(), lag=dict(LAG, missing=["r535", "r554", "r637"]), state=state)[0]["status"] == "APPLIED"
    d3 = dict(d, src="/x/new_tree")                                                       # or a new tree was applied
    assert TR.stop_fp(d3) != TR.stop_fp(d) and TR.stop_fp(dict(d, event="e2")) == TR.stop_fp(d)


def test_compose_failure_posts_needs_lane_and_stops():
    rec, posts, edits, state = run(ops=FakeOps(compose=False))
    assert rec["status"] == "COMPOSE-FAIL" and state["stopped"]["kv"]["status"] == "COMPOSE-FAIL"
    assert posts and posts[0].startswith("NEEDS-LANE [TOOLS-REFRESH -> KV-R3]") and "stopped (no retry)" in posts[0]


def test_single_flight_and_exit_codes(tmp_path, monkeypatch):
    import fcntl
    cfgp, st = tmp_path / "kit_wave.json", tmp_path / "state.json"
    cfgp.write_text(json.dumps({"dies": {"kv": {"tools_refresh": True, "src": "/x/t"}}}))
    held = open(tmp_path / "tools_refresh_kv.lock", "a")
    fcntl.flock(held, fcntl.LOCK_EX)                                                      # a pass is running
    out = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: out.append(" ".join(map(str, a))))
    assert TR.main(["--die", "kv", "--cfg", str(cfgp), "--state", str(st), "--repo", "/nonexistent"]) == 0
    assert json.loads(out[-1])["status"] == "BUSY" and not st.exists()                 # the second pass exits at once and writes nothing


def test_wave_does_not_start_a_stopped_die():
    import kit_wave as KW
    d = die()
    assert KW.tools_refresh_stop_fp(d) == TR.stop_fp(d)
    seen = []

    class AP:
        DRY = False
        AP_DIR = "/tmp/nodir_stop"
        log = staticmethod(lambda m: None)
        coord_append = staticmethod(lambda *a: None)
        launch_unit = staticmethod(lambda *a: seen.append(a))
    KW.TOOLS_LAG_CACHE["raw"] = {"kv": dict(LAG)}
    import pathlib, tempfile
    ap = pathlib.Path(tempfile.mkdtemp())
    (ap / "tools_refresh_state.json").write_text(json.dumps({"stopped": {"kv": {"fp": TR.stop_fp(d), "status": "BIND-FAIL"}}}))
    AP.AP_DIR = str(ap)
    KW.tools_refresh_tick(AP, {"dies": {"kv": dict(d, enabled=True)}}, {})
    assert not seen
    (ap / "tools_refresh_state.json").write_text(json.dumps({"stopped": {"kv": {"fp": "other", "status": "BIND-FAIL"}}}))
    KW.tools_refresh_tick(AP, {"dies": {"kv": dict(d, enabled=True)}}, {})
    assert len(seen) == 1


def test_apply_rekeys_pilot_and_tree_manifest_holds_atomically():
    old_h, new_h = "06dc15683502" + "0" * 4, "aabbccddeeff" + "1" * 4
    pilot = {"id": "pilot-kv-06dc15683502", "reason": "PILOT after tree 06dc15683502", "release": ["gen_pilot:kv:06dc15683502"], "items": ["*"],
             "pilot_items": ["it1"], "auto_pilot": True, "published_gen_proof": {"tree": OLD, "sha": "06dc15683502"}}
    tree = {"id": "t1", "release": ["tree_ready:kv:" + OLD, "result:L:tag"], "items": ["a"]}
    other = {"id": "other", "release": ["result:L:x"], "items": ["b"]}
    d = die(src_manifest_hash=old_h, hold_records=[pilot, tree, other])
    ops = FakeOps()
    ops.compose = lambda old, new: (True, "ok", new_h)
    rec, posts, edits, state = run(d=d, ops=ops)
    assert rec["status"] == "APPLIED" and len(edits) == 1               # one edit call = one atomic commit
    byp = {o["path"]: o for o in edits[0][0]}
    recs = byp["/dies/kv/hold_records"]["value"]
    new = TR.new_tree_path(OLD, SHA)
    assert recs[0]["id"] == "pilot-kv-aabbccddeeff" and recs[0]["release"] == ["gen_pilot:kv:aabbccddeeff"] and "aabbccddeeff" in recs[0]["reason"]
    assert recs[0]["pilot_items"] == ["it1"] and recs[0]["published_gen_proof"] == pilot["published_gen_proof"]
    assert recs[1]["release"] == ["tree_ready:kv:" + new, "result:L:tag"]
    assert recs[2] == other
    # no tree-keyed record: no hold_records op
    assert "/dies/kv/hold_records" not in {o["path"] for o in run(d=die(hold_records=[other]))[2][0][0]}


def test_tick_spawns_nothing_while_a_pass_holds_the_die_lock(tmp_path):
    import fcntl
    import kit_wave as KW
    launched = []

    class AP:
        DRY = False
        AP_DIR = str(tmp_path)
        log = staticmethod(lambda m: None)
        launch_unit = staticmethod(lambda unit, logf, argv: launched.append(unit))
    KW.TOOLS_LAG_CACHE["raw"] = {"kv": dict(LAG)}
    cfg = {"dies": {"kv": {"enabled": True, "tools_refresh": True}}}
    st = {}
    held = open(tmp_path / "tools_refresh_kv.lock", "a")
    fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)                      # a live pass
    assert KW.tools_refresh_pass_live(str(tmp_path), "kv")
    KW.tools_refresh_tick(AP, cfg, st)
    KW.tools_refresh_tick(AP, cfg, st)
    assert launched == [] and not st.get("tools_refresh_started")         # nothing spawned, nothing recorded as started
    fcntl.flock(held, fcntl.LOCK_UN)
    held.close()
    assert not KW.tools_refresh_pass_live(str(tmp_path), "kv")           # pass ended: the next tick starts it
    KW.tools_refresh_tick(AP, cfg, st)
    assert len(launched) == 1
    assert not KW.tools_refresh_pass_live(str(tmp_path / "none"), "kv")  # no lock file: not live, and none is created
    assert not (tmp_path / "none").exists()


def test_apply_moves_the_tools_pin_so_the_lag_check_stops_seeing_the_same_lag():
    d = die(tools_sha="8569788b0328")
    rec, posts, edits, state = run(d=d)
    assert rec["status"] == "APPLIED"
    byp = {o["path"]: o for o in edits[0][0]}
    assert byp["/dies/kv/tools_sha"]["op"] == "replace" and byp["/dies/kv/tools_sha"]["value"] == SHA
    import tools_lag as TL
    assert TL.pin_of(dict(d, tools_sha=byp["/dies/kv/tools_sha"]["value"])) == SHA          # the reader returns the new pin
    d2 = die()
    assert {o["path"]: o for o in run(d=d2)[2][0][0]}["/dies/kv/tools_sha"]["op"] == "add"     # a die with no pin gets one


def test_a_host_short_of_disk_is_dropped_not_a_compose_fail(monkeypatch):
    """LATENCY-R 11-18: replicate refused on one gen host (disk floor) -> the tree applies on the hosts that hold it; gen_hosts narrows in the same patch"""
    import overlay_classify as OC
    monkeypatch.setattr(OC, "classify_die", lambda repo, d, main, prefixes=None: {})
    d = die(gen_hosts=["epyc10", "epyc8", "epyc9"])

    def run_(host, cmd, timeout=0):
        if " replicate " in cmd:
            return 1, "epyc8: refuse (free 57 GB + part 0 - tree 47 = 49 GB after the copy < floor 50 + 20 GB)\nepyc9: linked from x\nepyc9: OK"
        if "delta.json" in cmd:
            return 0, json.dumps({"add": {"tools/a.py": 1}, "delete": []})
        return 0, "h"
    o = TR.Ops(d, "/r", SHA, run=run_)
    ok, detail, h = o.compose(OLD, "/n")
    assert ok and o.hosts == ["epyc10", "epyc9"] and list(o.dropped) == ["epyc8"] and "refuse" in o.dropped["epyc8"]
    seen = []
    o.run = lambda host, cmd, timeout=0: (seen.append(cmd) or (0, "ok"))
    o.guard("/n", "h")
    assert "--hosts epyc10,epyc9" in seen[0]
    ops = TR.patch_ops("kv", d, OLD, "/n", "h", SHA, hosts=o.hosts)
    assert {"op": "replace", "path": "/dies/kv/gen_hosts", "value": ["epyc10", "epyc9"]} in ops
    assert not [x for x in ops if x["path"] == "/dies/kv/gen_host"]                      # epyc10 still holds it


def test_refresh_records_dropped_hosts_and_narrows():
    class Drop(FakeOps):
        hosts = ["epyc10"]
        dropped = {"epyc8": "refuse"}
    rec, posts, edits, _ = run(ops=Drop())
    assert rec["status"] == "APPLIED" and rec["dropped_hosts"] == {"epyc8": "refuse"}
    assert {"op": "replace", "path": "/dies/kv/gen_hosts", "value": ["epyc10"]} in edits[0][0]
