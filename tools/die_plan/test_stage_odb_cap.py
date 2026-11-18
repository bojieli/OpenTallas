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
        got = self.names(d)
        self.assertEqual(got, ["2_1_floorplan.odb", "2_4_floorplan_pdn.odb", "3_1_place_gp_skip_io.odb", "3_5_place_dp.odb", "4_1_cts.odb",
                               "5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb"])
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
        self.assertEqual(len(dry), 8); self.assertTrue(os.path.exists(os.path.join(d, "6_1_fill.odb")))
        real = C.once(d, d, log=lambda m: None, scan=lambda p: (set(), []))
        self.assertEqual(len(real), 8); self.assertFalse(os.path.exists(os.path.join(d, "6_1_fill.odb")))
        self.assertTrue(all(os.path.exists(os.path.join(d, k)) for k in ("2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "6_final.odb")))
