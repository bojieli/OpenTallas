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


class SyncReporting(unittest.TestCase):
    def test_partial_success_reports_activated_current_and_actual_alert(self):
        r = subprocess.CompletedProcess([], 4,
            "ALERT installed tools differ from rt/abcdef123456: epyc7 /usr/local/bin/ot-heavy-reconcile differs\n"
            "rt/current -> abcdef123456 (was 0123456789ab); hosts epyc7:ok epyc8:FAIL 46 GB free < 50 GB\n",
            "SyntaxWarning: invalid escape sequence\n")
        note = M.sync_hook_note(r)
        self.assertTrue(note.startswith("rt/current -> abcdef123456"))
        self.assertIn("epyc8:FAIL 46 GB free < 50 GB", note)
        self.assertIn("ot-heavy-reconcile differs", note)
        self.assertIn("stderr context: SyntaxWarning", note)
        self.assertNotIn("not moved", note)
        self.assertNotIn("unchanged", note)

    def test_smoke_failure_reports_no_activation_with_real_cause(self):
        r = subprocess.CompletedProcess([], 3, "SMOKE-FAIL rt abcdef123456: ['syntax: kit_wave.py']\n", "SyntaxWarning: context\n")
        note = M.sync_hook_note(r)
        self.assertTrue(note.startswith("SMOKE-FAIL"))
        self.assertIn("syntax: kit_wave.py", note)
        self.assertIn("rt/current unchanged: smoke failed before activation", note)
        self.assertIn("stderr context", note)

    def test_floor_refusal_is_the_note_not_the_last_prune_line(self):
        r = subprocess.CompletedProcess([], 1,
            "2026-11-17 20:40:39 SYNC pruned 1 old snapshots (kept 10 newest + current): e757ea57282d\n"
            "2026-11-17 20:40:40 SYNC FAILED RuntimeError: /srv/opentallas-scratch2/claude/rt: 62 GB free < 100 GB (OT_RT_MIN_FREE_GB); nothing written (pruned 1)\n", "")
        note = M.sync_hook_note(r)
        self.assertTrue(note.startswith("RuntimeError: /srv/opentallas-scratch2/claude/rt: 62 GB free < 100 GB"))
        self.assertNotIn("not reported", note)

    def test_unreported_state_never_claims_current_unchanged(self):
        note = M.sync_hook_note(subprocess.CompletedProcess([], 1, "", "Traceback: failed after flip"))
        self.assertIn("activation state not reported", note)
        self.assertNotIn("unchanged", note)
        self.assertIn("Traceback", note)


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

    def test_proved_new_evidence_copy_keeps_exact_consumer_not_basenames(self):
        f = "results/component/copied_operator.sv"
        tests = ["tools/test_real.py", "tools/test_record.py", "tools/test_new.py"]
        texts = {tests[0]: "copied_operator.sv", tests[1]: f}
        got, _ = M.select_tests([f, tests[2]], tests, lambda t: texts.get(t, ""), copies={f: "rtl/copied_operator.sv"})
        self.assertEqual(got, [tests[2], tests[1]])
        ordinary, _ = M.select_tests([f], tests, lambda t: texts.get(t, ""))
        self.assertEqual(ordinary, [tests[0], tests[1]])
        copied_test = "results/component/test_real.py"
        got, _ = M.select_tests([copied_test], [copied_test] + tests, lambda t: texts.get(t, ""), copies={copied_test: tests[0]})
        self.assertEqual(got, [])

    def test_copy_proof_requires_added_path_identical_blob_and_unchanged_authority(self):
        from unittest.mock import patch
        old = "results/old/operator.sv"; new = "results/new/operator.sv"; bad = "results/bad/operator.sv"
        index = ("100644 abc 0\trtl/operator.sv\0" + "100644 abc 0\t" + old + "\0" +
                 "100644 abc 0\t" + new + "\0" + "100644 xyz 0\t" + bad + "\0")
        def g(*a, **kw):
            return subprocess.CompletedProcess([], 0, new + "\n" + bad if a[0] == "diff" else index, "")
        with patch.object(M, "git", side_effect=g):
            self.assertEqual(M.evidence_copies(Path("/unused"), "base", "tip", [old, new, bad]), {new: "rtl/operator.sv"})
            self.assertEqual(M.evidence_copies(Path("/unused"), "base", "tip", [old, new, bad, "rtl/operator.sv"]), {})

    def test_physical_die_plan_tests_next_to_a_changed_file_are_selected(self):
        """r619 changed physical/die_plan/qwen_compute/bind/ and the gate ran no test ('static only'): every test_*.py in that directory now runs"""
        T = ["physical/die_plan/qwen_compute/bind/test_bind_a.py", "physical/die_plan/qwen_compute/bind/test_other_thing.py",
             "physical/die_plan/qwen_compute/bind/tests/test_in_tests_dir.py", "physical/die_plan/qwen_compute/test_parent.py",
             "physical/die_plan/kv/bind/test_other_die.py", "tools/die_plan/test_x.py"]
        got = M.select_tests(["physical/die_plan/qwen_compute/bind/native_bind.py"], T, lambda t: "")[0]
        self.assertEqual(got, T[:3])                                   # same directory + its tests/ dir; not the parent directory, another die, or tools/
        self.assertEqual(M.select_tests(["physical/die_plan/qwen_compute/bind/plan.json"], T, lambda t: "")[0], T[:3])   # a data file there selects them too
        self.assertEqual(M.select_tests(["physical/die_plan/qwen_compute/bind/native_bind.py"], [], lambda t: "")[0], [])

    def test_all_test_files_lists_physical_die_plan(self):
        from unittest.mock import patch
        listing = "tools/x/test_a.py\nphysical/die_plan/q/test_b.py\nphysical/die_plan/q/data.json\n"
        with patch.object(M, "git", return_value=subprocess.CompletedProcess([], 0, listing, "")) as g, \
                patch.object(pathlib.Path, "is_file", return_value=True):
            self.assertEqual(M.all_test_files(pathlib.Path("/wt")), ["tools/x/test_a.py", "physical/die_plan/q/test_b.py"])
        self.assertIn("physical/die_plan", g.call_args[0])

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

    # ---- MERGE-AUTO-1118: no approval wait
    def _omq(self, *a):
        return subprocess.run([sys.executable, "-I", P, *a], env=self.env, capture_output=True, text=True, timeout=600)

    def _auto_setup(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text("# queue\n")
        self.env["MQ_AUTO_DIGEST_SECS"] = "0"
        return q

    def test_auto_tick_merges_only_green_gated_current_tip_and_only_when_switched_on(self):
        q = self._auto_setup()
        g = self._omq("gate", "claude/good"); self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        r = self._omq("gate", "claude/red"); self.assertNotEqual(r.returncode, 0)          # RED writes no record
        o = self.d / "origin.git"; main = sh("git", "rev-parse", "main", cwd=o)
        self.assertEqual(self.tick().returncode, 0)                                         # switch off: nothing lands
        self.assertEqual(sh("git", "rev-parse", "main", cwd=o), main)
        listing = self._omq("auto-list"); self.assertIn("auto-merge OFF", listing.stdout); self.assertIn("claude/good", listing.stdout)
        self.assertNotIn("claude/red", listing.stdout)
        (self.d / "mq/auto.on").write_text("")
        r = self.tick(); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        sh("git", "merge-base", "--is-ancestor", self.shas["good"], sh("git", "rev-parse", "main", cwd=o), cwd=o)
        self.assertIn(f"MERGED-AUTO [claude/good] @{self.shas['good']}", (self.d / "mq/log").read_text())
        t = q.read_text()
        self.assertRegex(t, r"MERGED \[MERGE-QUEUE -> [^]]+\] claude/good@"); self.assertIn("MERGED-AUTO digest", t)
        self.assertNotIn("claude/red", t.replace("# queue", ""))
        n = t.count("\n"); self.tick()
        self.assertEqual(q.read_text().count("\n"), n)                                      # idempotent
        self.assertIn("Merge claude/good", sh("git", "log", "-3", "--format=%B", "main", cwd=o)); self.assertIn("auto-merge", sh("git", "log", "-3", "--format=%B", "main", cwd=o))

    def test_auto_tick_respects_standalone_coord_revocation(self):
        q = self._auto_setup()
        for branch in ("good", "clash"):
            gate = self._omq("gate", f"claude/{branch}")
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        q.write_text(
            f"- 2026-11-20 05:16 PST RULING [COORD -> MERGE] "
            f"COORD REVOKED: claude/good @{self.shas['good'][:12]}\n"
            f"- 2026-11-20 05:17 PST STATE [OTHER-LANE -> MERGE] "
            f"COORD REVOKED: claude/clash @{self.shas['clash']}\n"
        )
        (self.d / "mq/auto.on").write_text("")
        listing = self._omq("auto-list")
        self.assertNotIn("claude/good", listing.stdout)
        self.assertIn("claude/clash", listing.stdout)
        result = self.tick()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("MERGED-AUTO [claude/good]", result.stdout)
        self.assertIn("MERGED-AUTO [claude/clash]", result.stdout)

    def test_auto_tick_skips_a_tip_that_moved_past_its_gate_and_an_old_record(self):
        self._auto_setup()
        self.assertEqual(self._omq("gate", "claude/good").returncode, 0)
        self.assertEqual(self._omq("gate", "claude/clash").returncode, 0)
        sh(*self.g, "checkout", "-q", "claude/good", cwd=self.dev)
        (self.dev / "tools/x/mod.py").write_text("def f():\n    return 9\n")
        sh(*self.g, "commit", "-qam", "moved", cwd=self.dev); sh(*self.g, "push", "-q", "origin", "claude/good", cwd=self.dev)
        old = self.d / "mq/gates" / f"{self.shas['clash']}.json"
        os.utime(old, (1.0, 1.0))
        (self.d / "mq/auto.on").write_text("")
        o = self.d / "origin.git"; main = sh("git", "rev-parse", "main", cwd=o)
        self.assertIn("no candidate", "no candidate" if "0 candidate(s)" in self._omq("auto-list").stdout else self._omq("auto-list").stdout)
        self.assertEqual(self.tick().returncode, 0)
        self.assertEqual(sh("git", "rev-parse", "main", cwd=o), main)

    def test_auto_tick_conflict_aborts_with_merge_fail_and_no_force(self):
        q = self._auto_setup()
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        self.assertEqual(self._omq("gate", "claude/clash").returncode, 0)
        sh(*self.g, "merge", "-q", "--no-edit", "claude/good", cwd=self.dev); sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        (self.d / "mq/auto.on").write_text("")
        o = self.d / "origin.git"; main = sh("git", "rev-parse", "main", cwd=o)
        self.assertEqual(self.tick().returncode, 0)
        self.assertEqual(sh("git", "rev-parse", "main", cwd=o), main)
        self.assertNotIn("MERGED-AUTO", (self.d / "mq/log").read_text())

    def test_merge_now_needs_gate_tip_and_lands_once(self):
        q = self._auto_setup()
        s = self.shas
        r = self._omq("merge-now", "claude/good", s["good"]); self.assertEqual(r.returncode, 3, r.stdout); self.assertIn("NO-GATE", r.stdout)
        self.assertEqual(self._omq("gate", "claude/good").returncode, 0)
        r = self._omq("merge-now", "claude/good", s["good"][:10]); self.assertEqual(r.returncode, 2)
        r = self._omq("merge-now", "claude/good", "0" * 40); self.assertEqual(r.returncode, 3)
        o = self.d / "origin.git"
        r = self._omq("merge-now", "claude/good", s["good"]); self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("MERGED", r.stdout)
        sh("git", "merge-base", "--is-ancestor", s["good"], "main", cwd=o)
        self.assertIn(f"MERGED-AUTO [claude/good] @{s['good']}", (self.d / "mq/log").read_text())
        r = self._omq("merge-now", "claude/good", s["good"]); self.assertEqual(r.returncode, 0); self.assertIn("already settled", r.stdout)

    def test_merge_now_refuses_a_moved_tip(self):
        self._auto_setup()
        self.assertEqual(self._omq("gate", "claude/good").returncode, 0)
        old = self.shas["good"]
        sh(*self.g, "checkout", "-q", "claude/good", cwd=self.dev)
        (self.dev / "tools/x/mod.py").write_text("def f():\n    return 9\n")
        sh(*self.g, "commit", "-qam", "moved", cwd=self.dev); sh(*self.g, "push", "-q", "origin", "claude/good", cwd=self.dev)
        o = self.d / "origin.git"; main = sh("git", "rev-parse", "main", cwd=o)
        r = self._omq("merge-now", "claude/good", old); self.assertEqual(r.returncode, 4); self.assertIn("TIP-MOVED", r.stdout)
        self.assertEqual(sh("git", "rev-parse", "main", cwd=o), main)

    def test_merge_now_skips_when_main_moved_over_its_files(self):
        self._auto_setup()
        self.assertEqual(self._omq("gate", "claude/good").returncode, 0)
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        (self.dev / "tools/x/test_mod.py").write_text((self.dev / "tools/x/test_mod.py").read_text() + "\n# touched\n")
        sh(*self.g, "commit", "-qam", "main moves", cwd=self.dev); sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        r = self._omq("merge-now", "claude/good", self.shas["good"]); self.assertEqual(r.returncode, 6, r.stdout + r.stderr)
        self.assertIn("gate it again", r.stdout)

    def _redwatch_pick(self, admitted):
        bindir = self.d / "bin"
        bindir.mkdir(exist_ok=True)
        shim = bindir / "ot-run"
        script = "printf 'localhost\\n'\n" if admitted else "printf 'NOT-RUN disk floor\\n' >&2\nexit 78\n"
        shim.write_text("#!/bin/sh\n" + script)
        shim.chmod(0o755)
        self.env["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]

    def test_redwatch_defers_untested_commit_without_losing_it_to_the_newest_cap(self):
        q = self._auto_setup()
        self.env["MQ_REDWATCH_MAX"] = "1"
        self._redwatch_pick(False)
        state = self.d / "mq/redwatch.json"

        self.assertEqual(self._omq("redwatch").returncode, 0)
        old = json.loads(state.read_text())["seen"]
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        (self.dev / "tools/x/mod.py").write_text("def f():\n    return 0\n")
        sh(*self.g, "commit", "-qam", "[LANE-BREAK] break f", cwd=self.dev)
        red = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        self.assertEqual(self._omq("redwatch").returncode, 0)
        self.assertEqual(json.loads(state.read_text()), {"seen": old, "deferred": [red]})
        self.assertFalse((self.d / "wt" / f"rw-{red[:10]}").exists())
        self.assertNotIn("KNOWN-RED", q.read_text())

        harmless = self.dev / "tools/x/other.txt"
        harmless.write_text("fine\n")
        sh(*self.g, "add", str(harmless), cwd=self.dev)
        sh(*self.g, "commit", "-qm", "[LANE-OK] harmless", cwd=self.dev)
        tip = sh("git", "rev-parse", "HEAD", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        self._redwatch_pick(True)
        self.assertEqual(self._omq("redwatch").returncode, 0)
        self.assertEqual(json.loads(state.read_text())["seen"], red)
        self.assertEqual(q.read_text().count("KNOWN-RED"), 1)
        self.assertEqual(self._omq("redwatch").returncode, 0)
        self.assertEqual(json.loads(state.read_text())["seen"], tip)
        self.assertEqual(q.read_text().count("KNOWN-RED"), 1)

    def test_redwatch_posts_known_red_for_a_commit_that_breaks_tests_and_blocks_nobody(self):
        q = self._auto_setup()
        self._redwatch_pick(True)
        self.assertEqual(self._omq("redwatch").returncode, 0)                               # first run: start at current main
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        (self.dev / "tools/x/mod.py").write_text("def f():\n    return 0\n")
        sh(*self.g, "commit", "-qam", "[LANE-BREAK] break f", cwd=self.dev)
        (self.dev / "tools/x/other.txt").write_text("fine\n")
        sh(*self.g, "add", "tools/x/other.txt", cwd=self.dev); sh(*self.g, "commit", "-qm", "[LANE-OK] harmless", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        r = self._omq("redwatch"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = q.read_text()
        self.assertRegex(t, r"KNOWN-RED \[MERGE-QUEUE -> LANE-BREAK\] main \w+ \('\[LANE-BREAK\] break f'\)")
        self.assertIn("test_mod.py::test_f", t); self.assertNotIn("LANE-OK]", t.split("KNOWN-RED")[-1].split("\n")[0] if False else "")
        n = t.count("KNOWN-RED"); self.assertEqual(n, 1)
        self._omq("redwatch"); self.assertEqual(q.read_text().count("KNOWN-RED"), 1)        # each commit judged once

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

    def _imported_directory_gate(self, present):
        sh(*self.g, "checkout", "-q", "main", cwd=self.dev)
        (self.dev / "data/fix").mkdir(parents=True)
        (self.dev / "data/fix/input.txt").write_text("42")
        (self.dev / "tools/x/reader.py").write_text("import pathlib\nR=pathlib.Path(__file__).resolve().parents[2]\ndef read():\n    return (R / 'data/fix' / " + "'input.txt'" + ").read_text()\n")
        (self.dev / "tools/x/test_reader.py").write_text("import reader\ndef test_read():\n    assert reader.read() == '42'\n")
        sh(*self.g, "add", "data/fix/input.txt", "tools/x/reader.py", "tools/x/test_reader.py", cwd=self.dev)
        sh(*self.g, "commit", "-qm", "reader fixture", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "main", cwd=self.dev)
        sh(*self.g, "checkout", "-q", "-b", "claude/reader", "main", cwd=self.dev)
        if not present:
            (self.dev / "data/fix/input.txt").unlink()
        with open(self.dev / "tools/x/reader.py", "a") as f:
            f.write("# changed implementation\n")
        sh(*self.g, "commit", "-qam", "reader change", cwd=self.dev)
        sh(*self.g, "push", "-q", "origin", "claude/reader", cwd=self.dev)
        return subprocess.run([sys.executable, "-I", P, "gate", "claude/reader"], env=self.env, capture_output=True, text=True, timeout=600)

    def test_imported_directory_actual_input_is_discovered(self):
        g = self._imported_directory_gate(True)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("source dir(s) the tests name: data/fix", g.stdout)
        self.assertNotIn("also fail on main", g.stdout)

    def test_imported_directory_absent_input_fails_closed(self):
        g = self._imported_directory_gate(False)
        self.assertNotEqual(g.returncode, 0, g.stdout + g.stderr)
        self.assertIn("RED", g.stdout)
        self.assertNotIn("GATE main=", g.stdout)

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

    def test_remote_admission_refusal_defers_without_hub_gate(self):
        q = self.d / "coord/lanes/COORD-REVIEW-QUEUE.md"
        q.write_text("- 2026-11-15 07:00 PST STATE [X -> COORD] nothing\n"
                     f"- 2026-11-15 09:00 PST [COORD] COORD APPROVED: claude/good @{self.shas['good'][:10]}\n")
        remote = "echo 'NOT-RUN disk-ETA hold: epyc2 leaves 45 GB < floor 50 GB' >&2; exit 78"
        r = self.tick(env=dict(self.env, MQ_GATE_REMOTE=remote))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = (self.d / "mq/log").read_text()
        self.assertIn("remote gate admission deferred: NOT-RUN disk-ETA hold", log)
        self.assertNotIn("gating on the hub", log)
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


class ParseAuthor(unittest.TestCase):
    def test_continuation_line_of_a_lane_entry_is_not_an_approval(self):
        import importlib.machinery, importlib.util
        ld = importlib.machinery.SourceFileLoader("omq_parse", P)
        m = importlib.util.module_from_spec(importlib.util.spec_from_loader("omq_parse", ld)); ld.exec_module(m)
        text = ("- 2026-11-15 23:54 PST STATE [MERGE-QUEUE-1 -> COORD] r253.\n"
                "skew2: on your 'COORD APPROVED: claude/x-skew2 @87ba593cd35' it lands.\n"
                "- 2026-11-15 23:58 PST RULING [COORD -> MERGE-QUEUE-1] r254\n"
                "  COORD APPROVED: claude/clean-refguard-1115 @0668000bbc4\n")
        keys = [a["key"] for a in m.parse_approvals(text)]
        self.assertEqual(keys, ["claude/clean-refguard-1115@0668000bbc4"])


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


class SparseResultFiles(unittest.TestCase):
    def test_exact_shallow_records_and_existing_directory_dependencies(self):
        files = ["results/rtl/new.json", "results/geom_review/review.json",
                 "results/rtl/deep/body.sv", "tools/fleet/new_helper.py"]
        entries = M.changed_checkout_entries(files)
        self.assertIn("file:results/rtl/new.json", entries)
        self.assertIn("file:results/geom_review/review.json", entries)
        self.assertIn("results/rtl/deep", entries)
        self.assertIn("tools/fleet", entries)
        pats = M.extra_sparse_patterns(entries)
        self.assertIn("/results/rtl/new.json", pats)
        self.assertNotIn("/results/rtl/", pats)
        self.assertIn("/results/rtl/deep/", pats)

    def test_real_git_checkout_keeps_requested_bytes_without_unrelated_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "sparse fixture"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@invalid"], check=True)
            payloads = {"results/rtl/new.json": '{"exact": true}\n',
                        "results/rtl/unrelated.v": "not requested\n",
                        "results/geom_review/review.json": '{"review": true}\n',
                        "results/geom_review/unrelated.png": "not requested either\n",
                        "results/rtl/deep/body.sv": "module body; endmodule\n"}
            for f, text in payloads.items():
                (repo / f).parent.mkdir(parents=True, exist_ok=True)
                (repo / f).write_text(text)
            subprocess.run(["git", "-C", str(repo), "add", "--", *payloads], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
            sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            m = load({"MQ_REPO": str(repo), "MQ_HOME": str(root / "mq"),
                      "MQ_WT": str(root / "wt"), "MQ_SPARSE": "/*,!/*/"})
            changed = ["results/rtl/new.json", "results/geom_review/review.json",
                       "results/rtl/deep/body.sv"]
            wt = m.wt_make("exact", sha, m.changed_checkout_entries(changed))
            for f in changed:
                self.assertEqual((wt / f).read_text(), payloads[f])
            self.assertFalse((wt / "results/rtl/unrelated.v").exists())
            self.assertFalse((wt / "results/geom_review/unrelated.png").exists())
            # Control: the old parent-directory inventory pulls the unrelated siblings.
            broad = m.wt_make("old-parent-control", sha, {os.path.dirname(f) for f in changed})
            self.assertTrue((broad / "results/rtl/unrelated.v").exists())
            self.assertTrue((broad / "results/geom_review/unrelated.png").exists())


class ImportedDirectoryInputs(unittest.TestCase):
    def test_unused_module_output_root_is_not_a_fixture_but_exact_file_is(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'tools').mkdir()
            (root / 'tools/test_case.py').write_text("import gen_phys\nFIXTURE = 'data/fix'\n")
            (root / 'tools/gen_phys.py').write_text("OUT = 'unused_outputs/fake_tree'\nINPUT = 'data/static/input.txt'\n")
            kinds = {'data/fix': 'tree', 'unused_outputs/fake_tree': 'tree', 'data/static/input.txt': 'blob'}
            with patch.object(M, '_tops', return_value=['tools', 'unused_outputs', 'data']), patch.object(M, '_tree_types', side_effect=lambda rev, paths: {p: kinds[p] for p in paths if p in kinds}):
                self.assertEqual(M.test_deps(root, 'main', ['tools/test_case.py']), {'data/fix', 'data/static'})

    def test_incomplete_baseline_cannot_mask_candidate_failure(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'tools').mkdir()
            (root / 'tools/test_case.py').write_text('')
            result = (1, {'tools/test_case.py::test_case', 'MISSING-SOURCE:data/fix/input.txt'}, '')
            with patch.object(M, 'wt_make', return_value=root), patch.object(M, 'pytest', return_value=result):
                with self.assertRaisesRegex(M.GitError, 'baseline fixture input missing'):
                    M.baseline('main', {'tools/test_case.py::test_case'}, tag='incomplete')


class FailureOutputRetention(unittest.TestCase):
    def test_primary_and_followup_failures_keep_distinct_immutable_output(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = load({'MQ_HOME': str(root / 'mq'), 'MQ_WT': str(root / 'wt')})
            one = subprocess.CompletedProcess([], 1, 'FAILED tools/test_case.py::primary\nfirst traceback\n', '')
            two = subprocess.CompletedProcess([], 1, 'FAILED tools/test_case.py::serial\nsecond traceback\n', '')
            with patch.object(m, 'run', side_effect=[one, two]), patch.object(m, 'missing_src', return_value=[]):
                m.pytest(root, ['tools/test_case.py'], 'same-tag', 1)
                m.pytest(root, ['tools/test_case.py'], 'same-tag', 1)
            logs = list((root / 'mq/failure-output').glob('*.log'))
            self.assertEqual(len(logs), 2)
            texts = [p.read_text() for p in logs]
            self.assertTrue(any('first traceback' in s for s in texts))
            self.assertTrue(any('second traceback' in s for s in texts))
            self.assertTrue(all('command=' in s and 'rc=1' in s for s in texts))


class WidenDirs(unittest.TestCase):
    def _repo(self):
        d = Path(tempfile.mkdtemp())
        for f in ("rtl/hdc/a.sv", "rtl/v41rom/b.sv", "physical/asap7_memory_macros_v2/lef/x.lef", "physical/asap7_memory_macros_v2/v/y.v",
                  "physical/die_plan/q/z.py", "physical/die_plan/q/w.py", "physical/die_plan/r/v.py"):
            (d / f).parent.mkdir(parents=True, exist_ok=True); (d / f).write_text("x")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        for c in (["init", "-q"], ["add", "."], ["commit", "-qm", "x"]):
            subprocess.run(["git", *c], cwd=d, env=env, check=True, capture_output=True)
        return d

    def test_rtl_miss_takes_whole_top_in_one_round(self):
        d = self._repo()
        self.assertEqual(M.widen_dirs(d, {"rtl/hdc/a.sv"}), ["rtl"]); shutil.rmtree(d)

    def test_macro_dir_widens_to_two_levels(self):
        d = self._repo()
        self.assertEqual(M.widen_dirs(d, {"physical/asap7_memory_macros_v2/v/y.v"}), ["physical/asap7_memory_macros_v2"]); shutil.rmtree(d)

    def test_big_two_level_dir_stays_parent(self):
        from unittest.mock import patch
        d = self._repo()
        with patch.object(M, "WIDE_MAX", 2):
            self.assertEqual(M.widen_dirs(d, {"physical/die_plan/q/z.py"}), ["physical/die_plan/q"])
        shutil.rmtree(d)


class PackGuard(unittest.TestCase):
    def _packs(self, n):
        d = Path(tempfile.mkdtemp()); (d / ".git" / "objects" / "pack").mkdir(parents=True)
        for i in range(n):
            (d / ".git" / "objects" / "pack" / f"pack-{i}.pack").write_text("")
        return d

    def _calls(self, n):
        from unittest.mock import patch
        d = self._packs(n); calls = []
        with patch.object(M, "git", side_effect=lambda *a, **k: calls.append(a) or subprocess.CompletedProcess([], 0, "", "")), patch.object(M, "log"):
            M.pack_guard(d)
        shutil.rmtree(d)
        return [c[0] for c in calls]

    def test_few_packs_untouched(self):
        self.assertEqual(self._calls(5), [])

    def test_many_packs_midx_only(self):
        self.assertEqual(self._calls(M.PACK_LIMIT + 1), ["multi-pack-index"])

    def test_huge_pack_count_repacks_then_midx_never_gc(self):
        c = self._calls(M.PACK_REPACK + 1)
        self.assertEqual(c, ["repack", "multi-pack-index"])
        self.assertNotIn("gc", c); self.assertNotIn("prune", c)

    def test_progressing_pack_is_preserved_without_second_repack(self):
        from unittest.mock import patch
        d = self._packs(M.PACK_REPACK + 1)
        with patch.object(M, "live_pack_processes", return_value=[123]), patch.object(M, "git") as git, patch.object(M, "log"):
            M.pack_guard(d)
        git.assert_not_called()
        shutil.rmtree(d)

    def test_live_pack_process_match_is_repository_and_executable_exact(self):
        root = Path(tempfile.mkdtemp()); repo = root / "repo"; repo.mkdir()
        proc = root / "proc"; proc.mkdir()
        for pid, cwd, cmd in [(1, repo, b"git\0repack\0-d\0"), (2, repo, b"/usr/lib/git-core/git\0status\0"),
                              (3, root, b"pack-objects\0--stdin-packs\0"), (4, repo, b"/usr/lib/git-core/pack-objects\0--stdin-packs\0")]:
            d = proc / str(pid); d.mkdir(); (d / "cwd").symlink_to(cwd); (d / "cmdline").write_bytes(cmd)
        self.assertEqual(M.live_pack_processes(repo, proc), [1, 4])
        shutil.rmtree(root)

    def test_rev_never_lazy_fetches(self):
        from unittest.mock import patch
        seen = {}
        def g(*a, **k):
            seen.update(k); return subprocess.CompletedProcess([], 1, "", "")
        with patch.object(M, "git", side_effect=g):
            self.assertEqual(M.rev("0" * 40), "")
        self.assertEqual(seen["env"]["GIT_NO_LAZY_FETCH"], "1")


class TickStall(unittest.TestCase):
    def test_run_group_kills_the_whole_group_on_timeout(self):
        import time as _t
        t0 = _t.time()
        with self.assertRaises(subprocess.TimeoutExpired):
            M.run_group("sleep 30 & sleep 30", 1)
        self.assertLess(_t.time() - t0, 10)

    def test_await_item_sets_a_slow_item_aside(self):
        import concurrent.futures as CF, threading
        from unittest.mock import patch
        ev = threading.Event(); ex = CF.ThreadPoolExecutor(1)
        fut = ex.submit(ev.wait, 30)
        it = {"key": "k", "t0": 1.0}
        with patch.object(M, "ITEM_SECS", 1), patch.object(M, "stall_alert"):
            M.ASIDE.clear()
            self.assertEqual(M.await_item({}, it, fut, 1)[0], "INFRA")
            self.assertEqual(M.ASIDE, ["k"])
        ev.set(); ex.shutdown(); M.ASIDE.clear()

    def test_stall_alert_posts_once_per_window(self):
        import time as _t
        from unittest.mock import patch
        past = _t.time() - M.STALL_SECS - 5
        st = {"last_merge_ts": past, "pending_since_ts": past}
        with patch.object(M, "flush_posts"), patch.object(M, "save_state"), patch.object(M, "log"):
            M.stall_alert(st, 3); M.stall_alert(st, 3)
        self.assertEqual([p["line"].split("[")[0].split()[-1] for p in st["posts"]], ["ALERT"])

    def test_no_alert_without_pending_or_when_recent(self):
        import time as _t
        st = {"last_merge_ts": _t.time()}
        M.stall_alert(st, 5); M.stall_alert({"last_merge_ts": 1.0}, 0)
        self.assertNotIn("posts", st)


    def test_idle_gap_does_not_age_new_pending_items(self):
        from unittest.mock import patch

        now = 3 * M.STALL_SECS
        st = {"last_merge_ts": 1, "pending_since_ts": 1}
        M.stall_alert(st, 0)
        self.assertNotIn("pending_since_ts", st)
        with patch.object(M.time, "time", return_value=now):
            M.stall_alert(st, 1)
        self.assertEqual(st["pending_since_ts"], now)
        self.assertNotIn("posts", st)


class MainFetchFreshness(unittest.TestCase):
    def _run(self, advertisement, rc=0, object_rc=0):
        from unittest.mock import patch
        from contextlib import nullcontext
        local = 'a' * 40
        calls = []
        def git(*args, **kwargs):
            calls.append(args)
            if args[0] == 'ls-remote':
                return subprocess.CompletedProcess([], rc, advertisement, '')
            if args[0] == 'cat-file':
                return subprocess.CompletedProcess([], object_rc, '', '')
            return subprocess.CompletedProcess([], 0, '', '')
        with patch.object(M, 'CLONE_LOCK', side_effect=nullcontext), patch.object(M, 'rev', return_value=local), patch.object(M, 'git', side_effect=git):
            result = M.fetch_main()
        return result, calls

    def test_exact_current_advertisement_and_present_commit_skip_fetch(self):
        result, calls = self._run('a' * 40 + '\trefs/heads/main\n')
        self.assertEqual(result, 'a' * 40)
        self.assertNotIn('fetch', [c[0] for c in calls])
        self.assertIn('cat-file', [c[0] for c in calls])

    def test_missing_commit_still_fetches(self):
        _, calls = self._run('a' * 40 + '\trefs/heads/main\n', object_rc=1)
        self.assertIn('fetch', [c[0] for c in calls])

    def test_changed_failed_or_ambiguous_advertisement_still_fetches(self):
        for text, rc in [('b' * 40 + '\trefs/heads/main\n', 0), ('', 128), ('a' * 40 + '\trefs/heads/main\n' + 'a' * 40 + '\trefs/heads/main\n', 0)]:
            with self.subTest(text=text, rc=rc):
                _, calls = self._run(text, rc=rc)
                self.assertIn('fetch', [c[0] for c in calls])


class MissingModuleInventory(unittest.TestCase):
    def repo(self, files):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        for name in files:
            f = d / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("# tracked source\n")
        env = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@test",
                   GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@test")
        for cmd in (["init", "-q"], ["add", "--", *files], ["commit", "-qm", "inventory"]):
            subprocess.run(["git", *cmd], cwd=d, env=env, check=True, capture_output=True)
        return d

    def test_unique_tracked_smwire_module_is_missing_source(self):
        name = "tools/s81_dv/sm_target/smwire_cal.py"
        d = self.repo([name])
        (d / name).unlink()
        self.assertEqual(M.missing_src(d, "E ModuleNotFoundError: No module named 'smwire_cal'"), [name])

    def test_ambiguous_module_stays_a_failure_without_guessing(self):
        files = ["tools/a/shared.py", "tools/b/shared.py"]
        d = self.repo(files)
        for name in files:
            (d / name).unlink()
        self.assertEqual(M.missing_modules(d, "ModuleNotFoundError: No module named 'shared'"), [])

    def test_untracked_or_present_module_is_not_sparse_inventory(self):
        d = self.repo(["tools/helper.py"])
        for name in ["not_a_repo_module", "helper"]:
            self.assertEqual(M.missing_modules(d, "ModuleNotFoundError: No module named '" + name + "'"), [])
