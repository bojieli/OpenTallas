"""Admitted gate work has no wall cap unless an operator explicitly opts in."""
import os
import re
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
import pre_route_gate as PG  # noqa: E402


def capped_fn(cap):
    m = re.search(r"^ot_capped\(\) \{\{.*?^\}\}$", PG.REMOTE_SH, re.S | re.M)
    return m.group(0).replace("{{", "{").replace("}}", "}").replace("{STEP_CAP}", str(cap))


def run(cap, cmd):
    script = "docker() { echo \"DOCKER $*\" >> \"$OT_T\"; }\n" + capped_fn(cap) + f"\not_capped gate_cts_x {cmd}; echo RC=$?\n"
    t0 = time.time()
    import os, tempfile
    with tempfile.NamedTemporaryFile("r") as f:
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120, env=dict(os.environ, OT_T=f.name))
        return r.stdout + f.read(), time.time() - t0


class GateStepCap(unittest.TestCase):
    def test_overrun_is_killed_and_reported(self):
        out, dt = run(1, "sleep 30")
        self.assertLess(dt, 20)
        self.assertIn("GATE_TIMEOUT gate_cts_x exceeded explicit 1 s wall cap", out)
        self.assertIn("DOCKER kill gate_cts_x", out)
        self.assertNotIn("RC=0", out)

    def test_default_runs_without_timeout_or_docker_kill(self):
        # Shadow timeout: reaching it would fail even though the payload succeeds.
        out, _ = run(0, "bash -c 'sleep 0.1; exit 7'")
        self.assertIn("RC=7", out)
        self.assertNotIn("DOCKER kill", out)
        self.assertNotIn("GATE_TIMEOUT", out)
        fn = capped_fn(0)
        script = "timeout() { echo UNEXPECTED_TIMEOUT; return 99; }\n" + fn + "\not_capped gate_cts_x true; echo RC=$?"
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=5)
        self.assertIn("RC=0", r.stdout)
        self.assertNotIn("UNEXPECTED_TIMEOUT", r.stdout)

    def test_sigkill_is_not_relabelled_as_wall_timeout(self):
        out, _ = run(30, "bash -c 'kill -KILL $$'")
        self.assertIn("RC=137", out)
        self.assertNotIn("GATE_TIMEOUT", out)
        self.assertNotIn("DOCKER kill", out)

    def test_fast_step_untouched(self):
        out, _ = run(30, "true")
        self.assertNotIn("GATE_TIMEOUT", out)
        self.assertIn("RC=0", out)

    def test_gate_parses_stall_as_fail(self):
        self.assertEqual(PG.GATE_STEP_CAP_S, int(os.environ.get("OT_GATE_STEP_CAP_S", "0")))
        self.assertIn('get("OT_GATE_STEP_CAP_S", "0")', Path(PG.__file__).read_text())
        self.assertIn("ot_capped gate_cts_", PG.REMOTE_SH)
        self.assertIn("ot_capped gate_grt_", PG.REMOTE_SH)


if __name__ == "__main__":
    unittest.main()
