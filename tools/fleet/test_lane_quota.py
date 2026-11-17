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
        a = Q.hub(["epyc7"], coord, run=run); b = Q.hub(["epyc7"], coord, run=run)
        self.assertEqual(len(a), 1); self.assertEqual(b, []); self.assertIn("laneA on epyc7 wrote 200 GB", a[0]); self.assertIn("alert only", posts[0])
