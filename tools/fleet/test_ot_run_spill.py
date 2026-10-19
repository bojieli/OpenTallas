"""ot-run SPILL copy paths (OTRUN-SPILL 2026-10-19).

Bug (MU-SLICE-GATE 10-19 ~04:05): two jobs of one lane spilled ot-epyc5 -> ot-epyc6 at the same moment; the two concurrent
`tar --keep-newer-files -x` into the same tree failed ('Unexpected inconsistency when making directory'), ot-run said
"SPILL copy FAILED; NOT RUN there", but v8 wrote the spill marker only AFTER a successful copy, so the copy on ot-epyc6 was
UNMARKED: the next 120 s re-place ran the job there as a normal job and nothing copied its outputs back.

The tests run the real copy commands with a fake `ssh` that maps each host to its own directory tree."""
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = pathlib.Path(__file__).resolve().parent

FAKE_SSH = r'''#!/usr/bin/env python3
import os, subprocess, sys
a = sys.argv[1:]
while a and a[0] == "-o":
    a = a[2:]
host, cmd = a[0], " ".join(a[1:])
if host == "ot-garbage":                 # a source whose stream breaks mid-copy
    sys.stdout.buffer.write(b"\x28\xb5\x2f\xfd garbage" * 1000)
    sys.exit(0)
hr = os.environ["OTST_BASE"] + "/h-" + host            # this host's "/"
tok = os.environ["OTST_TOKEN"]
cmd = cmd.replace(" -C / ", " -C %s " % hr).replace("cd / ", "cd %s " % hr).replace(tok, hr + tok)
sys.exit(subprocess.run(["bash", "-c", cmd]).returncode)
'''


