import json, os, tempfile, time, types, unittest
import lane_quota as Q


class Quota(unittest.TestCase):
    def test_scan_counts_recent_bytes_per_lane_hardlinks_once_and_skips_infra(self):
        root = tempfile.mkdtemp()
        for lane in ("big", "small", "rt"):
            os.makedirs(os.path.join(root, lane))
        with open(os.path.join(root, "big", "f"), "wb") as f: f.truncate(0); f.write(b"x" * 4096 * 300)
        os.link(os.path.join(root, "big", "f"), os.path.join(root, "big", "g"))
        open(os.path.join(root, "small", "f"), "w").write("x"); open(os.path.join(root, "rt", "f"), "w").write("x" * 10 ** 6)
        got = Q.scan(root, 6, 0.001)
        self.assertEqual(list(got), ["big"]); self.assertLess(got["big"], 0.0013 * 1.5)       # 1.2 MB once, not twice
        self.assertEqual(Q.scan(root, 6, 150), {})
        self.assertEqual(Q.scan(root, 6, 0.001, now=time.time() + 10 ** 6), {})                 # nothing written inside the window

    def test_hub_posts_once_per_lane_per_day(self):
        coord = tempfile.mkdtemp(); posts = []
        def run(cmd, **kw):
            if cmd[0] == "ssh": return types.SimpleNamespace(stdout=json.dumps({"laneA": 200.0}) + "\n")
            posts.append(cmd[-1]); return types.SimpleNamespace(stdout="")
        st = os.path.join(coord, "st.json"); a = Q.hub(["epyc7"], coord, run=run, state=st); b = Q.hub(["epyc7"], coord, run=run, state=st)
        self.assertEqual(len(a), 1); self.assertEqual(b, []); self.assertIn("laneA on epyc7 wrote 200 GB", a[0]); self.assertIn("alert only", posts[0])


class Tiers(unittest.TestCase):
    def test_burst_tier_catches_a_39gb_clone_and_a_dead_host_does_not_abort_the_poll(self):
        root = tempfile.mkdtemp(); os.makedirs(root + "/scratch2/claude/laneA"); os.makedirs(root + "/scratch3/claude/laneB")
        for lane in ("scratch2/claude/laneA", "scratch3/claude/laneB"):
            with open(os.path.join(root, lane, "f"), "wb") as f: f.write(b"x" * 4096 * 20)
        Q.BURST_GB = 0.00005; Q.QUOTA_GB = 10 ** 6
        got = Q.scan_all(roots=(root + "/scratch2/claude", root + "/scratch3/claude"))
        self.assertIn("laneA", got); self.assertTrue(any(k == "scratch3:laneB" for k in got), got)
        coord = tempfile.mkdtemp(); posts = []
        def run(cmd, **kw):
            if cmd[0] == "ssh" and cmd[6] == "bad": raise TimeoutError("slow host")
            if cmd[0] == "ssh": return types.SimpleNamespace(stdout=json.dumps({"laneX": 40.0}) + "\n")
            posts.append(cmd[-1]); return types.SimpleNamespace(stdout="")
        out = Q.hub(["bad", "good"], coord, run=run, state=os.path.join(coord, "s.json"))
        self.assertEqual(len(out), 1); self.assertIn("laneX on good", out[0])


def test_remote_scan_is_idle_io_and_time_capped():
    seen = []
    import types
    def run(cmd, **k):
        seen.append(cmd[-1]); return types.SimpleNamespace(stdout="{}", stderr="", returncode=0)
    import tempfile, os
    Q.hub(["h1"], tempfile.mkdtemp(), run=run, state=tempfile.mkdtemp() + "/s.json")
    assert "ionice -c3" in seen[0] and "timeout 600" in seen[0] and "rt/current/tools/fleet/lane_quota.py" in seen[0]
