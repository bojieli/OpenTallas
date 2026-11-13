"""CLEAN-2 11-12 (OWNER aggressive cleanup): with --live-refs-only the host keeps ONLY the current attempt of live / queued
kit-wave rows, the inputs of queued / running rows, signed current attempts, live jobs, protected paths still referenced and
unknown rows; earlier launches of a row, dropped record dirs, terminal rows whose queue column is stale and old-plan stage
rows no longer hold anything.  wt-reaper --tracked-ok: a signed citation that is clean git content does not pin a worktree.
    python3 -I tools/fleet/test_ot_autoclean_live.py"""
import json
import os
import subprocess as sp
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ot_autoclean_auto as T   # noqa: E402
import importlib.util                # noqa: E402

ac = T.ac
_spec = importlib.util.spec_from_file_location("wt_reaper_c2", os.path.join(HERE, "wt-reaper.py"))
wr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wr)

NOW = 2_000_000_000.0
R = "/srv/s2/claude/kw/runs/qc/kit-wave/qc/ev1/items"


def rec(status, q=None, kit="", d=None, upd=NOW - 86400, **kw):
    r = {"status": status, "q_status": q, "kit": kit, "evidence": "", "geom_dir": "", "dir": d, "updated": upd,
         "die": "qc", "item": kw.pop("item", "t1")}
    r.update(kw)
    return r


class RecLive(unittest.TestCase):
    def test_terminal_status_ends_live_after_grace(self):
        self.assertFalse(ac.rec_live(rec("CANCELLED", "RUNNING"), NOW))            # 203 stale rows on 11-12
        self.assertTrue(ac.rec_live(rec("CANCELLED", "RUNNING", upd=NOW - 600), NOW))   # teardown grace
        self.assertFalse(ac.rec_live(rec("CANCELLED", None, upd=NOW - 600), NOW))
        self.assertFalse(ac.rec_live(rec("FAIL"), NOW))

    def test_enqueued_follows_queue(self):
        self.assertFalse(ac.rec_live(rec("ENQUEUED", "FAIL"), NOW))
        self.assertFalse(ac.rec_live(rec("ENQUEUED", "SIGNED"), NOW))
        self.assertTrue(ac.rec_live(rec("ENQUEUED", "QUEUED"), NOW))
        self.assertTrue(ac.rec_live(rec("ENQUEUED", "WAIT-PARENT"), NOW))

    def test_active_and_unknown_status_live(self):
        for st in ("RUNNING", "ROUTE-HELD", "RETRY-INFRA", "PENDING-DEP", "PASS", "SOMETHING-NEW"):
            self.assertTrue(ac.rec_live(rec(st), NOW), st)