FAKE_TAR = r'''#!/bin/bash
# GNU tar 1.35 with --keep-newer-files: every pre-existing directory member is an error (exit 2) though files extract fine
real=$(PATH=${PATH#*:} command -v tar)
"$real" "$@"; rc=$?
if [ -n "$OTST_TAR135" ] && [[ " $* " == *" -xf "* ]]; then
  for p in $OTST_TAR135; do echo "tar: $p: Unexpected inconsistency when making directory" >&2; done
  echo "tar: Exiting with failure status due to previous errors" >&2; exit 2
fi
exit $rc
'''


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_mod", str(HERE / "ot-run"))
    spec = importlib.util.spec_from_loader("ot_run_mod", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


class Spill(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="otst-")
        b = os.path.join(self.base, "bin")
        os.makedirs(b)
        open(os.path.join(b, "ssh"), "w").write(FAKE_SSH)
        os.chmod(os.path.join(b, "ssh"), 0o755)
        open(os.path.join(b, "tar"), "w").write(FAKE_TAR)
        os.chmod(os.path.join(b, "tar"), 0o755)
        self.env = dict(os.environ)
        os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]
        self.tok = "/OTSTROOT-%s/" % os.path.basename(self.base)
        os.environ["OTST_TOKEN"] = self.tok
        os.environ["OTST_BASE"] = self.base
        self.m = load()
        st = os.path.join(self.base, "state")
        self.m.SPILL_PENDING = os.path.join(st, "pending")
        self.m.SPILL_STUCK_LOG = os.path.join(st, "stuck.log")
        self.m.SIGNAL_LOG = os.path.join(st, "signals.log")
        self.root = self.tok + "lane"           # the lane root as every host names it
        self.stamps = []
        src = self.host("src")
        for i in range(200):
            os.makedirs(f"{src}/d{i}/b/c")
            open(f"{src}/d{i}/b/c/f", "w").write("x")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        for s in self.stamps:
            for p in (s, s + ".done"):
                if os.path.exists(p):
                    os.unlink(p)
        shutil.rmtree(self.base, ignore_errors=True)

    def host(self, h):
        return f"{self.base}/h-{h}{self.tok}lane"

    def stamp(self):
        s = f"/tmp/ot-run-spill.otst-{os.getpid()}-{len(self.stamps)}-{os.path.basename(self.base)}"
        self.stamps.append(s)
        return s

    def fwd(self, src, dst, stamp):
        return subprocess.run(["bash", "-o", "pipefail", "-c", self.m.spill_fwd_cmd(src, dst, [self.root], stamp)],
                              capture_output=True, text=True)

    def test_concurrent_spills_of_one_lane_both_copy(self):
        """the MU-SLICE-GATE race: two spills of the same lane to the same host at once"""
        out = {}
        ts = [threading.Thread(target=lambda k: out.__setitem__(k, self.fwd("src", "dst", self.stamp())), args=(k,)) for k in (0, 1)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual([out[0].returncode, out[1].returncode], [0, 0], [out[0].stderr[-300:], out[1].stderr[-300:]])
        self.assertTrue(os.path.exists(self.host("dst") + "/d199/b/c/f"))
        self.assertTrue(os.path.exists(self.host("dst") + "/" + self.m.SPILL_MARK))

    def test_tar135_existing_directory_errors_are_not_a_failure(self):
        """tar 1.35 + --keep-newer-files fails on every existing directory (the real MU-SLICE-GATE trigger: a second
        spill of the lane to a host holding a copy); only that error, for a path that IS a directory, is forgiven"""
        os.environ["OTST_TAR135"] = "tmp usr/bin"            # directories ("/tmp", "/usr/bin" exist)
        r = self.fwd("src", "dst", self.stamp())
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertTrue(os.path.exists(self.stamps[-1]))
        os.environ["OTST_TAR135"] = "tmp tmp/ot-run-no-such-dir-otst"   # one is not a directory: a real failure
        r = self.fwd("src", "dst", self.stamp())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ot-run-no-such-dir-otst", r.stderr)
        self.assertFalse(os.path.exists(self.stamps[-1]))

    def test_failed_copy_leaves_a_marked_tree(self):
        """a copy that fails mid-stream must leave the dst tree MARKED, so normal placement never runs a job on it"""
        r = self.fwd("ot-garbage", "dst", self.stamp())
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(os.path.isdir(self.host("dst")))
        self.assertEqual(open(self.host("dst") + "/" + self.m.SPILL_MARK).read().strip(), "ot-garbage")
        self.assertFalse(os.path.exists(self.stamps[-1]))

    def test_real_lane_on_dst_is_refused(self):
        """an unmarked lane root on dst is real data there: never marked, never overwritten"""
        os.makedirs(self.host("dst"))
        open(self.host("dst") + "/mine", "w").write("real")
        r = self.fwd("src", "dst", self.stamp())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("OT_SPILL_REAL", r.stderr)
        self.assertFalse(os.path.exists(self.host("dst") + "/" + self.m.SPILL_MARK))
        self.assertFalse(os.path.exists(self.host("dst") + "/d0"))

    def test_back_copy_keeps_stamp_until_success(self):
        st = self.stamp()
        self.assertEqual(self.fwd("src", "dst", st).returncode, 0)
        os.makedirs(self.host("dst") + "/out")
        open(self.host("dst") + "/out/result.txt", "w").write("PASS")
        os.chmod(self.host("src"), 0o555)             # src cannot take the outputs: the copy fails, the stamp stays
        try:
            self.m.SPILL_BACK_TRIES = 1
            ok, err = self.m.spill_copy_back("src", "dst", [self.root], st)
        finally:
            os.chmod(self.host("src"), 0o755)
        self.assertFalse(ok)
        self.assertTrue(os.path.exists(st), "v8 removed the stamp even when the src side failed")
        ok, err = self.m.spill_copy_back("src", "dst", [self.root], st)
        self.assertTrue(ok, err)
        self.assertEqual(open(self.host("src") + "/out/result.txt").read(), "PASS")
        self.assertFalse(os.path.exists(self.host("src") + "/" + self.m.SPILL_MARK))
        self.assertFalse(os.path.exists(st))

    def test_sweep_copies_back_for_a_dead_client(self):
        """a client killed while its spilled run went on (session limit): the sweep copies the outputs back"""
        st = self.stamp()
        self.assertEqual(self.fwd("src", "dst", st).returncode, 0)
        open(self.host("dst") + "/late.txt", "w").write("late")
        dead = subprocess.Popen(["true"])
        dead.wait()
        self.m.pending_write(dict(tag="t1", pid=dead.pid, src="src", dst="dst", roots=[self.root], stamp=st, unit=None, t=0, cmd="x"))
        self.assertEqual(self.m.spill_sweep(say=lambda m: None), 0)
        self.assertEqual(open(self.host("src") + "/late.txt").read(), "late")
        self.assertTrue(os.path.exists(os.path.join(self.m.SPILL_PENDING, "t1.done")))

    def test_sweep_skips_a_live_client(self):
        self.m.pending_write(dict(tag="t2", pid=os.getpid(), src="src", dst="dst", roots=[self.root], stamp="/nonexistent",
                                  unit=None, t=0, cmd="x"))
        self.m.pid_alive = lambda pid: True
        self.assertEqual(self.m.spill_sweep(say=lambda m: None), 1)
        self.assertTrue(os.path.exists(os.path.join(self.m.SPILL_PENDING, "t2.json")))


if __name__ == "__main__":
    unittest.main()
