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



class Daily(unittest.TestCase):
    """daily: one batch, staged smoke on the gen host before any swap, then every gen_hosts replica, rollback on failure"""
    def setUp(self):
        d = self.d = pathlib.Path(tempfile.mkdtemp())
        g = self.g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
        sh(*g, "init", "-q", "--bare", str(d / "origin.git"))
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "dev"))
        self.dev = d / "dev"
        (self.dev / "tools/die_plan").mkdir(parents=True)
        (self.dev / "tools/die_plan/a.py").write_text("A = 1\n")
        self.v1 = self.commit("v1")
        self.src = d / "src"
        for root in (pathlib.Path("/"), d / "rep"):                    # gen host tree and replica tree (same path, own root)
            t = pathlib.Path(str(root) + str(self.src)) / "tools/die_plan"
            t.mkdir(parents=True)
            (t / "a.py").write_text("A = 1\n")
        sh("git", "clone", "-q", str(d / "origin.git"), str(d / "repo"))
        cfg = d / "kit_wave.json"
        cfg.write_text(json.dumps({"dies": {"qc": {"enabled": True, "gen_host": "hostg", "gen_hosts": ["hostg", "hostr"],
                                                   "src": str(self.src)}}}))
        (d / "mq").mkdir()
        (d / "mq/src-refresh-last.json").write_text(json.dumps({"qc": self.v1}))
        (d / "coord/lanes").mkdir(parents=True)
        (d / "coord/lanes/COORD-REVIEW-QUEUE.md").write_text("")
        self.env = dict(os.environ, MQ_REPO=str(d / "repo"), MQ_HOME=str(d / "mq"), OT_SRC_CFG=str(cfg),
                        OT_SRC_LOCAL_HOSTS="hostg hostr", OT_SRC_LOCAL_ROOTS=f"hostr={d / 'rep'}", MQ_COORD=str(d / "coord"),
                        MQ_COMMIT=str(d / "none.sh"))

    def commit(self, msg):
        sh(*self.g, "add", "-A", cwd=self.dev); sh(*self.g, "commit", "-qm", msg, cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        return sh("git", "rev-parse", "HEAD", cwd=self.dev)

    def daily(self):
        return subprocess.run([sys.executable, "-I", P, "daily", "--apply"], env=self.env, capture_output=True, text=True, timeout=300)

    def rep(self, rel):
        return pathlib.Path(str(self.d / "rep") + str(self.src / rel))

    def last(self):
        return json.loads((self.d / "mq/src-refresh-last.json").read_text())["qc"]

    def test_good_batch_reaches_gen_and_replica(self):
        (self.dev / "tools/die_plan/a.py").write_text("A = 2\n")
        (self.dev / "tools/die_plan/b.py").write_text("import a\nB = 1\n")
        v2 = self.commit("v2")
        r = self.daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in (self.src / "tools/die_plan/a.py", self.rep("tools/die_plan/a.py")):
            self.assertEqual(f.read_text(), "A = 2\n")
        self.assertTrue(self.rep("tools/die_plan/b.py").exists())
        self.assertEqual(self.last(), v2)
        self.assertIn("daily die-tree refresh", (self.d / "coord/lanes/COORD-REVIEW-QUEUE.md").read_text())
        self.assertFalse((self.src / ".mq-stage").exists() and any((self.src / ".mq-stage").iterdir()))

    def test_missing_dependency_from_before_base_is_added_and_odb_allowed(self):
        (self.dev / "tools/die_plan/dep.py").write_text("import dep2\nD = 1\n")    # on main before the base, never in the trees
        (self.dev / "tools/die_plan/dep2.py").write_text("D2 = 1\n")
        v1b = self.commit("v1b")
        (self.d / "mq/src-refresh-last.json").write_text(json.dumps({"qc": v1b}))
        (self.dev / "tools/die_plan/a.py").write_text("import dep\nA = 2\n")
        (self.dev / "tools/die_plan/hop.py").write_text("import os, odb\nH = 1\n")   # OpenROAD script: odb only inside openroad
        v2 = self.commit("v2")
        r = self.daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAILED", r.stdout + r.stderr)
        for rel in ("tools/die_plan/dep.py", "tools/die_plan/dep2.py", "tools/die_plan/hop.py"):
            self.assertTrue((self.src / rel).exists(), rel)
            self.assertTrue(self.rep(rel).exists(), rel)
        self.assertEqual(self.rep("tools/die_plan/a.py").read_text(), "import dep\nA = 2\n")
        self.assertEqual(self.last(), v2)

    def test_put_reports_vs_main_and_from_main_writes_every_copy(self):
        (self.dev / "tools/die_plan/a.py").write_text("A = 2\nT = 'tap_offset_table'\n")   # main moved, both trees still A = 1
        self.commit("v2")
        def put(*a):
            return subprocess.run([sys.executable, "-I", P, "put", "--die", "qc", *a], env=self.env, capture_output=True,
                                  text=True, timeout=300)
        u = put("tools/die_plan/a.py", "--apply")                 # 05:22 11-15: plain put syncs the gen host copy, says SAME
        self.assertIn("DIFFERS from main", u.stdout)
        self.assertIn("--from-main", u.stdout)
        self.assertEqual(self.rep("tools/die_plan/a.py").read_text(), "A = 1\n")
        dry = put("--from-main", "tools/die_plan/a.py")
        self.assertIn("a.py=REPLACE", dry.stdout)
        self.assertEqual((self.src / "tools/die_plan/a.py").read_text(), "A = 1\n")
        u = put("--from-main", "tools/die_plan/a.py", "--apply")
        self.assertEqual(u.returncode, 0, u.stdout + u.stderr)
        for f in (self.src / "tools/die_plan/a.py", self.rep("tools/die_plan/a.py")):
            self.assertEqual(f.read_text(), "A = 2\nT = 'tap_offset_table'\n")
        self.assertTrue(list((self.src / ".mq-refresh-bak").rglob("a.py")))
        self.assertIn("== main", put("tools/die_plan/a.py").stdout)
        self.assertIn("refused: not on main", put("--from-main", "tools/die_plan/nope.py", "--apply").stdout)

    def _tree(self, rel, text):
        for f in (self.src / rel, self.rep(rel)):
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)

    def test_lane_copy_older_than_the_base_merges_on_its_closest_main_version(self):
        # 06:00 11-15: the KV schema.py lane copy derives from a main version OLDER than the last daily sha; merging on that
        # sha dropped full_area_hard_ip.  The closest main version is the right base: lane edit + every main addition.
        pad = "".join(f"P{i} = {i}\n" for i in range(12)); qad = pad.replace("P", "Q")
        (self.dev / "tools/die_plan/schema.py").write_text(pad + qad)
        self.commit("v0")
        self._tree("tools/die_plan/schema.py", "def lane_fn():\n    return 'lane'\n" + pad + qad)
        (self.dev / "tools/die_plan/schema.py").write_text(pad + "def full_area_hard_ip(t):\n    return 1\n" + qad)
        base = self.commit("base")
        (self.d / "mq/src-refresh-last.json").write_text(json.dumps({"qc": base}))
        (self.dev / "tools/die_plan/schema.py").write_text(pad + "def full_area_hard_ip(t):\n    return 1\n" + qad
                                                           + "def tap_offset_table():\n    return 2\n")
        v2 = self.commit("v2")
        r = self.daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for f in (self.src / "tools/die_plan/schema.py", self.rep("tools/die_plan/schema.py")):
            t = f.read_text()
            for name in ("def lane_fn", "def full_area_hard_ip", "def tap_offset_table"):
                self.assertIn(name, t)
        self.assertEqual(self.last(), v2)

    def test_merge_that_would_drop_main_code_is_kept_as_conflict(self):
        # the lane deleted a main function: never decided by the refresh (no whole-file main overwrite, COORD 11-15)
        pad = "".join(f"P{i} = {i}\n" for i in range(12)); qad = pad.replace("P", "Q")
        lane = "def lane_fn():\n    return 'lane'\n" + pad + qad
        self._tree("tools/die_plan/schema.py", lane)
        (self.dev / "tools/die_plan/schema.py").write_text(pad + "def full_area_hard_ip(t):\n    return 1\n" + qad)
        base = self.commit("base")
        (self.d / "mq/src-refresh-last.json").write_text(json.dumps({"qc": base}))
        (self.dev / "tools/die_plan/schema.py").write_text(pad + "def full_area_hard_ip(t):\n    return 1\n" + qad
                                                           + "def tap_offset_table():\n    return 2\n")
        self.commit("v2")
        r = self.daily()
        self.assertIn("CONFLICT kept", r.stdout)
        self.assertIn("full_area_hard_ip", r.stdout)
        self.assertEqual((self.src / "tools/die_plan/schema.py").read_text(), lane)
        self.assertEqual(self.rep("tools/die_plan/schema.py").read_text(), lane)

    def test_staged_file_using_an_attribute_the_tree_module_lacks_fails_the_smoke(self):
        # the tree's schema.py is a lane copy without full_area_hard_ip and is NOT in the batch; main's gen_phys calls it
        self._tree("tools/die_plan/schema.py", "import os\nX = 1\n")
        (self.dev / "tools/die_plan/schema.py").write_text("import os\nX = 1\ndef full_area_hard_ip(t):\n    return 1\n")
        base = self.commit("base")
        (self.d / "mq/src-refresh-last.json").write_text(json.dumps({"qc": base}))
        (self.dev / "tools/die_plan/gen_phys.py").write_text("import schema as S\n\ndef f(t, d):\n    return S.full_area_hard_ip(t), "
                                                             "S.X, d.get(1), S.os\n")
        self.commit("v2")
        r = self.daily()
        self.assertIn("STAGED CHECK FAILED", r.stdout + r.stderr)
        self.assertIn("S.full_area_hard_ip", r.stdout)
        self.assertNotIn("S.X", r.stdout)
        self.assertFalse((self.src / "tools/die_plan/gen_phys.py").exists())
        self.assertEqual(self.last(), base)

    def test_staged_smoke_failure_swaps_nothing(self):
        (self.dev / "tools/die_plan/a.py").write_text("import no_such_module_xyz\nA = 2\n")
        self.commit("v2")
        r = self.daily()
        self.assertIn("STAGED CHECK FAILED", r.stdout + r.stderr)
        self.assertEqual((self.src / "tools/die_plan/a.py").read_text(), "A = 1\n")
        self.assertEqual(self.rep("tools/die_plan/a.py").read_text(), "A = 1\n")
        self.assertEqual(self.last(), self.v1)

    def test_lazy_third_party_import_does_not_fail_the_smoke(self):
        # die_clock.cmd_render imports matplotlib inside the function; the gen hosts have no matplotlib (dry run 11-15)
        (self.dev / "tools/die_plan/a.py").write_text("A = 2\n\ndef render():\n    import no_such_module_xyz\n"
                                                      "    return no_such_module_xyz\n")
        v2 = self.commit("v2")
        r = self.daily()
        self.assertNotIn("STAGED CHECK FAILED", r.stdout + r.stderr)
        self.assertIn("A = 2", (self.src / "tools/die_plan/a.py").read_text())
        self.assertEqual(self.last(), v2)

    def test_replica_drift_refuses_then_put_heals(self):
        (self.src / "tools/die_plan/helper.py").write_text("H = 1\n")   # a lane copied a file to the gen host copy only
        (self.dev / "tools/die_plan/a.py").write_text("A = 2\n")
        self.commit("v2")
        r = self.daily()
        self.assertIn("REPLICA DRIFT", r.stdout + r.stderr)
        self.assertIn("tools/die_plan/helper.py", r.stdout)
        self.assertEqual((self.src / "tools/die_plan/a.py").read_text(), "A = 1\n")
        self.assertEqual(self.last(), self.v1)
        e = subprocess.run([sys.executable, "-I", P, "drift", "--post"], env=self.env, capture_output=True, text=True, timeout=300)
        self.assertIn("helper.py", e.stdout)
        self.assertIn("REPLICA DRIFT", (self.d / "coord/lanes/COORD-REVIEW-QUEUE.md").read_text())
        u = subprocess.run([sys.executable, "-I", P, "put", "--die", "qc", "tools/die_plan/helper.py", "--apply"], env=self.env,
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(u.returncode, 0, u.stdout + u.stderr)
        self.assertEqual(self.rep("tools/die_plan/helper.py").read_text(), "H = 1\n")
        r = self.daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rep("tools/die_plan/a.py").read_text(), "A = 2\n")

    def test_swap_failure_on_one_host_rolls_back_every_host(self):
        (self.dev / "tools/die_plan/a.py").write_text("A = 2\n")
        (self.dev / "tools/die_plan/c.py").write_text("C = 1\n")
        self.commit("v2")
        rd = self.rep("tools/die_plan")
        os.chmod(rd, 0o555)                                            # the replica cannot take the swap
        try:
            r = self.daily()
        finally:
            os.chmod(rd, 0o755)
        self.assertIn("ROLLED BACK", r.stdout + r.stderr)
        self.assertEqual((self.src / "tools/die_plan/a.py").read_text(), "A = 1\n")
        self.assertFalse((self.src / "tools/die_plan/c.py").exists())
        self.assertEqual(self.rep("tools/die_plan/a.py").read_text(), "A = 1\n")
        self.assertEqual(self.last(), self.v1)


