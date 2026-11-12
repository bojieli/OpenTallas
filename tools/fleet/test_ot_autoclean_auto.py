#!/usr/bin/env python3
"""tests for ot-autoclean.py (AUTOCLEAN-7): each delete class, each skip reason, aliases, controls, the ALERT stop,
the kit-wave reduction, the wt-reaper call and the localhost archive driver (local ssh shim)."""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "ot-autoclean.py")
spec = importlib.util.spec_from_file_location("ot_autoclean_auto", SCRIPT)
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)

OLD = time.time() - 10 * 3600


def touch(p, n=4096, mtime=OLD):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b"x" * n)
    os.utime(p, (mtime, mtime))
    return p


def age_tree(d, mtime=OLD):
    for dp, dns, fns in os.walk(d):
        for n in fns + dns:
            os.utime(os.path.join(dp, n), (mtime, mtime), follow_symlinks=False)
    os.utime(d, (mtime, mtime))


class Base(unittest.TestCase):
    def setUp(self):
        self.t = os.path.realpath(tempfile.mkdtemp(prefix="acx"))
        os.environ["OT_AUTOCLEAN_OFF_FILES"] = os.path.join(self.t, "OFF")
        ac.OFF_FILES = (os.path.join(self.t, "OFF"),)
        self.root = os.path.join(self.t, "srv/scr/claude")
        os.makedirs(self.root)
        self.snap = os.path.join(self.t, "snap")
        self.state = os.path.join(self.t, "state")
        # the live tool REQUIRES rows from all three protected lists (lanes/PROTECTED-DBS.txt, PROTECTED-DBS.txt, lanes/prune/ARCHIVE-PROTECTED.tsv)
        self.prot = [(f"/srv/none/claude/l{i}/k", ("lanes/PROTECTED-DBS.txt", "PROTECTED-DBS.txt", "lanes/prune/ARCHIVE-PROTECTED.tsv")[i % 3])
                     for i in range(5)]
        self.qpaths, self.qwords = [], []
        self.kw = None
        # DESIGN_EXPORT_1112 gate (default on): these tests run with the gate file present and no current design named
        # (no holds); test_ot_autoclean_dx.py tests the gate itself
        self.dx = {"names": [], "ledger": []}
        d = os.path.join(self.t, "docker")
        os.makedirs(d)
        open(os.path.join(d, "ids"), "w").close()
        open(os.path.join(d, "mounts"), "w").close()
        with open(os.path.join(d, "fake"), "w") as f:
            f.write(f'#!/bin/sh\ncase "$1" in ps) cat {d}/ids;; inspect) cat {d}/mounts;; *) exit 1;; esac\n')
        self.docker = f"sh {d}/fake"
        self.ddir = d
        self.aliases = os.path.join(self.t, "findmnt.txt")
        # /srv/scr is the canonical bind target of <t>/home/scratch-root (like epyc5/6 scratch3)
        with open(self.aliases, "w") as f:
            f.write(f"/ /dev/sdz\n{self.t}/srv/scr /dev/sdz[{self.t}/home/scratch-root]\n")
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            p.kill()
            p.wait()
        shutil.rmtree(self.t, ignore_errors=True)

    def write_snap(self, age=0):
        os.makedirs(self.snap, exist_ok=True)
        with open(os.path.join(self.snap, "meta.json"), "w") as f:
            json.dump({"created": time.time() - age}, f)
        with open(os.path.join(self.snap, "protected.tsv"), "w") as f:
            f.write("".join(f"{p}\t{w}\n" for p, w in self.prot))
        with open(os.path.join(self.snap, "queue.json"), "w") as f:
            json.dump({"paths": self.qpaths, "words": self.qwords}, f)
        gp = os.path.join(self.snap, "design_export.json")
        if self.dx is not None:
            with open(gp, "w") as f:
                json.dump(self.dx, f)
        elif os.path.exists(gp):
            os.unlink(gp)
        kp = os.path.join(self.snap, "kitwave.json")
        if self.kw is not None:
            with open(kp, "w") as f:
                json.dump(self.kw, f)
        elif os.path.exists(kp):
            os.unlink(kp)

    def run_job(self, *extra, apply=True, snap_age=0, wt=""):
        self.write_snap(snap_age)
        argv = ["run", "--host", "hx", "--state", self.state, "--snapshot", self.snap, "--min-protected", "1",
                "--roots", self.root, "--docker", self.docker, "--aliases", self.aliases, "--wt-reaper", wt]
        argv += (["--apply"] if apply else []) + list(extra)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ac.main(argv)
        self.out = buf.getvalue()
        self.manifest = []
        for ln in self.out.splitlines():
            if ln.startswith("MANIFEST "):
                with open(ln.split(" ", 1)[1]) as fh:
                    rows = fh.read().splitlines()[1:]
                self.manifest = [r.split("\t") for r in rows]
        return rc

    def row(self, path):
        for r in self.manifest:
            if r[5] == path:
                return r
        return None

    def kit_b(self, rel, extra=()):
        k = os.path.join(self.root, rel)
        b = os.path.join(k, "run/results/asap7/d/base")
        for n in ("6_final.odb", "6_final.spef", "5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb", "5_2_route.odb",
                  "2_floorplan.odb") + tuple(extra):
            touch(os.path.join(b, n))
        touch(os.path.join(k, "run/logs/asap7/d/base/6_report.log"))
        return k, b

    def kit_c(self, rel, cts=True):
        k = os.path.join(self.root, rel)
        b = os.path.join(k, "run/results/asap7/d/base")
        names = list(ac.TRIM_C) + ["2_floorplan.odb", "3_place.odb", "4_1_cts.odb"] + (["4_cts.odb"] if cts else [])
        for n in names:
            touch(os.path.join(b, n))
        return k, b

    def spawn(self, args, cwd=None, env=None):
        p = subprocess.Popen(args, cwd=cwd, env=env)
        self.procs.append(p)
        time.sleep(0.4)
        return p


