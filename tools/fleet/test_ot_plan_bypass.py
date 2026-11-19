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
        with patch.dict(os.environ, {"OT_HEAVY_PRIO": "plan"}):
            txt = self.gate(3.0, ["bash", "chainR92.sh"], conf)          # 3 GB free, 5 plan jobs already running, cap 1
        self.assertTrue(txt.startswith("OK 48"), txt)
        self.assertIn("PLAN_BYPASS", txt)

    def test_a_normal_job_still_waits(self):
        conf = dict(PLAN_BYPASS=1, SIMPLE_ADMIT=1, PLAN_PRIO=1, PLAN_MAX_RUNNING=1, INV_HEADROOM_GB=64, SMALL_FLOOR_GB=36, SIMPLE_PEAK=1, PEAK_PCT=0.9, PEAK_MIN_N=3, SIMPLE_FRESH_S=0)
        self.assertTrue(self.gate(3.0, ["bash", "kit_route.sh"], conf).startswith("NO"))

    def test_bypass_off_keeps_the_old_gate(self):
        conf = dict(PLAN_BYPASS=0, SIMPLE_ADMIT=1, PLAN_PRIO=1, PLAN_MAX_RUNNING=1, INV_HEADROOM_GB=64, SMALL_FLOOR_GB=36, SIMPLE_PEAK=1, PEAK_PCT=0.9, PEAK_MIN_N=3, SIMPLE_FRESH_S=0)
        with patch.dict(os.environ, {"OT_HEAVY_PRIO": "plan"}):
            self.assertNotIn("PLAN_BYPASS", self.gate(3.0, ["bash", "chainR92.sh"], conf))

    def test_an_argv_pattern_alone_never_bypasses(self):
        """BYPASS-ENV-1119: wave kit launches (bind.py kit-rtl, chain*.sh, run_gate*) without the explicit env wait like any job"""
        conf = dict(PLAN_BYPASS=1, SIMPLE_ADMIT=1, PLAN_PRIO=1, PLAN_MAX_RUNNING=1, INV_HEADROOM_GB=64, SMALL_FLOOR_GB=36, SIMPLE_PEAK=1, PEAK_PCT=0.9, PEAK_MIN_N=3, SIMPLE_FRESH_S=0)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OT_HEAVY_PRIO", None)
            for argv in (["python3", "bind.py", "kit-rtl", "--x"], ["bash", "chainR92.sh"], ["bash", "run_gate_x.sh"]):
                self.assertTrue(self.gate(3.0, argv, conf).startswith("NO"), argv)
        self.assertFalse(R.bypass_like(["python3", "bind.py", "kit-rtl"]))
        self.assertTrue(R.bypass_like(["x"], ["OT_HEAVY_PRIO=plan"]))

    def test_type_builds_do_not_bypass(self):
        conf = dict(PLAN_BYPASS=1, SIMPLE_ADMIT=1, PLAN_PRIO=1, PLAN_MAX_RUNNING=1, INV_HEADROOM_GB=64, SMALL_FLOOR_GB=36, SIMPLE_PEAK=1, PEAK_PCT=0.9, PEAK_MIN_N=3, SIMPLE_FRESH_S=0)
        eco = ["bash", "-c", "cd /x/typekvioft/bundle/die_plan && python3 -I eco_loop.py r"]
        self.assertNotIn("PLAN_BYPASS", self.gate(3.0, eco, conf))

    def test_ot_run_rejects_priority_plan_for_a_type_build(self):
        self.assertTrue(RUN.plan_cmd_ok(["bash", "/x/s81-b3-clk/chainD92.sh"]))
        self.assertTrue(RUN.plan_cmd_ok(["bash", "bindB4L4_leafplan.sh"]))
        self.assertTrue(RUN.plan_cmd_ok(["bash", "/x/kv-hgi-refloor/run_gate.sh", "r3"]))
        self.assertTrue(RUN.plan_cmd_ok(["python3", "latcheck_kv.py"]))
        self.assertFalse(RUN.plan_cmd_ok(["bash", "-c", "cd /x/typekvioft && python3 -I eco_loop.py r"]))
        self.assertFalse(RUN.plan_cmd_ok(["bash", "run_kit.sh"]))
        with patch.dict(os.environ, {"OT_RUN_PLAN_OK": "1"}):
            self.assertTrue(RUN.plan_cmd_ok(["bash", "run_kit.sh"]))

    def test_ot_run_places_a_plan_job_on_the_listed_host_with_the_most_memavailable(self):
        res = {h: dict(free_gb=1, admit_gb=1, avail_gb=a, ncpu=96, load1=1, total_gb=1007) for h, a in (("epyc7", 40), ("epyc8", 107), ("epyc9", 65))}
        with patch.dict(os.environ, {"OT_RUN_PRIO_ENV": "OT_HEAVY_PRIO=plan "}), patch.object(RUN, "reserved", side_effect=lambda h, r: r), \
                patch.object(RUN, "physically_capable", return_value=True):
            self.assertEqual(RUN.choose(res, 48), ("epyc8", False))


class Reserve(unittest.TestCase):
    def test_plan_job_remaining_peak_is_held_back_only_for_its_own_units(self):
        hist = {"bind": [60.0, 70.0, 80.0, 90.0]}
        units = [("oth-ubuntu-111-1794700000", 120.0, "bind", 30.0), ("oth-ubuntu-222-1794700001", 48.0, "other", 5.0)]
        r = R.plan_reserve(units, hist, {"111"}, 0.9, 3, 0.5)
        self.assertAlmostEqual(r, 90.0 - 30.0)                  # p90 of the class minus what it holds now; the other unit is not a plan job
        self.assertEqual(R.plan_reserve(units, hist, set(), 0.9, 3, 0.5), 0.0)
        self.assertAlmostEqual(R.plan_reserve([("oth-ubuntu-111-1", 120.0, "new", 20.0)], {}, {"111"}, 0.9, 3, 0.5), 60.0 - 20.0)   # no history: 0.5 x request


if __name__ == "__main__":
    unittest.main()
