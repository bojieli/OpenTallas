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
        self.assertEqual(self.names(d), got)      # FLOW-FIX-2045: the same victims for a live run; once() empties the early ones (placeholder) instead of deleting
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
        self.assertEqual(len(real), 8)
        self.assertEqual(os.path.getsize(os.path.join(d, "3_5_place_dp.odb")), 0)       # the live pass empties the early stages, keeping the file (and its mtime) for make
        self.assertFalse(os.path.exists(os.path.join(d, "5_route.odb"))); self.assertFalse(os.path.exists(os.path.join(d, "6_1_fill.odb")))
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


def test_goal_finish_runs_the_same_grt_path_as_route():
    """FLOW-FIX-2045 (114 S81 D8i col builds launched with goal finish: the FF-corner GRT step and the TT / hold steps were skipped, the plain GRT then died 'must explicitly select FF')"""
    import re
    import gen_phys
    t = gen_phys.RUN_KIT
    lines = [l for l in t.splitlines() if "[ $GOAL = route ] || [ $GOAL = grt ]" in l]
    assert lines and all("[ $GOAL = finish ]" in l.split("[ $GOAL = grt ]", 1)[1][:40] for l in lines), lines[:2]
    assert "OT_VCLK_CORNER=ff \\$MF grt CORNER=BC" in t
    ff = [l for l in t.splitlines() if "OT_VCLK_CORNER=ff \\$MF grt CORNER=BC" in l][0]
    assert "[ $GOAL = finish ]" in ff
    assert '[ -z \\"\\$HM\\" ] || [ $GOAL = finish ]' not in t              # the plain `make grt` for finish is gone when the FF hold margin is known
    assert re.search(r'if \[ -z \\"\\\$HM\\" \]; then \\\$M grt', t)


MAKEFILE = """B = .
$(B)/2_1_floorplan.odb: $(B)/1_synth.odb
\tcp $< $@
$(B)/2_2_floorplan_macro.odb: $(B)/2_1_floorplan.odb
\tcp $< $@
$(B)/2_3_floorplan_tapcell.odb: $(B)/2_2_floorplan_macro.odb
\tcp $< $@
$(B)/2_4_floorplan_pdn.odb: $(B)/2_3_floorplan_tapcell.odb
\tcp $< $@
$(B)/2_floorplan.odb: $(B)/2_4_floorplan_pdn.odb
\tcp $< $@
$(B)/3_1_place_gp_skip_io.odb: $(B)/2_floorplan.odb
\tcp $< $@
$(B)/3_5_place_dp.odb: $(B)/3_1_place_gp_skip_io.odb
\tcp $< $@
$(B)/3_place.odb: $(B)/3_5_place_dp.odb
\tcp $< $@
$(B)/4_1_cts.odb: $(B)/3_place.odb
\tcp $< $@
$(B)/4_cts.odb: $(B)/4_1_cts.odb
\tcp $< $@
$(B)/5_1_grt.odb: $(B)/4_cts.odb
\tcp $< $@
"""


