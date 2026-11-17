import os, tempfile, unittest
import disk_rate as D


class Auto(unittest.TestCase):
    def test_not_under_two_hours_or_not_scratch2_does_nothing(self):
        self.assertEqual(D.auto_retire("epyc8", "/srv/opentallas-scratch2", 2.5), "")
        self.assertEqual(D.auto_retire("epyc8", "/srv/opentallas-scratch", 1.0), "")

    def test_without_the_switch_file_it_only_says_what_it_would_do(self):
        sw = os.path.join(tempfile.mkdtemp(), "ON")
        calls = []
        t = D.auto_retire("epyc8", "/srv/opentallas-scratch2", 1.0, switch=sw, run=lambda *a, **k: calls.append(a))
        self.assertIn("OFF", t); self.assertEqual(calls, [])

    def test_with_the_switch_it_runs_apply_on_that_host_and_reports_df(self):
        sw = os.path.join(tempfile.mkdtemp(), "ON"); open(sw, "w").write("")
        seen = []
        def run(cmd, **k):
            seen.append(cmd)
            return type("R", (), {"returncode": 0, "stdout": "df before: 150G\nDELETED x\nDELETED y\nREFUSED: z referenced\ndf after: 400G\n"})()
        t = D.auto_retire("epyc8", "/srv/opentallas-scratch2", 1.0, switch=sw, run=run)
        self.assertIn("epyc8", seen[0]); self.assertTrue(seen[0][-1].endswith("apply"))
        self.assertIn("df before: 150G / df after: 400G", t); self.assertIn("deleted 2", t)
