"""landed_raw_tap.tcl OT_LRT_BATCH (ROOT3 2026-10-19): the batched tap (L2H-PGVM 84d1b9ee6) is opt-in; the default
per-pin loop is unchanged.  Mock OpenROAD (lrt_batched_mock.tcl, independent raw pins): both forms build the same
chains, the batched one with fewer estimate_parasitics rounds."""
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "physical/common_flow/landed_raw_tap.tcl"
MOCK = Path(__file__).resolve().parent / "lrt_batched_mock.tcl"


def run(batch):
    env = dict(os.environ)
    env.pop("OT_PG_STRICT", None)
    if batch is None:
        env.pop("OT_LRT_BATCH", None)
    else:
        env["OT_LRT_BATCH"] = batch
    r = subprocess.run(["tclsh", str(MOCK), str(HOOK)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    m = re.search(r"estimates=(\d+) chains=(.*)$", r.stdout.strip().splitlines()[-1])
    return int(m.group(1)), m.group(2).strip(), r.stdout


@unittest.skipUnless(shutil.which("tclsh"), "tclsh not installed")
class LrtBatched(unittest.TestCase):
    def test_default_is_the_per_pin_loop(self):
        est, chains, out = run(None)
        self.assertEqual(run("0")[:2], (est, chains))
        self.assertNotIn("OT_LRT batched", out)
        self.assertEqual(est, 16)

    def test_batched_same_chains_fewer_rounds(self):
        est0, ch0, _ = run(None)
        est1, ch1, out = run("1")
        self.assertEqual(ch1, ch0)
        self.assertEqual(ch0, "I0_ckr 3 I1_ckr 2 I2_ckr 5")
        self.assertLess(est1, est0)
        self.assertIn("OT_LRT batched: 3 raw pins", out)


if __name__ == "__main__":
    unittest.main()