class ReduceLive(unittest.TestCase):
    def specs(self, m):
        return lambda d: m.get(d, {})

    def test_own_attempt_from_spec_work_when_no_kit(self):
        r = rec("FAIL", d="/kw/qc_t1_b1/a27")
        sp_ = {"work": f"{R}/t1/attempt_27", "gen_host": "epyc4"}
        self.assertEqual(ac.rec_own_attempt(r, sp_), ("epyc4", f"{R}/t1/attempt_27"))
        self.assertEqual(ac.rec_own_attempt(rec("FAIL", kit=f"epyc2:{R}/t1/attempt_3/gen/t1"), {}), ("epyc2", f"{R}/t1/attempt_3"))
        self.assertIsNone(ac.rec_own_attempt(rec("FAIL"), {}))
        self.assertIsNone(ac.rec_own_attempt(rec("FAIL"), {"work": f"{R}/t1", "gen_host": "e4"}))

    def test_history_superseded_current_kept_even_if_lower_number(self):
        state = {"items": {"qc|t1|b1": rec("RUNNING", d="/kw/qc_t1_b1/a27")}}
        specs = {"/kw/qc_t1_b1/a27": {"work": f"{R}/t1/attempt_27", "gen_host": "e4"}}
        hist = lambda d: [("e4", f"{R}/t1/attempt_41"), ("e4", f"{R}/t1/attempt_27")]
        out = ac.reduce_live(state, [], self.specs(specs), hist, [], NOW)
        a = out["live_attempts"]
        self.assertTrue(a[f"e4:{R}/t1/attempt_27"]["current"] and a[f"e4:{R}/t1/attempt_27"]["active"])
        self.assertIn("superseded", a[f"e4:{R}/t1/attempt_41"]["history"])
        self.assertFalse(a[f"e4:{R}/t1/attempt_41"]["current"])
        self.assertIn(f"e4:{R}/t1/attempt_27", out["live_keep"])
        self.assertNotIn(f"e4:{R}/t1/attempt_41", out["live_keep"])

    def test_orphan_dropped_only_when_item_known(self):
        state = {"items": {"qc|t1|b1": rec("FAIL", kit=f"e4:{R}/t1/attempt_5/gen/t1")}}
        orph = [("qc", "t1", "e4", f"{R}/t1/attempt_44"), ("qc", "zz", "e4", f"{R}/zz/attempt_1")]
        out = ac.reduce_live(state, [], None, None, orph, NOW)
        self.assertIn("dropped", out["live_attempts"][f"e4:{R}/t1/attempt_44"]["history"])
        self.assertNotIn(f"e4:{R}/zz/attempt_1", out["live_attempts"])        # unknown item: stays unknown (live)

    def test_keep_rules_running_queued_signed_stale(self):
        src = "/srv/s2/claude/kw45/src_qc"
        state = {"items": {
            "run": rec("RUNNING", kit=f"e4:{R}/t1/attempt_5/gen/t1", d="/kw/run/a5", resume=f"e4:{R}/t1/attempt_4"),
            "que": rec("ENQUEUED", "QUEUED", item="t2", kit=f"e4:{R}/t2/attempt_3/gen/t2", resume=f"e4:{R}/t2/attempt_2"),
            "sig": rec("ENQUEUED", "SIGNED", item="t3", kit=f"e4:{R}/t3/attempt_7/gen/t3", d="/kw/sig/a7"),
            "old": rec("CANCELLED", "RUNNING", item="t4", kit=f"e4:{R}/t4/attempt_9/gen/t4", d="/kw/old/a9"),
        }}
        specs = {"/kw/run/a5": {"src": src}, "/kw/sig/a7": {"src": "/srv/s2/claude/kw45/src_sig"},
                 "/kw/old/a9": {"src": "/srv/s2/claude/kw45/src_old"}}
        out = ac.reduce_live(state, [], self.specs(specs), None, [], NOW)
        keep = {k.partition(":")[2] for k in out["live_keep"]}
        self.assertIn(f"{R}/t1/attempt_5/gen/t1", keep)
        self.assertIn(src, keep)                                       # input of the running job
        self.assertNotIn(f"{R}/t1/attempt_4", keep)                    # running job is self contained
        self.assertIn(f"{R}/t2/attempt_2", keep)                       # queued row: resume source kept
        self.assertIn(f"{R}/t3/attempt_7", keep)                       # signed current attempt (until archived)
        self.assertNotIn("/srv/s2/claude/kw45/src_sig", keep)          # ... not its sources
        self.assertFalse(any("/t4/" in k or "src_old" in k for k in keep))   # CANCELLED with a stale RUNNING queue column
        a = out["live_attempts"]
        self.assertTrue(a[f"e4:{R}/t3/attempt_7"]["signed"])
        self.assertEqual(a[f"e4:{R}/t4/attempt_9"]["terminal"], ["CANCELLED/RUNNING"])
        self.assertTrue(all(why for why in out["live_keep_why"].values()))

    def test_stage_rows_old_plan_not_live_signed_marked(self):
        rows = [{"kit": f"e4:{R}/t5/attempt_2/gen/t5", "status": "PENDING-DEP", "class": "PLAN", "plan_current": "no"},
                {"kit": f"e4:{R}/t6/attempt_1/gen/t6", "status": "PENDING-DEP", "class": "PLAN", "plan_current": "yes"},
                {"kit": f"e4:{R}/t7/attempt_4/gen/t7", "status": "SIGNED", "class": "COUNTED", "plan_current": "no"}]
        out = ac.reduce_live({"items": {}}, rows, None, None, [], NOW)
        a = out["live_attempts"]
        self.assertFalse(a[f"e4:{R}/t5/attempt_2"]["active"])
        self.assertTrue(a[f"e4:{R}/t6/attempt_1"]["active"])
        self.assertTrue(a[f"e4:{R}/t7/attempt_4"]["signed"])
        keep = {k.partition(":")[2] for k in out["live_keep"]}
        self.assertNotIn(f"{R}/t5/attempt_2/gen/t5", keep)
        self.assertIn(f"{R}/t7/attempt_4/gen/t7", keep)


