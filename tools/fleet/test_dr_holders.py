import unittest
import disk_rate as D

LSOF = "p100\ncgit\ns7000000000\nn/srv/opentallas-scratch2/x/pack.pack (deleted)\ns1000000000\nn/srv/opentallas-scratch2/x/b.pack (deleted)\np200\ncother\ns9000000000\nn/tmp/y (deleted)\np300\ncpy\ns50\nn/srv/opentallas-scratch2/z (deleted)\n"


class Holders(unittest.TestCase):
    def test_parse_sums_per_pid_and_filters_mount(self):
        r = D.parse_holders(LSOF, "/srv/opentallas-scratch2")
        self.assertEqual([x[0] for x in r], ["100", "300"]); self.assertAlmostEqual(r[0][2], 8.0)

    def test_holders_text_names_pid_cmd_gb(self):
        def run(argv, **k):
            out = LSOF if "lsof" in argv[-1] or "lsof" in " ".join(argv) else "git log -S foo\n"
            return type("R", (), {"stdout": out})()
        t = D.holders_text("epyc8", "/srv/opentallas-scratch2", run=run)
        self.assertIn("pid 100", t); self.assertIn("git log -S foo", t); self.assertIn("8.0 GB", t)

    def test_levels(self):
        self.assertEqual([D.level(x) for x in (None, 7, 5, 1.5, 0.5)], [0, 0, 1, 2, 3])


class OncePerState(unittest.TestCase):
    def test_one_alert_per_state_change(self):
        import tempfile, os, json
        D.HIST = os.path.join(tempfile.mkdtemp(), "h.json")
        vals = iter([600e9 - 50e9 * i for i in range(8)])
        D.HOSTS = ["epyc8"]; D.sample = lambda host: {"/srv/opentallas-scratch2": next(vals)}
        n = []
        for i in range(8):
            n.append(len(D.main(post=False, now=1000.0 + 1800 * i, pusher=lambda *a: None, clearer=lambda *a: None, stopper=lambda *a: "", holder=lambda h, d: " LSOF")))
        self.assertLessEqual(sum(n), 3)   # 8 runs of a steady fall: at most one alert per state (1,2,3), never one per run
        self.assertGreaterEqual(sum(n), 1)


if __name__ == "__main__":
    unittest.main()