class TestClasses(Base):
    def test_b_trim_apply_and_dry(self):
        k, b = self.kit_b("lane1/kitA")
        self.assertEqual(self.run_job(apply=False), 0)
        self.assertIn("controls: positive PASS negative PASS", self.out)
        self.assertEqual(self.row(b)[3], "WOULD")
        self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))
        self.assertIn("PROTECTED/COUNTED HITS AT RECHECK: 0", self.out)
        self.assertIn("TOTAL class b WOULD: 1 rows", self.out)
        self.assertEqual(self.run_job(), 0)
        self.assertEqual(self.row(b)[3], "DELETED")
        left = sorted(os.listdir(b))
        self.assertEqual(left, ["2_floorplan.odb", "5_2_route.odb", "6_final.odb", "6_final.spef"])

    def test_b_needs_both_finals_and_age(self):
        _, b1 = self.kit_b("lane1/nospef")
        os.unlink(os.path.join(b1, "6_final.spef"))
        _, b2 = self.kit_b("lane1/smallspef")
        touch(os.path.join(b2, "6_final.spef"), n=100)
        _, b3 = self.kit_b("lane1/young")
        touch(os.path.join(b3, "6_final.odb"), mtime=time.time())
        self.run_job()
        for b in (b1, b2):
            self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))
            self.assertIsNone(self.row(b))
        self.assertTrue(self.row(b3)[4].startswith("lt6h"))
        self.assertTrue(os.path.exists(os.path.join(b3, "5_route.odb")))

    def test_c_intermediates(self):
        _, b = self.kit_c("lane2/kitC")
        _, b2 = self.kit_c("lane2/kitNoCts", cts=False)
        self.run_job()
        self.assertEqual(sorted(os.listdir(b)), ["2_floorplan.odb", "3_place.odb", "4_cts.odb"])
        self.assertEqual(sorted(os.listdir(b2)), ["2_floorplan.odb", "3_place.odb", "4_1_cts.odb"])

    def test_c_needs_3_place(self):
        _, b = self.kit_c("lane2/small")
        touch(os.path.join(b, "3_place.odb"), n=10)
        self.run_job()
        self.assertTrue(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))

    def attempt(self, item, n, event="ev1"):
        d = os.path.join(self.root, f"kw-x/kit-wave/hbm/{event}/items/{item}/attempt_{n}")
        touch(os.path.join(d, f"gen/{item}_abc/run/results/asap7/d/base/3_place.odb"))
        touch(os.path.join(d, "geom/auto_geom.json"))
        age_tree(d)
        return d

    def test_a_attempts(self):
        fin = self.attempt("item_fin", 1)
        sup = self.attempt("item_sup", 1)
        act = self.attempt("item_act", 1)
        sig = self.attempt("item_sig", 2)
        unk = self.attempt("item_unk", 1)
        kept = self.attempt("item_res", 1)
        young = self.attempt("item_yng", 1)
        touch(os.path.join(young, "new.log"), mtime=time.time())
        gitd = self.attempt("item_git", 1)
        touch(os.path.join(gitd, "src/.git"), n=10)
        signedrec = self.attempt("item_rec", 1)
        with open(os.path.join(signedrec, "signoff.json"), "w") as f:
            json.dump({"verdict": "SIGNED"}, f)
        age_tree(signedrec)
        h = "hx:"
        self.kw = {"attempts": {h + fin: {"active": False, "signed": False, "terminal": ["FAIL/None"]},
                                h + act: {"active": True, "signed": False, "terminal": []},
                                h + sig: {"active": False, "signed": True, "terminal": []},
                                h + young: {"active": False, "signed": False, "terminal": ["FAIL/None"]},
                                h + gitd: {"active": False, "signed": False, "terminal": ["FAIL/None"]},
                                h + signedrec: {"active": False, "signed": False, "terminal": ["FAIL/None"]},
                                h + kept: {"active": False, "signed": False, "terminal": ["CANCELLED/None"]}},
                   "latest": {h + os.path.dirname(sup): 3},
                   "keep": [h + os.path.join(kept, "gen/item_res_abc/run_kit.sh")]}
        self.run_job()
        self.assertFalse(os.path.exists(fin))
        self.assertFalse(os.path.exists(sup))
        self.assertEqual(self.row(sup)[3], "DELETED")
        self.assertIn("superseded", self.row(sup)[4])
        for d, why in ((act, "kit-wave active"), (sig, "kit-wave signed"), (unk, "kit-wave unknown"),
                       (kept, "kitwave-keep"), (young, "lt6h"), (gitd, "git inside"), (signedrec, "signed")):
            self.assertTrue(os.path.isdir(d), d)
            self.assertTrue(self.row(d)[4].startswith(why), (d, self.row(d)))

    def test_a_superseded_xpath_and_any_host(self):
        old = self.attempt("item_xp", 2, event="ev_old")      # older plan dir, state now runs attempt_5 elsewhere
        newer = self.attempt("item_xn", 7, event="ev_old")    # NEWER number than the state's current: keep
        other_act = self.attempt("item_oh", 1)                # active under another host name (ran_on copy)
        other_keep = self.attempt("item_ok", 1)               # keep path listed under the hub "localhost" name
        self.kw = {"attempts": {"localhost:" + other_act: {"active": True, "signed": False, "terminal": []}},
                   "latest": {},
                   "keep": ["localhost:" + os.path.join(other_keep, "gen")],
                   "current_di": {"hbm|item_xp": 5, "hbm|item_xn": 5, "hbm|item_ok": 3}}
        self.run_job()
        self.assertFalse(os.path.exists(old))
        self.assertIn("superseded-xpath", self.row(old)[4])
        self.assertTrue(os.path.isdir(newer))
        self.assertTrue(self.row(newer)[4].startswith("kit-wave unknown"), self.row(newer))
        self.assertTrue(os.path.isdir(other_act))
        self.assertTrue(self.row(other_act)[4].startswith("kit-wave active"), self.row(other_act))
        self.assertTrue(os.path.isdir(other_keep))
        self.assertTrue(self.row(other_keep)[4].startswith("kitwave-keep"), self.row(other_keep))

    def test_reduce_current_di(self):
        st = {"items": {"hbm|item_xp|s1": {"kit": "epyc4:/srv/x/kit-wave/hbm/ev_new/items/item_xp/attempt_5/gen/k",
                                             "status": "FAIL"}}}
        out = ac.reduce_kitwave(st, [])
        self.assertEqual(out["current_di"], {"hbm|item_xp": 5})

    def test_queuename_ignores_plan_dir_and_mounts(self):
        self.assertTrue(ac.generic_name("opentallas-scratch2"))
        d = self.attempt("item_pq", 1, event="event28w_c")
        self.qwords = ["event28w_c", "opentallas-scratch2"]
        self.kw = {"attempts": {"hx:" + d: {"active": False, "signed": False, "terminal": ["FAIL/None"]}},
                   "latest": {}, "keep": []}
        self.run_job()
        self.assertFalse(os.path.exists(d), self.row(d))

    def test_queuename_skip_superseded_flag(self):
        old = self.attempt("item_qsuper", 1, event="evq")
        cur = self.attempt("item_qsuper", 4, event="evq")
        self.qwords = ["item_qsuper"]
        self.kw = {"attempts": {"hx:" + cur: {"active": False, "signed": False, "terminal": ["FAIL/None"]}},
                   "latest": {"hx:" + os.path.dirname(cur): 4}, "keep": []}
        self.run_job()
        self.assertTrue(os.path.isdir(old)); self.assertTrue(os.path.isdir(cur))
        self.run_job("--queuename-skip-superseded")
        self.assertFalse(os.path.exists(old), self.row(old))
        self.assertTrue(os.path.isdir(cur))
        self.assertTrue(self.row(cur)[4].startswith("queuename"), self.row(cur))

    def test_symlinked_lane_keep_protects(self):
        # INCIDENT 11-07: state names the attempt through a lane symlink, the scan finds the real path
        real = self.attempt("item_symlinkd", 2, event="evs")
        lane_real = real.split("/kit-wave/")[0]
        link = lane_real + "-link"
        os.symlink(lane_real, link)
        alias = link + real[len(lane_real):]
        self.kw = {"attempts": {"hx:" + alias: {"active": True, "signed": False, "terminal": []}},
                   "latest": {}, "keep": ["hx:" + os.path.join(alias, "gen")],
                   "current_di": {"hbm|item_symlinkd": 5}}
        self.run_job("--queuename-skip-superseded")
        self.assertTrue(os.path.isdir(real), self.row(real))
        self.kw = {"attempts": {}, "latest": {}, "keep": ["hx:" + os.path.join(alias, "gen")],
                   "current_di": {"hbm|item_symlinkd": 5}}
        self.run_job("--queuename-skip-superseded")
        self.assertTrue(os.path.isdir(real), self.row(real))
        self.assertTrue(self.row(real)[4].startswith("kitwave-keep"), self.row(real))

    def test_independent_check_alerts_when_canon_misses(self):
        real = self.attempt("item_indepchk", 2, event="evi")
        lane_real = real.split("/kit-wave/")[0]
        link = lane_real + "-lnk"
        os.symlink(lane_real, link)
        alias = link + real[len(lane_real):]
        self.kw = {"attempts": {}, "latest": {}, "keep": ["hx:" + os.path.join(alias, "gen")],
                   "current_di": {"hbm|item_indepchk": 5}}
        orig = ac.Paths._realprefix
        ac.Paths._realprefix = lambda self_, p: p          # simulate the pre-fix canon (no symlink resolution)
        try:
            rc = self.run_job("--queuename-skip-superseded")
        finally:
            ac.Paths._realprefix = orig
        self.assertTrue(os.path.isdir(real))
        self.assertEqual(rc, 3)
        os.unlink(os.path.join(self.state, "ALERT"))

    def test_a_disabled_without_kitwave(self):
        d = self.attempt("item_x", 1)
        self.run_job()
        self.assertTrue(os.path.isdir(d))
        self.assertEqual(self.row(d)[4], "no kit-wave snapshot")


