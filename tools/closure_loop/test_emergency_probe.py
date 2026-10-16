"""HOST-EMERGENCY probe step (drive-1010 2026-10-10): picks the largest adj>=0 process below the free-memory floor."""
import subprocess
import unittest

import closure_loop as cl


class Emergency(unittest.TestCase):
    def run_probe(self, floor_gb, rss_kb):
        s = cl.EMERGENCY_PROBE.replace(f"-lt {cl.EMERGENCY_FREE_GB}", f"-lt {floor_gb}") \
            .replace("-ge 8388608", f"-ge {rss_kb}").replace("kill -9 $v;", "true;") \
            .replace("/tmp/ot_emergency_kill.log", "/dev/null")
        return subprocess.run(["bash", "-c", s], capture_output=True, text=True)

    def test_syntax_and_no_action_with_headroom(self):
        r = self.run_probe(0, 8388608)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("OT_EMERGENCY_KILL", r.stdout)

    def test_selects_a_non_protected_process_below_floor(self):
        r = self.run_probe(10**9, 1)          # always "below floor", any RSS qualifies
        self.assertEqual(r.returncode, 0)
        line = [l for l in r.stdout.splitlines() if l.startswith("OT_EMERGENCY_KILL")]
        self.assertEqual(len(line), 1)
        pid = line[0].split()[1]
        comm = open(f"/proc/{pid}/comm").read().strip()
        self.assertNotIn(comm, ("sshd", "systemd", "dockerd", "containerd"))
        self.assertGreaterEqual(int(open(f"/proc/{pid}/oom_score_adj").read()), 0)

    def test_probe_runs_it(self):
        import inspect
        self.assertIn("{EMERGENCY_PROBE}", inspect.getsource(cl.Fleet._probe_once))


if __name__ == "__main__":
    unittest.main()
