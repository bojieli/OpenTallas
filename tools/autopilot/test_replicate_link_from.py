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
        for d_, dn_, fn_ in os.walk(src):                                # rsync's quick check is size + mtime: the changed files must not look unchanged
            for f_ in fn_:
                if f_ != "a.py": os.utime(os.path.join(d_, f_), (1_000_000, 1_000_000))
        os.utime(src + "/tools/a.py", (os.stat(prev + "/tools/a.py").st_atime, os.stat(prev + "/tools/a.py").st_mtime))   # a.py really is unchanged
        os.makedirs(new + ".part")
        subprocess.run(["rsync", "-a", f"--link-dest={prev}/", src + "/", new + ".part/"], check=True)
        # mtimes differ in this fixture, so only content-equal + attribute-equal files link; make the fixture honest: align a.py's mtime
        self.assertEqual(os.stat(new + ".part/tools/b.py").st_ino == os.stat(prev + "/tools/b.py").st_ino, False)
        os.chmod(new + ".part", 0o755)                                  # replicate does `chmod u+w .` before writing the sidecar
        open(new + ".part/" + SM.LINKBASE, "w").write(os.path.realpath(prev) + "\n")
        self.assertEqual(os.stat(new + ".part/tools/a.py").st_ino, os.stat(prev + "/tools/a.py").st_ino)   # unchanged file is a link
        self.assertEqual(SM.link_base(new + ".part"), os.path.realpath(prev))
        errs, _ = SM.verify(new + ".part", expect=m2["manifest_hash"], full=True)
        self.assertEqual(errs, [])
        os.chmod(new + ".part", 0o755); [os.chmod(os.path.join(d, "tools"), 0o755) for d in (new + ".part", prev, src)]

    def test_a_linked_copy_is_budgeted_small(self):
        self.assertFalse(SM.room_after_copy(60, 49)[0]); self.assertTrue(SM.room_after_copy(90, 8)[0])


def test_remote_free_gb_uses_the_nearest_existing_ancestor_for_a_missing_target_dir():
    import types
    seen = []
    def fake_run(cmd, **k):
        seen.append(cmd[-1])
        return types.SimpleNamespace(stdout="2048\n123\n", stderr="", returncode=0)
    orig = SM.subprocess.run
    SM.subprocess.run = fake_run
    try:
        free, have = SM.remote_free_gb("h", "/srv/x/claude/kw45/snap_new", "/srv/x/claude/kw45/snap_new/t.part")
    finally:
        SM.subprocess.run = orig
    assert free == 2.0 and "dirname" in seen[0] and "while [ ! -d" in seen[0]
