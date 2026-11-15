"""PLANBYPASS_1114 (OWNER 11-14 19:40): plan connectivity jobs skip memory admission."""
import tempfile, contextlib, importlib.machinery, importlib.util, io, os, pathlib, unittest
from unittest.mock import patch

H = pathlib.Path(__file__).parent


def load(name, fn):
    l = importlib.machinery.SourceFileLoader(name, str(H / fn))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, l)); l.exec_module(m)
    return m


R, RUN = load("ot_heavy_reconcile_planbypass", "ot-heavy-reconcile"), load("ot_run_planbypass", "ot-run")


class Bypass(unittest.TestCase):
    def gate(self, avail, argv, conf):
        out = io.StringIO()
        with patch.object(R, "meminfo", return_value=(1007.0, avail)), patch.object(R, "conf", side_effect=lambda k: conf.get(k, 0)), \
                patch.object(R, "sizes", return_value={}), patch.object(R, "plan_census", return_value=(5, [])), patch.object(R, "classify", return_value="route"), \
                patch.object(R, "peak_history", return_value={}), patch.object(R, "running_units_light", return_value=[]), patch.object(R, "D", tempfile.mkdtemp()), contextlib.redirect_stdout(out):
            R.gate_locked(48, argv)
        return out.getvalue()

    def test_plan_job_is_admitted_with_no_memory_left_and_past_the_plan_cap(self):
        conf = dict(PLAN_BYPASS=1, SIMPLE_ADMIT=1, PLAN_PRIO=1, PLAN_MAX_RUNNING=1, INV_HEADROOM_GB=64, SMALL_FLOOR_GB=36, SIMPLE_PEAK=1, PEAK_PCT=0.9, PEAK_MIN_N=3, SIMPLE_FRESH_S=0)
        txt = self.gate(3.0, ["bash", "chainR92.sh"], conf)          # 3 GB free, 5 plan jobs already running, cap 1
        self.assertTrue(txt.startswith("OK 48"), txt)
        self.assertIn("PLAN_BYPASS", txt)

    def test_a_normal_job_still_waits(self):
        conf = dict(PLAN_BYPASS=1, SIMPLE_ADMIT=1, PLAN_PRIO=1, PLAN_MAX_RUNNING=1, INV_HEADROOM_GB=64, SMALL_FLOOR_GB=36, SIMPLE_PEAK=1, PEAK_PCT=0.9, PEAK_MIN_N=3, SIMPLE_FRESH_S=0)
        self.assertTrue(self.gate(3.0, ["bash", "kit_route.sh"], conf).startswith("NO"))

    def test_bypass_off_keeps_the_old_gate(self):
        conf = dict(PLAN_BYPASS=0, SIMPLE_ADMIT=1, PLAN_PRIO=1, PLAN_MAX_RUNNING=1, INV_HEADROOM_GB=64, SMALL_FLOOR_GB=36, SIMPLE_PEAK=1, PEAK_PCT=0.9, PEAK_MIN_N=3, SIMPLE_FRESH_S=0)
        self.assertNotIn("PLAN_BYPASS", self.gate(3.0, ["bash", "chainR92.sh"], conf))

    def test_ot_run_places_a_plan_job_on_the_listed_host_with_the_most_memavailable(self):
        res = {h: dict(free_gb=1, admit_gb=1, avail_gb=a, ncpu=96, load1=1, total_gb=1007) for h, a in (("epyc7", 40), ("epyc8", 107), ("epyc9", 65))}
        with patch.dict(os.environ, {"OT_RUN_PRIO_ENV": "OT_HEAVY_PRIO=plan "}), patch.object(RUN, "reserved", side_effect=lambda h, r: r), \
                patch.object(RUN, "physically_capable", return_value=True):
            self.assertEqual(RUN.choose(res, 48), ("epyc8", False))


if __name__ == "__main__":
    unittest.main()
