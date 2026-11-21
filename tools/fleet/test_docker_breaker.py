"""DOCKERBREAKER-1630: after one docker call times out, later calls in any process answer at once (no wait under the admission lock) until the breaker expires."""
import importlib.machinery
import importlib.util
import os
import pathlib
import stat
import tempfile
import time
import unittest
from unittest import mock

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("recon_breaker", P)
spec = importlib.util.spec_from_loader(loader.name, loader)
R = importlib.util.module_from_spec(spec)
loader.exec_module(R)


class Breaker(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.d = pathlib.Path(t.name)
        for k, v in (("BREAKER", str(self.d / "docker.broken")), ("DOCKER_TIMEOUT_S", 1)):
            p = mock.patch.object(R, k, v)
            p.start()
            self.addCleanup(p.stop)
        self.bin = self.d / "bin"
        self.bin.mkdir()
        p = mock.patch.dict(os.environ, {"PATH": f"{self.bin}:{os.environ['PATH']}"})
        p.start()
        self.addCleanup(p.stop)

    def fake(self, body):
        f = self.bin / "docker"
        f.write_text("#!/bin/bash\n" + body)
        f.chmod(f.stat().st_mode | stat.S_IXUSR)

    def test_hang_opens_breaker_then_calls_return_at_once_then_success_closes_it(self):
        self.fake("sleep 30\n")
        t0 = time.time()
        self.assertEqual(R.docker_cmd("ps")[0], 124)
        self.assertTrue(os.path.exists(R.BREAKER))
        t1 = time.time()
        self.assertEqual(R.docker_cmd("inspect", "x")[0], R.BREAKER_RC)
        self.assertLess(time.time() - t1, 0.5)                    # no wait: the breaker answered
        self.assertTrue(R.breaker_open())
        self.assertFalse(R.breaker_open(now=time.time() + 120))     # expired: the next call probes
        self.fake("echo ok\n")
        os.utime(R.BREAKER, (time.time() - 120, time.time() - 120))
        self.assertEqual(R.docker_cmd("ps"), (0, "ok\n"))
        self.assertFalse(os.path.exists(R.BREAKER))

    def test_open_breaker_inspect_all_returns_nothing_without_a_retry_burst(self):
        open(R.BREAKER, "a").close()
        with mock.patch.object(R.subprocess, "run", side_effect=AssertionError("docker must not run")):
            self.assertEqual(R.docker_inspect_all(["a", "b"]), [])

    def test_no_docker_binary_is_127_and_never_opens_the_breaker(self):
        with mock.patch.object(R.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(R.docker_cmd("ps")[0], 127)
        self.assertFalse(os.path.exists(R.BREAKER))


if __name__ == "__main__":
    unittest.main()
