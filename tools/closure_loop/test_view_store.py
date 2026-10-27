"""el1013-fleet3 2026-10-13: closed .lib/.lef views are stored once per run root and hard-linked into job trees."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import closure_loop as C
import git_mirror as G


def sh(script, **k):
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, **k)


class ViewStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.repo = self.d / "repo"
        (self.repo / "physical/v").mkdir(parents=True)
        (self.repo / "tools").mkdir()
        (self.repo / "physical/v/big.lib").write_bytes(b"L" * (G.VIEW_MIN_BYTES + 5))
        (self.repo / "physical/v/big.lef").write_bytes(b"F" * (G.VIEW_MIN_BYTES + 9))
        (self.repo / "physical/v/small.lib").write_text("small\n")
        (self.repo / "physical/v/odd name.lib").write_bytes(b"O" * (G.VIEW_MIN_BYTES + 1))   # not a plain path: archived
        (self.repo / "tools/t.py").write_text("print(1)\n")
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                      capture_output=True, text=True, check=True).stdout.strip()
        g("init", "-q")
        g("add", ".")
        g("commit", "-q", "-m", "a")
        self.full = g("rev-parse", "HEAD")
        self.g = g
        self.base = self.d / "base"
        self.base.mkdir()

    def tearDown(self):
        subprocess.run(["chmod", "-R", "u+w", self.tmp.name])
        self.tmp.cleanup()

    def extract(self, run, full=None, **k):
        s = G.extract_script(str(self.repo / ".git"), full or self.full, ["tools", "physical"], str(self.base / run), **k)
        r = sh(s)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("GIT_MIRROR_EXTRACTED", r.stdout)
        return r.stdout

    def test_views_are_linked_once_and_the_tree_is_identical(self):
        self.extract("plain")
        out = self.extract("a", view_store=True)
        self.assertIn("GIT_MIRROR_VIEWS 2 ", out)
        self.extract("b", view_store=True)
        self.assertEqual(sh(f"diff -r {self.base}/plain/src {self.base}/a/src").returncode, 0)
        big = self.base / "a/src/physical/v/big.lib"
        self.assertEqual(os.stat(big).st_ino, os.stat(self.base / "b/src/physical/v/big.lib").st_ino)
        self.assertEqual(os.stat(big).st_nlink, 3)                       # store + two jobs
        self.assertEqual(os.stat(big).st_mode & 0o777, 0o444)
        self.assertEqual(os.stat(self.base / "a/src/physical/v/small.lib").st_nlink, 1)
        self.assertEqual(os.stat(self.base / "a/src/physical/v/odd name.lib").st_nlink, 1)
        self.assertEqual(len([x for x in os.listdir(self.base / G.VIEW_STORE_DIR) if not x.startswith(".")]), 2)

    def test_changed_view_adds_one_entry_and_a_bad_entry_is_rebuilt(self):
        self.extract("a", view_store=True)
        store = self.base / G.VIEW_STORE_DIR
        victim = next(x for x in store.iterdir() if not x.name.startswith("."))
        os.chmod(victim, 0o644)
        victim.write_bytes(b"corrupt")                                   # wrong size
        (self.repo / "physical/v/big.lef").write_bytes(b"G" * (G.VIEW_MIN_BYTES + 77))
        self.g("commit", "-q", "-am", "b")
        new = self.g("rev-parse", "HEAD")
        self.extract("c", full=new, view_store=True)
        self.extract("ref", full=new)
        self.assertEqual(sh(f"diff -r {self.base}/ref/src {self.base}/c/src").returncode, 0)

    def test_resync_over_an_existing_src_never_writes_through_a_store_link(self):
        self.extract("a", view_store=True)
        self.extract("b", view_store=True)
        self.extract("a", view_store=True)                               # resumed job: src not empty
        self.extract("plain")
        self.assertEqual(sh(f"diff -r {self.base}/plain/src {self.base}/a/src").returncode, 0)
        self.assertEqual(sh(f"diff -r {self.base}/plain/src {self.base}/b/src").returncode, 0)

    def test_receipt_archive_is_never_thinned(self):
        receipt = dict(commit="b" * 40, paths=["tools"], archive_sha256="0" * 64, required_sha256={"tools/t.py": "1" * 64})
        s = G.extract_script("/m", "b" * 40, ["tools"], "/run", receipt, view_store=True)
        self.assertNotIn("export-ignore", s)
        self.assertNotIn(G.VIEW_STORE_DIR, s)

    def test_bench_copy_links_the_views_and_copies_the_rest(self):
        self.extract("a", view_store=True)
        self.extract("plain")
        for run in ("a", "plain"):
            src, priv = self.base / run / "src", self.base / run / "bench_src_a1"
            r = sh("set -e\n" + C.bench_copy_script(str(src), str(priv)) + "pwd\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), str(priv))
            self.assertEqual(sh(f"diff -r {src} {priv}").returncode, 0)
            self.assertNotEqual(os.stat(src / "tools/t.py").st_ino, os.stat(priv / "tools/t.py").st_ino)
        a = self.base / "a"
        self.assertEqual(os.stat(a / "src/physical/v/big.lib").st_ino, os.stat(a / "bench_src_a1/physical/v/big.lib").st_ino)
        p = self.base / "plain"
        self.assertNotEqual(os.stat(p / "src/physical/v/big.lib").st_ino, os.stat(p / "bench_src_a1/physical/v/big.lib").st_ino)
        (a / "bench_src_a1/tools/t.py").write_text("changed\n")           # a bench edits its private tree only
        self.assertEqual((a / "src/tools/t.py").read_text(), "print(1)\n")


if __name__ == "__main__":
    unittest.main()
