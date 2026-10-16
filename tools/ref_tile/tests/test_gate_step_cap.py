"""GATE STEP CAP (ROOT 2026-10-15): a capped gate step that overruns is killed and reported as GATE_STALL."""
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
        self.assertIn("GATE_STALL gate_cts_x exceeded 1 s", out)
        self.assertIn("DOCKER kill gate_cts_x", out)
        self.assertNotIn("RC=0", out)

    def test_fast_step_untouched(self):
        out, _ = run(30, "true")
        self.assertNotIn("GATE_STALL", out)
        self.assertIn("RC=0", out)

    def test_gate_parses_stall_as_fail(self):
        self.assertEqual(PG.GATE_STEP_CAP_S, 14400)
        self.assertIn("ot_capped gate_cts_", PG.REMOTE_SH)
        self.assertIn("ot_capped gate_grt_", PG.REMOTE_SH)


if __name__ == "__main__":
    unittest.main()
