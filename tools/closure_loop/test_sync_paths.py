"""SYNC-PATHS (drive-1010 2026-10-10): extra_paths missing at the commit fail once with the path; default configs/src."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="syncpaths_"))
import closure_loop as cl  # noqa: E402


def run(*a, cwd):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


class SyncPaths(unittest.TestCase):
    def setUp(self):
        t = Path(tempfile.mkdtemp()); self.repo = t / "r"
        run("init", "-q", "-b", "main", str(self.repo), cwd=t)
        for f in ("tools/a.py", "rtl/a.sv", "physical/x", "Makefile", "results/uarch/m.json"):
            (self.repo / f).parent.mkdir(parents=True, exist_ok=True); (self.repo / f).write_text("x\\n")
        run("add", "-A", cwd=self.repo); run("commit", "-qm", "c", cwd=self.repo)
        self.c = run("rev-parse", "HEAD", cwd=self.repo)
        run("update-ref", "refs/remotes/origin/main", self.c, cwd=self.repo)
        for p in (patch.object(cl, "REPO", self.repo), patch.object(cl, "gfetch"), patch.object(cl, "require_checkpoint_location"),
                  patch.object(cl, "log")):
            p.start(); self.addCleanup(p.stop)

    def job(self, extra):
        return {"name": "j", "host": "h", "run": "/r/j", "spec": {"name": "j", "stages": {}, "source": {
            "branch": "main", "commit": self.c, "extra_paths": extra}}}

    def test_missing_extra_path_is_terminal_and_named(self):
        with self.assertRaisesRegex(ValueError, "results/uarch/missing.json"):
            cl.sync_source(self.job(["results/uarch/missing.json"]))

    def test_defaults_skip_absent_dirs_and_keep_present_extra(self):
        seen = {}
        class Stop(Exception):
            pass
        def capture(spec, paths, full):
            seen["paths"] = list(paths); raise Stop
        with patch.object(cl, "implied_src_paths", side_effect=capture):
            with self.assertRaises(Stop):
                cl.sync_source(self.job(["results/uarch/m.json"]))
        self.assertEqual(seen["paths"], ["tools", "rtl", "physical", "Makefile", "results/uarch/m.json"])   # no configs/src at this commit
        self.assertIn("configs", cl.DEFAULT_SRC_PATHS)
        self.assertIn("src", cl.DEFAULT_SRC_PATHS)


if __name__ == "__main__":
    unittest.main()
