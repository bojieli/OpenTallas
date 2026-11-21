import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("pr", Path(__file__).with_name("post_redirect.py"))
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)

ST = {
    "A": ("stood-down", "B", "x"),
    "B": ("stood-down", "C", "x"),
    "C": ("live", "", "x"),
    "L1": ("stood-down", "L2", "x"),
    "L2": ("stood-down", "L1", "x"),
}


class RedirectTests(unittest.TestCase):
    def test_chain(self):
        self.assertEqual(pr.resolve("A", ST), ["B", "C"])
        self.assertEqual(pr.resolve("C", ST), [])
        self.assertEqual(pr.resolve("ZZ", ST), [])

    def test_cycle(self):
        self.assertEqual(pr.resolve("L1", ST), ["L2"])

    def test_rewrite_adds_final_successor(self):
        t, n = pr.rewrite("- 2026 X [Q -> A, COORD; cc D] hi\n  more", ST)
        self.assertIn("[Q -> A, COORD, C; cc D]", t)
        self.assertTrue(t.endswith("\n  more"))
        self.assertEqual(len(n), 1)
        self.assertIn("REDIRECTED A -> C", n[0])

    def test_no_dup_and_live_untouched(self):
        t, n = pr.rewrite("- 2026 X [Q -> A, C] hi", ST)
        self.assertEqual(t, "- 2026 X [Q -> A, C] hi")
        t, n = pr.rewrite("- 2026 X [Q -> C] hi", ST)
        self.assertEqual((t, n), ("- 2026 X [Q -> C] hi", []))

    def test_no_header(self):
        self.assertEqual(pr.rewrite("plain", ST), ("plain", []))

    def test_post_sh_end_to_end(self):
        coord_post = Path(__file__).resolve().parents[1] / "bin" / "post.sh"
        if not coord_post.exists():
            self.skipTest("no post.sh")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "lanes").mkdir()
            (Path(d) / "lanes/LANE-STATUS.tsv").write_text("lane\tstatus\tsuccessor\tupdated\nA\tstood-down\tC\t2026-11-20\n")
            (Path(d) / "bin").mkdir()
            (Path(d) / "bin/coord-commit.sh").write_text("#!/bin/bash\nexit 0\n")
            (Path(d) / "tools").mkdir()
            (Path(d) / "tools/post_redirect.py").write_text(Path(pr.__file__).read_text())
            import os
            r = subprocess.run(["bash", str(coord_post), "T", "TAG [T -> A] x"], capture_output=True, text=True,
                               env={**os.environ, "COORD_DIR": d})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("REDIRECTED A -> C", r.stderr)
            self.assertIn("[T -> A, C]", (Path(d) / "lanes/posts/T.md").read_text())


if __name__ == "__main__":
    unittest.main()
