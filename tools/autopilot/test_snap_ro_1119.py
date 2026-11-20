"""SNAP-RO-1119 (FABLE-FLOW-2155 classes 1 and 3): a manifest and its tree come from one tracked list; snapshots are read-only; the apply proves the tree on every gen host;
a snapshot that fails src_manifest opens ONE die-level breaker instead of blocking rows one by one."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_reviewed_tree_marker as A  # noqa: E402
import kit_wave as KW  # noqa: E402
import live_tree as LT  # noqa: E402
import src_manifest as SM  # noqa: E402
from test_live_tree import make_published, make_pack, chmod_all_w, sha  # noqa: E402


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True, capture_output=True, text=True).stdout.strip()


class Tmp(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        SM.CACHE_DIR = self.t + "/cache"
        self.addCleanup(self._rm)

    def _rm(self):
        chmod_all_w(self.t)
        shutil.rmtree(self.t, ignore_errors=True)


class Manifest(Tmp):
    def test_listed_but_skipped_name_is_checked_where_it_is(self):
        """n46_s1: a pack listed tools/x.py.orig; the walk skips *.orig, so every host said 'missing' for a file that was there"""
        root = self.t + "/tree"
        make_published(root, {"tools/x.py": b"X", "tools/x.py.orig": b"OLD"})
        m = json.load(open(root + "/" + SM.MANIFEST))
        self.assertIn("tools/x.py.orig", m["files"])
        errs, _ = SM.verify(root, ro=True, full=True)
        self.assertEqual(errs, [])
        rc, txt = 0, ""
        for dp, dn, fn in os.walk(root):
            os.chmod(dp, 0o755)
        os.chmod(root + "/tools/x.py.orig", 0o644)
        open(root + "/tools/x.py.orig", "wb").write(b"CHANGED")
        errs, _ = SM.verify(root, full=True)
        self.assertTrue(any("tools/x.py.orig (modified" in e for e in errs), errs)
        os.unlink(root + "/tools/x.py.orig")
        errs, _ = SM.verify(root, full=True)
        self.assertTrue(any("tools/x.py.orig (missing" in e for e in errs), errs)

    def test_build_lists_only_tracked_content_and_delta_never_lists_a_skipped_name(self):
        repo = self.t + "/repo"
        os.makedirs(repo + "/tools")
        git(repo, "init", "-q")
        for f, c in (("tools/a.py", "A=1\n"), ("tools/a.py.orig", "A=0\n"), ("tools/b.py.bak-1", "b\n")):
            open(os.path.join(repo, f), "w").write(c)
        git(repo, "add", "-f", "tools")
        git(repo, "commit", "-qm", "m")
        sha1 = git(repo, "rev-parse", "HEAD")
        out = self.t + "/t1"
        m = SM.build(repo, sha1, None, ["tools"], out, main_ref="")
        self.assertEqual(sorted(m["files"]), ["tools/a.py"])
        self.assertFalse(os.path.exists(out + "/tools/a.py.orig"))                     # not written either: the copy and the manifest are one list
        self.assertEqual(SM.verify(out, full=True)[0], [])
        open(repo + "/tools/a.py.orig", "w").write("A=-1\n")
        open(repo + "/tools/a.py", "w").write("A=2\n")
        git(repo, "add", "-f", "tools")
        git(repo, "commit", "-qm", "m2")
        pack = self.t + "/pack"
        SM.delta_make(repo, out, git(repo, "rev-parse", "HEAD"), pack)
        d = json.load(open(pack + "/delta.json"))
        self.assertEqual(sorted(d["add"]), ["tools/a.py"])

    def test_untracked_file_cannot_enter_a_build(self):
        repo = self.t + "/repo"
        os.makedirs(repo + "/tools")
        git(repo, "init", "-q")
        open(repo + "/tools/a.py", "w").write("A\n")
        git(repo, "add", "tools")
        git(repo, "commit", "-qm", "m")
        out = self.t + "/t1"
        m = SM.build(repo, git(repo, "rev-parse", "HEAD"), None, ["tools"], out, main_ref="")
        self.assertEqual(sorted(m["files"]), ["tools/a.py"])


class Snapshot(Tmp):
    def test_snapshot_is_read_only_and_a_pack_cannot_list_a_skipped_name(self):
        pub = self.t + "/src_x_r1"
        h0 = make_published(pub, {"tools/a.py": b"A1"})
        live, snaps = LT.live_path("d", self.t), LT.snap_root("d", self.t)
        LT.host_seed(pub, live)
        os.chmod(live + "/tools/a.py", 0o644)                                          # a writable live file would reach every snapshot
        pk = self.t + "/pk"
        make_pack(pk, h0, {"tools/a.py": b"A2", "tools/a.py.orig": b"PATCH-BACKUP"})
        LT.host_apply(live, pk, snaps, "s1")
        s1 = snaps + "/s1"
        self.assertEqual(LT.writable_names(s1), [])
        m = json.load(open(s1 + "/" + SM.MANIFEST))
        self.assertNotIn("tools/a.py.orig", m["files"])
        self.assertEqual(SM.verify(s1, expect=m["manifest_hash"], ro=True, full=True)[0], [])
        with self.assertRaises(PermissionError):
            open(s1 + "/tools/a.py", "wb")
        with self.assertRaises(PermissionError):
            os.rename(s1 + "/tools/a.py", s1 + "/tools/a.py.SNAP-DISABLED")            # the n46_s0 rename

    def test_writable_names_finds_a_writable_file_and_dir(self):
        d = self.t + "/s"
        os.makedirs(d + "/sub")
        open(d + "/sub/f", "w").write("x")
        self.assertEqual(sorted(LT.writable_names(d)), sorted([d, d + "/sub", d + "/sub/f"]))


class IncrementalVerify(Tmp):
    """COORD 11-20: a new snapshot version derived from a verified parent hashes only its changed files"""

    def _chain(self):
        pub = self.t + "/src_x_r1"
        h0 = make_published(pub, {"tools/a.py": b"A1", "tools/b.py": b"B1", "physical/plan.json": b"P1"})
        live, snaps = LT.live_path("d", self.t), LT.snap_root("d", self.t)
        LT.host_seed(pub, live)
        LT.host_apply(live, "", snaps, "s2")
        self.assertEqual(SM.verify(snaps + "/s2", expect=h0, ro=True, full=True)[0], [])     # the parent's completed verification (writes its receipt)
        pk = self.t + "/pk"
        make_pack(pk, h0, {"tools/b.py": b"B2"})
        LT.host_apply(live, pk, snaps, "s2_p1")
        return snaps, live

    def test_only_changed_files_are_hashed_and_the_rest_is_inherited(self):
        snaps, live = self._chain()
        s3 = snaps + "/s2_p1"
        dl = json.load(open(s3 + "/.snap-delta"))
        self.assertEqual(dl["changed"], ["tools/b.py"])
        hashed = []
        orig = SM.tree_hash
        SM.tree_hash = lambda p: (hashed.append(os.path.basename(p)), orig(p))[1]
        self.addCleanup(setattr, SM, "tree_hash", orig)
        m3 = json.load(open(s3 + "/" + SM.MANIFEST))
        errs, info = SM.verify(s3, expect=m3["manifest_hash"], ro=True, full=True)
        self.assertEqual(errs, [])
        self.assertEqual(hashed, ["b.py"])
        self.assertEqual(info.get("inherited_from"), snaps + "/s2")

    def test_a_replaced_unchanged_file_is_not_inherited(self):
        snaps, live = self._chain()
        s3 = snaps + "/s2_p1"
        for dp, dn, fn in os.walk(s3):
            os.chmod(dp, 0o755)
        os.unlink(s3 + "/tools/a.py")                                            # same bytes would pass, different bytes must not
        open(s3 + "/tools/a.py", "wb").write(b"EVIL")
        os.chmod(s3 + "/tools/a.py", 0o444)
        m3 = json.load(open(s3 + "/" + SM.MANIFEST))
        errs, _ = SM.verify(s3, expect=m3["manifest_hash"], full=True)
        self.assertTrue(any("tools/a.py (modified" in e for e in errs), errs)

    def test_no_verified_parent_means_a_full_verify(self):
        snaps, live = self._chain()
        s3 = snaps + "/s2_p1"
        for f in os.listdir(SM.CACHE_DIR):
            os.unlink(os.path.join(SM.CACHE_DIR, f))                              # the parent has no receipt
        hashed = []
        orig = SM.tree_hash
        SM.tree_hash = lambda p: (hashed.append(os.path.basename(p)), orig(p))[1]
        self.addCleanup(setattr, SM, "tree_hash", orig)
        m3 = json.load(open(s3 + "/" + SM.MANIFEST))
        errs, info = SM.verify(s3, expect=m3["manifest_hash"], ro=True, full=True)
        self.assertEqual(errs, [])
        self.assertEqual(sorted(hashed), ["a.py", "b.py", "plan.json"])
        self.assertNotIn("inherited_from", info)


class ApplyHosts(Tmp):
    def test_findings_refuse_unreachable_only_warns_ok_passes(self):
        def run(cmd):
            if "--hosts bad " in cmd:
                return 1, "bad: SRC_MANIFEST DRIFT tools/x (missing)"
            if "--hosts down " in cmd:
                return 255, "ssh: connect timed out"
            return 0, "ok"
        bad, unreach = A.verify_tree_on_all_hosts("/t", "h" * 64, ["good", "bad", "down"], "/rt", run=run)
        self.assertEqual(sorted(bad), ["bad"])
        self.assertEqual(sorted(unreach), ["down"])
        self.assertEqual(A.verify_tree_on_all_hosts("/t", "h", ["good"], "/rt", run=run), ({}, {}))

    def test_cached_receipt_miss_falls_back_to_the_full_verify(self):
        seen = []

        def run(cmd):
            seen.append("--cached-receipts" in cmd)
            return (1, "SRC_MANIFEST CACHE MISS") if "--cached-receipts" in cmd else (0, "ok")
        self.assertEqual(A.verify_tree_on_all_hosts("/t", "h", ["g"], "/rt", run=run), ({}, {}))
        self.assertEqual(seen, [True, False])

    def test_bind_output_missing_on_a_host_is_a_finding(self):
        def run(cmd):
            return (1, "") if "bind_report.json" in cmd else (0, "ok")
        bad, _ = A.verify_tree_on_all_hosts("/t", "h", ["g"], "/rt", run=run, bind_out="/b/out")
        self.assertIn("g", bad)

    def test_apply_marker_refuses_before_any_switch(self):
        from test_apply_reviewed_tree_marker import mk, cand, TC, PGOK
        c = mk()
        before = (c / "autopilot/kit_wave.json").read_text()
        with self.assertRaises(SystemExit) as cm:
            A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC, PG=PGOK, host_verify=lambda *a, **k: ({"epyc10": "SRC_MANIFEST DRIFT tools/x (missing)"}, {}))
        self.assertIn("APPLY REFUSED", str(cm.exception))
        self.assertEqual((c / "autopilot/kit_wave.json").read_text(), before)


class AdoptBind(Tmp):
    def _run_factory(self, fail_host=None, calls=None):
        from test_publish_apply import _R

        def run(argv, **k):
            calls.append(argv)
            if argv[0] == "ssh" and "bash -s" in argv[-1]:
                return _R(0, "ADOPT_SEAL /t/tree_bind_0101\n")
            if argv[0] == "ssh" and argv[1] == "-n" and argv[5 if False else -2] == fail_host:
                return _R(1)
            return _R(0)
        return run

    def test_post_bind_copy_travels_with_the_bind_is_proved_on_every_host_and_registered(self):
        import argparse
        import publish_apply as PA
        from test_publish_apply import _adopt_cfg
        C, cfg = _adopt_cfg(Path(self.t))
        calls = []
        a = argparse.Namespace(die="s81", lane="L", tree="/t/tree", copy="/t/tree_postbind_0101", host="epyc8", id="u1", stamp="0101", coord=str(C))
        rc = PA.cmd_adopt_bind(a, run=self._run_factory(calls=calls), check_fn=lambda *x, **y: (True, "ok"))
        self.assertEqual(rc, 0)
        rs = [c[-1] for c in calls if c[0] == "ssh" and "rsync" in c[-1]]
        self.assertTrue(all("/t/tree_postbind_0101/_postbind/out/" in r and "/t/tree_bind_0101/" in r for r in rs) and len(rs) == 2)
        proofs = [c[-2] for c in calls if c[0] == "ssh" and c[1] == "-n" and "native_topology.json" in c[-1]]
        self.assertEqual(sorted(proofs), ["epyc10", "epyc8", "intel1"])                      # every gen host, the bind host included
        edit = [c for c in calls if any("kit_wave_edit.py" in str(x) for x in c)][0]
        patch = json.load(open(edit[edit.index("--patch-file") + 1])) if os.path.exists(edit[edit.index("--patch-file") + 1]) else None
        if patch is not None:
            self.assertIn({"op": "add", "path": "/dies/s81/bind_copy_of_record", "value": ["/t/tree_postbind_0101"]}, patch)

    def test_a_host_without_the_copy_refuses_the_adopt(self):
        import argparse
        import publish_apply as PA
        from test_publish_apply import _adopt_cfg
        C, cfg = _adopt_cfg(Path(self.t))
        calls = []
        a = argparse.Namespace(die="s81", lane="L", tree="/t/tree", copy="/t/tree_postbind_0101", host="epyc8", id="u1", stamp="0101", coord=str(C))
        rc = PA.cmd_adopt_bind(a, run=self._run_factory(fail_host="intel1", calls=calls), check_fn=lambda *x, **y: (True, "ok"))
        self.assertEqual(rc, 2)
        self.assertFalse(any(any("kit_wave_edit.py" in str(x) for x in c) for c in calls))

    def test_registered_copy_is_on_the_delete_guards_protected_list(self):
        sys.path.insert(0, str(HERE.parent / "fleet"))
        import ot_delete_guard as G
        c = Path(self.t) / "coord"
        (c / "autopilot").mkdir(parents=True)
        cp = "/srv/opentallas-scratch2/claude/kw45/src_kv_x_postbind_1119"
        (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"kv": {"bind_copy_of_record": [cp]}}}))
        self.assertIn(cp, G.build_protected(str(c)))


class Breaker(unittest.TestCase):
    CFG = {"dies": {"qc": {"src": "/k/snap/n46_s1", "gen_host": "epyc9", "src_manifest_hash": "h"}}}
    WHY = "SRC_MANIFEST FAIL /k/snap/n46_s1: tree is not main abc + its overlay manifest (1 finding(s); first: SRC_MANIFEST DRIFT x (missing))"

    class AP:
        lines = []
        def log(self, s): self.lines.append(s)

    def test_three_failures_open_one_breaker_two_do_not(self):
        st = {}
        self.assertEqual(KW.src_breaker_note(st, "qc", self.WHY, now=1000), "")
        self.assertEqual(KW.src_breaker_note(st, "qc", self.WHY, now=1010), "")
        self.assertEqual(KW.src_breaker_note(st, "qc", self.WHY, now=1020), "qc|/k/snap/n46_s1")
        self.assertEqual(KW.src_breaker_note(st, "qc", self.WHY, now=1030), "")            # already open: no second line
        st2 = {}
        for t in (0, 1000, 2000):                                                            # spread over more than a tick: no breaker
            self.assertEqual(KW.src_breaker_note(st2, "qc", self.WHY, now=t), "")

    def test_gate_stops_the_die_until_the_snapshot_verifies_then_closes(self):
        st, ap, skip = {}, self.AP(), {}
        for t in (1, 2, 3):
            KW.src_breaker_note(st, "qc", self.WHY, now=t)
        go = [{"item": f"r{i}"} for i in range(17)]
        bad = lambda d, sp: (1, "SRC_MANIFEST DRIFT x (missing)", "epyc9")
        st["src_breaker"]["qc|/k/snap/n46_s1"]["probe"] = 5                                  # a probe just went: nothing launches
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, skip, verify_fn=bad, now=10), [])
        self.assertEqual(sum(len(v) for v in skip.values()), 17)
        skip2 = {}                                                                           # half-open: ONE row goes after the probe interval, 16 wait
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, skip2, verify_fn=bad, now=700), go[:1])
        self.assertEqual(sum(len(v) for v in skip2.values()), 16)
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, {}, verify_fn=bad, now=850), [])   # next probe only after SRC_BREAKER_PROBE_S
        none = lambda d, sp: (None, "", "epyc9")                                             # no answer: stays open
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, {}, verify_fn=none, now=1000), [])
        ok = lambda d, sp: (0, "SRC_MANIFEST OK", "epyc9")
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, {}, verify_fn=ok, now=1200), go)
        self.assertEqual([l for l in ap.lines if "CLOSED" in l].__len__(), 1)
        self.assertNotIn("qc|/k/snap/n46_s1", st["src_breaker"])
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, {}, verify_fn=bad, now=1500), go)   # closed: a healthy path is never gated

    def test_a_new_snapshot_ends_the_old_breaker(self):
        st = {}
        for t in (1, 2, 3):
            KW.src_breaker_note(st, "qc", self.WHY, now=t)
        cfg = {"dies": {"qc": {"src": "/k/snap/n46_s2"}}}
        go = [{"item": "a"}]
        self.assertEqual(KW.src_breaker_gate(self.AP(), cfg, st, "qc", go, {}, verify_fn=lambda d, sp: (1, "x", "h"), now=10), go)
        self.assertEqual(st["src_breaker"], {})

    def test_verifier_is_the_newest_published_one_not_the_pinned_tree(self):
        """n46_s2: rows queued under rt/77973bd52d22 ran its old verifier; the shipped verifier is rt/current's"""
        t = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, t, True)
        for tree in ("old/tools/autopilot", "newer/tools/autopilot"):
            os.makedirs(f"{t}/rt/{tree}")
            open(f"{t}/rt/{tree}/src_manifest.py", "w").write(tree)
        os.symlink(f"{t}/rt/newer", f"{t}/rt/current")
        self.assertEqual(KW.verifier_path(f"{t}/rt/old/tools/autopilot/kit_wave.py"), Path(f"{t}/rt/current/tools/autopilot/src_manifest.py"))
        own = Path(t) / "other/tools/autopilot/kit_wave.py"                                 # not under rt/: its own copy
        self.assertEqual(KW.verifier_path(own), own)

    def test_failure_classifier(self):
        self.assertTrue(KW.is_src_manifest_fail("src_manifest", ""))
        self.assertTrue(KW.is_src_manifest_fail("", self.WHY))
        self.assertFalse(KW.is_src_manifest_fail("gen", "route overflow"))


if __name__ == "__main__":
    unittest.main()
