"""ot-tools-sync (MERGE-QUEUE-1): main@sha becomes a read-only versioned tree, rt/current flips by one rename only after the
smoke test passes, an older version is never touched, and a live edit of the current tree is reported as drift."""
import importlib.machinery, importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest

P = str(pathlib.Path(__file__).with_name("ot-tools-sync"))


def sh(*a, cwd=None):
    return subprocess.run(list(a), cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Sync(unittest.TestCase):
    def setUp(self):
        d = self.d = pathlib.Path(tempfile.mkdtemp())
        g = self.g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
        sh(*g, "init", "-q", "--bare", str(d / "origin.git"))
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "dev"))
        dev = self.dev = d / "dev"
        for sub in ("tools/autopilot", "tools/fleet", "tools/die_plan", "physical/common_flow", "rtl"):
            (dev / sub).mkdir(parents=True)
        (dev / "tools/autopilot/kit_wave.py").write_text("print('wave')\n")
        (dev / "tools/fleet/ot-run").write_text("#!/usr/bin/env python3\nprint('ot-run')\n")
        (dev / "tools/die_plan/gen_phys.py").write_text("X = 1\n")
        (dev / "physical/common_flow/grt183_make.sh").write_text("#!/bin/bash\necho grt\n")
        (dev / "rtl/big.sv").write_text("module m; endmodule\n")
        sh(*g, "add", "-A", cwd=dev); sh(*g, "commit", "-qm", "v1", cwd=dev); sh(*g, "push", "-q", "origin", "main", cwd=dev)
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "repo"))
        sh("git", "config", "extensions.worktreeConfig", "true", cwd=d / "repo")
        self.env = dict(os.environ, OT_RT_ROOT=str(d / "rt"), MQ_REPO=str(d / "repo"), MQ_HOME=str(d / "mq"), OT_RT_HOSTS="",
                        OT_RT_SMOKE_TESTS="", OT_RT_LEGACY="", OT_RT_BACKEND_ROOTS="", MQ_COORD=str(d / "coord"), MQ_PYTHON=sys.executable)

    def run_(self, *a):
        return subprocess.run([sys.executable, "-I", P, *a], env=self.env, capture_output=True, text=True, timeout=300)

    def commit(self, rel, text):
        (self.dev / rel).write_text(text)
        sh(*self.g, "commit", "-qam", rel, cwd=self.dev); sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        return sh("git", "rev-parse", "HEAD", cwd=self.dev)

    def test_sync_flip_readonly_and_old_version_untouched(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        r = self.run_("sync", "--no-hosts")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rt = self.d / "rt"
        self.assertEqual(os.readlink(rt / "current"), v1[:12])
        self.assertTrue((rt / "current/tools/autopilot/kit_wave.py").is_file())
        self.assertFalse((rt / "current/rtl").exists())                 # sparse: tools + physical/common_flow only
        self.assertFalse(os.access(rt / "current/tools/autopilot/kit_wave.py", os.W_OK) and os.geteuid() != 0)
        man = json.loads((rt / f"{v1[:12]}.manifest.json").read_text())
        self.assertEqual(man["sha"], v1)
        old_bytes = (rt / v1[:12] / "tools/die_plan/gen_phys.py").read_bytes()
        v2 = self.commit("tools/die_plan/gen_phys.py", "X = 2\n")
        r = self.run_("sync", "--no-hosts")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(os.readlink(rt / "current"), v2[:12])
        self.assertEqual((rt / v1[:12] / "tools/die_plan/gen_phys.py").read_bytes(), old_bytes)
        self.assertIn(f"-> {v2[:12]}", (rt / "history.log").read_text())

    def test_smoke_failure_keeps_current(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        self.assertEqual(self.run_("sync", "--no-hosts").returncode, 0)
        v2 = self.commit("tools/autopilot/kit_wave.py", "def broken(:\n")
        r = self.run_("sync", "--no-hosts")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual(os.readlink(self.d / "rt/current"), v1[:12])
        self.assertTrue((self.d / f"rt/{v2[:12]}.smoke-failed").is_file())

    def test_live_edit_is_drift(self):
        v1 = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        self.assertEqual(self.run_("sync", "--no-hosts").returncode, 0)
        self.assertEqual([l for l in self.run_("drift").stdout.splitlines() if l.startswith("DRIFT")], [])
        f = self.d / "rt" / v1[:12] / "tools/die_plan/gen_phys.py"
        os.chmod(f, 0o644); f.write_text("X = 99  # live-only\n")
        out = self.run_("drift").stdout
        self.assertIn(f"hub rt/{v1[:12]} changed: tools/die_plan/gen_phys.py", out)


if __name__ == "__main__":
    unittest.main()
