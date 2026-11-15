"""STAGE_PEAK (ADMIT-TUNE-1 11-14, OWNER-approved Fable fix 3): running builds are charged their measured STAGE peak (current + next stage), not their RSS now."""
import importlib.machinery, importlib.util, json, os, pathlib, tempfile, unittest

H = pathlib.Path(__file__).parent


def load(name, fn):
    l = importlib.machinery.SourceFileLoader(name, str(H / fn))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, l)); l.exec_module(m)
    return m


R, S = load("ot_heavy_reconcile_stage", "ot-heavy-reconcile"), load("ot_stage_peaks", "ot-stage-peaks")
TAB = {"global_route.tcl": 30.0, "detail_route.tcl": 40.0, "cts.tcl": 14.0, "final_report.tcl": 6.0, "yosys_x.tcl": 20.0}


class Charge(unittest.TestCase):
    def test_stage_of_reads_the_flow_script(self):
        self.assertEqual(R.stage_of("openroad -exit -no_init /OpenROAD-flow-scripts/flow/scripts/detail_route.tcl -metrics m"), "detail_route.tcl")
        self.assertEqual(R.stage_of("bash -c sleep 1"), "")

    def test_charge_is_current_plus_next_stage_peak_never_below_rss(self):
        self.assertEqual(R.stage_peak(TAB, "global_route.tcl", 12.0, 1), 40.0)      # GRT job also charged for the DRT that follows
        self.assertEqual(R.stage_peak(TAB, "global_route.tcl", 12.0, 0), 30.0)      # lookahead 0: current stage only
        self.assertEqual(R.stage_peak(TAB, "detail_route.tcl", 45.0, 1), 45.0)      # RSS already above the table: RSS
        self.assertEqual(R.stage_peak(TAB, "cts.tcl", 5.0, 1), 30.0)
        self.assertEqual(R.stage_peak(TAB, "yosys_x.tcl", 3.0, 1), 20.0)            # outside the flow order: its own table peak
        self.assertEqual(R.stage_peak(TAB, "unknown.tcl", 3.0, 1), 3.0)

    def test_growth_sums_peak_minus_rss_scaled_by_frac(self):
        procs = [("openroad", "openroad grt global_route.tcl", 12.0), ("openroad", "openroad detail_route.tcl", 38.0), ("python3", "lec", 60.0)]
        g, n = R.stage_growth(TAB, 1, 1.0, procs)
        self.assertEqual((g, n), ((40 - 12) + (40 - 38) + 0, 3))
        self.assertEqual(R.stage_growth(TAB, 1, 0.5, procs)[0], 15.0)

    def test_new_job_is_charged_its_first_stage_peak(self):
        self.assertEqual(R.first_stage_peak({"floorplan.tcl": 2.0, "global_place.tcl": 21.8, "global_route.tcl": 30.0}), 21.8)
        self.assertEqual(R.first_stage_peak({}), 0.0)
        self.assertEqual(R.DEFAULTS["STAGE_LOOKAHEAD"], 0.0)

    def test_table_loads_and_survives_garbage(self):
        d = tempfile.mkdtemp(); p = d + "/t.json"
        open(p, "w").write(json.dumps(TAB)); self.assertEqual(R.load_stage_table(p)["cts.tcl"], 14.0)
        open(p, "w").write("{oops"); self.assertEqual(R.load_stage_table(p), {})
        self.assertEqual(R.load_stage_table(d + "/missing.json"), {})


class Sampler(unittest.TestCase):
    def test_table_is_p90_x_1_1_with_five_samples_else_seed(self):
        now = 1_000_000.0
        rows = [(now - 10, "global_route.tcl", float(x)) for x in (10, 12, 14, 16, 18, 20, 22, 24, 26, 30)]
        t = S.build_table(rows, now)
        self.assertEqual(t["global_route.tcl"], round(30 * 1.1, 1))                 # index int(0.9 * 10) = 9
        self.assertEqual(S.build_table(rows[:4], now)["global_route.tcl"], S.SEED["global_route.tcl"])   # < 5 samples: seed
        old = [(now - 2 * 86400, "global_route.tcl", 99.0)] * 9
        self.assertEqual(S.build_table(old, now)["global_route.tcl"], S.SEED["global_route.tcl"])        # older than 24 h: ignored

    def test_scan_and_main_record_a_vanished_stage_with_its_high_water_mark(self):
        d = tempfile.mkdtemp(); proc = d + "/proc"
        def mk(pid, comm, cmd, hwm_kb):
            os.makedirs(f"{proc}/{pid}")
            open(f"{proc}/{pid}/comm", "w").write(comm + "\n"); open(f"{proc}/{pid}/cmdline", "w").write(cmd.replace(" ", "\0"))
            open(f"{proc}/{pid}/stat", "w").write("1 (%s) S %s" % (comm, " ".join(["0"] * 18 + ["12345"])))
            open(f"{proc}/{pid}/status", "w").write(f"VmRSS:\t{hwm_kb} kB\nVmHWM:\t{hwm_kb} kB\n")
        mk(11, "openroad", "openroad detail_route.tcl", 30 * 1048576); mk(12, "bash", "bash x.tcl", 5)
        cur = S.scan(proc)
        self.assertEqual(list(cur.values()), [("detail_route.tcl", 30.0)])
        state = {"7:1": ("global_route.tcl", 21.5)}                                  # pid 7 was seen last minute and is gone now
        S.json.dump(state, open(d + "/stage-peaks.state", "w"))
        S.scan = lambda proc="/proc": cur
        S.main(["--dir", d])
        self.assertIn("global_route.tcl\t21.5", open(d + "/stage-peaks.tsv").read())
        self.assertEqual(json.load(open(d + "/stage-peaks.json"))["detail_route.tcl"], S.SEED["detail_route.tcl"])


if __name__ == "__main__":
    unittest.main()
