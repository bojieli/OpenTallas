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
        self.assertIn("peak_gap=round(gap, 1)", src)
        self.assertIn('avail - conf("INV_HEADROOM_GB") - gap', src)


if __name__ == "__main__":
    unittest.main()
