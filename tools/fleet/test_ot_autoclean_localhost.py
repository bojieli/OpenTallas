"""LOCALHOST_1111 (KW-FIX-44, COORD 11-11): localhost is an autoclean host; never-touch trees are refused everywhere."""
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("oa_lh", os.path.join(HERE, "ot-autoclean.py"))
oa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oa)


class TestLocalhost(unittest.TestCase):
    def test_localhost_in_hosts_and_alias(self):
        self.assertIn("localhost", oa.HOSTS)
        self.assertEqual(oa.HOSTNAME_ALIAS.get("ubuntu"), "localhost")

    def test_remote_localhost_runs_locally(self):
        r = oa.Remote("ssh -o BatchMode=yes", "ssh agidock", 30)
        self.assertEqual(r.argv("localhost"), ["bash", "-c"])
        self.assertEqual(r.argv("epyc4")[-1], "epyc4")
        p = r.host("localhost", "echo ok-$((1+1))")
        self.assertEqual(p.stdout.strip(), "ok-2")

    def test_never_touch(self):
        h = oa.HOME
        for p in (h + "/.codex/x", h + "/OpenTallas", h + "/OpenTallas/tools", "/srv/opentallas-scratch/claude/coro-train/a",
                  h + "/OpenRealtime/b", "/opt/Xilinx/c", h + "/closed_archive/d", h + "/coord/lanes"):
            self.assertTrue(oa.never_touch(p), p)
        for p in (h + "/wt/ds85-a", "/srv/opentallas-scratch/claude/wt/x", h + "/codex-hbm-1113/run",
                  h + "/OpenTallas-other"):
            self.assertIsNone(oa.never_touch(p), p)

    def test_never_touch_by_realpath(self):
        d = tempfile.mkdtemp()
        tgt = os.path.join(d, "coro-train")
        os.makedirs(tgt)
        ln = os.path.join(d, "innocent")
        os.symlink(tgt, ln)
        self.assertTrue(oa.never_touch(ln))

    def test_local_extra_roots(self):
        d = tempfile.mkdtemp()
        for n in ("wt", "codex-a", "wt-codex-b", "scratch-codex-c", "other", "codex-coro-train"):
            os.makedirs(os.path.join(d, n))
        os.symlink(os.path.join(d, "other"), os.path.join(d, "codex-link"))
        old = oa.LOCAL_EXTRA_GLOBS
        try:
            oa.LOCAL_EXTRA_GLOBS = [os.path.join(d, g) for g in ("wt", "codex-*", "wt-codex-*", "scratch-codex-*")]
            got = sorted(os.path.basename(r) for r in oa.local_extra_roots())
        finally:
            oa.LOCAL_EXTRA_GLOBS = old
        self.assertEqual(got, ["codex-a", "scratch-codex-c", "wt", "wt-codex-b"])   # no symlink, no never-touch, no other


if __name__ == "__main__":
    unittest.main()
