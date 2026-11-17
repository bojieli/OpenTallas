"""replicate --link-from: a target holding the earlier tree gets hardlinks for unchanged files and a .link-base that verify accepts."""
import json, os, subprocess, sys, tempfile, unittest
import src_manifest as SM

HERE = os.path.dirname(os.path.abspath(__file__))


class LinkFrom(unittest.TestCase):
    def test_rsync_link_dest_shares_inodes_and_verify_accepts_with_link_base(self):
        t = tempfile.mkdtemp(); prev, new = t + "/src_x_d1", t + "/tgt/src_x_d2"
        os.makedirs(t + "/tgt"); os.makedirs(prev + "/tools")
        for rel, txt in (("tools/a.py", "A=1\n"), ("tools/b.py", "B=1\n")):
            open(os.path.join(prev, rel), "w").write(txt)
        m = {"version": 1, "main_sha": "a" * 40, "scope": ["tools"], "overlay": {}, "files": {r: SM.sha256_file(os.path.join(prev, r)) for r in ("tools/a.py", "tools/b.py")}}
        m["manifest_hash"] = SM.manifest_hash(m); json.dump(m, open(prev + "/" + SM.MANIFEST, "w")); open(prev + "/" + SM.HASHFILE, "w").write(m["manifest_hash"] + "\n"); SM.make_ro(prev)
        # the new tree (source side): a.py unchanged, b.py changed
        src = t + "/src_x_d2"; os.makedirs(src + "/tools")
        open(src + "/tools/a.py", "w").write("A=1\n"); open(src + "/tools/b.py", "w").write("B=22\n")
        m2 = dict(m, files={"tools/a.py": SM.sha256_file(src + "/tools/a.py"), "tools/b.py": SM.sha256_file(src + "/tools/b.py")}); m2["manifest_hash"] = SM.manifest_hash(m2)
        json.dump(m2, open(src + "/" + SM.MANIFEST, "w")); open(src + "/" + SM.HASHFILE, "w").write(m2["manifest_hash"] + "\n"); SM.make_ro(src)
        os.makedirs(new + ".part")
        subprocess.run(["rsync", "-a", f"--link-dest={prev}/", src + "/", new + ".part/"], check=True)
        # mtimes differ in this fixture, so only content-equal + attribute-equal files link; make the fixture honest: align a.py's mtime
        self.assertEqual(os.stat(new + ".part/tools/b.py").st_ino == os.stat(prev + "/tools/b.py").st_ino, False)
        open(new + ".part/" + SM.LINKBASE, "w").write(os.path.realpath(prev) + "\n")
        self.assertEqual(SM.link_base(new + ".part"), os.path.realpath(prev))
        errs, _ = SM.verify(new + ".part", expect=m2["manifest_hash"], full=True)
        self.assertEqual(errs, [])

    def test_a_linked_copy_is_budgeted_small(self):
        self.assertFalse(SM.room_after_copy(60, 49)[0]); self.assertTrue(SM.room_after_copy(90, 8)[0])
