"""FABLE-FLOW-1555 A: SIMPLE_ADMIT status rows carry the measured-peak gap (peak 0 on every host before)."""
import importlib.machinery, importlib.util, os, pathlib, tempfile, unittest

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_pk", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile_pk", loader))
loader.exec_module(R)


class PeakGap(unittest.TestCase):
    def mk(self, units):
        d = tempfile.mkdtemp(); sc = tempfile.mkdtemp()
        for name, reserved, cur_gb in units:
            open(f"{d}/res.{name}", "w").write(f"{name} {reserved}\n")
            if cur_gb is not None:
                os.makedirs(f"{sc}/x/{name}.scope")
                open(f"{sc}/x/{name}.scope/memory.current", "w").write(str(int(cur_gb * 2**30)))
        return d, f"{sc}/x/oth-*.scope"

    def test_gap_is_reserved_minus_current_summed_and_never_negative(self):
        d, g = self.mk([("oth-a-1", 40, 10.0), ("oth-b-2", 16, 20.0), ("oth-c-3", 8, 8.0)])
        self.assertAlmostEqual(R.peak_gap_gb(d, g), 30.0, places=3)          # 40-10 = 30; the job past its charge adds 0

    def test_units_without_a_live_scope_or_a_bad_file_are_ignored(self):
        d, g = self.mk([("oth-a-1", 40, None), ("oth-b-2", 16, 4.0)])
        open(f"{d}/res.oth-z-9", "w").write("garbage")
        self.assertAlmostEqual(R.peak_gap_gb(d, g), 12.0, places=3)

    def test_a_container_job_whose_scope_reads_zero_adds_no_gap(self):
        d, g = self.mk([("oth-a-1", 48, 0.0), ("oth-b-2", 48, 0.01), ("oth-c-3", 40, 10.0)])
        self.assertAlmostEqual(R.peak_gap_gb(d, g), 30.0, places=3)          # only the unit that really runs in its scope counts

    def test_empty_host_has_no_gap(self):
        d, g = self.mk([])
        self.assertEqual(R.peak_gap_gb(d, g), 0.0)

    def test_the_status_row_reports_the_gap(self):
        src = open(P).read()
        self.assertIn("peak_gap=round(raw_gap, 1)", src)
        self.assertIn('conf("PEAK_GAP_FACTOR")', src)               # charged only on request: the default 0 keeps the owner's light admission
        self.assertIn('avail - conf("INV_HEADROOM_GB") - gap', src)


if __name__ == "__main__":
    unittest.main()


class PlanGap(unittest.TestCase):
    def test_plan_job_charges_its_unreached_peak(self):
        import subprocess
        d = tempfile.mkdtemp()
        sl = subprocess.Popen(["sleep", "30"])
        try:
            open(f"{d}/plan.job.{sl.pid}", "w").close()
            open(f"{d}/res.oth-u-{sl.pid}-1795000000", "w").write(f"oth-u-{sl.pid}-1795000000 40\n")
            gap = R.plan_gap_gb(d)
            self.assertGreater(gap, 39.0)                    # a sleep holds ~0 GB: the whole 40 GB charge is still to come
            self.assertLessEqual(gap, 40.0)
            os.unlink(f"{d}/plan.job.{sl.pid}")
            self.assertEqual(R.plan_gap_gb(d), 0.0)          # no plan marker: nothing charged
        finally:
            sl.kill(); sl.wait()

    def test_the_charge_is_capped_and_switchable(self):
        src = open(P).read()
        self.assertIn("min(plan_gap_gb(), 0.25 * avail)", src)
        self.assertIn('conf("PLAN_GAP_FACTOR")', src)


class MeasuredGap(unittest.TestCase):
    def test_only_classes_with_history_charge_their_unreached_peak(self):
        hist = {"synth": [20.0, 22.0, 24.0, 26.0]}
        units = [("u1", 48.0, "synth", 5.0),       # measured p90 ~26 GB, uses 5: 21 GB still to come
                 ("u2", 48.0, "newcls", 1.0),      # no history: nothing charged
                 ("u3", 16.0, "synth", 30.0)]      # already above its peak: nothing
        g = R.measured_gap_gb(units, hist)
        self.assertAlmostEqual(g, 26.0 - 5.0, places=3)

    def test_the_charge_is_capped_at_half_of_available_and_switchable(self):
        src = open(P).read()
        self.assertIn("min(measured_gap_gb(), 0.5 * avail)", src)
        self.assertIn('conf("MEASURED_GAP_FACTOR")', src)