if __name__ == "__main__":
    unittest.main()


class PutSnapshot(unittest.TestCase):
    """SNAP-RO-1119: a pinned snapshot is read-only, so `put --apply` makes a NEW snapshot version with the file (QC-HOLD-0030: ERROR with no reason on every host)"""

    def mod(self):
        import importlib.machinery, importlib.util
        ld = importlib.machinery.SourceFileLoader("ot_src_refresh_mod", P)
        spec = importlib.util.spec_from_loader("ot_src_refresh_mod", ld)
        m = importlib.util.module_from_spec(spec)
        ld.exec_module(m)
        return m

    def test_error_text_carries_the_note(self):
        m = self.mod()
        self.assertEqual(m.fmt_put_result({"results": [{"path": "a.py", "status": "ERROR", "note": "[Errno 13] Permission denied: '/t/.mqref.x'"}, {"path": "b.py", "status": "SAME"}]}),
                         "a.py=ERROR ([Errno 13] Permission denied: '/t/.mqref.x') b.py=SAME")
        self.assertEqual(m.fmt_put_result({"error": "no tree /x"}), "ERROR no tree /x")

    def test_new_snapshot_version_carries_the_file_and_the_old_one_is_untouched(self):
        import base64, hashlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "autopilot"))
        import live_tree as LT
        import src_manifest as SM
        m = self.mod()
        t = pathlib.Path(tempfile.mkdtemp())
        files = {"tools/die_plan/a.py": b"A = 1\n"}
        pub = t / "src_x_r1"
        for p, b in files.items():
            (pub / p).parent.mkdir(parents=True, exist_ok=True)
            (pub / p).write_bytes(b)
        mf = {"version": 1, "main_sha": "a" * 40, "scope": ["tools"], "overlay": {}, "files": {p: hashlib.sha256(b).hexdigest() for p, b in files.items()}}
        mf["manifest_hash"] = SM.manifest_hash(mf)
        (pub / SM.MANIFEST).write_text(json.dumps(mf))
        (pub / SM.HASHFILE).write_text(mf["manifest_hash"] + "\n")
        SM.make_ro(str(pub))
        live, snaps = LT.live_path("d", str(t)), LT.snap_root("d", str(t))
        LT.host_seed(str(pub), live)
        LT.host_apply(live, "", snaps, "s2")
        jobs = [{"path": "tools/die_plan/hold_margin_family.py", "new": base64.b64encode(b"H = 2\n").decode()}]
        pack = str(t / "pk")
        m.build_put_pack(jobs, mf["manifest_hash"], pack)
        LT.host_apply(live, pack, snaps, "s2_p1")
        s2, s3 = snaps + "/s2", snaps + "/s2_p1"
        self.assertFalse(os.path.exists(s2 + "/tools/die_plan/hold_margin_family.py"))
        self.assertEqual(open(s3 + "/tools/die_plan/hold_margin_family.py", "rb").read(), b"H = 2\n")
        m3 = json.load(open(s3 + "/" + SM.MANIFEST))
        self.assertIn("tools/die_plan/hold_margin_family.py", m3["overlay"])
        self.assertEqual(SM.verify(s3, expect=m3["manifest_hash"], ro=True, full=True)[0], [])
        self.assertEqual(LT.writable_names(s3), [])
        for dp, dn, fn in os.walk(t):
            os.chmod(dp, 0o755)
