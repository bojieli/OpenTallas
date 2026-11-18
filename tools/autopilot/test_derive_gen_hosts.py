import json, os, tempfile, types, unittest
import derive_gen_hosts as G
import src_manifest as SM

T = "/srv/opentallas-scratch2/claude/kw45/src_x_d1"


def cfg(hosts):
    return {"dies": {"kv": {"src": T, "src_manifest_hash": "h1", "gen_hosts": list(hosts)}}}


class Derive(unittest.TestCase):
    def test_hosts_with_the_tree_hash_and_room_only(self):
        probes = {"a": ("h1", False, 200.0), "b": ("h1", False, 60.0), "c": ("", False, 300.0), "d": ("h1", True, 300.0), "e": ("old", False, 300.0)}
        res = G.derive(cfg(["a", "b", "c", "e"]), hosts=tuple(probes), prober=lambda h, t: probes[h], checker=lambda h, p: [])
        self.assertEqual(res["kv"][0], ["a"])                       # b: 60 GB free < 50 + 20; c/e lack the tree; d partial
        self.assertTrue(any("c: tree missing" in w for w in res["kv"][1]) and any("b: 60 GB free" in w for w in res["kv"][1]))

    def test_new_verified_host_is_added_after_the_current_ones(self):
        probes = {"a": ("h1", False, 200.0), "b": ("h1", False, 200.0)}
        res = G.derive(cfg(["a"]), hosts=("a", "b"), prober=lambda h, t: probes[h], checker=lambda h, p: [])
        self.assertEqual(res["kv"][0], ["a", "b"])

    def test_never_an_empty_list(self):
        res = G.derive(cfg(["a"]), hosts=("a",), prober=lambda h, t: ("", False, 10.0), checker=lambda h, p: [])
        self.assertEqual(res["kv"][0], ["a"]); self.assertTrue(res["kv"][1][0].startswith("ALERT"))

    def test_apply_rewrites_under_the_lock_and_commits(self):
        c = tempfile.mkdtemp(); os.makedirs(c + "/autopilot"); os.makedirs(c + "/bin")
        json.dump(cfg(["a", "b"]), open(c + "/autopilot/kit_wave.json", "w")); calls = []
        done = G.apply(c, {"kv": (["a"], [])}, run=lambda cmd, **k: calls.append(cmd) or types.SimpleNamespace(returncode=0))
        d = json.load(open(c + "/autopilot/kit_wave.json"))["dies"]["kv"]
        self.assertEqual((d["gen_hosts"], d["prev_gen_hosts_derive"], done), (["a"], ["a", "b"], ["kv=a"])); self.assertIn("autopilot/kit_wave.json", calls[0])


class Room(unittest.TestCase):
    def test_copy_must_leave_floor_plus_20(self):
        self.assertEqual(SM.room_after_copy(120, 49)[0], True)        # 71 left >= 70
        self.assertEqual(SM.room_after_copy(118, 49)[0], False)       # 69 left
        self.assertEqual(SM.room_after_copy(95, 49, part_gb=30)[0], True)   # 95 + 30 already written - 49 = 76 left
        self.assertEqual(SM.room_after_copy(100, 57, floor_gb=80)[0], False)


class Log(unittest.TestCase):
    def test_main_logs_every_die_and_marks_applied_changes(self):
        c = tempfile.mkdtemp(); os.makedirs(c + "/autopilot"); os.makedirs(c + "/bin")
        json.dump(cfg(["a", "b"]), open(c + "/autopilot/kit_wave.json", "w")); open(c + "/bin/coord-commit.sh", "w").write("#!/bin/bash\nexit 0\n"); os.chmod(c + "/bin/coord-commit.sh", 0o755)
        G.probe = lambda h, t, run=None: ("h1", False, 200.0) if h == "a" else ("", False, 200.0)
        orig = G.derive.__defaults__
        G.derive.__defaults__ = (G.HOSTS, G.probe, None, lambda h, p: [])
        try:
            lg = c + "/derive.log"
            G.main(["--coord", c, "--hosts", "a,b", "--apply", "--log", lg])
        finally:
            G.derive.__defaults__ = orig
        txt = open(lg).read()
        self.assertIn("kv a,b -> a APPLIED", txt); self.assertIn("b: tree missing or other hash", txt)
        self.assertEqual(json.load(open(c + "/autopilot/kit_wave.json"))["dies"]["kv"]["gen_hosts"], ["a"])


class Requires(unittest.TestCase):
    def test_a_host_without_the_required_tool_path_is_not_a_gen_host(self):
        probes = {"a": ("h1", False, 200.0), "b": ("h1", False, 200.0)}
        seen = []
        def checker(h, paths):
            seen.append((h, paths)); return [] if h == "a" else [paths[0]]
        res = G.derive(cfg(["a", "b"]), hosts=("a", "b"), prober=lambda h, t: probes[h], checker=checker)
        self.assertEqual(res["kv"][0], ["a"]); self.assertTrue(any("b: lacks ~/.local/opentallas-pdk-asap7/lib" in w for w in res["kv"][1]))
        self.assertEqual(seen[0][1], G.REQUIRES_DEFAULT)

    def test_a_die_can_override_or_drop_the_requirement(self):
        probes = {"a": ("h1", False, 200.0)}
        c = cfg(["a"]); c["dies"]["kv"]["host_requires"] = []
        res = G.derive(c, hosts=("a",), prober=lambda h, t: probes[h], checker=lambda h, p: ["x"])
        self.assertEqual(res["kv"][0], ["a"])                                     # no requirement: the checker is never consulted
        c["dies"]["kv"]["host_requires"] = ["~/.local/x"]
        res = G.derive(c, hosts=("a",), prober=lambda h, t: probes[h], checker=lambda h, p: list(p))
        self.assertTrue(res["kv"][1][0].startswith("ALERT"))                      # nothing qualifies: list kept + ALERT

    def test_host_requires_reports_missing_paths_and_unreachable_hosts(self):
        import types
        run = lambda cmd, **k: types.SimpleNamespace(returncode=0, stdout="MISSING '~/.local/opentallas-pdk-asap7/lib'\n")
        self.assertEqual(G.host_requires("h", ("~/.local/opentallas-pdk-asap7/lib",), run=run), ["~/.local/opentallas-pdk-asap7/lib"])
        bad = lambda cmd, **k: (_ for _ in ()).throw(OSError("down"))
        self.assertEqual(G.host_requires("h", ("~/a", "~/b"), run=bad), ["~/a", "~/b"])


def test_per_host_min_free_floor_drops_a_host_until_it_has_the_room():
    import derive_gen_hosts as D
    cfg = {"dies": {"s81": {"src": "/t", "src_manifest_hash": "h", "gen_hosts": ["a", "b"], "gen_host_min_free_gb": {"b": 150}}}}
    pr = lambda host, tree: ("h", False, {"a": 100.0, "b": 137.0}[host])
    out = D.derive(cfg, hosts=("a", "b"), prober=pr, checker=lambda h, need: [])
    assert out["s81"][0] == ["a"] and any("b: 137 GB free < 150" in w for w in out["s81"][1])
    pr2 = lambda host, tree: ("h", False, {"a": 100.0, "b": 160.0}[host])
    assert D.derive(cfg, hosts=("a", "b"), prober=pr2, checker=lambda h, need: [])["s81"][0] == ["a", "b"]
