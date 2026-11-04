"""A staged file's parent is marked only when the spill creates it (KW-FIX-8 11-04).  Runs the dst-side shell in a temp dir; no ssh, no job."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest
from unittest import mock

loader = importlib.machinery.SourceFileLoader('ot_run_stage', str(Path(__file__).with_name('ot-run')))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)
MARK = m.SPILL_MARK


class StagePre(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.lane = os.path.join(t.name, "claude", "lane")
        os.makedirs(self.lane)
        for name, val in (("SCRATCH_RE", re.compile("^(" + re.escape(t.name) + r"/claude/[^/]+)(/|$)")),):
            p = mock.patch.object(m, name, val)
            p.start()
            self.addCleanup(p.stop)
        self.gen = self.lane + "/a/gen"
        self.kit, self.run = self.gen + "/T", self.gen + "/run_kit.sh"
        p = mock.patch.object(m, "STAGE_FILES", {self.run})
        p.start()
        self.addCleanup(p.stop)

    def pre(self, roots):
        """the dst-side preparation of spill_fwd_cmd, tar and touch cut off"""
        dcmd = shlex.split(m.spill_fwd_cmd("epyc4", "dst", roots, "/tmp/stamp").split(" BatchMode=yes dst ", 1)[1])[0]
        cut = dcmd.index("flock ")
        return subprocess.run(["bash", "-c", dcmd[:cut]], capture_output=True, text=True)

    def test_created_parent_is_marked_and_next_spill_passes(self):
        for roots in ([self.kit, self.run], [self.run, self.kit]):
            with self.subTest(roots=roots):
                subprocess.run(["rm", "-rf", self.lane + "/a"], check=True)
                self.assertEqual(self.pre(roots).returncode, 0)
                self.assertTrue(os.path.exists(self.gen + "/" + MARK))
                Path(self.run).write_text("copy")          # what tar leaves
                r = self.pre(roots)
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_existing_parent_with_real_data_is_not_marked(self):
        os.makedirs(self.gen)
        Path(self.gen + "/real.db").write_text("real")
        self.assertEqual(self.pre([self.kit, self.run]).returncode, 0)
        self.assertFalse(os.path.exists(self.gen + "/" + MARK))

    def test_existing_unmarked_file_still_refuses_and_marks_nothing(self):
        os.makedirs(self.gen)
        Path(self.run).write_text("real")
        r = self.pre([self.kit, self.run])
        self.assertEqual(r.returncode, 3)
        self.assertIn("OT_SPILL_REAL", r.stderr)
        self.assertFalse(os.path.exists(self.gen + "/" + MARK))
        self.assertFalse(os.path.exists(self.kit))

    def test_marked_parent_lets_a_copied_file_pass(self):
        os.makedirs(self.gen)
        Path(self.gen + "/" + MARK).write_text("epyc4")
        Path(self.run).write_text("copy")
        self.assertEqual(self.pre([self.kit, self.run]).returncode, 0)

    def test_unmarked_lane_root_stays_unmarked(self):
        self.assertEqual(self.pre([self.kit, self.run]).returncode, 0)
        self.assertFalse(os.path.exists(self.lane + "/" + MARK))


if __name__ == "__main__":
    unittest.main()