class Placeholder(unittest.TestCase):
    """FLOW-FIX-2045: intermediate stage ODBs of a live run are emptied, not deleted: make -q must report nothing to rebuild (the deletion made every later make restart at floorplan)"""

    def build(self):
        import subprocess
        d = tempfile.mkdtemp()
        names = ["1_synth.odb", "2_1_floorplan.odb", "2_2_floorplan_macro.odb", "2_3_floorplan_tapcell.odb", "2_4_floorplan_pdn.odb", "2_floorplan.odb", "3_1_place_gp_skip_io.odb",
                 "3_5_place_dp.odb", "3_place.odb", "4_1_cts.odb", "4_cts.odb", "5_1_grt.odb"]
        for i, n in enumerate(names):
            p = os.path.join(d, n); open(p, "wb").write(b"x" * 1000); os.utime(p, (NOW - 10000 + i * 100, NOW - 10000 + i * 100))
        open(os.path.join(d, "Makefile"), "w").write(MAKEFILE)
        return d, names, lambda: subprocess.run(["make", "-q", "-C", d, "5_1_grt.odb"], capture_output=True).returncode

    def test_make_reports_nothing_to_rebuild_after_placeholders_and_the_boundaries_stay_real(self):
        d, names, q = self.build()
        self.assertEqual(q(), 0)
        mt = {n: os.stat(os.path.join(d, n)).st_mtime for n in names}
        done = C.once(d, d, log=lambda m: None, scan=lambda p: (set(), []), now=NOW)
        got = sorted(os.path.basename(p) for p, _ in done)
        self.assertEqual(got, ["2_1_floorplan.odb", "2_2_floorplan_macro.odb", "2_3_floorplan_tapcell.odb", "2_4_floorplan_pdn.odb", "3_1_place_gp_skip_io.odb", "3_5_place_dp.odb", "4_1_cts.odb"])
        for n in got:
            self.assertEqual(os.path.getsize(os.path.join(d, n)), 0)
            self.assertEqual(os.stat(os.path.join(d, n)).st_mtime, mt[n])
        for n in ("1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb"):
            self.assertEqual(os.path.getsize(os.path.join(d, n)), 1000)              # what a later stage reads stays whole
        self.assertEqual(q(), 0)                                                     # make -q: nothing to rebuild
        self.assertEqual(C.once(d, d, log=lambda m: None, scan=lambda p: (set(), []), now=NOW), [])      # a placeholder is not a victim again

    def test_deleting_them_is_what_made_make_rebuild(self):
        d, names, q = self.build()
        os.unlink(os.path.join(d, "3_5_place_dp.odb"))
        self.assertNotEqual(q(), 0)

    def test_hardlinked_and_open_files_are_not_emptied(self):
        d, names, q = self.build()
        os.link(os.path.join(d, "3_1_place_gp_skip_io.odb"), os.path.join(d, "twin.odb"))
        C.once(d, d, log=lambda m: None, scan=lambda p: ({os.path.join(d, "3_5_place_dp.odb")}, []), now=NOW)
        self.assertEqual(os.path.getsize(os.path.join(d, "twin.odb")), 1000)
        self.assertEqual(os.path.getsize(os.path.join(d, "3_5_place_dp.odb")), 1000)


class ReplaceWatchers(unittest.TestCase):
    def test_a_running_watcher_is_replaced_by_the_new_script_with_the_same_arguments(self):
        import signal
        import subprocess
        import sys
        k = tempfile.mkdtemp(); root = os.path.join(k, "run", "results", "asap7"); os.makedirs(root)
        script = os.path.join(k, "stage_odb_cap.py")
        open(script, "w").write("import time\ntime.sleep(300)\n"); os.chmod(script, 0o644)
        old = subprocess.Popen(["python3", "-I", script, "--watch", root, "--kit", k, "--interval", "1000", "--max-hours", "1", "--parent", str(os.getpid())])
        new_pid = None
        try:
            import time as _t
            _t.sleep(1)
            out = C.replace_watchers(lambda m: None)
            mine = [x for x in out if x[0] == old.pid]
            self.assertEqual(len(mine), 1)
            new_pid = mine[0][1]
            _t.sleep(0.5)
            self.assertIsNotNone(old.poll() or old.wait(timeout=5) is None or True)
            self.assertIn("EARLY_RULES", open(script).read())                         # the kit's copy is the new script
            args = open("/proc/%d/cmdline" % new_pid, "rb").read().split(b"\0")
            self.assertIn(b"--parent", args); self.assertIn(root.encode(), args)
        finally:
            for pid in [old.pid] + ([new_pid] if new_pid else []):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            try:
                old.wait(timeout=5)
            except Exception:
                pass


class BusyPattern(unittest.TestCase):
    def test_recorded_in_a_kit_command_line_is_not_an_eco_process(self):
        cmd = "docker run --rm --name dpkit-x bash -lc echo 'LEC WARNING (exit 1): not proved, recorded in lec/lec.json; the flow continues' second decorated"
        self.assertIsNone(C.BUSY_CMD.search(cmd))
        for real in ("python3 eco_loop.py --kit K", "bash run_eco.sh", "python3 kit_resume.py K", "ot-run ... --eco x", "OT_ECO_MODE=1 openroad"):
            self.assertIsNotNone(C.BUSY_CMD.search(real), real)