class History(T.Base):
    def test_kitwave_history_reads_record_tree(self):
        kw = os.path.join(self.t, "kit_wave")
        for kd, n, work in (("qc_t1_b1", 27, f"{R}/t1/attempt_27"), ("qc_t1_b1", 41, f"{R}/t1/attempt_41"),
                            ("qc_t1_b9", 44, f"{R}/t1/attempt_44")):
            os.makedirs(os.path.join(kw, kd, f"a{n}"))
            with open(os.path.join(kw, kd, f"a{n}", "spec.json"), "w") as f:
                json.dump({"work": work, "gen_host": "e4", "die": "qc", "item": "t1"}, f)
        hist, orph = ac.kitwave_history([os.path.join(kw, "qc_t1_b1", "a27")])
        self.assertEqual(sorted(p for _, p in hist(os.path.join(kw, "qc_t1_b1", "a27"))),
                         [f"{R}/t1/attempt_27", f"{R}/t1/attempt_41"])
        self.assertEqual(orph, [("qc", "t1", "e4", f"{R}/t1/attempt_44")])


class HostLive(T.Base):
    qopen = ()

    def write_snap(self, age=0):
        super().write_snap(age)
        with open(os.path.join(self.snap, ac.OPEN_FILE), "w") as f:
            json.dump({"paths": list(self.qopen)}, f)

    def attempt(self, item, n, rel="kw-x/kit-wave/qkv/ev1"):
        d = os.path.join(self.root, rel, f"items/{item}/attempt_{n}")
        T.touch(os.path.join(d, f"gen/{item}/run/results/asap7/dp_{item}/base/3_place.odb"))
        T.age_tree(d)
        return d

    def snap_kw(self, att, keep=()):
        self.kw = {"attempts": {}, "latest": {}, "keep": [],
                   "live_attempts": {"hx:" + d: dict({"active": False, "signed": False, "terminal": [], "current": False,
                                                      "history": ""}, **v) for d, v in att.items()},
                   "live_keep": ["hx:" + k for k in keep], "live_keep_why": {}}

    def test_history_attempt_deleted_current_live_kept(self):
        cur, old = self.attempt("t1", 27), self.attempt("t1", 41)
        unk = self.attempt("t9", 3)
        self.snap_kw({cur: {"active": True, "current": True}, old: {"history": "superseded: row x is now at attempt attempt_27"}},
                     keep=[cur])
        self.run_job("--classes", "a", "--live-refs-only")
        self.assertTrue(os.path.isdir(cur))
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.isdir(unk))                     # unknown row: never deleted (FLEET-2 rule kept)
        self.assertIn("kit-wave unknown", self.row(unk)[4])

    def test_without_flag_live_fields_ignored(self):
        old = self.attempt("t1", 41)
        self.snap_kw({old: {"history": "superseded: x"}})
        self.run_job("--classes", "a")
        self.assertTrue(os.path.isdir(old))                     # the old rules do not know it: unknown, kept

    def test_flag_refuses_snapshot_without_live_fields(self):
        self.attempt("t1", 41)
        self.kw = {"attempts": {}, "latest": {}, "keep": []}
        self.assertEqual(self.run_job("--classes", "a", "--live-refs-only"), 2)      # refused, nothing done
        self.assertTrue(os.path.isdir(os.path.join(self.root, "kw-x/kit-wave/qkv/ev1/items/t1/attempt_41")))

    def test_current_fail_attempt_keeps_resume_hold_despite_higher_number(self):
        cur = self.attempt("t1", 27)
        T.touch(os.path.join(cur, "gen/t1/run/results/asap7/dp_t1/base/2_1_floorplan.odb"))
        T.age_tree(cur)
        os.utime(cur, (time.time() - 3600,) * 2)
        newer = os.path.join(cur, "gen/t1/run/logs/x.log")
        T.touch(newer, 10, time.time() - 3600)                    # < 24 h: the kit wave may resume it
        other = os.path.join(os.path.dirname(cur), "attempt_41")
        self.snap_kw({cur: {"current": True, "terminal": ["FAIL/None"]}, other: {"history": "superseded: x"}})
        self.kw["latest"] = {"hx:" + os.path.dirname(cur): 41}
        self.run_job("--classes", "c", "--live-refs-only")
        self.assertTrue(os.path.exists(os.path.join(cur, "gen/t1/run/results/asap7/dp_t1/base/2_1_floorplan.odb")))

    def test_spec_root_and_item_parent_are_not_bind_refs(self):
        cur, old = self.attempt("t1", 5), self.attempt("t1", 4)
        other = self.attempt("t2", 1)
        ev = os.path.dirname(os.path.dirname(os.path.dirname(cur)))
        src = os.path.join(self.root, "src_tree")
        os.makedirs(src)
        rdir = os.path.join(self.root, "hubrec/a5")
        os.makedirs(rdir)
        with open(os.path.join(rdir, "spec.json"), "w") as f:
            json.dump({"root": ev, "work": cur, "src": src, "resume_from": old + "/gen"}, f)
        os.makedirs(old + "/gen", exist_ok=True)
        self.snap_kw({cur: {"active": True, "current": True}, old: {"terminal": ["FAIL/None"]},
                      other: {"terminal": ["CANCELLED/None"]}}, keep=[cur, rdir])
        self.run_job("--classes", "a", "--live-refs-only")
        self.assertTrue(os.path.isdir(cur))
        self.assertTrue(os.path.isdir(src))
        self.assertTrue(os.path.isdir(old), "a path the spec names (resume source) stays")
        self.assertFalse(os.path.exists(other), "spec root (whole event dir) must not hold other items")
        self.run_job("--classes", "a")                         # old rules: root held it -> (already gone) no error

    def test_queue_path_frees_superseded_not_current_and_open_readyask_holds(self):
        cur, old, old2 = self.attempt("t1", 7), self.attempt("t1", 6), self.attempt("t1", 5)
        self.snap_kw({cur: {"current": True, "terminal": ["FAIL/None"]}, old: {"history": "superseded: x"},
                      old2: {"history": "superseded: x"}})
        self.qpaths = [cur, old, old2]
        self.qopen = [old2]
        self.run_job("--classes", "a", "--live-refs-only", "--aggressive")
        self.assertTrue(os.path.isdir(cur), "current attempt named by a queue path stays")
        self.assertFalse(os.path.exists(old), "superseded attempt named only by a queue path goes")
        self.assertTrue(os.path.isdir(old2), "path in an open READY/ASK stays")
        self.assertIn("queue-open", self.row(old2)[4])

    def test_flag_refuses_snapshot_without_open_list(self):
        d = self.attempt("t1", 2)
        self.snap_kw({d: {"history": "superseded: x"}})
        T.Base.write_snap(self)
        os.unlink(os.path.join(self.snap, ac.OPEN_FILE)) if os.path.exists(os.path.join(self.snap, ac.OPEN_FILE)) else None
        self.write_snap = lambda age=0: T.Base.write_snap(self, age)
        self.assertEqual(self.run_job("--classes", "a", "--live-refs-only"), 2)
        self.assertTrue(os.path.isdir(d))

    def signed_attempt(self, item, n, archived=False):
        d = self.attempt(item, n)
        unit = os.path.join(d, "gen", item, "signed_unit")
        T.touch(os.path.join(unit, "6_final.odb"))
        with open(os.path.join(unit, "signoff.json"), "w") as f:
            json.dump({"status": "SIGNED", "verdict": "SIGNED"}, f)
        T.age_tree(d)
        return d, unit

    def test_signed_attempt_needs_export_first(self):
        d, unit = self.signed_attempt("t3", 2)
        self.snap_kw({d: {"history": "superseded: x"}})
        self.run_job("--classes", "a", "--live-refs-only", "--aggressive")
        self.assertTrue(os.path.isdir(d))
        if self.row(d):
            self.assertIn("signed", self.row(d)[4])

    def test_signed_attempt_with_verified_export_goes_only_aggressive(self):
        d, unit = self.signed_attempt("t4", 2)
        self.snap_kw({d: {"history": "superseded: x"}})
        orig = ac.Job.stub_verified
        ac.Job.stub_verified = lambda self_, u: None if u == unit else "no ARCHIVED.json"
        try:
            self.run_job("--classes", "a", "--live-refs-only")
            self.assertTrue(os.path.isdir(d), "not without --aggressive")
            self.run_job("--classes", "a", "--live-refs-only", "--aggressive")
            self.assertFalse(os.path.exists(d), self.out[-600:])
            self.assertEqual(self.recheck_alerts(), 0)
        finally:
            ac.Job.stub_verified = orig

    def recheck_alerts(self):
        return sum(1 for r in self.manifest if r[3] == "ALERT")

    def stale_setup(self, stale_rel):
        kit = os.path.join(self.root, stale_rel)
        d = os.path.join(kit, "run/results/asap7/x/base")
        for n in ("3_place.odb", "2_1_floorplan.odb"):
            T.touch(os.path.join(d, n))
        self.prot.append((kit, "lanes/prune/ARCHIVE-PROTECTED.tsv"))
        self.kw = {"attempts": {}, "latest": {}, "keep": [], "live_attempts": {}, "live_keep": [], "live_keep_why": {}}
        os.makedirs(self.snap, exist_ok=True)
        with open(os.path.join(self.snap, ac.STALE_FILE), "w") as f:
            f.write(kit + "\n")
        return kit, os.path.join(d, "2_1_floorplan.odb")

    def test_unreferenced_stale_archive_row_released(self):
        kit, f = self.stale_setup("lane-a/kitA")
        self.run_job("--classes", "c")
        self.assertTrue(os.path.exists(f))                       # old rules: protected
        self.run_job("--classes", "c", "--live-refs-only")
        self.assertFalse(os.path.exists(f))

    def test_referenced_stale_archive_row_still_protects(self):
        kit, f = self.stale_setup("lane-a/kitB")
        self.kw["live_keep"] = ["hx:" + kit]
        self.run_job("--classes", "c", "--live-refs-only")
        self.assertTrue(os.path.exists(f))

    def test_stale_file_ignored_for_fresh_rows(self):
        coord = os.path.join(self.t, "coord")
        os.makedirs(os.path.join(coord, "lanes/prune"))
        with open(os.path.join(coord, ac.ARCHIVE_LIST), "w") as f:
            f.write("# hdr\nany\t/srv/a/claude/x/old\tARCHIVE-1106B asbuilt/bind.f 21:3x\n"
                    "any\t/srv/a/claude/x/new\tWAVE-OPS-1 nightly wave src\n"
                    "any\t/srv/a/claude/x/both\tCOORD 20:2x asbuilt-named path (kw*/dkv*)\n"
                    "any\t/srv/a/claude/x/blank\t\n")
        rows = [("/srv/a/claude/x/old", ac.ARCHIVE_LIST), ("/srv/a/claude/x/new", ac.ARCHIVE_LIST),
                ("/srv/a/claude/x/both", ac.ARCHIVE_LIST), ("/srv/a/claude/x/both", "lanes/PROTECTED-DBS.txt"),
                ("/srv/a/claude/x/blank", ac.ARCHIVE_LIST)]
        self.assertEqual(ac.archive_stale_paths(coord, rows), {"/srv/a/claude/x/old", "/srv/a/claude/x/blank"})


