import os, tempfile, time, unittest
import stage_odb_cap as C

NOW = 1_000_000.0


def mk(files, age=1000):
    d = tempfile.mkdtemp()
    for n, sz in files.items():
        p = os.path.join(d, n); open(p, "wb").write(b"x" * sz); os.utime(p, (NOW - age, NOW - age))
    return d


FULL = {n: 10 for n in ("1_synth.odb", "2_1_floorplan.odb", "2_4_floorplan_pdn.odb", "2_floorplan.odb", "3_1_place_gp_skip_io.odb", "3_5_place_dp.odb", "3_place.odb",
                        "4_1_cts.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb", "6_final.odb", "6_final.v", "6_final.def")}


class Cap(unittest.TestCase):
    def names(self, d, **kw):
        return sorted(os.path.basename(p) for p, _ in C.plan(d, NOW, **kw))

    def test_finished_kit_keeps_anchors_and_the_latest_final_only(self):
        d = mk(FULL)
        got = self.names(d, ended=True)       # FLOW-FIX-2045: the early-stage rules apply to an ended run only
        self.assertEqual(got, ["2_1_floorplan.odb", "2_4_floorplan_pdn.odb", "3_1_place_gp_skip_io.odb", "3_5_place_dp.odb", "4_1_cts.odb",
                               "5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb"])
        self.assertEqual(self.names(d), ["5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb"])      # a live watcher never takes a make prerequisite of a later stage
        for keep in ("1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "6_final.odb", "6_final.v", "6_final.def"):
            self.assertNotIn(keep, got)

    def test_nothing_goes_before_its_successor_is_written(self):
        d = mk({k: 10 for k in ("2_1_floorplan.odb", "3_1_place_gp_skip_io.odb", "4_1_cts.odb", "5_3_fillcell.odb", "6_1_fill.odb")})
        self.assertEqual(self.names(d), [])                         # no 2_floorplan / 3_place / 4_cts / 5_route / 6_final yet
        d = mk(dict(FULL, **{"6_final.odb": 0}))                     # an empty final is not written
        self.assertNotIn("6_1_fill.odb", self.names(d))

    def test_young_successor_and_open_files_are_kept(self):
        d = mk(FULL, age=1000)
        os.utime(os.path.join(d, "6_final.odb"), (NOW - 30, NOW - 30))
        self.assertNotIn("5_route.odb", self.names(d)); self.assertNotIn("6_1_fill.odb", self.names(d))
        d = mk(FULL)
        self.assertNotIn("5_3_fillcell.odb", self.names(d, open_files={os.path.join(d, "5_3_fillcell.odb")}))

    def test_hardlinked_file_is_never_deleted(self):
        d = mk(FULL); os.link(os.path.join(d, "5_3_fillcell.odb"), os.path.join(d, "x_link"))
        self.assertNotIn("5_3_fillcell.odb", self.names(d))

    def test_opt_out_env_and_keep_file_and_busy_eco_process(self):
        d = mk(FULL); log = []
        os.environ["OT_KEEP_STAGE_ODBS"] = "1"
        try:
            self.assertEqual(C.once(d, d, now=NOW, log=log.append, scan=lambda p: (set(), [])), [])
        finally:
            del os.environ["OT_KEEP_STAGE_ODBS"]
        open(os.path.join(d, ".keep_stage_odbs"), "w").close()
        self.assertEqual(C.once(d, d, now=NOW, log=log.append, scan=lambda p: (set(), [])), [])
        d2 = mk(FULL)
        self.assertEqual(C.once(d2, d2, now=NOW, log=log.append, scan=lambda p: (set(), ["python3 eco_loop.py"])), [])
        self.assertTrue(any("eco/resume process active" in m for m in log))

    def test_real_pass_deletes_and_dry_pass_does_not(self):
        d = mk(FULL, age=100000)
        dry = C.once(d, d, dry=True, log=lambda m: None, scan=lambda p: (set(), []))
        self.assertEqual(len(dry), 3); self.assertTrue(os.path.exists(os.path.join(d, "6_1_fill.odb")))
        real = C.once(d, d, log=lambda m: None, scan=lambda p: (set(), []))
        self.assertEqual(len(real), 3)
        self.assertTrue(os.path.exists(os.path.join(d, "3_5_place_dp.odb")))       # the live pass keeps the early stages
        self.assertEqual(len(C.once(d, d, log=lambda m: None, scan=lambda p: (set(), []), ended=True)), 5); self.assertFalse(os.path.exists(os.path.join(d, "6_1_fill.odb")))
        self.assertTrue(all(os.path.exists(os.path.join(d, k)) for k in ("2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "6_final.odb")))


class StageGuard(unittest.TestCase):
    """FLOW-FIX-2045 (FABLE-PD-HEAD-2040): a kit whose older watcher deleted early-stage ODBs must not silently rebuild from floorplan after CTS"""

    def kit(self, have, deleted):
        k = tempfile.mkdtemp()
        b = os.path.join(k, "run", "results", "asap7", "dp_x", "base"); os.makedirs(b)
        for n in have:
            open(os.path.join(b, n), "wb").write(b"x")
        open(os.path.join(k, "stage_odb_cap.log"), "w").write("".join("2026-11-19 01:55:00 STAGE-CAP deleted %s/%s 10\n" % (b, n) for n in deleted))
        return k

    def test_no_cap_deletions_no_finding(self):
        self.assertEqual(C.guard(self.kit(["3_place.odb", "4_cts.odb"], []), log=lambda m: None), 0)

    def test_cts_done_and_early_odb_missing_is_loud(self):
        msgs = []
        k = self.kit(["2_floorplan.odb", "3_place.odb", "4_cts.odb"], ["3_5_place_dp.odb", "4_1_cts.odb"])
        self.assertEqual(C.guard(k, "4_cts.odb", msgs.append), 13)
        self.assertIn("FAIL_STAGE_ODB_MISSING", msgs[0]); self.assertIn("3_5_place_dp.odb", msgs[0])
        os.environ["OT_ALLOW_STAGE_REBUILD"] = "1"
        try:
            self.assertEqual(C.guard(k, "4_cts.odb", lambda m: None), 0)
        finally:
            del os.environ["OT_ALLOW_STAGE_REBUILD"]

    def test_place_only_kit_is_a_warning_not_a_stop(self):
        msgs = []
        k = self.kit(["2_floorplan.odb", "3_place.odb"], ["3_1_place_gp_skip_io.odb"])
        self.assertEqual(C.guard(k, "4_cts.odb", msgs.append), 0)
        self.assertIn("STAGE-ODB-REBUILD", msgs[0])
        self.assertEqual(C.guard(k, "3_place.odb", lambda m: None), 13)

    def test_restored_file_is_not_missing(self):
        k = self.kit(["4_cts.odb", "3_5_place_dp.odb"], ["3_5_place_dp.odb"])
        self.assertEqual(C.guard(k, "4_cts.odb", lambda m: None), 0)

    def test_run_kit_calls_the_guard_before_the_ff_grt_pass_and_at_start(self):
        import gen_phys
        t = gen_phys.RUN_KIT
        self.assertLess(t.index("stage_odb_cap.py --guard /work --need 4_cts.odb"), t.index("OT_VCLK_CORNER=ff \\$MF grt CORNER=BC"))
        self.assertIn('stage_odb_cap.py" --guard "$K" --need 5_1_grt.odb', t)
        self.assertNotIn("--ended", t)       # the live watcher never gets the early-stage rules
