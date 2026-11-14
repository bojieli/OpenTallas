"""SIMPLE_PEAK (ADMIT-TUNE-1 11-14, COORD): admit on the expected PEAK of the job (p90 of completed runs of its class, else the request)
and subtract the expected remaining growth of the running jobs; not the request, not the current RSS."""
import contextlib, importlib.machinery, importlib.util, io, os, pathlib, tempfile, unittest
from unittest.mock import patch

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_peak", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile_peak", loader))
loader.exec_module(R)
HIST = {"route": [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 40.0], "few": [30.0, 31.0]}


class Peak(unittest.TestCase):
    def test_expected_peak_is_the_p90_capped_at_the_request(self):
        self.assertEqual(R.expected_peak("route", 48, HIST), 40.0)          # index int(0.9 * 10) = 9
        self.assertEqual(R.expected_peak("route", 30, HIST), 30.0)          # a job cannot exceed its MemoryMax
        self.assertEqual(R.expected_peak("few", 48, HIST), 48.0)            # < 3 completed runs: the request
        self.assertEqual(R.expected_peak("never", 48, HIST), 48.0)

    def test_reserve_counts_only_remaining_growth_scaled_by_frac(self):
        units = [("u1", 48.0, "route", 5.0), ("u2", 48.0, "route", 45.0), ("u3", 48.0, "never", 8.0)]
        self.assertAlmostEqual(R.peak_reserve(units, HIST, 1.0), (40 - 5) + 0 + (48 - 8))
        self.assertAlmostEqual(R.peak_reserve(units, HIST, 0.1), 7.5)

    def test_peak_history_uses_completed_runs_only(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("t\tu\trun_kit.sh:route\t48\t20.0\t100\t0\nt\tu\trun_kit.sh:route\t48\t99.0\t100\t137\nbad\n")
        self.assertEqual(R.peak_history(f.name), {"run_kit.sh:route": [20.0]})

    def gate(self, avail, units, cls="route", mem=48, conf=None):
        env = dict({"SIMPLE_ADMIT": "1", "SIMPLE_PEAK": "1", "INV_HEADROOM_GB": "16", "PEAK_GROWTH_FRAC": "0.1", "SIMPLE_FRESH_S": "0"}, **(conf or {}))
        d = tempfile.mkdtemp()
        with patch.dict(os.environ, env), patch.object(R, "D", d), patch.object(R, "classify", return_value=cls), \
                patch.object(R, "sizes", return_value={}), patch.object(R, "meminfo", return_value=(1000.0, float(avail))), \
                patch.object(R, "peak_history", return_value=HIST), patch.object(R, "running_units_light", return_value=units), \
                patch.object(R, "read_units", side_effect=AssertionError("slow read_units")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                R.gate_locked(48, ["x"])
        return out.getvalue()

    def test_admits_when_free_covers_expected_peak_after_growth(self):
        units = [("u%d" % i, 48.0, "route", 5.0) for i in range(10)]      # growth 10 x 35 x 0.1 = 35
        self.assertTrue(self.gate(16 + 35 + 40, units).startswith("OK 40 "))
        self.assertTrue(self.gate(16 + 35 + 39, units).startswith("NO 40 "))

    def test_unknown_class_is_charged_its_request(self):
        self.assertTrue(self.gate(16 + 48, [], cls="never").startswith("OK 48 "))
        self.assertTrue(self.gate(16 + 47, [], cls="never").startswith("NO 48 "))

    def test_off_by_default_keeps_the_simple_rule(self):
        self.assertIn("SIMPLE_ADMIT:", self.gate(100, [], conf={"SIMPLE_PEAK": "0"}))


if __name__ == "__main__":
    unittest.main()
