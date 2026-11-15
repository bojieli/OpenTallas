"""ot-merge-queue (MERGE-QUEUE-1): approval parsing, lane lookup, tag series, test selection, and one end-to-end tick on a
throwaway origin: a green branch lands with tags + MERGED, a red one and a conflicting one get MERGE-FAIL, a second tick is a no-op."""
import importlib.machinery, importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest

P = str(pathlib.Path(__file__).with_name("ot-merge-queue"))


def load(env=None):
    old = dict(os.environ)
    os.environ.update(env or {})
    try:
        loader = importlib.machinery.SourceFileLoader("ot_merge_queue", P)
        m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_merge_queue", loader))
        loader.exec_module(m)
        return m
    finally:
        os.environ.clear(); os.environ.update(old)


M = load()


class Parse(unittest.TestCase):
    def test_approvals_branch_sha_several_per_line_and_revoke(self):
        q = ("- 2026-11-14 19:30 PST [COORD] ruled: COORD APPROVED: claude/a-1114 @0123456789ab; COORD APPROVED: @abcdef1234\n"
             "- 2026-11-14 19:31 PST READY [LANE-X -> COORD] branch claude/x head 99999999aa (asks: COORD APPROVED: claude/x @99999999aa)\n"
             "- 2026-11-14 19:32 PST COORD APPROVED: claude/b @fedcba98765\n"
             "- 2026-11-14 19:33 PST COORD REVOKED: claude/b @fedcba9\n"
             "- 2026-11-14 19:34 PST COORD APPROVED: claude/a-1114 @0123456789ab (repeat)\n")
        a = M.parse_approvals(q)
        self.assertEqual([x["key"] for x in a], ["claude/a-1114@0123456789ab", "-@abcdef1234", "claude/b@fedcba98765"])
        self.assertEqual([x["revoked"] for x in a], [False, False, True])

    def test_only_coord_or_owner_approves(self):
        q = ("- 2026-11-14 19:55 PST STATE [MERGE-QUEUE-1 (successor) -> COORD] waiting on COORD line: COORD APPROVED: claude/m @54d5fd4ca78\n"
             "- 2026-11-14 19:56 PST ASK [LANE-Y -> COORD] please post COORD APPROVED: claude/y @1111111111\n"
             "- 2026-11-14 19:57 PST RULING [COORD -> LANE-Z] COORD APPROVED: claude/z @2222222222\n"
             "- 2026-11-14 19:58 PST [OWNER] COORD APPROVED: claude/o @3333333333\n")
        self.assertEqual([x["key"] for x in M.parse_approvals(q)], ["claude/z@2222222222", "claude/o@3333333333"])

    def test_lane_from_ready_line_else_branch(self):
        q = ("- READY [TYPE-KVAHUB -> COORD] branch claude/type-kvahub-1114 head 9c23b2490fc6\n"
             "- STATE [KIT-OPS-5 -> COORD] cc about claude/type-kvahub-1114\n")
        self.assertEqual(M.lane_for(q, "claude/type-kvahub-1114", "9c23b2490fc6"), "TYPE-KVAHUB")
        self.assertEqual(M.lane_for("", "claude/admit-tune-30-1114", "76948b1b43"), "ADMIT-TUNE-30")
        q2 = ("- READY [WAVE-RECIPE-1 -> MERGE-QUEUE-1] branch claude/w-1114 @3d69f0eb0c5 asks COORD APPROVED: claude/w-1114 @3d69f0eb0c5\n"
              "- RULING [COORD -> MERGE-QUEUE-1] COORD APPROVED: claude/w-1114 @3d69f0eb0c5\n"
              "- STATE [MERGE-QUEUE-1 -> COORD] about 3d69f0eb0c5\n")
        self.assertEqual(M.lane_for(q2, "claude/w-1114", "3d69f0eb0c5"), "WAVE-RECIPE-1")
        q3 = q2 + "- READY [MERGE-QUEUE-1 -> COORD] re-queued w 3d69f0eb0c5 after a false RED\n"
        self.assertEqual(M.lane_for(q3, "claude/w-1114", "3d69f0eb0c5"), "WAVE-RECIPE-1")

    def test_next_tag_follows_newest_series(self):
        names = ["abc\trefs/tags/flow-20261113-cu-kv", "abc\trefs/tags/flow-20261113-ct-hbm", "x\trefs/tags/flow-20261112-zz-qc"]
        self.assertEqual(M.next_tag(names, ""), "flow-20261113-cv")
        self.assertEqual(M.next_tag(names, "tags flow-20261113-cx-head read back"), "flow-20261113-cy")
        self.assertEqual(M.next_tag(["refs/tags/flow-20261113-cz-s81"]), "flow-20261113-da")


