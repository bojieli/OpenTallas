"""FABLE-FLOW-0600 class D: rt/current flips only after the copy on one gen host composes a kit launch tree; red keeps current on hub and hosts."""
import importlib.machinery, importlib.util, os, pathlib, shutil, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
P = str(HERE / "ot-tools-sync")


def load(rt=None):
    old = os.environ.get("OT_RT_ROOT")
    if rt:
        os.environ["OT_RT_ROOT"] = str(rt)              # RT is a default argument of current(): bind it at import
    try:
        return _load()
    finally:
        if rt:
            if old is None:
                os.environ.pop("OT_RT_ROOT", None)
            else:
                os.environ["OT_RT_ROOT"] = old


def _load():
    ld = importlib.machinery.SourceFileLoader("ot_tools_sync_gs", P)
    spec = importlib.util.spec_from_loader("ot_tools_sync_gs", ld)
    m = importlib.util.module_from_spec(spec)
    ld.exec_module(m)
    return m


class GenSmokeScript(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        r = self.r = self.d / "rt"
        for sub in ("tools/autopilot", "tools/die_plan", "tools/fleet", "physical/common_flow"):
            (r / sub).mkdir(parents=True)
        for f in ("rt_launch_tree.sh", "src_manifest.py", "live_tree.py", "kit_wave.py"):
            shutil.copy(HERE.parent / "autopilot" / f, r / "tools/autopilot" / f)
        (r / "physical/common_flow/a.sh").write_text("echo a\n")
        self.M = load()

    def tearDown(self):
        subprocess.run(["chmod", "-R", "u+w", str(self.d)])
        shutil.rmtree(self.d, ignore_errors=True)

    def smoke(self):
        p = subprocess.run(["bash", "-s", "--", str(self.r)], input=self.M.GEN_SMOKE_SH, capture_output=True, text=True, timeout=300)
        return p.stdout + p.stderr

    def test_complete_copy_is_ok(self):
        self.assertIn("GEN-SMOKE-OK", self.smoke())

    def test_incomplete_copy_is_red(self):
        shutil.rmtree(self.r / "physical/common_flow")
        out = self.smoke()
        self.assertNotIn("GEN-SMOKE-OK", out)
        self.assertIn("RED ", out)

    def test_bad_shell_is_red(self):
        (self.r / "physical/common_flow/b.sh").write_text("if then fi (\n")
        self.assertIn("RED bash -n physical/common_flow/b.sh", self.smoke())


class SyncGate(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.M = load(self.d / "rt")
        self.M.RT.mkdir()
        (self.M.RT / "aaaaaaaaaaaa").mkdir()
        self.M.flip(self.M.RT, "aaaaaaaaaaaa")
        self.M.MQ = self.d / "mq"
        self.M.MQ.mkdir()
        self.M.HOSTS = ["h1", "h2"]
        self.M.GEN_SMOKE_HOSTS = ["g1", "g2"]
        self.M.git = lambda *a, **k: "b" * 40
        self.M.materialize = lambda full: self.M.RT / "bbbbbbbbbbbb"
        self.M.smoke = lambda d, tests=True: []
        self.calls = []

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def fake(self, verdicts):
        def hs(host, name, prev, do_flip=True, smoke_here=False):
            self.calls.append((host, do_flip, smoke_here))
            return verdicts.get(host, (True, "ok"))
        self.M.host_sync = hs

    def test_red_keeps_current_everywhere(self):
        self.fake({"g1": (False, "RED gen smoke: RED launch tree lacks physical/common_flow")})
        self.assertEqual(self.M.sync("x"), 3)
        self.assertEqual(self.M.current(), "aaaaaaaaaaaa")
        self.assertEqual(self.calls, [("g1", False, True)])                     # no host flipped
        self.assertTrue((self.M.RT / "bbbbbbbbbbbb.smoke-failed").is_file())

    def test_unreachable_tries_next_then_flips(self):
        self.fake({"g1": (False, "ssh: refused")})
        self.M.installed_diffs = lambda *a, **k: []
        self.M.names_in_use_text = lambda: ""
        self.M.KEEP = 0
        (self.M.RT / "bbbbbbbbbbbb.manifest.json").write_text('{"files": {}}')
        self.assertEqual(self.M.sync("x"), 0)
        self.assertEqual(self.M.current(), "bbbbbbbbbbbb")
        self.assertEqual(self.calls[:2], [("g1", False, True), ("g2", False, True)])
        self.assertEqual([c[0] for c in self.calls[2:]], ["h1", "h2"])

    def test_all_unreachable_does_not_flip(self):
        self.fake({"g1": (False, "ssh: x"), "g2": (False, "rsync rc=12")})
        self.assertEqual(self.M.sync("x"), 5)
        self.assertEqual(self.M.current(), "aaaaaaaaaaaa")


if __name__ == "__main__":
    unittest.main()
