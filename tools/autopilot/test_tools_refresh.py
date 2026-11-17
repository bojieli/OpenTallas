"""WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 A): automatic tools-only refresh; bind unchanged -> applied, bind changed -> NEEDS-LANE."""
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
    assert run(ops=FakeOps(compose=False))[1] == []                       # a compose failure is retried next tick, no lane noise


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
    assert "bind.py bind" in o.bind_cmd(new, "/o") and "--strict" in o.bind_cmd("/n", "/o")


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
