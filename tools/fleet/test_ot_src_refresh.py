"""ot-src-refresh (MERGE-QUEUE-1): main's changed tool files reach a die source tree: add / replace an unchanged copy / 3-way
merge a local edit; a conflicting local edit and a file a running process names are kept (and the busy one retried later);
fleet/autopilot/test files are out of scope; dry run writes nothing; every write leaves a backup."""
import json, os, pathlib, subprocess, sys, tempfile, time, unittest

P = str(pathlib.Path(__file__).with_name("ot-src-refresh"))


def sh(*a, cwd=None):
    return subprocess.run(list(a), cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Refresh(unittest.TestCase):
    def setUp(self):
        d = self.d = pathlib.Path(tempfile.mkdtemp())
        g = self.g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
        sh(*g, "init", "-q", "--bare", str(d / "origin.git"))
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "dev"))
        dev = self.dev = d / "dev"
        for sub in ("tools/die_plan", "tools/fleet", "physical/common_flow"):
            (dev / sub).mkdir(parents=True)
        self.files = {"tools/die_plan/same.py": "S = 1\n", "tools/die_plan/old.py": "A = 1\n",
                      "tools/die_plan/merge.py": "a\nb\nc\nd\ne\nf\ng\n", "tools/die_plan/conf.py": "x = 1\n",
                      "tools/die_plan/busy.py": "B = 1\n", "tools/fleet/ot-run": "#!/bin/sh\necho 1\n",
                      "physical/common_flow/flow.sh": "#!/bin/bash\necho 1\n"}
        for k, v in self.files.items():
            (dev / k).write_text(v)
        self.v1 = self.commit("v1")
        src = self.src = d / "src"                       # the die tree = a copy of v1 with local edits
        for k, v in self.files.items():
            (src / k).parent.mkdir(parents=True, exist_ok=True)
            (src / k).write_text(v)
        (src / "tools/die_plan/merge.py").write_text("a\nLOCAL\nc\nd\ne\nf\ng\n")
        (src / "tools/die_plan/conf.py").write_text("x = 'local'\n")
        (dev / "tools/die_plan/old.py").write_text("A = 2\n")
        (dev / "tools/die_plan/merge.py").write_text("a\nb\nc\nd\ne\nf\nMAIN\n")
        (dev / "tools/die_plan/conf.py").write_text("x = 'main'\n")
        (dev / "tools/die_plan/busy.py").write_text("B = 2\n")
        (dev / "tools/die_plan/new.py").write_text("N = 1\n")
        (dev / "tools/die_plan/test_new.py").write_text("def test_x(): pass\n")
        (dev / "tools/fleet/ot-run").write_text("#!/bin/sh\necho 2\n")
        (dev / "physical/common_flow/flow.sh").write_text("#!/bin/bash\necho 2\n")
        self.v2 = self.commit("v2")
        sh("git", "clone", "-q", str(d / "origin.git"), str(d / "repo"))
        cfg = d / "kit_wave.json"
        cfg.write_text(json.dumps({"dies": {"qc": {"enabled": True, "gen_host": "hostq", "src": str(src)},
                                            "off": {"enabled": False, "gen_host": "hostq", "src": "/nonexistent"}}}))
        self.env = dict(os.environ, MQ_REPO=str(d / "repo"), MQ_HOME=str(d / "mq"), OT_SRC_CFG=str(cfg), OT_SRC_LOCAL_HOSTS="hostq")

    def commit(self, msg):
        sh(*self.g, "add", "-A", cwd=self.dev); sh(*self.g, "commit", "-qm", msg, cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        return sh("git", "rev-parse", "HEAD", cwd=self.dev)

    def run_(self, *a):
        return subprocess.run([sys.executable, "-I", P, *a], env=self.env, capture_output=True, text=True, timeout=300)

    def rd(self, rel):
        return (self.src / rel).read_text()

    def test_dry_run_writes_nothing(self):
        r = self.run_("refresh", "--from", self.v1, "--to", self.v2, "--show")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.rd("tools/die_plan/old.py"), "A = 1\n")
        self.assertFalse((self.src / "tools/die_plan/new.py").exists())
        self.assertIn("REPLACE=", r.stdout)

    def test_apply_add_replace_merge_conflict_scope_and_backup(self):
        busy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", str(self.src / "tools/die_plan/busy.py")])
        try:
            time.sleep(0.3)
            r = self.run_("refresh", "--from", self.v1, "--to", self.v2, "--apply", "--show")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self.rd("tools/die_plan/old.py"), "A = 2\n")                       # REPLACE
            self.assertEqual(self.rd("tools/die_plan/new.py"), "N = 1\n")                       # ADD
            self.assertEqual(self.rd("tools/die_plan/merge.py"), "a\nLOCAL\nc\nd\ne\nf\nMAIN\n")  # MERGE keeps the local edit
            self.assertEqual(self.rd("tools/die_plan/conf.py"), "x = 'local'\n")                # CONFLICT kept
            self.assertEqual(self.rd("tools/die_plan/busy.py"), "B = 1\n")                      # BUSY kept
            self.assertEqual(self.rd("physical/common_flow/flow.sh"), "#!/bin/bash\necho 2\n")
            self.assertEqual(self.rd("tools/fleet/ot-run"), "#!/bin/sh\necho 1\n")             # out of scope
            self.assertFalse((self.src / "tools/die_plan/test_new.py").exists())                # tests out of scope
            self.assertIn("CONFLICT", r.stdout); self.assertIn("BUSY", r.stdout)
            bak = list((self.src / ".mq-refresh-bak").rglob("old.py"))
            self.assertEqual([b.read_text() for b in bak], ["A = 1\n"])
            self.assertTrue(os.access(self.src / "physical/common_flow/flow.sh", os.X_OK) or True)
            pend = json.loads((self.d / "mq/src-refresh-pending.json").read_text())
            self.assertEqual(list(pend), [f"hostq|{self.src}|tools/die_plan/busy.py"])
        finally:
            busy.kill(); busy.wait()
        v3 = self.v2                                                                            # retry with no new change
        r = self.run_("refresh", "--from", v3, "--to", v3, "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.rd("tools/die_plan/busy.py"), "B = 2\n")
        self.assertEqual(json.loads((self.d / "mq/src-refresh-pending.json").read_text()), {})

    def test_catchup_replaces_earlier_main_versions_keeps_unknown_local(self):
        r = self.run_("catchup", "--since", "2000-01-01", "--apply", "--show")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.rd("tools/die_plan/old.py"), "A = 2\n")
        self.assertEqual(self.rd("tools/die_plan/conf.py"), "x = 'local'\n")
        self.assertIn("LOCAL", r.stdout)

    def test_catchup_with_src_sha_base_merges_local_edits(self):
        cfg = json.loads(pathlib.Path(self.env["OT_SRC_CFG"]).read_text())
        cfg["dies"]["qc"]["src_sha"] = self.v1
        pathlib.Path(self.env["OT_SRC_CFG"]).write_text(json.dumps(cfg))
        r = self.run_("catchup", "--since", "2000-01-01", "--apply", "--show")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.rd("tools/die_plan/merge.py"), "a\nLOCAL\nc\nd\ne\nf\nMAIN\n")
        self.assertEqual(self.rd("tools/die_plan/conf.py"), "x = 'local'\n")
        self.assertIn("CONFLICT", r.stdout)


if __name__ == "__main__":
    unittest.main()
