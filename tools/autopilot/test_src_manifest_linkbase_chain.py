"""Chained link trees (D4 -> M5 -> M5T) and a read-only .link-base (QC 11-17: replicate --link-from of a tree that was itself a link
replica copied the source's read-only .link-base, the target write failed and verify refused ~323k shared inodes)."""
import json, os, shutil, stat, subprocess, sys, tempfile, unittest
import src_manifest as SM
from test_src_manifest_link import mk_base, mk_pack

FAKE_SSH = r'''#!/usr/bin/env python3
# stand-in for ssh: drop the host, map the "source host" path prefix to the "target host" one, run the joined words in bash (as ssh does)
import os, subprocess, sys
args = sys.argv[1:]
while args and args[0].startswith("-"):
    args = args[2:] if args[0] in ("-o", "-p", "-l", "-i") else args[1:]
args = args[1:]
src, dst = os.environ["FAKE_FROM"], os.environ["FAKE_TO"]
cmd = " ".join(a.replace(src, dst) for a in args)
env = dict(os.environ, HOME=os.environ["FAKE_HOME"])
sys.exit(subprocess.run(["bash", "-c", cmd], env=env).returncode)
'''


def unwritable_cleanup(t):
    subprocess.run(["find", t, "-type", "d", "-exec", "chmod", "u+w", "{}", "+"])
    shutil.rmtree(t, ignore_errors=True)


class Chain(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(); self.addCleanup(unwritable_cleanup, self.t)
        self.old_cache = SM.CACHE_DIR; SM.CACHE_DIR = os.path.join(self.t, "cache")
        self.addCleanup(setattr, SM, "CACHE_DIR", self.old_cache)
        self.k = os.path.join(self.t, "src", "kw45"); os.makedirs(self.k)
        self.d4 = os.path.join(self.k, "D4")
        self.d4m = mk_base(self.d4, {"tools/a.py": "A=1\n", "tools/b.py": "B=1\n", "rtl/x.sv": "module x; endmodule\n"})

    def step(self, base, name, add):
        bm = SM.load_manifest(base)
        pack = os.path.join(self.t, "pack_" + name)
        mk_pack(pack, bm["manifest_hash"], add)
        out = os.path.join(self.k, name)
        nm = SM.delta_apply(pack, base, out, link=True)
        SM.publish(out)
        return out, nm

    def chain(self):
        # changed files differ in SIZE: rsync --link-dest quick-checks size+mtime and these are written within one second
        m5, m5m = self.step(self.d4, "M5", {"tools/b.py": "B=22\n"})
        # verified before M5T exists: once a child links a file the base owns (tools/b.py), the base sees nlink 2 (known limit, not this fix)
        self.assertEqual(SM.verify(m5, expect=m5m["manifest_hash"], ro=True, full=True)[0], [])
        m5t, m5tm = self.step(m5, "M5T", {"tools/a.py": "A=333\n", "tools/new.py": "N=1\n"})
        return m5, m5m, m5t, m5tm

    def test_chained_delta_apply_link_replaces_the_inherited_read_only_link_base(self):
        m5, m5m, m5t, m5tm = self.chain()
        lb = lambda r: open(os.path.join(r, SM.LINKBASE)).read().strip()
        self.assertEqual(lb(m5), os.path.realpath(self.d4))       # never written through by the next link step
        self.assertEqual(lb(m5t), os.path.realpath(m5))
        self.assertNotEqual(os.lstat(os.path.join(m5, SM.LINKBASE)).st_ino, os.lstat(os.path.join(m5t, SM.LINKBASE)).st_ino)
        self.assertEqual(stat.S_IMODE(os.lstat(os.path.join(m5t, SM.LINKBASE)).st_mode), 0o444)
        ino = {os.lstat(os.path.join(r, "rtl/x.sv")).st_ino for r in (self.d4, m5, m5t)}
        self.assertEqual(len(ino), 1)                              # the unchanged file is one inode through the whole chain
        self.assertEqual(SM.verify(m5t, expect=m5tm["manifest_hash"], ro=True, full=True)[0], [])

    def test_cached_receipt_accepts_inodes_shared_with_the_declared_base_only(self):
        m5, m5m, m5t, m5tm = self.chain()
        self.assertEqual(SM.verify(m5t, expect=m5tm["manifest_hash"], ro=True, full=True)[0], [])   # writes the completed-verify cache
        errs, info = SM.cached_receipt(m5t, expect=m5tm["manifest_hash"])
        self.assertEqual(errs, []); self.assertEqual(info["verdict"], "PASS")
        os.link(os.path.join(m5t, "tools/new.py"), os.path.join(self.t, "stray.py"))   # a file this tree owns, linked elsewhere: still a miss
        errs, _ = SM.cached_receipt(m5t, expect=m5tm["manifest_hash"])
        self.assertTrue(any("shared inode tools/new.py" in e for e in errs), errs)

    def test_replicate_link_from_a_chained_tree_writes_a_fresh_link_base_on_the_target(self):
        m5, m5m, m5t, m5tm = self.chain()
        self.assertEqual(stat.S_IMODE(os.lstat(os.path.join(m5t, SM.LINKBASE)).st_mode), 0o444)    # the read-only file the copy used to carry
        fake = os.path.join(self.t, "fake_ssh"); open(fake, "w").write(FAKE_SSH); os.chmod(fake, 0o755)
        src_root, dst_root = os.path.join(self.t, "src"), os.path.join(self.t, "dst")
        os.makedirs(os.path.join(dst_root, "kw45")); os.makedirs(os.path.join(self.t, "home"))
        env = dict(FAKE_FROM=src_root + "/", FAKE_TO=dst_root + "/", FAKE_HOME=os.path.join(self.t, "home"))
        saved = (SM.SSH, SM.RSYNC_SSH, SM.REPL_FLOOR_GB, dict(os.environ))
        def restore():
            SM.SSH, SM.RSYNC_SSH, SM.REPL_FLOOR_GB = saved[:3]; os.environ.clear(); os.environ.update(saved[3])
        self.addCleanup(restore)
        SM.SSH, SM.RSYNC_SSH, SM.REPL_FLOOR_GB = [fake], fake, 0
        os.environ.update(env)
        self.assertEqual(SM.main(["replicate", self.d4, "--hosts", "h"]), 0)
        self.assertEqual(SM.main(["replicate", m5, "--hosts", "h", "--link-from", "D4"]), 0)
        self.assertEqual(SM.main(["replicate", m5t, "--hosts", "h", "--link-from", "M5"]), 0)
        dk = os.path.join(dst_root, "kw45")
        lb = lambda r: open(os.path.join(dk, r, SM.LINKBASE)).read().strip()
        self.assertEqual(lb("M5"), os.path.realpath(os.path.join(dk, "D4")))
        self.assertEqual(lb("M5T"), os.path.realpath(os.path.join(dk, "M5")))
        self.assertFalse(os.path.exists(os.path.join(dk, "D4", SM.LINKBASE)))
        self.assertEqual(os.lstat(os.path.join(dk, "M5T", "rtl/x.sv")).st_ino, os.lstat(os.path.join(dk, "M5", "rtl/x.sv")).st_ino)
        self.assertEqual(SM.verify(os.path.join(dk, "M5T"), expect=m5tm["manifest_hash"], ro=True, full=True)[0], [])


if __name__ == "__main__":
    unittest.main()