class Select(unittest.TestCase):
    T = ["tools/autopilot/test_kit_wave.py", "tools/autopilot/test_autopilot_x.py", "tools/die_plan/test_core_place_slot.py",
         "tools/die_plan/test_other.py", "tools/fleet/test_ot_run_x.py", "tools/fleet/test_ot_heavy_y.py",
         "tools/fleet/test_ot_mem_grow.py", "tools/fleet/test_grt.py"]
    TEXT = {"tools/die_plan/test_other.py": "import core_place\n", "tools/fleet/test_grt.py": "uses grt183_make.sh here"}

    def sel(self, changed):
        return M.select_tests(changed, self.T, lambda t: self.TEXT.get(t, ""))[0]

    def test_autopilot_rule(self):
        self.assertIn("tools/autopilot/test_kit_wave.py", self.sel(["tools/autopilot/autopilot.py"]))

    def test_die_plan_named_and_referencing(self):
        self.assertEqual(self.sel(["tools/die_plan/core_place.py"]),
                         ["tools/die_plan/test_core_place_slot.py", "tools/die_plan/test_other.py"])

    def test_ot_run_and_ot_heavy(self):
        self.assertEqual(self.sel(["tools/fleet/ot-run"]), ["tools/fleet/test_ot_run_x.py"])
        self.assertEqual(self.sel(["tools/fleet/ot-heavy-reconcile"]), ["tools/fleet/test_ot_heavy_y.py"])

    def test_own_tests_and_shell_reference(self):
        self.assertEqual(self.sel(["tools/fleet/ot-mem-grow", "tools/fleet/test_ot_mem_grow.py"]), ["tools/fleet/test_ot_mem_grow.py"])
        self.assertEqual(self.sel(["physical/common_flow/grt183_make.sh"]), ["tools/fleet/test_grt.py"])

    def test_docs_select_nothing(self):
        self.assertEqual(self.sel(["docs/X.md"]), [])