class TestSkips(Base):
    def assertSkip(self, b, why):
        r = self.row(b)
        self.assertIsNotNone(r, b)
        self.assertEqual(r[3], "SKIP", r)
        self.assertTrue(r[4].startswith(why), r)
        self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))

    def test_protected_parent_child_and_alias(self):
        k1, b1 = self.kit_b("lp/k1")
        k2, b2 = self.kit_b("lp/k2")
        k3, b3 = self.kit_b("lp/k3")
        self.prot += [(k1 + "/run/results/asap7/d/base/6_final.odb", "child row"),
                      (os.path.join(self.root, "lp"), "parent row"),
                      ]
        self.run_job()
        self.assertSkip(b1, "protected")
        self.assertSkip(b2, "protected")
        self.assertSkip(b3, "protected")

    def test_protected_alias_form_and_relative(self):
        k1, b1 = self.kit_b("la/k1")
        k2, b2 = self.kit_b("lb/k2")
        alias = k1.replace(f"{self.t}/srv/scr", f"{self.t}/home/scratch-root")
        self.prot += [(alias, "alias form")]
        rows = ac.parse_protected("intel1 scratch3/claude/x/y kit\nh\t/srv/a/claude/b\tz\n", "f")
        self.assertEqual([p for p, _ in rows], ["/srv/opentallas-scratch3/claude/x/y", "/srv/a/claude/b"])
        self.run_job()
        self.assertSkip(b1, "protected")
        self.assertEqual(self.row(b2)[3], "DELETED")

    def test_counted_by_signed_record(self):
        k, b = self.kit_b("lc/k")
        rs = os.path.join(self.root, "lc2/resign/signoff/signoff.json")
        os.makedirs(os.path.dirname(rs))
        with open(rs, "w") as f:
            json.dump({"verdict": "SIGNED", "inputs": {"odb": b + "/6_final.odb"}}, f)
        k2, b2 = self.kit_b("lc/notsigned")
        rs2 = os.path.join(self.root, "lc2/fail/signoff/signoff.json")
        os.makedirs(os.path.dirname(rs2))
        with open(rs2, "w") as f:
            json.dump({"verdict": "NOT SIGNED", "inputs": {"odb": b2 + "/6_final.odb"}}, f)
        # a lane-root citation must not block the lane's other trees
        k3, b3 = self.kit_b("lc3/k")
        rs3 = os.path.join(self.root, "lc2/r3/PROVENANCE.json")
        os.makedirs(os.path.dirname(rs3))
        with open(rs3, "w") as f:
            json.dump({"kind": "resign", "verdict": "SIGNED", "lane_dir": os.path.join(self.root, "lc3")}, f)
        self.run_job()
        self.assertSkip(b, "counted")
        self.assertEqual(self.row(b2)[3], "DELETED")
        self.assertEqual(self.row(b3)[3], "DELETED")

    def test_queue_path_and_names(self):
        k1, b1 = self.kit_b("lq/qpath")
        k2, b2 = self.kit_b("lq/specific_dirname")
        k3, b3 = self.kit_b("lq/0123456789abcdef")
        k4, b4 = self.kit_b("lq/qwen_compute")
        self.qpaths = [k1 + "/run/logs"]
        self.qwords = ["specific_dirname", "0123456789abcdef", "qwen_compute", "lq"]
        self.run_job()
        self.assertSkip(b1, "queuepath")
        self.assertSkip(b2, "queuename")
        self.assertEqual(self.row(b3)[3], "DELETED")
        self.assertEqual(self.row(b4)[3], "DELETED")

    def test_queuename_skip_trim_c_flag(self):
        # AUTOCLEAN-9 11-08: a design type name in a post blocks old class c trims of that type in every lane
        _, c1 = self.kit_c("lt/kv3_pv_v5n")
        k2, c2 = self.kit_c("lt2/kv3_pv_v5n")
        _, b3 = self.kit_b("lt3/kv3_pv_v5n")
        self.qwords = ["kv3_pv_v5n"]
        self.qpaths = [k2]
        self.run_job()
        self.assertEqual(self.row(c1)[3], "SKIP"); self.assertTrue(self.row(c1)[4].startswith("queuename"), self.row(c1))
        self.assertTrue(os.path.exists(os.path.join(c1, "3_3_place_gp.odb")))
        self.run_job("--queuename-skip-trim-c")
        self.assertEqual(self.row(c1)[3], "DELETED", self.row(c1))
        self.assertEqual(sorted(os.listdir(c1)), ["2_floorplan.odb", "3_place.odb", "4_cts.odb"])
        self.assertEqual(self.row(c2)[3], "SKIP")             # an exact queue path still protects
        self.assertTrue(self.row(c2)[4].startswith("queuepath"), self.row(c2))
        self.assertTrue(os.path.exists(os.path.join(c2, "3_3_place_gp.odb")))
        self.assertSkip(b3, "queuename")                      # class b unchanged
        self.assertTrue(os.path.exists(os.path.join(b3, "5_route.odb")))

    def test_c_resume_pending_fail_attempt(self):
        # COORD 11-08 04:4x: the kit wave resumes FAIL rows from their last valid stage; class c keeps their files
        def att(item, n, young=True):
            d = os.path.join(self.root, f"kw-r/kit-wave/hbm/ev1/items/{item}/attempt_{n}")
            k, b = self.kit_c(os.path.relpath(os.path.join(d, f"gen/{item}"), self.root))
            age_tree(d, mtime=OLD if young else time.time() - 30 * 3600)
            if young:
                touch(os.path.join(d, "gen/fail.log"), mtime=time.time() - 8 * 3600)   # attempt < 24 h, files > 6 h
            return d, b
        fail, bf = att("i_fail", 2)
        sup, bs = att("i_sup", 1)
        unk, bu = att("i_unk", 1)
        canc, bc = att("i_canc", 1)
        old, bo = att("i_old", 1, young=False)
        _, bn = self.kit_c("kw-r/kit-wave/hbm/ev1/items/i_noatt/gen/i_noatt")     # item dir without attempt_N
        touch(os.path.join(self.root, "kw-r/kit-wave/hbm/ev1/items/i_noatt/gen/x.log"), mtime=time.time() - 8 * 3600)
        h = "hx:"
        self.kw = {"attempts": {h + fail: {"active": False, "signed": False, "terminal": ["ENQUEUED/FAIL", "stage:FAIL"]},
                                h + sup: {"active": False, "signed": False, "terminal": ["FAIL/None"]},
                                h + canc: {"active": False, "signed": False, "terminal": ["CANCELLED/None"]},
                                h + old: {"active": False, "signed": False, "terminal": ["FAIL/None"]}},
                   "latest": {h + os.path.dirname(sup): 3, h + os.path.dirname(fail): 2}, "keep": []}
        self.run_job("--queuename-skip-trim-c", "--classes", "c")   # class a would take whole finished attempts
        for b in (bf, bu, bn):
            self.assertEqual(self.row(b)[3], "SKIP", self.row(b))
            self.assertTrue(self.row(b)[4].startswith("resume-pending"), self.row(b))
            self.assertTrue(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
        for b in (bs, bc, bo):
            self.assertEqual(self.row(b)[3], "DELETED", self.row(b))
            self.assertEqual(sorted(os.listdir(b)), ["2_floorplan.odb", "3_place.odb", "4_cts.odb"])

    def test_parse_queue_window_and_continuation(self):
        now = time.time()
        recent = time.strftime("%Y-%m-%d %H:%M", time.localtime(now - 3600))
        old = time.strftime("%Y-%m-%d %H:%M", time.localtime(now - 40 * 3600))
        txt = (f"- {old} PST STATE [A] /srv/opentallas-scratch2/claude/old/kit\n  cont /srv/x/claude/oldcont\n"
               f"- {recent} PST STATE [B] epyc6:/srv/opentallas-scratch2/claude/new/kit_dirname.\n"
               f"  - continuation scratch3/claude/newcont/zz\n")
        paths, words = ac.parse_queue(txt, now, 25, tz="")
        self.assertIn("/srv/opentallas-scratch2/claude/new/kit_dirname", paths)
        self.assertIn("/srv/opentallas-scratch3/claude/newcont/zz", paths)
        self.assertNotIn("/srv/opentallas-scratch2/claude/old/kit", paths)
        self.assertNotIn("/srv/x/claude/oldcont", paths)
        self.assertIn("kit_dirname", words)

    def test_live_cwd_cmdline_fd_docker(self):
        k1, b1 = self.kit_b("lv/cwd")
        k2, b2 = self.kit_b("lv/cmd")
        k3, b3 = self.kit_b("lv/fd")
        k4, b4 = self.kit_b("lv/dock")
        k5, b5 = self.kit_b("lv/dockanc/inner")
        self.spawn([sys.executable, "-c", "import time; time.sleep(60)"], cwd=k1)
        self.spawn([sys.executable, "-c", "import time; time.sleep(60)", k2 + "/run"])
        env = dict(os.environ, P=os.path.join(b3, "6_final.odb"))
        self.spawn([sys.executable, "-c", "import os,time; f=open(os.environ['P']); time.sleep(60)"], env=env)
        with open(os.path.join(self.ddir, "ids"), "w") as f:
            f.write("c1\nc2\n")
        with open(os.path.join(self.ddir, "mounts"), "w") as f:
            f.write(f"{k4}/run {os.path.join(self.root, 'lv/dockanc')} \n")
        self.run_job()
        self.assertSkip(b1, "live cwd")
        self.assertSkip(b2, "live cmdline")
        self.assertSkip(b3, "live fd")
        self.assertSkip(b4, "docker mount")
        self.assertSkip(b5, "docker mount")

    def test_hardlink_gitlocked_keep_lanes(self):
        k1, b1 = self.kit_b("lh/hl")
        os.link(os.path.join(b1, "5_route.odb"), os.path.join(self.t, "otherlink"))
        k2, b2 = self.kit_b("lh/wt/kit")
        gd = os.path.join(self.t, "gitadmin")
        os.makedirs(gd)
        touch(os.path.join(gd, "locked"), n=1)
        with open(os.path.join(self.root, "lh/wt/.git"), "w") as f:
            f.write(f"gitdir: {gd}\n")
        k3, b3 = self.kit_b("lh/keepanc/kit")
        touch(os.path.join(self.root, "lh/keepanc/.keep"), n=0)
        k4, b4 = self.kit_b("lh/keepin")
        touch(os.path.join(k4, "sub/.keep"), n=0)
        k5, b5 = self.kit_b("tok-lane/kit")
        k6, b6 = self.kit_b("kv-fn-9/kit")
        k7, b7 = self.kit_b("lh/rtools/kit")
        self.run_job()
        self.assertSkip(b1, "hardlink")
        self.assertSkip(b2, "gitlocked")
        self.assertSkip(b3, "keep")
        self.assertSkip(b4, "keep")
        self.assertSkip(b5, "lane")
        self.assertSkip(b6, "lane")
        self.assertSkip(b7, "tool tree")

    def test_c_old_keep_finished_only(self):
        # COORD 11-08 08:0x / 09:2x (DISK-URGENT-1): an ancestor .keep older than --c-old-keep-h does not stop the
        # class c trim of a FINISHED or SUPERSEDED kit; young .keep, .keep inside the kit, unfinished kits and every
        # other guard still protect
        day3 = time.time() - 72 * 3600
        touch(os.path.join(self.root, "ok/.keep"), n=0, mtime=day3)
        touch(os.path.join(self.root, "yk/.keep"), n=0, mtime=time.time() - 10 * 3600)
        fin, bfin = self.kit_c("ok/fin")
        touch(os.path.join(bfin, "6_final.odb"))
        sig, bsig = self.kit_c("ok/sig")
        touch(os.path.join(sig, "signoff/signoff.json"), n=10)
        unf, bunf = self.kit_c("ok/unf")
        inner, binner = self.kit_c("ok/inner")
        touch(os.path.join(binner, "6_final.odb"))
        touch(os.path.join(inner, "sub/.keep"), n=0)
        young, byoung = self.kit_c("yk/fin")
        touch(os.path.join(byoung, "6_final.odb"))
        prot, bprot = self.kit_c("ok/prot")
        touch(os.path.join(bprot, "6_final.odb"))
        self.prot.append((prot, "test protected"))
        a1 = os.path.join(self.root, "ok/kit-wave/hbm/ev1/items/it/attempt_1")
        _, ba1 = self.kit_c(os.path.relpath(os.path.join(a1, "gen/it"), self.root))
        os.makedirs(os.path.join(self.root, "ok/kit-wave/hbm/ev1/items/it/attempt_2"))
        age_tree(os.path.join(self.root, "ok/kit-wave"), mtime=time.time() - 30 * 3600)
        self.run_job("--queuename-skip-trim-c", "--classes", "c")          # negative control: flag off
        for b in (bfin, ba1):
            self.assertEqual(self.row(b)[3], "SKIP", self.row(b)); self.assertTrue(self.row(b)[4].startswith("keep"), self.row(b))
            self.assertTrue(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
        self.run_job("--queuename-skip-trim-c", "--classes", "c", "--c-old-keep-h", "48")
        self.assertTrue(self.row(bsig)[4].startswith("counted"), self.row(bsig))   # a signed kit stays counted
        for b in (bfin, ba1):
            self.assertEqual(self.row(b)[3], "DELETED", self.row(b))
            self.assertFalse(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
            self.assertTrue(os.path.exists(os.path.join(b, "3_place.odb")))
            self.assertTrue(os.path.exists(os.path.join(b, "2_floorplan.odb")))
        for b in (bunf, binner, byoung):
            self.assertEqual(self.row(b)[3], "SKIP", self.row(b)); self.assertTrue(self.row(b)[4].startswith("keep"), self.row(b))
            self.assertTrue(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
        self.assertEqual(self.row(bprot)[3], "SKIP", self.row(bprot))   # positive control: protected still wins
        self.assertTrue(self.row(bprot)[4].startswith("protected"), self.row(bprot))
        self.assertTrue(os.path.exists(os.path.join(bprot, "3_3_place_gp.odb")))

    def test_alternates_target(self):
        k, b = self.kit_b("lalt/objsrc")
        repo = os.path.join(self.root, "lalt2/repo/.git/objects/info")
        os.makedirs(repo)
        with open(os.path.join(repo, "alternates"), "w") as f:
            f.write(k + "/objects\n")
        self.run_job()
        self.assertSkip(b, "local keep")

    def test_inode_dedupe_roots(self):
        os.symlink(self.root, os.path.join(self.t, "rootalias"))
        self.assertEqual(ac.dedupe_roots([self.root, os.path.join(self.t, "rootalias")]), [self.root])


class TestAliases(unittest.TestCase):
    def test_findmnt(self):
        txt = ("/ /dev/md0\n/srv/opentallas-scratch3 /dev/md0[/home/ubuntu/scratch-root]\n"
               "/var/lib/docker /dev/md1[/system/docker]\n/run/docker/netns/x nsfs[net:[4026539810]]\n"
               "/srv/opentallas-scratch2 /dev/md1\n")
        al = ac.parse_findmnt(txt)
        self.assertIn(("/home/ubuntu/scratch-root", "/srv/opentallas-scratch3"), al)
        self.assertIn(("/srv/opentallas-scratch2/system/docker", "/var/lib/docker"), al)
        P = ac.Paths(al)
        self.assertEqual(P.canon("/home/ubuntu/scratch-root/claude/a"), "/srv/opentallas-scratch3/claude/a")
        self.assertIn("/home/ubuntu/scratch-root/claude/a", P.forms("/srv/opentallas-scratch3/claude/a"))
        ps = ac.PathSet([("/home/ubuntu/scratch-root/claude/a/k", "row")], canon=P.canon)
        self.assertTrue(ps.hit("/srv/opentallas-scratch3/claude/a/k/run"))
        self.assertTrue(ps.hit("/srv/opentallas-scratch3/claude/a"))
        self.assertIsNone(ps.hit("/srv/opentallas-scratch3/claude/b"))


class TestSafety(Base):
    def test_alert_stop_and_sticky(self):
        k1, b1 = self.kit_b("lz/a1")
        k2, b2 = self.kit_b("lz/a2")
        orig = ac.Job.eval_trim
        snapf = os.path.join(self.snap, "protected.tsv")

        def sneaky(job, cls, d):
            r = orig(job, cls, d)
            if d == b1:                    # a protected row appears between the scan and the recheck
                with open(snapf, "a") as f:
                    f.write(f"{k1}\tlate row\n")
            return r
        ac.Job.eval_trim = sneaky
        try:
            rc = self.run_job()
        finally:
            ac.Job.eval_trim = orig
        self.assertEqual(rc, 3)
        self.assertEqual(self.row(b1)[3], "ALERT")
        self.assertIsNone(self.row(b2))            # no further rows / deletes after the ALERT
        self.assertTrue(os.path.exists(os.path.join(b1, "5_route.odb")))
        self.assertTrue(os.path.exists(os.path.join(b2, "5_route.odb")))
        self.assertTrue(os.path.exists(os.path.join(self.state, "ALERT")))
        self.assertEqual(self.run_job(), 3)        # sticky
        self.assertIn("sticky", self.out)

    def test_positive_control_failure_aborts(self):
        k, b = self.kit_b("lctl/k")
        orig = ac.Job.delete
        ac.Job.delete = lambda job, cls, files: 0
        try:
            rc = self.run_job()
        finally:
            ac.Job.delete = orig
        self.assertEqual(rc, 4)
        self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "_ot_autoclean_ctl")))

    def test_negative_control_failure_aborts(self):
        k, b = self.kit_b("lctl/k")
        orig = ac.Job.guard_hits
        ac.Job.guard_hits = lambda job, k: None
        try:
            rc = self.run_job()
        finally:
            ac.Job.guard_hits = orig
        self.assertEqual(rc, 4)
        self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))

    def test_fail_closed_inputs(self):
        k, b = self.kit_b("lfc/k")
        self.assertEqual(self.run_job(snap_age=4 * 3600), 2)
        self.assertEqual(self.run_job("--min-protected", "1000"), 2)
        self.docker = "/nonexistent/docker"
        self.assertEqual(self.run_job(), 2)
        self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))
        open(os.path.join(self.t, "OFF"), "w").close()
        self.docker = "sh " + os.path.join(self.ddir, "fake")
        self.assertEqual(self.run_job(), 0)
        self.assertIn("OFF switch", self.out)
        self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))

    def test_docker_container_gone_between_ps_and_inspect(self):
        k, b = self.kit_b("dkr/k")
        with open(os.path.join(self.ddir, "ids"), "w") as f:
            f.write("abc123\n")
        gone = os.path.join(self.ddir, "gone")
        with open(gone, "w") as f:
            f.write('#!/bin/sh\ncase "$1" in ps) echo abc123;; inspect) echo "error: no such object: abc123" >&2; exit 1;; esac\n')
        self.docker = "sh " + gone
        self.assertEqual(self.run_job(), 0)
        self.assertFalse(os.path.exists(os.path.join(b, "5_route.odb")))
        bad = os.path.join(self.ddir, "bad")
        with open(bad, "w") as f:
            f.write('#!/bin/sh\ncase "$1" in ps) echo abc123;; inspect) echo "permission denied" >&2; exit 1;; esac\n')
        k2, b2 = self.kit_b("dkr/k2")
        self.docker = "sh " + bad
        self.assertEqual(self.run_job(), 2)
        self.assertTrue(os.path.exists(os.path.join(b2, "5_route.odb")))

    def test_never_names(self):
        job = ac.Job.__new__(ac.Job)
        with self.assertRaises(OSError):
            job.delete("b", [touch(os.path.join(self.t, "x/2_floorplan.odb"))])
        for n in ("2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "6_final.odb"):
            self.assertNotIn(n, ac.TRIM_B + ac.TRIM_C)

    def test_wt_reaper_call(self):
        self.kit_b("lw/k")
        fake = os.path.join(self.t, "fake_reaper.py")
        with open(fake, "w") as f:
            f.write("import sys,json\nopen(sys.argv[0]+'.argv','w').write(json.dumps(sys.argv[1:]))\nprint('wt-reaper: ok')\n")
        self.kw = {"attempts": {}, "latest": {}, "keep": ["hx:/srv/q/claude/src_tree"]}
        self.prot += [("/srv/p/claude/prot_row", "x")]
        self.run_job(wt=fake)
        argv = ac.jl(fake + ".argv")
        i = argv.index("--protected-dbs")
        self.assertEqual(argv[argv.index("--protected-dbs-repo") + 1], "")
        self.assertIn("--apply", argv)
        union = ac.rd(argv[i + 1])
        self.assertIn("hx\t/srv/q/claude/src_tree\tkitwave", union)
        self.assertIn("hx\t/srv/p/claude/prot_row\tprotected", union)
        self.assertIn("wt-reaper rc 0", self.out)

    def test_union_real_sources_only(self):
        # DISK-URGENT-2 audit, COORD 11-08: the union is copied back to protect.d/protected-dbs.txt by wt-reaper.  With the
        # flag, a path dropped from every real source leaves the union on the next tick and its row is free to go.
        home = os.path.join(self.t, "home")
        pd = os.path.join(home, ".local/state/wt-reaper/protect.d")
        os.makedirs(pd)
        k, b = self.kit_c("lane/kit")
        src = os.path.join(pd, "lane.txt")
        fake = os.path.join(self.t, "fake_sync.py")
        with open(fake, "w") as f:
            f.write("import sys,shutil\nsrc=sys.argv[sys.argv.index('--protected-dbs')+1]\n"
                    f"shutil.copy(src,{os.path.join(pd, 'protected-dbs.txt')!r})\nprint('wt-reaper: ok')\n")
        def union():
            return ac.rd(os.path.join(self.state, "protected-union.txt"))
        saved = ac.HOME
        ac.HOME = home
        try:
            with open(src, "w") as f:
                f.write(k + "\n")
            self.run_job("--classes", "c", "--union-real-sources-only", wt=fake)      # tick 1: a real source names it
            self.assertTrue(self.row(b)[4].startswith("local keep"), self.row(b))
            self.assertIn(k, union())
            self.assertTrue(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
            os.unlink(src)
            self.run_job("--classes", "c", wt=fake)                                  # negative control: flag off, it stays
            self.assertTrue(self.row(b)[4].startswith("local keep"), self.row(b))
            self.assertIn("protected-dbs.txt", self.row(b)[4])
            self.assertIn(k, union())
            self.run_job("--classes", "c", "--union-real-sources-only", wt=fake)      # no source left: gone from the union
            self.assertNotIn(k, union())
            self.assertEqual(self.row(b)[3], "DELETED", self.row(b))
            self.assertFalse(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
            self.assertTrue(os.path.exists(os.path.join(b, "3_place.odb")))
            k2, b2 = self.kit_c("lane/kit2")                                         # a real protected row still holds
            self.prot.append((k2, "real protected row"))
            self.run_job("--classes", "c", "--union-real-sources-only", wt=fake)
            self.assertTrue(self.row(b2)[4].startswith("protected"), self.row(b2))
            self.assertIn(k2, union())
        finally:
            ac.HOME = saved

    def test_spill_done_stops_holding(self):
        # COORD 11-08: <tag>.done = back-copy finished (spill_sweep reads only *.json).  With the flag it holds nothing; a
        # pending *.json still holds; flag off is the negative control.
        home = os.path.join(self.t, "home")
        sp = os.path.join(home, ".local/state/ot-run/spill_pending")
        os.makedirs(sp)
        k, b = self.kit_c("lane/spilled")
        k2, b2 = self.kit_c("lane/pending")
        with open(os.path.join(sp, "1-1.done"), "w") as f:
            json.dump({"roots": [k]}, f)
        with open(os.path.join(sp, "2-2.json"), "w") as f:
            json.dump({"roots": [k2]}, f)
        saved = ac.HOME
        ac.HOME = home
        try:
            self.run_job("--classes", "c")
            self.assertIn("1-1.done", self.row(b)[4])
            self.assertTrue(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
            self.run_job("--classes", "c", "--union-real-sources-only")
            self.assertEqual(self.row(b)[3], "DELETED", self.row(b))
            self.assertFalse(os.path.exists(os.path.join(b, "3_3_place_gp.odb")))
            self.assertIn("2-2.json", self.row(b2)[4])
            self.assertTrue(os.path.exists(os.path.join(b2, "3_3_place_gp.odb")))
        finally:
            ac.HOME = saved


class TestKitwave(unittest.TestCase):
    def test_reduce(self):
        A = "/srv/s2/claude/kit-wave/hbm/e1/items"
        st = {"items": {
            "1": {"status": "FAIL", "kit": f"epyc4:{A}/it/attempt_1/gen/k"},
            "2": {"status": "RUNNING", "kit": f"epyc4:{A}/it/attempt_3/gen/k",
                  "resume": {"changed": [["synth", "runner", f"{A}/it/attempt_2/gen/k/run_kit.sh"]]}, "dir": "/d2"},
            "3": {"status": "CANCELLED", "q_status": "RUNNING", "kit": f"intel1:{A}/cq/attempt_1/gen/k"},
            "4": {"status": "ENQUEUED", "q_status": "SIGNED", "kit": f"intel1:{A}/sg/attempt_2/gen/k"},
            "5": {"status": "ENQUEUED", "q_status": "FAIL", "kit": f"intel1:{A}/ef/attempt_1/gen/k"},
            "6": {"status": "WEIRD", "kit": f"intel1:{A}/wd/attempt_1/gen/k"},
        }}
        rows = [{"kit": f"epyc4:{A}/st/attempt_4/gen/k", "status": "SIGNED", "class": "COUNTED"},
                {"kit": f"epyc4:{A}/st/attempt_2/gen/k", "status": "SUPERSEDED", "class": "SUPERSEDED"}]
        out = ac.reduce_kitwave(st, rows, read_spec=lambda d: {"src": "/srv/s2/claude/kw/src_x", "host": "epyc4"} if d == "/d2" else {})
        at = out["attempts"]
        self.assertEqual(at[f"epyc4:{A}/it/attempt_1"]["terminal"], ["FAIL/None"])
        self.assertTrue(at[f"epyc4:{A}/it/attempt_3"]["active"])
        self.assertTrue(at[f"intel1:{A}/cq/attempt_1"]["active"])
        self.assertTrue(at[f"intel1:{A}/sg/attempt_2"]["signed"])
        self.assertFalse(at[f"intel1:{A}/ef/attempt_1"]["active"])
        self.assertTrue(at[f"intel1:{A}/wd/attempt_1"]["active"])
        self.assertTrue(at[f"epyc4:{A}/st/attempt_4"]["signed"])
        self.assertEqual(at[f"epyc4:{A}/st/attempt_2"]["terminal"], ["stage:SUPERSEDED"])
        self.assertEqual(out["latest"][f"epyc4:{A}/it"], 3)
        self.assertIn(f"epyc4:{A}/it/attempt_2/gen/k/run_kit.sh", out["keep"])     # resume source of a running row
        self.assertIn("epyc4:/srv/s2/claude/kw/src_x", out["keep"])


class TestProtectedSources(unittest.TestCase):
    """COORD 2026-11-10 (AUTOCLEAN-13): lanes/prune/ARCHIVE-PROTECTED.tsv is the third protected list"""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="ac-src-")
        self.coord = os.path.join(self.t, "coord")
        os.makedirs(os.path.join(self.coord, "lanes/prune"))
        with open(os.path.join(self.coord, "lanes/PROTECTED-DBS.txt"), "w") as f:
            f.write("hx\t/srv/none/claude/a/b\tkit_root\n")
        with open(os.path.join(self.coord, "PROTECTED-DBS.txt"), "w") as f:
            f.write("hx /srv/none/claude/c/d note\n")

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def write_ap(self, text):
        with open(os.path.join(self.coord, "lanes/prune/ARCHIVE-PROTECTED.tsv"), "w") as f:
            f.write(text)

    def test_archive_protected_rows_in_union(self):
        self.write_ap("# ARCHIVE protected union\n"
                      "any\t/srv/opentallas-scratch3/claude/kw24/eco/physical/die_plan/s81/bind\tasbuilt\n"
                      "intel2\t/srv/opentallas-scratch3/claude/kw24-wave-1106/runs\tlive input | NOTE 2026-11-10 retired\n")
        got = dict(ac.build_protected_union(self.coord))
        self.assertEqual(got.get("/srv/opentallas-scratch3/claude/kw24/eco/physical/die_plan/s81/bind"),
                         "lanes/prune/ARCHIVE-PROTECTED.tsv")
        self.assertIn("/srv/opentallas-scratch3/claude/kw24-wave-1106/runs", got)
        self.assertIn("/srv/none/claude/a/b", got)

    def test_archive_protected_required(self):
        # AUTOCLEAN-12 11-10 (live tool): the third list is REQUIRED like the first two; missing = refuse, nothing is deleted
        with self.assertRaises((RuntimeError, FileNotFoundError)):
            ac.build_protected_union(self.coord)
        self.write_ap("any\t/srv/none/claude/e/f\tasbuilt\n")
        rows = ac.build_protected_union(self.coord)
        self.assertEqual(sorted(p for p, _ in rows), ["/srv/none/claude/a/b", "/srv/none/claude/c/d", "/srv/none/claude/e/f"])

    def test_all_three_lists_required(self):
        self.write_ap("any\t/srv/none/claude/e/f\tasbuilt\n")
        for rel in ("PROTECTED-DBS.txt", "lanes/PROTECTED-DBS.txt", "lanes/prune/ARCHIVE-PROTECTED.tsv"):
            keep = os.path.join(self.coord, rel)
            data = open(keep).read()
            os.remove(keep)
            with self.assertRaises((RuntimeError, FileNotFoundError), msg=rel):
                ac.build_protected_union(self.coord)
            with open(keep, "w") as f:
                f.write(data)


class TestArchiveDriver(Base):
    def test_drive_archive_and_run(self):
        # a signed resign unit that cites a routed DB in a kit
        k, b = self.kit_b("larc/kit")
        unit = os.path.join(self.root, "larc/resign_x")
        os.makedirs(os.path.join(unit, "signoff"))
        os.makedirs(os.path.join(unit, "lec"))
        touch(os.path.join(unit, "lec/lec.json"), n=50)
        with open(os.path.join(unit, "signoff/signoff.json"), "w") as f:
            json.dump({"verdict": "SIGNED", "odb": b + "/6_final.odb"}, f)
        with open(os.path.join(unit, "PROVENANCE.json"), "w") as f:
            json.dump({"kind": "resign", "verdict": "SIGNED", "routed_db": b + "/6_final.odb"}, f)
        touch(os.path.join(b, "kit.lef"), n=77)
        k2, b2 = self.kit_b("larc/plainkit")
        coord = os.path.join(self.t, "coord")
        os.makedirs(os.path.join(coord, "lanes"))
        with open(os.path.join(coord, "lanes/PROTECTED-DBS.txt"), "w") as f:
            f.write("# header\nhx\t/srv/none/claude/a/b\tkit_root\n")
        with open(os.path.join(coord, "PROTECTED-DBS.txt"), "w") as f:
            f.write("hx /srv/none/claude/c/d note words\n")
        os.makedirs(os.path.join(coord, "lanes/prune"), exist_ok=True)
        with open(os.path.join(coord, "lanes/prune/ARCHIVE-PROTECTED.tsv"), "w") as f:
            f.write("any\t/srv/none/claude/e/f\tasbuilt\n")
        recent = time.strftime("%Y-%m-%d %H:%M")
        with open(os.path.join(coord, "lanes/COORD-REVIEW-QUEUE.md"), "w") as f:
            f.write(f"- {recent} PST STATE [X] nothing here /srv/none/claude/q/r\n")
        kws = os.path.join(self.t, "kws.json")
        with open(kws, "w") as f:
            json.dump({"items": {}}, f)
        shim = os.path.join(self.t, "shim.py")
        with open(shim, "w") as f:
            f.write("import subprocess,sys\nsys.exit(subprocess.run(['bash','-c',sys.argv[-1]]).returncode)\n")
        tools, rstate, arch = (os.path.join(self.t, x) for x in ("tools", "rstate", "archive"))
        base = ["drive", "--hosts", "hx", "--coord", coord, "--kitwave-state", kws, "--kitwave-stages", "/nonexistent",
                "--ssh", f"{sys.executable} -I {shim}", "--agidock-ssh", f"{sys.executable} -I {shim} agidock",
                "--agidock-python", f"{sys.executable} -I {tools}/ot-autoclean.py", "--archive-root", arch,
                "--compress", "zstd" if shutil.which("zstd") else "none", "--roots", self.root, "--tools-dir", tools,
                "--remote-state", rstate, "--design-export-hook", "",   # the export gate has its own tests (test_ot_autoclean_dx.py)
                f"--run-args=--roots {self.root} --docker '{self.docker}' --aliases {self.aliases} --min-protected 1 --wt-reaper '' --design-export off"]
        env = dict(os.environ, OT_AUTOCLEAN_OFF_FILES=os.path.join(self.t, "OFF"))
        r = subprocess.run([sys.executable, "-I", SCRIPT] + base, capture_output=True, text=True, env=env, timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WOULD-ARCHIVE hx:" + unit, r.stdout)
        self.assertIn("hx: TOTAL class b WOULD", r.stdout)
        self.assertFalse(os.path.exists(arch))
        self.assertTrue(os.path.exists(os.path.join(b2, "5_route.odb")))
        prune = os.listdir(os.path.join(coord, "lanes/prune"))
        self.assertTrue(any(p.startswith("AUTOCLEAN-auto-hx-") for p in prune), prune)
        # apply
        r = subprocess.run([sys.executable, "-I", SCRIPT] + base[:1] + ["--apply"] + base[1:], capture_output=True,
                           text=True, env=env, timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ARCHIVED hx:" + unit, r.stdout, r.stdout)
        a = ac.jl(os.path.join(unit, "ARCHIVED.json"))
        paths = {f["path"] for f in a["files"]}
        for p in (unit + "/signoff/signoff.json", unit + "/PROVENANCE.json", unit + "/lec/lec.json",
                  b + "/6_final.odb", b + "/6_final.spef", b + "/kit.lef"):
            self.assertIn(p, paths)
            self.assertTrue(os.path.isfile(arch + "/hx" + p), p)
        self.assertNotIn(b + "/5_route.odb", paths)
        self.assertTrue(a["verify"].startswith("OK files"))
        # signed content untouched; the cited kit is counted (kept), the plain kit trimmed
        self.assertTrue(os.path.exists(os.path.join(b, "5_route.odb")))
        self.assertFalse(os.path.exists(os.path.join(b2, "5_route.odb")))
        # second pass: nothing new to archive
        r = subprocess.run([sys.executable, "-I", SCRIPT] + base[:1] + ["--apply", "--no-run"] + base[1:],
                           capture_output=True, text=True, env=env, timeout=600)
        self.assertIn("already archived 1, to archive 0", r.stdout)

    def test_verify_mismatch_writes_no_marker(self):
        unit = os.path.join(self.root, "lm/resign")
        with open(touch(os.path.join(unit, "signoff/signoff.json"), n=1), "w") as f:
            json.dump({"verdict": "SIGNED"}, f)
        arch = os.path.join(self.t, "archive")
        tools = os.path.join(self.t, "tools")
        os.makedirs(tools)
        shim = os.path.join(self.t, "shim.py")
        with open(shim, "w") as f:
            f.write("import subprocess,sys\nsys.exit(subprocess.run(['bash','-c',sys.argv[-1]]).returncode)\n")
        # the 'agidock' end corrupts every file it unpacks
        bad = os.path.join(self.t, "badshim.py")
        with open(bad, "w") as f:
            f.write("import subprocess,sys,os\nc=sys.argv[-1]\nr=subprocess.run(['bash','-c',c]).returncode\n"
                    f"[open(os.path.join(d,x),'a').write('!') for d,_,fs in os.walk({arch!r}) for x in fs] if 'tar -C' in c else None\n"
                    "sys.exit(r)\n")
        shutil.copy(SCRIPT, os.path.join(tools, "ot-autoclean.py"))
        ns = ac.argparse.Namespace(ssh=f"{sys.executable} -I {shim}", agidock_ssh=f"{sys.executable} -I {bad}",
                                   timeout=300, tools_dir=tools, remote_state=os.path.join(self.t, "rs"),
                                   roots=[self.root], find_timeout=300, archive_root=arch, apply=True, compress="none",
                                   agidock_python=f"{sys.executable} -I {tools}/ot-autoclean.py")
        d = ac.Driver(ns)
        d.py = f"{sys.executable} -I {tools}/ot-autoclean.py"
        rows = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            ok = d.archive("hx", rows)
        self.assertFalse(ok, buf.getvalue())
        self.assertIn("verify mismatch", rows[0][6])
        self.assertFalse(os.path.exists(os.path.join(unit, "ARCHIVED.json")))


class SymlinkRootTest(unittest.TestCase):
    def test_symlinked_root_scanned_by_target(self):
        d = tempfile.mkdtemp()
        try:
            real = os.path.join(d, "scratch2", "claude"); os.makedirs(real)
            link = os.path.join(d, "scratch", "claude"); os.makedirs(os.path.dirname(link)); os.symlink(real, link)
            self.assertEqual(ac.dedupe_roots([link, real]), [os.path.realpath(real)])
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