class OpenReadyAsk(unittest.TestCase):
    Q = ("- 2026-11-12 10:00 PST READY [A -> COORD] claude/a-1112@aaaaaaaaaa11 keep /srv/s2/claude/a/x\n"
         "- 2026-11-12 10:05 PST READY [B -> COORD] claude/b-1112@bbbbbbbbbb22 path /srv/s2/claude/b/y\n"
         "- 2026-11-12 10:10 PST STATE [C -> COORD] status\n"
         "  ASK COORD: may I drop /srv/s2/claude/c/z\n"
         "- 2026-11-12 11:00 PST MERGED [ROOT-MERGE -> A] claude/a-1112@aaaaaaaaaa11\n"
         "- 2026-11-01 10:00 PST READY [OLD] /srv/s2/claude/old/w\n")

    def test_open_and_closed(self):
        import datetime
        from zoneinfo import ZoneInfo
        now = datetime.datetime(2026, 11, 12, 12, 0, tzinfo=ZoneInfo("America/Los_Angeles")).timestamp()
        got = ac.parse_open_readyask(self.Q, now)
        self.assertNotIn("/srv/s2/claude/a/x", got)        # merged
        self.assertIn("/srv/s2/claude/b/y", got)           # still open
        self.assertIn("/srv/s2/claude/c/z", got)           # ASK continuation line, no key: open
        self.assertNotIn("/srv/s2/claude/old/w", got)      # outside the 7-day window