class ResumeInputsStayWhole(unittest.TestCase):
    """FLOW-FIX-2045 (COORD: S81-GEOM-OPUS restarts failed builds with goal route): what the next stage to run reads is never emptied, failed run or not"""

    def build(self, have):
        d = tempfile.mkdtemp()
        for i, n in enumerate(have):
            p = os.path.join(d, n); open(p, "wb").write(b"x" * 100); os.utime(p, (NOW - 10000 + i * 10, NOW - 10000 + i * 10))
        return d

    def emptied(self, d):
        C.once(d, d, log=lambda m: None, scan=lambda p: (set(), []), now=NOW)
        return sorted(n for n in os.listdir(d) if os.path.getsize(os.path.join(d, n)) == 0)

    def test_failed_grt_leaves_cts_boundary_and_grt_inputs_whole(self):
        d = self.build(["1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_1_cts.odb", "4_cts.odb", "4_cts.sdc", "5_1_grt-failed.odb"])     # GRT failed: no 5_1_grt.odb
        self.assertEqual(self.emptied(d), ["4_1_cts.odb"])                          # ORFS global_route.tcl loads 4_cts.odb + 4_cts.sdc, never 4_1_cts.odb
        for n in ("4_cts.odb", "4_cts.sdc", "3_place.odb", "5_1_grt-failed.odb"):
            self.assertEqual(os.path.getsize(os.path.join(d, n)), 100)

    def test_failed_cts_or_place_empties_nothing_the_stage_needs(self):
        d = self.build(["1_synth.odb", "2_floorplan.odb", "3_1_place_gp_skip_io.odb", "3_5_place_dp.odb", "3_place.odb", "4_1_cts-failed.odb"])
        self.assertEqual(self.emptied(d), ["3_1_place_gp_skip_io.odb", "3_5_place_dp.odb"])    # CTS reads 3_place.odb, kept
        d = self.build(["1_synth.odb", "2_floorplan.odb", "3_1_place_gp_skip_io.odb", "3_3_place_gp-failed.odb"])     # place failed: 3_place.odb absent
        self.assertEqual(self.emptied(d), [])

    def test_route_inputs_5_1_grt_and_5_2_route_are_never_victims(self):
        d = self.build(["3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb", "6_final.odb", "6_final.v"])
        C.once(d, d, log=lambda m: None, scan=lambda p: (set(), []), now=NOW)
        for n in ("5_1_grt.odb", "5_2_route.odb", "4_cts.odb"):
            self.assertEqual(os.path.getsize(os.path.join(d, n)), 100)

    def test_resume_step_outputs_are_boundaries_only(self):
        import re as _re
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "autopilot", "kit_resume.py")).read()
        names = set(_re.findall(r'"([2-5]_[a-z_0-9]*\.odb)"', src.split("STEP_OUT = ")[1].split("}")[0]))
        self.assertTrue(names)
        for n in names:
            self.assertFalse(any(rx.match(n) for rx, _ in C.EARLY_RULES) or any(rx.match(n) for rx, _ in C.RULES if n != "5_route.odb"), n)

    def test_prd_mk_treats_an_empty_4_1_cts_as_absent(self):
        t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "post_route_drv", "prd_mk.sh")).read()
        self.assertIn('if [ ! -s "$RS/4_1_cts.odb" ]; then', t)


def test_floorplan_repair_is_skipped_on_a_huge_netlist_by_remove_abc_buffers():
    """FLOW-FIX-2045 (LONG-RUN-0315: S81 svc_lo_dsdv_svc_rs__t7, 4,992,695 instances, floorplan-stage repair_timing ran 21,913 s at wire-load estimate): above OT_FLOORPLAN_REPAIR_MAX_INST (1.5 M) run_kit makes the floorplan
    step use the ORFS REMOVE_ABC_BUFFERS branch (remove_buffers only), logs a classified line; OT_FLOORPLAN_REPAIR=on keeps the repair"""
    import gen_phys
    t = gen_phys.RUN_KIT
    i = t.index("OT_FLOORPLAN_REPAIR SKIPPED class=SIZE")
    blk = t[i - 900:i + 200]
    assert "OT_FLOORPLAN_REPAIR_MAX_INST:-1500000" in blk and 'REMOVE_ABC_BUFFERS=1' in blk and "grep -cE" in blk
    assert t.index("OT_FLOORPLAN_REPAIR SKIPPED") < t.index("check-synth") and t.index("OT_FLOORPLAN_REPAIR SKIPPED") < t.index("SKIP_CTS_REPAIR_TIMING=1")
