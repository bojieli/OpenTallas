"""SRCCOPY_1111 (KW-FIX-44, COORD 11-11): a git-tracked unmodified signed record in a pushed checkout whose canonical copy is in
the signed store is a source copy, not counted.  Every failed condition keeps it counted."""
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("oa_sc", os.path.join(HERE, "ot-autoclean.py"))
oa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oa)
SIGNED = {"verdict": "SIGNED", "name": "blk", "views": "/srv/opentallas-scratch2/claude/elsewhere/blk/6_final.odb"}


def git(d, *a):
    subprocess.run(["git", "-C", d] + list(a), check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.origin = os.path.join(self.d, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", self.origin], check=True)
        self.wt = os.path.join(self.d, "wt")
        subprocess.run(["git", "clone", "-q", self.origin, self.wt], check=True, capture_output=True)
        self.recdir = os.path.join(self.wt, "results/signoff/blk")
        os.makedirs(self.recdir)
        self.rec = os.path.join(self.recdir, "signoff.json")
        self.text = json.dumps(SIGNED)
        open(self.rec, "w").write(self.text)
        open(os.path.join(self.recdir, "blk.lef"), "w").write("MACRO blk\n")
        git(self.wt, "add", "-A")
        git(self.wt, "commit", "-q", "-m", "rec")
        git(self.wt, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.sha = hashlib.sha256(open(self.rec, "rb").read()).hexdigest()
        self.store = os.path.join(self.d, "store.json")
        self.write_store({self.sha: {"archive": "/archive/opentallas-signed-1106/intel1",
                                     "locs": ["intel1:/srv/opentallas-scratch2/claude/elsewhere/blk/signoff.json"]}})

    def write_store(self, idx):
        json.dump(idx, open(self.store, "w"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def check(self, text=None):
        return oa.SourceCopy(self.store, "localhost").check(self.rec, self.text if text is None else text)


class TestSourceCopy(Base):
    def test_source_copy(self):
        self.assertIsNone(self.check())

    def test_modified_file_keeps(self):
        open(self.rec, "a").write(" ")
        self.assertIsNotNone(self.check())

    def test_untracked_in_record_dir_keeps(self):
        open(os.path.join(self.recdir, "6_final.odb"), "w").write("x")
        self.assertIn("differs", self.check())

    def test_ignored_in_record_dir_keeps(self):
        open(os.path.join(self.wt, ".gitignore"), "w").write("*.odb\n")
        git(self.wt, "add", ".gitignore"); git(self.wt, "commit", "-q", "-m", "ig"); git(self.wt, "push", "-q", "origin", "HEAD:refs/heads/main")
        open(os.path.join(self.recdir, "6_final.odb"), "w").write("x")
        self.assertIn("differs", self.check())

    def test_staged_change_keeps(self):
        open(os.path.join(self.recdir, "blk.lef"), "w").write("MACRO other\n")
        git(self.wt, "add", "-A")
        self.assertIsNotNone(self.check())

    def test_head_not_on_origin_keeps(self):
        open(os.path.join(self.wt, "x.txt"), "w").write("x")
        git(self.wt, "add", "x.txt"); git(self.wt, "commit", "-q", "-m", "local only")
        self.assertEqual(self.check(), "HEAD not on origin")

    def test_fetch_failure_keeps(self):
        shutil.rmtree(self.origin)
        self.assertEqual(self.check(), "fetch origin failed")

    def test_fetch_is_fresh_not_cached(self):
        # the remote-tracking ref still says the commit is on origin, but origin no longer has the branch: doubted
        git(self.origin, "update-ref", "-d", "refs/heads/main")       # cached refs/remotes/origin/main still has HEAD
        self.assertEqual(self.check(), "HEAD not on origin")

    def test_not_in_store_keeps(self):
        self.write_store({})
        self.assertEqual(self.check(), "not in signed store")

    def test_no_store_index_keeps(self):
        os.remove(self.store)
        self.assertEqual(self.check(), "no signed-store index")

    def test_no_archive_keeps(self):
        self.write_store({self.sha: {"archive": "", "locs": []}})
        self.assertEqual(self.check(), "store entry has no AGIdock archive")

    def test_store_location_inside_tree_keeps(self):
        self.write_store({self.sha: {"archive": "/archive/x", "locs": ["localhost:" + self.rec]}})
        self.assertEqual(self.check(), "store location inside this checkout")

    def test_named_untracked_path_inside_keeps(self):
        os.makedirs(os.path.join(self.wt, "run"))
        odb = os.path.join(self.wt, "run/6_final.odb")
        open(odb, "w").write("x")
        t = json.dumps(dict(SIGNED, odb=odb))
        self.assertIsNotNone(self.check(t))

    def test_not_signoff_keeps(self):
        p = os.path.join(self.recdir, "PROVENANCE.json")
        self.assertEqual(oa.SourceCopy(self.store, "localhost").check(p, self.text), "not signoff.json")

    def test_not_git_keeps(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "signoff.json")
        open(p, "w").write(self.text)
        self.assertEqual(oa.SourceCopy(self.store, "localhost").check(p, self.text), "not in a git checkout")


class TestLoadCounted(Base):
    def job(self, srccopy):
        j = object.__new__(oa.Job)
        snap = os.path.join(self.d, "snap"); os.makedirs(snap, exist_ok=True)
        shutil.copy(self.store, os.path.join(snap, oa.STORE_INDEX))
        j.a = types.SimpleNamespace(snapshot=snap, state=self.d, srccopy=srccopy)
        j.host = "localhost"
        j.found = {"record": [self.rec]}
        j.paths = oa.Paths({})
        j.roots = [self.d]
        return j

    def test_off_keeps_counted(self):
        j = self.job(False); j.load_counted()
        self.assertTrue(j.counted.hit(self.recdir + "/blk.lef"))

    def test_on_drops_record_dir_keeps_outside_named(self):
        j = self.job(True); j.load_counted()
        self.assertFalse(j.counted.hit(self.recdir + "/blk.lef"))
        self.assertTrue(j.counted.hit("/srv/opentallas-scratch2/claude/elsewhere/blk/6_final.odb"))
        self.assertEqual(open(os.path.join(self.d, "srccopy.tsv")).read().split(), [self.rec])


class TestStoreIndex(unittest.TestCase):
    def test_index_from_store(self):
        c = tempfile.mkdtemp()
        rd = os.path.join(c, "signed-store/records/ab"); os.makedirs(rd)
        for eid, v in (("ab" + "1" * 62, "SIGNED"), ("ab" + "2" * 62, "FAIL")):
            with gzip.open(os.path.join(rd, eid + ".json.gz"), "wt") as fh:
                json.dump({"id": eid, "verdict": v, "archive": "/archive/a", "origin": "intel1:/srv/x/signoff.json",
                           "aliases": ["epyc2:/srv/y/signoff.json"]}, fh)
        out = os.path.join(c, "store.json")
        self.assertEqual(oa.write_store_index(c, out), 1)
        idx = json.load(open(out))
        self.assertEqual(idx["ab" + "1" * 62]["locs"], ["intel1:/srv/x/signoff.json", "epyc2:/srv/y/signoff.json"])

    def test_no_store_no_file(self):
        c = tempfile.mkdtemp()
        self.assertEqual(oa.write_store_index(c, os.path.join(c, "store.json")), 0)
        self.assertFalse(os.path.exists(os.path.join(c, "store.json")))


if __name__ == "__main__":
    unittest.main()
