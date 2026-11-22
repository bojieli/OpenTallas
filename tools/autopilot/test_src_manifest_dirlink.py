"""DIRLINK-1121: a tracked symlink that points at a directory is one manifest entry (build, verify, link_tree); a tree whose
older manifest does not list its directory symlinks still verifies."""
import json, os, shutil, subprocess, tempfile, unittest
import src_manifest as SM


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True,
                          capture_output=True, text=True).stdout.strip()


class DirLink(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.addCleanup(self._rm)
        self.repo = self.t + "/repo"
        os.makedirs(self.repo + "/tools/real")
        open(self.repo + "/tools/real/a.py", "w").write("A=1\n")
        os.symlink("real", self.repo + "/tools/dlink")              # -> directory
        os.symlink("real/a.py", self.repo + "/tools/flink")         # -> file
        os.symlink("nowhere", self.repo + "/tools/dangling")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "tools")
        git(self.repo, "commit", "-qm", "m")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        SM.CACHE_DIR = self.t + "/cache"
        self.out = self.t + "/tree1"

    def _rm(self):
        for dp, dn, fn in os.walk(self.t):
            os.chmod(dp, 0o755)
        shutil.rmtree(self.t, ignore_errors=True)

    def build(self):
        return SM.build(self.repo, self.sha, "", ["tools"], self.out, main_ref="")

    def test_walk_lists_directory_symlink_once_and_does_not_descend(self):
        w = SM.walk_tree(self.repo)
        self.assertEqual(sorted(w), ["tools/dangling", "tools/dlink", "tools/flink", "tools/real/a.py"])

    def test_build_records_directory_symlink(self):
        m = self.build()
        self.assertEqual(sorted(m["files"]), ["tools/dangling", "tools/dlink", "tools/flink", "tools/real/a.py"])
        self.assertTrue(m["files"]["tools/dlink"].startswith("link:"))
        self.assertTrue(os.path.islink(self.out + "/tools/dlink"))
        self.assertEqual(SM.verify(self.out, full=True)[0], [])

    def test_verify_sees_retargeted_missing_and_extra_directory_symlink(self):
        self.build()
        os.unlink(self.out + "/tools/dlink")
        errs = SM.verify(self.out, full=True)[0]
        self.assertTrue(any("tools/dlink (missing)" in e for e in errs), errs)
        os.makedirs(self.out + "/tools/other")
        os.symlink("other", self.out + "/tools/dlink")
        errs = SM.verify(self.out, full=True)[0]
        self.assertTrue(any("tools/dlink (modified" in e for e in errs), errs)

    def test_manifest_written_before_the_fix_still_verifies(self):
        m = self.build()
        del m["files"]["tools/dlink"]                               # as the old walk wrote it: silent about the directory symlink
        m["manifest_hash"] = SM.manifest_hash(m)
        json.dump(m, open(self.out + "/" + SM.MANIFEST, "w"))
        open(self.out + "/" + SM.HASHFILE, "w").write(m["manifest_hash"] + "\n")
        self.assertEqual(SM.verify(self.out, full=True)[0], [])
        os.symlink("real/a.py", self.out + "/tools/extra_flink")    # an unlisted FILE symlink is still an extra
        errs = SM.verify(self.out, full=True)[0]
        self.assertTrue(any("tools/extra_flink (extra" in e for e in errs), errs)

    def test_link_tree_recreates_directory_symlink(self):
        self.build()
        dst = self.t + "/linked"
        SM.link_tree(self.out, dst)
        self.assertTrue(os.path.islink(dst + "/tools/dlink"))
        self.assertEqual(os.readlink(dst + "/tools/dlink"), "real")
        self.assertEqual(sorted(SM.walk_tree(dst)), sorted(SM.walk_tree(self.out)))


if __name__ == "__main__":
    unittest.main()