class ReaperTracked(T.Base):
    def setUp(self):
        super().setUp()
        self.wt = os.path.join(self.root, "lane/wt")
        os.makedirs(os.path.join(self.wt, "physical/views"))
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        sp.run(["git", "init", "-q", self.wt], check=True)
        with open(os.path.join(self.wt, "physical/views/v.json"), "w") as f:
            f.write("{}")
        sp.run(["git", "-C", self.wt, "add", "physical"], check=True)
        sp.run(["git", "-C", self.wt, "commit", "-q", "-m", "x"], check=True, env=env)
        wr.tracked_clean.cache_clear()

    def pr(self, p, origin, ok=True):
        return wr.protected(self.wt, os.path.join(self.wt, ".git"), os.path.join(self.t, "other.git"), (), [(p, origin)], ok)

    def test_tracked_clean_citation_does_not_pin(self):
        p = os.path.join(self.wt, "physical/views/v.json")
        self.assertIsNone(self.pr(p, "protected-dbs.txt [counted]"))
        self.assertIsNone(self.pr(os.path.dirname(p), "protected-dbs.txt [protected]"))
        self.assertIsNotNone(self.pr(p, "protected-dbs.txt [counted]", ok=False))   # flag off: unchanged

    def test_export_marker_is_not_dirt(self):
        p = os.path.join(self.wt, "physical/views")
        with open(os.path.join(p, "ARCHIVED.json"), "w") as f:
            f.write("{}")
        self.assertIsNone(self.pr(p, "protected-dbs.txt [counted]"))
        real, junk = wr.dirt(self.wt, True)
        self.assertEqual(real, [])
        self.assertEqual(len(wr.dirt(self.wt, False)[0]), 1)       # flag off: unchanged
        with open(os.path.join(p, "other.json"), "w") as f:
            f.write("{}")
        wr.tracked_clean.cache_clear()
        self.assertIsNotNone(self.pr(p, "protected-dbs.txt [counted]"))

    def test_kitwave_and_localkeep_rows_still_pin(self):
        p = os.path.join(self.wt, "physical/views/v.json")
        for o in ("protected-dbs.txt [kitwave]", "protected-dbs.txt [localkeep]", "kit_wave.txt", "protected-dbs.txt"):
            self.assertIsNotNone(self.pr(p, o), o)

    def test_untracked_or_modified_or_ignored_pins(self):
        u = os.path.join(self.wt, "results/signed/signoff.json")
        os.makedirs(os.path.dirname(u))
        with open(u, "w") as f:
            f.write("{}")
        self.assertIsNotNone(self.pr(u, "protected-dbs.txt [counted]"))
        p = os.path.join(self.wt, "physical/views/v.json")
        with open(p, "w") as f:
            f.write('{"changed": 1}')
        wr.tracked_clean.cache_clear()
        self.assertIsNotNone(self.pr(p, "protected-dbs.txt [counted]"))
        self.assertIsNotNone(self.pr(os.path.dirname(p), "protected-dbs.txt [counted]"))

    def test_union_kind_parsed_into_origin(self):
        st = os.path.join(self.t, "rstate")
        os.makedirs(os.path.join(st, "protect.d"))
        with open(os.path.join(st, "protect.d", "protected-dbs.txt"), "w") as f:
            f.write("# x\nhx\t/srv/a/b/c\tcounted: named by signed /x\nhx\t/srv/a/b/d\tkitwave: kit-wave live\n")
        got = dict(wr.protect_list(st))
        self.assertEqual(got["/srv/a/b/c"], "protected-dbs.txt [counted]")
        self.assertEqual(got["/srv/a/b/d"], "protected-dbs.txt [kitwave]")

    def test_closure_from_live_seed_never_released(self):
        p = os.path.join(self.wt, "physical/views/v.json")
        self.assertIsNotNone(wr.closure_ref(self.wt, [(p, "live process/docker")], True))
        self.assertIsNone(wr.closure_ref(self.wt, [(p, "protected-dbs.txt [counted] -> /x")], True))


if __name__ == "__main__":
    unittest.main()