def sh(*a, cwd=None):
    return subprocess.run(list(a), cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        d = self.d
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
        sh(*g, "init", "-q", "--bare", str(d / "origin.git"))
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "dev"))
        dev = d / "dev"
        (dev / "tools/x").mkdir(parents=True)
        (dev / "tools/x/mod.py").write_text("def f():\n    return 1\n")
        (dev / "tools/x/test_mod.py").write_text("import os, sys\nsys.path.insert(0, os.path.dirname(__file__))\nimport mod\n\n"
                                                 "def test_f():\n    assert mod.f() >= 1\n")
        sh(*g, "add", "-A", cwd=dev); sh(*g, "commit", "-qm", "base", cwd=dev); sh(*g, "push", "-q", "origin", "main", cwd=dev)
        self.g, self.dev = g, dev
        self.shas = {}
        for name, body, test in (("good", "def f():\n    return 2\n", None),
                                 ("red", "def f():\n    return 0\n", None),
                                 ("clash", "def f():\n    return 3\n", None)):
            sh(*g, "checkout", "-q", "-b", f"claude/{name}", "main", cwd=dev)
            (dev / "tools/x/mod.py").write_text(body)
            sh(*g, "commit", "-qam", name, cwd=dev)
            sh(*g, "push", "-q", "origin", f"claude/{name}", cwd=dev)
            self.shas[name] = sh("git", "rev-parse", "HEAD", cwd=dev)
        sh(*g, "clone", "-q", str(d / "origin.git"), str(d / "repo"))
        sh("git", "config", "user.name", "q", cwd=d / "repo"); sh("git", "config", "user.email", "q@q", cwd=d / "repo")
        sh("git", "config", "extensions.worktreeConfig", "true", cwd=d / "repo")
        (d / "coord/lanes").mkdir(parents=True)
        s = self.shas
        (d / "coord/lanes/COORD-REVIEW-QUEUE.md").write_text(
            f"- 2026-11-14 19:00 PST READY [LANE-GOOD -> COORD] branch claude/good head {s['good'][:10]}\n"
            f"- 2026-11-14 19:01 PST READY [LANE-RED -> COORD] branch claude/red head {s['red'][:10]}\n"
            f"- 2026-11-14 19:02 PST [COORD] COORD APPROVED: claude/good @{s['good'][:10]}; COORD APPROVED: claude/red @{s['red'][:10]}; "
            f"COORD APPROVED: claude/clash @{s['clash'][:10]} tags flow-20261113-cw-head\n")
        (d / "commit.sh").write_text("#!/bin/bash\necho committed \"$@\" >> " + str(d / "commits.log") + "\n")
        self.env = dict(os.environ, MQ_HOME=str(d / "mq"), MQ_REPO=str(d / "repo"), MQ_WT=str(d / "wt"), MQ_COORD=str(d / "coord"),
                        MQ_COORD_COMMIT=str(d / "commit.sh"), MQ_PYTHON=sys.executable, MQ_FALLBACK_REMOTE="", MQ_XDIST="1",
                        MQ_SYNC_HOOK="", MQ_SRC_HOOK="", MQ_SPARSE="/*,!/*/,/tools/", GIT_AUTHOR_NAME="q", GIT_AUTHOR_EMAIL="q@q",
                        GIT_COMMITTER_NAME="q", GIT_COMMITTER_EMAIL="q@q")

    def tick(self):
        return subprocess.run([sys.executable, "-I", P, "tick"], env=self.env, capture_output=True, text=True, timeout=600)

    def test_green_lands_red_and_conflict_fail_second_tick_noop(self):
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        o = self.d / "origin.git"
        main = sh("git", "rev-parse", "main", cwd=o)
        sh("git", "merge-base", "--is-ancestor", self.shas["good"], main, cwd=o)
        self.assertNotEqual(subprocess.run(["git", "merge-base", "--is-ancestor", self.shas["red"], main], cwd=o).returncode, 0)
        tags = sh("git", "tag", "-l", "flow-*", cwd=o).split()
        self.assertEqual(sorted(tags), [f"flow-20261113-cx-{x}" for x in sorted(("head", "qc", "kv", "s81", "hbm"))])
        q = (self.d / "coord/lanes/COORD-REVIEW-QUEUE.md").read_text()
        self.assertIn("MERGED [MERGE-QUEUE -> LANE-GOOD] claude/good@", q)
        self.assertIn("MERGE-FAIL [MERGE-QUEUE -> LANE-RED] claude/red@", q)
        self.assertIn("test_mod.py::test_f", q)
        self.assertRegex(q, r"MERGE-FAIL \[MERGE-QUEUE -> CLASH\] claude/clash@\w+ NOT landed, skipped: conflict with main \w+ in: tools/x/mod.py")
        self.assertTrue((self.d / "mq/log").is_file())
        st = json.loads((self.d / "mq/state.json").read_text())
        self.assertEqual(sorted(i["status"] for i in st["items"].values()), ["FAIL", "FAIL", "MERGED"])
        n = q.count("\n")
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.d / "coord/lanes/COORD-REVIEW-QUEUE.md").read_text().count("\n"), n)
        self.assertEqual(sh("git", "rev-parse", "main", cwd=o), main)

    def test_already_in_main_posts_nothing_to_land(self):
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        sh(*self.g, "merge", "-q", "--ff-only", "claude/good", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text(f"- COORD APPROVED: claude/good @{self.shas['good'][:10]}\n")
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nothing to land", q.read_text())


if __name__ == "__main__":
    unittest.main()
