#!/usr/bin/env python3
"""KW-FIX-32 RESYNTH-GUARD (COORD 20:2x, DIE-QC-91 20:15): a kit whose restored results are older than its config.mk /
sdc / rtl refuses a make-chain goal instead of silently re-synthesising; fresh kits, GOAL=synth, stage-resume kits
(resume.json, do-* path) and OT_ALLOW_RESYNTH=1 are unchanged.  The guard is run straight out of every runner source."""
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNERS = [
    "tools/die_plan/gen_phys.py",
    "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py",
    "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py",
    "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh",
    "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh",
]
HEAD = "# KW-FIX-32 RESYNTH-GUARD"


def guard_script(rel):
    """the runner's K/GOAL line + its guard block, as a standalone script that prints PASSED when the guard lets it on"""
    text = (REPO / rel).read_text()
    i = text.index(HEAD)
    k = text.rindex("\nK=$(cd", 0, i) + 1
    kline = text[k:text.index("\n", k) + 1]
    j = text.index("\nfi\n", text.index("exit 12", i)) + len("\nfi\n")
    return "set -uo pipefail\n" + kline + text[i:j] + "echo PASSED\n"


def kit(root, results=True, newer=True):
    K = Path(root) / "kit"
    (K / "rtl").mkdir(parents=True)
    base = K / "run/results/asap7/top/base"
    if results:
        base.mkdir(parents=True)
        for n in ("1_2_yosys.v", "1_synth.v", "2_floorplan.odb", "3_place.odb"):
            (base / n).write_text("x")
    old, now = time.time() - 7200, time.time()
    for p in base.glob("*") if results else []:
        os.utime(p, (old, old))
    for p in (K / "config.mk", K / "constraint.sdc", K / "rtl/top.sv"):
        p.write_text("y")
        t = now if newer else old - 3600
        os.utime(p, (t, t))
    return K


class ResynthGuard(unittest.TestCase):
    def run_guard(self, rel, K, goal, env=None):
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
            f.write(guard_script(rel))
        e = dict(os.environ)
        e.pop("OT_ALLOW_RESYNTH", None)
        e.update(env or {})
        p = subprocess.run(["bash", f.name, str(K), goal], capture_output=True, text=True, env=e)
        os.unlink(f.name)
        return p

    def test_copied_checkpoint_refuses_make_chain(self):
        for rel in RUNNERS:
            for goal in ("finish", "route", "grt", "cts"):
                with self.subTest(rel=rel, goal=goal), tempfile.TemporaryDirectory() as d:
                    p = self.run_guard(rel, kit(d), goal)
                    self.assertEqual(p.returncode, 12, p.stdout + p.stderr)
                    self.assertIn("RESYNTH-GUARD", p.stderr)
                    self.assertIn("do-* targets", p.stderr)
                    self.assertNotIn("PASSED", p.stdout)

    def test_unchanged_cases_pass(self):
        for rel in RUNNERS:
            with self.subTest(rel=rel, case="fresh kit"), tempfile.TemporaryDirectory() as d:
                self.assertIn("PASSED", self.run_guard(rel, kit(d, results=False), "finish").stdout)
            with self.subTest(rel=rel, case="sources older"), tempfile.TemporaryDirectory() as d:
                self.assertIn("PASSED", self.run_guard(rel, kit(d, newer=False), "finish").stdout)
            with self.subTest(rel=rel, case="synth"), tempfile.TemporaryDirectory() as d:
                self.assertIn("PASSED", self.run_guard(rel, kit(d), "synth").stdout)
            with self.subTest(rel=rel, case="stage resume"), tempfile.TemporaryDirectory() as d:
                K = kit(d)
                (K / "resume.json").write_text("{}")
                self.assertIn("PASSED", self.run_guard(rel, K, "finish").stdout)
            with self.subTest(rel=rel, case="override"), tempfile.TemporaryDirectory() as d:
                p = self.run_guard(rel, kit(d), "finish", {"OT_ALLOW_RESYNTH": "1"})
                self.assertIn("PASSED", p.stdout)

    def test_type_runner_fingerprint_unchanged(self):
        """the guard is outside the stage-resume runner fingerprint (kit_resume.runner_norm), so landing it does not
        force every resumed type relaunch back to synth"""
        import sys
        sys.path.insert(0, str(REPO / "tools/autopilot"))
        import kit_resume
        text = (REPO / "tools/die_plan/gen_phys.py").read_text()
        i = text.index(HEAD)
        b = text.rindex("\n", 0, i) + 1
        b = text.rindex("\n", 0, b - 1) + 1          # the '# KWRS-BEGIN' line above the guard
        e = text.index("# KWRS-END\n", i) + len("# KWRS-END\n")
        self.assertTrue(text[b:i].rstrip().endswith("# KWRS-BEGIN"))
        self.assertEqual(kit_resume.runner_norm(text), kit_resume.runner_norm(text[:b] + text[e:]))


if __name__ == "__main__":
    unittest.main()
