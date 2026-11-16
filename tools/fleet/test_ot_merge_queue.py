"""ot-merge-queue (MERGE-QUEUE-1): approval parsing, lane lookup, tag series, test selection, and one end-to-end tick on a
throwaway origin: a green branch lands with tags + MERGED, a red one and a conflicting one get MERGE-FAIL, a second tick is a no-op."""
import importlib.machinery, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

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

    def test_approval_with_the_word_branch(self):
        a = M.parse_approvals("COORD APPROVED: branch claude/kit-ops-5-curplan-1114 @4c696027e0ef (supersedes @86a682bd0276)\n")
        self.assertEqual([x["key"] for x in a], ["claude/kit-ops-5-curplan-1114@4c696027e0ef"])

    def test_lettered_list_and_content_note_from_the_cutoff_only(self):
        q = ("- 2026-11-15 11:06 PST RULING [COORD -> MQ] r130 COORD APPROVED (content): claude/kv-pvgen-1115 @bb5381316de5 (plan key)\n"
             "- 2026-11-15 11:15 PST RULING [COORD -> MQ] r132 COORD APPROVED: (a) claude/g-1115 @5f6c68b932d (GATE main=6b4f2ff26a2 "
             "18/18). (b) claude/l-1115 @1617cedd312 (class 8). Also: x\n"
             "- 2026-11-14 11:15 PST RULING [COORD] COORD APPROVED: (a) claude/old-1 @1234567abc (b) claude/old-2 @abcdef1234\n"
             "- 2026-11-15 11:20 PST STATE [LANE-X -> COORD] COORD APPROVED: (a) claude/self @aaaaaaa111\n")
        self.assertEqual([x["key"] for x in M.parse_approvals(q)],
                         ["claude/kv-pvgen-1115@bb5381316de5", "claude/g-1115@5f6c68b932d", "claude/l-1115@1617cedd312"])

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
                        MQ_SYNC_HOOK="", MQ_SRC_HOOK="", MQ_GATE_REMOTE="", MQ_SPARSE="/*,!/*/,/tools/", GIT_AUTHOR_NAME="q", GIT_AUTHOR_EMAIL="q@q",
                        GIT_COMMITTER_NAME="q", GIT_COMMITTER_EMAIL="q@q")

    def tick(self, env=None):
        return subprocess.run([sys.executable, "-I", P, "tick"], env=env or self.env, capture_output=True, text=True, timeout=600)

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

    def test_unfetchable_sha_fails_without_crashing_the_tick(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text(f"- COORD APPROVED: claude/ghost @deadbeef123\n- COORD APPROVED: claude/good @{self.shas['good'][:10]}\n")
        self.env["MQ_WAIT_TICKS"] = "1"
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = q.read_text()
        self.assertIn("MERGE-FAIL [MERGE-QUEUE -> ", t); self.assertIn("claude/ghost@deadbeef123 NOT landed", t)
        self.assertRegex(t, r"MERGED \[MERGE-QUEUE -> [^]]+\] claude/good@")

    def test_ready_without_a_usable_stamp_is_gated_not_bounced_only_for_new_lines(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        o = self.d / "origin.git"
        main = sh("git", "rev-parse", "main", cwd=o)
        g = self.shas["good"]
        q.write_text(f"- 2026-11-15 07:00 PST READY [OLD-LANE -> COORD] branch claude/red @{self.shas['red'][:10]} no stamp\n")
        r = self.tick()                                  # rule goes live: the old READY is not judged
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("BOUNCE", q.read_text())
        with open(q, "a") as f:
            f.write(f"- 2026-11-15 08:00 PST READY [LANE-A -> COORD] branch claude/good @{g[:10]} tests ok\n"
                    f"- 2026-11-15 08:01 PST READY [LANE-B -> COORD] branch claude/good @{g[:11]} GATE main={main[:11]} pass=3/4\n"
                    f"- 2026-11-15 08:02 PST READY [LANE-C -> COORD] branch claude/clash @{self.shas['clash'][:10]} "
                    f"GATE main={g[:11]} pass=2/2\n"
                    f"- 2026-11-15 08:03 PST READY [LANE-D -> COORD] branch claude/good @{g[:12]} GATE main={main[:11]} pass=5/5\n"
                    f"- 2026-11-15 08:04 PST READY [LANE-E -> COORD] result line without a branch sha, GATE nothing\n")
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t, log = q.read_text(), (self.d / "mq/log").read_text()
        self.assertNotIn("BOUNCE", t)                        # COORD r178: never bounce; the queue gates it
        self.assertRegex(log, r"READY claude/good@\w+ line \d+: no GATE stamp; no remote runner")
        self.assertIn("pass=3/4 is not all-pass", log); self.assertIn("is not a commit on main", log)
        self.assertIn("gate stamp ok", log)
        self.assertNotIn("ready gate check error", log)   # a valid stamp is judged, not swallowed
        n = log.count("READY claude/")
        self.tick()
        self.assertEqual((self.d / "mq/log").read_text().count("READY claude/"), n)   # each READY judged once

    def test_gate_command_prints_the_stamp_for_green_and_touches_no_state(self):
        g = subprocess.run([sys.executable, "-I", P, "gate", "claude/good"], env=self.env, capture_output=True, text=True, timeout=600)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        main = sh("git", "rev-parse", "main", cwd=self.d / "origin.git")
        self.assertIn(f"GATE main={main[:11]} pass=1/1", g.stdout)
        self.assertTrue((self.d / "mq/gates" / f"{self.shas['good']}.json").is_file())
        r = subprocess.run([sys.executable, "-I", P, "gate", f"claude/red@{self.shas['red'][:10]}"], env=self.env, capture_output=True,
                           text=True, timeout=600)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("RED", r.stdout); self.assertNotIn("GATE main=", r.stdout)
        self.assertFalse((self.d / "mq/state.json").exists())                   # no queue state, nothing posted
        self.assertFalse((self.d / "commits.log").exists())
        self.assertEqual(sh("git", "rev-parse", "main", cwd=self.d / "origin.git"), main)

    def _dep_branch(self, name, test_body):
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        (self.dev / "data/fix").mkdir(parents=True, exist_ok=True)
        (self.dev / "data/fix/input.txt").write_text("42\n")
        (self.dev / "tools/x/test_mod_dep.py").write_text(test_body)
        sh(*self.g, "add", "data/fix/input.txt", "tools/x/test_mod_dep.py", cwd=self.dev)
        sh(*self.g, "commit", "-qm", "dep test", cwd=self.dev); sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        sh(*self.g, "checkout", "-q", "-b", name, "main", cwd=self.dev)
        (self.dev / "tools/x/mod.py").write_text("def f():\n    return 5\n")
        sh(*self.g, "commit", "-qam", name, cwd=self.dev); sh(*self.g, "push", "-q", "origin", name, cwd=self.dev)
        return subprocess.run([sys.executable, "-I", P, "gate", name], env=self.env, capture_output=True, text=True, timeout=600)

    def test_a_test_reading_stdin_does_not_hang_under_an_open_stdin_pipe(self):
        # KV-PVGEN 11-15: yosys started by tests waits on an inherited open stdin; the gate must hand pytest /dev/null
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        sh(*self.g, "checkout", "-q", "-b", "claude/stdin", "main", cwd=self.dev)
        (self.dev / "tools/x").mkdir(parents=True, exist_ok=True)
        (self.dev / "tools/x/test_stdin.py").write_text(
            "import subprocess\n\ndef test_child_reads_stdin():\n"
            "    assert subprocess.run(['cat'], capture_output=True, timeout=20).returncode == 0\n")
        sh(*self.g, "add", "tools/x/test_stdin.py", cwd=self.dev); sh(*self.g, "commit", "-qm", "stdin", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "claude/stdin", cwd=self.dev)
        p = subprocess.Popen([sys.executable, "-I", P, "gate", "claude/stdin"], env=self.env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            out = p.stdout.read(); err = p.stderr.read(); p.wait(timeout=600)
        finally:
            p.stdin.close()
        self.assertEqual(p.returncode, 0, out + err)
        self.assertIn("GATE main=", out)

    def test_gate_tree_gets_the_sources_a_selected_test_names(self):
        # the branch touches tools/x/mod.py only; the selected test reads data/fix/input.txt (outside the sparse set)
        g = self._dep_branch("claude/dep", "import os, pathlib, mod\nR = pathlib.Path(__file__).resolve().parents[2]\n\n"
                                           "def test_dep():\n    assert (R / \"data/fix/input.txt\").read_text() == \"42\\n\"\n"
                                           "    assert mod.f() >= 1\n")
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("GATE main=", g.stdout)
        self.assertIn("source dir(s) the tests name: data/fix", g.stdout)    # ran with the file, not masked as a main baseline
        self.assertNotIn("also fail on main", g.stdout)

    def test_source_missing_from_the_gate_tree_is_added_and_rerun(self):
        # a path the scan cannot see (built at run time) and the tree lacks: MISSING SOURCE, not RED and not a timeout
        g = self._dep_branch("claude/dyn", "import pathlib, mod\nR = pathlib.Path(__file__).resolve().parents[2]\n\n"
                                           "def test_dep():\n    assert (R / ('da' + 'ta') / 'fix' / 'input.txt').read_text()\n")
        # the run reported data/fix/input.txt missing: the gate adds data/fix and reruns once -> GREEN, dir listed
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("source dir(s) the tests name: data/fix", g.stdout)
        self.assertIn("GATE main=", g.stdout)

    def test_last_missing_source_round_adds_the_whole_allowed_top_dir(self):
        self.env = dict(self.env, MQ_GATE_MISS_ROUNDS="0", MQ_GATE_WHOLE_TOPS="data")
        g = self._dep_branch("claude/dyn2", "import pathlib, mod\nR = pathlib.Path(__file__).resolve().parents[2]\n\n"
                                            "def test_dep():\n    assert (R / ('da' + 'ta') / 'fix' / 'input.txt').read_text()\n")
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("source dir(s) the tests name: data", g.stdout)
        self.assertIn("GATE main=", g.stdout)

    def test_tick_lands_on_a_green_gate_record_without_a_second_test_run(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text("- 2026-11-15 07:00 PST STATE [X -> COORD] nothing\n")
        g = subprocess.run([sys.executable, "-I", P, "gate", "claude/good"], env=self.env, capture_output=True, text=True, timeout=600)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        with open(q, "a") as f:
            f.write(f"- 2026-11-15 09:00 PST [COORD] COORD APPROVED: claude/good @{self.shas['good'][:10]}\n")
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = (self.d / "mq/log").read_text()
        self.assertIn("gate record from hub", log)
        self.assertIn("MERGED", q.read_text())

    def test_tick_gates_on_the_remote_runner_and_lands_its_record(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text("- 2026-11-15 07:00 PST STATE [X -> COORD] nothing\n"
                     f"- 2026-11-15 09:00 PST [COORD] COORD APPROVED: claude/good @{self.shas['good'][:10]}\n")
        # the "remote" runner is the queue's own gate command; it writes the record the tick then reads
        d = self.d
        remote = (f"[ -d {d}/rrepo ] || git clone -q --no-checkout {d}/origin.git {d}/rrepo; MQ_HOME={d}/rmq MQ_REPO={d}/rrepo MQ_WT={d}/rwt {sys.executable} -I {P} gate {{key}}; rc=$?; "
                  f"mkdir -p {d}/mq/gates; cp {d}/rmq/gates/*.json {d}/mq/gates/; exit $rc")
        r = self.tick(env=dict(self.env, MQ_GATE_REMOTE=remote, MQ_GATE_REMOTE_TIMEOUT="120"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("remote gate record from", (self.d / "mq/log").read_text())
        self.assertIn("MERGED", q.read_text())

    def test_remote_red_is_red_and_a_runner_that_cannot_start_falls_back_to_the_hub(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text("- 2026-11-15 07:00 PST STATE [X -> COORD] nothing\n"
                     f"- 2026-11-15 09:00 PST [COORD] COORD APPROVED: claude/good @{self.shas['good'][:10]}\n")
        r = self.tick(env=dict(self.env, MQ_GATE_REMOTE="echo 'RED claude/good@x on main y: 1 failing: test_z.py'; exit 1"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("remote: 1 failing: test_z.py", (self.d / "mq/log").read_text())
        self.assertNotIn("MERGED", q.read_text())

    def test_remote_runner_missing_gates_on_the_hub(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text("- 2026-11-15 07:00 PST STATE [X -> COORD] nothing\n"
                     f"- 2026-11-15 09:00 PST [COORD] COORD APPROVED: claude/good @{self.shas['good'][:10]}\n")
        r = self.tick(env=dict(self.env, MQ_GATE_REMOTE="/nonexistent/ot-run {key}"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("remote gate did not run", (self.d / "mq/log").read_text())
        self.assertIn("MERGED", q.read_text())

    def test_parallel_gate_commands_run_together(self):
        procs = [subprocess.Popen([sys.executable, "-I", P, "gate", b], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True) for b in ("claude/good", "claude/clash", "claude/red")]
        outs = [p.communicate(timeout=600) for p in procs]
        self.assertEqual([p.returncode for p in procs], [0, 0, 1], outs)
        self.assertEqual(sum("GATE main=" in o for o, _ in outs), 2)

    def test_fleet_test_timeout_under_load_is_rerun_alone_once(self):
        mark = self.d / "slow.mark"
        mark.write_text("")
        sh(*self.g, "checkout", "-q", "-b", "claude/slow", "main", cwd=self.dev)
        (self.dev / "tools/fleet").mkdir(parents=True, exist_ok=True)
        (self.dev / "tools/fleet/test_slow.py").write_text(
            "import os, pathlib, time\n\ndef test_x():\n    m = pathlib.Path(os.environ['MQ_TEST_SLOWMARK'])\n"
            "    if m.exists():\n        m.unlink()\n        time.sleep(60)\n")
        sh(*self.g, "add", "tools/fleet/test_slow.py", cwd=self.dev); sh(*self.g, "commit", "-qm", "slow", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "claude/slow", cwd=self.dev)
        env = dict(self.env, MQ_FLEET_TIMEOUT="8", MQ_TEST_SLOWMARK=str(mark), MQ_SPARSE="/*,!/*/,/tools/")
        g = subprocess.run([sys.executable, "-I", P, "gate", "claude/slow"], env=env, capture_output=True, text=True, timeout=600)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("GATE main=", g.stdout)
        self.assertIn("TIMEOUT", g.stdout)                                       # reported as load-flaky, not RED

    def test_ready_for_an_approved_or_landed_sha_is_not_bounced(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text("- 2026-11-15 07:00 PST STATE [X -> COORD] nothing\n")
        self.tick()                                      # rule live
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        sh(*self.g, "merge", "-q", "--ff-only", "claude/good", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        with open(q, "a") as f:
            f.write(f"- 2026-11-15 09:00 PST READY [LANE-M -> COORD] branch claude/good @{self.shas['good'][:10]} no stamp, on main\n"
                    f"- 2026-11-15 09:01 PST READY [LANE-R -> COORD] branch claude/red @{self.shas['red'][:10]} no stamp\n"
                    f"COORD APPROVED: claude/red @{self.shas['red'][:10]}\n")
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("BOUNCE", q.read_text())
        self.assertNotIn("ready gate check error", (self.d / "mq/log").read_text())

    def test_priority_high_approval_lands_first(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text(f"- COORD APPROVED: claude/clash @{self.shas['clash'][:10]}\n"
                     f"- COORD APPROVED: claude/good @{self.shas['good'][:10]} Merge priority HIGH.\n")
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = q.read_text()
        self.assertRegex(t, r"MERGED \[MERGE-QUEUE -> [^]]+\] claude/good@")          # good first, so clash (same file) fails
        self.assertIn("claude/clash@", t.split("MERGED")[1])


if __name__ == "__main__":
    unittest.main()


class Reap(unittest.TestCase):
    def test_wt_drop_kills_processes_left_in_the_tree_and_its_basetemp_only(self):
        import importlib.machinery, importlib.util, tempfile, time
        d = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(d / "repo")], check=True)
        old = {k: os.environ.get(k) for k in ("MQ_HOME", "MQ_WT", "MQ_REPO")}
        os.environ.update(MQ_HOME=str(d / "mq"), MQ_WT=str(d / "wt"), MQ_REPO=str(d / "repo"))
        try:
            ld = importlib.machinery.SourceFileLoader("omq_reap", P)
            m = importlib.util.module_from_spec(importlib.util.spec_from_loader("omq_reap", ld)); ld.exec_module(m)
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        for x in ("wt/abc", "wt/bt/abc-a", "wt/other"):
            (d / x).mkdir(parents=True)
        a = subprocess.Popen(["sleep", "300"], cwd=d / "wt/abc")
        b = subprocess.Popen(["sleep", "300"], cwd=d / "wt/bt/abc-a")
        c = subprocess.Popen(["sleep", "300"], cwd=d / "wt/other")
        try:
            m.wt_drop("abc")
            time.sleep(0.5)
            self.assertIsNotNone(a.poll()); self.assertIsNotNone(b.poll()); self.assertIsNone(c.poll())
            self.assertFalse((d / "wt/abc").exists())
        finally:
            for p in (a, b, c):
                p.kill(); p.wait()
            shutil.rmtree(d, ignore_errors=True)
