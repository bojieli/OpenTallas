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
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, skip, verify_fn=bad, now=10), [])
        self.assertEqual(sum(len(v) for v in skip.values()), 17)
        none = lambda d, sp: (None, "", "epyc9")                                             # no answer: stays open
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, {}, verify_fn=none, now=500), [])
        ok = lambda d, sp: (0, "SRC_MANIFEST OK", "epyc9")
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, {}, verify_fn=ok, now=700), go)
        self.assertEqual([l for l in ap.lines if "CLOSED" in l].__len__(), 1)
        self.assertNotIn("qc|/k/snap/n46_s1", st["src_breaker"])
        self.assertEqual(KW.src_breaker_gate(ap, self.CFG, st, "qc", go, {}, verify_fn=bad, now=900), go)   # closed: a healthy path is never gated

    def test_a_new_snapshot_ends_the_old_breaker(self):
        st = {}
        for t in (1, 2, 3):
            KW.src_breaker_note(st, "qc", self.WHY, now=t)
        cfg = {"dies": {"qc": {"src": "/k/snap/n46_s2"}}}
        go = [{"item": "a"}]
        self.assertEqual(KW.src_breaker_gate(self.AP(), cfg, st, "qc", go, {}, verify_fn=lambda d, sp: (1, "x", "h"), now=10), go)
        self.assertEqual(st["src_breaker"], {})

    def test_failure_classifier(self):
        self.assertTrue(KW.is_src_manifest_fail("src_manifest", ""))
        self.assertTrue(KW.is_src_manifest_fail("", self.WHY))
        self.assertFalse(KW.is_src_manifest_fail("gen", "route overflow"))


if __name__ == "__main__":
    unittest.main()
