#!/usr/bin/env python3
"""tests for ot_autoclean.py: only allowed files are emptied, every protection holds, and it fails closed"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ot_autoclean as ac

OLD = time.time() - 7200


def touch(p, text="x" * 4096, mtime=OLD):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)
    os.utime(p, (mtime, mtime))


class T(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="ac")
        self.root = os.path.join(os.path.realpath(self.t), "srv", "scr", "claude")
        os.makedirs(self.root)
        self.prot_kit = self.kit("lane0/protkit")
        self.rows = [self.prot_kit] + [f"/srv/x/claude/l{i}/k" for i in range(ac.MIN_ROWS)]

    def tearDown(self):
        shutil.rmtree(self.t)

    def base(self, k):
        return os.path.join(k, "run/results/asap7/d/base")

    def kit(self, rel, odbs=("2_1_a.odb", "2_floorplan.odb", "3_3_place_gp.odb", "3_place.odb", "4_1_cts.odb", "4_cts.odb")):
        k = os.path.join(self.root, rel)
        for i, n in enumerate(odbs):
            touch(os.path.join(self.base(k), n), mtime=OLD + i)
        touch(os.path.join(k, "run/logs/asap7/d/base/3_place.log"))
        return k

    def go(self, dry=False, **kw):
        req = dict(roots=[self.root], protected=self.rows, live=[], blob="", dry=dry, state_dir=os.path.join(self.t, "state"))
        req.update(kw)
        return ac.sweep(req)

    def size(self, k, n):
        return os.path.getsize(os.path.join(self.base(k), n))

    def test_substep_emptied_mtime_kept_stage_kept(self):
        k = self.kit("l/k1")
        m = os.path.getmtime(os.path.join(self.base(k), "3_3_place_gp.odb"))
        r = self.go()
        self.assertEqual(r.get("fail_closed"), None)
        self.assertEqual(self.size(k, "3_3_place_gp.odb"), 0)
        self.assertEqual(os.path.getmtime(os.path.join(self.base(k), "3_3_place_gp.odb")), m)
        self.assertEqual(self.size(k, "2_1_a.odb"), 0)
        for n in ("4_cts.odb", "4_1_cts.odb"):
            self.assertGreater(self.size(k, n), 0)
        self.assertGreater(os.path.getsize(os.path.join(k, "run/logs/asap7/d/base/3_place.log")), 0)

    def test_make_sees_stage_up_to_date(self):
        if not shutil.which("make"):
            self.skipTest("no make")
        k = self.kit("l/kmake", ("3_5_dp.odb", "3_place.odb", "4_cts.odb"))
        b = self.base(k)
        os.rename(os.path.join(b, "3_5_dp.odb"), os.path.join(b, "3_5_place_dp.odb"))
        mk = os.path.join(b, "Makefile")
        with open(mk, "w") as f:
            f.write("all: 4_cts.odb\n4_cts.odb: 3_place.odb\n\tcp $< $@\n3_place.odb: 3_5_place_dp.odb\n\tcp $< $@\n")
        os.utime(mk, (OLD, OLD))
        self.go()
        self.assertEqual(self.size(k, "3_5_place_dp.odb"), 0)
        self.assertEqual(subprocess.run(["make", "-q", "-C", b]).returncode, 0)

    def test_no_stage_or_older_stage_keeps_substep(self):
        k = self.kit("l/k2", ("3_1_a.odb", "3_2_b.odb"))
        k3 = self.kit("l/k3", ("3_place.odb", "3_4_new.odb"))
        self.go()
        self.assertGreater(self.size(k, "3_1_a.odb"), 0)
        self.assertGreater(self.size(k3, "3_4_new.odb"), 0)

    def test_chain_needs_6_final(self):
        a = self.kit("l/a", ("5_1_grt.odb", "5_2_route.odb", "5_3_fillcell.odb", "5_route.odb"))
        b = self.kit("l/b", ("5_1_grt.odb", "5_2_route.odb", "5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb", "6_final.odb"))
        self.go()
        self.assertGreater(self.size(a, "5_route.odb"), 0)
        self.assertEqual(self.size(b, "5_route.odb"), 0)
        self.assertEqual(self.size(b, "6_1_fill.odb"), 0)
        for n in ("5_1_grt.odb", "5_2_route.odb", "6_final.odb"):
            self.assertGreater(self.size(b, n), 0)

    def test_stage_old_lane_kit_and_superseded_attempt_not_newest(self):
        names = ("1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt-failed.odb")
        lane = self.kit("l/lane", names)
        old = self.kit("w/items/x/attempt_1/gen/x", names)
        new = self.kit("w/items/x/attempt_2/gen/x", names)
        self.go()
        self.assertEqual(self.size(lane, "1_synth.odb"), 0)
        self.assertEqual(self.size(lane, "3_place.odb"), 0)
        self.assertGreater(self.size(lane, "4_cts.odb"), 0)
        self.assertGreater(self.size(lane, "5_1_grt-failed.odb"), 0)
        self.assertGreater(self.size(new, "3_place.odb"), 0)          # gated: kit_resume source
        self.assertGreater(self.size(new, "5_1_grt-failed.odb"), 0)

    def test_old_run_unlinks_big_keeps_records(self):
        names = ("1_synth.odb", "4_cts.odb")
        old = self.kit("w2/items/y/attempt_1/gen/y", names)
        self.kit("w2/items/y/attempt_2/gen/y", names)
        big = os.path.join(self.base(old), "4_cts.odb")
        with open(big, "wb") as f:
            f.write(b"x" * (2 << 20))
        os.utime(big, (OLD, OLD))
        log = os.path.join(old, "run/logs/asap7/d/base/big.log")
        touch(log, "x" * (2 << 20))
        self.go()
        self.assertFalse(os.path.exists(big))
        self.assertTrue(os.path.exists(log))

    def test_routed_lane_kit_keeps_seeds(self):
        k = self.kit("rl/kit", ("3_place.odb", "4_1_cts.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb", "6_final.odb"))
        self.go()
        for n in ("5_1_grt.odb", "5_2_route.odb", "6_final.odb"):
            self.assertGreater(self.size(k, n), 0)
        self.assertEqual(self.size(k, "4_cts.odb"), 0)
        self.assertFalse(os.path.exists(os.path.join(self.base(k), "4_1_cts.odb")))

    def test_latest_stage_stays(self):
        k = self.kit("l/plc", ("1_synth.odb", "2_floorplan.odb", "3_place.odb"))
        self.go()
        self.assertGreater(self.size(k, "3_place.odb"), 0)
        self.assertEqual(self.size(k, "2_floorplan.odb"), 0)

    def test_protected_rows_control_and_children(self):
        k = self.kit("lane1/par/kit9")
        self.rows.append(os.path.join(k, "run/results/asap7/d/base/6_final.odb"))
        u = self.kit("lane2/under/kit8")
        self.rows.append(os.path.join(self.root, "lane2/under"))
        r = self.go()
        for x in (k, u, self.prot_kit):
            self.assertGreater(self.size(x, "3_3_place_gp.odb"), 0)
        self.assertEqual(r["control_hits"], 3)

    def test_no_control_hit_fails_closed(self):
        k = self.kit("l/k")
        self.rows.remove(self.prot_kit)
        r = self.go()
        self.assertIn("control", r["fail_closed"])
        self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0)

    def test_short_list_fails_closed(self):
        k = self.kit("l/k")
        r = self.go(protected=[self.prot_kit])
        self.assertIn("usable rows", r["fail_closed"])
        self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0)

    def test_records_and_marks_keep_whole_kit(self):
        cases = {"keep": (".keep", ""), "prov": ("PROVENANCE.json", "{}"), "arch": ("ARCHIVED.json", "{}"),
                 "spill": (".ot-run-spill-copy", ""), "sgn": ("signoff/signoff.json", '{"verdict": "SIGNED"}'),
                 "lp": ("signoff/signoff.json", '{"verdict": "LOCAL_PASS_NEEDS_PARENT"}')}
        kits = {}
        for name, (f, txt) in cases.items():
            kits[name] = self.kit(f"m/{name}")
            touch(os.path.join(kits[name], f), txt)
        ns = self.kit("m/notsigned")
        touch(os.path.join(ns, "signoff/signoff.json"), '{"verdict": "NOT SIGNED"}')
        self.go()
        for name, k in kits.items():
            self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0, name)
        self.assertEqual(self.size(ns, "3_3_place_gp.odb"), 0)

    def test_ancestor_keep_and_signed_eco_child(self):
        k = self.kit("keepl/sub/k")
        touch(os.path.join(self.root, "keepl/.keep"), "")
        p = self.kit("n/parent")
        touch(os.path.join(p, "eco_a/i1/signoff/signoff.json"), '{"verdict": "SIGNED"}')
        self.go()
        self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0)
        self.assertGreater(self.size(p, "3_3_place_gp.odb"), 0)

    def test_live_path_cmdline_other_host_quiet(self):
        a = self.kit("o/livepath")
        b = self.kit("o/livecmdline")
        c = self.kit("o/otherhost")
        d = self.kit("o/recent")
        touch(os.path.join(d, "run/logs/x.log"), mtime=time.time())
        e = self.kit("o2/mountabove/k")
        self.go(live=[os.path.join(a, "run/x"), os.path.join(self.root, "o2/mountabove")],
                blob="bash run_kit.sh gen/livecmdline route", other_host_live=[c])
        for k in (a, b, c, d, e):
            self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0, k)

    def test_cited_abs_and_relative(self):
        a = self.kit("c/citedabs_kit")
        b = self.kit("c/cited_by_token")
        c = self.kit("cc/kit")
        d = self.kit("dd/kit")
        self.go(cited=[a], tokens=["cited_by_token", "cc/kit"])
        for k in (a, b, c):
            self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0, k)
        self.assertEqual(self.size(d, "3_3_place_gp.odb"), 0)

    def test_cited_lane_root_does_not_hold_far_kit(self):
        far = self.kit("wv/a/b/c/kitfar")
        near = self.kit("wv2/a/kitnear")
        self.go(cited=[os.path.join(self.root, "wv"), os.path.join(self.root, "wv2/a")])
        self.assertEqual(self.size(far, "3_3_place_gp.odb"), 0)
        self.assertGreater(self.size(near, "3_3_place_gp.odb"), 0)

    def test_closed_plan_keeps_read_db_and_final(self):
        k = self.kit("cl/kit1", ("1_synth.odb", "4_cts.odb", "5_route.odb", "6_1_fill.odb", "6_final.odb"))
        touch(os.path.join(k, "signoff/signoff.json"), json.dumps(dict(verdict="SIGNED", inputs=dict(odb=os.path.join(self.base(k), "5_route.odb")))))
        rec = ac.signed_record(k)
        got = {os.path.basename(p) for p, _ in ac.closed_plan(k, set(), rec)}
        self.assertEqual(got, {"1_synth.odb", "4_cts.odb", "6_1_fill.odb"})
        goal_route = self.kit("cl/kit2", ("1_synth.odb", "5_route.odb"))
        self.assertEqual(ac.closed_plan(goal_route, set(), rec), [])

    def test_closed_units_and_stub(self):
        k = self.kit("cl/kit3", ("1_synth.odb", "4_cts.odb", "6_final.odb"))
        touch(os.path.join(k, "signoff/signoff.json"), '{"verdict": "SIGNED"}')
        touch(os.path.join(k, "run/logs/x.log"), mtime=time.time() - 8 * 3600)
        for r, d, fs in os.walk(k):
            for f in fs:
                os.utime(os.path.join(r, f), (time.time() - 8 * 3600,) * 2)
        p = self.kit("cl/kit4", ("1_synth.odb", "6_final.odb"))
        touch(os.path.join(p, "signoff/signoff.json"), '{"verdict": "SIGNED"}')
        for r, d, fs in os.walk(p):
            for f in fs:
                os.utime(os.path.join(r, f), (time.time() - 8 * 3600,) * 2)
        self.rows.append(p)
        req = dict(roots=[self.root], protected=self.rows, live=[], blob="", state_dir=os.path.join(self.t, "state"))
        r = ac.closed_units(req)
        self.assertEqual([u["path"] for u in r["units"]], [k])
        self.assertGreaterEqual(r["control_hits"], 1)

    def test_cli_unknown_and_help_do_nothing(self):
        seen = []
        real = ac.read_required
        ac.read_required = lambda *x: seen.append(1) or (_ for _ in ()).throw(RuntimeError("must not get here"))
        try:
            self.assertEqual(ac.main(["--help"]), 0)
            self.assertEqual(ac.main(["--dryrun"]), 2)
        finally:
            ac.read_required = real
        self.assertEqual(seen, [])

    def test_hardlink_never_emptied(self):
        k = self.kit("l/hl")
        p = os.path.join(self.base(k), "3_3_place_gp.odb")
        os.link(p, p + ".other")
        self.go()
        self.assertGreater(os.path.getsize(p), 0)

    def test_eco_superseded_keeps_best_and_last(self):
        n = ("5_1_grt.odb", "5_2_route.odb", "6_final.odb")
        i = {x: self.kit(f"eco/r/{x}", n) for x in ("i1", "i2", "i3")}
        touch(os.path.join(self.root, "eco/r/eco_loop.json"), json.dumps(dict(
            verdict="EXHAUSTED", best=dict(dir=i["i2"]), iterations=[dict(dir=i["i1"]), dict(dir=i["i2"]), dict(dir=i["i3"])])))
        big = os.path.join(self.base(i["i1"]), "6_final.odb")
        touch(big, "x" * (2 << 20))
        self.go()
        self.assertFalse(os.path.exists(big))
        self.assertGreater(self.size(i["i2"], "6_final.odb"), 0)
        self.assertGreater(self.size(i["i3"], "6_final.odb"), 0)

    def test_eco_series_with_signed_pass_untouched(self):
        n = ("5_1_grt.odb", "6_final.odb")
        i1, i2 = self.kit("eco2/r/i1", n), self.kit("eco2/r/i2", n)
        touch(os.path.join(i2, "signoff/signoff.json"), '{"verdict": "SIGNED"}')
        touch(os.path.join(self.root, "eco2/r/eco_loop.json"), json.dumps(dict(
            verdict="PASS", best=dict(dir=i2), iterations=[dict(dir=i1), dict(dir=i2)])))
        self.go()
        self.assertGreater(self.size(i1, "6_final.odb"), 0)

    def test_dry_writes_nothing_and_counts(self):
        k = self.kit("l/dry")
        r = self.go(dry=True)
        self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0)
        self.assertGreater(sum(r["class_files"].values()), 0)
        self.assertFalse(os.path.exists(os.path.join(self.t, "state", "manifest.tsv")))
        self.assertFalse(os.path.exists(os.path.join(k, "run", ac.MARKER)))

    def test_manifest_lists_every_emptied_file_and_second_run_idle(self):
        self.kit("l/m")
        r = self.go()
        man = open(os.path.join(self.t, "state", "manifest.tsv")).read()
        self.assertEqual(len(man.strip().split("\n")), r["files"])
        self.assertIn("3_3_place_gp.odb", man)
        r2 = self.go()
        self.assertEqual(r2["files"], 0)
        self.assertGreaterEqual(r2["verdicts"].get("already-clean", 0), 1)

    def test_locked_worktree_not_entered_tracked_file_kept(self):
        wt = os.path.join(self.root, "w1")
        k = self.kit("w1/k")
        gd = os.path.join(self.t, "gd")
        os.makedirs(gd)
        touch(os.path.join(gd, "locked"), "")
        touch(os.path.join(wt, ".git"), "gitdir: " + gd)
        self.go()
        self.assertGreater(self.size(k, "3_3_place_gp.odb"), 0)
        repo = os.path.join(self.root, "w2")
        k2 = self.kit("w2/k")
        subprocess.run(["git", "init", "-q", repo], check=True)
        rel = os.path.relpath(os.path.join(self.base(k2), "3_3_place_gp.odb"), repo)
        subprocess.run(["git", "-C", repo, "add", "-f", rel], check=True)
        self.go()
        self.assertGreater(self.size(k2, "3_3_place_gp.odb"), 0)
        self.assertEqual(self.size(k2, "2_1_a.odb"), 0)

    def test_parse_rows_all_forms(self):
        rows = ac.parse_rows("# c\nepyc2\t/srv/a/claude/x\tn\nany\t/srv/a/claude/y\t\nepyc4:/srv/a/claude/z note\nepyc4 /srv/a/claude/w\n")
        self.assertEqual(rows, ["/srv/a/claude/x", "/srv/a/claude/y", "/srv/a/claude/z", "/srv/a/claude/w"])

    def test_queue_window(self):
        now = time.time()
        old = time.strftime("%Y-%m-%d %H:%M", time.localtime(now - 20 * 3600))
        new = time.strftime("%Y-%m-%d %H:%M", time.localtime(now - 3600))
        a, t = ac.queue_cites(f"- {old} PST x /srv/opentallas-scratch2/claude/old/k\n- {new} PST y /srv/opentallas-scratch2/claude/new/k\n  z kw/src_a\n", now)
        self.assertEqual(a, ["/srv/opentallas-scratch2/claude/new/k"])
        self.assertIn("kw/src_a", t)

    def test_live_rows_only_unfinished(self):
        p = "/srv/opentallas-scratch2/claude/"
        got = ac.live_rows({"jobs": {"a": {"status": "RUNNING", "kit": p + "r"}, "b": {"status": "DONE-CRASH", "kit": p + "d"}, "c": {"status": "GRT-DONE", "kit": p + "g"}}},
                           {"items": {"x": {"status": "ENQUEUED", "e": p + "q"}, "y": {"status": "FAIL", "e": p + "f"}}, "plans": {"z": p + "z"}})
        self.assertEqual(got, {p + "r", p + "g", p + "q", p + "z"})

    def test_hub_fail_closed_and_off_switch(self):
        env = os.environ.get("OT_AUTOCLEAN")
        os.environ["OT_AUTOCLEAN"] = "0"
        self.assertEqual(ac.main(["--dry"]), 0)
        if env is None:
            del os.environ["OT_AUTOCLEAN"]
        else:
            os.environ["OT_AUTOCLEAN"] = env
        with self.assertRaises(Exception):
            ac.read_required(self.t)


if __name__ == "__main__":
    unittest.main()
