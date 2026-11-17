import json, os, tempfile, types, unittest
import derive_gen_hosts as G
import src_manifest as SM

T = "/srv/opentallas-scratch2/claude/kw45/src_x_d1"


def cfg(hosts):
    return {"dies": {"kv": {"src": T, "src_manifest_hash": "h1", "gen_hosts": list(hosts)}}}


class Derive(unittest.TestCase):
    def test_hosts_with_the_tree_hash_and_room_only(self):
        probes = {"a": ("h1", False, 200.0), "b": ("h1", False, 60.0), "c": ("", False, 300.0), "d": ("h1", True, 300.0), "e": ("old", False, 300.0)}
        res = G.derive(cfg(["a", "b", "c", "e"]), hosts=tuple(probes), prober=lambda h, t: probes[h])
        self.assertEqual(res["kv"][0], ["a"])                       # b: 60 GB free < 50 + 20; c/e lack the tree; d partial
        self.assertTrue(any("c: tree missing" in w for w in res["kv"][1]) and any("b: 60 GB free" in w for w in res["kv"][1]))

    def test_new_verified_host_is_added_after_the_current_ones(self):
        probes = {"a": ("h1", False, 200.0), "b": ("h1", False, 200.0)}
        res = G.derive(cfg(["a"]), hosts=("a", "b"), prober=lambda h, t: probes[h])
        self.assertEqual(res["kv"][0], ["a", "b"])

    def test_never_an_empty_list(self):
        res = G.derive(cfg(["a"]), hosts=("a",), prober=lambda h, t: ("", False, 10.0))
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
